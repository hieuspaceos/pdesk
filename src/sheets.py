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
    """Each row with non-empty A and a keep-status chip in H is a Task.

    We initially assumed multi-row blocks (with blank rows as separators)
    based on the first screenshot. After live smoke against the user's
    Sheet, we discovered the actual layout is one row per task — the
    chip sits on the same row as the task description. If a row has
    text but no chip, it's not actionable (no status set yet).
    """
    if not rows:
        return []

    out: list[Task] = []
    for idx, row in enumerate(rows, start=1):
        padded = row + [""] * (9 - len(row))
        a_val = (padded[0] or "").strip()
        h_val = (padded[7] or "").strip()
        if not a_val:
            continue
        if h_val not in KEEP_STATUSES:
            continue
        out.append(
            Task(
                id=f"row-{idx}",
                title=a_val.split("\n", 1)[0],
                description=a_val,
                sheet_status=h_val,
            )
        )
    return out
