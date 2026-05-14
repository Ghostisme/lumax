from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.oceanengine_local_project_runtime.endpoint_runner import main, run_endpoint
from tools.oceanengine_local_project_runtime.rule_loader import load_rule_config

RULE_FILE = Path(__file__).resolve().parents[2] / "rules" / "create-unit.json"
SPEC = load_rule_config(RULE_FILE)


def run(payload: dict, dry_run: bool = False) -> dict:
    return run_endpoint(SPEC, payload, dry_run=dry_run)


if __name__ == "__main__":
    main(SPEC)
