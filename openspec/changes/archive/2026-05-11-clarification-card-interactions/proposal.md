# 扩展 MCP 动态候选卡片契约

## 背景

OceanEngine 本地推原生业务工具已经能在参数补齐时返回 `data.clarification.input_control`。静态枚举会按 `rules/*.json` 生成 `choice_cards`，部分动态候选也会通过只读 MCP 查询生成 `choice_cards`，例如商品候选。

用户希望动态 MCP 查询出来的数据也沿用本地参数枚举的展示方式，以卡片候选表达，便于后续选择。当前约束是：本次提案阶段和后续实施均不得修改前端代码，因此本 change 只约束后端 / Gateway 输出契约与文本兜底，不新增或调整前端组件。

## 问题

如果动态 MCP 查询候选只进入普通文本，或只在后端内部结构中存在而没有通过用户可见出口稳定返回，会出现：

1. 动态候选与静态枚举的 `choice_cards` 契约不一致，前端无法按同一结构消费。
2. 候选项的 `value`、`label`、`description`、`metadata` 或分页信息可能在 Gateway 清洗时丢失。
3. 支持单选或多选的后端契约边界不清，容易把 `selection_mode` 写死为某个字段或某个 capability。
4. 在不改前端的前提下，如果缺少 `data.user_visible_text` 兜底，用户仍可能看不到可读候选。
5. 候选查询失败、为空或前置参数不足时，系统可能误生成空卡片或臆造候选。

## 目标

- 动态 MCP 候选 SHALL 使用与静态枚举一致的 `data.clarification.input_control.type=choice_cards` 契约。
- 动态候选 SHALL 保留后续补齐所需的 `value`、用户可读的 `label`，并在安全时保留 `description`、`metadata`、`page_info`。
- `selection_mode` SHALL 支持 `single` 或 `multiple`，由具体补齐字段和业务语义决定，不得由前端推断。
- Gateway / 用户可见出口 SHALL 保留结构化澄清数据，并隐藏内部 tool name、MCP tool name、payload JSON、trace 和平台请求日志 ID。
- 在不修改前端代码的前提下，后端 SHALL 同步提供可读的 `data.user_visible_text` 兜底，展示候选项并提示用户如何回复。
- 候选查询失败、为空或前置参数不足时 SHALL 不生成虚假 `choice_cards.options`。
- 验收 SHALL 使用真实浏览器和真实用户自然语言输入，不得通过指定工具名、`capability`、`payload_json`、底层 MCP tool 名或脚本直连等方式绕过 Agent 流程。

## 非目标

- 不修改 `frontend/**` 下任何代码、样式、测试或生成文件。
- 不改造后端 SSE 协议或 LangGraph thread submit 协议。
- 不引入新的全局状态系统或持久化存储。
- 不把平台实时动态候选写入 `rules/*.json` 静态枚举。
- 不绕过 OceanEngine 原生业务工具改用主 Agent 直连 MCP Router、HTTP API、curl 或 SDK。
- 不把本地日志、Langfuse 日志、curl、脚本或 MCP 直连结果作为最终浏览器验收的替代。

## 方案概述

复用现有 `structured-parameter-clarification` 契约，把动态 MCP 查询候选明确纳入 `choice_cards` 输出。后端生成候选时先完成本地参数校验；只有当前缺参适合动态候选且前置参数足够时，才发起只读 MCP 查询。查询结果清洗为候选卡片结构，保留安全字段和原始顺序，不臆造、不重排、不合并。

Gateway 用户可见出口继续基于结构化契约提取 `data.clarification.input_control`，确保 `selection_mode`、`options`、`description`、`metadata` 和 `page_info` 可被客户端读取。与此同时，后端文本兜底必须能展示单选或多选候选，确保当前不改前端代码也能让用户理解并继续回复。

实施阶段应优先补齐后端单元测试和 Gateway 清洗测试；若发现现有前端无法展示 `selection_mode=multiple`，本 change 只记录为已知 UI 能力边界，不在本次修改前端。

验收阶段必须登录真实页面后使用自然语言触发本地推候选补齐流程，测试参数使用本地提账号 `1854708763953159`。如果浏览器验收失败或链路不清晰，应先结合本地 Gateway、backend、frontend 和 MCP 相关日志排查；仍无法定位时，可通过本轮 `sessionId` 查询 Langfuse 日志辅助诊断。问题排除后必须回到浏览器，用同样的真实用户方式重新测试并记录结果。
