# 任务清单

## 1. 定位与影响

- [x] 1.1 定位 IP 状态切换逻辑和已存在的 `thinkingtoresult` 资源配置。
- [x] 1.2 确认 GitNexus impact analysis 可用性；当前 Cursor MCP 列表未暴露 GitNexus 工具，已改用静态调用关系确认低风险影响范围。

## 2. 实现

- [x] 2.1 新增 `thinkingtoresult` 展示时长常量。
- [x] 2.2 将 `streaming -> ready` 的 IP 状态切换从直接 `good` 改为先 `thinkingtoresult`。
- [x] 2.3 在 `thinkingtoresult` 展示结束后切到 `good`，并确保新的 streaming/error 状态可打断该过渡。
- [x] 2.4 新增 `canceltothinking` 展示时长常量。
- [x] 2.5 记录取消或失败后的下一次 streaming 需要先进入 `canceltothinking`。
- [x] 2.6 在 `canceltothinking` 展示结束后切到 `thinking`，并确保 ready/error 状态可打断该过渡。
- [x] 2.7 将 IP 图片切换改为交叉淡入淡出，避免 `wait` 顺序动画带来的断裂感。
- [x] 2.8 预加载所有 IP GIF 资源，降低首次进入过渡状态时的空白或卡顿。
- [x] 2.9 调整 `canceltothinking` 和 `thinkingtoresult` 的桥接时长，使过渡更短更自然。
- [x] 2.10 增加固定尺寸 IP 舞台容器，避免不同 GIF 画布尺寸导致切换位移。
- [x] 2.11 将 IP 图片改为在舞台容器内绝对重叠，并统一 `object-fit` / `object-position`。
- [x] 2.12 确认当前实际参与 IP 状态切换的 GIF 文件和画布尺寸。
- [x] 2.13 建立每个 IP 状态的 `scale/x/y` 校准表，对齐不同 GIF 的视觉主体锚点。
- [x] 2.14 将 per-state 校准应用到 IP 图片动画渲染中，同时保留交叉淡入淡出。

## 3. 验证

- [x] 3.1 运行本次修改文件的 ESLint 和 IDE lints。
- [x] 3.2 再次运行本次修改文件的 ESLint 和 IDE lints。
- [x] 3.3 再次运行本次修改文件的 ESLint 和 IDE lints。
- [x] 3.4 再次运行本次修改文件的 ESLint 和 IDE lints。
- [x] 3.5 再次运行本次修改文件的 ESLint 和 IDE lints。
