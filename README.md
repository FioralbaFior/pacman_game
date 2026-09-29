*This activity has been created as part of the 42 curriculum by ffrasher.*

# Pac-Man — Ghosts! More ghosts!

## Description

A complete, playable Pac-Man written in Python with object-oriented
design and a modular architecture. Mazes come from the assigned
*A-Maze-ing* package, used as-is; the game reads a JSON-with-comments
configuration, keeps a persistent top-ten highscore table, and ships a
cheat mode so a reviewer can exercise every feature quickly.

The rendering layer is deliberately restricted to MLX-equivalent
operations: an off-screen image buffer is filled pixel by pixel
(`mlx_pixel_put`), then pushed to the window in a single call
(`mlx_put_image_to_window`). No shape-drawing primitive without an MLX
counterpart is used.

## Instructions

```
make install     # dependencies + the assigned A-Maze-ing wheel
make run         # equivalent to: python3 pac-man.py config.json
make lint        # flake8 + mypy with the mandated flags
make lint-strict # flake8 + mypy --strict
make test        # unit tests
make package     # PyInstaller build from pacman.spec
make clean
```

Launch the game with exactly one argument, a JSON configuration file:

```
python3 pac-man.py config.json
```

Any error — missing file, bad extension, malformed JSON, invalid value,
missing generator — is reported as a plain message. The program never
prints a Python traceback.

Requires Python 3.10 or later.

## Controls

| Key | Action |
| --- | --- |
| Arrows / WASD | Move |
| P or Esc | Pause and resume |
| M | Return to main menu (while paused) |
| Enter / Space | Confirm in menus |

### Cheat mode

Cheat mode exists to make peer review fast: it lets a reviewer reach any
level, survive any ghost, and check the win path without a long play
session.

| Key | Effect |
| --- | --- |
| C | Toggle cheat mode (required before I, F and V) |
| I | Invincibility — ghosts cannot take a life |
| F | Freeze ghosts |
| N | Skip the current level (win it immediately) |
| L | Add one life |
| V | Increased player speed |

Active cheats are shown in the HUD so a run using them is never mistaken
for a clean one.

## Configuration

The file is standard JSON plus full-line comments: a line whose first
non-blank characters are `#` or `//` is stripped before parsing.

Every key is optional. A missing or invalid value is clamped to a safe
default and reported on stdout; unknown keys are ignored with a warning.

| Key | Default | Range | Meaning |
| --- | --- | --- | --- |
| `highscore_filename` | `highscores.json` | relative path | Highscore table file |
| `lives` | `3` | 1–99 | Starting lives |
| `pacgum_density` | `0.72` | 0.10–1.0 | Fraction of free cells holding a pacgum |
| `points_per_pacgum` | `10` | 0–100000 | Score per pacgum |
| `points_per_super_pacgum` | `50` | 0–100000 | Score per super-pacgum |
| `points_per_ghost` | `200` | 0–100000 | Score per edible ghost |
| `seed` | `42` | 1–2147483647 | Seed of level 1 only |
| `ghost_respawn_seconds` | `5` | 1–60 | Delay before an eaten ghost returns |
| `super_duration_seconds` | `7` | 1–60 | How long ghosts stay edible |
| `player_step_seconds` | `0.10` | 0.03–1.0 | Seconds per player grid step |
| `level_max_time` | derived | 10–900 | Global time limit override |
| `window_width` | `1000` | 640–2560 | Window width |
| `window_height` | `900` | 600–1440 | Window height |
| `levels` | 10 entries | — | Array of `{width, height, level_max_time}` |

Per-level keys: `width` and `height` (11–45) and an optional
`level_max_time`.

### Why the time limit is derived, not a flat 90 seconds

Sweeping a braided maze costs roughly 1.3 moves per walkable cell even
with perfect routing. A flat 90-second limit makes every maze beyond the
smallest one impossible to clear, which would put the victory screen out
of reach. When `level_max_time` is absent, the game derives it as
`width × height × 2.6 × 0.10` seconds, which leaves a competent player
about twice the optimal-play time. Fewer than ten levels in `levels` are
padded with growing mazes so the mandated minimum always holds.

## Highscore system

Stored as a JSON array of `{"name": ..., "score": ...}` objects. JSON was
chosen because it is human-readable, so a peer can inspect or corrupt the
file during review and watch the game recover.

- Names: 1–10 characters, ASCII letters, digits and spaces only.
- Scores: non-negative integers.
- Only the top ten are kept, sorted descending.
- Loaded at startup, rewritten on every insertion and again at exit.
- A missing file starts an empty table; a corrupt or wrongly-shaped file
  logs a warning and starts empty; individual malformed records are
  dropped while valid ones survive.
- Entered on the game-over and victory screens; shown on the main menu
  (top five) and in full under *View Highscores*.

From a source checkout the file sits in the working directory. In a
packaged build it is redirected to the per-user data directory, because
the PyInstaller bundle directory is temporary and read-only.

## Maze Generation

The assigned *A-Maze-ing* package is installed from the wheel at the
repository root and used unmodified. `pacman/maze_adapter.py` adapts our
code to their interface, never the reverse:

```python
MazeGenerator(size=(w, h), perfect=False,
              entry_cell=(0, 0), exit_cell=(w - 1, h - 1), seed=seed)
```

`PERFECT` is `False`, so the generator braids away dead ends and produces
Pac-Man-compatible corridors.

The returned grid is a list of rows of wall bitmasks — north 1, east 2,
south 4, west 8 — where a set bit means a wall. A cell holding 15 is
fully enclosed: those are the isolated `42` glyph the package stamps in
the middle, and the adapter treats them as unwalkable. The adapter
validates the shape and the value type of everything it receives and
raises `MazeError` on anything unexpected.

The import itself is guarded, so a missing or broken package produces a
clean in-game error screen rather than an `ImportError` at startup. A
generator failure mid-run returns the player to the main menu with a
message instead of killing the process.

Level 1 uses the configured fixed seed; every later level draws a random
one. A seed of 0 is clamped to 1, because the package treats non-positive
seeds as "reseed from the system clock", which would make level 1
non-deterministic.

## Implementation

- **Grid movement.** The player and the ghosts occupy whole cells and
  advance on independent timers. A requested direction is buffered and
  applied at the next step if the wall bitmask allows it.
- **Ghost AI.** Blinky chases via BFS shortest path, Pinky targets three
  cells ahead of the player, Inky mixes chasing with random turns, Clyde
  retreats to his corner within five cells of the player. When
  frightened, every ghost moves to the neighbour furthest from the
  player.
- **Collisions.** Resolved after each move by cell equality. Because the
  player and the ghosts move in separate calls, one always lands on the
  other's cell first, so no pass-through can occur.
- **Timers.** All timing uses `time.monotonic()`. Pausing accumulates
  paused time and subtracts it, so a pause never consumes level time.
- **Timeout rule.** Reaching zero costs one life and restarts the level
  timer; eaten pacgums stay eaten. Losing the last life ends the run.
- **Rendering.** The maze and every sprite are rasterised once per level
  into image buffers and afterwards only blitted. Rebuilding them each
  frame cost about 140 ms; caching brings a steady frame to roughly
  1 ms, which is what makes the 60 FPS loop and responsive input real.

## General Software Architecture

```
pac-man.py            argument handling and the top-level error boundary
pacman/
  config.py           JSON-with-comments parsing, clamping, defaults
  paths.py            resource and writable-file resolution, frozen-aware
  maze_adapter.py     adapter over the assigned package + MazeData queries
  game.py             rules: GameSession, Player, Ghost, CheatState
  highscores.py       HighscoreStore, ScoreEntry, persistence
  graphics.py         Image buffers, sprite rasterisers, Graphics window
  app.py              PacmanApp: main loop, screens, input, rendering
```

Dependencies point one way only. `game.py` knows nothing about pygame
and is fully testable headless; `graphics.py` knows nothing about game
rules; `app.py` is the only module that joins them. Swapping the
graphical backend touches `graphics.py` and the drawing half of `app.py`
and nothing else.

`GameSession` owns all mutable run state. `MazeData` is frozen and
exposes the queries the rules need — `walkable`, `can_move`,
`neighbors`, `nearest_walkable`, `shortest_step`.

## Project Management

Timeline, kanban board, risk analysis, acceptance tests, team
organisation and blocking points live in
[`project_management/`](project_management/).

## Packaging

`make package` builds a single executable from `pacman.spec`, bundling
`config.json`, `PACKAGED_README.txt` and the A-Maze-ing package. Launched
with no argument the executable loads its bundled configuration, so it
works when started from a store front; passing a `.json` path still
overrides it.

## Resources

- Pac-Man Dossier — ghost behaviour and original arcade rules:
  <https://pacman.holenet.info/>
- pygame documentation: <https://www.pygame.org/docs/>
- MLX reference for the allowed drawing operations:
  <https://harm-smits.github.io/42docs/libs/minilibx>
- PEP 257, docstring conventions: <https://peps.python.org/pep-0257/>
- mypy and flake8 documentation.
- Bresenham's line algorithm and barycentric triangle filling, for the
  pixel-level rasterisers.

### AI usage

AI was used as a reviewer and a rubber duck, not as an author:

- To audit an earlier version against the subject, which surfaced the
  three real defects: the renderer redrawing every pixel each frame, the
  packaged build refusing to start without an argument, and time limits
  that made every level past the first mathematically unclearable.
- To discuss the caching strategy for the image buffers before it was
  implemented.
- To suggest edge cases now covered in `tests/`.

Every measurement quoted above was reproduced locally, and every line in
this repository was reviewed and is defensible on request.
