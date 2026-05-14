from unittest.mock import patch

from tools.oceanengine_local_project_runtime.mutation_confirm import confirm_mutation


def test_created_project_confirmation_uses_configured_fields_only():
    spec = {
        "title": "创建项目",
        "confirmation": {
            "mode": "created_project",
            "fields": ["name"],
        },
    }
    payload = {
        "local_account_id": 1854708763953159,
        "name": "Codex验收测试0506-1912",
        "delivery_goal": "PRODUCT",
        "budget_mode": "BUDGET_MODE_DAY",
        "start_time": "2026-05-07",
        "end_time": "2026-05-08",
    }
    mutation_result = {
        "raw": {
            "data": {
                "data": {
                    "projectId": 7636654872435884074,
                }
            }
        }
    }
    detail_result = {
        "raw": {
            "data": {
                "data": {
                    "projectId": 7636654872435884074,
                    "name": "Codex验收测试0506-1912",
                    "budgetMode": "DAY",
                    "startTime": "2026-05-07 00:00:00",
                    "endTime": "2026-05-08 23:59:59",
                }
            }
        }
    }

    with patch("tools.oceanengine_local_project_runtime.mutation_confirm.mcp_client.invoke_endpoint", return_value=detail_result):
        result = confirm_mutation(spec, payload, mutation_result)

    assert result["confirmed"] is True
    assert result["mode"] == "project_detail"
    assert result["retry_count"] == 0


def test_project_detail_confirmation_treats_same_calendar_day_as_date_match():
    spec = {
        "title": "更新项目",
        "confirmation": {
            "mode": "project_detail",
            "fields": ["end_time"],
        },
    }
    payload = {
        "local_account_id": 1854708763953159,
        "project_id": 7636742197837561910,
        "end_time": "2026-05-09",
    }
    mutation_result = {"raw": {"data": {"data": {}}}}
    detail_result = {
        "raw": {
            "data": {
                "data": {
                    "projectId": 7636742197837561910,
                    "endTime": "2026-05-09 23:59:59",
                }
            }
        }
    }

    with patch("tools.oceanengine_local_project_runtime.mutation_confirm.mcp_client.invoke_endpoint", return_value=detail_result):
        result = confirm_mutation(spec, payload, mutation_result)

    assert result["confirmed"] is True
    assert result["retry_count"] == 0


def test_next_day_week_schedule_confirmation_does_not_require_immediate_schedule_time_change():
    spec = {
        "title": "列表批量更新项目投放时段",
        "confirmation": {
            "mode": "batch_project_detail",
            "batch_field": "items",
        },
    }
    payload = {
        "local_account_id": 1854708763953159,
        "items": [
            {
                "project_id": 7636742197837561910,
                "schedule_scene": "NEXT_DAY",
                "schedule_time": "0" * 336,
            }
        ],
    }
    mutation_result = {"raw": {"data": {"data": {}}}}
    detail_result = {
        "raw": {
            "data": {
                "data": {
                    "projectId": 7636742197837561910,
                    "scheduleTime": "1" * 336,
                }
            }
        }
    }

    with patch("tools.oceanengine_local_project_runtime.mutation_confirm.mcp_client.invoke_endpoint", return_value=detail_result):
        result = confirm_mutation(spec, payload, mutation_result)

    assert result["confirmed"] is True
    assert result["mode"] == "project_detail_deferred"
    assert result["deferred_effect"] is True
    assert result["retry_count"] == 0
