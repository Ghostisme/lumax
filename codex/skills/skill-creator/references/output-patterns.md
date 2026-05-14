# 输出模式

当一个 skill 需要稳定地产出高质量结果时，可以复用这些输出模式。

## 模板模式

如果输出格式很重要，就给出模板。模板的严格程度要和任务风险匹配。

### 严格模板

适用于 API 响应、结构化文档、固定报告格式等：

```markdown
## 报告结构

必须严格使用以下结构：

# [分析标题]

## Executive summary
[一段总结]

## Key findings
- 发现 1
- 发现 2
- 发现 3

## Recommendations
1. 建议 1
2. 建议 2
```

### 弹性模板

适用于需要根据上下文调整结构的任务：

```markdown
## 报告结构

以下是建议默认结构，可根据实际情况调整：

# [分析标题]

## Executive summary
[概述]

## Key findings
[根据实际发现调整小节]

## Recommendations
[结合具体场景给建议]
```

## 示例模式

如果输出质量高度依赖示例，优先提供输入 / 输出对：

```markdown
## Commit message 格式

按以下示例生成：

**示例 1：**
Input: Added user authentication with JWT tokens
Output:
```
feat(auth): implement JWT-based authentication

Add login endpoint and token validation middleware
```
```

示例通常比抽象描述更能帮助模型把握风格、粒度和结构。
