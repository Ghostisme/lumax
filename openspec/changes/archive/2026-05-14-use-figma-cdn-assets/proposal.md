# 统一 Figma 静态资源 CDN 访问

## 背景

前端已将多数 `frontend/public/images/figma` 静态资源改为 CDN 地址，但仍有部分组件直接使用 `/images/figma/...` 本地 public 路径。`make dev` 启动时 Next.js dev server 会按本地 public 资源提供这些路径，因此浏览器不会通过 CDN 请求这些资源。

## 目标

- 新增统一的 Figma 静态资源 URL helper，集中维护 CDN 基址和路径拼接。
- 通过 `NEXT_PUBLIC_FIGMA_ASSET_BASE_URL` 支持覆盖 CDN 基址，默认使用当前生产 CDN：`https://prod-upload.jialugroup.cn/lumax-ai/figma`。
- 将现有 Figma 静态资源引用统一迁移到 helper，避免遗漏 `/images/figma/...` 本地路径。
- 对使用 `next/image` 渲染且需要浏览器直连 CDN 的图片保留或补充 `unoptimized`。

## 非目标

- 不使用 Next.js `assetPrefix` 改写 public 资源路径。
- 不调整非 Figma 静态资源加载策略。
- 不移动或删除 `frontend/public/images/figma` 下的本地资源文件。

## 影响范围

- 前端环境变量声明：`frontend/src/env.js`。
- 前端资源 URL helper：预计新增于 `frontend/src/core/config/` 或相近现有配置模块。
- 工作区欢迎页、侧边栏、聊天页、输入框和全局样式中的 Figma 资源引用。

## 风险与约束

- CSS 文件不能直接导入 TypeScript helper，因此全局样式中的 CDN URL 需要保持静态 URL 或改为由 CSS 变量承接；本次优先保证代码路径统一，避免引入额外运行时样式复杂度。
- `NEXT_PUBLIC_*` 环境变量在 Next.js 客户端构建时内联，修改 `.env` 后需要重启 `pnpm dev` / `make dev` 才会生效。
- 当前可用 MCP 列表未暴露 GitNexus 工具；代码实施前将在可用工具范围内记录影响边界，并按静态调用关系控制变更范围。
