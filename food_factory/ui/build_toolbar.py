# ui/build_toolbar.py — department palette shown during build mode

from __future__ import annotations
import pygame
from typing import TYPE_CHECKING
from ui.button import Button
from settings import SCREEN_W, STAGE_ORDER, DEPT_NAMES, DEPT_COLORS, COL_HUD_BG, FONT_SM

if TYPE_CHECKING:
    from world.layout_builder import LayoutBuilder


class BuildToolbar:
    """
    Shown at the top of the screen when build mode is active.
    Contains one button per department type + a Done button.
    Player selects a dept, then drags on the map to place its zone.
    """

    H = 40

    def __init__(self, layout_builder) -> None:
        self._lb = layout_builder
        self._buttons: dict[str, Button] = {}
        self._btn_done: Button

        btn_w = 110
        btn_h = 28
        by = (self.H - btn_h) // 2

        x = 8
        for dept_name in STAGE_ORDER:
            color = DEPT_COLORS[dept_name]
            name  = DEPT_NAMES.get(dept_name, dept_name)
            d = dept_name
            btn = Button(
                pygame.Rect(x, by, btn_w, btn_h),
                name,
                callback=lambda d=d: self._select(d),
            )
            self._buttons[dept_name] = btn
            x += btn_w + 6

        self._btn_done = Button(
            pygame.Rect(SCREEN_W - 90, by, 82, btn_h),
            "Done (B)",
            callback=self._lb.toggle,
        )

    def _select(self, dept_name: str) -> None:
        self._lb.selected_dept = dept_name

    def handle_event(self, event: pygame.Event) -> bool:
        consumed = False
        for btn in self._buttons.values():
            if btn.handle_event(event):
                consumed = True
        self._btn_done.handle_event(event)
        return consumed

    def draw(self, screen: pygame.Surface) -> None:
        # Background bar at top
        bar = pygame.Rect(0, 0, SCREEN_W, self.H)
        pygame.draw.rect(screen, (18, 22, 38), bar)
        pygame.draw.rect(screen, (60, 60, 90), bar, 1)

        for dept_name, btn in self._buttons.items():
            btn.active = (self._lb.selected_dept == dept_name)
            # Tint button with dept color when active
            btn.draw(screen)
            # Small dept color swatch on button
            color = DEPT_COLORS[dept_name]
            swatch = pygame.Rect(btn.rect.x + 4, btn.rect.y + (btn.rect.height - 8) // 2, 8, 8)
            pygame.draw.rect(screen, color, swatch)

        self._btn_done.draw(screen)
