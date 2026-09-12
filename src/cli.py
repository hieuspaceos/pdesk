"""Command-line entry for pdesk.

Phase 05 layout:

- `pdesk` (no args) and `pdesk today` both launch the TUI.
- `pdesk list` prints all cached tasks with their local_status.
- `pdesk plan <task_id>` prints an AI plan to stdout (no TUI).
- `pdesk done <task_id>` sets local_status = done.
- `pdesk config show` prints the loaded config without secrets.

Errors are surfaced as one-line messages on stderr; the program exits
non-zero without a traceback.
"""

from __future__ import annotations

import argparse
import sys

from . import __version__, ai, sheets, tasks
from .config import Config, ConfigError, ensure_dirs, load, show as show_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pdesk",
        description="Personal work orchestrator (Sheet → MiniMax → local).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"pdesk {__version__}",
    )
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("today", help="Open the TUI (default command).")
    sub.add_parser("list", help="Print cached tasks with local_status.")

    p_plan = sub.add_parser("plan", help="Generate an AI plan for a task id.")
    p_plan.add_argument("task_id")

    p_done = sub.add_parser("done", help="Mark a task id done locally.")
    p_show = sub.add_parser("config", help="Config commands.")
    show_cmd = p_show.add_subparsers(dest="config_cmd", required=True)
    show_cmd.add_parser("show", help="Print loaded config (no secrets).")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.cmd is None or args.cmd == "today":
        ensure_dirs()
        try:
            cfg = load()
        except ConfigError as exc:
            sys.stderr.write(str(exc) + "\n")
            return 2
        try:
            from .tui import PetDeskApp
        except ImportError as exc:
            sys.stderr.write(f"TUI dependencies missing: {exc}\n")
            return 2
        PetDeskApp(cfg).run()
        return 0

    if args.cmd == "list":
        return _cmd_list()
    if args.cmd == "plan":
        return _cmd_plan(args.task_id)
    if args.cmd == "done":
        return _cmd_done(args.task_id)
    if args.cmd == "config":
        if getattr(args, "config_cmd", None) == "show":
            return _cmd_config_show()
        parser.error("config requires a subcommand (try: config show)")
    parser.error(f"unknown command: {args.cmd}")
    return 2  # unreachable


def _cmd_list() -> int:
    try:
        cfg = load()
    except ConfigError as exc:
        sys.stderr.write(str(exc) + "\n")
        return 2
    tasks.init(cfg.db_path)
    rows = tasks.list_tasks(cfg.db_path)
    if not rows:
        print("No cached tasks. Run `pdesk today` or `pdesk` to pull from Sheet.")
        return 0
    for t in rows:
        local = tasks.get_local_status(cfg.db_path, t.id) or "pending"
        print(f"[{t.sheet_status or '—'}] [{local:7s}] {t.id}  {t.title}")
    return 0


def _cmd_plan(task_id: str) -> int:
    try:
        cfg = load()
    except ConfigError as exc:
        sys.stderr.write(str(exc) + "\n")
        return 2
    tasks.init(cfg.db_path)
    rows = {t.id: t for t in tasks.list_tasks(cfg.db_path)}
    if task_id not in rows:
        sys.stderr.write(f"Task not in local cache: {task_id}\n")
        sys.stderr.write("Run `pdesk today` first to pull from Sheet.\n")
        return 2
    try:
        text = ai.plan(rows[task_id])
    except ai.AIError as exc:
        sys.stderr.write(f"AI error: {exc}\n")
        return 1
    print(text)
    return 0


def _cmd_done(task_id: str) -> int:
    try:
        cfg = load()
    except ConfigError as exc:
        sys.stderr.write(str(exc) + "\n")
        return 2
    tasks.init(cfg.db_path)
    try:
        ok = tasks.mark(cfg.db_path, task_id, "done")
    except tasks.TaskStoreError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1
    if not ok:
        sys.stderr.write(f"No task with id: {task_id}\n")
        return 2
    print(f"done: {task_id}")
    return 0


def _cmd_config_show() -> int:
    try:
        cfg = load()
    except ConfigError as exc:
        sys.stderr.write(str(exc) + "\n")
        return 2
    print(show_config(cfg))
    return 0


if __name__ == "__main__":
    sys.exit(main())
