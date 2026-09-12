"""Smoke test for src.sheets.

Run with real Sheet credentials:

    PDESK_SHEET_ID=... PDESK_SA_PATH=/path/to/sa.json \\
        .venv/bin/python tests/smoke_sheets.py

Without env, exits 2 with a one-line hint.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import Config, ConfigError
from src.sheets import SheetsError, fetch_tasks, _parse_blocks
from src.models import Task


def _cfg_from_env() -> Config:
    sheet_id = os.environ.get("PDESK_SHEET_ID")
    sa_path = os.environ.get("PDESK_SA_PATH")
    sheet_range = os.environ.get("PDESK_SHEET_RANGE") or "'Chưa giải quyết'!A1:H1000"
    if not sheet_id or not sa_path:
        raise ConfigError(
            "Set PDESK_SHEET_ID and PDESK_SA_PATH (and optionally "
            "PDESK_SHEET_RANGE) in env."
        )
    return Config(
        sheet_id=sheet_id,
        sheet_range=sheet_range,
        sa_path=Path(sa_path),
        minimax_api_key="",  # not needed for this smoke
        minimax_model="MiniMax-M3",
        db_path=Path("/tmp/pdesk-test.sqlite"),
    )


def main() -> int:
    # Static unit check: parse a fixture of A + G values.
    fixture = [
        ["", "", "", "", "", "", "", ""],                                # blank
        ["Dorm: chuyển qua OP là khách", "", "", "", "", "", "", ""],     # task 1
        ["Đơn giá : giá chia 2", "", "", "", "", "", "", ""],
        ["Số lượng là số khách", "", "", "", "", "", "", ""],
        ["", "", "", "", "", "", "Ưu tiên", "Hiếu"],
        ["", "", "", "", "", "", "", ""],                                # blank
        ["Package : xem lại D1 là D0", "", "", "", "", "", "", ""],
        ["", "", "", "", "", "", "Xem lại", "Hiếu"],
        ["", "", "", "", "", "", "", ""],
        ["Done task — already handled", "", "", "", "", "", "", ""],
        ["", "", "", "", "", "", "Done", "Hiếu"],
        ["", "", "", "", "", "", "", ""],
    ]
    parsed = _parse_blocks(fixture)
    if len(parsed) != 2:
        print(f"FAIL: expected 2 kept blocks, got {len(parsed)}", file=sys.stderr)
        return 1
    if parsed[0].sheet_status != "Ưu tiên":
        print(f"FAIL: first status {parsed[0].sheet_status!r}", file=sys.stderr)
        return 1
    if parsed[1].sheet_status != "Xem lại":
        print(f"FAIL: second status {parsed[1].sheet_status!r}", file=sys.stderr)
        return 1
    print(f"OK: fixture parsed {len(parsed)} tasks (Ưu tiên, Xem lại).")

    # Live check (only if creds present).
    try:
        cfg = _cfg_from_env()
    except ConfigError:
        print("skip: live smoke (no PDESK_SHEET_ID / PDESK_SA_PATH).")
        return 0
    try:
        tasks = fetch_tasks(cfg)
    except SheetsError as exc:
        print(f"FAIL: live fetch failed: {exc}", file=sys.stderr)
        return 2
    print(f"OK: live fetch returned {len(tasks)} tasks.")
    for t in tasks[:3]:
        print(f"  - {t.id}  [{t.sheet_status}]  {t.title[:60]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
