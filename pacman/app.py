"""Graphical application controller, menus, and rendering."""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum

import pygame

from pacman.config import GameConfig
from pacman.game import DOWN, LEFT, RIGHT, UP, GameSession, Phase
from pacman.graphics import (
    BLACK,
    BLUE,
    CYAN,
    FRIGHT,
    GLYPH,
    GRAY,
    GREEN,
    ORANGE,
    PINK,
    RED,
    WHITE,
    YELLOW,
    Color,
    Graphics,
    Image,
    Viewport,
    make_dot,
    make_ghost,
    make_pacman,
)
from pacman.highscores import HighscoreStore
from pacman.maze_adapter import (
    EAST,
    NORTH,
    SOUTH,
    WEST,
    Cell,
    MazeError,
)

GHOST_COLORS: dict[str, Color] = {
    "Blinky": RED,
    "Pinky": PINK,
    "Inky": CYAN,
    "Clyde": ORANGE,
}


class Screen(Enum):
    """Application-level UI screens."""

    MENU = "menu"
    PLAYING = "playing"
    HIGHSCORES = "highscores"
    INSTRUCTIONS = "instructions"
    NAME_ENTRY = "name_entry"
    ERROR = "error"


@dataclass
class LevelArt:
    """Every image buffer rasterised once for the current level."""

    key: tuple[int, int]
    view: Viewport
    maze: Image
    pacgum: Image
    super_pacgum: Image
    pacman: dict[Cell, Image]
    ghosts: dict[str, Image]
    frightened: Image


class PacmanApp:
    """Own the main loop, UI navigation, rendering, and key hooks."""

    def __init__(self, config: GameConfig) -> None:
        self.config = config
        self.graphics = Graphics(config.window_width, config.window_height)
        self.highscores = HighscoreStore(config.highscore_filename)
        self.screen = Screen.MENU
        self.menu_index = 0
        self.menu_items = [
            "Start Game",
            "View Highscores",
            "Instructions",
            "Exit",
        ]
        self.running = True
        self.session: GameSession | None = None
        self.name_input = ""
        self.final_message = ""
        self.error_message = ""
        self.last_player_step = 0.0
        self.last_ghost_step = 0.0
        self.art: LevelArt | None = None

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Run until Exit or window close, always cleaning up pygame."""
        try:
            while self.running:
                now = time.monotonic()
                self._handle_events(now)
                self._update(now)
                self._draw(now)
                self.graphics.tick(60)
        finally:
            self.highscores.save()
            self.graphics.close()

    def _handle_events(self, now: float) -> None:
        for event in self.graphics.events():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self._handle_key(event, now)

    def _handle_key(self, event: pygame.event.Event, now: float) -> None:
        key = event.key
        if self.screen is Screen.MENU:
            self._menu_key(key)
        elif self.screen in (Screen.HIGHSCORES, Screen.INSTRUCTIONS):
            if key in (pygame.K_ESCAPE, pygame.K_BACKSPACE, pygame.K_RETURN):
                self.screen = Screen.MENU
        elif self.screen is Screen.ERROR:
            if key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                self.screen = Screen.MENU
        elif self.screen is Screen.NAME_ENTRY:
            self._name_entry_key(event)
        elif self.screen is Screen.PLAYING and self.session is not None:
            self._game_key(key, now)

    def _menu_key(self, key: int) -> None:
        count = len(self.menu_items)
        if key in (pygame.K_UP, pygame.K_w):
            self.menu_index = (self.menu_index - 1) % count
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.menu_index = (self.menu_index + 1) % count
        elif key in (pygame.K_RETURN, pygame.K_SPACE):
            self._select_menu()

    def _select_menu(self) -> None:
        if self.menu_index == 0:
            self._start_game()
        elif self.menu_index == 1:
            self.screen = Screen.HIGHSCORES
        elif self.menu_index == 2:
            self.screen = Screen.INSTRUCTIONS
        else:
            self.running = False

    def _start_game(self) -> None:
        """Begin a run, surfacing generator failures as an error screen."""
        try:
            self.session = GameSession(self.config)
        except MazeError as exc:
            self.session = None
            self.art = None
            self.error_message = str(exc)
            self.screen = Screen.ERROR
            return
        self.art = None
        self.screen = Screen.PLAYING
        self.last_player_step = time.monotonic()
        self.last_ghost_step = self.last_player_step

    def _game_key(self, key: int, now: float) -> None:
        session = self.session
        if session is None:
            return
        cheat = session.cheat
        if key in (pygame.K_UP, pygame.K_w):
            session.request_direction(UP)
        elif key in (pygame.K_RIGHT, pygame.K_d):
            session.request_direction(RIGHT)
        elif key in (pygame.K_DOWN, pygame.K_s):
            session.request_direction(DOWN)
        elif key in (pygame.K_LEFT, pygame.K_a):
            session.request_direction(LEFT)
        elif key in (pygame.K_p, pygame.K_ESCAPE):
            session.toggle_pause(now)
        elif key == pygame.K_c:
            session.enable_cheat()
        elif key == pygame.K_i and cheat.enabled:
            cheat.invincible = not cheat.invincible
        elif key == pygame.K_f and cheat.enabled:
            cheat.ghosts_frozen = not cheat.ghosts_frozen
        elif key == pygame.K_v and cheat.enabled:
            cheat.speed_boost = not cheat.speed_boost
        elif key == pygame.K_l:
            session.add_life()
        elif key == pygame.K_n:
            self._cheat_skip(session)
        elif key == pygame.K_m and session.pause_started_at is not None:
            self._return_to_menu()

    def _cheat_skip(self, session: GameSession) -> None:
        """Skip a level, keeping generator failures non-fatal."""
        try:
            session.skip_level()
        except MazeError as exc:
            self.error_message = str(exc)
            self.session = None
            self.art = None
            self.screen = Screen.ERROR

    def _return_to_menu(self) -> None:
        self.screen = Screen.MENU
        self.session = None
        self.art = None

    def _name_entry_key(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_RETURN:
            score = self.session.score if self.session else 0
            if self.highscores.add(self.name_input.strip(), score):
                self.name_input = ""
                self._return_to_menu()
            return
        if event.key == pygame.K_BACKSPACE:
            self.name_input = self.name_input[:-1]
            return
        if len(self.name_input) >= 10:
            return
        char = event.unicode
        if char and char.isascii() and (char.isalnum() or char == " "):
            self.name_input += char

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def _update(self, now: float) -> None:
        if self.screen is not Screen.PLAYING or self.session is None:
            return
        session = self.session
        session.check_timeout(now)
        if self._finish_if_over(session):
            return
        if session.pause_started_at is not None:
            return

        interval = self.config.player_step_seconds
        if session.cheat.enabled and session.cheat.speed_boost:
            interval *= 0.6
        ghost_interval = max(0.10, 0.50 - session.level_index * 0.008)

        try:
            if now - self.last_player_step >= interval:
                session.player_step(now)
                self.last_player_step = now
            if now - self.last_ghost_step >= ghost_interval:
                session.ghost_step(now)
                self.last_ghost_step = now
        except MazeError as exc:
            self.error_message = str(exc)
            self.session = None
            self.art = None
            self.screen = Screen.ERROR
            return
        self._finish_if_over(session)

    def _finish_if_over(self, session: GameSession) -> bool:
        """Move to name entry once the run has ended."""
        if session.phase is Phase.PLAYING:
            return False
        won = session.phase is Phase.WON
        self.final_message = "VICTORY!" if won else "GAME OVER"
        self.screen = Screen.NAME_ENTRY
        return True

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _draw(self, now: float) -> None:
        self.graphics.clear(BLACK)
        if self.screen is Screen.MENU:
            self._draw_menu()
        elif self.screen is Screen.HIGHSCORES:
            self._draw_highscores()
        elif self.screen is Screen.INSTRUCTIONS:
            self._draw_instructions()
        elif self.screen is Screen.ERROR:
            self._draw_error()
        elif self.screen is Screen.NAME_ENTRY:
            self._draw_name_entry()
        elif self.screen is Screen.PLAYING and self.session is not None:
            self._draw_game(now)

    def _draw_menu(self) -> None:
        g = self.graphics
        mid = g.width // 2
        g.text("PAC-MAN", mid, 120, YELLOW, "title", True)
        g.text("42 EDITION", mid, 185, CYAN, "normal", True)
        for index, item in enumerate(self.menu_items):
            selected = index == self.menu_index
            color = YELLOW if selected else WHITE
            prefix = "> " if selected else "  "
            g.text(prefix + item, mid, 285 + index * 58, color, "normal", True)
        g.text("TOP SCORES", mid, 555, CYAN, "normal", True)
        top = self.highscores.entries[:5]
        if not top:
            g.text("No scores yet.", mid, 620, GRAY, "small", True)
        for index, entry in enumerate(top, start=1):
            row = f"{index:>2}. {entry.name:<10} {entry.score:>7}"
            g.text(row, mid, 590 + index * 30, GRAY, "small", True)
        g.text(
            "W/S or arrows - Enter to select",
            mid,
            g.height - 45,
            GRAY,
            "small",
            True,
        )

    def _draw_highscores(self) -> None:
        g = self.graphics
        mid = g.width // 2
        g.text("TOP 10 HIGHSCORES", mid, 110, YELLOW, "big", True)
        if not self.highscores.entries:
            g.text("No scores yet.", mid, 300, GRAY, "normal", True)
        for index, entry in enumerate(self.highscores.entries, start=1):
            row = f"{index:>2}. {entry.name:<10} {entry.score:>8} pts"
            color = CYAN if index <= 3 else WHITE
            g.text(row, mid, 180 + index * 47, color, "normal", True)
        g.text(
            "Esc / Enter to return", mid, g.height - 45, GRAY, "small", True
        )

    def _draw_instructions(self) -> None:
        g = self.graphics
        mid = g.width // 2
        g.text("HOW TO PLAY", mid, 80, YELLOW, "big", True)
        lines = [
            "Move: Arrow keys or WASD",
            "Pause / Resume: P or Esc",
            "Eat all pacgums to clear a level.",
            "Power pellets make ghosts edible for a short time.",
            "Score and remaining lives carry between levels.",
            "Timeout: lose one life, the level timer restarts.",
            "",
            "REVIEW CHEAT MODE",
            "C: toggle cheat mode",
            "I: invincibility   F: freeze ghosts",
            "N: skip level      L: extra life",
            "V: increased player speed",
            "When paused, M returns to main menu.",
        ]
        for index, line in enumerate(lines):
            color = CYAN if line == "REVIEW CHEAT MODE" else WHITE
            g.text(line, mid, 160 + index * 43, color, "normal", True)
        g.text(
            "Esc / Enter to return", mid, g.height - 40, GRAY, "small", True
        )

    def _draw_error(self) -> None:
        g = self.graphics
        mid = g.width // 2
        g.text("LEVEL GENERATION FAILED", mid, 220, RED, "big", True)
        g.text(self.error_message[:70], mid, 320, WHITE, "small", True)
        g.text(
            "Reinstall the assigned A-Maze-ing package.",
            mid,
            370,
            GRAY,
            "small",
            True,
        )
        g.text(
            "Press Enter to return to the main menu",
            mid,
            450,
            GRAY,
            "small",
            True,
        )

    def _draw_name_entry(self) -> None:
        g = self.graphics
        mid = g.width // 2
        score = self.session.score if self.session else 0
        g.text(self.final_message, mid, 150, YELLOW, "title", True)
        g.text(f"FINAL SCORE: {score}", mid, 280, CYAN, "big", True)
        g.text(
            "Enter your name (1-10, letters/digits/spaces):",
            mid,
            390,
            WHITE,
            "normal",
            True,
        )
        box = (mid - 190, 445, 380, 70)
        g.fill_rect(box, (25, 25, 45))
        g.frame_rect(box, BLUE, 3)
        g.text(self.name_input + "_", mid, 480, YELLOW, "big", True)
        typed = self.name_input.strip()
        if self.name_input and not HighscoreStore.valid_name(typed):
            g.text("Name is not valid yet.", mid, 555, RED, "small", True)
        g.text(
            "Press Enter to save and return to the menu",
            mid,
            620,
            GRAY,
            "small",
            True,
        )

    # ------------------------------------------------------------------
    # Game view
    # ------------------------------------------------------------------

    def _viewport(self, session: GameSession) -> Viewport:
        maze = session.maze
        max_w = self.graphics.width - 80
        max_h = self.graphics.height - 175
        cell = max(8, min(max_w // maze.width, max_h // maze.height))
        width = cell * maze.width
        height = cell * maze.height
        left = (self.graphics.width - width) // 2
        return Viewport(left, 125, cell, width, height)

    def _build_art(self, session: GameSession) -> LevelArt:
        """Rasterise the maze and every sprite once for this level."""
        view = self._viewport(session)
        maze = session.maze
        image = Image(view.width + 4, view.height + 4, BLACK)
        for y, row in enumerate(maze.walls):
            for x, walls in enumerate(row):
                x0 = x * view.cell
                y0 = y * view.cell
                x1 = x0 + view.cell
                y1 = y0 + view.cell
                if (x, y) in maze.blocked:
                    body = (x0 + 2, y0 + 2, view.cell - 4, view.cell - 4)
                    image.rect(body, GLYPH)
                if walls & NORTH:
                    image.line((x0, y0), (x1, y0), BLUE, 2)
                if walls & EAST:
                    image.line((x1, y0), (x1, y1), BLUE, 2)
                if walls & SOUTH:
                    image.line((x0, y1), (x1, y1), BLUE, 2)
                if walls & WEST:
                    image.line((x0, y0), (x0, y1), BLUE, 2)

        ghost_r = max(5, int(view.cell * 0.32))
        player_r = max(5, int(view.cell * 0.38))
        return LevelArt(
            key=(session.level_index, view.cell),
            view=view,
            maze=image,
            pacgum=make_dot(max(2, view.cell // 10), WHITE),
            super_pacgum=make_dot(max(4, view.cell // 4), YELLOW),
            pacman={
                heading: make_pacman(player_r, heading)
                for heading in (UP, DOWN, LEFT, RIGHT, (0, 0))
            },
            ghosts={
                name: make_ghost(ghost_r, color)
                for name, color in GHOST_COLORS.items()
            },
            frightened=make_ghost(ghost_r, FRIGHT),
        )

    def _level_art(self, session: GameSession) -> LevelArt:
        """Return cached art, rebuilding it only when the level changes."""
        view = self._viewport(session)
        key = (session.level_index, view.cell)
        if self.art is None or self.art.key != key:
            self.art = self._build_art(session)
        return self.art

    def _center(self, cell: Cell, view: Viewport) -> tuple[int, int]:
        return (
            view.x + cell[0] * view.cell + view.cell // 2,
            view.y + cell[1] * view.cell + view.cell // 2,
        )

    def _draw_hud(self, session: GameSession, now: float) -> None:
        g = self.graphics
        levels = len(session.config.levels)
        g.text(f"SCORE {session.score}", 30, 25, WHITE, "normal")
        g.text(f"LIVES {session.lives}", 255, 25, YELLOW, "normal")
        g.text(
            f"LEVEL {session.level_number}/{levels}", 450, 25, CYAN, "normal"
        )
        remaining = session.remaining_time(now)
        color = RED if remaining <= 10 else WHITE
        g.text(f"TIME {remaining}", g.width - 190, 25, color, "normal")
        g.text(
            f"PACGUMS {len(session.pacgums) + len(session.super_pacgums)}",
            30,
            72,
            GRAY,
            "small",
        )
        if session.cheat.enabled:
            flags = []
            if session.cheat.invincible:
                flags.append("INV")
            if session.cheat.ghosts_frozen:
                flags.append("FREEZE")
            if session.cheat.speed_boost:
                flags.append("FAST")
            label = "CHEAT " + ("/".join(flags) or "ON")
            g.text(label, g.width - 260, 72, GREEN, "small")

    def _draw_game(self, now: float) -> None:
        session = self.session
        if session is None:
            return
        g = self.graphics
        art = self._level_art(session)
        view = art.view

        self._draw_hud(session, now)
        g.put_image(art.maze, view.x, view.y)

        for cell in session.pacgums:
            g.put_image_centered(art.pacgum, *self._center(cell, view))
        for cell in session.super_pacgums:
            g.put_image_centered(art.super_pacgum, *self._center(cell, view))

        heading = session.player.direction
        sprite = art.pacman.get(heading, art.pacman[(0, 0)])
        g.put_image_centered(sprite, *self._center(session.player.cell, view))

        frightened = now < session.frightened_until
        # In the last two seconds the frightened sprite alternates with
        # the normal one, warning that the ghosts turn deadly again.
        flashing = session.frightened_ending(now) and int(now * 5) % 2 == 0
        for ghost in session.ghosts:
            if not ghost.active:
                continue
            if frightened and not flashing:
                image = art.frightened
            else:
                image = art.ghosts[ghost.name]
            g.put_image_centered(image, *self._center(ghost.cell, view))

        if session.pause_started_at is not None:
            self._draw_pause_overlay()

    def _draw_pause_overlay(self) -> None:
        g = self.graphics
        box = (g.width // 2 - 235, g.height // 2 - 105, 470, 210)
        g.fill_rect(box, (20, 20, 35))
        g.frame_rect(box, CYAN, 3)
        g.text("PAUSED", g.width // 2, g.height // 2 - 45, YELLOW, "big", True)
        g.text(
            "P / Esc: resume    M: main menu",
            g.width // 2,
            g.height // 2 + 40,
            WHITE,
            "small",
            True,
        )
