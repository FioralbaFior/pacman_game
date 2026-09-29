#!/usr/bin/env python3
"""42 Pac-Man entry point."""

from __future__ import annotations

import sys

from pacman.app import PacmanApp
from pacman.config import ConfigError, load_config
from pacman.maze_adapter import MazeError
from pacman.paths import default_config_path, is_frozen

USAGE = "Usage: python3 pac-man.py config.json"


def resolve_argument(argv: list[str]) -> str | None:
    """Return the configuration path, or None when the call is invalid.

    From a source checkout the program takes exactly one argument, as the
    subject requires. A packaged build launched from a store front gets
    no arguments at all, so it falls back to the configuration bundled
    inside the package.
    """
    if len(argv) == 2:
        candidate = argv[1]
        if not candidate.lower().endswith(".json"):
            print("Error: the configuration file must be a .json file.")
            return None
        return candidate
    if len(argv) == 1 and is_frozen():
        bundled = default_config_path()
        print(f"No configuration given; using bundled {bundled.name}.")
        return str(bundled)
    print(USAGE)
    return None


def main(argv: list[str]) -> int:
    """Validate arguments, load the configuration, and run the game."""
    path = resolve_argument(argv)
    if path is None:
        return 1
    try:
        config = load_config(path)
        PacmanApp(config).run()
    except ConfigError as exc:
        print(f"Configuration error: {exc}")
        return 1
    except MazeError as exc:
        print(f"Maze generation error: {exc}")
        return 1
    except KeyboardInterrupt:
        print("\nGame interrupted cleanly.")
        return 0
    except Exception as exc:  # defensive boundary: never show a traceback
        print(f"Game error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
