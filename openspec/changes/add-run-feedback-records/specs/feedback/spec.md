# feedback Specification

## Purpose

定义 Run 级点赞点踩反馈记录的 SQL 表语义、自动创建行为、API 行为和统计口径。

## Requirements

### Requirement: SQL feedback 表必须支持未评价记录

SQL feedback 表 SHALL 能保存用户尚未点赞或点踩的 run 级反馈记录。

#### Scenario: Run 成功完成但用户未评价

- **GIVEN** 一个 run 以 `RunStatus.success` 完成
- **AND** 当前用户对该 `thread_id + run_id` 尚无 SQL feedback 记录
- **WHEN** run worker 完成收尾逻辑
- **THEN** 系统 SHALL 创建一条 SQL feedback 记录
- **AND** `rating` SHALL 为 `0`
- **AND** `result` SHALL 为 `NULL`
- **AND** `comment` SHALL 为 `NULL`
- **AND** `feedback_time` SHALL 为 `NULL`
- **AND** `message_id` SHALL 等于该 run 当前轮最终 assistant 消息的消息 ID

#### Scenario: Run 成功完成但无法找到最终 assistant 消息

- **GIVEN** 一个 run 以 `RunStatus.success` 完成
- **AND** 系统无法从最终 checkpoint 或当前轮消息中找到 assistant 消息 ID
- **WHEN** run worker 完成收尾逻辑
- **THEN** 系统 SHALL 继续创建未评价 SQL feedback 记录
- **AND** `message_id` SHALL 为 `NULL`
- **AND** 系统 SHALL NOT 因缺失 `message_id` 将成功 run 标记为失败

#### Scenario: 非成功 Run 不创建未评价记录

- **GIVEN** 一个 run 以 error、interrupted 或 rollback 结束
- **WHEN** run worker 完成收尾逻辑
- **THEN** 系统 SHALL NOT 自动创建未评价 feedback 记录

#### Scenario: 已有评价不被覆盖

- **GIVEN** 当前用户对 `thread_id + run_id` 已有 SQL feedback 记录
- **AND** 该记录已是点赞或点踩状态
- **WHEN** run worker 尝试创建未评价记录
- **THEN** 系统 SHALL 保留原记录
- **AND** 系统 SHALL NOT 覆盖 `rating`、`result`、`comment`、`feedback_time` 或 `message_id`

### Requirement: rating 字段必须保持整数兼容

SQL feedback 表的 `rating` 字段 SHALL 保持整数类型，并继续兼容既有点赞点踩语义。

#### Scenario: 点赞状态

- **GIVEN** 用户对一个 run 点赞
- **WHEN** 系统写入 SQL feedback 表
- **THEN** `rating` SHALL 为 `1`
- **AND** `result` SHALL 为 `positive`

#### Scenario: 点踩状态

- **GIVEN** 用户对一个 run 点踩
- **WHEN** 系统写入 SQL feedback 表
- **THEN** `rating` SHALL 为 `-1`
- **AND** `result` SHALL 为 `negative`

#### Scenario: 未评价状态

- **GIVEN** 用户尚未对一个成功 run 点赞或点踩
- **WHEN** 系统写入 SQL feedback 表
- **THEN** `rating` SHALL 为 `0`
- **AND** `result` SHALL 为 `NULL`

### Requirement: Run 级反馈接口必须更新同一条记录

Run 级点赞点踩接口 SHALL 按 `thread_id + run_id + user_id` 更新同一条 SQL feedback 记录。

#### Scenario: 使用 result 点赞

- **GIVEN** 当前用户可以访问目标 thread 和 run
- **WHEN** 调用 `PUT /api/threads/{thread_id}/runs/{run_id}/feedback` 且 body 包含 `result=positive`
- **THEN** 系统 SHALL upsert 当前用户的 SQL feedback 记录
- **AND** `rating` SHALL 为 `1`
- **AND** `result` SHALL 为 `positive`
- **AND** `feedback_time` SHALL 为当前时间

#### Scenario: 使用 result 点踩

- **GIVEN** 当前用户可以访问目标 thread 和 run
- **WHEN** 调用 `PUT /api/threads/{thread_id}/runs/{run_id}/feedback` 且 body 包含 `result=negative`
- **THEN** 系统 SHALL upsert 当前用户的 SQL feedback 记录
- **AND** `rating` SHALL 为 `-1`
- **AND** `result` SHALL 为 `negative`
- **AND** `feedback_time` SHALL 为当前时间

#### Scenario: 兼容 rating 入参

- **GIVEN** 当前用户可以访问目标 thread 和 run
- **WHEN** 调用 run 级 PUT 接口且 body 包含 `rating=1` 或 `rating=-1`
- **THEN** 系统 SHALL 接受该请求
- **AND** 系统 SHALL 同步写入对应的 `result`

#### Scenario: 取消评价

- **GIVEN** 当前用户可以访问目标 thread 和 run
- **WHEN** 调用 `DELETE /api/threads/{thread_id}/runs/{run_id}/feedback`
- **THEN** 系统 SHALL 将同一条 SQL feedback 记录重置为未评价
- **AND** `rating` SHALL 为 `0`
- **AND** `result` SHALL 为 `NULL`
- **AND** `feedback_time` SHALL 为 `NULL`
- **AND** 系统 SHALL NOT 物理删除该记录

### Requirement: 反馈记录必须包含 Agent 标识

SQL feedback 记录 SHALL 保存 run 对应的 agent 标识字段。

#### Scenario: 自定义 Agent

- **GIVEN** run 运行时 context 中包含 `agent_name`
- **WHEN** 系统创建或更新 SQL feedback 记录
- **THEN** `agent_name` SHALL 等于运行时 context 的 `agent_name`
- **AND** `agent_id` SHALL 等于该 run 的 `assistant_id`

#### Scenario: 默认 Agent

- **GIVEN** run 没有运行时 `agent_name`
- **WHEN** 系统创建 SQL feedback 记录
- **THEN** `agent_name` SHALL 为空字符串
- **AND** `agent_id` SHALL 为 `lead_agent`

### Requirement: 反馈统计必须只统计有效评价

反馈统计 SHALL 区分反馈记录数和有效点赞点踩数；未评价记录 SHALL NOT 计入 positive、negative 或有效反馈 total。

#### Scenario: 只有未评价记录

- **GIVEN** 一个 run 只有 `rating=0` 且 `result=NULL` 的 feedback 记录
- **WHEN** 系统聚合该 run 的反馈统计
- **THEN** `positive` SHALL 为 `0`
- **AND** `negative` SHALL 为 `0`
- **AND** 有效反馈 `total` SHALL 为 `0`

#### Scenario: 有点赞和点踩记录

- **GIVEN** 一个 run 存在点赞和点踩 feedback 记录
- **AND** 同时存在未评价 feedback 记录
- **WHEN** 系统聚合该 run 的反馈统计
- **THEN** `positive` SHALL 等于 `rating=1` 的记录数
- **AND** `negative` SHALL 等于 `rating=-1` 的记录数
- **AND** 有效反馈 `total` SHALL 等于 `positive + negative`

### Requirement: 消息列表必须回填新反馈字段

线程消息列表 SHALL 在最后一条 AI 消息上回填当前用户的 SQL feedback 状态。

#### Scenario: 最后一条 AI 消息存在反馈记录

- **GIVEN** 当前用户请求线程消息列表
- **AND** 某个 run 的最后一条 AI 消息存在 SQL feedback 记录
- **WHEN** 系统返回消息列表
- **THEN** 该消息的 `feedback` SHALL 包含 `feedback_id`
- **AND** 该消息的 `feedback` SHALL 包含 `rating`
- **AND** 该消息的 `feedback` SHALL 包含 `result`
- **AND** 该消息的 `feedback` SHALL 包含 `comment`
- **AND** 该消息的 `feedback` SHALL 包含 `feedback_time`
- **AND** 该消息的 `feedback` SHALL 包含 `agent_id`
- **AND** 该消息的 `feedback` SHALL 包含 `agent_name`
