# ui/hud.py — root HUD container, always in screen space

from __future__ import annotations
import pygame
from settings import SCREEN_W, SCREEN_H, HUD_HEIGHT, VIEWPORT_H, COL_HUD_BG
from ui.clock_panel import ClockPanel
from ui.department_panel import DepartmentPanel
from ui.order_panel import OrderPanel


class HUD:
    """
    Bottom strip HUD layout (1280 × HUD_HEIGHT):

      x=0      x=220     x=560                x=1280
      +--------+---------+---------------------+
      | Clock  |  Depts  |      Orders         |
      | 220px  |  340px  |      720px          |
      +--------+---------+---------------------+
    """

    CLOCK_W = 200
    DEPT_W  = 360
    ORDER_W = SCREEN_W - CLOCK_W - DEPT_W   # remaining width

    def __init__(self, clock, worker_manager, task_manager, order_manager, event_bus) -> None:
        hud_y = VIEWPORT_H   # HUD starts just below the world viewport

        self._clock_panel = ClockPanel(
            pygame.Rect(0, hud_y, self.CLOCK_W, HUD_HEIGHT),
            clock,
        )
        self._dept_panel = DepartmentPanel(
            pygame.Rect(self.CLOCK_W, hud_y, self.DEPT_W, HUD_HEIGHT),
            worker_manager,
            task_manager,
            event_bus,
        )
        self._order_panel = OrderPanel(
            pygame.Rect(self.CLOCK_W + self.DEPT_W, hud_y, self.ORDER_W, HUD_HEIGHT),
            order_manager,
        )

    def handle_event(self, event: pygame.Event) -> bool:
        if self._clock_panel.handle_event(event):
            return True
        if self._dept_panel.handle_event(event):
            return True
        if self._order_panel.handle_event(event):
            return True
        return False

    def update(self) -> None:
        self._clock_panel.update()
        self._dept_panel.update()

    def draw(self, screen: pygame.Surface) -> None:
        # HUD background bar
        hud_rect = pygame.Rect(0, VIEWPORT_H, SCREEN_W, HUD_HEIGHT)
        pygame.draw.rect(screen, COL_HUD_BG, hud_rect)

        self._clock_panel.draw(screen)
        self._dept_panel.draw(screen)
        self._order_panel.draw(screen)
