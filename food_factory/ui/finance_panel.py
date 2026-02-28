# ui/finance_panel.py — financial summary panel in the HUD

from __future__ import annotations
import pygame
from typing import TYPE_CHECKING
from settings import COL_PANEL_BG, COL_PANEL_BORDER, COL_WHITE, FONT_SM, FONT_MD

if TYPE_CHECKING:
    from core.finance_manager import FinanceManager


class FinancePanel:
    """
    Displays the company's financial position:
      Balance | Revenue today | Wages today | Net profit
    """

    def __init__(self, rect: pygame.Rect, finance_manager: FinanceManager) -> None:
        self.rect = rect
        self._fm = finance_manager
        self._font_md = pygame.font.SysFont("Arial", FONT_MD, bold=True)
        self._font_sm = pygame.font.SysFont("Arial", FONT_SM)

    def handle_event(self, event: pygame.Event) -> bool:
        return False

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, COL_PANEL_BG, self.rect)
        pygame.draw.rect(surface, COL_PANEL_BORDER, self.rect, 1)

        fm = self._fm
        x = self.rect.x + 8
        y = self.rect.y + 6

        # Balance
        bal_color = (80, 220, 80) if fm.balance >= 0 else (220, 80, 80)
        bal_surf = self._font_md.render(fm.format_balance(), True, bal_color)
        surface.blit(bal_surf, (x, y))
        y += bal_surf.get_height() + 4

        # Today's revenue / wages
        rev_surf = self._font_sm.render(f"Rev: £{fm.revenue_today:,.0f}", True, (100, 200, 100))
        wg_surf  = self._font_sm.render(f"Wages: £{fm.wages_today:,.0f}", True, (200, 120, 80))
        surface.blit(rev_surf, (x, y))
        surface.blit(wg_surf,  (x, y + rev_surf.get_height() + 2))
        y += rev_surf.get_height() + wg_surf.get_height() + 6

        # Net profit overall
        profit_color = (80, 200, 80) if fm.profit >= 0 else (220, 80, 80)
        pf_surf = self._font_sm.render(f"Profit: {fm.format_profit()}", True, profit_color)
        surface.blit(pf_surf, (x, y))
