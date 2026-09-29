42 PAC-MAN - PACKAGE QUICK START
================================

RUNNING
  Double-click the executable. With no argument it loads the
  configuration bundled inside the package.
  To use your own configuration instead:
      ./pacman42 my-config.json
  The argument must be a .json file.

CONTROLS
  Move              Arrow keys / WASD
  Pause / Resume    P or Esc
  Main menu         M while paused
  Menus             W/S or arrows, Enter to select

REVIEW CHEAT MODE
  C  toggle cheat mode (required before I, F and V)
  I  invincibility
  F  freeze ghosts
  N  skip the current level
  L  add one life
  V  increased player speed

CONFIGURATION
  The file is JSON and accepts full-line comments starting with # or //.
  Missing or invalid values fall back to documented defaults and are
  reported on standard output; the game never shows a traceback.
  Every key is listed in README.md in the source repository.

SAVED DATA
  Highscores are written to your user data directory:
    Linux    ~/.local/share/pacman42/highscores.json
    macOS    ~/Library/Application Support/pacman42/highscores.json
    Windows  %APPDATA%\pacman42\highscores.json
