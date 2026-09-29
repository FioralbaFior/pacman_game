# Kanban

## Done

- Parse JSON config with # and // full-line comments
- Safe defaults, clamping, unknown-key ignore behavior
- External maze adapter with `perfect=False`
- Fixed first-level seed and randomized subsequent levels
- Player movement through passages only
- Four autonomous ghosts with chase/flee behavior
- Pacgums and four corner super-pacgums
- Lives, respawn, score, game win/loss
- At least ten levels and per-level time limit
- Pause/resume
- Persistent validated top-ten highscores
- Main menu, highscore screen, instructions, HUD, pause, victory/game-over flow
- Cheat mode: invincible, level skip, freeze, extra life, speed
- Makefile, lint rules, tests, packaging spec, README

## Verify before defense

- `make install`
- `make test`
- `make lint`
- Full ten-level playthrough with cheat mode
- Corrupt/missing config and highscore files
- Reinstall assigned wheel and rerun smoke tests
- Regenerate packaged build

## External

- Upload packaged build to free unlisted/private public gaming platform
- Record release URL in README before final submission
