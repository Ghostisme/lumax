# 获取本地推创编可用抖音号

来源 URL：https://open.oceanengine.com/labels/37/docs/1807990317937690
Path：`/open_api/v3.0/local/aweme/authorized/get/`
方法：`GET`
脚本：`scripts/endpoints/list_authorized_awemes.py`

## 参数

- `local_account_id`：必填，本地推投放账户ID。
- `marketing_goal`：必填，抖音号使用场景，允许 `LIVE` 直播、`VIDEO_IMAGE` 短视频/图文。
- `filtering.search_key_word`：可选，根据抖音号 ID 和名称搜索。
- `aweme_id`：兼容本地旧输入，可选，抖音号；官方筛选字段在 `filtering.search_key_word` 下。
- `page`、`page_size`：可选，分页参数。

## 输出建议

展示可用于本地推创编的抖音号、昵称和授权状态。直播项目或需要投放直播间时使用返回的 `aweme_id`。

## 响应字段

- `data.aweme_id_list[].aweme_id`：抖音号。
- `data.aweme_id_list[].aweme_name`：抖音号名称。
- `data.aweme_id_list[].aweme_avatar`：抖音头像。
- `data.aweme_id_list[].auth_type`：抖音号授权类型，允许 `OFFICIAL` 官方、`SELF` 自运营、`AWEME_COOPERATOR` 合作达人。
- `data.aweme_id_list[].aweme_has_uni_prom`：该抖音号是否有直播roi2计划投放。
- `data.aweme_id_list[].can_create_roi2_ad`：该抖音号是否能创建roi2单元，`marketing_goal=LIVE` 时返回。
- `data.page_info.page`、`data.page_info.page_size`、`data.page_info.total_page`、`data.page_info.total_number`：分页信息。
- 不向用户展示请求日志 ID。

## 调用约束

- 用户要求获取创编可用抖音号时，使用 `capability=list-authorized-awemes`，不要用 `list-projects`、`list-consult-awemes` 或底层 MCP 替代。
- 搜索抖音号 ID 或名称时使用官方字段 `filtering.search_key_word`。
- `marketing_goal` 只支持 `LIVE` 直播、`VIDEO_IMAGE` 短视频/图文；不得把“长视频”猜成 `VIDEO_IMAGE`，用户说长视频时必须说明当前接口不支持该使用场景或追问其是否指短视频/图文。
