---
name: oceanengine-local-project
description: 管理巨量本地推项目的对话 skill：创建本地推投流项目流程优先使用 `oceanengine_local_project_create_flow`；项目更新、列表/详情查询、状态或排期修改，以及 POI/商品/抖音号/人群/留资组件/营销页列表/详情查询/咨询抖音号查询使用 `oceanengine_local_project`；遇到本地推项目、营销页或留资组件请求时立即读取本 skill，不要先搜索或直连 `nacos-mcp-router`；支持根据多门店ID拉取门店ID；支持单条与批量操作


---

# 巨量本地推项目管理

通过 DeerFlow 原生业务工具调用巨量引擎本地推项目管理模块接口。创建本地推投流项目流程使用 `oceanengine_local_project_create_flow`；项目更新、列表/详情查询、状态或排期修改及资源查询使用 `oceanengine_local_project`。主文件只负责导航和执行流程；接口参数、枚举和示例按需读取 `references/`，机器可执行规则按需读取 `rules/`。

## 使用流程

1. 判断用户意图：用户要求“创建本地推项目 / 创建投流项目 / 创建项目流程”，且提到投手、营销场景、投放目标、单元类型、投放门店/商品、用户定向、排期预算、出价或视频素材时，必须优先调用 `oceanengine_local_project_create_flow`，不要改用 `oceanengine_local_project` 的 `create-project` capability。
1.0.1 创建流程中即使用户说“先从可投门店 / 可投商品 / 素材库里选择”，也必须先调用 `oceanengine_local_project_create_flow` 进入流程；不得先调用 `oceanengine_local_project`、`oceanengine_local_material` 或底层 MCP 做候选查询来替代创建流程入口。
1.1 创建流程中常见中文枚举需先映射：短视频/图文=`VIDEO_IMAGE`，直播间=`LIVE`，团购成交=`PRODUCT_PAY`，线下到店=`POI_RECOMMEND`，获取线索=`EXTERNAL`，线上互动=`CONTENT_HEAT`，通投=`GENERAL`，搜索=`SEARCH`；用户说“从素材库选择视频”时传 `select_library_videos=true`。
1.2 非创建流程请求，先读 `references/index.md` 定位接口、reference、rule 和 capability。
2. 只读取当前接口对应的 reference 与 rule 文件，不要一次性加载全部接口文档和规则配置。
3. 命中本 skill 后，即使用户缺少必填参数，也不得直接调用 `ask_clarification` 自行汇总多个缺失项；必须先把已知信息整理成 JSON，调用对应 DeerFlow 原生业务工具做本地校验。
4. 调用 `oceanengine_local_project_create_flow` 时传入 `payload_json`；调用 `oceanengine_local_project` 时传入 `capability` 和 `payload_json`；由业务工具决定本轮只追问哪一个参数。
4.1 参数不足或不合法时，把业务工具返回的 `data.user_visible_text` 或首条中文错误直接反馈给用户；不得追加其它未展示缺失项。
5. 业务工具返回 `success=false` 时必须立即停止，只按 `message`、`errors` 或 `data.user_visible_text` 中的中文错误回复；不得删除用户要求的分页、筛选、枚举或资源字段后重试，也不得从失败结果里整理数据冒充成功。
6. 增删改类接口必须让业务工具执行后置查询确认；失败或不一致最多重试 3 次。
7. 批量操作逐项执行、逐项确认、逐项返回结果，不用整体成功掩盖单项失败。
8. 不得使用 `task` 或任何子代理执行、诊断或替代执行本 skill；必须由主 Agent 直接调用 `oceanengine_local_project` 或返回业务工具不可用。
9. 不要直接调用底层 `localProject*` MCP 工具来替代业务工具，尤其不要把 snake_case 参数直接传给底层 MCP；即使 `nacos-mcp-router_use_tool`、curl、HTTP API 或子代理可用，也不得用它们替代业务工具发起真实接口请求。
10. 业务工具返回缺少必填项或条件必填项时，立即停止，只用中文询问用户该字段是什么值；如果该字段是枚举，必须展示中文可选项。
11. 用户请求查询、验收或执行真实业务时，`dry_run` 必须为 `false`；只有用户明确要求“本地预检”“不调用真实接口”“只校验参数”时才允许 `dry_run=true`。
12. 一次用户请求只执行与用户意图匹配的单个 `capability` 和必要的后置确认；不得为了补充说明主动改查其他枚举、其他分页或其他能力。
13. 用户明确给出的边界值、非法值或疑似非法值必须原样交给业务工具做本地校验；不得自行裁剪、改写成合法默认值或换参数重试。
13.1 用户给出的枚举文本不在当前接口允许范围内时，不得把它猜成语义相近的合法枚举；例如“半官方授权”不得猜成“官方授权”，必须原样交给业务工具校验或中文说明支持范围。
13.2 创建项目时，用户给出的营销目的不在官方支持的“线上互动、线下到店、团购成交、获取线索”范围内时，不得猜成任何合法营销目的；例如“品牌曝光”不得猜成“线上互动”，必须原样交给业务工具校验或中文说明支持范围。
14. 用户说“每页 N 条”时，N 必须作为 `page_size` 原样传入；例如“每页 1001 条”必须传 `page_size=1001` 并让业务工具返回本地校验错误，不得改成 1000。
15. 用户说“第 N 页”或“页码 N”时，N 必须作为 `page` 原样传入；例如“第 0 页”必须传 `page=0` 并让业务工具返回本地校验错误，不得改成 1。
16. 留资组件的获取线索方式只允许用户明确表达的“自定义”或“智能优选”；不得把用户给出的其他获取线索方式猜成自定义或智能优选，必须按原值交给业务工具校验或追问确认。
17. 返回字段由业务工具和 `rules/*.json` 决定；不得追问用户希望展示哪些返回字段，也不得主动要求用户指定响应字段。
16. 用户要求根据多门店ID拉取门店ID时，直接使用 `capability=get-poi-ids-by-multi-poi-id`；只缺少本地推投放账户ID时，只追问本地推投放账户ID，不要追问时间范围、是否调用 API、展示字段或其它无关信息。
17. 缺少字段时只使用中文业务字段名追问；面向用户不要展示底层 MCP tool 名、API 字段名或参数枚举码。
18. 用户明确说空列表时，必须把空数组原样传给业务工具校验，不得自行改成缺失字段后追问。
18.1 用户给出的数组项数量超过规则上限时，也必须把全量数组原样交给业务工具校验，不得自行截断、抽样、删除重复项或只传前 N 个。
19. 创建项目时，用户说“指定门店”“门店 ID”“投门店”并给出 ID，必须把该 ID 原样整理到 `promotion_poi_ids`；即使该字段与商品投放组合冲突，也必须交给业务工具做本地校验并按中文错误回复，不得静默删除用户提供的门店。
20. 更新项目时，当前官方 `LocalProjectUpdateV30Request` 只支持更新 `end_time`，不支持 `start_time`；用户要求修改开始时间时必须交给业务工具按不支持字段返回中文错误，不得绕过本地校验让平台部分更新。
21. 用户用“投放时间改成 A 到 B”“开始时间改成 A”“从 A 投到 B”等表达要求变更开始日期时，必须在 `payload_json` 中保留 `start_time=A` 让业务工具拦截；不得改成只更新 `end_time=B`，也不得把部分更新当作完成。
22. 批量更新项目投放时段时，`schedule_time` 必须是连续 336 位 `0`/`1` 字符串；“每天全天投放”必须直接复制下面的 `ALL_DAY_SCHEDULE_TIME`，不得手工扩写、截断、加入空格、换行、分段标签或说明文字。
23. `ALL_DAY_SCHEDULE_TIME=111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111`
24. `NONE_SCHEDULE_TIME=000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000`
24.1 批量更新项目投放时段时，不得创建脚本或文件来计算 `schedule_time`；必须使用本文件或对应 reference 中已经给出的固定 336 位字符串，或在无法确定时追问用户。
25. 批量更新项目状态时，用户说“暂停投放”必须整理为 `items=[{"project_id": 用户项目ID, "opt_status": "PAUSED"}]`，并调用 `capability=batch-update-project-status`。
26. 批量更新项目状态时，用户说“启用项目”必须整理为 `items=[{"project_id": 用户项目ID, "opt_status": "ENABLE"}]`，并调用 `capability=batch-update-project-status`。
27. 批量更新项目状态不得使用 `project_ids`、`status`、`PROJECT_STATUS_DISABLE` 或 `PROJECT_STATUS_ENABLE` 构造状态更新 payload；这些不是该接口官方入参。
28. 批量更新项目状态时，用户重复给出的项目 ID 必须在 `items` 中按出现次数原样保留；不得合并、去重、改为查询其它项目或追问“是否重复”。
29. 获取本地推创编可用抖音号时，`marketing_goal` 只支持直播和短视频/图文；用户说“长视频”不是官方支持的抖音号使用场景，不得猜成短视频/图文或 `VIDEO_IMAGE`，必须按不支持范围说明或交给业务工具校验。
30. 项目列表查询必须把用户给出的每个筛选条件都写入 `filtering`；不得只用状态、名称或项目 ID 等部分条件查询后，再用返回结果口头筛选展示。
31. 更新项目请求缺少项目 ID 时，只追问项目 ID，不得改查项目列表、不得用项目名称关键词猜测项目，也不得批量修改任何候选项目。
32. 更新项目高峰日预算时，若用户要求开启或变更高峰日预算但未明确给出预算上调比例，必须追问上调比例；不得从项目详情中复用旧的高峰日预算上调比例，也不得用默认比例替代。

## DeerFlow 原生业务工具入口

运行时必须优先使用 DeerFlow 原生业务工具：

```json
{
  "capability": "list-projects",
  "payload_json": "{\"local_account_id\":1854708763953159}",
  "dry_run": false
}
```

业务工具输出结构化 JSON，字段包括 `success`、`message`、`data`、`errors`、`tool_name`、`request_id`、`retry_count`。`data` 中会包含 `execution_source=deerflow-native-tool`、`business_tool_name`、`mcp_server_name` 和 `mcp_tool_name`。

严禁绕过业务工具做增删改；直接调用 MCP 不会执行业务工具内参数校验、枚举映射和后置查询确认，容易出现“接口返回成功但数据未变更”的误判。

## 本地开发脚本入口

所有接口仍保留独立 Python 脚本，用于本地开发、dry-run 和回归测试；运行时不依赖命令行脚本执行：

```bash
python /mnt/skills/custom/oceanengine-local-project/scripts/endpoints/list_projects.py --input '{"local_account_id":1854708763953159}'
```

本地路径运行时可使用：

```bash
python3 skills/custom/oceanengine-local-project/scripts/endpoints/list_projects.py --input '{"local_account_id":1854708763953159}' --dry-run
```

脚本真实 MCP 调用复用项目共享运行时 `tools.oceanengine_local_project_runtime.mcp_client`，并以 Nacos 注册信息或 DeerFlow 已加载的 Nacos MCP server 配置解析 `platform-agent-biz` 的真实 MCP endpoint。缺少项目根目录、Nacos 配置、目标 MCP server、目标 endpoint 或目标 MCP tool 时，脚本应返回中文失败诊断，不得自动改用本机固定 Router、curl、SDK、HTTP API 或 mock。

```bash
cd backend
uv run python ../skills/custom/oceanengine-local-project/scripts/endpoints/list_projects.py --input '{"local_account_id":1854708763953159}'
```

如需覆盖目标 MCP server 名，可设置环境变量：

```bash
OCEANENGINE_MCP_SERVER_NAME=platform-agent-biz DEER_FLOW_PROJECT_ROOT=/path/to/lumax python /mnt/skills/custom/oceanengine-local-project/scripts/endpoints/list_projects.py --input '{"local_account_id":1854708763953159}'
```

## 接口导航

- 创建项目：读 `references/create-project.md` 和 `rules/create-project.json`，`capability=create-project`
- 更新项目：读 `references/update-project.md` 和 `rules/update-project.json`，`capability=update-project`
- 获取项目列表：读 `references/list-projects.md` 和 `rules/list-projects.json`，`capability=list-projects`
- 获取项目详情：读 `references/get-project-detail.md` 和 `rules/get-project-detail.json`，`capability=get-project-detail`
- 批量更新项目状态：读 `references/batch-update-project-status.md` 和 `rules/batch-update-project-status.json`，`capability=batch-update-project-status`
- 获取可投门店列表：读 `references/list-promotable-pois.md` 和 `rules/list-promotable-pois.json`，`capability=list-promotable-pois`
- 获取可投商品列表：读 `references/list-promotable-products.md` 和 `rules/list-promotable-products.json`，`capability=list-promotable-products`
- 获取本地推创编可用抖音号：读 `references/list-authorized-awemes.md` 和 `rules/list-authorized-awemes.json`，`capability=list-authorized-awemes`
- 查询本地推创编可用人群包：读 `references/list-custom-audiences.md` 和 `rules/list-custom-audiences.json`，`capability=list-custom-audiences`
- 根据多门店ID拉取门店ID：读 `references/get-poi-ids-by-multi-poi-id.md` 和 `rules/get-poi-ids-by-multi-poi-id.json`，`capability=get-poi-ids-by-multi-poi-id`
- 获取可用留资组件列表：读 `references/list-tool-packs.md` 和 `rules/list-tool-packs.json`，`capability=list-tool-packs`
- 获取可用留资组件详情：读 `references/get-tool-pack-detail.md` 和 `rules/get-tool-pack-detail.json`，`capability=get-tool-pack-detail`
- 获取可用营销页列表：读 `references/list-market-pages.md` 和 `rules/list-market-pages.json`，`capability=list-market-pages`
- 查询营销页详情：读 `references/get-market-page-detail.md` 和 `rules/get-market-page-detail.json`，`capability=get-market-page-detail`
- 获取私信接待抖音号：读 `references/list-consult-awemes.md` 和 `rules/list-consult-awemes.json`，`capability=list-consult-awemes`
- 列表批量更新项目投放时段：读 `references/batch-update-project-week-schedule.md` 和 `rules/batch-update-project-week-schedule.json`，`capability=batch-update-project-week-schedule`

## MCP 与安全约束

- 目标 MCP 服务名为 `platform-agent-biz`。
- 目标 MCP 工具名由对应 rule 文件绑定；创建项目固定为 `localProjectCreate`。
- 指定服务名和工具名调用失败时停止执行并返回业务工具中的中文错误，不自动切换其他 server、tool、curl、HTTP API 或 SDK。
- 不直接绕过 MCP 调用 OceanEngine HTTP API。
- 增删改类操作完成后必须重新查询确认，最多重试 3 次。
