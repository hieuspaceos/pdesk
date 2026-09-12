"""Config loader for pdesk.

Reads env vars (`PDESK_*`) first, then files under
`~/.config/pdesk/` (POSIX) or `%APPDATA%\\pdesk\\` (Windows). Missing
required field raises `ConfigError` with a one-line "what to do" hint.

The version-only path (`pdesk --version`) does NOT require any
config, so this loader is only called from subcommands that need it.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
import sys

ENV_PREFIX = "PDESK_"


class ConfigError(RuntimeError):
    """Raised when a required config field is missing or invalid."""


@dataclass(frozen=True)
class Config:
    sheet_id: str
    sheet_range: str
    sa_path: Path
    minimax_api_key: str
    minimax_model: str
    db_path: Path


def _config_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / "pdesk"
    return Path.home() / ".config" / "pdesk"


def _data_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "pdesk"
    return Path.home() / ".local" / "share" / "pdesk"


def _read_env(name: str) -> str | None:
    val = os.environ.get(ENV_PREFIX + name)
    return val.strip() if val and val.strip() else None


def _read_toml(path: Path) -> dict[str, str]:
    """Tiny TOML reader for the few keys we need.

    We avoid a `tomllib` dependency (3.11+) by parsing the simple
    `key = "value"` lines ourselves. Strings may use single or double
    quotes; values are stripped. Anything else is ignored.
    """
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        key = k.strip()
        val = v.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
            val = val[1:-1]
        out[key] = val
    return out


def load() -> Config:
    """Load config from env + config dir. Raises ConfigError on missing
    required fields, with a one-line hint per field.
    """
    cfg_dir = _config_dir()
    file_cfg = _read_toml(cfg_dir / "pdesk.toml")

    def pick(key: str) -> str | None:
        return _read_env(key) or file_cfg.get(key)

    sheet_id = pick("SHEET_ID")
    sa_path = pick("SA_PATH")
    api_key = pick("MINIMAX_API_KEY")

    missing: list[str] = []
    if not sheet_id:
        missing.append(
            "Set PDESK_SHEET_ID (Google Sheet ID from the URL)"
        )
    if not sa_path:
        missing.append(
            "Set PDESK_SA_PATH (path to service-account JSON)"
        )
    if not api_key:
        missing.append(
            "Set PDESK_MINIMAX_API_KEY (MiniMax API key)"
        )
    if missing:
        raise ConfigError(
            "pdesk config missing:\n  - " + "\n  - ".join(missing)
        )

    return Config(
        sheet_id=sheet_id or "",
        sheet_range=(
            pick("SHEET_RANGE")
            or "'Chưa giải quyết'!A1:H1000"
        ),
        sa_path=Path(sa_path or "").expanduser(),
        minimax_api_key=api_key or "",
        minimax_model=pick("MINIMAX_MODEL") or "MiniMax-M3",
        db_path=Path(
            pick("DB_PATH") or str(_data_dir() / "tasks.sqlite")
        ).expanduser(),
    )


def show(cfg: Config) -> str:
    """Format config for `pdesk config show`. Never print the API key."""
    sa_exists = cfg.sa_path.exists()
    return (
        f"sheet_id:     {cfg.sheet_id}\n"
        f"sheet_range:  {cfg.sheet_range}\n"
        f"sa_path:      {cfg.sa_path}  ({'exists' if sa_exists else 'NOT FOUND'})\n"
        f"minimax_model: {cfg.minimax_model}\n"
        f"db_path:      {cfg.db_path}\n"
        f"api_key:      set (hidden)"
    )


def ensure_dirs() -> None:
    _config_dir().mkdir(parents=True, exist_ok=True)
    _data_dir().mkdir(parents=True, exist_ok=True)
