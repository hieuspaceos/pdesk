"""Debug: dump raw values from the user's tab so we can see what
chip text actually looks like."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import load
from src.sheets import _client


def main() -> int:
    cfg = load()
    svc = _client(cfg)
    result = (
        svc.spreadsheets()
        .values()
        .get(
            spreadsheetId=cfg.sheet_id,
            range=cfg.sheet_range,
            valueRenderOption="FORMATTED_VALUE",
        )
        .execute()
    )
    rows = result.get("values", [])
    print(f"Total rows fetched: {len(rows)}")
    for idx, row in enumerate(rows, start=1):
        padded = row + [""] * (8 - len(row))
        a = (padded[0] or "").strip()
        g = (padded[6] or "").strip()
        h = (padded[7] or "").strip()
        if not a and not g:
            continue
        print(f"  row {idx:3d}: A={a[:50]!r:52s}  G={g!r}  H={h!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
