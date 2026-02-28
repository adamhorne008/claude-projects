# ui/clock_panel.py — simulation clock display and speed control buttons

from __future__ import annotations
import pygame
from typing import TYPE_CHECKING
from ui.button import Button
from settings import SPEED_STEPS, COL_WHITE, COL_PANEL_BG, COL_PANEL_BORDER, FONT_LG, FONT_SM

if TYPE_CHECKING:
    from core.clock import SimClock


class ClockPanel:
    """
    Displays:
      - Current sim day and time
      - Speed control buttons: [||] [1x] [2x] [4x]
    """

    def __init__(self, rect: pygame.Rect, clock: SimClock) -> None:
        self.rect = rect
        self._clock = clock
        self._font_lg = pygame.font.SysFont("Arial", FONT_LG, bold=True)
        self._font_sm = pygame.font.SysFont("Arial", FONT_SM)

        btn_w, btn_h = 36, 24
        btn_y = rect.y + rect.height - btn_h - 8
        labels = ["||", "1x", "2x", "4x"]
        self._speed_buttons: list[Button] = []
        for i, label in enumerate(labels):
            bx = rect.x + 8 + i * (btn_w + 6)
            idx = i  # capture
            self._speed_buttons.append(Button(
                pygame.Rect(bx, btn_y, btn_w, btn_h),
                label,
                callback=lambda i=idx: self._clock.set_speed_index(i),
            ))

    def handle_event(self, event: pygame.Event) -> bool:
        for btn in self._speed_buttons:
            if btn.handle_event(event):
                return True
        return False

    def update(self) -> None:
        speed = self._clock.speed
        for i, btn in enumerate(self._speed_buttons):
            btn.active = (SPEED_STEPS[i] == speed)

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, COL_PANEL_BG, self.rect)
        pygame.draw.rect(surface, COL_PANEL_BORDER, self.rect, 1)

        t = self._clock.time
        # Day
        day_surf = self._font_lg.render(t.day_name(), True, COL_WHITE)
        surface.blit(day_surf, (self.rect.x + 8, self.rect.y + 8))
        # Time
        time_surf = self._font_sm.render(f"{t.hour:02d}:{t.minute:02d}  Week {t.week}", True, (180, 180, 200))
        surface.blit(time_surf, (self.rect.x + 8, self.rect.y + 36))

        for btn in self._speed_buttons:
            btn.draw(surface)
