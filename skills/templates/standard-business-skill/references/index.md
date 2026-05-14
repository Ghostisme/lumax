# 标准业务 Skill 能力索引

复制模板后，用真实业务能力替换下表，并保持 reference、rule 和 endpoint 脚本一一对应。

| 能力 | 类型 | Reference | Rule | Script |
| --- | --- | --- | --- | --- |
| 读取示例 | read | `references/read-example.md` | `rules/read-example.json` | `scripts/endpoints/read_example.py` |
| 增删改示例 | mutation | `references/mutation-example.md` | `rules/mutation-example.json` | `scripts/endpoints/mutation_example.py` |
| 批量示例 | batch | `references/batch-example.md` | `rules/batch-example.json` | `scripts/endpoints/batch_example.py` |

维护要求：

- 新增能力时必须同步新增 reference、rule 和 endpoint 脚本。
- 删除能力时必须同步移除索引项，避免主 Agent 调度到不存在的文件。
- 每个 reference 应说明用户可输入字段、业务含义、示例和错误处理。
