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

2. Copy the credential template and fill in your values:

   ```bash
   cd pdesk
   cp .env.example .env.local      # git-ignored
   ```

   `.env.local` holds three values: `PDESK_SHEET_ID`,
   `PDESK_SA_PATH`, `PDESK_MINIMAX_API_KEY`. Open `.env.local` in
   any editor; fields are inline-commented so the format is obvious.

   Equivalent: export the same `PDESK_*` vars in your shell, or write
   them to `~/.config/pdesk/pdesk.toml` (TOML keys without the
   `PDESK_` prefix). The loader checks env first, then TOML.

3. Set up Google Sheets access once:

   - Create a Google Cloud project, enable the **Sheets API**, create a
     service account, download its JSON key. The SA email looks like
     `something@<project>.iam.gserviceaccount.com`.
   - Share the target workbook with that SA email as **Viewer**. (If
     the workbook owner is someone else and you're a Viewer too, ask
     them to do the share — service accounts are how pdesk authenticates,
     they don't replace your Google login.)

4. Run `pdesk config show` to confirm everything is loaded.

5. `pdesk` to open the TUI.

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
├── .env.example          # template — copy to .env.local, fill in
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
