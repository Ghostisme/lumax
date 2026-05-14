# JSON Schema 参考

本文档记录 `skill-creator` 常用的 JSON 文件结构，供你在做 eval、grading 和 benchmark 时参考。

---

## `evals/evals.json`

用于定义某个 skill 的 eval 集合。

```json
{
  "skill_name": "example-skill",
  "evals": [
    {
      "id": 1,
      "prompt": "用户任务提示词",
      "expected_output": "期望结果描述",
      "files": ["evals/files/sample1.pdf"],
      "expectations": [
        "输出包含 X",
        "skill 使用了脚本 Y"
      ]
    }
  ]
}
```

字段说明：

- `skill_name`：应与 skill frontmatter 中的 `name` 一致
- `evals[].id`：唯一整数 ID
- `evals[].prompt`：执行任务的用户提示词
- `evals[].expected_output`：人类可读的成功定义
- `evals[].files`：可选输入文件列表，相对 skill 根目录
- `evals[].expectations`：可验证的断言列表

---

## `history.json`

用于记录 Improve 模式中的版本演进。

```json
{
  "started_at": "2026-01-15T10:30:00Z",
  "skill_name": "pdf",
  "current_best": "v2",
  "iterations": [
    {
      "version": "v0",
      "parent": null,
      "expectation_pass_rate": 0.65,
      "grading_result": "baseline",
      "is_current_best": false
    }
  ]
}
```

字段说明：

- `started_at`：开始时间
- `skill_name`：skill 名称
- `current_best`：当前表现最好的版本
- `iterations[].version`：版本号
- `iterations[].parent`：来源版本
- `iterations[].expectation_pass_rate`：评分通过率
- `iterations[].grading_result`：`baseline` / `won` / `lost` / `tie`
- `iterations[].is_current_best`：是否当前最佳

---

## `grading.json`

评分代理输出结果。

```json
{
  "expectations": [
    {
      "text": "输出包含姓名 'John Smith'",
      "passed": true,
      "evidence": "Transcript 第 3 步提到提取到该姓名"
    }
  ],
  "summary": {
    "passed": 1,
    "failed": 0,
    "total": 1,
    "pass_rate": 1.0
  }
}
```

常见字段：

- `expectations[]`：每条 expectation 的评分结果
- `summary`：通过率汇总
- `execution_metrics`：执行期指标
- `timing`：耗时信息
- `claims`：从输出里抽取并验证的 claim
- `user_notes_summary`：执行者备注摘要
- `eval_feedback`：对 eval 设计的改进建议

---

## `metrics.json`

执行代理输出的过程指标。

```json
{
  "tool_calls": {
    "Read": 5,
    "Write": 2,
    "Bash": 8
  },
  "total_tool_calls": 15,
  "total_steps": 6,
  "errors_encountered": 0,
  "output_chars": 12450,
  "transcript_chars": 3200
}
```

---

## `timing.json`

记录单次运行的 wall clock 时间。

```json
{
  "total_tokens": 84852,
  "duration_ms": 23332,
  "total_duration_seconds": 23.3
}
```

注意：

- 子代理完成时出现的 `duration_ms` / `total_tokens` 要及时保存
- 这些信息往往不会在别处持久化

---

## `benchmark.json`

用于汇总多轮 eval 的总体结果。

实际字段可能会根据聚合脚本演进，但至少应能表达这些信息：

- 不同配置（如 `with_skill` / `without_skill`）的结果
- 每个 eval 的通过率
- 时间和 token 成本
- 均值、方差或标准差
- 差异结论

如果你不是直接使用现成聚合脚本，生成 benchmark 前先检查当前 viewer 期待的字段结构。
