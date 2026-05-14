# 批量更新项目状态

来源 URL：https://open.oceanengine.com/labels/37/docs/1809958369980564
Path：`/open_api/v3.0/local/project/status/update/`
方法：`POST`
脚本：`scripts/endpoints/batch_update_project_status.py`

## 必填参数

- `local_account_id`：本地推投放账户ID。
- `items`：批量项目状态列表；映射到官方请求字段 `data`，长度限制 1 到 50。
- `items[].project_id`：项目ID。
- `items[].opt_status`：项目操作状态，官方允许 `ENABLE` 启用项目、`PAUSED` 暂停项目。

## 枚举与限制

- `opt_status=ENABLE`：启用项目。
- `opt_status=PAUSED`：暂停项目。
- 官方文档说明删除项目不可进行任何操作；当前接口不暴露删除枚举，用户要求删除时应明确告知不支持，不要尝试传 `DELETE`。

## 自然语言映射

- 用户说“暂停投放”必须整理为 `items[].opt_status=PAUSED`，项目 ID 放入同一批量项的 `items[].project_id`。
- 用户说“启用项目”必须整理为 `items[].opt_status=ENABLE`，项目 ID 放入同一批量项的 `items[].project_id`。
- 不要使用 `project_ids`、`status`、`PROJECT_STATUS_DISABLE` 或 `PROJECT_STATUS_ENABLE` 构造本接口 payload。
- 用户重复给出同一个项目 ID 时，重复项目 ID 不得合并、去重或改为查询其它项目；必须按出现次数原样写入 `items`，由业务工具或平台返回逐项结果。

## 批量规则

逐项校验、逐项执行、逐项确认。任一项目失败时，结果中必须标明失败项、重试次数和失败原因。单批最多 50 个项目。

## 执行确认

每个项目状态更新后查询项目详情或列表确认状态。确认失败最多重试 3 次。
