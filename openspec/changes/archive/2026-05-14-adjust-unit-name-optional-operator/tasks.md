# 任务清单

## 1. 规格确认

- [x] 1.1 确认 `openspec/project.md` 与 `openspec/AGENTS.md` 在当前分支不存在时，以根 `AGENTS.md` 和现有 specs 为约束来源。
- [x] 1.2 读取 `oceanengine-local-unit-management` 中单元名称生成规则。
- [x] 1.3 确认本次范围只调整默认单元名称的投手后缀可选逻辑。

## 2. 测试先行

- [x] 2.1 增加 `build_default_unit_name()` 有投手姓名时仍追加投手首字母的回归测试。
- [x] 2.2 增加缺少 `operator_name`、`operator_name=None`、`operator_name=""` 时不追加任何投手占位符的测试。
- [x] 2.3 增加 `unit_name` 明确传入时仍覆盖默认规则的测试。

## 3. 实现

- [x] 3.1 调整 `tools/oceanengine_local_project_create_flow.py` 中默认单元名称生成逻辑，使投手首字母后缀仅在拿到非空投手姓名时追加。
- [x] 3.2 保持现有日期、地域、定向类型和年龄拼接规则不变。
- [x] 3.3 保持 `operator_name` 不进入 `localProjectCreate` payload。

## 4. 验证

- [x] 4.1 运行项目创建流程聚焦测试。
- [x] 4.2 运行相关素材管理、单元管理和结构化追问回归测试。
- [x] 4.3 运行 `openspec validate adjust-unit-name-optional-operator --strict`。
- [x] 4.4 本次未涉及浏览器验收；已通过单元测试确认默认名称在无投手姓名时不出现 `X`、`None`、`null`、`未知` 等投手占位符。

## 5. 扩展规格：项目名与单元名一致

- [x] 5.1 更新项目管理规格，明确默认项目名使用与单元名一致的命名规则。
- [x] 5.2 更新单元管理规格，明确未显式提供 `unit_name` 时默认复用项目名。
- [x] 5.3 运行 `openspec validate adjust-unit-name-optional-operator --strict`。

## 6. 扩展测试先行

- [x] 6.1 增加测试：用户未提供 `name` / `unit_name` 时，`project_payload.name` 与 `unit_plan.name` 默认一致。
- [x] 6.2 增加测试：用户只提供 `name` 时，`unit_plan.name` 默认复用 `name`。
- [x] 6.3 增加测试：用户同时提供 `name` 和 `unit_name` 时，项目名使用 `name`，单元名使用 `unit_name`。
- [x] 6.4 增加测试：默认项目名缺少投手姓名时不追加 `X`、`None`、`null`、`未知` 等占位符。

## 7. 扩展实现与验证

- [x] 7.1 调整 `tools/oceanengine_local_project_create_flow.py`，让项目名默认走同一套命名函数。
- [x] 7.2 调整单元名生成优先级：`unit_name` > `name` > 默认命名。
- [x] 7.3 保持用户显式项目名不被默认命名覆盖。
- [x] 7.4 运行项目创建流程聚焦测试和相关回归测试。
- [x] 7.5 更新验证记录。

## 验证记录

- `PYTHONPATH=. uv run --project backend python -m pytest backend/tests/test_oceanengine_local_project_create_flow.py::test_create_flow_default_unit_name_omits_operator_suffix_when_operator_is_missing_or_blank backend/tests/test_oceanengine_local_project_create_flow.py::test_create_flow_default_unit_name_uses_current_date_region_audience_age_and_operator_initials backend/tests/test_oceanengine_local_project_create_flow.py::test_create_flow_explicit_unit_name_overrides_default_rule -q`：先失败 1 个用例，确认缺投手场景当前不满足；实现后 3 passed。
- `openspec validate adjust-unit-name-optional-operator --strict`：valid。
- `PYTHONPATH=. uv run --project backend python -m pytest backend/tests/test_oceanengine_local_project_create_flow.py backend/tests/test_oceanengine_local_material_native_tool.py backend/tests/test_oceanengine_local_unit_native_tool.py backend/tests/test_oceanengine_single_question_clarification.py backend/tests/test_oceanengine_dependent_clarification_options.py -q`：163 passed。
- `PYTHONPATH=. uv run --project backend ruff check tools/oceanengine_local_project_create_flow.py backend/tests/test_oceanengine_local_project_create_flow.py`：All checks passed。
- `git diff --check`：通过。
- `PYTHONPATH=. uv run --project backend python -m pytest backend/tests/test_oceanengine_local_project_create_flow.py::test_create_flow_defaults_project_name_and_unit_name_to_same_generated_name backend/tests/test_oceanengine_local_project_create_flow.py::test_create_flow_uses_explicit_project_name_as_default_unit_name backend/tests/test_oceanengine_local_project_create_flow.py::test_create_flow_preserves_explicit_project_name_and_explicit_unit_name_separately backend/tests/test_oceanengine_local_project_create_flow.py::test_create_flow_default_project_name_omits_operator_placeholder_when_operator_missing -q`：先失败 3 个用例，确认当前缺少默认项目名和单元名复用项目名逻辑；实现后相关 5 个命名用例通过。
- `openspec validate adjust-unit-name-optional-operator --strict`：valid。
- `PYTHONPATH=. uv run --project backend python -m pytest backend/tests/test_oceanengine_local_project_create_flow.py backend/tests/test_oceanengine_local_material_native_tool.py backend/tests/test_oceanengine_local_unit_native_tool.py backend/tests/test_oceanengine_single_question_clarification.py backend/tests/test_oceanengine_dependent_clarification_options.py -q`：167 passed。
- `PYTHONPATH=. uv run --project backend ruff check tools/oceanengine_local_project_create_flow.py backend/tests/test_oceanengine_local_project_create_flow.py`：All checks passed。
- `git diff --check`：通过。
