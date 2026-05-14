## ADDED Requirements

### Requirement: 项目管理创建项目必须本地校验出价方式适用场景

`oceanengine_local_project` 在执行 `create-project` 时，SHALL 在调用 `platform-agent-biz` MCP tool 前校验 `bid_type` 是否被当前业务场景支持。对于可由本地规则确定不支持的出价方式，系统 SHALL 返回中文参数校验失败结果，并 SHALL NOT 调用 MCP 或等待平台返回 `code=40000`。

#### Scenario: 展示量优化目标只允许手动出价

- **GIVEN** 用户请求创建本地推项目
- **AND** 参数中 `external_action` 为 `SHOW`
- **WHEN** `bid_type` 不是 `MANUAL`
- **THEN** `oceanengine_local_project` SHALL 返回中文参数校验失败
- **AND** 错误 SHALL 说明当前展示量优化目标仅支持 `MANUAL`
- **AND** 系统 SHALL NOT 调用 `localProjectCreate` MCP tool

#### Scenario: 直播交易场景只允许智能出价

- **GIVEN** 用户请求创建本地推项目
- **AND** 参数中 `marketing_goal` 为 `LIVE`
- **AND** 参数中 `local_delivery_scene` 为 `CONTENT_HEAT` 或 `PRODUCT_PAY`
- **WHEN** `bid_type` 不是 `SMART`
- **THEN** `oceanengine_local_project` SHALL 返回中文参数校验失败
- **AND** 错误 SHALL 说明当前直播交易场景仅支持 `SMART`
- **AND** 系统 SHALL NOT 调用 `localProjectCreate` MCP tool

#### Scenario: 非 UBL 留资场景只允许稳定成本或最大转化

- **GIVEN** 用户请求创建本地推项目
- **AND** 参数中 `local_delivery_scene` 为 `EXTERNAL`
- **AND** 当前组合不属于 UBL 相关链路
- **WHEN** `bid_type` 不是 `STABILIZE_COSTS` 或 `MAX_CONVERSION`
- **THEN** `oceanengine_local_project` SHALL 返回中文参数校验失败
- **AND** 错误 SHALL 说明当前非 UBL 留资场景仅支持 `STABILIZE_COSTS` 或 `MAX_CONVERSION`
- **AND** 系统 SHALL NOT 调用 `localProjectCreate` MCP tool

#### Scenario: 合法出价方式组合继续进入正常链路

- **GIVEN** 用户请求创建本地推项目
- **AND** 参数中的 `bid_type` 被当前 `marketing_goal`、`local_delivery_scene` 和 UBL 相关组合支持
- **WHEN** 其它本地参数校验也通过
- **THEN** `oceanengine_local_project` SHALL 继续按现有 payload 映射构造 `localProjectCreate` 请求
- **AND** 系统 SHALL 保持现有 MCP endpoint 解析、MCP 调用、后置确认和用户可见清洗逻辑不变
