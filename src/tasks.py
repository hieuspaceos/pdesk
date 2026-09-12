"""Local task store backed by SQLite.

Two status fields per task:

- `sheet_status` — chip text pulled from Google Sheets (`Ưu tiên`,
  `Xem lại`). Always refreshed on upsert.
- `local_status` — user's progress (`pending` | `planned` | `done`).
  **Never** reset by upsert. Once a task is `done`, it stays `done`
  even if the Sheet chip still says `Ưu tiên`.

The upsert rule prevents Sheet pulls from undoing local progress
just because the chip hasn't been cleared.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, Optional

from .models import Task


LOCAL_STATUSES = ("pending", "planned", "done")


class TaskStoreError(RuntimeError):
    """Raised for invalid operations on the store."""


SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT,
  sheet_status TEXT NOT NULL DEFAULT '',
  local_status TEXT NOT NULL DEFAULT 'pending',
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS tasks_local_status_idx
  ON tasks(local_status);
"""


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def init(db_path: Path) -> None:
    """Create the schema if missing. Safe to call repeatedly."""
    with _connect(db_path) as conn:
        conn.commit()


def upsert(db_path: Path, tasks: Iterable[Task]) -> int:
    """Refresh title/description/sheet_status for each task.

    New rows get `local_status = 'pending'`. Existing rows keep their
    `local_status` — even if `done`, even if the Sheet chip is the
    same. Returns the number of rows inserted or refreshed.
    """
    count = 0
    with _connect(db_path) as conn:
        for t in tasks:
            conn.execute(
                """
                INSERT INTO tasks (id, title, description, sheet_status, local_status, updated_at)
                VALUES (?, ?, ?, ?, 'pending', datetime('now'))
                ON CONFLICT(id) DO UPDATE SET
                  title = excluded.title,
                  description = excluded.description,
                  sheet_status = excluded.sheet_status,
                  updated_at = excluded.updated_at
                """,
                (t.id, t.title, t.description, t.sheet_status),
            )
            count += 1
        conn.commit()
    return count


def list_tasks(
    db_path: Path, *, local_status: Optional[str] = None
) -> list[Task]:
    """Return tasks filtered by local_status (None = all).

    Note: returns `Task` with `sheet_status` populated, but `Task` has
    no `local_status` field. The caller can read it via a separate
    helper or treat the result list as an opaque view.
    """
    with _connect(db_path) as conn:
        if local_status is None:
            rows = conn.execute(
                "SELECT id, title, description, sheet_status FROM tasks"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, title, description, sheet_status FROM tasks "
                "WHERE local_status = ?",
                (local_status,),
            ).fetchall()
    return [
        Task(
            id=r["id"],
            title=r["title"],
            description=r["description"] or "",
            sheet_status=r["sheet_status"] or "",
        )
        for r in rows
    ]


def get_local_status(db_path: Path, task_id: str) -> Optional[str]:
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT local_status FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
    return row["local_status"] if row else None


def mark(db_path: Path, task_id: str, local_status: str) -> bool:
    """Set the local_status for a row. Returns False if id missing."""
    if local_status not in LOCAL_STATUSES:
        raise TaskStoreError(
            f"local_status must be one of {LOCAL_STATUSES}, got {local_status!r}"
        )
    with _connect(db_path) as conn:
        cur = conn.execute(
            "UPDATE tasks SET local_status = ?, updated_at = datetime('now') "
            "WHERE id = ?",
            (local_status, task_id),
        )
        conn.commit()
        return cur.rowcount > 0
