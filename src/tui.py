"""Textual TUI for pdesk.

Single screen: a `ListView` of Sheet tasks (filtered to `Ưu tiên` /
`Xem lại`). Bindings on the list itself:

- `enter` → open a plan modal (calls `ai.plan` in a worker thread)
- `d` → mark the highlighted task done locally
- `r` → re-fetch from Sheet, upsert, refresh
- `q` → quit

No filter Input is needed for MVP, so we do NOT copy
`SearchInput.on_key` from `music-youtube`.
"""

from __future__ import annotations

import asyncio
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import (
    Footer,
    Header,
    Label,
    ListItem,
    ListView,
    Static,
)

from . import ai, sheets, tasks
from .config import Config
from .models import Task

class TaskRow(ListItem):
    """ListView row. Stores the Sheet task + its current local_status."""

    def __init__(self, task: Task, local_status: str) -> None:
        label = f"[{task.sheet_status or '—'}] [{local_status}]  {task.title}"
        super().__init__(Label(label))
        self.task_data = task
        self.local_status = local_status

class PetDeskApp(App):
    CSS = """
    Screen { layout: vertical; }
    #status { height: 1; padding: 0 1; background: $boost; color: $text; }
    """

    BINDINGS = [
        Binding("d", "mark_done", "Mark done"),
        Binding("r", "refresh", "Refresh"),
        Binding("q", "quit", "Quit"),
    ]

    status: reactive[str] = reactive("Loading…")

    def __init__(self, cfg: Config) -> None:
        super().__init__()
        self.cfg = cfg
        self.tasks_view: Optional[ListView] = None
        self.status_widget: Optional[Static] = None
        self.row_by_id: dict[str, TaskRow] = {}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static(self.status, id="status")
        yield ListView(id="tasks")
        yield Footer()

    def on_mount(self) -> None:
        self.status_widget = self.query_one("#status", Static)
        self.tasks_view = self.query_one("#tasks", ListView)
        self._refresh(initial=True)

    # --- actions ---

    def action_refresh(self) -> None:
        self._refresh(initial=False)

    def action_mark_done(self) -> None:
        if not self.tasks_view:
            return
        row = self.tasks_view.highlighted_child
        if not isinstance(row, TaskRow):
            return
        if row.local_status == "done":
            self._set_status(f"already done: {row.task_data.title[:40]}")
            return
        tasks.mark(self.cfg.db_path, row.task_data.id, "done")
        self._set_status(f"done: {row.task_data.title[:40]}")
        self._refresh(initial=False)

    # --- internals ---

    def _set_status(self, msg: str) -> None:
        self.status = msg
        if self.status_widget is not None:
            self.status_widget.update(msg)

    def _refresh(self, *, initial: bool) -> None:
        if initial:
            tasks.init(self.cfg.db_path)
        try:
            fetched = sheets.fetch_tasks(self.cfg)
        except sheets.SheetsError as exc:
            self._set_status(f"Sheet fetch failed: {exc}")
            return
        if not fetched:
            self._set_status("No tasks with 'Ưu tiên' or 'Xem lại'.")
            return
        tasks.upsert(self.cfg.db_path, fetched)
        assert self.tasks_view is not None
        self.tasks_view.clear()
        self.row_by_id.clear()
        for t in fetched:
            local = tasks.get_local_status(self.cfg.db_path, t.id) or "pending"
            row = TaskRow(t, local)
            self.tasks_view.append(row)
            self.row_by_id[t.id] = row
        self._set_status(f"{len(fetched)} task(s) loaded.")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Enter on a row → spawn a worker thread to call MiniMax, then
        mount the plan modal on the UI thread."""
        row = event.item
        if not isinstance(row, TaskRow):
            return
        self._set_status(f"Planning: {row.task_data.title[:40]}…")
        self.run_worker(
            self._plan_for_row(row),
            exclusive=False,
            thread=True,
        )

    async def _plan_for_row(self, row: TaskRow) -> None:
        """Worker body. Runs in a worker thread, talks back to the UI."""
        loop = asyncio.get_running_loop()
        try:
            plan_text = await loop.run_in_executor(None, ai.plan, row.task_data)
        except ai.AIError as exc:
            self.call_from_thread(self._set_status, f"AI error: {exc}")
            return
        if row.local_status == "pending":
            tasks.mark(self.cfg.db_path, row.task_data.id, "planned")
        self.call_from_thread(
            self._set_status, f"Plan ready: {row.task_data.title[:40]}"
        )
        self.call_from_thread(self._show_plan, plan_text)
    def _call_ai(self, task: Task) -> str:
        return ai.plan(task)

    def _show_plan(self, text: str) -> None:
        # MVP: display the plan text in the status bar so the user can
        # see it without quitting the TUI. A proper modal/overlay screen
        # is a phase-6 polish; the status bar keeps the runnable shell
        # honest while the AI path is verified end-to-end.
        first_line = text.strip().splitlines()[0] if text.strip() else ""
        self._set_status(f"Plan: {first_line[:80]}")
        # Full plan goes into a log file the user can tail.
        log_path = self.cfg.db_path.parent / "plans.log"
        try:
            with log_path.open("a", encoding="utf-8") as fh:
                fh.write(f"\n===== {self.cfg.sheet_id} =====\n{text}\n")
        except OSError:
            pass
