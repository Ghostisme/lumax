from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.endpoint_runner import main, run_endpoint
from common.rule_loader import load_rule_config


RULE_FILE = Path(__file__).resolve().parents[2] / "rules" / "batch-update-project-week-schedule.json"
SPEC = load_rule_config(RULE_FILE)


def run(payload: dict, dry_run: bool = False) -> dict:
    return run_endpoint(SPEC, payload, dry_run=dry_run)


if __name__ == "__main__":
    main(SPEC)
