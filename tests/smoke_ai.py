"""Smoke test for src.ai.

Run with a real key in env:

    PDESK_MINIMAX_API_KEY=... .venv/bin/python tests/smoke_ai.py

Without a key, exits 2 with a one-line hint and no traceback.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow `python tests/smoke_ai.py` from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ai import AIError, plan
from src.models import Task


def main() -> int:
    task = Task(
        id="row-1-row-1",
        title="Write a hello world in Python",
        description="Print the string 'hello, world' to stdout.",
        sheet_status="",
    )
    try:
        text = plan(task)
    except AIError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2

    if "print(" not in text:
        print(f"FAIL: response did not contain 'print(': {text[:200]}", file=sys.stderr)
        return 1

    print("OK: plan() returned a non-empty plan with 'print('.")
    print("---")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
