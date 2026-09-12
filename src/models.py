"""Lightweight domain models shared across modules.

Defined here rather than re-declared in `sheets.py` and `tasks.py` so
the schema lives in one place.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Task:
    id: str
    title: str
    description: str
    sheet_status: str  # e.g. "Ưu tiên", "Xem lại"; "" if absent
