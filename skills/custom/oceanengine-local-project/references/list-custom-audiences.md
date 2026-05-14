# 查询本地推创编可用人群包

来源 URL：https://open.oceanengine.com/labels/37/docs/1808003891639609
Path：`/open_api/v3.0/local/custom_audience/get/`
方法：`POST`
脚本：`scripts/endpoints/list_custom_audiences.py`

## 参数

- `local_account_id`：必填，本地推投放账户ID。
- `tags_type`：必填，按人群包属性筛选，允许 `CUSTOM` 自定义人群包、`SYS_RECOMMEND` 系统推荐人群包。用户说“自定义人群包”时使用 `CUSTOM`，用户说“系统推荐人群包”时使用 `SYS_RECOMMEND`；如果用户没有说明人群包属性，应追问，不得省略 `tags_type` 调用接口。
- `page`、`page_size`：可选，分页参数。

## 输出建议

展示人群包ID、名称、覆盖量和状态。创建或更新项目定向时使用返回的人群包ID。

返回空列表也属于成功查询结果，应直接向用户说明当前条件下没有查到可用人群包；不得为了补充说明自动切换 `tags_type`、删除 `tags_type` 或更改分页后继续查询。

## 响应字段

- `data.custom_audience_list[].custom_audience_id`：人群包ID。
- `data.custom_audience_list[].custom_audience_name`：人群包名称。
- `data.custom_audience_list[].cover_num`：覆盖量。
- `data.custom_audience_list[].status`：状态，常见值 `AVAILABLE` 可用、`UNAVAILABLE` 不可用。
- `data.page_info.page`、`data.page_info.page_size`、`data.page_info.total_number`、`data.page_info.total_page`：分页信息。
- `request_id`：请求日志id。
