"""Upgrade config.yaml to match config.example.yaml.

This is the Python equivalent of scripts/config-upgrade.sh, used by Windows
Make targets when Git Bash is unavailable.
"""

from __future__ import annotations

import copy
import os
import shutil
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "config.example.yaml"

MIGRATIONS = {
    1: {
        "description": "Rename src.* module paths to deerflow.*",
        "replacements": [
            ("src.community.", "deerflow.community."),
            ("src.sandbox.", "deerflow.sandbox."),
            ("src.models.", "deerflow.models."),
            ("src.tools.", "deerflow.tools."),
        ],
    },
}


def _resolve_config_path() -> Path | None:
    env_path = os.environ.get("DEER_FLOW_CONFIG_PATH")
    if env_path and Path(env_path).is_file():
        return Path(env_path)

    backend_config = ROOT / "backend" / "config.yaml"
    if backend_config.is_file():
        return backend_config

    root_config = ROOT / "config.yaml"
    if root_config.is_file():
        return root_config

    return None


def _merge_missing(target: dict, source: dict, added: list[str], path: str = "") -> None:
    for key, value in source.items():
        key_path = f"{path}.{key}" if path else str(key)
        if key not in target:
            target[key] = copy.deepcopy(value)
            added.append(key_path)
        elif isinstance(value, dict) and isinstance(target[key], dict):
            _merge_missing(target[key], value, added, key_path)


def main() -> int:
    if not EXAMPLE.is_file():
        print(f"ERROR config.example.yaml not found at {EXAMPLE}")
        return 1

    config_path = _resolve_config_path()
    if config_path is None:
        print("No config.yaml found - creating from example...")
        shutil.copy2(EXAMPLE, ROOT / "config.yaml")
        print("OK config.yaml created. Please review and set your API keys.")
        return 0

    raw_text = config_path.read_text(encoding="utf-8")
    user = yaml.safe_load(raw_text) or {}
    example = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8")) or {}

    user_version = user.get("config_version", 0)
    example_version = example.get("config_version", 0)

    if user_version >= example_version:
        print(f"OK config.yaml is already up to date (version {user_version}).")
        return 0

    print(f"Upgrading config.yaml: version {user_version} -> {example_version}")
    print()

    migrated: list[str] = []
    for version in range(user_version + 1, example_version + 1):
        migration = MIGRATIONS.get(version)
        if not migration:
            continue
        for old, new in migration.get("replacements", []):
            if old in raw_text:
                raw_text = raw_text.replace(old, new)
                migrated.append(f"{old} -> {new}")

    user = yaml.safe_load(raw_text) or {}

    if migrated:
        print(f"Applied {len(migrated)} migration(s):")
        for migration in migrated:
            print(f"  ~ {migration}")
        print()

    added: list[str] = []
    _merge_missing(user, example, added)
    user["config_version"] = example_version

    backup = config_path.with_suffix(".yaml.bak")
    shutil.copy2(config_path, backup)
    print(f"Backed up to {backup.name}")

    config_path.write_text(
        yaml.dump(user, default_flow_style=False, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    if added:
        print(f"Added {len(added)} new field(s):")
        for field in added:
            print(f"  + {field}")

    if not migrated and not added:
        print("No changes needed (version bumped only).")

    print()
    print(f"OK config.yaml upgraded to version {example_version}.")
    print("  Please review the changes and set any new required values.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
