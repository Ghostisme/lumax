# 默认使用线程 ID 作为 Langfuse Session 分组键

## 背景

当前项目已经接入 Langfuse tracing，模型调用生成的 trace 确实可以上报到 Langfuse，但多数 trace 没有 `session_id`，导致在 Langfuse Sessions 视图中无法按会话线程聚合查看。

现有实现存在两层问题：

- 主聊天 run 链路只有在显式提供 `metadata.langfuse_session_id` 时，才会把 session 信息传给 Langfuse。
- 一些独立的子模型调用链路会单独 `create_chat_model(...).ainvoke(...)`，但没有统一继承线程级 `langfuse_session_id`。

这会导致：

1. 主线程对话可能缺少默认 session 分组。
2. `title_agent`、`suggest_agent`、`memory_agent` 等子链路虽然有 trace，但 `session_id` 为空。
3. 同一线程的多类 trace 在 Langfuse 中无法统一聚合到一个 Session 下。

## 问题

对于 DeerFlow / Lumax 的对话运行链路，`thread_id` 已经是稳定的会话级标识，但当前系统没有把它一致地映射到所有模型调用的 Langfuse Session ID。

结果是：

1. 同一线程内的主对话 run 与子模型调用在 Langfuse 中缺少统一 session 分组。
2. 只有调用方显式传入 `metadata.langfuse_session_id` 时，部分链路的 Langfuse Session 才可能生效。
3. 从 Langfuse Sessions 视图排查问题时，会误以为“没有数据进 Langfuse”，实际是 trace 已上报但没有 session 归组。

## 目标

- 当调用方未显式提供 `metadata.langfuse_session_id` 时，默认使用当前 `thread_id` 作为 Langfuse Session ID。
- 当调用方已经显式提供 `metadata.langfuse_session_id` 时，保留显式值，不做覆盖。
- 让主聊天 run 与独立子模型调用都能继承同一线程级 `langfuse_session_id`。
- 覆盖已确认的独立链路，包括 `title_agent`、`suggest_agent`、`memory_agent`。
- 增加定向测试覆盖默认值、显式覆盖、以及子链路配置继承行为。

## 非目标

- 不修改前端登录 session 结构。
- 不把浏览器登录态 session、access token 或 refresh token 映射到 Langfuse Session。
- 不调整 Langfuse trace、user、tenant 或其他 metadata 字段语义。
- 不重构 tracing factory、模型创建流程或其他 observability provider 的接入方式。

## 方案概述

为线程级 Langfuse session 注入提供统一配置入口，并在所有直接模型调用链路中复用：

- 若请求 metadata 中已经存在有效的 `langfuse_session_id`，则直接沿用。
- 若请求 metadata 中不存在该字段，则写入当前 `thread_id`。
- 对主聊天 run，继续在 Gateway run config 组装阶段注入该默认值。
- 对独立子模型调用，统一从父级 RunnableConfig / 线程上下文继承并补齐 `langfuse_session_id`，避免 `title_agent`、`suggest_agent`、`memory_agent` 等链路丢失 session。

这样 Langfuse Python / LangChain 集成在处理根 callback run 时，就能稳定从 metadata 解析出 `session_id`，并把同一线程的多类 trace 聚合到同一个 Session 下。
