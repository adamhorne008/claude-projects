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
from ui.hud import HUD


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

        # Production logic (TaskManager first — WorkerManager depends on it)
        self._task_manager = TaskManager(self._tilemap, bus)

        # Workers
        self._worker_manager = WorkerManager(
            self._tilemap, self._task_manager, self._clock, bus
        )

        # Orders
        self._order_manager = OrderManager(self._task_manager, self._tilemap, bus)

        # UI
        self._hud = HUD(
            self._clock,
            self._worker_manager,
            self._task_manager,
            self._order_manager,
            bus,
        )

        # Seed
        self._worker_manager.seed_initial_workers()
        self._order_manager.seed_initial_orders()

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
                    self._running = False
                elif event.key == pygame.K_SPACE:
                    self._clock.cycle_speed()
                elif event.key == pygame.K_F1:
                    self._debug = not self._debug

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

        # Debug overlay
        if self._debug:
            self._draw_debug()

        # HUD (always on top, screen space)
        self._hud.draw(self._screen)

        # Speed indicator overlay (top-right)
        self._draw_speed_indicator()

        pygame.display.flip()

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
