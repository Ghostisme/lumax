# 获取视频素材评估标签

- 官方 `doc_id`：`1848486485420108`
- 官方 path：`/open_api/2/file/material_attributes/list/`
- 方法：`GET`
- capability：`list-video-material-attributes`
- MCP 工具：当前 `platform-agent-biz` 未暴露

## 请求字段

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `account_id` | 是 | 账户 ID |
| `account_type` | 是 | 账户类型，官方支持 `BP`、`AGENT`、`AD`、`QIANCHUAN`、`LOCAL`；本地推场景规则仅放行 `LOCAL` |
| `filtering.material_ids` | 否 | 素材 ID 列表，1 到 1000 个 |
| `filtering.material_properties` | 否 | 素材属性列表，支持 `FIRST_PUBLISH_MATERIAL`、`AD_HIGH_QUALITY_MATERIAL`、`ECP_HIGH_QUALITY_MATERIAL`、`AD_LOW_QUALITY_MATERIAL`、`ECP_LOW_QUALITY_MATERIAL`、`INEFFICIENT_MATERIAL`、`SIMILAR_MATERIAL`、`SIMILAR_QUEUE_MATERIAL`、`CARRY_MATERIAL` |
| `filtering.start_time` | 否 | 统计开始时间 |
| `filtering.end_time` | 否 | 统计结束时间 |
| `filtering.attributes_modify_time` | 否 | 标签更新时间 |
| `return_lowquality_suggestions` | 否 | 是否返回低质建议 |
| `page_size` | 是 | 每页数量 |
| `page` | 是 | 页码 |

## 缺口记录

当前 MCP 工具列表未包含该接口对应工具。触发本 capability 时，业务工具只返回中文缺失诊断，不改用 HTTP API、curl 或 SDK 直连。

## 响应字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `code` | `number` | 返回码,详见 【附录-返回码】 |
| `message` | `string` | 返回信息,详见 【附录-返回码】 |
| `data` | `json` | 返回数据 |
| `data.materials[]` | `object[]` | 素材及素材属性列表 |
| `data.materials[].material_id` | `number` | 素材id |
| `data.materials[].ad_low_quality_suggestions[]` | `string[]` | 当该素材为AD低质素材时，返回低质原因，仅当return_lowquality_suggestions = true时，会返回此参数 |
| `data.materials[].ecp_low_quality_suggestions[]` | `string[]` | 当该素材为千川低质素材时，返回低质原因，仅当return_lowquality_suggestions = true时，会返回此参数 |
| `data.materials[].local_low_quality_suggestions[]` | `string[]` | 当该素材为本地推低质素材时，返回低质原因，仅当return_lowquality_suggestions = true时，会返回此参数 |
| `data.materials[].is_ad_high_quality_material` | `bool` | 是否AD优质素材 |
| `data.materials[].is_ad_low_quality_material` | `bool` | 是否AD低质素材 |
| `data.materials[].is_ecp_high_quality_material` | `bool` | 是否千川优质素材 |
| `data.materials[].is_ecp_low_quality_material` | `bool` | 是否千川低质素材 |
| `data.materials[].is_local_high_quality_material` | `bool` | 是否本地推优质素材 |
| `data.materials[].is_local_low_quality_material` | `bool` | 是否本地推低质素材 |
| `data.materials[].is_first_publish_material` | `bool` | 是否是首发素材 |
| `data.materials[].is_inefficient_material` | `bool` | 是否低效素材 |
| `data.materials[].is_carry_material` | `bool` | 是否存在搬运风险，建议入参account_type = AD 或 QIANCHUAN 或本地推查询 |
| `data.materials[].is_similar_material` | `bool` | 是否同质化挤压严重素材，方舟/工作台账户不支持 |
| `data.materials[].is_similar_queue_material` | `bool` | 是否同质化素材风险-排队投放素材，方舟/工作台账户不支持 |
| `data.materials[].is_similar_expected_queue_material` | `bool` | 是否同质化素材风险-未投放预计排队素材，方舟/工作台账户不支持 |
| `data.materials[].attributes_modify_time` | `string` | 「存在搬运打压风险」属性最后一次更新时间，如素材未被标记为搬运，则不会返回该时间。格式为yyyy-mm-dd HH:MM:SS |
| `data.page` | `object` | 分页信息 |
| `data.page.page` | `number` | 页码 |
| `data.page.page_size` | `number` | 页面大小 |
| `data.page.total_count` | `number` | 总页数 |
| `data.page.total_number` | `number` | 总数 |
| `request_id` | `string` | 请求日志id |
