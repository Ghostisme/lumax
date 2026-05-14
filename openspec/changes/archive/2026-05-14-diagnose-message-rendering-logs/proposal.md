# 对话回显链路诊断与临时恢复

## 背景

当前现象是对话后 `lumax_conversation_message` 有记录，但前端聊天页面没有回显。该表是 Lumax 用量结算和审计明细，不是前端聊天列表的直接数据源。前端聊天回显主要依赖 LangGraph 流式事件和 thread state/checkpoint 中的 `values.messages`。

因此本次不把 `lumax_conversation_message` 作为问题根因处理，也不修改表结构、结算逻辑或消息持久化语义。前序诊断日志已用于定位消息在“提交、流式返回、checkpoint 状态读取、前端状态合并、渲染前消息列表”中的断点；按用户要求，本 change 不再保留新增诊断日志代码，只保留已确认根因对应的临时回显恢复措施。

## 目标

- 删除前序添加的后端 run、SSE、thread state 诊断日志和仅为日志服务的辅助函数。
- 删除前序添加的前端 `useThreadStream` 开发期 console 诊断日志和仅为日志服务的辅助函数。
- 临时跳过普通 assistant 正文的内部内容正则隐藏判断，避免正常回答中出现“技能”等词时被清空并标记 `hide_from_ui`。
- 保留 summary、内部 tool call、structured clarification、reasoning_content 等现有用户可见清洗规则。
- 删除日志不改变对话执行、结算、权限、前端展示逻辑。

## 非目标

- 不读取或改造 `lumax_conversation_message` 作为前端回显数据源。
- 不新增数据库字段、迁移或后台补偿任务。
- 不修改 DeerFlow 受保护源码包中的业务逻辑，除非后续明确批准且符合 OpenSpec apply 要求。
- 不把诊断日志作为长期观测能力保留。
- 不在用户可见界面展示诊断信息。
- 不删除用户可见清洗框架，不放开 tool call、structured clarification、summary、reasoning_content 等内部信息隐藏逻辑。

## 方案概述

后端删除前序在 Gateway 接入层添加的结构化诊断日志：

- `app.gateway.services.start_run`：删除 run 创建后的诊断 `logger.info` 和仅用于日志的请求 stream mode 变量。
- `app.gateway.services.sse_consumer`：删除事件计数、断开状态跟踪和诊断日志，恢复只负责 SSE 输出、heartbeat、end 和关闭清理。
- `app.gateway.routers.threads`：删除 thread state/history 读取处的 checkpoint 消息数量和角色分布诊断日志，以及对应辅助函数。

前端删除 `frontend/src/core/threads/hooks.ts` 中的开发期诊断日志：

- 删除 `[thread-stream]` console 日志开关、角色计数和统一日志函数。
- 删除提交、完成、失败、server messages 数量变化、乐观消息清理等日志调用。
- 保持 `useThreadStream` 的提交、乐观消息和状态合并行为不变。

临时恢复回显时，在 `app.gateway.visibility` 中仅停用 `_INTERNAL_ASSISTANT_CONTENT_RE` 对普通 assistant 正文的整条隐藏处理。保留其它隐藏条件：

- summary 消息继续隐藏。
- 内部 OceanEngine tool call / read_file tool call 继续隐藏。
- structured clarification tool message 继续转换为结构化澄清并隐藏原始 tool message。
- reasoning_content 中命中内部 reasoning 模式时继续移除该字段。

该临时措施用于快速验证和恢复前端回显，后续应以更精确的内部内容识别规则替换，而不是长期依赖全局跳过正文正则。

## 风险与约束

- 该仓库要求修改长期资产前先走 OpenSpec；本 change 覆盖删除前序诊断日志和保留临时回显恢复。
- GitNexus MCP 工具当前未在可用 MCP 工具列表中暴露，无法执行 `gitnexus_impact`。实施前会用静态调用点和定向测试说明影响范围。
- 删除日志后会降低临时观测信息；后续若需要长期可观测性，应重新设计带开关、脱敏和测试约束的正式日志方案。
