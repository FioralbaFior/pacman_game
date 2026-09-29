"""Minimal renderer restricted to MLX-equivalent capabilities.

Every drawing routine writes individual pixels into an off-screen image
buffer, exactly like ``mlx_pixel_put`` on an image created with
``mlx_new_image``. Finished images are pushed to the window in one call,
the equivalent of ``mlx_put_image_to_window``. Static content (the maze,
the sprites) is rasterised once and then only blitted, which is what
keeps the frame budget reasonable.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pygame

Color = tuple[int, int, int]

BLACK: Color = (8, 8, 18)
WHITE: Color = (245, 245, 245)
YELLOW: Color = (255, 220, 0)
BLUE: Color = (45, 105, 255)
DARK_BLUE: Color = (15, 35, 100)
RED: Color = (245, 60, 65)
PINK: Color = (255, 120, 180)
CYAN: Color = (80, 220, 235)
ORANGE: Color = (255, 160, 65)
FRIGHT: Color = (60, 80, 230)
GRAY: Color = (150, 155, 175)
GREEN: Color = (70, 220, 120)
GLYPH: Color = (24, 24, 55)

# Reserved key colour marking pixels that must not be copied to the
# window, the direct analogue of a transparent XPM entry under MLX.
TRANSPARENT: Color = (255, 0, 255)


@dataclass
class Viewport:
    """Maze drawing geometry in window pixels."""

    x: int
    y: int
    cell: int
    width: int
    height: int


class Image:
    """An off-screen pixel buffer, equivalent to an MLX image."""

    def __init__(
        self,
        width: int,
        height: int,
        fill: Color | None = None,
        transparent: bool = False,
    ) -> None:
        self.width = max(1, width)
        self.height = max(1, height)
        self.surface = pygame.Surface((self.width, self.height))
        self.surface.fill(fill if fill is not None else TRANSPARENT)
        if transparent:
            self.surface.set_colorkey(TRANSPARENT)

    def pixel(self, x: int, y: int, color: Color) -> None:
        """Write one pixel when it lies inside the buffer."""
        if 0 <= x < self.width and 0 <= y < self.height:
            self.surface.set_at((x, y), color)

    def line(
        self,
        start: tuple[int, int],
        end: tuple[int, int],
        color: Color,
        width: int = 1,
    ) -> None:
        """Rasterise a thick line with Bresenham's algorithm."""
        x0, y0 = start
        x1, y1 = end
        dx = abs(x1 - x0)
        step_x = 1 if x0 < x1 else -1
        dy = -abs(y1 - y0)
        step_y = 1 if y0 < y1 else -1
        error = dx + dy
        half = max(0, width // 2)
        while True:
            for offset_y in range(-half, half + 1):
                for offset_x in range(-half, half + 1):
                    self.pixel(x0 + offset_x, y0 + offset_y, color)
            if x0 == x1 and y0 == y1:
                break
            doubled = 2 * error
            if doubled >= dy:
                error += dy
                x0 += step_x
            if doubled <= dx:
                error += dx
                y0 += step_y

    def circle(
        self, center: tuple[int, int], radius: int, color: Color
    ) -> None:
        """Fill a circle through direct pixel writes."""
        cx, cy = center
        radius = max(1, radius)
        limit = radius * radius
        for y in range(cy - radius, cy + radius + 1):
            for x in range(cx - radius, cx + radius + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= limit:
                    self.pixel(x, y, color)

    def rect(
        self,
        rect: tuple[int, int, int, int],
        color: Color,
        width: int = 0,
    ) -> None:
        """Fill or outline a rectangle through direct pixel writes."""
        x, y, w, h = rect
        if width <= 0:
            for py in range(y, y + h):
                for px in range(x, x + w):
                    self.pixel(px, py, color)
            return
        for offset in range(width):
            top = y + offset
            bottom = y + h - 1 - offset
            left = x + offset
            right = x + w - 1 - offset
            self.line((left, top), (right, top), color)
            self.line((left, bottom), (right, bottom), color)
            self.line((left, top), (left, bottom), color)
            self.line((right, top), (right, bottom), color)

    def triangle(
        self, points: list[tuple[int, int]], color: Color
    ) -> None:
        """Fill a triangle using barycentric edge signs."""
        if len(points) != 3:
            return
        (x1, y1), (x2, y2), (x3, y3) = points
        min_x, max_x = min(x1, x2, x3), max(x1, x2, x3)
        min_y, max_y = min(y1, y2, y3), max(y1, y2, y3)

        def side(
            px: int, py: int, ax: int, ay: int, bx: int, by: int
        ) -> int:
            return (px - bx) * (ay - by) - (ax - bx) * (py - by)

        for py in range(min_y, max_y + 1):
            for px in range(min_x, max_x + 1):
                d1 = side(px, py, x1, y1, x2, y2)
                d2 = side(px, py, x2, y2, x3, y3)
                d3 = side(px, py, x3, y3, x1, y1)
                negative = d1 < 0 or d2 < 0 or d3 < 0
                positive = d1 > 0 or d2 > 0 or d3 > 0
                if not (negative and positive):
                    self.pixel(px, py, color)


def make_dot(radius: int, color: Color) -> Image:
    """Rasterise a pellet sprite once."""
    size = radius * 2 + 1
    image = Image(size, size, transparent=True)
    image.circle((radius, radius), radius, color)
    return image


def make_ghost(radius: int, color: Color) -> Image:
    """Rasterise a ghost sprite once."""
    size = radius * 2 + 2
    image = Image(size, size + radius // 2, transparent=True)
    cx = cy = radius
    image.circle((cx, cy), radius, color)
    image.rect((cx - radius, cy, radius * 2 + 1, radius + radius // 2), color)
    eye = max(2, radius // 4)
    pupil = max(1, eye // 2)
    for sign in (-1, 1):
        ex = cx + sign * (radius // 3)
        ey = cy - radius // 4
        image.circle((ex, ey), eye, WHITE)
        image.circle((ex, ey), pupil, DARK_BLUE)
    return image


def make_pacman(radius: int, direction: tuple[int, int]) -> Image:
    """Rasterise one Pac-Man orientation once."""
    size = radius * 2 + 1
    image = Image(size, size, transparent=True)
    center = (radius, radius)
    image.circle(center, radius, YELLOW)
    angle = {
        (1, 0): 0.0,
        (0, 1): math.pi / 2,
        (-1, 0): math.pi,
        (0, -1): -math.pi / 2,
    }.get(direction, 0.0)
    spread = 0.45
    reach = radius * 1.6
    points = [
        center,
        (
            int(center[0] + reach * math.cos(angle - spread)),
            int(center[1] + reach * math.sin(angle - spread)),
        ),
        (
            int(center[0] + reach * math.cos(angle + spread)),
            int(center[1] + reach * math.sin(angle + spread)),
        ),
    ]
    image.triangle(points, TRANSPARENT)
    return image


class Graphics:
    """Window, input hooks, text output, and image presentation."""

    def __init__(self, width: int, height: int) -> None:
        pygame.init()
        pygame.font.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("42 Pac-Man")
        self.clock = pygame.time.Clock()
        self.font_small = pygame.font.Font(None, 25)
        self.font = pygame.font.Font(None, 34)
        self.font_big = pygame.font.Font(None, 72)
        self.font_title = pygame.font.Font(None, 110)

    def close(self) -> None:
        """Destroy the graphical context cleanly."""
        pygame.quit()

    def events(self) -> list[pygame.event.Event]:
        """Return pending input and window events."""
        return list(pygame.event.get())

    def tick(self, fps: int = 60) -> None:
        """Present the frame and limit the loop rate."""
        pygame.display.flip()
        self.clock.tick(fps)

    def fps(self) -> float:
        """Return the measured frame rate."""
        return float(self.clock.get_fps())

    def clear(self, color: Color = BLACK) -> None:
        """Clear the window buffer."""
        self.screen.fill(color)

    def put_image(self, image: Image, x: int, y: int) -> None:
        """Copy an image buffer into the window at a corner position."""
        self.screen.blit(image.surface, (x, y))

    def put_image_centered(
        self, image: Image, x: int, y: int
    ) -> None:
        """Copy an image buffer into the window around a center point."""
        self.screen.blit(
            image.surface, (x - image.width // 2, y - image.height // 2)
        )

    def fill_rect(
        self, rect: tuple[int, int, int, int], color: Color
    ) -> None:
        """Fill a window rectangle without going through an image."""
        self.screen.fill(color, pygame.Rect(rect))

    def frame_rect(
        self, rect: tuple[int, int, int, int], color: Color, width: int
    ) -> None:
        """Outline a window rectangle with four filled edges."""
        x, y, w, h = rect
        self.fill_rect((x, y, w, width), color)
        self.fill_rect((x, y + h - width, w, width), color)
        self.fill_rect((x, y, width, h), color)
        self.fill_rect((x + w - width, y, width, h), color)

    def text(
        self,
        message: str,
        x: int,
        y: int,
        color: Color = WHITE,
        size: str = "normal",
        center: bool = False,
    ) -> None:
        """Draw text, equivalent in purpose to mlx_string_put."""
        font = {
            "small": self.font_small,
            "normal": self.font,
            "big": self.font_big,
            "title": self.font_title,
        }.get(size, self.font)
        surface = font.render(message, True, color)
        rect = surface.get_rect()
        if center:
            rect.center = (x, y)
        else:
            rect.topleft = (x, y)
        self.screen.blit(surface, rect)
