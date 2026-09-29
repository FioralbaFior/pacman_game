"""Configuration parsing tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pacman.config import ConfigError, default_level_time, load_config


def write(text: str) -> str:
    """Write a temporary configuration file and return its path."""
    handle = tempfile.NamedTemporaryFile(
        "w", suffix=".json", delete=False, encoding="utf-8"
    )
    with handle:
        handle.write(text)
    return handle.name


class ConfigTests(unittest.TestCase):
    """Cover comments, defaults, clamping, and hard failures."""

    def test_comments_are_stripped(self) -> None:
        path = write('# hash\n// slashes\n{"lives": 5}\n')
        self.assertEqual(load_config(path).lives, 5)

    def test_invalid_lives_clamped(self) -> None:
        path = write(json.dumps({"lives": -100}))
        self.assertEqual(load_config(path).lives, 1)

    def test_unknown_keys_ignored(self) -> None:
        path = write(json.dumps({"nonsense": True, "lives": 2}))
        self.assertEqual(load_config(path).lives, 2)

    def test_zero_seed_is_clamped_to_one(self) -> None:
        # The generator reseeds from the clock on seed <= 0, which would
        # break the fixed first level.
        path = write(json.dumps({"seed": 0}))
        self.assertEqual(load_config(path).seed, 1)

    def test_ten_levels_are_guaranteed(self) -> None:
        path = write(json.dumps({"levels": [{"width": 21, "height": 21}]}))
        self.assertEqual(len(load_config(path).levels), 10)

    def test_level_time_scales_with_area(self) -> None:
        small = default_level_time(21, 21)
        large = default_level_time(29, 31)
        self.assertLess(small, large)

    def test_derived_time_used_when_absent(self) -> None:
        path = write(json.dumps({"levels": [{"width": 29, "height": 31}]}))
        level = load_config(path).levels[0]
        self.assertEqual(level.level_max_time, default_level_time(29, 31))

    def test_missing_file_raises_config_error(self) -> None:
        with self.assertRaises(ConfigError):
            load_config("definitely-not-here.json")

    def test_broken_json_raises_config_error(self) -> None:
        path = write("{,,,}")
        with self.assertRaises(ConfigError):
            load_config(path)

    def test_non_object_raises_config_error(self) -> None:
        path = write("[1, 2, 3]")
        with self.assertRaises(ConfigError):
            load_config(path)

    def test_unsafe_highscore_path_rejected(self) -> None:
        path = write(json.dumps({"highscore_filename": "../escape.json"}))
        name = load_config(path).highscore_filename
        self.assertEqual(Path(name).name, "highscores.json")


if __name__ == "__main__":
    unittest.main()
