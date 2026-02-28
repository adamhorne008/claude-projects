# core/finance_manager.py — tracks money, wages, and revenue

from __future__ import annotations
from typing import TYPE_CHECKING

from settings import STARTING_BALANCE, WORKER_HOURLY_WAGE

if TYPE_CHECKING:
    from core.event_bus import EventBus
    from workers.worker_manager import WorkerManager
    from production.recipe_manager import RecipeManager


class FinanceManager:
    """
    Tracks the company's financial position.

    Revenue: added when an order is delivered (sum of recipe RRP × quantity).
    Wages:   deducted each sim hour (£WORKER_HOURLY_WAGE × total worker count).
    """

    def __init__(
        self,
        event_bus: EventBus,
        worker_manager: WorkerManager,
        recipe_manager: RecipeManager,
    ) -> None:
        self._bus = event_bus
        self._wm = worker_manager
        self._rm = recipe_manager

        self.balance: float       = STARTING_BALANCE
        self.total_revenue: float = 0.0
        self.total_wages: float   = 0.0
        self.revenue_today: float = 0.0
        self.wages_today: float   = 0.0

        event_bus.subscribe("ORDER_COMPLETE", self._on_order_complete)
        event_bus.subscribe("SIM_TICK", self._on_sim_tick)

    # ------------------------------------------------------------------
    # Event callbacks
    # ------------------------------------------------------------------

    def _on_order_complete(self, data: dict) -> None:
        order = data.get("order")
        if not order:
            return
        revenue = 0.0
        for meal_name, qty in order.meals.items():
            recipe = self._rm.get_by_name(meal_name)
            if recipe:
                revenue += recipe.rrp_price * qty
        self.balance       += revenue
        self.total_revenue += revenue
        self.revenue_today += revenue

    def _on_sim_tick(self, data: dict) -> None:
        """Called each sim hour."""
        total_workers = len(self._wm._workers)
        wage_cost = total_workers * WORKER_HOURLY_WAGE
        self.balance     -= wage_cost
        self.total_wages += wage_cost
        self.wages_today += wage_cost

        # Reset daily totals at midnight
        sim_time = data.get("sim_time")
        if sim_time and sim_time.hour == 0:
            self.revenue_today = 0.0
            self.wages_today   = 0.0

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    @property
    def profit(self) -> float:
        return self.total_revenue - self.total_wages

    @property
    def profit_today(self) -> float:
        return self.revenue_today - self.wages_today

    def format_balance(self) -> str:
        return f"£{self.balance:,.2f}"

    def format_profit(self) -> str:
        sign = "+" if self.profit >= 0 else ""
        return f"{sign}£{self.profit:,.2f}"
