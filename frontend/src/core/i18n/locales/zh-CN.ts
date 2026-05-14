import {
  CompassIcon,
  GraduationCapIcon,
  ImageIcon,
  PenLineIcon,
  SparklesIcon,
  VideoIcon,
} from "lucide-react";

import type { Translations } from "./types";

export const zhCN: Translations = {
  // Locale meta
  locale: {
    localName: "中文",
  },

  // Common
  common: {
    home: "首页",
    settings: "设置",
    delete: "删除",
    edit: "编辑",
    rename: "重命名",
    share: "分享",
    openInNewWindow: "在新窗口打开",
    close: "关闭",
    more: "更多",
    search: "搜索",
    download: "下载",
    thinking: "思考",
    artifacts: "文件",
    public: "公共",
    custom: "自定义",
    notAvailableInDemoMode: "在演示模式下不可用",
    loading: "加载中...",
    version: "版本",
    lastUpdated: "最后更新",
    code: "代码",
    preview: "预览",
    cancel: "取消",
    save: "保存",
    install: "安装",
    create: "创建",
    import: "导入",
    export: "导出",
    exportAsMarkdown: "导出为 Markdown",
    exportAsJSON: "导出为 JSON",
    exportSuccess: "对话已导出",
  },

  // Home
  home: {
    docs: "文档",
    blog: "博客",
  },

  // Welcome
  welcome: {
    greeting: "你好，我是Lumax\n很高兴为你服务",
    description:
      "欢迎使用 🦌 鹿宝，一个完全开源的超级智能体。通过内置和自定义的 Skills，\n鹿宝可以帮你搜索网络、分析数据，还能为你生成幻灯片、\n图片、视频、播客及网页等，几乎可以做任何事情。",
    mascotGreeting: "欢迎来到嘉鹿AI空间，美妙旅程一键开启！",

    createYourOwnSkill: "创建你自己的 Agent SKill",
    createYourOwnSkillDescription:
      "创建你的 Agent Skill 来释放鹿宝的潜力。通过自定义技能，鹿宝\n可以帮你搜索网络、分析数据，还能为你生成幻灯片、\n网页等作品，几乎可以做任何事情。",
  },

  // Clipboard
  clipboard: {
    copyToClipboard: "复制到剪贴板",
    copiedToClipboard: "已复制到剪贴板",
    failedToCopyToClipboard: "复制到剪贴板失败",
    linkCopied: "链接已复制到剪贴板",
  },

  // Feedback
  feedback: {
    submitted: "反馈已提交",
    failed: "反馈提交失败，请重试",
    missingRunId: "缺少运行 ID，无法提交反馈",
  },

  // Input Box
  inputBox: {
    placeholder: "想要聊点什么呐...",
    createSkillPrompt:
      "我们一起用 skill-creator 技能来创建一个技能吧。先问问我希望这个技能能做什么。",
    addAttachments: "上传附件",
    contentFactory: "内容工厂",
    smartDistribution: "智能投流",
    smartQA: "智能问答",
    materialOrganizing: "资料整理",
    mode: "模式",
    flashMode: "闪速",
    flashModeDescription: "快速且高效的完成任务，但可能不够精准",
    reasoningMode: "思考",
    reasoningModeDescription: "思考后再行动，在时间与准确性之间取得平衡",
    proMode: "Thinking With 3.1 Pro",
    proModeDescription: "思考、计划再执行，获得更精准的结果，可能需要更多时间",
    ultraMode: "Ultra",
    ultraModeDescription:
      "继承自 Pro 模式，可调用子代理分工协作，适合复杂多步骤任务，能力最强",
    reasoningEffort: "推理深度",
    reasoningEffortMinimal: "最低",
    reasoningEffortMinimalDescription: "检索 + 直接输出",
    reasoningEffortLow: "低",
    reasoningEffortLowDescription: "简单逻辑校验 + 浅层推演",
    reasoningEffortMedium: "中",
    reasoningEffortMediumDescription: "多层逻辑分析 + 基础验证",
    reasoningEffortHigh: "高",
    reasoningEffortHighDescription: "全维度逻辑推演 + 多路径验证 + 反推校验",
    searchModels: "搜索模型...",
    surpriseMe: "小惊喜",
    surpriseMePrompt: "给我一个小惊喜吧",
    followupLoading: "正在生成可能的后续问题...",
    followupConfirmTitle: "发送建议问题？",
    followupConfirmDescription: "当前输入框已有内容，选择发送方式。",
    followupConfirmAppend: "追加并发送",
    followupConfirmReplace: "替换并发送",
    suggestions: [
      {
        suggestion: "帮我写一份汽车分析报告",
        prompt:
          "请帮我写一份关于新能源汽车市场趋势的分析报告，包含市场规模、竞品格局和投资建议。",
        icon: PenLineIcon,
      },
      {
        suggestion: "欢迎来到嘉鹿AI空间，美妙旅程一键开启！",
        prompt: "欢迎来到嘉鹿AI空间，美妙旅程一键开启！",
        icon: SparklesIcon,
      },
      {
        suggestion: "帮我制定一个AI学习计划",
        prompt:
          "请根据我目前的基础，帮我制定一份4周的AI学习计划，每周包含学习目标、实践任务和复盘要点。",
        icon: GraduationCapIcon,
      },
    ],
    suggestionsCreate: [
      {
        suggestion: "网页",
        prompt: "生成一个关于[主题]的网页",
        icon: CompassIcon,
      },
      {
        suggestion: "图片",
        prompt: "生成一个关于[主题]的图片",
        icon: ImageIcon,
      },
      {
        suggestion: "视频",
        prompt: "生成一个关于[主题]的视频",
        icon: VideoIcon,
      },
      {
        type: "separator",
      },
      {
        suggestion: "技能",
        prompt:
          "我们一起用 skill-creator 技能来创建一个技能吧。先问问我希望这个技能能做什么。",
        icon: SparklesIcon,
      },
    ],
  },

  // Sidebar
  sidebar: {
    newChat: "新建对话",
    chats: "对话",
    recentChats: "最近的对话",
    demoChats: "演示对话",
    agents: "智能体",
    noHistory: "暂无历史对话",
    login: "登录",
    loggedIn: "已登录",
    loginDialog: {
      title: "账号登录",
      description: "请输入账号和密码完成登录。",
      username: "账号",
      usernamePlaceholder: "请输入账号",
      password: "密码",
      passwordPlaceholder: "请输入密码",
      captcha: "验证码",
      captchaPlaceholder: "请输入验证码",
      refreshCaptcha: "刷新",
      captchaLoading: "验证码加载中...",
      captchaImageAlt: "图形验证码",
      submit: "登录",
      submitting: "登录中...",
      tenantTitle: "选择您的企业",
      tenantDescription: "请选择本次登录使用的企业。",
      tenantFallbackName: "企业",
      tenantDisabled: "已禁用",
      back: "返回",
      confirmLogin: "确认登录",
      success: "登录成功",
      alreadyLoggedIn: "当前已登录",
      validationRequired: "请输入账号和密码",
      validationCaptchaRequired: "请输入验证码",
      validationCaptchaRandomStrRequired:
        "验证码上下文已失效，请刷新验证码后重试",
      validationTenantRequired: "请选择企业",
      validationTenantDisabled: "该企业已禁用，请选择其他企业",
    },
  },

  // Agents
  agents: {
    title: "智能体",
    description: "创建和管理具有专属 Prompt 与能力的自定义智能体。",
    newAgent: "新建智能体",
    emptyTitle: "还没有自定义智能体",
    emptyDescription: "创建你的第一个自定义智能体，设置专属系统提示词。",
    chat: "对话",
    delete: "删除",
    deleteConfirm: "确定要删除该智能体吗？此操作不可撤销。",
    deleteSuccess: "智能体已删除",
    newChat: "新对话",
    createPageTitle: "设计你的智能体",
    createPageSubtitle: "描述你想要的智能体，我来帮你通过对话创建。",
    nameStepTitle: "给新智能体起个名字",
    nameStepHint:
      "只允许字母、数字和连字符，存储时自动转为小写（例如 code-reviewer）",
    nameStepPlaceholder: "例如 code-reviewer",
    nameStepContinue: "继续",
    nameStepInvalidError: "名称无效，只允许字母、数字和连字符",
    nameStepAlreadyExistsError: "已存在同名智能体",
    nameStepNetworkError: "网络请求失败，请检查网络或后端连接",
    nameStepCheckError: "无法验证名称可用性，请稍后重试",
    nameStepBootstrapMessage:
      "新智能体的名称是 {name}，现在开始为它生成 **SOUL**。",
    save: "保存智能体",
    saving: "正在保存智能体...",
    saveRequested: "已提交保存请求，鹿宝正在根据当前对话生成并保存初版智能体。",
    saveHint:
      "你可以在右上角的菜单里随时保存这个智能体，就算目前还只是初稿也可以。",
    saveCommandMessage:
      "请现在根据我们目前已经讨论的全部内容保存这个自定义智能体。这就是我明确的保存确认。如果仍有少量细节缺失，请根据上下文做出合理假设，生成一份简洁的英文初始 SOUL.md，并直接调用 setup_agent，不要再向我索要额外确认。",
    agentCreatedPendingRefresh:
      "智能体已创建，但鹿宝暂时还无法读取到它。请稍后刷新当前页面。",
    more: "更多操作",
    agentCreated: "智能体已创建！",
    startChatting: "开始对话",
    backToGallery: "返回 Gallery",
  },

  // Breadcrumb
  breadcrumb: {
    workspace: "工作区",
    chats: "对话",
  },

  // Workspace
  workspace: {
    officialWebsite: "访问鹿宝官方网站",
    githubTooltip: "访问鹿宝的 Github 仓库",
    settingsAndMore: "设置和更多",
    visitGithub: "在 Github 上查看鹿宝",
    reportIssue: "报告问题",
    contactUs: "联系我们",
    about: "关于嘉鹿集团",
    generatedDisclaimer: "内容由 AI 生成，请仔细甄别",
    logout: "退出登录",
    logoutConfirmTitle: "确认退出登录？",
    logoutConfirmDescription: "退出后将清除当前设备上的登录态和权限信息。",
    logoutSuccess: "已退出登录",
    logoutSubmitting: "退出中...",
    logoutRemoteFailedLocalCleared: "服务端退出失败，但已清除本地登录态",
    notLoggedIn: "当前未登录",
    noAiChatPermission: "暂无 AI 智能对话权限，请联系管理员开通。",
    permissionsLoading: "正在加载权限，请稍候...",
    permissionsLoadFailed: "权限加载失败，请刷新页面或重新登录。",
  },

  // Conversation
  conversation: {
    noMessages: "还没有消息",
    startConversation: "开始新的对话以查看消息",
  },

  // Chats
  chats: {
    searchChats: "搜索对话",
  },

  // Page titles (document title)
  pages: {
    appName: "鹿宝",
    chats: "对话",
    newChat: "新对话",
    untitled: "未命名",
  },

  // Tool calls
  toolCalls: {
    moreSteps: (count: number) => `查看其他 ${count} 个步骤`,
    lessSteps: "隐藏步骤",
    executeCommand: "执行命令",
    presentFiles: "展示文件",
    needYourHelp: "需要你的协助",
    useTool: (toolName: string) => `使用 “${toolName}” 工具`,
    searchFor: (query: string) => `搜索 “${query}”`,
    searchForRelatedInfo: "搜索相关信息",
    searchForRelatedImages: "搜索相关图片",
    searchForRelatedImagesFor: (query: string) => `搜索相关图片 “${query}”`,
    searchOnWebFor: (query: string) => `在网络上搜索 “${query}”`,
    viewWebPage: "查看网页",
    listFolder: "列出文件夹",
    readFile: "读取文件",
    writeFile: "写入文件",
    clickToViewContent: "点击查看文件内容",
    writeTodos: "更新 To-do 列表",
    skillInstallTooltip: "安装技能并使其可在鹿宝中使用",
  },

  uploads: {
    uploading: "上传中...",
    uploadingFiles: "文件上传中，请稍候...",
  },

  subtasks: {
    subtask: "子任务",
    executing: (count: number) =>
      `${count > 1 ? "并行" : ""}执行 ${count} 个子任务`,
    in_progress: "子任务运行中",
    completed: "子任务已完成",
    failed: "子任务失败",
  },

  // Token Usage
  tokenUsage: {
    title: "Token 用量",
    label: "Tokens",
    input: "输入",
    output: "输出",
    total: "总计",
    unavailable:
      "暂无 Token 用量。只有模型成功返回且供应商提供 usage_metadata 时才会显示。",
    unavailableShort: "未返回用量",
  },

  // Shortcuts
  shortcuts: {
    searchActions: "搜索操作...",
    noResults: "未找到结果。",
    actions: "操作",
    keyboardShortcuts: "键盘快捷键",
    keyboardShortcutsDescription: "使用键盘快捷键更快地操作鹿宝。",
    openCommandPalette: "打开命令面板",
    toggleSidebar: "切换侧边栏",
  },

  // Settings
  settings: {
    title: "设置",
    description: "根据你的偏好调整鹿宝的界面和行为。",
    sections: {
      appearance: "外观",
      memory: "记忆",
      tools: "工具",
      skills: "技能",
      notification: "通知",
      about: "关于",
    },
    memory: {
      title: "记忆",
      description:
        "鹿宝会在后台不断从你的对话中自动学习。这些记忆能帮助鹿宝更好地理解你，并提供更个性化的体验。",
      empty: "暂无可展示的记忆数据。",
      rawJson: "原始 JSON",
      exportButton: "导出记忆",
      exportSuccess: "记忆已导出",
      importButton: "导入记忆",
      importConfirmTitle: "导入记忆？",
      importConfirmDescription: "这会用选中的 JSON 备份覆盖当前记忆。",
      importFileLabel: "已选择文件",
      importInvalidFile: "读取记忆文件失败，请选择有效的 JSON 导出文件。",
      importSuccess: "记忆已导入",
      manualFactSource: "手动添加",
      addFact: "添加事实",
      addFactTitle: "添加记忆事实",
      editFactTitle: "编辑记忆事实",
      addFactSuccess: "事实已创建",
      editFactSuccess: "事实已更新",
      clearAll: "清空全部记忆",
      clearAllConfirmTitle: "要清空全部记忆吗？",
      clearAllConfirmDescription:
        "这会删除所有已保存的摘要和事实。此操作无法撤销。",
      clearAllSuccess: "已清空全部记忆",
      factDeleteConfirmTitle: "要删除这条事实吗？",
      factDeleteConfirmDescription:
        "这条事实会立即从记忆中删除。此操作无法撤销。",
      factDeleteSuccess: "事实已删除",
      factContentLabel: "内容",
      factCategoryLabel: "类别",
      factConfidenceLabel: "置信度",
      factContentPlaceholder: "描述你想保存的记忆事实",
      factCategoryPlaceholder: "context",
      factConfidenceHint: "请输入 0 到 1 之间的数字。",
      factSave: "保存事实",
      factValidationContent: "事实内容不能为空。",
      factValidationConfidence: "置信度必须是 0 到 1 之间的数字。",
      noFacts: "还没有保存的事实。",
      summaryReadOnly:
        "摘要分区当前仍为只读。现在你可以清空全部记忆或删除单条事实。",
      memoryFullyEmpty: "还没有保存任何记忆。",
      factPreviewLabel: "即将删除的事实",
      searchPlaceholder: "搜索记忆",
      filterAll: "全部",
      filterFacts: "事实",
      filterSummaries: "摘要",
      noMatches: "没有找到匹配的记忆。",
      conventions: {
        title: "工程约定",
        description: "包含仓库基线约定与当前会话中沉淀的增量约定。",
        repoTitle: "仓库基线约定",
        sessionTitle: "会话增量约定",
        empty: "当前还没有会话增量约定。",
        add: "新增约定",
        edit: "编辑约定",
        save: "保存约定",
        deleteSuccess: "约定已删除",
        topicLabel: "主题",
        topicPlaceholder: "例如：状态管理、命名、API 契约",
        contentLabel: "约定内容",
        contentPlaceholder: "填写可复用、可执行的约定内容。",
        validationTopic: "主题不能为空。",
        validationContent: "约定内容不能为空。",
        exportButton: "导出约定",
        importButton: "导入约定",
        exportSuccess: "约定已导出",
        importSuccess: "约定已导入",
        importInvalidFile: "读取约定文件失败，请选择有效的 JSON 导出文件。",
        importConfirmTitle: "导入约定？",
        importConfirmDescription: "导入的会话约定会合并到当前会话约定中。",
        conflictTitle: "冲突处理",
        conflictDescription: "检测到同主题但内容不同的约定，请选择合并策略。",
        resolutionKeep: "保留现有",
        resolutionIncoming: "使用导入内容",
        resolutionMerge: "合并两者",
        sourceRepo: "仓库",
        sourceSession: "会话",
        deltaLabel: "本轮对话增量约定摘要",
        deltaPlaceholder: "总结本轮对话新增或修订的关键约定。",
        deltaSave: "保存本轮摘要",
        deltaSaveSuccess: "本轮摘要已保存",
      },
      markdown: {
        overview: "概览",
        userContext: "用户上下文",
        work: "工作",
        personal: "个人",
        topOfMind: "近期关注（Top of mind）",
        historyBackground: "历史背景",
        recentMonths: "近几个月",
        earlierContext: "更早上下文",
        longTermBackground: "长期背景",
        updatedAt: "更新于",
        facts: "事实",
        empty: "（空）",
        table: {
          category: "类别",
          confidence: "置信度",
          confidenceLevel: {
            veryHigh: "极高",
            high: "较高",
            normal: "一般",
            unknown: "未知",
          },
          content: "内容",
          source: "来源",
          createdAt: "创建时间",
          view: "查看",
        },
      },
    },
    appearance: {
      themeTitle: "主题",
      themeDescription: "跟随系统或选择固定的界面模式。",
      system: "系统",
      light: "浅色",
      dark: "深色",
      systemDescription: "自动跟随系统主题。",
      lightDescription: "更明亮的配色，适合日间使用。",
      darkDescription: "更暗的配色，减少眩光方便专注。",
      languageTitle: "语言",
      languageDescription: "在不同语言之间切换。",
    },
    tools: {
      title: "工具",
      description: "管理 MCP 工具的配置和启用状态。",
    },
    skills: {
      title: "技能",
      description: "管理 Agent Skill 配置和启用状态。",
      createSkill: "新建技能",
      emptyTitle: "还没有技能",
      emptyDescription:
        "将你的 Agent Skill 文件夹放在鹿宝根目录下的 `/skills/custom` 文件夹中。",
      emptyButton: "创建你的第一个技能",
    },
    notification: {
      title: "通知",
      description:
        "鹿宝只会在窗口不活跃时发送完成通知，特别适合长时间任务：你可以先去做别的事，完成后会收到提醒。",
      requestPermission: "请求通知权限",
      deniedHint:
        "通知权限已被拒绝。可在浏览器的网站设置中重新开启，以接收完成提醒。",
      testButton: "发送测试通知",
      testTitle: "鹿宝",
      testBody: "这是一条测试通知。",
      notSupported: "当前浏览器不支持通知功能。",
      disableNotification: "关闭通知",
    },
    acknowledge: {
      emptyTitle: "致谢",
      emptyDescription: "相关的致谢信息会展示在这里。",
    },
  },
};
