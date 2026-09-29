"""Highscore tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pacman.highscores import HighscoreStore


class HighscoreTests(unittest.TestCase):
    """Verify name constraints and top-ten persistence."""

    def test_name_validation(self) -> None:
        self.assertTrue(HighscoreStore.valid_name("Fiora 42"))
        self.assertFalse(HighscoreStore.valid_name("too-long-name"))
        self.assertFalse(HighscoreStore.valid_name("bad!"))

    def test_top_ten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = HighscoreStore(str(Path(directory) / "scores.json"))
            for value in range(15):
                self.assertTrue(store.add(f"P{value}", value))
            self.assertEqual(len(store.entries), 10)
            self.assertEqual(store.entries[0].score, 14)


if __name__ == "__main__":
    unittest.main()
