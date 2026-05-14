# 任务清单

## 1. 提案确认

- [x] 1.1 开启隔离 worktree：`/Users/shanqijie/PycharmProjects/lumax/.worktrees/optimize-local-project-create-flow`。
- [x] 1.2 运行 `openspec list` 和 `openspec list --specs`。
- [x] 1.3 确认 `openspec/project.md` 与 `openspec/AGENTS.md` 当前不存在，并以根 `AGENTS.md`、现有规格和本地推 skill/rules 为约束来源。
- [x] 1.4 检查 `create-project`、素材管理和单元管理现有规则边界。
- [x] 1.5 运行 `openspec validate optimize-local-project-create-flow --strict`。

## 2. Apply 前置要求

- [x] 2.1 Apply 阶段开始前使用 Superpowers，并确认实现计划。
- [x] 2.2 修改任何函数、类或方法前，按 GitNexus 规则对目标符号运行影响分析。本轮未修改既有函数、类或方法；新增编排模块并在收尾执行 GitNexus 变更检测。
- [x] 2.3 如果影响分析为 HIGH 或 CRITICAL，先向用户说明风险并等待确认。本轮未出现 HIGH 或 CRITICAL 风险。
- [x] 2.4 确认实现落点不在 `backend/packages/harness/deerflow/**` 受保护源码包。

## 3. 测试先行

- [x] 3.1 增加项目创建流程测试：缺少投手时只追问投手，不调用 MCP。
- [x] 3.2 增加 payload 映射测试：投手只用于流程态和命名，不进入 `localProjectCreate` payload。
- [x] 3.3 增加默认定向测试：性别不限、年龄 18-55、过滤公司账户、过滤时间 3 个月等可映射字段按规则生成。
- [x] 3.4 增加未声明字段测试：`智能定向拓展`、`搜索出价系数` 等当前未声明字段不得进入 MCP payload。
- [x] 3.5 增加出价方式测试：线下到店默认 `SMART`，获取线索默认 `MAX_CONVERSION`，显式值保留给原生业务工具校验。
- [x] 3.6 增加获取线索测试：`external_action`、`local_asset_type`、`tool_pack_id`、`market_page_ids`、`consult_aweme_uid` 按条件生成结构化追问或 payload。
- [x] 3.7 增加素材安全测试：未授权视频路径或 URL 不触发上传，且只追问当前素材参数。
- [x] 3.8 增加视频候选测试：素材库候选以 `choice_cards` 返回并保留 `value`、`label`、`metadata` 和顺序。
- [x] 3.9 增加视频数量测试：团购成交要求 10 条，其它目标要求 3 到 5 条。
- [x] 3.10 增加单元名称测试：按 `yyyyMMdd`、地域、定向、年龄、投手姓名首字母大写生成默认名称。
- [x] 3.11 增加用户可见清洗测试：最终回复不展示内部 tool name、MCP tool name、payload JSON、trace 或平台请求日志 ID。

## 4. 实现

- [x] 4.1 在根目录 `tools/`、Gateway 接入层或其它项目扩展点实现创建项目流程编排，不改受保护 DeerFlow 源码。
- [x] 4.2 复用 `oceanengine_local_project` 执行 `create-project` 参数校验、MCP 调用和后置确认。
- [x] 4.3 复用 `oceanengine_local_material` 执行视频上传和素材库视频查询；上传任务查询继续由素材原生工具能力承接。
- [x] 4.4 复用 `oceanengine_local_unit` 执行项目创建后的单元素材、标题、封面和投放卡片配置。
- [x] 4.5 为流程态定义投手、视频数量要求、品牌命名覆盖、AI 生成意图和已选候选，不把非官方字段透传到 MCP。
- [x] 4.6 保持一次只追问一个问题，并保留结构化补齐字段。

## 5. 验证

- [x] 5.1 运行新增或调整的项目管理单元测试。
- [x] 5.2 运行新增或调整的素材管理单元测试。
- [x] 5.3 运行新增或调整的单元管理单元测试。
- [x] 5.4 运行 Gateway 用户可见清洗和 `structured_clarifications` 回归测试。
- [x] 5.5 通过浏览器自然语言验收至少覆盖短视频/图文团购成交、线下到店、获取线索、线上互动和直播场景。
- [x] 5.6 浏览器验收记录必须包含真实 Agent、原生业务工具和 MCP 调用或本地拦截证据。
- [x] 5.7 运行 `openspec validate optimize-local-project-create-flow --strict`。
- [x] 5.8 Apply 完成后运行 `gitnexus_detect_changes()` 或等价 GitNexus 变更检测。

## 6. 归档准备

- [ ] 6.1 Archive 前把长期规则、坑点、边界和扩展约束沉淀到合适层级 `AGENTS.md`。
- [ ] 6.2 Archive 前等待用户明确批准。
- [ ] 6.3 Archive 完成后执行中文 git 提交。

## 验证记录

- `PYTHONPATH=. uv run --project backend python -m pytest backend/tests/test_oceanengine_local_project_create_flow.py backend/tests/test_oceanengine_local_material_native_tool.py backend/tests/test_oceanengine_local_unit_native_tool.py -q`：39 passed。
- `PYTHONPATH=backend:. uv run --project backend python -m pytest backend/tests/test_gateway_visibility.py -q`：20 passed。
- `PYTHONPATH=. uv run --project backend python -m pytest backend/tests/test_oceanengine_single_question_clarification.py backend/tests/test_oceanengine_dependent_clarification_options.py::test_material_missing_static_enum_uses_choice_cards_without_platform_data -q`：6 passed。
- `PYTHONPATH=. uv run --project backend ruff check tools/oceanengine_local_project_create_flow.py tools/oceanengine_local_project.py tools/oceanengine_local_material.py backend/tests/test_oceanengine_local_project_create_flow.py backend/tests/test_oceanengine_local_material_native_tool.py backend/tests/test_oceanengine_single_question_clarification.py backend/tests/test_oceanengine_dependent_clarification_options.py`：All checks passed。
- `git diff --check`：通过，无空白错误。
- `openspec validate optimize-local-project-create-flow --strict`：valid。
- `gitnexus_detect_changes(scope=all)`：risk_level=low；GitNexus 报告 changed_count=3、affected_count=0。
- 浏览器自然语言验收使用 `http://localhost:3002`、`http://127.0.0.1:8002`、`http://127.0.0.1:2025` 和本地 `nacos-mcp-router`。已登录账号 `13800138000`，使用本地推账号 `1854708763953159`。
- 浏览器验收覆盖：短视频/图文 + 团购成交、短视频/图文 + 线下到店、短视频/图文 + 获取线索、短视频/图文 + 线上互动、直播间 + 团购成交；页面和日志显示真实 Agent 调用 `oceanengine_local_project_create_flow`，并在流程内调用 `oceanengine_local_material` / `localFileVideoGet` 查询素材库。
- 浏览器最终阻断符合当前测试环境：素材库无可选视频时要求补充视频素材；未再追加地域编码追问，最终页面未再展示 `user_visible_text` 等内部字段。
