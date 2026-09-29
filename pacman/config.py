"""Configuration parsing and validation."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# A player needs roughly 1.3 moves per walkable cell to sweep a braided
# maze optimally. Doubling that leaves room for imperfect routing and for
# detours forced by the ghosts, which is what makes a level winnable.
_MOVES_PER_CELL = 2.6
_SECONDS_PER_MOVE = 0.10

_TIME_LOW = 10
_TIME_HIGH = 900
_SIZE_LOW = 11
_SIZE_HIGH = 45


class ConfigError(Exception):
    """Raised when the configuration file cannot be read at all."""


@dataclass(frozen=True)
class LevelConfig:
    """Validated configuration for one level."""

    width: int = 21
    height: int = 21
    level_max_time: int = 110


@dataclass(frozen=True)
class GameConfig:
    """Validated game configuration."""

    highscore_filename: str
    levels: tuple[LevelConfig, ...]
    lives: int
    pacgum_density: float
    points_per_pacgum: int
    points_per_super_pacgum: int
    points_per_ghost: int
    seed: int
    ghost_respawn_seconds: float
    super_duration_seconds: float
    player_step_seconds: float
    window_width: int
    window_height: int


_ALLOWED_TOP = frozenset(
    {
        "highscore_filename",
        "levels",
        "level",
        "lives",
        "pacgum_density",
        "points_per_pacgum",
        "points_per_super_pacgum",
        "points_per_ghost",
        "seed",
        "level_max_time",
        "ghost_respawn_seconds",
        "super_duration_seconds",
        "player_step_seconds",
        "window_width",
        "window_height",
    }
)


def default_level_time(width: int, height: int) -> int:
    """Return a time limit a competent player can actually meet.

    The estimate scales with the maze area rather than being a flat 90
    seconds, otherwise every level past the smallest one is impossible
    to clear before the timer expires.
    """
    budget = width * height * _MOVES_PER_CELL * _SECONDS_PER_MOVE
    return max(_TIME_LOW, min(int(math.ceil(budget)), _TIME_HIGH))


def _strip_comments(text: str) -> str:
    """Remove full-line # and // comments from JSON-like input."""
    kept: list[str] = []
    for raw in text.splitlines():
        stripped = raw.lstrip()
        if stripped.startswith("#") or stripped.startswith("//"):
            continue
        kept.append(raw)
    return "\n".join(kept)


def _int_value(
    data: dict[str, Any], key: str, default: int, low: int, high: int
) -> int:
    """Read an integer and clamp invalid values to a safe range."""
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        print(f"Config warning: {key!r} is invalid; using {default}.")
        return default
    if value < low or value > high:
        clamped = max(low, min(value, high))
        print(f"Config warning: {key!r} clamped from {value} to {clamped}.")
        return clamped
    return value


def _float_value(
    data: dict[str, Any], key: str, default: float, low: float, high: float
) -> float:
    """Read a number and clamp invalid values to a safe range."""
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        print(f"Config warning: {key!r} is invalid; using {default}.")
        return default
    numeric = float(value)
    if numeric < low or numeric > high:
        clamped = max(low, min(numeric, high))
        print(f"Config warning: {key!r} clamped to {clamped}.")
        return clamped
    return numeric


def _safe_filename(value: Any) -> str:
    """Validate a local JSON filename for highscores."""
    if not isinstance(value, str) or not value.strip():
        print("Config warning: bad highscore name; using highscores.json.")
        return "highscores.json"
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        print("Config warning: unsafe highscore path; using highscores.json.")
        return "highscores.json"
    return value


def _parse_level(item: dict[str, Any], fallback: int | None) -> LevelConfig:
    """Build one validated level entry."""
    width = _int_value(item, "width", 21, _SIZE_LOW, _SIZE_HIGH)
    height = _int_value(item, "height", 21, _SIZE_LOW, _SIZE_HIGH)
    default_time = fallback or default_level_time(width, height)
    max_time = _int_value(
        item, "level_max_time", default_time, _TIME_LOW, _TIME_HIGH
    )
    return LevelConfig(width, height, max_time)


def _parse_levels(
    data: dict[str, Any], fallback: int | None
) -> tuple[LevelConfig, ...]:
    """Parse level definitions and guarantee the minimum of ten."""
    raw = data.get("levels", data.get("level", []))
    parsed: list[LevelConfig] = []
    if isinstance(raw, list):
        for index, item in enumerate(raw):
            if not isinstance(item, dict):
                print(f"Config warning: level {index + 1} invalid; skipped.")
                continue
            parsed.append(_parse_level(item, fallback))
    elif raw not in (None, []):
        print("Config warning: levels must be an array; using defaults.")

    while len(parsed) < 10:
        width = 21 + 2 * (len(parsed) // 2)
        height = 21 + 2 * ((len(parsed) + 1) // 2)
        width = min(width, _SIZE_HIGH)
        height = min(height, _SIZE_HIGH)
        parsed.append(
            LevelConfig(
                width, height, fallback or default_level_time(width, height)
            )
        )
    return tuple(parsed)


def load_config(filename: str) -> GameConfig:
    """Load a JSON-with-comments configuration using safe defaults."""
    path = Path(filename)
    try:
        with path.open("r", encoding="utf-8") as handle:
            raw_text = handle.read()
    except OSError as exc:
        raise ConfigError(f"cannot read {filename!r}: {exc}") from None

    try:
        raw = json.loads(_strip_comments(raw_text))
    except json.JSONDecodeError as exc:
        raise ConfigError(
            f"invalid JSON near line {exc.lineno}: {exc.msg}"
        ) from None
    if not isinstance(raw, dict):
        raise ConfigError("top-level configuration must be a JSON object")

    for key in raw:
        if key not in _ALLOWED_TOP:
            print(f"Config warning: unknown key {key!r} ignored.")

    # An explicit global level_max_time overrides the derived estimate;
    # when absent, each level gets a limit scaled to its own maze area.
    global_time: int | None = None
    if "level_max_time" in raw:
        global_time = _int_value(
            raw, "level_max_time", 110, _TIME_LOW, _TIME_HIGH
        )

    return GameConfig(
        highscore_filename=_safe_filename(
            raw.get("highscore_filename", "highscores.json")
        ),
        levels=_parse_levels(raw, global_time),
        lives=_int_value(raw, "lives", 3, 1, 99),
        pacgum_density=_float_value(raw, "pacgum_density", 0.72, 0.10, 1.0),
        points_per_pacgum=_int_value(raw, "points_per_pacgum", 10, 0, 100000),
        points_per_super_pacgum=_int_value(
            raw, "points_per_super_pacgum", 50, 0, 100000
        ),
        points_per_ghost=_int_value(raw, "points_per_ghost", 200, 0, 100000),
        # The generator treats a seed of zero as "reseed from the system
        # clock", which would break the fixed first level, so clamp to 1.
        seed=_int_value(raw, "seed", 42, 1, 2_147_483_647),
        ghost_respawn_seconds=_float_value(
            raw, "ghost_respawn_seconds", 5.0, 1.0, 60.0
        ),
        super_duration_seconds=_float_value(
            raw, "super_duration_seconds", 7.0, 1.0, 60.0
        ),
        player_step_seconds=_float_value(
            raw, "player_step_seconds", _SECONDS_PER_MOVE, 0.03, 1.0
        ),
        window_width=_int_value(raw, "window_width", 1000, 640, 2560),
        window_height=_int_value(raw, "window_height", 900, 600, 1440),
    )
