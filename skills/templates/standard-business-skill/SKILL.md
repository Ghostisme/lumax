---
name: standard-business-skill-template
description: Template for DeerFlow custom skills that validate structured inputs locally and call MCP tools through native DeerFlow business tools.
---

# 标准业务 Skill 模板

本模板用于创建需要调用 MCP 的业务 custom skill。复制到 `skills/custom/<skill-name>/` 后，必须替换 frontmatter `name`、`description`、接口导航、规则配置和 DeerFlow 原生业务工具入口。

## 使用流程

1. 判断用户意图，读取 `references/index.md` 定位能力、reference、rule 和 capability。
2. 只读取当前能力对应的 reference 与 rule 文件。
3. 将用户输入整理为 JSON，调用对应 DeerFlow 原生业务工具。
4. 参数不足或不合法时，直接反馈业务工具返回的中文 `errors`。
5. 校验通过后由业务工具调用 MCP；不要绕过业务工具直接调用底层 MCP 工具。
6. 增删改类能力必须让业务工具执行后置确认，确认失败不得声称业务成功。

## 原生业务工具入口

运行时应通过 `config.yaml.tools[]` 注册的 DeerFlow 原生业务工具执行真实业务请求。

```json
{
  "capability": "<capability>",
  "payload_json": "{\"account_id\":123456}",
  "dry_run": false
}
```

## 本地开发脚本入口

endpoint 脚本仅作为本地开发和回归测试入口：

```bash
python /mnt/skills/custom/<skill-name>/scripts/endpoints/<capability>.py --input '{"account_id":123456}'
```

本地开发可使用 dry-run 验证校验与请求构造：

```bash
python3 skills/custom/<skill-name>/scripts/endpoints/<capability>.py --input '{"account_id":123456}' --dry-run
```

## 文件导航

- 能力索引：`references/index.md`
- 规则索引：`rules/index.json`
- 读取类示例：`rules/read-example.json`
- 增删改类示例：`rules/mutation-example.json`
- 批量类示例：`rules/batch-example.json`
- 公共脚本说明：`scripts/common/README.md`
- Endpoint 脚本说明：`scripts/endpoints/README.md`

## 安全约束

- 主 Agent 只负责收集入参和调度原生业务工具。
- 原生业务工具是最终参数合法性判断来源。
- 校验失败时不得调用 MCP。
- 当前环境没有命令执行能力时，也不得直接调用 MCP 绕过业务工具。
