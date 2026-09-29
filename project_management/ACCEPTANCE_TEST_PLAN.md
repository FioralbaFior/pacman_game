# Acceptance Test Plan

| ID | Feature | Test | Expected result |
|---|---|---|---|
| A01 | CLI | Run with zero/two args | Usage message, no traceback |
| A02 | Config | Missing file | Clean configuration error |
| A03 | Config | # comment + valid JSON | File loads |
| A04 | Config | Invalid numeric value | Warning + safe clamp/default |
| A05 | Config | Unknown key | Warning, key ignored |
| A06 | Maze | Reinstall assigned wheel, run level | External generator used unchanged with `perfect=False` |
| A07 | Maze | Level 1 twice with seed 42 | Same generated maze |
| A08 | Maze | Start later levels | Fresh random seed used |
| A09 | Player | Push into wall | Player does not cross wall |
| A10 | Player | Eat pacgum | Pacgum disappears, +X score |
| A11 | Power | Eat super-pacgum | +Y, ghosts become edible temporarily |
| A12 | Ghost | Touch normal ghost | Lose life, respawn in middle |
| A13 | Ghost | Eat frightened ghost | +Z, ghost temporarily inactive then respawns in corner |
| A14 | Lives | Lose final life | Game over → final score → name entry |
| A15 | Level | Clear pellets | Advance level; score/lives preserved |
| A16 | Game | Complete final level | Victory → final score → name entry |
| A17 | Timer | Reach zero | Lose life and restart timer per chosen policy |
| A18 | Pause | Pause for 10 s | Remaining level time does not drop by 10 s |
| A19 | Highscore | Enter invalid name | Not saved |
| A20 | Highscore | Add >10 scores | Only top 10 retained |
| A21 | Highscore | Corrupt JSON | Warning, game still opens with empty table |
| A22 | UI | Main menu | Start, highscores, instructions, exit visible |
| A23 | HUD | During play | Score, lives, level, time always visible |
| A24 | Cheat | C+I | Invincibility works |
| A25 | Cheat | C+F | Ghosts freeze |
| A26 | Cheat | C+N | Level skips |
| A27 | Cheat | C+L | Extra life added |
| A28 | Cheat | C+V | Player step rate increases |
| A29 | Quality | `make test` | All unit tests pass |
| A30 | Quality | `make lint` | flake8 + required mypy invocation pass |
| A31 | Package | `make package` | Rebuildable executable produced in `dist/` |
