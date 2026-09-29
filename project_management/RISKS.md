# Risk Analysis

| Risk | Impact | Mitigation |
|---|---|---|
| Assigned wheel API changes/reinstall | High | Isolate package calls in `maze_adapter.py`; fail cleanly; smoke-test after reinstall |
| Invalid/missing config | High | Top-level ConfigError, defaults/clamps, no traceback |
| Corrupt highscore file | Medium | Validate records, use empty table on load errors |
| 42 isolated cells mistaken for corridors | High | Treat preserved wall value 15 cells as blocked in this assigned package |
| Ghost path cannot reach target | Medium | BFS returns current cell; fallback to local random neighbor |
| Player starts inside 42 glyph | High | Resolve center to nearest walkable cell |
| Small/large level dimensions break UI | Medium | Clamp config dimensions and dynamically size viewport cells |
| Timer continues while paused | Medium | Explicit pause timestamp and accumulated paused time |
| Reviewer cannot reach late states quickly | High | Cheat mode supports skip, freeze, invincibility, life, speed |
| Package not reproducible | High | Root PyInstaller spec + `make package` + packaged instructions |
| Public platform upload unavailable in dev environment | Medium | Keep deterministic build process; owner uploads final generated package |
