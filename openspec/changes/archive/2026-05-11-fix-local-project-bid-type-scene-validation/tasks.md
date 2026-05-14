# 任务清单

## 1. 规格确认

- [x] 1.1 确认本次范围仅覆盖 `create-project` 的 `bid_type` 与业务场景交叉校验。
- [x] 1.2 确认其它参数交叉校验问题不在本次实现范围内。
- [x] 1.3 运行 `openspec validate fix-local-project-bid-type-scene-validation --strict`。

## 2. 测试先行

- [x] 2.1 增加失败测试：`external_action=SHOW` 且 `bid_type` 不是 `MANUAL` 时，本地校验失败且不得调用 MCP。
- [x] 2.2 增加失败测试：`marketing_goal=LIVE` 且 `local_delivery_scene=CONTENT_HEAT` / `PRODUCT_PAY` 时，非 `SMART` 出价方式本地校验失败且不得调用 MCP。
- [x] 2.3 增加失败测试：`local_delivery_scene=EXTERNAL` 的非 UBL 场景传入非 `STABILIZE_COSTS` / `MAX_CONVERSION` 出价方式时，本地校验失败且不得调用 MCP。
- [x] 2.4 增加正向测试：代表性合法出价方式组合继续通过本地校验。

## 3. 实现

- [x] 3.1 在 `create-project` 规则中补充 `bid_type` 场景约束。
- [x] 3.2 如现有规则解释器无法表达该约束，最小扩展项目管理校验器，不引入其它参数行为变化。
- [x] 3.3 确保失败结果使用中文用户可见错误，并遵守一次只展示一个问题的现有规则。
- [x] 3.4 确保本地校验失败时不会构造或调用项目管理 MCP tool。

## 4. 验证

- [x] 4.1 运行本次新增或调整的项目管理参数校验定向测试。
- [x] 4.2 运行 `openspec validate fix-local-project-bid-type-scene-validation --strict`。
- [x] 4.3 按仓库规则运行 GitNexus 变更检测，确认受影响范围符合预期。

## 5. 交付前检查

- [x] 5.1 检查是否需要把新的长期规则沉淀到最近层级 `AGENTS.md`。
- [x] 5.2 记录实际验证命令和结果。
- [x] 5.3 本 change archive 前等待用户明确批准。

## 验证记录

- `PYTHONPATH=. backend/.venv/bin/python -m pytest backend/tests/test_oceanengine_local_project_rules.py -k 'unsupported_bid_type or supported_bid_type_scene' -q`：4 passed。
- `PYTHONPATH=. backend/.venv/bin/python -m pytest backend/tests/test_oceanengine_local_project_rules.py -q`：79 passed。
- `openspec validate fix-local-project-bid-type-scene-validation --strict`：valid。
- `gitnexus detect_changes(scope=unstaged, repo=lumax)`：risk_level=low，affected_count=0。
