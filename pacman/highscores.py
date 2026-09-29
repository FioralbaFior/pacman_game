"""Persistent top-ten highscore storage."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from pacman.paths import writable_path

_NAME_RE = re.compile(r"^[A-Za-z0-9 ]{1,10}$")


@dataclass(frozen=True)
class ScoreEntry:
    """One validated highscore record."""

    name: str
    score: int


class HighscoreStore:
    """Load, validate, rank, and persist highscores robustly."""

    def __init__(self, filename: str) -> None:
        # A frozen build cannot write next to its bundled files, so
        # the table is redirected to a per-user data directory.
        self.path = writable_path(filename)
        self.entries: list[ScoreEntry] = []
        self.load()

    @staticmethod
    def valid_name(name: str) -> bool:
        """Return whether a name satisfies the subject constraints."""
        return _NAME_RE.fullmatch(name) is not None

    @staticmethod
    def _entry_from_unknown(item: Any) -> ScoreEntry | None:
        if not isinstance(item, dict):
            return None
        name = item.get("name")
        score = item.get("score")
        if not isinstance(name, str) or not HighscoreStore.valid_name(name):
            return None
        if isinstance(score, bool) or not isinstance(score, int) or score < 0:
            return None
        return ScoreEntry(name, score)

    def load(self) -> None:
        """Load valid records; missing/corrupt files become an empty table."""
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                raw = json.load(handle)
        except FileNotFoundError:
            self.entries = []
            return
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Highscore warning: cannot load {self.path}: {exc}")
            self.entries = []
            return
        if not isinstance(raw, list):
            print("Highscore warning: invalid format; table reset.")
            self.entries = []
            return
        valid = [
            entry
            for item in raw
            if (entry := self._entry_from_unknown(item)) is not None
        ]
        valid.sort(key=lambda entry: entry.score, reverse=True)
        self.entries = valid[:10]

    def add(self, name: str, score: int) -> bool:
        """Add a validated score and immediately persist the top ten."""
        normalized = name.strip()
        if not self.valid_name(normalized) or score < 0:
            return False
        self.entries.append(ScoreEntry(normalized, int(score)))
        self.entries.sort(key=lambda entry: entry.score, reverse=True)
        self.entries = self.entries[:10]
        self.save()
        return True

    def save(self) -> None:
        """Persist the highscore list without leaking an open file handle."""
        payload = [entry.__dict__ for entry in self.entries]
        try:
            with self.path.open("w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
                handle.write("\n")
        except OSError as exc:
            print(f"Highscore warning: cannot save {self.path}: {exc}")
