"""Persistence for screentime history and widget config.

Data lives in %APPDATA%\\RestYourEyes\\ so it survives across runs and is kept
separate from the code folder. Writes are atomic (temp file + replace) so a
crash mid-save can never corrupt the JSON.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


APP_DIR_NAME = "RestYourEyes"


def data_dir() -> Path:
    """Return (creating if needed) the per-user data directory."""
    base = os.environ.get("APPDATA") or str(Path.home())
    path = Path(base) / APP_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def _load(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
            return data if isinstance(data, dict) else {}
    except (FileNotFoundError, ValueError, OSError):
        return {}


def _save(path: Path, data: dict[str, Any]) -> None:
    # Atomic write: dump to a temp file in the same dir, then replace.
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        os.replace(tmp, path)
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def load_screentime() -> dict[str, dict[str, float]]:
    """Map of {"YYYY-MM-DD": {"active": secs, "idle": secs}}."""
    return _load(data_dir() / "screentime.json")


def save_screentime(history: dict[str, dict[str, float]]) -> None:
    _save(data_dir() / "screentime.json", history)


def load_config() -> dict[str, Any]:
    """Widget config (window position, locked state, ...)."""
    return _load(data_dir() / "config.json")


def save_config(config: dict[str, Any]) -> None:
    _save(data_dir() / "config.json", config)
