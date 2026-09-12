# AGENTS.md — pdesk

Process rules for AI sessions working in this project. Built during
the initial implementation, 2026-09-12.

## Why these rules exist

Each rule was a real failure or near-miss during the build, not a guess.
They are here to keep the next agent from repeating them.

## Rules

- **The Sheet schema is one row per task, not multi-row blocks.**
  We initially assumed tasks spanned multiple rows with blank-row
  separators. Live smoke on 2026-09-12 showed the actual layout is
  one row per task: column A holds the description, column H holds
  the status chip (`Ưu tiên`, `Xem lại`, `Done`, `Hiếu`, …), all
  on the same row. `src/sheets.py::_parse_blocks` was rewritten to
  handle single-row tasks. If a future Sheet author inserts
  multi-row blocks, this code collapses each non-blank row into a
  separate task. Verify against the live sheet, not the plan.

- **Status chip is column H, not G.** Earlier reading of a screenshot
  with the header off by one column led us to filter on column G.
  The actual header "Trạng thái" is in column H (index 7). The
  filter reads `padded[7]`; if a future Sheet reshuffles columns,
  re-verify with `tests/_debug_dump.py` (or equivalent) and update
  this comment.

- **`SearchInput.on_key` does not apply here.** Unlike
  `music-youtube`, pdesk's TUI uses a `ListView`, not a search `Input`.
  Bind Enter on the list (Textual emits `ListView.Selected`); do not
  copy `SearchInput.on_key` from `music-youtube` unless a filter input
  is added later. Reaching for that pattern would be wrong here.

- **`local_status` is never touched by upsert.** The `tasks.upsert()`
  path refreshes `title`, `description`, and `sheet_status`, but it
  leaves `local_status` alone — even if the row is already `done`.
  Re-asserting `local_status = pending` on upsert is the most likely
  regression after a Sheet refresh; do not "simplify" the SQL.

- **The Sheet chip is `sheet_status`, the SQLite column is
  `local_status`.** They are two different fields with two
  different value sets. Don't merge them into a single `status`
  column. The user manages the chip in the Sheet; the user manages
  `local_status` in pdesk. Both surface in the TUI but they are
  owned by different systems.

- **Sheet chip cells need `valueRenderOption="FORMATTED_VALUE"`.**
  Without it, `values().get()` returns rich-text metadata and the
  chip text is empty in `padded[7]`. The current `src/sheets.py`
  sets this explicitly; if a future refactor drops it, no chip
  text will surface and `_parse_blocks` will silently drop every
  task. Verify with the unit fixture in `tests/smoke_sheets.py` if
  in doubt.

- **The user's tab name contains a Unicode character (`Chưa giải
  quyết`) and a space. Always quote it in the A1 range:**
  `'Chưa giải quyết'!A1:H1000`. The default `cfg.sheet_range`
  already quotes it; user overrides must too, or the Sheets API
  returns 400.

- **AI plan output is shown in the status bar, not a modal.**
  `Textual.containers.Vertical` cannot be pushed as a screen via
  `push_screen()` (that's for `Screen` subclasses only). The MVP
  displays the first line in the status bar and writes the full
  plan to `~/.local/share/pdesk/plans.log`. A proper modal screen
  is a phase-7 polish — don't refactor `_show_plan` until you know
  what the replacement Screen class needs to look like.

- **`Textual` + `asyncio.run_in_executor`.** The `on_list_view_selected`
  path uses `loop.run_in_executor(None, ai.plan, row.task)` to call
  the MiniMax API off the UI thread. Do not call `ai.plan()`
  directly from the Selected handler — the UI freezes for tens of
  seconds per plan.

- **POSIX-only Windows paths in `config._config_dir()`.** The
  Windows branch reads `%APPDATA%` / `%LOCALAPPDATA%`. If you ever
  touch it, also re-test the wrapper path `pdesk.py` because it
  has its own POSIX/Windows split.

- **Filter set is just `Ưu tiên` + `Xem lại`.** The Sheet contains
  many other status values (`Done`, `Hiếu`, `Hà`, `để sau`,
  `Gấp`, `THEO DÕI`, `Đang sửa`, `Chưa rõ`, …). The user
  explicitly chose to keep the filter narrow as of 2026-09-12.
  If a wider filter is wanted, update `KEEP_STATUSES` in
  `src/sheets.py` and update `tests/smoke_sheets.py`'s fixture to
  cover the new values.
