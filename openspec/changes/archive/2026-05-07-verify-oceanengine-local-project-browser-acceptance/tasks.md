# 任务清单

## 1. 官方范围与矩阵准备

- [x] 1.1 通过官方 `label/tree/get`、`tree/get` 和 `node/get` 确认 `doc_id=1807977111009572` 当前 16 个子接口的 `doc_id`、标题和 path。
- [x] 1.2 对照 `skills/custom/oceanengine-local-project/references/index.md` 与 `rules/index.json`，确认 16 个 capability、规则文件和 MCP tool 映射一致。
- [x] 1.3 建立逐接口浏览器覆盖矩阵；不指定固定用例数量，而是为每个接口列出必须覆盖的字段、枚举、条件规则、数组、分页、金额、长度、时间、批量项、真实业务路径和输出展示边界。
- [x] 1.4 检查所有浏览器输入，确保不包含 `oceanengine-local-project`、`oceanengine_local_project`、`capability`、`payload_json`、`dry_run`、底层 MCP tool 名、脚本路径或“直接调用某工具”等提示。
- [x] 1.5 为每条实际执行用例标注参数差异点，确保账号、项目、门店、商品、分页、枚举、数组、时间、预算、投放时段和布尔开关尽量多样化。
- [x] 1.6 为创建、更新、状态批量更新和投放时段批量更新建立测试数据链，约定测试项目命名前缀、复用关系和最终状态记录方式。

## 2. 环境与工具链确认

- [x] 2.1 启动或确认 DeerFlow 前端、Gateway、agent runtime、MCP Router 和 `platform-agent-biz` 测试环境可用。
- [x] 2.2 在真实浏览器中完成本地会话和业务登录；登录密码、Cookie、token 和本地存储值不得写入验收记录。
- [x] 2.3 确认 `oceanengine_local_project` 已注册为可用原生业务工具，并记录只读证据。
- [x] 2.4 确认 `platform-agent-biz` MCP 配置可用，且 16 个项目管理 MCP tool 可被业务工具内部调用。
- [x] 2.5 建立验收记录文件，记录环境、用例、覆盖维度、执行轮次、trace、调用证据、用户可见结果和失败清零信息。

## 3. 浏览器自然语言验收

> 勾选规则：每个覆盖项必须在浏览器提交、记录线程或 trace 证据、确认业务工具和 MCP 调用证据、确认用户可见结果后，才能标记完成。不得按 capability 批量勾选。

### 3.1 `create-project`

- [x] 3.1.1 覆盖短视频/图文、直播、线索获取、推门店、推商品、全部门店、指定门店、预算和出价组合的真实创建路径。
- [x] 3.1.2 覆盖普通必填、条件必填、条件禁止、非法枚举、金额边界、长度边界、数组数量、`audience` 分支和平台业务失败分层。
- [x] 3.1.3 记录创建出的测试项目 ID、项目名称、平台响应和后续用例复用关系。

### 3.2 `update-project`

- [x] 3.2.1 覆盖名称、预算、出价、固定时长、日期范围、投放时段、高峰日预算、地域定向、营销页和私信接待抖音号更新路径。
- [x] 3.2.2 覆盖缺 `project_id`、`schedule_type` 条件规则、`is_set_peak_budget` 条件规则、金额边界、长度边界、非法枚举和平台业务失败分层。
- [x] 3.2.3 使用详情查询或平台响应确认更新结果，并记录失败后的重测起点。

### 3.3 `list-projects`

- [x] 3.3.1 覆盖空筛选、项目 ID、项目状态、门店 ID、商品 ID、营销目的、营销场景、单元类型、名称、创建/更新时间、出价方式、投放类型和分页查询。
- [x] 3.3.2 覆盖缺账号、筛选字段类型错误、非法枚举、数组项类型错误、分页边界、时间范围倒置或格式错误。

### 3.4 `get-project-detail`

- [x] 3.4.1 覆盖本轮创建项目、更新后项目、状态变更后项目、投放时段变更后项目和合法但不存在项目查询。
- [x] 3.4.2 覆盖缺账号、缺项目 ID、项目 ID 类型错误、负数、0、超大数和平台业务失败分层。

### 3.5 `batch-update-project-status`

- [x] 3.5.1 覆盖单项目暂停、单项目启用、多项目暂停、多项目启用、部分成功/失败组合。
- [x] 3.5.2 覆盖缺账号、缺 `data`、空数组、批量项缺字段、非法 `opt_status`、项目 ID 类型错误、重复项目 ID 和不存在项目 ID。
- [x] 3.5.3 用列表或详情查询确认状态变更结果。

### 3.6 `list-promotable-pois`

- [x] 3.6.1 覆盖不同 `local_delivery_scene`、关键词、省份、城市、商品 ID 和分页查询。
- [x] 3.6.2 覆盖缺账号、缺营销目的、非法营销目的、`filtering` 类型错误、省市字段类型错误、商品 ID 类型错误、页码和 `page_size` 边界。

### 3.7 `list-promotable-products`

- [x] 3.7.1 覆盖不同 `local_delivery_scene`、商品名称/ID 关键词和分页查询。
- [x] 3.7.2 覆盖缺账号、缺营销目的、非法营销目的、`filtering` 类型错误、关键词类型错误、页码和 `page_size` 边界。

### 3.8 `list-authorized-awemes`

- [x] 3.8.1 覆盖 `marketing_goal=LIVE`、`VIDEO_IMAGE`、抖音号名称关键词、抖音号 ID 关键词和分页查询。
- [x] 3.8.2 覆盖缺账号、缺 `marketing_goal`、非法 `marketing_goal`、`filtering` 类型错误、关键词类型错误、页码和 `page_size` 边界。

### 3.9 `list-custom-audiences`

- [x] 3.9.1 覆盖 `tags_type=CUSTOM`、`SYS_RECOMMEND`、不同页码和页大小查询。
- [x] 3.9.2 覆盖缺账号、缺 `tags_type`、非法 `tags_type`、`page` 类型错误、`page_size` 小于 1、等于 1000、超过 1000 和页码边界。

### 3.10 `get-poi-ids-by-multi-poi-id`

- [x] 3.10.1 覆盖单个、多项、`need_enable=true`、`need_enable=false` 和数组上限内查询。
- [x] 3.10.2 覆盖缺账号、缺 `multi_poi_ids`、空数组、超过 50 个、数组项类型错误和 `need_enable` 类型错误。

### 3.11 `list-tool-packs`

- [x] 3.11.1 覆盖 `delivery_goal=POI`、`PRODUCT`、`intelligent_selection_mode` 开/关、门店 ID、商品 ID 和分页查询。
- [x] 3.11.2 覆盖缺账号、缺 `delivery_goal`、缺 `intelligent_selection_mode`、条件必填、非法枚举、`poi_ids`/`product_ids` 数量边界和分页边界。

### 3.12 `get-tool-pack-detail`

- [x] 3.12.1 覆盖来自列表的组件 ID、不同组件 ID、合法不存在组件 ID 的详情查询。
- [x] 3.12.2 覆盖缺账号、缺 `tool_pack_id`、`tool_pack_id` 类型错误、负数、0 和超大数。

### 3.13 `list-market-pages`

- [x] 3.13.1 覆盖 `delivery_goal=POI`、`PRODUCT`、门店 ID、商品 ID、不同页码和页大小查询。
- [x] 3.13.2 覆盖缺账号、缺 `delivery_goal`、条件必填、非法 `delivery_goal`、`poi_ids`/`product_ids` 数量边界和 `page_size` 超过 100。

### 3.14 `get-market-page-detail`

- [x] 3.14.1 覆盖单个营销页、多个营销页、门店来源营销页、商品来源营销页和合法不存在营销页详情。
- [x] 3.14.2 覆盖缺账号、缺 `market_page_ids`、空数组、数组项类型错误、负数、0、超大 ID 和重复 ID。

### 3.15 `list-consult-awemes`

- [x] 3.15.1 覆盖 `delivery_goal=POI`、`PRODUCT`、关键词、授权类型、门店 ID、商品 ID 和分页查询。
- [x] 3.15.2 覆盖缺账号、缺 `delivery_goal`、条件必填、非法 `delivery_goal`、`filtering` 类型错误、`auth_type` 类型/枚举错误和 `product_ids` 数量边界。

### 3.16 `batch-update-project-week-schedule`

- [x] 3.16.1 覆盖单项目、多项目、`REALTIME`、`NEXT_DAY`、全天投放、工作日高峰和局部时段更新。
- [x] 3.16.2 覆盖缺账号、缺 `data`、空数组、批量项缺字段、`schedule_time` 非 336 位、非法 `schedule_scene`、项目 ID 类型错误、重复项目 ID 和不存在项目 ID。
- [x] 3.16.3 用详情或列表查询确认投放时段更新结果。

### 3.17 完成状态汇总

- [x] 3.17.1 每条实际用例完成后立即更新对应 checkbox 和验收记录，不保留“整组完成后统一勾选”的状态。
- [x] 3.17.2 每个接口按自身规则完成正向真实调用、负向校验、边界条件、输出展示和失败恢复覆盖；不以固定用例数量作为完成标准。
- [x] 3.17.3 汇总每个接口的已覆盖字段、已覆盖枚举、已覆盖条件规则、已覆盖边界、平台业务失败、环境失败和待补充项。

## 4. 问题修复与重测

- [x] 4.1 对浏览器验收发现的问题，先通过日志、trace、线程历史、`/api/mcp/config`、原生工具 dry-run 或定向测试定位根因。
- [x] 4.2 若需要修改 function、class 或 method，先按仓库规则运行 GitNexus impact analysis，并向用户报告 blast radius。
- [x] 4.3 按最小影响范围修复工具注册、skill 导航、自然语言参数整理、本地校验、字段映射、MCP guard、结果展示、认证或环境配置问题。
- [x] 4.4 修复后运行相关后端定向 `pytest`、前端 `pnpm check` 或对应单元测试。
- [x] 4.5 回到浏览器重新执行受影响接口的用例组，并记录重测证据。

## 5. OpenSpec 与交付校验

- [x] 5.1 运行 `openspec validate verify-oceanengine-local-project-browser-acceptance --strict`。
- [x] 5.2 汇总最终浏览器验收记录，说明 16 个接口的覆盖维度、真实调用证据、负向拦截证据、平台业务失败、修复和未解决风险。
- [x] 5.3 在进入 archive 前，检查是否有新增长期规则、坑点、边界或扩展约束需要沉淀到最近层级 `AGENTS.md`。
- [x] 5.4 提交前运行 `gitnexus_detect_changes()`，确认受影响范围符合预期。
