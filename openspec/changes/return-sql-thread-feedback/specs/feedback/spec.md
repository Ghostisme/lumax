## MODIFIED Requirements

### Requirement: 线程反馈查询必须返回 SQL 当前态

`GET /api/threads/{thread_id}/feedback` SHALL 返回当前用户在目标线程下的 SQL run 级 feedback 当前态记录，而不是 LangGraph Store 中的 legacy message feedback 历史记录。

#### Scenario: 查询线程下当前用户的 SQL feedback

- **GIVEN** 当前用户可以访问目标 thread
- **AND** SQL `feedback` 表中存在该用户在该 `thread_id` 下的 run 级 feedback 记录
- **WHEN** 调用 `GET /api/threads/{thread_id}/feedback`
- **THEN** 系统 SHALL 查询 SQL feedback repository
- **AND** 响应 SHALL 包含 `feedback` 列表
- **AND** 响应 SHALL 包含 `count`
- **AND** `count` SHALL 等于返回的 SQL feedback 当前态记录数

#### Scenario: 返回 SQL feedback 字段

- **GIVEN** SQL feedback 当前态记录包含 run 级反馈字段
- **WHEN** 调用 `GET /api/threads/{thread_id}/feedback`
- **THEN** 每条反馈记录 SHALL 包含 `feedback_id`
- **AND** 每条反馈记录 SHALL 包含 `thread_id`
- **AND** 每条反馈记录 SHALL 包含 `run_id`
- **AND** 每条反馈记录 SHALL 包含 `user_id`
- **AND** 每条反馈记录 SHALL 包含 `message_id`
- **AND** 每条反馈记录 SHALL 包含 `rating`
- **AND** 每条反馈记录 SHALL 包含 `result`
- **AND** 每条反馈记录 SHALL 包含 `comment`
- **AND** 每条反馈记录 SHALL 包含 `feedback_time`
- **AND** 每条反馈记录 SHALL 包含 `agent_id`
- **AND** 每条反馈记录 SHALL 包含 `agent_name`
- **AND** 每条反馈记录 SHALL 包含 `created_at`

#### Scenario: 未评价占位记录也返回

- **GIVEN** SQL feedback 表中存在 `rating=0` 且 `result=NULL` 的未评价记录
- **WHEN** 调用 `GET /api/threads/{thread_id}/feedback`
- **THEN** 该未评价记录 SHALL 出现在响应 `feedback` 列表中
- **AND** 该记录的 `rating` SHALL 为 `0`
- **AND** 该记录的 `result` SHALL 为 `NULL`
- **AND** 该记录的 `feedback_time` SHALL 为 `NULL`

#### Scenario: Store 历史记录不影响查询结果

- **GIVEN** LangGraph Store 中存在同一 `thread_id` 的多条 legacy feedback 历史记录
- **AND** SQL feedback 表中只存在较少的当前态记录
- **WHEN** 调用 `GET /api/threads/{thread_id}/feedback`
- **THEN** 响应 SHALL 只基于 SQL feedback 当前态记录生成
- **AND** 响应 SHALL NOT 返回 Store 中仅作为历史记录存在的 legacy feedback

#### Scenario: SQL feedback repository 不可用

- **GIVEN** Gateway 未配置 SQL feedback repository
- **WHEN** 调用 `GET /api/threads/{thread_id}/feedback`
- **THEN** 系统 SHALL 返回服务不可用错误
- **AND** 系统 SHALL NOT 回退到 Store legacy feedback 查询
