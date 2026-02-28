# ui/hud.py — root HUD container, always in screen space

from __future__ import annotations
import pygame
from settings import SCREEN_W, HUD_HEIGHT, VIEWPORT_H, COL_HUD_BG
from ui.clock_panel import ClockPanel
from ui.finance_panel import FinancePanel
from ui.department_panel import DepartmentPanel
from ui.order_panel import OrderPanel


class HUD:
    """
    Bottom strip HUD layout (1280 × HUD_HEIGHT):

      Clock(200) | Finance(180) | Depts(300) | Orders(600) = 1280px
    """

    CLOCK_W   = 200
    FINANCE_W = 180
    DEPT_W    = 300
    ORDER_W   = SCREEN_W - 200 - 180 - 300   # 600px

    def __init__(self, clock, worker_manager, task_manager, order_manager, event_bus, finance_manager=None) -> None:
        hud_y = VIEWPORT_H

        self._clock_panel = ClockPanel(
            pygame.Rect(0, hud_y, self.CLOCK_W, HUD_HEIGHT),
            clock,
        )
        self._finance_panel = FinancePanel(
            pygame.Rect(self.CLOCK_W, hud_y, self.FINANCE_W, HUD_HEIGHT),
            finance_manager,
        ) if finance_manager else None

        dept_x = self.CLOCK_W + self.FINANCE_W
        self._dept_panel = DepartmentPanel(
            pygame.Rect(dept_x, hud_y, self.DEPT_W, HUD_HEIGHT),
            worker_manager,
            task_manager,
            event_bus,
        )
        self._order_panel = OrderPanel(
            pygame.Rect(dept_x + self.DEPT_W, hud_y, self.ORDER_W, HUD_HEIGHT),
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
        hud_rect = pygame.Rect(0, VIEWPORT_H, SCREEN_W, HUD_HEIGHT)
        pygame.draw.rect(screen, COL_HUD_BG, hud_rect)

        self._clock_panel.draw(screen)
        if self._finance_panel:
            self._finance_panel.draw(screen)
        self._dept_panel.draw(screen)
        self._order_panel.draw(screen)
