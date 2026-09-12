"""Google Sheets reader for the `Chưa giải quyết` tab.

Sheet schema (verified 2026-09-12 from the user's screenshot of "Data
IMA Workspace"):

- Column A holds task descriptions. One task spans multiple
  contiguous rows; tasks are separated by **blank rows**.
- Column G holds a status chip on some row in the block. Possible
  labels: `Ưu tiên`, `Xem lại`, empty.
- Column H holds an assignee chip (`Hiếu`).

Default range is `'Chưa giải quyết'!A1:H1000` (tab name is quoted
because it contains a space).

The reader returns only blocks whose G chip is in
`KEEP_STATUSES = {"Ưu tiên", "Xem lại"}`. Other chips or empty cells
are dropped — those tasks are already resolved by the user.
"""

from __future__ import annotations

from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account

from .config import Config
from .models import Task


SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
KEEP_STATUSES = {"Ưu tiên", "Xem lại"}


class SheetsError(RuntimeError):
    """Raised when Sheets cannot be read for any reason."""


def _client(cfg: Config):
    if not cfg.sa_path.exists():
        raise SheetsError(
            f"Service account JSON not found at {cfg.sa_path}. "
            "Set PDESK_SA_PATH correctly."
        )
    try:
        creds = service_account.Credentials.from_service_account_file(
            str(cfg.sa_path), scopes=SCOPES
        )
    except Exception as exc:
        raise SheetsError(f"Failed to load service account: {exc}") from exc
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def fetch_tasks(cfg: Config) -> list[Task]:
    """Pull and parse the user's task tab. Returns `[]` on empty result.

    Raises `SheetsError` for any non-empty failure (network, scope,
    parse). The caller surfaces a one-line message.
    """
    try:
        svc = _client(cfg)
        result = (
            svc.spreadsheets()
            .values()
            .get(
                spreadsheetId=cfg.sheet_id,
                range=cfg.sheet_range,
                valueRenderOption="FORMATTED_VALUE",
                dateTimeRenderOption="SERIAL_NUMBER",
            )
            .execute()
        )
    except HttpError as exc:
        raise SheetsError(
            f"Sheets API error: {exc.resp.status} {exc.resp.reason}"
        ) from exc
    except Exception as exc:
        raise SheetsError(f"Sheets request failed: {exc}") from exc

    rows: list[list[str]] = result.get("values", [])
    return _parse_blocks(rows)


def _parse_blocks(rows: list[list[str]]) -> list[Task]:
    """Group rows by blank-row separators, emit tasks whose G chip is
    in `KEEP_STATUSES`.
    """
    if not rows:
        return []

    out: list[Task] = []
    block_start: int | None = None
    block_a: list[tuple[int, str]] = []   # (row_index_1based, value)
    block_g: list[tuple[int, str]] = []

    def flush(end_idx: int) -> None:
        nonlocal block_start, block_a, block_g
        if block_start is None or not block_a:
            block_start, block_a, block_g = None, [], []
            return
        chip = next((v.strip() for _, v in block_g if v.strip()), "")
        start_snapshot = block_start
        a_snapshot = block_a
        block_start, block_a, block_g = None, [], []
        if chip not in KEEP_STATUSES:
            return
        title = a_snapshot[0][1].strip()
        desc_lines = [v for _, v in a_snapshot[1:]]
        description = "\n".join(desc_lines).strip()
        out.append(
            Task(
                id=f"row-{start_snapshot}-row-{end_idx}",
                title=title,
                description=description,
                sheet_status=chip,
            )
        )

    for idx, row in enumerate(rows, start=1):
        # Pad row to column H so index 6 (G) and 7 (H) always exist.
        padded = row + [""] * (8 - len(row))
        a_val = (padded[0] or "").strip()
        g_val = (padded[6] or "").strip()
        if not a_val and not g_val:
            # Blank row inside the block separator.
            flush(idx - 1)
            continue
        if block_start is None:
            block_start = idx
        if a_val:
            block_a.append((idx, a_val))
        if g_val:
            block_g.append((idx, g_val))

    flush(len(rows))
    return out
