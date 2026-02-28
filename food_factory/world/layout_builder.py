# world/layout_builder.py — factory build mode: click and drag to place dept zones

from __future__ import annotations
import pygame
from typing import Optional, TYPE_CHECKING
from settings import TILE_SIZE, DEPT_COLORS, STAGE_ORDER, VIEWPORT_H

if TYPE_CHECKING:
    from world.tilemap import TileMap
    from world.camera import Camera
    from core.clock import SimClock


class LayoutBuilder:
    """
    Build mode manager. Press B to toggle.
    While active, the sim clock is paused.
    Player selects a dept type, then clicks and drags on the tile grid
    to define its zone. On mouse-up the zone is committed to the tilemap.
    """

    def __init__(self, tilemap: TileMap, clock: SimClock) -> None:
        self._tilemap = tilemap
        self._clock = clock

        self.active = False
        self.selected_dept: Optional[str] = None
        self._drag_start: Optional[tuple[int, int]] = None   # tile col, row
        self._drag_end: Optional[tuple[int, int]] = None
        self._prev_speed_index = 1

    # ------------------------------------------------------------------
    # Toggle
    # ------------------------------------------------------------------

    def toggle(self) -> None:
        self.active = not self.active
        if self.active:
            self._prev_speed_index = self._clock._speed_index
            self._clock.set_speed_index(0)   # pause
        else:
            self._clock.set_speed_index(self._prev_speed_index)
            self._drag_start = None
            self._drag_end = None

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.Event, camera: Camera) -> bool:
        if not self.active:
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if event.pos[1] >= VIEWPORT_H:
                return False
            wx, wy = camera.screen_to_world(*event.pos)
            col, row = self._tilemap.world_to_tile(wx, wy)
            self._drag_start = (col, row)
            self._drag_end = (col, row)
            return True

        if event.type == pygame.MOUSEMOTION and self._drag_start:
            wx, wy = camera.screen_to_world(*event.pos)
            col, row = self._tilemap.world_to_tile(wx, wy)
            self._drag_end = (col, row)
            return True

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self._drag_start:
            wx, wy = camera.screen_to_world(*event.pos)
            col, row = self._tilemap.world_to_tile(wx, wy)
            self._drag_end = (col, row)
            self._commit_zone()
            self._drag_start = None
            self._drag_end = None
            return True

        return False

    def _commit_zone(self) -> None:
        if not self.selected_dept or not self._drag_start or not self._drag_end:
            return

        c1, r1 = self._drag_start
        c2, r2 = self._drag_end
        col = min(c1, c2)
        row = min(r1, r2)
        w   = abs(c2 - c1) + 1
        h   = abs(r2 - r1) + 1

        # Clamp to map bounds
        col = max(0, col)
        row = max(0, row)
        w   = min(w, self._tilemap.cols - col)
        h   = min(h, self._tilemap.rows - row)

        if w >= 4 and h >= 4:
            self._tilemap.place_dept_zone(self.selected_dept, col, row, w, h)

    # ------------------------------------------------------------------
    # Preview draw
    # ------------------------------------------------------------------

    def draw_overlay(self, screen: pygame.Surface, camera: Camera) -> None:
        if not self.active:
            return

        # Dim the world slightly in build mode
        dim = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 60))
        screen.blit(dim, (0, 0))

        # Highlight existing dept zones
        for dept in self._tilemap.departments.values():
            color = dept.color
            wx = dept.zone_col * TILE_SIZE
            wy = dept.zone_row * TILE_SIZE
            ww = dept.zone_w * TILE_SIZE
            wh = dept.zone_h * TILE_SIZE
            sx, sy = camera.world_to_screen(wx, wy)
            surf = pygame.Surface((ww, wh), pygame.SRCALPHA)
            surf.fill((*color, 40))
            screen.blit(surf, (int(sx), int(sy)))
            pygame.draw.rect(screen, color, (int(sx), int(sy), ww, wh), 2)

        # Drag preview
        if self._drag_start and self._drag_end and self.selected_dept:
            c1, r1 = self._drag_start
            c2, r2 = self._drag_end
            col = min(c1, c2)
            row = min(r1, r2)
            w   = (abs(c2 - c1) + 1) * TILE_SIZE
            h   = (abs(r2 - r1) + 1) * TILE_SIZE
            wx = col * TILE_SIZE
            wy = row * TILE_SIZE
            sx, sy = camera.world_to_screen(wx, wy)
            color = DEPT_COLORS.get(self.selected_dept, (200, 200, 200))
            preview = pygame.Surface((w, h), pygame.SRCALPHA)
            preview.fill((*color, 80))
            screen.blit(preview, (int(sx), int(sy)))
            pygame.draw.rect(screen, color, (int(sx), int(sy), w, h), 3)

        # "BUILD MODE" label
        font = pygame.font.SysFont("Arial", 18, bold=True)
        lbl = font.render("BUILD MODE  (B to exit)", True, (255, 220, 60))
        screen.blit(lbl, (TILE_SIZE, TILE_SIZE))
