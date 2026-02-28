# ui/order_panel.py — scrollable list of active orders

from __future__ import annotations
import pygame
from typing import TYPE_CHECKING
from settings import (
    COL_PANEL_BG, COL_PANEL_BORDER, COL_WHITE, COL_STATUS,
    FONT_SM, FONT_MD, DAY_NAMES
)

if TYPE_CHECKING:
    from production.order_manager import OrderManager


class OrderPanel:
    """
    Displays active orders as scrollable rows with:
      - Client name
      - Meal summary
      - Progress bar
      - Deadline and status badge
    """

    ROW_H = 38

    def __init__(self, rect: pygame.Rect, order_manager: OrderManager) -> None:
        self.rect = rect
        self._om = order_manager
        self._scroll = 0
        self._font_md = pygame.font.SysFont("Arial", FONT_MD, bold=True)
        self._font_sm = pygame.font.SysFont("Arial", FONT_SM)

    def handle_event(self, event: pygame.Event) -> bool:
        if event.type == pygame.MOUSEWHEEL and self.rect.collidepoint(pygame.mouse.get_pos()):
            self._scroll = max(0, self._scroll - event.y * self.ROW_H)
            return True
        return False

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, COL_PANEL_BG, self.rect)
        pygame.draw.rect(surface, COL_PANEL_BORDER, self.rect, 1)

        # Header
        header = self._font_sm.render("ORDERS", True, (160, 160, 200))
        surface.blit(header, (self.rect.x + 6, self.rect.y + 4))

        orders = self._om.get_active_orders()
        if not orders:
            no_orders = self._font_sm.render("No active orders", True, (100, 100, 120))
            surface.blit(no_orders, (self.rect.x + 6, self.rect.y + 22))
            return

        # Clip drawing to panel
        clip = surface.get_clip()
        surface.set_clip(self.rect.inflate(-2, -2))

        y_start = self.rect.y + 20 - self._scroll
        for order in orders:
            ry = y_start
            y_start += self.ROW_H

            if ry + self.ROW_H < self.rect.y:
                continue
            if ry > self.rect.bottom:
                break

            row_rect = pygame.Rect(self.rect.x + 2, ry, self.rect.width - 4, self.ROW_H - 2)

            # Row background
            status_str = order.status.value
            if status_str == "OVERDUE":
                bg = (60, 20, 20)
            elif status_str == "READY":
                bg = (20, 50, 20)
            else:
                bg = (35, 35, 50)
            pygame.draw.rect(surface, bg, row_rect, border_radius=3)

            # Client name
            name_surf = self._font_sm.render(order.client_name, True, COL_WHITE)
            surface.blit(name_surf, (row_rect.x + 4, row_rect.y + 2))

            # Meals summary (truncated)
            summary = order.meals_summary
            if len(summary) > 28:
                summary = summary[:25] + "..."
            meal_surf = self._font_sm.render(summary, True, (160, 160, 180))
            surface.blit(meal_surf, (row_rect.x + 4, row_rect.y + 16))

            # Progress bar
            bar_x = row_rect.x + 160
            bar_w = 80
            bar_h = 8
            bar_y = row_rect.y + (row_rect.height - bar_h) // 2
            pygame.draw.rect(surface, (50, 50, 70), (bar_x, bar_y, bar_w, bar_h), border_radius=3)
            fill_w = int(bar_w * order.progress_pct)
            if fill_w > 0:
                pygame.draw.rect(surface, (60, 180, 60), (bar_x, bar_y, fill_w, bar_h), border_radius=3)

            # Deadline
            deadline_text = f"Due {DAY_NAMES[order.deadline_day][:3]}"
            dl_surf = self._font_sm.render(deadline_text, True, (140, 140, 160))
            surface.blit(dl_surf, (bar_x + bar_w + 6, row_rect.y + 2))

            # Status badge
            status_color = COL_STATUS.get(status_str, (160, 160, 160))
            badge_surf = self._font_sm.render(status_str, True, status_color)
            surface.blit(badge_surf, (bar_x + bar_w + 6, row_rect.y + 18))

        surface.set_clip(clip)

        # Max scroll
        max_scroll = max(0, len(orders) * self.ROW_H - (self.rect.height - 20))
        self._scroll = min(self._scroll, max_scroll)
