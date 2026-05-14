# 根据多门店ID拉取门店ID

来源 URL：https://open.oceanengine.com/labels/37/docs/1809719485612043
Path：`/open_api/v3.0/local/multi_poi_id/poi_ids/get/`
方法：`POST`
脚本：`scripts/endpoints/get_poi_ids_by_multi_poi_id.py`

## 必填参数

- `local_account_id`：本地推投放账户ID。
- `multi_poi_ids`：多门店ID列表，至少 1 项，最多 50 项。
- `need_enable`：可选，是否仅查询当前在投门店；允许 `true` 仅查询在投门店、`false` 查询所有门店，默认 `false`。

## 输出建议

返回多门店ID与门店ID的映射关系，供创建或更新指定门店投放项目使用。

## 响应字段

| 字段 | 说明 |
| --- | --- |
| `data.multi_poi_info[].multi_poi_id` | 多门店 ID。 |
| `data.multi_poi_info[].poi_ids[]` | 多门店 ID 下属的门店 ID。 |
