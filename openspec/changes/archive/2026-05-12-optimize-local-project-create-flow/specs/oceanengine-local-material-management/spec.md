## ADDED Requirements

### Requirement: 创建项目流程中的视频必须通过素材管理上传或选择

创建项目业务流程需要视频素材时，系统 SHALL 通过 `oceanengine_local_material` 上传用户明确授权的视频或查询素材库候选。系统 SHALL NOT 扫描最近文件、下载目录、浏览器记录、剪贴板或任意目录来猜测素材。

#### Scenario: 用户提供本地视频文件

- **GIVEN** 用户在创建项目流程中要求添加视频
- **AND** 用户明确提供或授权了 `video_file_path`
- **WHEN** 系统需要把视频加入素材库
- **THEN** 系统 SHALL 调用 `oceanengine_local_material` 的上传视频能力
- **AND** 上传前 SHALL 执行素材管理本地文件参数校验
- **AND** 校验失败时 SHALL 只追问当前一个视频参数问题
- **AND** 系统 SHALL NOT 直接调用 `localFileVideoUpload` MCP tool

#### Scenario: 用户要求从素材库选择视频

- **GIVEN** 用户在创建项目流程中要求从素材库选择视频
- **WHEN** 系统需要展示可选视频
- **THEN** 系统 SHALL 调用 `oceanengine_local_material` 的素材库视频查询能力
- **AND** 候选结果 SHALL 以 `data.clarification.input_control.type=choice_cards` 或等价结构返回
- **AND** 每个候选 SHALL 保留用于回填的 `value`、用户可读 `label`、安全业务摘要 `metadata` 和原始顺序
- **AND** 用户可见文本 SHALL 不展示内部 MCP tool 名、平台请求日志 ID 或原始 JSON 包装

#### Scenario: 视频来源未被用户授权

- **GIVEN** 创建项目流程需要视频
- **AND** 用户没有提供或授权视频文件、视频 URL、签名或素材库候选
- **WHEN** 系统准备获取视频
- **THEN** 系统 SHALL 返回中文单问题追问
- **AND** 系统 SHALL NOT 从本机目录、最近文件、浏览器记录、剪贴板或历史会话中推断视频来源
- **AND** 系统 SHALL NOT 生成虚假的素材候选

### Requirement: 创建项目流程必须按投放目标校验视频数量

创建项目流程选择视频时，系统 SHALL 按投放目标维护默认视频数量要求：团购成交需要 10 条视频，其它投放目标需要 3 到 5 条视频。数量不足或过多时，系统 SHALL 返回中文提示或候选补齐，不得静默裁剪用户选择。

#### Scenario: 团购成交视频数量要求

- **GIVEN** 创建项目流程的投放目标为团购成交
- **WHEN** 用户选择的视频数量少于 10 条
- **THEN** 系统 SHALL 返回中文提示说明团购成交需要 10 条视频
- **AND** 系统 SHALL 可继续通过素材库候选 `choice_cards` 引导用户补齐
- **AND** 系统 SHALL NOT 静默使用不足 10 条视频继续创建单元素材

#### Scenario: 其它目标视频数量要求

- **GIVEN** 创建项目流程的投放目标不是团购成交
- **WHEN** 用户选择的视频数量少于 3 条或超过 5 条
- **THEN** 系统 SHALL 返回中文提示说明当前目标需要 3 到 5 条视频
- **AND** 用户明确坚持边界外数量时 SHALL 由后续单元或素材规则校验处理
- **AND** 系统 SHALL NOT 自行截断、抽样或删除用户选择的视频

#### Scenario: 素材候选为空或查询失败

- **GIVEN** 系统已调用素材管理查询候选视频
- **WHEN** MCP 工具缺失、MCP 调用失败、平台业务失败或返回空候选
- **THEN** 系统 SHALL 返回中文失败或暂无候选说明
- **AND** 系统 SHALL NOT 生成空的或臆造的 `choice_cards.options`
- **AND** 该结果 SHALL NOT 被当作创建项目流程成功

