# 修正项目管理 MCP endpoint 解析链路

## 背景

当前 OceanEngine 本地推单元管理和素材管理规格已经要求：原生业务工具调用 `platform-agent-biz` MCP tool 前，必须以 Nacos 注册信息或 DeerFlow 已加载的 Nacos MCP server 配置为权威来源解析真实 MCP endpoint，不能把 `http://127.0.0.1:18000/mcp/` 作为默认业务兜底端点。

项目管理能力复用同一业务边界，但现有 `oceanengine-local-project-template-migration` 规格尚未写入同等约束。同时，`skills/custom/oceanengine-local-project/SKILL.md` 和 `skills/custom/oceanengine-local-project/scripts/common/mcp_client.py` 仍保留历史说明和脚本默认值：在部分脚本执行环境中会默认直连 `http://127.0.0.1:18000/mcp/` 的 Nacos MCP Router。

这会造成规格和实现边界不一致：运行时主路径已经存在共享的 `tools/oceanengine_local_project_runtime/mcp_client.py`，可以通过 Nacos 解析 `platform-agent-biz` 的真实 endpoint；但项目管理 skill 的历史脚本路径仍可能让维护者误以为固定本机 Router 是可接受的业务兜底。

## 目标

- 为 `oceanengine-local-project` 补齐 MCP 调用必须通过 Nacos 解析真实服务端点的规格要求。
- 使项目管理、单元管理、素材管理三类 OceanEngine 原生业务工具在 MCP endpoint 权威来源上保持一致。
- Apply 阶段移除项目管理 skill 脚本文档和脚本实现中对 `http://127.0.0.1:18000/mcp/` 的默认业务兜底依赖。
- 保持项目管理现有参数校验、payload 映射、受管理 MCP guard、后置确认和用户可见清洗语义不变。

## 非目标

- 不修改巨量官方接口参数、枚举、响应字段或项目管理 capability 范围。
- 不新增 curl、SDK、开放平台 HTTP API 或 mock 作为替代调用链路。
- 不绕过 `oceanengine_local_project` 原生业务工具。
- 不修改 `oceanengine-local-unit` 或 `oceanengine-local-material` 已有规格和主运行时逻辑。
- 不改变 Nacos 服务注册、Java 服务启动或 MCP Router sidecar 的全局机制。

## 方案概述

1. 在 `oceanengine-local-project-template-migration` 规格中新增项目管理 MCP endpoint 解析要求，语义对齐单元管理和素材管理。
2. Apply 阶段检查项目管理脚本入口，确保真实 MCP 调用优先复用 `tools/oceanengine_local_project_runtime.mcp_client` 的 Nacos 解析逻辑。
3. 对仍需保留的本地开发脚本路径，删除固定本机 Router 默认兜底；缺少 Nacos 配置、目标 MCP server、目标 endpoint 或目标 tool 时返回中文失败诊断。
4. 增加定向测试覆盖：项目管理脚本无法加载 DeerFlow MCP tools 时，应通过 Nacos 解析真实 endpoint，而不是请求 `127.0.0.1:18000`。

## 影响范围

- `openspec/specs/oceanengine-local-project-template-migration/spec.md`：归档后补齐项目管理 MCP endpoint 解析要求。
- `skills/custom/oceanengine-local-project/SKILL.md`：Apply 阶段修正文档中关于脚本默认直连本机 Router 的说明。
- `skills/custom/oceanengine-local-project/scripts/common/mcp_client.py`：Apply 阶段移除固定本机 Router 默认业务兜底，或改为复用共享 Nacos endpoint 解析运行时。
- `skills/custom/oceanengine-local-project/scripts/tests/` 或 `backend/tests/`：按实际落点增加或调整项目管理 MCP endpoint 解析测试。

## 风险与约束

- 项目管理脚本路径可能仍被本地开发或回归测试使用，移除本机 Router 默认值后，缺少 Nacos 配置的环境会从“尝试固定本机 Router”变成“明确失败诊断”。
- 如果脚本目录与共享 `tools/` 运行时存在导入路径差异，Apply 阶段需要保持最小改动，并确保在项目根目录和 `backend/` 目录运行都能得到一致结果。
- 修改代码前必须按 GitNexus 规则对目标函数或符号做影响分析；若 GitNexus 工具不可用，需要记录约束并用静态调用关系补充影响说明。
- Apply / 实现阶段涉及设计、代码、测试或行为变更时，必须显式使用合适的 Superpowers 技能。
