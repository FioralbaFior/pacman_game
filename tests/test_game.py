"""Game rule tests that do not need a window."""

from __future__ import annotations

import time
import unittest

from pacman.config import load_config
from pacman.game import DOWN, GameSession, Phase
from pacman.paths import resource_path


def session() -> GameSession:
    """Build a session from the shipped configuration."""
    return GameSession(load_config(str(resource_path("config.json"))))


class GameTests(unittest.TestCase):
    """Cover scoring, lives, pausing, and level progression."""

    def test_first_level_is_deterministic(self) -> None:
        a, b = session(), session()
        self.assertEqual(a.maze.walls, b.maze.walls)
        self.assertEqual(a.pacgums, b.pacgums)

    def test_four_ghosts_and_four_supers(self) -> None:
        game = session()
        self.assertEqual(len(game.ghosts), 4)
        self.assertEqual(len(game.super_pacgums), 4)

    def test_density_leaves_some_corridors_empty(self) -> None:
        game = session()
        free = sum(
            game.maze.walkable((x, y))
            for y in range(game.maze.height)
            for x in range(game.maze.width)
        )
        self.assertLess(len(game.pacgums), free)

    def test_every_pacgum_is_reachable(self) -> None:
        from collections import deque

        game = session()
        seen = {game.player.cell}
        queue = deque([game.player.cell])
        while queue:
            for cell in game.maze.neighbors(queue.popleft()):
                if cell not in seen:
                    seen.add(cell)
                    queue.append(cell)
        remaining = (game.pacgums | game.super_pacgums) - seen
        self.assertEqual(remaining, set())

    def test_score_never_decreases(self) -> None:
        game = session()
        now = time.monotonic()
        previous = game.score
        for _ in range(200):
            now += 0.1
            game.request_direction(DOWN)
            game.player_step(now)
            self.assertGreaterEqual(game.score, previous)
            previous = game.score

    def test_pause_does_not_consume_level_time(self) -> None:
        game = session()
        now = time.monotonic()
        before = game.remaining_time(now)
        game.toggle_pause(now)
        game.toggle_pause(now + 30)
        self.assertEqual(game.remaining_time(now + 30), before)

    def test_cheat_skip_reaches_victory(self) -> None:
        game = session()
        game.enable_cheat()
        for _ in range(len(game.config.levels)):
            game.skip_level()
        self.assertIs(game.phase, Phase.WON)

    def test_cheats_do_nothing_while_disabled(self) -> None:
        game = session()
        lives, level = game.lives, game.level_number
        game.add_life()
        game.skip_level()
        self.assertEqual((game.lives, game.level_number), (lives, level))

    def test_invincibility_prevents_life_loss(self) -> None:
        game = session()
        game.enable_cheat()
        game.cheat.invincible = True
        now = time.monotonic()
        game.ghosts[0].cell = game.player.cell
        game._resolve_collisions(now)
        self.assertEqual(game.lives, game.config.lives)

    def test_ghost_collision_costs_a_life(self) -> None:
        game = session()
        now = time.monotonic()
        game.ghosts[0].cell = game.player.cell
        game._resolve_collisions(now)
        self.assertEqual(game.lives, game.config.lives - 1)

    def test_timeout_costs_a_life_and_restarts_timer(self) -> None:
        game = session()
        now = time.monotonic() + game.level_limit + 1
        game.check_timeout(now)
        self.assertEqual(game.lives, game.config.lives - 1)
        self.assertGreater(game.remaining_time(now), 0)

    def test_ghost_never_respawns_onto_the_player(self) -> None:
        game = session()
        now = time.monotonic()
        ghost = game.ghosts[0]
        ghost.active = False
        ghost.respawn_at = now
        game.player.cell = ghost.spawn
        game.ghost_step(now)
        self.assertEqual(game.lives, game.config.lives)
        self.assertFalse(ghost.active)

    def test_held_back_ghost_returns_once_player_moves(self) -> None:
        game = session()
        now = time.monotonic()
        ghost = game.ghosts[0]
        ghost.active = False
        ghost.respawn_at = now
        game.player.cell = game.player.spawn
        game.ghost_step(now)
        self.assertTrue(ghost.active)

    def test_frightened_flash_warns_before_the_window_closes(self) -> None:
        game = session()
        now = time.monotonic()
        game.frightened_until = now + 5.0
        self.assertFalse(game.frightened_ending(now))
        self.assertTrue(game.frightened_ending(now + 3.5))
        self.assertFalse(game.frightened_ending(now + 6.0))


if __name__ == "__main__":
    unittest.main()
