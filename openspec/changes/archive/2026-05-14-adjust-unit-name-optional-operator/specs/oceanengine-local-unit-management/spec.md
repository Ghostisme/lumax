## MODIFIED Requirements

### Requirement: 创建项目后单元名称必须按业务默认生成

当创建项目流程需要继续创建或配置单元时，`oceanengine-local-unit` SHALL 支持使用业务默认规则生成单元名称。默认名称 SHALL 使用执行日期、地域、定向类型和年龄组成；当流程态包含非空投手姓名时，默认名称 SHALL 在末尾追加投手姓名首字母大写。默认项目名和默认单元名 SHALL 使用同一套命名规则，且在用户未显式覆盖时保持一致。品牌另有要求时才由用户明确覆盖。

#### Scenario: 生成包含投手后缀的默认单元名称

- **GIVEN** 创建项目流程已收集到项目创建所需业务信息
- **AND** 流程态包含地域、定向类型、年龄和非空投手姓名
- **AND** 用户没有提供品牌自定义单元名称规则
- **WHEN** 系统生成单元名称
- **THEN** 单元名称 SHALL 使用 `yyyyMMdd` + 地域 + 定向类型 + 年龄 + 投手姓名首字母大写
- **AND** 系统 SHALL NOT 把投手姓名作为自造字段写入 `localProjectCreate` payload

#### Scenario: 拿不到投手姓名时省略投手后缀

- **GIVEN** 创建项目流程需要生成默认单元名称
- **AND** 流程态包含地域、定向类型和年龄
- **AND** 系统拿不到非空投手姓名
- **AND** 用户没有提供品牌自定义单元名称规则
- **WHEN** 系统生成单元名称
- **THEN** 单元名称 SHALL 使用 `yyyyMMdd` + 地域 + 定向类型 + 年龄
- **AND** 单元名称 SHALL NOT 追加 `X`、`--`、`未知`、`None`、`null` 或其它投手占位符
- **AND** 系统 SHALL NOT 把缺失投手姓名写入 `localProjectCreate` payload

#### Scenario: 未提供单元名称时默认复用项目名

- **GIVEN** 创建项目流程已生成项目名
- **AND** 用户没有显式提供品牌自定义单元名称规则
- **WHEN** 系统生成单元名称
- **THEN** 单元名称 SHALL 默认复用项目名
- **AND** 单元名称 SHALL NOT 再按另一套规则生成不同名称
- **AND** 如果项目名是默认生成的名称，项目名和单元名 SHALL 完全一致

#### Scenario: 品牌自定义名称覆盖默认规则

- **GIVEN** 用户明确提供品牌自定义单元名称
- **WHEN** 系统生成单元名称
- **THEN** 系统 SHALL 使用用户提供的名称
- **AND** 系统 SHALL NOT 再追加执行日期、地域、定向类型、年龄或投手首字母后缀
