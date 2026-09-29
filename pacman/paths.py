"""Filesystem locations that stay correct in a packaged build.

When PyInstaller freezes the game, read-only resources live in the
temporary extraction directory exposed as ``sys._MEIPASS`` while the
highscore table must go somewhere the user can actually write to.
Running from a git checkout keeps everything next to the sources.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "pacman42"


def is_frozen() -> bool:
    """Return whether the game runs from a PyInstaller bundle."""
    return bool(getattr(sys, "frozen", False))


def resource_dir() -> Path:
    """Return the directory holding read-only bundled resources."""
    bundle = getattr(sys, "_MEIPASS", None)
    if isinstance(bundle, str):
        return Path(bundle)
    return Path(__file__).resolve().parent.parent


def resource_path(name: str) -> Path:
    """Return the full path of a bundled read-only resource."""
    return resource_dir() / name


def default_config_path() -> Path:
    """Return the configuration shipped inside the package."""
    return resource_path("config.json")


def _user_data_dir() -> Path:
    """Return a per-user writable directory for this game."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA")
        root = Path(base) if base else Path.home() / "AppData" / "Roaming"
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        base = os.environ.get("XDG_DATA_HOME")
        root = Path(base) if base else Path.home() / ".local" / "share"
    return root / APP_NAME


def writable_path(filename: str) -> Path:
    """Resolve a writable file location for the current run mode.

    A source checkout keeps the file in the working directory so peers
    can inspect it. A frozen build redirects it to the user data
    directory, because the bundle directory is temporary and read-only.
    """
    if not is_frozen():
        return Path(filename)
    target = _user_data_dir()
    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError:
        return Path(filename)
    return target / Path(filename).name
