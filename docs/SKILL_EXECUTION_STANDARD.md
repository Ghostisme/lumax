# DeerFlow 标准 Skill 执行架构

本文档是后续业务 custom skill 的开发规范。目标是让主 Agent 只负责用户交互和 skill 调度，把复杂业务校验、MCP 请求构造和执行结果包装收敛到 skill 内部的规则配置与 Python 脚本中。

## 适用范围

适用于需要调用 MCP、外部业务接口或执行确定性参数校验的 custom skill。简单的说明类、写作类或不调用业务系统的 public skill 可以不完整套用，但不能借此绕过真实业务请求的本地校验。

## 职责边界

| 模块 | 职责 | 禁止事项 |
| --- | --- | --- |
| 主 Agent | 接收用户请求、识别 intent、收集入参、选择 skill、调用脚本、转述结构化结果 | 不做复杂业务规则推理；不编造默认业务参数；不绕过脚本直接调用 MCP |
| `SKILL.md` | 说明触发条件、最小流程、文件导航、脚本入口和安全禁令 | 不塞入全部接口参数；不手写大量枚举；不让模型自由拼接请求 |
| `references/` | 存放接口说明、字段解释、示例和维护说明 | 不作为最终校验来源；不替代机器可读规则配置 |
| `rules/` | 存放参数、枚举、依赖、约束、MCP 映射和确认规则 | 不保存无法执行的自然语言规则；不留下会被误用的空规则 |
| `scripts/` | 读取规则、执行本地硬校验、构造 MCP 请求、包装结果 | 校验失败时不调用 MCP；不把业务合法性判断交给大模型 |

## 标准目录结构

```text
skills/custom/<skill-name>/
├── SKILL.md
├── references/
│   ├── index.md
│   └── <capability>.md
├── rules/
│   ├── index.json
│   ├── <read-capability>.json
│   ├── <mutation-capability>.json
│   └── <batch-capability>.json
└── scripts/
    ├── common/
    │   ├── validators.py
    │   ├── mcp_client.py
    │   ├── response.py
    │   └── runner.py
    └── endpoints/
        └── <capability>.py
```

命名要求：

- skill 目录名与 frontmatter `name` 使用 kebab-case。
- 脚本文件使用 snake_case，并与 capability 一一对应。
- reference 和 rule 文件使用 kebab-case，并能从 `references/index.md` 与 `rules/index.json` 定位。
- 输出字段保留稳定英文键，例如 `success`、`message`、`data`、`errors`、`tool_name`、`request_id`、`retry_count`。

## 标准执行流程

1. 主 Agent 根据用户请求选择 skill。
2. 主 Agent 读取 `SKILL.md`，再读取命中的 reference 和 rule 文件。
3. 主 Agent 将用户输入整理为 JSON，传给对应 Python 脚本。
4. Python 脚本读取 `rules/<capability>.json`。
5. Python 脚本执行本地硬校验：必填、类型、枚举、条件必填、条件禁止、互斥、范围、批量项和字段映射。
6. 校验失败时，脚本返回 `success=false` 和中文 `errors`，主 Agent 直接反馈用户补填或修改。
7. 校验通过后，脚本按规则配置构造 MCP 请求并调用真实业务接口。
8. 脚本统一包装 MCP 响应。读取类返回查询摘要；增删改类必须按规则做后置确认。
9. 后置确认失败时，脚本返回失败或部分失败，并给出最后一次请求、查询摘要和不一致原因。

## 规则配置表字段

规则配置表使用 JSON，第一阶段减少依赖并方便脚本直接读取。

```json
{
  "schema_version": 1,
  "name": "list-projects",
  "title": "获取项目列表",
  "operation_type": "read",
  "mcp": {
    "server": "platform-agent-biz",
    "tool": "localProjectList",
    "field_map": {
      "local_account_id": "localAccountId"
    },
    "value_maps": {
      "status": {
        "ENABLE": "ENABLE"
      }
    }
  },
  "parameters": [
    {
      "name": "local_account_id",
      "label": "本地推账户 ID",
      "type": "integer",
      "required": true
    }
  ],
  "constraints": [],
  "output": {
    "success_fields": ["project_id", "name"]
  }
}
```

字段约定：

- `schema_version`：规则配置版本，当前为 `1`。
- `name`：能力唯一标识，kebab-case。
- `title`：中文能力名称。
- `operation_type`：`read`、`mutation` 或 `batch`。
- `mcp.server`：目标 MCP 服务名。
- `mcp.tool`：优先使用的 MCP 工具名；如果只能运行时匹配，可用 `mcp.match_tokens`。
- `parameters[]`：用户可输入字段定义，必须包含 `name`、`label`、`type`。
- `constraints[]`：跨字段规则，例如 `conditional_required`、`forbidden_when`、`mutually_exclusive`、`range`。
- `batch`：批量能力的批量字段、项内 schema 和定位字段。
- `confirmation`：增删改类能力的后置查询确认配置。
- `output`：成功摘要和错误展示建议。

## 配置优先级

规则变化优先改 `rules/*.json`。只有新增通用规则类型、MCP 调用机制或输出协议时才改 `scripts/common/`。单个业务接口的特殊逻辑应先判断能否用 `constraints` 或 `confirmation` 表达，不能表达时再在对应 endpoint 脚本中做小范围扩展。

## 结构化响应协议

校验失败：

```json
{
  "success": false,
  "message": "参数校验失败，请根据中文提示补充或修改后重试。",
  "errors": [
    {
      "field": "local_account_id",
      "message": "本地推账户 ID 为必填字段，请补充后再执行。"
    }
  ],
  "data": {
    "capability": "list-projects"
  }
}
```

调用成功：

```json
{
  "success": true,
  "message": "获取项目列表调用完成。",
  "data": {
    "result": {}
  },
  "tool_name": "localProjectList",
  "request_id": "request-001",
  "retry_count": 0
}
```

批量失败项应使用 `errors[].item_index` 或业务标识定位具体输入项。

## 后置确认

`operation_type=mutation` 或真实改变业务状态的 `batch` 能力必须配置或实现后置确认。确认规则至少包含：

- `confirmation.enabled=true`
- `confirmation.query_capability`
- `confirmation.match_fields`
- `confirmation.max_retries`

达到重试上限仍不一致时，不得声称业务成功。脚本必须返回最后一次请求摘要、查询摘要和不一致原因。

## 自检命令

新增或修改规则配置后运行：

```bash
python3 scripts/skill_rule_config_validator.py skills/templates/standard-business-skill/rules/read-example.json skills/templates/standard-business-skill/rules/mutation-example.json skills/templates/standard-business-skill/rules/batch-example.json
```

后端测试中覆盖了必需字段、枚举重复、依赖字段引用和批量项定位。新增规则类型时应同步补充测试。

## 现有样板核对

`skills/custom/oceanengine-local-project/` 已符合以下标准：轻量 `SKILL.md`、接口级 reference、按接口拆分脚本、Python 本地校验、MCP 调用封装、中文结构化输出和增删改后置确认。

当前偏差：该样板把规则直接声明在 endpoint 脚本中，尚未拆到 `rules/*.json`。这个偏差不影响真实业务行为，应在后续维护或新增接口时逐步迁移，不在本次变更中做大范围重构。
