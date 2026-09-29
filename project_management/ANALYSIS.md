# Project Analysis and Technical Choices

## External maze boundary

The strongest coupling risk is the assigned A-Maze-ing wheel. All assumptions about its interface are confined to `maze_adapter.py`. The rest of the game sees `MazeData`, not the third-party object. This lets a reviewer reinstall the assigned package without forcing changes across game logic.

## Grid movement

Movement is cell-based rather than free-pixel physics. This makes wall legality exact: a move is allowed only when the wall bit for that direction is open and the target is walkable. It also keeps ghost pathfinding deterministic and reviewable.

## Ghost AI

BFS supplies a shortest next step toward a target. Personalities only change the target selection. Frightened behavior chooses the neighboring cell with greatest Manhattan distance from Pac-Man. The approach is simple enough to explain and change during a defense.

## Persistence

JSON is used for highscores because only ten small records are required. Every record is validated at the boundary; corrupt files degrade to an empty table instead of crashing.

## Timeout policy

The subject allows the implementation to choose timeout behavior. This project treats timeout as a lost life plus actor respawn and timer restart, while preserving the accumulated score and remaining lives.

## Graphics restriction

The renderer uses a deliberately narrow pygame surface: window creation, events, loop timing, elementary image-buffer drawing, text, and frame presentation. These correspond to capabilities available in MLX-style projects. No physics, scene graph, sprite engine, collision engine, networking, audio engine, or GUI widgets are used.
