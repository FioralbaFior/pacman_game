"""Assigned maze package integration tests."""

from __future__ import annotations

import unittest

from pacman.maze_adapter import generate_maze


class MazeAdapterTests(unittest.TestCase):
    """Smoke-test generation and walkability."""

    def test_generate_nonperfect_maze(self) -> None:
        maze = generate_maze(21, 21, 42)
        self.assertEqual(maze.width, 21)
        self.assertEqual(maze.height, 21)
        start = maze.nearest_walkable((10, 10))
        self.assertTrue(maze.walkable(start))
        self.assertGreater(len(maze.neighbors(start)), 0)


if __name__ == "__main__":
    unittest.main()
