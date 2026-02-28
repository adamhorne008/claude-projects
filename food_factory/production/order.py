# production/order.py — an order from a client for a set of meals

from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from items.item import Item
    from core.clock import SimTime


class OrderStatus(Enum):
    PENDING     = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    READY       = "READY"
    DELIVERED   = "DELIVERED"
    OVERDUE     = "OVERDUE"


@dataclass
class Order:
    """
    A client order containing one or more meal types.
    Each meal unit becomes a separate Item in the production pipeline.
    """
    order_id: str    = field(default_factory=lambda: str(uuid.uuid4())[:8])
    client_name: str = ""
    meals: dict[str, int] = field(default_factory=dict)   # {"Burger": 3, "Salad": 2}

    arrived_week: int = 0
    deadline_day: int = 5   # 0=Mon, 5=Sat (orders arrive Sunday, due by Saturday)

    status: OrderStatus = OrderStatus.PENDING
    items: list = field(default_factory=list)   # list[Item]

    @property
    def total_items(self) -> int:
        return len(self.items)

    @property
    def completed_items(self) -> int:
        return sum(1 for item in self.items if item.is_complete)

    @property
    def progress_pct(self) -> float:
        if not self.items:
            return 0.0
        return self.completed_items / self.total_items

    @property
    def meals_summary(self) -> str:
        parts = [f"{count}x {name}" for name, count in self.meals.items()]
        return ", ".join(parts)

    def update_status(self, current_day: int, current_week: int) -> None:
        if self.status == OrderStatus.DELIVERED:
            return
        if self.progress_pct >= 1.0:
            self.status = OrderStatus.READY
        elif current_week > self.arrived_week and current_day > self.deadline_day:
            self.status = OrderStatus.OVERDUE
        elif self.completed_items > 0:
            self.status = OrderStatus.IN_PROGRESS

    def mark_delivered(self) -> None:
        self.status = OrderStatus.DELIVERED

    def __repr__(self) -> str:
        return f"Order({self.order_id} {self.client_name} {self.meals_summary})"
