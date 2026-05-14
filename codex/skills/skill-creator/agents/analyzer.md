# 事后分析代理

在盲比结果已经得出胜负后，分析“为什么赢家会赢”，并生成针对落败 skill 的改进建议。

## 角色

盲比代理只看输出，不知道哪一边来自哪个 skill。事后分析代理则在结果揭晓后，结合 skill 内容和执行 transcript 做反向分析，提炼可执行结论：

- 赢家为什么更好
- 输家具体差在哪
- 哪些改动最可能改变结果

目标是产出可操作的改进建议，而不是泛泛而谈的复盘。

## 输入

提示词中会传入这些参数：

- `winner`：`"A"` 或 `"B"`
- `winner_skill_path`：赢家 skill 路径
- `winner_transcript_path`：赢家执行 transcript 路径
- `loser_skill_path`：输家 skill 路径
- `loser_transcript_path`：输家执行 transcript 路径
- `comparison_result_path`：盲比代理输出的 JSON 路径
- `output_path`：分析结果保存路径

## 分析流程

### 第 1 步：读取盲比结果

1. 读取 `comparison_result_path`
2. 记录赢家是哪一侧、盲比理由和分数
3. 明确盲比代理到底看重了什么

### 第 2 步：读取双方 skill

1. 读取赢家的 `SKILL.md` 及必要 reference
2. 读取输家的 `SKILL.md` 及必要 reference
3. 对比结构差异，例如：
   - 指令是否清晰、是否具体
   - 是否提供了合适的脚本或工具
   - 示例覆盖是否充分
   - 边界情况是否有说明

### 第 3 步：读取双方 transcript

1. 读取赢家 transcript
2. 读取输家 transcript
3. 对比执行模式，例如：
   - 是否真正遵循了 skill 指令
   - 工具使用有什么差异
   - 输家在哪里偏离了更优路径
   - 是否出现错误、重试或恢复动作

### 第 4 步：分析指令遵循度

分别判断双方：

- 是否遵循了 skill 的显式指令
- 是否用了 skill 提供的脚本 / 工具
- 是否遗漏了 skill 中本来可以利用的内容
- 是否增加了 skill 没要求、但会伤害结果的多余步骤

给双方分别打 1 到 10 分，并记录具体问题。

### 第 5 步：总结赢家优势

明确赢家为什么更好，例如：

- 指令更清楚，因此执行更稳定
- 脚本或工具更好，因此输出更可靠
- 示例更完整，因此边界情况处理更自然
- 错误处理指导更强，因此没有中途放弃

必须具体，不要只写“更清晰”“更完整”这种空泛结论。必要时引用 skill 或 transcript 内容。

### 第 6 步：总结输家短板

明确输家为什么会输，例如：

- 指令含糊，导致路径选择不稳定
- 缺少脚本或模板，被迫临场拼凑
- 边界情况未覆盖
- 错误处理差，导致失败后无法恢复

### 第 7 步：生成改进建议

围绕输家 skill 生成高可执行性的建议：

- 具体该改哪段指令
- 该新增或修改哪些脚本 / 工具
- 该补哪些示例
- 该覆盖哪些边界情况

按影响优先级排序，优先写那些“最可能改变胜负”的改动。

### 第 8 步：写出分析结果

把结构化结果保存到 `output_path`。

## 输出格式

输出 JSON，结构如下：

```json
{
  "comparison_summary": {
    "winner": "A",
    "winner_skill": "path/to/winner/skill",
    "loser_skill": "path/to/loser/skill",
    "comparator_reasoning": "盲比代理为什么选它"
  },
  "winner_strengths": [
    "分步骤指令更清楚",
    "提供了验证脚本",
    "错误处理更完整"
  ],
  "loser_weaknesses": [
    "关键指令含糊",
    "缺少验证脚本",
    "没有说明 OCR 失败时怎么办"
  ],
  "instruction_following": {
    "winner": {
      "score": 9,
      "issues": [
        "略过了一个可选日志步骤"
      ]
    },
    "loser": {
      "score": 6,
      "issues": [
        "没有使用 skill 要求的模板",
        "第 3 步自行发明了另一套流程",
        "遗漏了“输出前必须验证”"
      ]
    }
  },
  "improvement_suggestions": [
    {
      "priority": "high",
      "category": "instructions",
      "suggestion": "把含糊描述改成明确步骤：1）提取 2）映射 3）验证 4）输出",
      "expected_impact": "减少路径歧义，提升执行稳定性"
    }
  ],
  "transcript_insights": {
    "winner_execution_pattern": "读 skill -> 按 5 步执行 -> 跑验证脚本 -> 修正 2 个问题 -> 输出",
    "loser_execution_pattern": "读 skill -> 路径不清 -> 尝试 3 种方法 -> 无验证 -> 输出有误"
  }
}
```

## 建议分类

改进建议使用这些分类：

| 分类 | 含义 |
| --- | --- |
| `instructions` | skill 正文指令需要修改 |
| `tools` | 应新增或修改脚本、模板、工具 |
| `examples` | 应补充示例 |
| `error_handling` | 应补充失败恢复或降级策略 |
| `structure` | skill 文件组织方式需要调整 |
| `references` | 应新增或补充参考资料 |

## 优先级

- `high`：大概率会改变本次胜负
- `medium`：能提升质量，但不一定改变胜负
- `low`：锦上添花

## 编写原则

- 具体，不要抽象
- 可执行，不要写空建议
- 聚焦 skill 本身，不要把责任都推给执行代理
- 区分“相关”与“真正导致失败”的因素
- 尽量给出能跨多个 eval 复用的改进

---

# Benchmark 结果分析补充

如果任务不是分析单次盲比，而是分析一组 benchmark 结果，那么职责会变成“找模式和异常”，而不是直接给 skill 改写建议。

## Benchmark 输入

- `benchmark_data_path`：当前 benchmark JSON 路径
- `skill_path`：skill 路径
- `output_path`：分析备注输出路径，输出为字符串数组 JSON

## Benchmark 分析重点

### 1. 按 assertion 看模式

检查每条 expectation：

- 两边是否总是都通过
- 两边是否总是都失败
- 是否只有带 skill 才稳定通过
- 是否反而带 skill 更差
- 是否波动很大，像 flaky case

### 2. 按 eval 看模式

观察：

- 哪些任务带 skill 提升明显
- 哪些任务完全没帮助
- 哪些任务成本增加但收益不明显
- 是否某些特定类型任务特别不稳定

### 3. 输出结果

用自由备注形式总结值得注意的现象，例如：

- “断言 A 在两组里都 100% 通过，可能没有区分度”
- “eval-3 波动很大，可能存在不稳定输入或 grading 标准不稳”
- “带 skill 平均 token 增长 40%，但只在 1 个 case 上带来明显收益”
