## ADDED Requirements

### Requirement: 创建项目流程默认项目名必须与单元名保持一致

创建项目流程在用户未显式提供项目名时，系统 SHALL 使用与默认单元名相同的业务规则生成项目名。默认项目名 SHALL 使用执行日期、地域、定向类型和年龄组成；当流程态包含非空投手姓名时，默认项目名 SHALL 在末尾追加投手姓名首字母大写。项目名和单元名在无显式覆盖时 SHALL 默认一致。

#### Scenario: 未提供项目名和单元名时生成一致名称

- **GIVEN** 用户请求创建本地推项目
- **AND** 流程态包含地域、定向类型和年龄
- **AND** 用户没有显式提供 `name`
- **AND** 用户没有显式提供 `unit_name`
- **WHEN** 系统生成 `create-project` payload 和后续单元计划
- **THEN** `project_payload.name` SHALL 使用 `yyyyMMdd` + 地域 + 定向类型 + 年龄 + 可选投手姓名首字母大写
- **AND** `unit_plan.name` SHALL 与 `project_payload.name` 完全一致
- **AND** 系统 SHALL NOT 追加 `X`、`--`、`未知`、`None`、`null` 或其它投手占位符

#### Scenario: 只提供项目名时单元名默认复用项目名

- **GIVEN** 用户请求创建本地推项目
- **AND** 用户显式提供 `name`
- **AND** 用户没有显式提供 `unit_name`
- **WHEN** 系统生成 `create-project` payload 和后续单元计划
- **THEN** `project_payload.name` SHALL 使用用户提供的 `name`
- **AND** `unit_plan.name` SHALL 默认复用同一个 `name`
- **AND** 系统 SHALL NOT 再按默认规则生成不同的单元名

#### Scenario: 项目名和单元名都显式提供时分别保留

- **GIVEN** 用户请求创建本地推项目
- **AND** 用户显式提供 `name`
- **AND** 用户显式提供 `unit_name`
- **WHEN** 系统生成 `create-project` payload 和后续单元计划
- **THEN** `project_payload.name` SHALL 使用用户提供的 `name`
- **AND** `unit_plan.name` SHALL 使用用户提供的 `unit_name`
- **AND** 系统 SHALL NOT 用默认命名覆盖任一显式名称
