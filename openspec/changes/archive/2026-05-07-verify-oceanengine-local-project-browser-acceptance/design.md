# 设计说明

## 当前能力面

官方“项目管理模块”目录 `doc_id=1807977111009572` 当前包含 16 个子接口。本地 `skills/custom/oceanengine-local-project/references/index.md` 与 `rules/index.json` 已对齐这些接口：

| 接口 | capability | 类型 | MCP tool |
| --- | --- | --- | --- |
| 创建项目 | `create-project` | 增改 | `localProjectCreate` |
| 更新项目 | `update-project` | 增改 | `localProjectUpdate` |
| 获取项目列表 | `list-projects` | 读取 | `localProjectList` |
| 获取项目详情 | `get-project-detail` | 读取 | `localProjectDetail` |
| 批量更新项目状态 | `batch-update-project-status` | 批量变更 | `localProjectStatusBatchUpdate` |
| 获取可投门店列表 | `list-promotable-pois` | 读取 | `localPoiGet` |
| 获取可投商品列表 | `list-promotable-products` | 读取 | `localProductGet` |
| 获取本地推创编可用抖音号 | `list-authorized-awemes` | 读取 | `localAwemeAuthorizedGet` |
| 查询本地推创编可用人群包 | `list-custom-audiences` | 读取 | `localCustomAudienceGet` |
| 根据多门店ID拉取门店ID | `get-poi-ids-by-multi-poi-id` | 读取 | `localMultiPoiIdPoiIdsGet` |
| 获取可用留资组件列表 | `list-tool-packs` | 读取 | `localToolPackListGet` |
| 获取可用留资组件详情 | `get-tool-pack-detail` | 读取 | `localToolPackDetailGet` |
| 获取可用营销页列表 | `list-market-pages` | 读取 | `localMarketPageListGet` |
| 查询营销页详情 | `get-market-page-detail` | 读取 | `localMarketPageGet` |
| 获取私信接待抖音号 | `list-consult-awemes` | 读取 | `localImAccountGet` |
| 列表批量更新项目投放时段 | `batch-update-project-week-schedule` | 批量变更 | `localProjectWeekScheduleBatchUpdate` |

主验收必须通过浏览器中的 DeerFlow 对话页面提交自然语言请求。直接 Python dry-run、curl、HTTP API、SDK 或 MCP 直连只能作为根因定位和辅助证据，不能替代浏览器验收。

## 方案选择

### 方案 A：按接口建立边界维度矩阵

为 16 个接口逐个建立覆盖维度矩阵，不预设固定用例数量。每个接口先列出需要覆盖的字段、枚举、条件依赖、数组限制、分页限制、金额/长度/时间边界、批量项定位、真实平台路径和输出展示，再根据执行结果持续补充用例，直到该接口已声明规则和可执行边界均有证据。

优点：

- 覆盖范围跟随接口真实复杂度，不会因为固定数量导致复杂接口覆盖不足或简单接口机械堆用例。
- 能证明自然语言路由、参数整理、本地 Pydantic 校验、MCP guard、真实 MCP 调用和中文展示都可用。
- 创建项目、更新项目、状态批量更新和投放时段批量更新可以组成测试数据链，减少环境依赖和脏数据扩散。

缺点：

- 执行成本高，需要前端、Gateway、agent runtime、MCP Router 和 `platform-agent-biz` Java 测试环境可用。
- 覆盖充分性需要逐字段核对，不能只靠用例数量判断。

### 方案 B：后端原生工具批量 dry-run 加少量浏览器抽样

通过 `oceanengine_local_project` 或 endpoint 测试覆盖规则和 payload，再在浏览器只抽样几个接口。

优点：

- 快速、稳定，便于定位参数校验和 payload 构造问题。

缺点：

- 不能证明全部接口都能被真实用户自然语言触发。
- 不能证明主 Agent 不会绕过业务工具直接调用受保护 MCP tool。
- 不满足用户“真实调用浏览器”和“每个接口创建测试用例”的要求。

推荐采用方案 A，并允许方案 B 作为失败定位的辅助检查。主交付证据必须来自浏览器对话、线程历史、trace、后端日志或 MCP 调用记录。

## 浏览器输入约束

测试人员在浏览器对话框提交的内容必须符合以下要求：

- 使用自然语言描述业务目的，例如“帮我用本地推账号 1854708763953159 查询最近创建的项目第一页，每页 20 条”。
- 可以包含真实业务参数，例如账号 ID、项目 ID、门店 ID、商品 ID、页码、每页数量、投放场景、营销目的、预算、出价、投放时段、时间范围和批量数组。
- 不得包含 `oceanengine-local-project`、`oceanengine_local_project`、`capability`、`payload_json`、`dry_run`、底层 MCP tool 名、Python 函数名或脚本路径。
- 不得要求“直接调用某工具”“使用某 skill”“用 MCP tool 名”“只校验不调用接口”等会降低路由难度或绕过真实接口的表达。
- 浏览器验收记录可以出现 `oceanengine_local_project`、capability 和 MCP tool 名，因为这些用于证明真实调用路径；限制只作用于浏览器输入内容。

## 覆盖规则

- 不为单个接口指定固定测试用例数量；覆盖充分性由该接口的字段、枚举、条件规则、数组/分页/金额/长度/时间边界和真实业务路径是否有证据决定。
- 每个接口都必须覆盖正向真实调用、缺普通必填、类型错误、非法枚举、边界值、输出展示和失败恢复；若该接口没有某类规则，应在验收记录中注明“不适用”的证据来源。
- 存在条件必填、条件禁止、互斥、至少一个、批量项递归或后置确认的接口，必须覆盖这些规则的触发和未触发路径。
- 读取类接口的正向成功标准是：真实调用对应 MCP tool，返回平台成功响应或空列表成功响应，并以中文展示结果摘要。
- 增改类和批量变更类接口的正向成功标准是：真实调用对应 MCP tool，并通过后置查询或平台响应确认目标对象、状态或投放时段符合预期。
- 平台业务错误、环境失败、校验失败与正向成功分开记录；本地校验失败不计入正向成功。
- 测试次数不设固定上限。发现问题后，修复影响面内的用例组应清零并重测。

## 测试数据策略

- 固定本地推账号：`1854708763953159`。
- 创建类用例使用名称前缀 `Codex浏览器验收` 加日期、接口名和随机短后缀，避免与既有业务项目混淆。
- 后续更新、详情、状态批量更新和投放时段批量更新优先复用本轮创建的测试项目 ID。
- 读取类依赖数据按链路逐步获得：先查门店、商品、抖音号、人群包、留资组件、营销页、私信接待抖音号，再把返回 ID 用于详情或依赖型查询。
- 若测试环境缺少某类数据，先记录真实接口返回，再通过允许造数据的方式补齐前置数据；不得凭空编造已成功的接口结果。

## 逐接口覆盖矩阵

每条实际执行的用例都应在验收记录中单独登记状态。只有该条浏览器输入已提交、线程或 trace 证据已记录、真实工具调用证据已确认、用户可见结果已确认后，才能把对应任务标记为完成。

| capability | 正向真实路径覆盖 | 边界与负向覆盖重点 | 依赖与后置证据 |
| --- | --- | --- | --- |
| `create-project` | 覆盖短视频/图文、直播、线索获取、推门店、推商品、全部门店、指定门店、预算和出价组合 | 缺 `name`、`marketing_goal`、`local_delivery_scene`、`ad_type`、`budget`、`bid_type`；`delivery_goal` 条件必填；`promotion_poi_ids` 条件必填；`product_id` 条件必填；`aweme_id` 条件必填；`external_action` 条件必填；`audience` 下 `REGION`、`LOCAL`、`POI` 分支；`name` 长度；`budget`、`high_budget_rate`、`daily_delivery_seconds`、`market_page_ids` 数量边界；非法枚举 | 返回项目 ID 后进入 `get-project-detail`、`list-projects`、状态更新和投放时段更新；失败时区分本地校验、平台业务限制和代码 bug |
| `update-project` | 覆盖名称、预算、出价、固定时长、日期范围、投放时段、高峰日预算、地域定向、营销页、私信接待抖音号更新 | 缺 `project_id`；`schedule_type=FIXED_TIME` 时 `schedule_fixed_seconds` 条件必填；`FIXED_TIME` 与 `schedule_time` 条件禁止；`is_set_peak_budget=true` 时 `high_budget_rate` 和 `peak_week_days`/`peak_holidays` 规则；`name` 长度；`budget`、`high_budget_rate`、`schedule_time` 长度边界；非法枚举 | 通过详情或列表确认更新结果；受状态限制的项目要记录平台业务失败 |
| `list-projects` | 覆盖空筛选、项目 ID、项目状态、门店 ID、商品 ID、营销目的、营销场景、单元类型、名称、创建/更新时间、出价方式、投放类型和分页 | 缺 `local_account_id`；筛选字段类型错误；非法状态、营销目的、营销场景、单元类型、出价方式；页码和页大小边界；时间范围倒置或格式错误；数组项类型错误 | 使用本轮创建项目验证 `project_ids`、`project_name` 和时间筛选；空列表成功需中文说明 |
| `get-project-detail` | 覆盖本轮创建项目、更新后项目、状态变更后项目、投放时段变更后项目、合法但不存在项目 | 缺 `local_account_id`；缺 `project_id`；`project_id` 类型错误、负数、0、超大数 | 详情结果作为更新、状态和投放时段后置确认依据 |
| `batch-update-project-status` | 覆盖单项目暂停、单项目启用、多项目暂停、多项目启用、部分成功/失败组合 | 缺 `local_account_id`；缺 `data`；`data=[]`；批量项缺 `project_id` 或 `opt_status`；`opt_status` 非 `ENABLE`/`PAUSED`；项目 ID 类型错误；重复项目 ID；不存在项目 ID | 通过详情或列表确认状态；平台状态限制必须分层记录 |
| `list-promotable-pois` | 覆盖不同 `local_delivery_scene`、关键词、省份、城市、商品 ID、分页 | 缺 `local_account_id`；缺 `local_delivery_scene`；非法营销目的；`filtering` 类型错误；`province`/`city` 非数组；`product_id` 类型错误；页码和 `page_size` 边界 | 返回门店 ID 供创建、留资组件、营销页和私信接待抖音号用例复用 |
| `list-promotable-products` | 覆盖不同 `local_delivery_scene`、商品名称/ID 关键词、分页 | 缺 `local_account_id`；缺 `local_delivery_scene`；非法营销目的；`filtering` 类型错误；关键词类型错误；页码和 `page_size` 边界 | 返回商品 ID 供创建、留资组件、营销页和私信接待抖音号用例复用 |
| `list-authorized-awemes` | 覆盖 `marketing_goal=LIVE`、`VIDEO_IMAGE`、抖音号名称关键词、抖音号 ID 关键词、分页 | 缺 `local_account_id`；缺 `marketing_goal`；非法 `marketing_goal`；`filtering` 类型错误；`search_key_word` 类型错误；页码和 `page_size` 边界 | 返回 `aweme_id` 供直播创建项目和私信接待链路复用 |
| `list-custom-audiences` | 覆盖 `tags_type=CUSTOM`、`SYS_RECOMMEND`、不同页码和页大小 | 缺 `local_account_id`；缺 `tags_type`；非法 `tags_type`；`page` 类型错误；`page_size` 小于 1、等于 1000、超过 1000；页码边界 | 返回人群包 ID 可用于创建/更新项目的定向字段 |
| `get-poi-ids-by-multi-poi-id` | 覆盖单个、多项、`need_enable=true`、`need_enable=false`、数组上限内查询 | 缺 `local_account_id`；缺 `multi_poi_ids`；空数组；超过 50 个；数组项类型错误；`need_enable` 类型错误 | 返回门店 ID 可回流到门店相关项目创建和依赖型查询 |
| `list-tool-packs` | 覆盖 `delivery_goal=POI`、`PRODUCT`、`intelligent_selection_mode` 开/关、门店 ID、商品 ID、分页 | 缺 `local_account_id`；缺 `delivery_goal`；缺 `intelligent_selection_mode`；`POI` 缺 `poi_ids`；`PRODUCT` 缺 `product_ids`；非法枚举；`poi_ids`、`product_ids` 数量边界；分页边界 | 返回 `tool_pack_id` 供详情查询和线索项目创建复用 |
| `get-tool-pack-detail` | 覆盖来自列表的组件 ID、不同组件 ID、合法不存在组件 ID | 缺 `local_account_id`；缺 `tool_pack_id`；`tool_pack_id` 类型错误、负数、0、超大数 | 详情输出用于验证中文字段展示和线索组件可用性 |
| `list-market-pages` | 覆盖 `delivery_goal=POI`、`PRODUCT`、门店 ID、商品 ID、不同页码和页大小 | 缺 `local_account_id`；缺 `delivery_goal`；`POI` 缺 `poi_ids`；`PRODUCT` 缺 `product_ids`；非法 `delivery_goal`；`poi_ids`、`product_ids` 数量边界；`page_size` 超过 100 | 返回 `market_page_ids` 供详情查询和项目创建/更新复用 |
| `get-market-page-detail` | 覆盖单个营销页、多个营销页、门店来源营销页、商品来源营销页、合法不存在营销页 | 缺 `local_account_id`；缺 `market_page_ids`；空数组；数组项类型错误；负数、0、超大 ID；重复 ID | 详情输出用于验证中文字段展示和营销页可用性 |
| `list-consult-awemes` | 覆盖 `delivery_goal=POI`、`PRODUCT`、关键词、授权类型、门店 ID、商品 ID、分页 | 缺 `local_account_id`；缺 `delivery_goal`；`POI` 缺 `poi_ids`；`PRODUCT` 缺 `product_ids`；非法 `delivery_goal`；`filtering` 类型错误；`auth_type` 类型/枚举错误；`product_ids` 数量边界 | 返回私信接待抖音号供创建/更新项目复用 |
| `batch-update-project-week-schedule` | 覆盖单项目、多项目、`REALTIME`、`NEXT_DAY`、全天投放、工作日高峰、局部时段 | 缺 `local_account_id`；缺 `data`；空数组；批量项缺 `project_id` 或 `schedule_time`；`schedule_time` 非 336 位；`schedule_scene` 非法；项目 ID 类型错误；重复项目 ID；不存在项目 ID | 通过详情或列表确认投放时段；平台状态限制必须分层记录 |

## 执行与证据

Apply 阶段应建立验收记录，至少包含：

- 环境状态：前端 URL、Gateway、agent runtime、MCP Router、`platform-agent-biz`、业务工具注册状态和登录状态，不记录密码、Cookie、token 或本地存储值。
- 用例登记：capability、用例 ID 或自然语言摘要、覆盖维度、参数差异点、预期结果、是否计入正向真实调用。
- 执行记录：轮次、线程 ID 或 trace ID、业务工具调用证据、MCP tool 调用证据、平台响应或本地校验结果、用户可见中文结果、单条完成状态。
- 覆盖闭环：逐接口列出已覆盖字段、已覆盖枚举、已覆盖条件规则、已覆盖边界、未覆盖原因或待补充项。
- 测试数据链：创建出的测试项目 ID、后续更新/详情/状态/投放时段用例的复用关系和最终状态。
- 失败清零记录：失败摘要、根因层级、修复文件、重测起点、受影响用例组和重测结果。

## 修复与重测策略

如果浏览器验收发现问题，按以下顺序处理：

1. 先确认失败层级：前端发送、认证、Agent 路由、skill 导航、业务工具注册、本地校验、字段映射、MCP guard、MCP 服务、Java 服务、平台业务、结果展示或环境依赖。
2. 用最小辅助检查定位根因，例如日志、线程历史、trace、`/api/mcp/config`、原生工具 dry-run 或定向测试。
3. 只修复与本次验收直接相关的问题，不混入无关重构。
4. 修复前若要修改 function、class 或 method，先按仓库规则运行 GitNexus impact analysis。
5. 修复后重新运行相关后端定向 `pytest`、前端 `pnpm check` 或对应单元测试。
6. 回到浏览器重新执行受影响接口的用例组；受影响覆盖项重新计算。

## 验收完成标准

- 16 个项目管理接口都有浏览器自然语言用例记录。
- 每个接口均完成与自身规则匹配的正向真实调用、负向校验、边界条件、输出展示和失败恢复覆盖；不以固定用例数量作为完成标准。
- 所有浏览器输入均未点名 tool、skill、capability、MCP tool、脚本路径或 JSON tool payload。
- 正向用例均有真实 `oceanengine_local_project` 业务工具调用证据和对应 MCP tool 调用证据。
- 负向用例能证明本地校验在 MCP 前拦截，或平台业务错误被中文展示并分层记录。
- 创建、更新、状态批量更新、投放时段批量更新之间的测试数据链可追踪。
- 如出现问题，已完成修复、定向验证和浏览器重测记录。
