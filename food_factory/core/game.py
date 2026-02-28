# core/game.py — master game class, main loop

import pygame
import sys
from settings import SCREEN_W, SCREEN_H, VIEWPORT_H, TITLE, FPS, COL_BG

from core.event_bus import bus
from core.clock import SimClock
from world.tilemap import TileMap
from world.camera import Camera
from workers.worker_manager import WorkerManager
from production.task_manager import TaskManager
from production.order_manager import OrderManager
from production.recipe_manager import RecipeManager
from core.finance_manager import FinanceManager
from world.truck import TruckManager
from world.layout_builder import LayoutBuilder
from ui.hud import HUD
from ui.recipe_menu import RecipeMenu
from ui.build_toolbar import BuildToolbar
from ui.item_popup import ItemPopup


class Game:
    """
    Top-level orchestrator. Initialises all subsystems in dependency order,
    then runs the main game loop.

    Initialization order:
      1. pygame + display
      2. EventBus (global singleton) + SimClock
      3. TileMap (builds layout, pre-renders background)
      4. Camera
      5. TaskManager
      6. WorkerManager
      7. OrderManager
      8. HUD
      9. Seed workers and initial orders
    """

    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption(TITLE)
        self._screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self._pg_clock = pygame.time.Clock()

        # Core
        self._clock = SimClock(bus)

        # World
        self._tilemap = TileMap()
        self._tilemap.render_background()
        self._camera = Camera()

        # Center camera on the factory at start
        map_center_x = (self._tilemap.cols // 2) * 32
        map_center_y = (self._tilemap.rows // 2) * 32
        self._camera.center_on(map_center_x, map_center_y)

        # Recipes (must be before TaskManager and OrderManager)
        self._recipe_manager = RecipeManager()

        # Production logic (TaskManager first — WorkerManager depends on it)
        self._task_manager = TaskManager(self._tilemap, bus, self._recipe_manager)

        # Workers
        self._worker_manager = WorkerManager(
            self._tilemap, self._task_manager, self._clock, bus
        )

        # Orders
        self._order_manager = OrderManager(
            self._task_manager, self._tilemap, bus, self._recipe_manager
        )

        # Finance (after WorkerManager and RecipeManager)
        self._finance_manager = FinanceManager(bus, self._worker_manager, self._recipe_manager)

        # Trucks
        self._truck_manager = TruckManager(self._tilemap, bus, self._order_manager)

        # UI
        self._hud = HUD(
            self._clock,
            self._worker_manager,
            self._task_manager,
            self._order_manager,
            bus,
            self._finance_manager,
        )

        # Seed initial orders (no workers — player hires manually)
        self._order_manager.seed_initial_orders()

        # Overlays
        self._recipe_menu = RecipeMenu(self._recipe_manager, self._order_manager)
        self._layout_builder = LayoutBuilder(self._tilemap, self._clock)
        self._build_toolbar = BuildToolbar(self._layout_builder)
        self._item_popup = ItemPopup()

        # Drop point drag state
        self._drag_tile = None      # Tile being dragged
        self._drag_dept = None      # dept name of dragged tile
        self._drag_preview: tuple | None = None  # (col, row) hover preview

        self._running = True
        self._debug = False

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self) -> None:
        while self._running:
            dt_ms = self._pg_clock.tick(FPS)
            dt = dt_ms / 1000.0

            self._handle_events()
            self._update(dt, dt_ms)
            self._draw()

        pygame.quit()
        sys.exit()

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self._recipe_menu.visible:
                        self._recipe_menu.hide()
                    else:
                        self._running = False
                elif event.key == pygame.K_SPACE:
                    if not self._recipe_menu.visible:
                        self._clock.cycle_speed()
                elif event.key == pygame.K_F1:
                    self._debug = not self._debug
                elif event.key == pygame.K_m:
                    self._recipe_menu.toggle()
                elif event.key == pygame.K_b:
                    self._layout_builder.toggle()

            # Recipe menu consumes all events when open
            if self._recipe_menu.handle_event(event):
                continue

            # Build mode intercepts mouse in world
            if self._layout_builder.active:
                if self._build_toolbar.handle_event(event):
                    continue
                if self._layout_builder.handle_event(event, self._camera):
                    continue

            # Item popup handles events first
            if self._item_popup.handle_event(event):
                continue

            # Drop point drag
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._on_mouse_down(event.pos)
            if event.type == pygame.MOUSEMOTION:
                self._on_mouse_move(event.pos)
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self._on_mouse_up(event.pos)

            # Give HUD first chance to consume the event
            if self._hud.handle_event(event):
                continue

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def _update(self, dt: float, dt_ms: float) -> None:
        # Advance simulation time
        self._clock.tick(dt_ms)

        # Camera pan (keyboard)
        keys = pygame.key.get_pressed()
        self._camera.update(dt, keys)

        # Production tick (retry stalled tasks)
        self._task_manager.tick()

        # Update order statuses
        t = self._clock.time
        self._order_manager.update_order_statuses(t.day, t.week)

        # Worker AI — scaled by sim speed
        speed = max(1, self._clock.speed)  # at least 1x for smooth movement
        self._worker_manager.update(dt * speed)

        # Trucks (real-time, not sim-scaled)
        self._truck_manager.update(dt)

        # HUD
        self._hud.update()

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def _draw(self) -> None:
        self._screen.fill(COL_BG)

        # World
        self._tilemap.draw(self._screen, self._camera)
        self._worker_manager.draw_all(self._screen, self._camera)
        self._truck_manager.draw_all(self._screen, self._camera)

        # Debug overlay
        if self._debug:
            self._draw_debug()

        # HUD (always on top, screen space)
        self._hud.draw(self._screen)

        # Dispatch item boxes
        self._draw_dispatch_items()

        # Build mode overlay and toolbar
        if self._layout_builder.active:
            self._layout_builder.draw_overlay(self._screen, self._camera)
            self._build_toolbar.draw(self._screen)

        # Drop point drag preview
        if self._drag_preview:
            col, row = self._drag_preview
            wx, wy = self._tilemap.tile_center_world(col, row)
            sx, sy = self._camera.world_to_screen(wx, wy)
            from settings import TILE_SIZE
            preview_rect = pygame.Rect(int(sx) - TILE_SIZE // 2, int(sy) - TILE_SIZE // 2, TILE_SIZE, TILE_SIZE)
            preview_surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
            preview_surf.fill((255, 255, 100, 80))
            self._screen.blit(preview_surf, preview_rect.topleft)
            pygame.draw.rect(self._screen, (255, 255, 100), preview_rect, 2)

        # Modals (drawn over HUD)
        self._recipe_menu.draw(self._screen)
        self._item_popup.draw(self._screen)

        # Speed indicator overlay (top-right)
        self._draw_speed_indicator()

        pygame.display.flip()

    def _draw_dispatch_items(self) -> None:
        """Draw small clickable boxes for items sitting in Dispatch."""
        from settings import TILE_SIZE
        dispatch = self._tilemap.departments.get("dispatch")
        if not dispatch:
            return
        for i, item in enumerate(dispatch.item_buffer):
            box_wx = dispatch.zone_col * TILE_SIZE + 16 + (i % 4) * 14
            box_wy = dispatch.zone_row * TILE_SIZE + 16 + (i // 4) * 14
            if not self._camera.is_visible(box_wx, box_wy, margin=20):
                continue
            sx, sy = self._camera.world_to_screen(box_wx, box_wy)
            sx, sy = int(sx), int(sy)
            pygame.draw.rect(self._screen, (180, 120, 60), (sx, sy, 12, 12), border_radius=2)
            pygame.draw.rect(self._screen, (230, 180, 100), (sx, sy, 12, 12), 1, border_radius=2)

    def _on_mouse_down(self, pos: tuple) -> None:
        from settings import VIEWPORT_H, TILE_SIZE
        if pos[1] >= VIEWPORT_H:
            return   # click in HUD, not world

        # Check dispatch item boxes first
        dispatch = self._tilemap.departments.get("dispatch")
        if dispatch:
            for i, item in enumerate(dispatch.item_buffer):
                box_wx = dispatch.zone_col * TILE_SIZE + 16 + (i % 4) * 14
                box_wy = dispatch.zone_row * TILE_SIZE + 16 + (i // 4) * 14
                sx, sy = self._camera.world_to_screen(box_wx, box_wy)
                box_rect = pygame.Rect(int(sx), int(sy), 12, 12)
                if box_rect.collidepoint(pos):
                    order = self._order_manager.get_order_by_id(item.order_id)
                    self._item_popup.show(item, order, pos[0], pos[1])
                    return

        wx, wy = self._camera.screen_to_world(*pos)
        col, row = self._tilemap.world_to_tile(wx, wy)
        tile = self._tilemap.get_tile(col, row)
        if tile and tile.is_drop_point and tile.dept:
            self._drag_tile = tile
            self._drag_dept = tile.dept

    def _on_mouse_move(self, pos: tuple) -> None:
        if self._drag_tile:
            wx, wy = self._camera.screen_to_world(*pos)
            col, row = self._tilemap.world_to_tile(wx, wy)
            self._drag_preview = (col, row)

    def _on_mouse_up(self, pos: tuple) -> None:
        if self._drag_tile and self._drag_dept:
            wx, wy = self._camera.screen_to_world(*pos)
            col, row = self._tilemap.world_to_tile(wx, wy)
            self._tilemap.move_drop_point(self._drag_tile, col, row, self._drag_dept)
        self._drag_tile = None
        self._drag_dept = None
        self._drag_preview = None

    def _draw_speed_indicator(self) -> None:
        font = pygame.font.SysFont("Arial", 14)
        speed = self._clock.speed
        label = "PAUSED" if speed == 0 else f"{speed}x"
        color = (220, 80, 80) if speed == 0 else (100, 200, 100)
        surf = font.render(label, True, color)
        self._screen.blit(surf, (SCREEN_W - surf.get_width() - 10, 8))

    def _draw_debug(self) -> None:
        font = pygame.font.SysFont("Arial", 12)
        lines = [
            f"FPS: {self._pg_clock.get_fps():.0f}",
            f"Workers: {len(self._worker_manager._workers)}",
            f"Orders: {len(self._order_manager.orders)}",
            f"Pending tasks: {sum(self._task_manager.get_pending_count(d) for d in self._tilemap.departments)}",
        ]
        for i, line in enumerate(lines):
            surf = font.render(line, True, (200, 200, 100))
            self._screen.blit(surf, (8, 8 + i * 16))
