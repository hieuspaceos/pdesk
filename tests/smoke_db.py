"""Smoke test for src.tasks.

Verifies:
1. upsert refreshes sheet_status + title/description.
2. upsert never overwrites a local_status of 'done'.
3. mark() validates the status and reports missing ids.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.models import Task
from src.tasks import (
    LOCAL_STATUSES,
    TaskStoreError,
    get_local_status,
    init,
    list_tasks,
    mark,
    upsert,
)


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "pdesk.sqlite"
        init(db)

        tasks_v1 = [
            Task("row-1-row-3", "Dorm task", "first body\nsecond body", "Ưu tiên"),
            Task("row-5-row-7", "Package task", "body only", "Xem lại"),
        ]
        upsert(db, tasks_v1)
        # Initially pending.
        assert get_local_status(db, "row-1-row-3") == "pending"

        # Mark one done locally.
        assert mark(db, "row-1-row-3", "done")
        assert get_local_status(db, "row-1-row-3") == "done"

        # Re-upsert with a refreshed sheet_status — done must NOT be reset.
        tasks_v2 = [
            Task("row-1-row-3", "Dorm task (edited)", "new body", "Ưu tiên"),
            Task("row-5-row-7", "Package task", "body only", "Xem lại"),
            Task("row-9-row-10", "Newly appeared", "fresh", "Ưu tiên"),
        ]
        upsert(db, tasks_v2)

        assert get_local_status(db, "row-1-row-3") == "done", (
            "upsert must not reset a 'done' row back to 'pending'"
        )
        assert get_local_status(db, "row-5-row-7") == "pending"
        assert get_local_status(db, "row-9-row-10") == "pending"

        # Sheet title updated, local_status preserved.
        rows = {t.id: t for t in list_tasks(db)}
        assert rows["row-1-row-3"].title == "Dorm task (edited)"
        assert rows["row-1-row-3"].description == "new body"

        # Mark validation rejects unknown status.
        try:
            mark(db, "row-1-row-3", "frobnicated")
        except TaskStoreError:
            pass
        else:
            print("FAIL: mark accepted an invalid status", file=sys.stderr)
            return 1

        # Mark missing id returns False.
        assert not mark(db, "row-99-row-99", "done")

        # Pending filter returns just the pending ones.
        pending = list_tasks(db, local_status="pending")
        assert {t.id for t in pending} == {"row-5-row-7", "row-9-row-10"}
        done = list_tasks(db, local_status="done")
        assert {t.id for t in done} == {"row-1-row-3"}

        print(f"OK: upsert preserved 'done'; statuses = {LOCAL_STATUSES}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
