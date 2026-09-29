"""Adapter for the externally assigned A-Maze-ing package."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any, Iterable

# The assigned A-Maze-ing package is imported dynamically so a missing
# or broken install degrades into a clean MazeError instead of an
# ImportError traceback at startup.
_GENERATOR: Any = None
_IMPORT_ERROR = ""
try:
    from mazegenerator import MazeGenerator as _AssignedGenerator
except ImportError as exc:
    _IMPORT_ERROR = str(exc)
else:
    _GENERATOR = _AssignedGenerator

Cell = tuple[int, int]

NORTH = 1
EAST = 2
SOUTH = 4
WEST = 8

_DIRECTIONS: tuple[tuple[int, int, int], ...] = (
    (0, -1, NORTH),
    (1, 0, EAST),
    (0, 1, SOUTH),
    (-1, 0, WEST),
)


class MazeError(Exception):
    """Raised when the assigned generator cannot produce a usable maze."""


@dataclass(frozen=True)
class MazeData:
    """Immutable maze view used by game logic."""

    walls: tuple[tuple[int, ...], ...]
    width: int
    height: int
    blocked: frozenset[Cell]

    def inside(self, cell: Cell) -> bool:
        """Return whether a cell lies inside the grid."""
        x, y = cell
        return 0 <= x < self.width and 0 <= y < self.height

    def walkable(self, cell: Cell) -> bool:
        """Return whether a cell is traversable."""
        return self.inside(cell) and cell not in self.blocked

    def can_move(self, cell: Cell, direction: Cell) -> bool:
        """Return whether a move crosses no wall into a walkable cell."""
        if not self.walkable(cell):
            return False
        x, y = cell
        dx, dy = direction
        bit = {
            (0, -1): NORTH,
            (1, 0): EAST,
            (0, 1): SOUTH,
            (-1, 0): WEST,
        }.get((dx, dy))
        if bit is None or self.walls[y][x] & bit:
            return False
        return self.walkable((x + dx, y + dy))

    def neighbors(self, cell: Cell) -> list[Cell]:
        """Return walkable neighbors connected by open passages."""
        x, y = cell
        result: list[Cell] = []
        for dx, dy, bit in _DIRECTIONS:
            nxt = (x + dx, y + dy)
            if self.walkable(nxt) and not (self.walls[y][x] & bit):
                result.append(nxt)
        return result

    def nearest_walkable(self, target: Cell) -> Cell:
        """Find the nearest traversable cell to a requested position."""
        if self.walkable(target):
            return target
        queue: deque[Cell] = deque([target])
        seen: set[Cell] = {target}
        while queue:
            x, y = queue.popleft()
            for dx, dy, _ in _DIRECTIONS:
                nxt = (x + dx, y + dy)
                if nxt in seen or not self.inside(nxt):
                    continue
                if self.walkable(nxt):
                    return nxt
                seen.add(nxt)
                queue.append(nxt)
        raise MazeError("maze contains no walkable cells")

    def shortest_step(self, start: Cell, goal: Cell) -> Cell:
        """Return the first BFS step to goal, or start if unreachable."""
        if start == goal:
            return start
        queue: deque[Cell] = deque([start])
        previous: dict[Cell, Cell | None] = {start: None}
        while queue:
            current = queue.popleft()
            for nxt in self.neighbors(current):
                if nxt in previous:
                    continue
                previous[nxt] = current
                if nxt == goal:
                    cursor = nxt
                    while previous[cursor] != start:
                        parent = previous[cursor]
                        if parent is None:
                            return start
                        cursor = parent
                    return cursor
                queue.append(nxt)
        return start


def _find_blocked_42(walls: list[list[int]]) -> frozenset[Cell]:
    """Identify isolated value-15 cells inserted by the assigned generator."""
    blocked: set[Cell] = set()
    for y, row in enumerate(walls):
        for x, value in enumerate(row):
            if value != 15:
                continue
            # Value 15 means all four walls: the isolated '42' glyph
            # the assigned package stamps into the middle of the maze.
            blocked.add((x, y))
    return frozenset(blocked)


def generate_maze(width: int, height: int, seed: int) -> MazeData:
    """Generate a non-perfect maze through the external package as-is."""
    if _GENERATOR is None:
        detail = f": {_IMPORT_ERROR}" if _IMPORT_ERROR else ""
        raise MazeError(f"A-Maze-ing package is not installed{detail}")
    try:
        generator = _GENERATOR(
            size=(width, height),
            perfect=False,
            entry_cell=(0, 0),
            exit_cell=(width - 1, height - 1),
            seed=seed,
        )
        raw = generator.maze
    except Exception as exc:
        raise MazeError(f"assigned maze generator failed: {exc}") from None
    if not isinstance(raw, list) or len(raw) != height:
        raise MazeError("assigned maze generator returned an invalid height")
    if any(not isinstance(row, list) or len(row) != width for row in raw):
        raise MazeError("assigned maze generator returned an invalid width")
    try:
        normalized = [[int(value) & 0xF for value in row] for row in raw]
    except (TypeError, ValueError):
        raise MazeError("maze generator returned non-integer walls") from None
    return MazeData(
        walls=tuple(tuple(row) for row in normalized),
        width=width,
        height=height,
        blocked=_find_blocked_42(normalized),
    )


def corner_cells(maze: MazeData) -> tuple[Cell, Cell, Cell, Cell]:
    """Return walkable cells nearest to the four maze corners."""
    requests: Iterable[Cell] = (
        (0, 0),
        (maze.width - 1, 0),
        (0, maze.height - 1),
        (maze.width - 1, maze.height - 1),
    )
    found = [maze.nearest_walkable(cell) for cell in requests]
    return (found[0], found[1], found[2], found[3])
