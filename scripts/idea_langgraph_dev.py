#!/usr/bin/env python
"""IDEA/PyCharm debug entrypoint for LangGraph CLI.

The Windows console script is an .exe, so launching this small Python wrapper
keeps the process under the IDE debugger while preserving the normal CLI args.
"""

from pathlib import Path

from dotenv import load_dotenv
from langgraph_cli.cli import cli


ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")
load_dotenv(ROOT_DIR / "backend" / ".env", override=False)


if __name__ == "__main__":
    cli()
