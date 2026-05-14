# 增加 Thinking 到 Result 的 IP 过渡

## 背景

聊天输入框右侧 IP 动画已有 `thinkingtoresult-ip.gif` 资源和 `thinkingtoresult` 状态配置，但当前运行状态从 `streaming` 回到 `ready` 时会直接从 `thinking-ip.gif` 切换到 `good-ip.gif`，缺少中间过渡。另一个已配置但未使用的资源是 `canceltothinking-ip.gif`，当用户取消或回复失败后再次进入思考时，也需要先展示该过渡动画。

## 目标

- 当一次流式回复结束时，IP 动画从 `thinking` 先切到 `thinkingtoresult`。
- `thinkingtoresult` 短暂展示后再切到 `good`。
- 当上一次对话被取消或失败后重新进入 `streaming`，IP 动画从当前状态先切到 `canceltothinking`。
- `canceltothinking` 短暂展示后再切到 `thinking`。
- 所有 IP 状态图片切换统一使用短时交叉淡入淡出和轻微缩放，避免 GIF 直接硬切。
- 预加载所有 IP GIF 资源，降低首次切换到过渡动画时的空白和卡顿。
- 所有 IP 状态图片必须在固定尺寸的舞台容器内切换，使用统一的 `object-fit` 和 `object-position` 锚定视觉基准，避免不同 GIF 画布尺寸导致位移。
- 在设计资源尚未统一画布和锚点前，前端需要提供每个状态的 `scale/x/y` 校准表，将不同 GIF 的视觉主体对齐到同一舞台锚点。
- 保留现有 `good` 自动隐藏、`fail`、`sleep` 等状态行为。

## 非目标

- 不调整 IP 图片资源文件。
- 不改变模型请求、消息流、停止生成或错误处理逻辑。
- 不新增用户可配置项。

## 影响范围

- 前端聊天输入框组件：`frontend/src/components/workspace/input-box.tsx`。

## 风险与约束

- 过渡时长需要以常量控制，避免阻塞后续 `streaming`、`ready` 或 `error` 状态切换。
- 交叉淡入淡出只动画 `opacity` 和 `transform`，避免触发布局计算。
- 固定舞台容器应保持原有视觉区域，不改变输入框布局或占位高度。
- per-state 校准只作为短期前端补偿；长期仍应由设计资源统一画布尺寸、透明留白和角色锚点。
- 用户偏好减少动画时，仍需保留简化后的淡入淡出，不做缩放。
- 由于当前 Cursor MCP 列表未暴露 GitNexus 工具，实施阶段如无法运行 impact analysis，需要记录为工具约束。
