# 任务清单

## 1. 测试

- [x] 为 run config 组装链路增加测试：未传 `langfuse_session_id` 时，默认注入当前 `thread_id`。
- [x] 为 run config 组装链路增加测试：已显式传入 `langfuse_session_id` 时，保留显式值。
- [x] 为 Langfuse run context 增加测试：当 metadata 中存在 session id 时，运行边界上下文可正常建立。
- [x] 为统一配置工具增加测试：能从父级 config / 线程上下文继承并补齐 `langfuse_session_id`。
- [x] 为 `title_agent`、`suggest_agent`、`memory_agent` 增加定向测试：独立模型调用会继承线程级 `langfuse_session_id`。

## 2. 实现

- [x] 在 Gateway run config 组装逻辑中补充 `langfuse_session_id` 默认值注入。
- [x] 抽取统一的 RunnableConfig / metadata 补齐逻辑，供独立模型调用链路复用。
- [x] 保持显式传入的 `langfuse_session_id` 优先，不覆盖调用方指定值。
- [x] 将统一配置工具接入 `title_agent`、`suggest_agent`、`memory_agent` 的模型调用链路。
- [x] 如有必要，补充最小注释，使线程级 Langfuse session 继承语义清晰可维护。

## 3. 验证

- [x] 运行后端定向测试，覆盖主 run config 与子链路 Langfuse session 继承相关用例。
- [x] 如定向测试暴露兼容性问题，补充必要的最小修正并重新验证。
- [x] 通过 Langfuse API 或 UI 验证：同一线程的主 run 与 `title/suggest/memory` trace 能归并到同一 Session。
