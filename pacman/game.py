"""Pac-Man game state and rules."""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum

from pacman.config import GameConfig
from pacman.maze_adapter import (
    Cell,
    MazeData,
    corner_cells,
    generate_maze,
)

UP: Cell = (0, -1)
RIGHT: Cell = (1, 0)
DOWN: Cell = (0, 1)
LEFT: Cell = (-1, 0)
STOP: Cell = (0, 0)


class Phase(Enum):
    """High-level game result state."""

    PLAYING = "playing"
    WON = "won"
    LOST = "lost"


@dataclass
class Player:
    """Player model."""

    cell: Cell
    spawn: Cell
    direction: Cell = STOP
    wanted_direction: Cell = STOP


@dataclass
class Ghost:
    """Ghost model with a simple personality and respawn state."""

    name: str
    cell: Cell
    spawn: Cell
    personality: str
    active: bool = True
    respawn_at: float = 0.0


@dataclass
class CheatState:
    """Reviewer-oriented cheat controls."""

    enabled: bool = False
    invincible: bool = False
    ghosts_frozen: bool = False
    speed_boost: bool = False


@dataclass
class GameSession:
    """Own all mutable state for one full multi-level game."""

    config: GameConfig
    score: int = 0
    lives: int = field(init=False)
    level_index: int = 0
    phase: Phase = Phase.PLAYING
    maze: MazeData = field(init=False)
    player: Player = field(init=False)
    ghosts: list[Ghost] = field(init=False, default_factory=list)
    pacgums: set[Cell] = field(init=False, default_factory=set)
    super_pacgums: set[Cell] = field(init=False, default_factory=set)
    frightened_until: float = 0.0
    level_started_at: float = field(init=False)
    paused_seconds: float = 0.0
    pause_started_at: float | None = None
    cheat: CheatState = field(default_factory=CheatState)

    def __post_init__(self) -> None:
        self.lives = self.config.lives
        self._load_level(0)

    @property
    def level_number(self) -> int:
        """Return one-based level number."""
        return self.level_index + 1

    @property
    def level_limit(self) -> int:
        """Return current level time limit."""
        return self.config.levels[self.level_index].level_max_time

    def remaining_time(self, now: float) -> int:
        """Return whole seconds remaining in this level."""
        elapsed = now - self.level_started_at - self.paused_seconds
        if self.pause_started_at is not None:
            elapsed -= now - self.pause_started_at
        return max(0, int(math.ceil(self.level_limit - elapsed)))

    def _load_level(self, index: int) -> None:
        level = self.config.levels[index]
        if index == 0:
            seed = self.config.seed
        else:
            seed = random.randint(1, 2_147_483_647)
        self.maze = generate_maze(level.width, level.height, seed)
        middle = (self.maze.width // 2, self.maze.height // 2)
        player_spawn = self.maze.nearest_walkable(middle)
        self.player = Player(player_spawn, player_spawn)
        corners = corner_cells(self.maze)
        identities = (
            ("Blinky", "chase"),
            ("Pinky", "ambush"),
            ("Inky", "random"),
            ("Clyde", "shy"),
        )
        self.ghosts = [
            Ghost(name, cell, cell, behavior)
            for (name, behavior), cell in zip(identities, corners)
        ]
        self.super_pacgums = set(corners)
        reserved = {player_spawn, *corners}
        candidates = sorted(
            (x, y)
            for y in range(self.maze.height)
            for x in range(self.maze.width)
            if self.maze.walkable((x, y)) and (x, y) not in reserved
        )
        # "Pacgums in most corridors": a density below 1.0 keeps the
        # sweep long enough to be interesting without making the level
        # impossible to finish inside its time limit.
        keep = max(1, int(len(candidates) * self.config.pacgum_density))
        picker = random.Random(seed)
        self.pacgums = set(picker.sample(candidates, keep))
        self.frightened_until = 0.0
        self.level_started_at = time.monotonic()
        self.paused_seconds = 0.0
        self.pause_started_at = None

    def request_direction(self, direction: Cell) -> None:
        """Queue a requested player direction."""
        if direction in (UP, RIGHT, DOWN, LEFT):
            self.player.wanted_direction = direction

    def player_step(self, now: float) -> None:
        """Advance the player by one grid cell if possible."""
        if self.phase is not Phase.PLAYING:
            return
        if self.pause_started_at is not None:
            return
        if self.maze.can_move(self.player.cell, self.player.wanted_direction):
            self.player.direction = self.player.wanted_direction
        if self.maze.can_move(self.player.cell, self.player.direction):
            dx, dy = self.player.direction
            x, y = self.player.cell
            self.player.cell = (x + dx, y + dy)
        self._collect(now)
        self._resolve_collisions(now)
        self._check_level_complete()

    def ghost_step(self, now: float) -> None:
        """Advance each active ghost according to chase/flee behavior."""
        if self.phase is not Phase.PLAYING:
            return
        if self.pause_started_at is not None:
            return
        for ghost in self.ghosts:
            if not ghost.active:
                if now >= ghost.respawn_at and self._respawn_is_safe(ghost):
                    ghost.active = True
                    ghost.cell = ghost.spawn
                continue
            if self.cheat.enabled and self.cheat.ghosts_frozen:
                continue
            neighbors = self.maze.neighbors(ghost.cell)
            if not neighbors:
                continue
            if now < self.frightened_until:
                ghost.cell = max(
                    neighbors,
                    key=lambda cell: self._manhattan(cell, self.player.cell),
                )
            else:
                target = self._ghost_target(ghost)
                step = self.maze.shortest_step(ghost.cell, target)
                if step == ghost.cell:
                    step = random.choice(neighbors)
                ghost.cell = step
        self._resolve_collisions(now)

    def _respawn_is_safe(self, ghost: Ghost) -> bool:
        """Return whether a ghost may reappear without ambushing.

        A ghost respawns in its corner, which also holds a
        super-pacgum. Materialising straight onto the player would take
        a life with nothing visible beforehand, so the return is held
        back until the player steps away.
        """
        return self._manhattan(ghost.spawn, self.player.cell) > 1

    def frightened_ending(self, now: float) -> bool:
        """Return whether the edible window is about to close.

        Drives the warning flash so the player is never surprised by
        ghosts turning dangerous again.
        """
        if now >= self.frightened_until:
            return False
        return self.frightened_until - now <= 2.0

    def _ghost_target(self, ghost: Ghost) -> Cell:
        if ghost.personality == "random" and random.random() < 0.35:
            around = self.maze.neighbors(ghost.cell) or [ghost.cell]
            return random.choice(around)
        if ghost.personality == "ambush":
            px, py = self.player.cell
            dx, dy = self.player.direction
            target = (px + dx * 3, py + dy * 3)
            return self.maze.nearest_walkable(
                (
                    max(0, min(target[0], self.maze.width - 1)),
                    max(0, min(target[1], self.maze.height - 1)),
                )
            )
        if ghost.personality == "shy":
            if self._manhattan(ghost.cell, self.player.cell) <= 5:
                return ghost.spawn
        return self.player.cell

    @staticmethod
    def _manhattan(a: Cell, b: Cell) -> int:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def _collect(self, now: float) -> None:
        cell = self.player.cell
        if cell in self.pacgums:
            self.pacgums.remove(cell)
            self.score += self.config.points_per_pacgum
        if cell in self.super_pacgums:
            self.super_pacgums.remove(cell)
            self.score += self.config.points_per_super_pacgum
            self.frightened_until = now + self.config.super_duration_seconds

    def _resolve_collisions(self, now: float) -> None:
        for ghost in self.ghosts:
            if not ghost.active or ghost.cell != self.player.cell:
                continue
            if now < self.frightened_until:
                self.score += self.config.points_per_ghost
                ghost.active = False
                ghost.respawn_at = now + self.config.ghost_respawn_seconds
                ghost.cell = ghost.spawn
                continue
            if self.cheat.enabled and self.cheat.invincible:
                continue
            self._lose_life(now)
            return

    def _lose_life(self, now: float) -> None:
        self.lives -= 1
        if self.lives <= 0:
            self.phase = Phase.LOST
            return
        self.player.cell = self.player.spawn
        self.player.direction = STOP
        self.player.wanted_direction = STOP
        for ghost in self.ghosts:
            ghost.cell = ghost.spawn
            ghost.active = True
            ghost.respawn_at = 0.0
        self.frightened_until = 0.0
        # A timeout or a collision restarts the level timer while the
        # score and the remaining pacgums are preserved.
        self.level_started_at = now
        self.paused_seconds = 0.0

    def check_timeout(self, now: float) -> None:
        """Apply the timeout rule: lose a life, restart the timer."""
        if (
            self.phase is Phase.PLAYING
            and self.pause_started_at is None
            and self.remaining_time(now) <= 0
        ):
            self._lose_life(now)

    def _check_level_complete(self) -> None:
        if self.pacgums or self.super_pacgums:
            return
        self.complete_level()

    def complete_level(self) -> None:
        """Advance to the next level, or mark the whole game won."""
        if self.level_index + 1 >= len(self.config.levels):
            self.phase = Phase.WON
            return
        self.level_index += 1
        self._load_level(self.level_index)

    def toggle_pause(self, now: float) -> None:
        """Pause or resume while keeping timers accurate."""
        if self.phase is not Phase.PLAYING:
            return
        if self.pause_started_at is None:
            self.pause_started_at = now
        else:
            self.paused_seconds += now - self.pause_started_at
            self.pause_started_at = None

    def enable_cheat(self) -> None:
        """Toggle reviewer cheat mode globally."""
        self.cheat.enabled = not self.cheat.enabled
        if not self.cheat.enabled:
            self.cheat.invincible = False
            self.cheat.ghosts_frozen = False
            self.cheat.speed_boost = False

    def add_life(self) -> None:
        """Cheat: add one life."""
        if self.cheat.enabled:
            self.lives += 1

    def skip_level(self) -> None:
        """Cheat: immediately complete the current level."""
        if self.cheat.enabled:
            self.complete_level()
