"""Interpreter startup compatibility for DeerFlow local development."""

from __future__ import annotations

import asyncio
import sys


if sys.platform == "win32":
    policy_cls = getattr(asyncio, "WindowsSelectorEventLoopPolicy", None)
    if policy_cls is not None and not isinstance(asyncio.get_event_loop_policy(), policy_cls):
        asyncio.set_event_loop_policy(policy_cls())

sys._deerflow_sitecustomize_loaded = True
