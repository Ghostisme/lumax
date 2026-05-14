# 任务清单

## 1. 定位与影响

- [x] 1.1 盘点 `frontend/public/images/figma` 相关引用，确认仍走本地 public 路径的位置。
- [x] 1.2 在可用工具范围内完成影响分析，并记录无法使用 GitNexus MCP 时的替代评估。

## 2. 实现

- [x] 2.1 新增统一 Figma 静态资源 URL helper，并支持 `NEXT_PUBLIC_FIGMA_ASSET_BASE_URL` 默认值。
- [x] 2.2 在 `frontend/src/env.js` 声明并暴露 `NEXT_PUBLIC_FIGMA_ASSET_BASE_URL`。
- [x] 2.3 将组件中的 `/images/figma/...` 和已硬编码 CDN 的 Figma 资源引用迁移为 helper。
- [x] 2.4 对需要浏览器直连 CDN 的 `next/image` 图片保留或补充 `unoptimized`。

## 3. 验证

- [x] 3.1 搜索确认前端源码中不再存在新的 `/images/figma/...` 本地资源引用。
- [x] 3.2 运行前端 lint/typecheck 或记录无法运行原因。
