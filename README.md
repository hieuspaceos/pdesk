# pdesk

Personal work orchestrator. Pulls unresolved tasks from a Google Sheet
tab `Chưa giải quyết`, plans them with MiniMax M3, tracks your progress
locally in SQLite. Sheet is read-only; your local status stays put
even when the Sheet chip hasn't been cleared.

## What it does

- `pdesk` or `pdesk today` — open the Textual TUI.
- `pdesk list` — list cached tasks with their local progress.
- `pdesk plan <task_id>` — print an AI plan to stdout (no TUI).
- `pdesk done <task_id>` — mark a task done locally.
- `pdesk config show` — print the loaded config (no secrets).

In the TUI: `enter` opens a plan, `d` marks the highlighted row done,
`r` re-fetches the Sheet, `q` quits.

## Requirements

- Python 3.10+
- `yt-dlp` is **not** required (that's `music-youtube`).
- A Google Sheet workbook you can read.
- A MiniMax API key with the `MiniMax-M3` model enabled.

## Setup

1. Clone the repo and symlink the wrapper:

   ```bash
   git clone https://github.com/hieuspaceos/pdesk
   ln -s "$(pwd)/pdesk/pdesk.py" ~/.local/bin/pdesk
   ```

   On first run, `pdesk` creates `.venv/`, installs `requirements.txt`,
   then execs into the venv. Subsequent runs skip setup.

2. Create a service-account JSON key in Google Cloud Console with the
   Sheets API enabled. Note the SA email (looks like
   `something@project.iam.gserviceaccount.com`).

3. Share the Sheet workbook with that email as **Viewer**.

4. Set three env vars (or put them in `~/.config/pdesk/pdesk.toml`):

   ```ini
   # ~/.config/pdesk/pdesk.toml
   SHEET_ID="..."               # from the Sheet URL
   SA_PATH="/path/to/sa.json"   # service-account JSON
   MINIMAX_API_KEY="..."
   ```

   Defaults: `SHEET_RANGE = 'Chưa giải quyết'!A1:H1000`,
   `DB_PATH = ~/.local/share/pdesk/tasks.sqlite`.

5. Run `pdesk config show` to confirm everything is loaded.

6. `pdesk` to open the TUI.

## Sheet schema

The reader targets the `Chưa giải quyết` tab in your workbook.

- **Column A**: task description. One task may span multiple rows;
  rows are split on all-empty separators.
- **Column G**: status chip (`Ưu tiên` or `Xem lại`). Other chips are
  ignored — those tasks are already resolved.
- The other tabs (`Km`, `Train`, `Restaurant`, …) are supplier
  catalogues and are not read.

## Layout

```
pdesk/
├── README.md
├── AGENTS.md
├── .gitignore
├── requirements.txt
├── pdesk.py              # bootstrap wrapper
├── src/
│   ├── __init__.py
│   ├── cli.py
│   ├── tui.py
│   ├── sheets.py
│   ├── ai.py
│   ├── tasks.py
│   ├── models.py
│   └── config.py
└── tests/
    ├── smoke_ai.py
    ├── smoke_sheets.py
    └── smoke_db.py
```

For dev notes (decisions, gotchas, rejected scope) see
[`../docs/projects/pdesk.md`](../docs/projects/pdesk.md).
