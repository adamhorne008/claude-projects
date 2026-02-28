# ui/item_popup.py — popup showing item and order details on click

from __future__ import annotations
import pygame
from typing import Optional, TYPE_CHECKING
from settings import COL_PANEL_BG, COL_PANEL_BORDER, COL_WHITE, COL_STATUS, FONT_SM, FONT_MD, DAY_NAMES

if TYPE_CHECKING:
    from items.item import Item
    from production.order import Order


class ItemPopup:
    """
    Small screen-space popup that appears when the player clicks
    a completed item box in the Dispatch department.
    Dismissed by clicking anywhere outside, or pressing Escape.
    """

    W = 260
    H = 160

    def __init__(self) -> None:
        self._item: Optional[Item] = None
        self._order: Optional[Order] = None
        self.visible = False
        self._rect = pygame.Rect(0, 0, self.W, self.H)
        self._font_md = pygame.font.SysFont("Arial", FONT_MD, bold=True)
        self._font_sm = pygame.font.SysFont("Arial", FONT_SM)

    def show(self, item, order, screen_x: int, screen_y: int) -> None:
        self._item = item
        self._order = order
        # Position popup above the click point, clamped to screen
        from settings import SCREEN_W, VIEWPORT_H
        x = min(screen_x, SCREEN_W - self.W - 4)
        y = max(4, screen_y - self.H - 8)
        self._rect = pygame.Rect(x, y, self.W, self.H)
        self.visible = True

    def dismiss(self) -> None:
        self.visible = False
        self._item = None
        self._order = None

    def handle_event(self, event: pygame.Event) -> bool:
        if not self.visible:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN:
            if not self._rect.collidepoint(event.pos):
                self.dismiss()
            return True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.dismiss()
            return True
        return False

    def draw(self, screen: pygame.Surface) -> None:
        if not self.visible or not self._item:
            return

        # Background
        pygame.draw.rect(screen, (16, 16, 28), self._rect, border_radius=6)
        pygame.draw.rect(screen, COL_PANEL_BORDER, self._rect, 2, border_radius=6)

        x = self._rect.x + 10
        y = self._rect.y + 8

        # Item meal name
        meal_surf = self._font_md.render(self._item.meal_name, True, COL_WHITE)
        screen.blit(meal_surf, (x, y))
        y += meal_surf.get_height() + 6

        # Item ID
        id_surf = self._font_sm.render(f"Item ID: {self._item.item_id}", True, (160, 160, 180))
        screen.blit(id_surf, (x, y)); y += id_surf.get_height() + 3

        # Order info
        if self._order:
            ord_surf = self._font_sm.render(f"Order: #{self._order.order_id}", True, (160, 180, 220))
            screen.blit(ord_surf, (x, y)); y += ord_surf.get_height() + 3

            client_surf = self._font_sm.render(f"Client: {self._order.client_name}", True, COL_WHITE)
            screen.blit(client_surf, (x, y)); y += client_surf.get_height() + 3

            deadline_surf = self._font_sm.render(
                f"Deadline: {DAY_NAMES[self._order.deadline_day]}", True, (200, 160, 100)
            )
            screen.blit(deadline_surf, (x, y)); y += deadline_surf.get_height() + 3

            status_str = self._order.status.value
            status_color = COL_STATUS.get(status_str, (160, 160, 160))
            status_surf = self._font_sm.render(f"Status: {status_str}", True, status_color)
            screen.blit(status_surf, (x, y))
