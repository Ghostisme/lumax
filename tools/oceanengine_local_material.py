"""Native DeerFlow tool for OceanEngine local material operations."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path, PurePosixPath
from typing import Any

from langchain.tools import ToolRuntime, tool
from langgraph.config import get_config

from deerflow.config import get_app_config
from deerflow.config.paths import VIRTUAL_PATH_PREFIX, get_paths, join_host_path
from deerflow.runtime.user_context import get_effective_user_id
from tools.managed_mcp_guard import allow_managed_mcp_calls
from tools.oceanengine_local_project_runtime import endpoint_runner, rule_loader
from tools.oceanengine_local_project_runtime.agent_visible import agent_visible_result

BUSINESS_TOOL_NAME = "oceanengine_local_material"
SKILL_NAME = "oceanengine-local-material"
UPLOADS_VIRTUAL_PREFIX = f"{VIRTUAL_PATH_PREFIX}/uploads/"
logger = logging.getLogger(__name__)
_DUPLICATE_UPLOAD_MARKERS = (
    "素材已上传",
    "视频已上传",
    "已存在",
    "重复",
    "幂等",
    "命中已有",
    "already uploaded",
    "already exists",
    "duplicate",
    "duplicated",
    "idempotent",
)
_MATERIAL_ID_KEYS = {"material_id", "materialId"}
_VIDEO_ID_KEYS = {"video_id", "videoId"}
_VIDEO_URL_KEYS = {"video_url", "videoUrl"}
_UPLOAD_MESSAGE_KEYS = {"message", "msg", "status", "status_desc", "statusDesc", "description", "reason"}

CREATE_FLOW_CAPABILITIES = {"get-library-videos", "upload-video"}
CREATE_FLOW_INTENT_KEYWORDS = (
    "创建本地推项目",
    "创建本地推投流项目",
    "创建投流项目",
    "创建项目",
    "投流项目",
)
CREATE_FLOW_FIELD_KEYWORDS = (
    "投手",
    "营销场景",
    "投放目标",
    "单元类型",
    "投放门店",
    "投放商品",
    "日预算",
    "出价",
    "视频从素材库",
    "素材库选择",
)


def _skill_root() -> Path:
    return get_app_config().skills.get_skills_path() / "custom" / SKILL_NAME


def _load_capability_rule(skill_root: Path, capability: str) -> dict[str, Any]:
    index_path = skill_root / "rules" / "index.json"
    rules_index = json.loads(index_path.read_text(encoding="utf-8"))
    for item in rules_index.get("capabilities", []):
        if item.get("name") == capability:
            rule_path = skill_root / item["rule"]
            return rule_loader.load_rule_config(rule_path)
    supported = ", ".join(item.get("name", "") for item in rules_index.get("capabilities", []))
    raise ValueError(f"未知的 oceanengine-local-material 能力：{capability}。可选能力：{supported}")


def _build_user_visible_text(result: dict[str, Any], spec: dict[str, Any]) -> str:
    title = spec.get("title") or "素材管理接口"
    message = result.get("message") or "执行完成"
    if result.get("success"):
        return f"{title}：{message}"
    errors = result.get("errors") or []
    error_text = "；".join(str(item.get("message", "")) for item in errors if isinstance(item, dict) and item.get("message"))
    if error_text:
        return f"{title}未完成：{error_text}"
    return f"{title}未完成：{message}"


def _enrich_result(result: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(result)
    data = dict(enriched.get("data") or {})
    data.setdefault("execution_source", "deerflow-native-tool")
    data.setdefault("business_tool_name", BUSINESS_TOOL_NAME)
    data.setdefault(
        "mcp_server_name",
        spec.get("mcp_server_name") or spec.get("mcp", {}).get("server") or "platform-agent-biz",
    )
    data.setdefault("mcp_tool_name", spec.get("mcp_tool_name") or spec.get("mcp", {}).get("tool"))
    data.setdefault("user_visible_text", _build_user_visible_text(enriched, spec))
    enriched["data"] = data
    return enriched


def _missing_mcp_result(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "success": False,
        "message": "当前 MCP 工具缺失，无法执行该官方接口。",
        "data": {
            "path": spec["path"],
            "title": spec["title"],
            "mcp_missing": True,
        },
        "errors": [
            {
                "field": "mcp_tool_name",
                "message": f"{spec['title']} 当前未在 platform-agent-biz 暴露对应 MCP 工具，请补齐 MCP server 后再执行。",
            }
        ],
        "tool_name": BUSINESS_TOOL_NAME,
        "request_id": None,
    }


def _current_thread_id(explicit_thread_id: str | None = None) -> str | None:
    if explicit_thread_id:
        return explicit_thread_id
    try:
        config = get_config()
    except RuntimeError:
        return None
    configurable = config.get("configurable") or {}
    thread_id = configurable.get("thread_id")
    return str(thread_id) if thread_id else None


def _failure_result(spec: dict[str, Any], message: str, *, field: str = "video_file_path", data: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "success": False,
        "message": "聊天附件素材上传前置校验失败。",
        "data": {
            "path": spec["path"],
            "title": spec["title"],
            **(data or {}),
        },
        "errors": [{"field": field, "message": message}],
        "tool_name": BUSINESS_TOOL_NAME,
        "request_id": None,
    }


def _replace_private_path(value: Any, private_path: str, replacement: str) -> Any:
    if isinstance(value, str):
        sanitized = value.replace(private_path, replacement)
        parent = str(Path(private_path).parent)
        if parent and parent != private_path:
            sanitized = sanitized.replace(parent, "当前对话附件目录")
        return sanitized
    if isinstance(value, list):
        return [_replace_private_path(item, private_path, replacement) for item in value]
    if isinstance(value, dict):
        return {key: _replace_private_path(item, private_path, replacement) for key, item in value.items()}
    return value


def _normalized_key(value: str) -> str:
    return value.replace("_", "").lower()


def _iter_keyed_values(value: Any):
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str):
                yield key, item
            yield from _iter_keyed_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_keyed_values(item)


def _iter_text_values(value: Any):
    if isinstance(value, dict):
        for item in value.values():
            yield from _iter_text_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_text_values(item)
    elif isinstance(value, str):
        yield value


def _first_text_scalar_by_keys(value: Any, keys: set[str]) -> str | None:
    key_pattern = "|".join(re.escape(key) for key in sorted(keys, key=len, reverse=True))
    pattern = re.compile(
        rf'(?<![\w])["\']?(?:{key_pattern})["\']?\s*[:=]\s*["\']?(?P<value>[^"\'\s,}}\]\)]+)',
        re.IGNORECASE,
    )
    for text in _iter_text_values(value):
        for match in pattern.finditer(text):
            matched_value = match.group("value").strip()
            if matched_value and matched_value.lower() not in {"null", "none"}:
                return matched_value
    return None


def _first_scalar_by_keys(value: Any, keys: set[str]) -> Any | None:
    normalized_keys = {_normalized_key(key) for key in keys}
    for key, item in _iter_keyed_values(value):
        if _normalized_key(key) not in normalized_keys:
            continue
        if item is None or isinstance(item, dict | list):
            continue
        text = str(item).strip()
        if text:
            return item
    return _first_text_scalar_by_keys(value, keys)


def _message_texts(value: Any) -> list[str]:
    normalized_keys = {_normalized_key(key) for key in _UPLOAD_MESSAGE_KEYS}
    texts: list[str] = []
    for key, item in _iter_keyed_values(value):
        if _normalized_key(key) not in normalized_keys:
            continue
        if isinstance(item, str) and item.strip():
            texts.append(item.strip())
    return texts


def _has_duplicate_upload_signal(result: dict[str, Any], raw: Any) -> bool:
    data = result.get("data") if isinstance(result.get("data"), dict) else {}
    texts = [
        str(text)
        for text in (
            result.get("message"),
            data.get("message") if isinstance(data, dict) else None,
        )
        if isinstance(text, str) and text.strip()
    ]
    texts.extend(_message_texts(raw))
    texts.extend(_iter_text_values(raw))
    combined = "\n".join(texts).lower()
    return any(marker.lower() in combined for marker in _DUPLICATE_UPLOAD_MARKERS)


def _format_upload_video_result_text(prefix: str, *, material_id: Any | None, video_id: Any | None, video_url: Any | None) -> str:
    lines = [prefix]
    if material_id is not None:
        lines.append(f"素材ID：{material_id}")
    if video_id is not None:
        lines.append(f"视频ID：{video_id}")
    if video_url is not None:
        lines.append(f"视频地址：{video_url}")
    return "\n".join(lines)


def _apply_upload_video_result_semantics(result: dict[str, Any], *, dry_run: bool) -> dict[str, Any]:
    if dry_run or result.get("success") is not True:
        return result

    enriched = dict(result)
    data = dict(enriched.get("data") or {})
    raw = data.get("result")
    material_id = _first_scalar_by_keys(raw, _MATERIAL_ID_KEYS)
    video_id = _first_scalar_by_keys(raw, _VIDEO_ID_KEYS)
    video_url = _first_scalar_by_keys(raw, _VIDEO_URL_KEYS)
    has_confirmed_material = any(value is not None for value in (material_id, video_id, video_url))
    duplicate = _has_duplicate_upload_signal(enriched, raw)

    if duplicate and has_confirmed_material:
        display_text = _format_upload_video_result_text(
            "素材已上传",
            material_id=material_id,
            video_id=video_id,
            video_url=video_url,
        )
        data["upload_result_status"] = "already_uploaded"
        data["display_text"] = display_text
        data["user_visible_text"] = display_text
        enriched["message"] = "素材已上传。"
        enriched["data"] = data
        return enriched

    if not has_confirmed_material:
        display_text = "上传接口未返回可确认的素材结果，请通过素材中心或后续查询确认。"
        data["upload_result_status"] = "unconfirmed"
        data["display_text"] = display_text
        data["user_visible_text"] = display_text
        enriched["success"] = False
        enriched["message"] = "上传接口未返回可确认的素材结果。"
        errors = list(enriched.get("errors") or [])
        errors.append(
            {
                "field": "mcp",
                "message": "localFileVideoUpload 未返回素材ID、视频ID、视频地址或明确重复命中结果。",
            }
        )
        enriched["errors"] = errors
        enriched["data"] = data
        return enriched

    data["upload_result_status"] = "uploaded"
    if not isinstance(data.get("display_text"), str) or not data["display_text"].strip():
        display_text = _format_upload_video_result_text(
            "视频上传成功",
            material_id=material_id,
            video_id=video_id,
            video_url=video_url,
        )
        data["display_text"] = display_text
        data["user_visible_text"] = display_text
    enriched["data"] = data
    return enriched


def _virtual_upload_filename(video_file_path: str) -> str | None:
    if not video_file_path.startswith(UPLOADS_VIRTUAL_PREFIX):
        return None
    filename = video_file_path.removeprefix(UPLOADS_VIRTUAL_PREFIX)
    path = PurePosixPath(filename)
    if not filename or path.name != filename or filename in {".", ".."} or "\\" in filename:
        raise ValueError("视频文件路径必须指向当前对话附件目录中的单个文件。")
    return filename


def _prepare_upload_video_payload(
    spec: dict[str, Any],
    payload: dict[str, Any],
    *,
    thread_id: str | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if spec.get("name") != "upload-video":
        return payload, None

    video_file_path = payload.get("video_file_path")
    if not isinstance(video_file_path, str):
        return payload, None

    try:
        filename = _virtual_upload_filename(video_file_path)
    except ValueError as exc:
        return None, _failure_result(
            spec,
            f"视频文件路径不是有效的当前对话附件：{exc}",
            data={"upload_source": "chat-attachment"},
        )
    if filename is None:
        return payload, None

    current_thread_id = _current_thread_id(thread_id)
    if not current_thread_id:
        return None, _failure_result(
            spec,
            "无法确认当前对话 thread_id，不能安全地把聊天附件上传到本地推素材库。请重新通过当前对话附件上传视频后再试。",
            data={"upload_source": "chat-attachment"},
        )

    user_id = get_effective_user_id()
    paths = get_paths()
    try:
        actual_path = paths.resolve_virtual_path(current_thread_id, video_file_path, user_id=user_id)
    except ValueError as exc:
        return None, _failure_result(
            spec,
            f"视频文件路径不是有效的当前对话附件：{exc}",
            data={"upload_source": "chat-attachment"},
        )
    if not actual_path.is_file():
        return None, _failure_result(
            spec,
            "当前对话附件不存在或已失效，附件已上传到对话但不能继续上传到本地推素材库。",
            data={"upload_source": "chat-attachment"},
        )

    requested_filename = payload.get("filename")
    if isinstance(requested_filename, str) and requested_filename and requested_filename != filename:
        return None, _failure_result(
            spec,
            "请求中的视频文件名与当前对话附件不一致，请重新选择正确附件后再上传。",
            data={"upload_source": "chat-attachment"},
        )

    actual_size = actual_path.stat().st_size
    requested_size = payload.get("video_file_size_bytes")
    if requested_size is not None and requested_size != actual_size:
        return None, _failure_result(
            spec,
            "请求中的视频文件大小与当前对话附件不一致，请重新上传附件后再试。",
            field="video_file_size_bytes",
            data={"upload_source": "chat-attachment"},
        )

    host_uploads_dir = paths.host_sandbox_uploads_dir(current_thread_id, user_id=user_id)
    prepared = dict(payload)
    prepared["filename"] = filename
    prepared["video_file_path"] = join_host_path(host_uploads_dir, filename)
    prepared.setdefault("video_file_size_bytes", actual_size)
    return prepared, None


def run_oceanengine_local_material(capability: str, payload: dict[str, Any], *, dry_run: bool = False, thread_id: str | None = None) -> dict[str, Any]:
    skill_root = _skill_root()
    spec = _load_capability_rule(skill_root, capability)
    source_video_path = payload.get("video_file_path") if isinstance(payload, dict) else None
    logger.info(
        "OceanEngine native business tool invoked: business_tool=%s capability=%s dry_run=%s mcp_server=%s mcp_tool=%s",
        BUSINESS_TOOL_NAME,
        capability,
        dry_run,
        spec.get("mcp_server_name") or spec.get("mcp", {}).get("server") or "platform-agent-biz",
        spec.get("mcp_tool_name") or spec.get("mcp", {}).get("tool"),
    )

    if spec.get("mcp_missing"):
        return _enrich_result(_missing_mcp_result(spec), spec)

    payload, failure_result = _prepare_upload_video_payload(spec, payload, thread_id=thread_id)
    if failure_result is not None:
        return _enrich_result(failure_result, spec)

    with allow_managed_mcp_calls(BUSINESS_TOOL_NAME):
        result = endpoint_runner.run_endpoint(spec, payload, dry_run=dry_run)
    if spec.get("name") == "upload-video" and isinstance(payload.get("video_file_path"), str):
        replacement = "当前对话附件文件" if isinstance(source_video_path, str) and source_video_path.startswith(UPLOADS_VIRTUAL_PREFIX) else "授权视频文件"
        result = _replace_private_path(result, payload["video_file_path"], replacement)
        result = _apply_upload_video_result_semantics(result, dry_run=dry_run)
    return _enrich_result(result, spec)


def _message_text(message: object) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "\n".join(parts)
    return ""


def _latest_human_text(runtime: ToolRuntime[Any, Any] | None) -> str:
    state = getattr(runtime, "state", None) if runtime is not None else None
    if isinstance(state, dict):
        messages = state.get("messages")
    else:
        messages = getattr(state, "messages", None)
    if not isinstance(messages, list):
        return ""
    for message in reversed(messages):
        if getattr(message, "type", None) == "human":
            return _message_text(message)
    return ""


def _is_create_flow_context(capability: str, runtime: ToolRuntime[Any, Any] | None) -> bool:
    if capability not in CREATE_FLOW_CAPABILITIES:
        return False
    text = _latest_human_text(runtime)
    if not text:
        return False
    return any(keyword in text for keyword in CREATE_FLOW_INTENT_KEYWORDS) and any(
        keyword in text for keyword in CREATE_FLOW_FIELD_KEYWORDS
    )


def _create_flow_route_mismatch_result() -> dict[str, Any]:
    return {
        "success": False,
        "message": "当前请求属于创建项目流程，不能先调用素材工具。",
        "data": {
            "execution_source": "deerflow-native-tool",
            "business_tool_name": BUSINESS_TOOL_NAME,
            "route_tool_preference": "oceanengine_local_project_create_flow",
            "agent_guidance": "创建项目流程应使用 oceanengine_local_project_create_flow，并保留用户原始创建项目字段重试。",
            "user_visible_text": "请继续创建项目流程，我会在流程中处理素材库视频选择。",
        },
        "errors": [
            {
                "field": "tool",
                "message": "创建项目流程应使用 oceanengine_local_project_create_flow。",
            }
        ],
        "tool_name": BUSINESS_TOOL_NAME,
        "request_id": None,
    }


@tool("oceanengine_local_material", parse_docstring=True)
def oceanengine_local_material_tool(
    runtime: ToolRuntime[Any, Any],
    capability: str,
    payload_json: str,
    dry_run: bool = False,
) -> str:
    """Execute OceanEngine local material business operations through DeerFlow native logic.

    Use this tool for standalone local material operations such as uploading
    videos/images or querying material-library assets. If the user is creating
    a local-promotion project or 投流项目 and mentions project-flow fields such
    as 投手, 营销场景, 投放目标, 单元类型, 投放门店/商品, 用户定向, 排期预算,
    出价, or 视频素材, 不要先用本素材工具; do not call this material tool first. Use
    oceanengine_local_project_create_flow instead, even when the user says
    从素材库选择视频, because that flow owns material-library candidate
    clarification for 创建本地推项目.

    Args:
        capability: Capability name from oceanengine-local-material rules index, such as upload-video or get-library-videos.
        payload_json: JSON object string containing user business input fields.
        dry_run: Validate and build payload without calling MCP when true.
    """
    try:
        if _is_create_flow_context(capability, runtime):
            return json.dumps(_create_flow_route_mismatch_result(), ensure_ascii=False)
        payload = json.loads(payload_json) if payload_json else {}
        if not isinstance(payload, dict):
            raise ValueError("payload_json 必须是 JSON object。")
        result = run_oceanengine_local_material(capability=capability, payload=payload, dry_run=dry_run)
        result = agent_visible_result(result)
    except Exception as exc:
        result = {
            "success": False,
            "message": "OceanEngine 本地推素材业务工具执行失败。",
            "data": {
                "execution_source": "deerflow-native-tool",
                "business_tool_name": BUSINESS_TOOL_NAME,
                "capability": capability,
            },
            "errors": [{"field": "tool", "message": str(exc)}],
            "tool_name": BUSINESS_TOOL_NAME,
            "request_id": None,
        }
    return json.dumps(result, ensure_ascii=False)
