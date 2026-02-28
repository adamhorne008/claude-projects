# world/camera.py — viewport into the scrollable world map

import pygame
from settings import (
    SCREEN_W, VIEWPORT_H, MAP_COLS, MAP_ROWS,
    TILE_SIZE, CAMERA_SPEED
)


class Camera:
    """
    Maintains a viewport offset (x, y) in world pixels.
    World pixel (0,0) is the top-left corner of the map.
    Screen pixel (0,0) is the top-left corner of the game viewport.

    Coordinate conversion:
      screen = world - camera_offset
      world  = screen + camera_offset
    """

    def __init__(self) -> None:
        self.x: float = 0.0
        self.y: float = 0.0
        self._map_pw = MAP_COLS * TILE_SIZE
        self._map_ph = MAP_ROWS * TILE_SIZE

    def update(self, dt: float, keys) -> None:
        """Pan camera with WASD or arrow keys. dt = real seconds."""
        dx = dy = 0

        if keys[pygame.K_LEFT]  or keys[pygame.K_a]:
            dx -= CAMERA_SPEED * dt
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx += CAMERA_SPEED * dt
        if keys[pygame.K_UP]    or keys[pygame.K_w]:
            dy -= CAMERA_SPEED * dt
        if keys[pygame.K_DOWN]  or keys[pygame.K_s]:
            dy += CAMERA_SPEED * dt

        self.x = max(0.0, min(self.x + dx, self._map_pw - SCREEN_W))
        self.y = max(0.0, min(self.y + dy, self._map_ph - VIEWPORT_H))

    def world_to_screen(self, wx: float, wy: float) -> tuple[float, float]:
        return wx - self.x, wy - self.y

    def screen_to_world(self, sx: float, sy: float) -> tuple[float, float]:
        return sx + self.x, sy + self.y

    def center_on(self, world_x: float, world_y: float) -> None:
        self.x = max(0.0, min(world_x - SCREEN_W / 2, self._map_pw - SCREEN_W))
        self.y = max(0.0, min(world_y - VIEWPORT_H / 2, self._map_ph - VIEWPORT_H))

    @property
    def viewport_rect(self) -> pygame.Rect:
        """Viewport rect in world space — used for culling."""
        return pygame.Rect(int(self.x), int(self.y), SCREEN_W, VIEWPORT_H)

    def is_visible(self, world_x: float, world_y: float, margin: int = 32) -> bool:
        r = self.viewport_rect
        return (r.left - margin < world_x < r.right + margin and
                r.top - margin < world_y < r.bottom + margin)
