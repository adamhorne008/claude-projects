# ui/button.py — reusable clickable button widget

from __future__ import annotations
import pygame
from settings import (
    COL_BTN_NORMAL, COL_BTN_HOVER, COL_BTN_ACTIVE,
    COL_BTN_DISABLED, COL_BTN_TEXT, FONT_SM
)


class Button:
    def __init__(
        self,
        rect: pygame.Rect,
        label: str,
        callback=None,
        active: bool = False,
        enabled: bool = True,
        font_size: int = FONT_SM,
    ) -> None:
        self.rect = rect
        self.label = label
        self.callback = callback
        self.active = active
        self.enabled = enabled
        self._hover = False
        self._font = pygame.font.SysFont("Arial", font_size, bold=True)

    def handle_event(self, event: pygame.Event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            self._hover = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.enabled and self.rect.collidepoint(event.pos):
                if self.callback:
                    self.callback()
                return True
        return False

    def draw(self, surface: pygame.Surface) -> None:
        if not self.enabled:
            color = COL_BTN_DISABLED
        elif self.active:
            color = COL_BTN_ACTIVE
        elif self._hover:
            color = COL_BTN_HOVER
        else:
            color = COL_BTN_NORMAL

        pygame.draw.rect(surface, color, self.rect, border_radius=4)
        pygame.draw.rect(surface, (80, 80, 110), self.rect, 1, border_radius=4)

        text_surf = self._font.render(self.label, True, COL_BTN_TEXT)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)
