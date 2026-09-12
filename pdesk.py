#!/usr/bin/env python3
"""Bootstrap wrapper for pdesk.

Mirrors `music-youtube/pmusic.py`: ensure a `.venv` next to this
script exists, install `requirements.txt` if `textual` is not yet
importable, then `execv` into `.venv/bin/python -m src.cli` with the
user's argv.

Standalone phases (--version, future smoke scripts) work without
config; only subcommands that touch Sheet or AI need config.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
VENV_DIR = PROJECT_DIR / ".venv"
REQ_FILE = PROJECT_DIR / "requirements.txt"


def _venv_python() -> Path | None:
    if os.name == "nt":
        candidate = VENV_DIR / "Scripts" / "python.exe"
    else:
        candidate = VENV_DIR / "bin" / "python"
    if not candidate.exists():
        return None
    try:
        subprocess.run(
            [str(candidate), "--version"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return candidate


def _need_install() -> bool:
    py = _venv_python()
    if py is None:
        return True
    try:
        subprocess.run(
            [str(py), "-c", "import textual, openai"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return False
    except subprocess.CalledProcessError:
        return True


def _create_venv() -> None:
    if VENV_DIR.exists():
        return
    print(f"  creating venv at {VENV_DIR}")
    subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)


def _pip_install() -> None:
    py = _venv_python()
    assert py is not None
    print(f"  installing {REQ_FILE.name}")
    subprocess.run(
        [str(py), "-m", "pip", "install", "--upgrade", "pip"],
        check=True,
    )
    subprocess.run(
        [str(py), "-m", "pip", "install", "-r", str(REQ_FILE)],
        check=True,
    )


def _exec_in_venv(argv: list[str]) -> None:
    py = _venv_python()
    assert py is not None
    os.chdir(PROJECT_DIR)
    os.execv(str(py), [str(py), "-m", "src.cli", *argv])


def main() -> int:
    if _need_install():
        print("pdesk: setting up Python environment…")
        _create_venv()
        _pip_install()
        print("pdesk: ready.")
    _exec_in_venv(sys.argv[1:])
    return 0


if __name__ == "__main__":
    sys.exit(main())
