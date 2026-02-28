# production/order_manager.py — order generation, lifecycle, and pipeline tracking

from __future__ import annotations
import random
from typing import TYPE_CHECKING

from production.order import Order, OrderStatus
from production.recipe_manager import RecipeManager
from items.item import Item
from settings import (
    CLIENT_NAMES,
    ORDERS_PER_WEEK_MIN, ORDERS_PER_WEEK_MAX,
    ITEMS_PER_ORDER_MIN, ITEMS_PER_ORDER_MAX,
    STAGE_ORDER,
)

if TYPE_CHECKING:
    from production.task_manager import TaskManager
    from core.event_bus import EventBus
    from world.tilemap import TileMap


class OrderManager:
    """
    Generates orders each Sunday and tracks their progress through the pipeline.

    Orders arrive at the start of each new week (Monday 00:00 event).
    Items are created and placed in the Receiving buffer immediately.
    """

    def __init__(
        self,
        task_manager: TaskManager,
        tilemap: TileMap,
        event_bus: EventBus,
        recipe_manager: RecipeManager,
    ) -> None:
        self._task_manager = task_manager
        self._tilemap = tilemap
        self._bus = event_bus
        self._rm = recipe_manager

        self.orders: list[Order] = []

        event_bus.subscribe("NEW_WEEK", self._on_new_week)
        event_bus.subscribe("ITEM_DELIVERED", self._on_item_delivered)

    # ------------------------------------------------------------------
    # Event callbacks
    # ------------------------------------------------------------------

    def _on_new_week(self, data: dict) -> None:
        week = data.get("week", 1)
        new_orders = self._generate_orders(week)
        for order in new_orders:
            self.orders.append(order)
            self._spawn_items(order)
            self._bus.publish("NEW_ORDER", {"order": order})

    def _on_item_delivered(self, data: dict) -> None:
        item = data.get("item")
        if not item:
            return
        order = self.get_order_by_id(item.order_id)
        if order and order.progress_pct >= 1.0 and order.status.value not in ("READY", "DELIVERED"):
            order.status = __import__("production.order", fromlist=["OrderStatus"]).OrderStatus.READY
            self._bus.publish("ORDER_READY", {"order": order})

    # ------------------------------------------------------------------
    # Seeding — called at game start to populate week 1 orders
    # ------------------------------------------------------------------

    def seed_initial_orders(self) -> None:
        """Generate starting orders without waiting for the first NEW_WEEK event."""
        initial_orders = self._generate_orders(week=1)
        for order in initial_orders:
            self.orders.append(order)
            self._spawn_items(order)
            self._bus.publish("NEW_ORDER", {"order": order})

    # ------------------------------------------------------------------
    # Order generation
    # ------------------------------------------------------------------

    def mark_delivered(self, order_id: str) -> None:
        """Called by TruckManager after truck departs."""
        order = self.get_order_by_id(order_id)
        if order:
            order.mark_delivered()
            self._bus.publish("ORDER_COMPLETE", {"order": order})

    def _generate_orders(self, week: int) -> list[Order]:
        count = random.randint(ORDERS_PER_WEEK_MIN, ORDERS_PER_WEEK_MAX)
        orders = []
        available_meals = self._rm.recipe_names()
        if not available_meals:
            return orders
        for i in range(count):
            num_meal_types = random.randint(1, min(3, len(available_meals)))
            meal_choices = random.sample(available_meals, num_meal_types)
            total_items = random.randint(ITEMS_PER_ORDER_MIN, ITEMS_PER_ORDER_MAX)
            # Distribute total_items across meal types
            meals: dict[str, int] = {}
            remaining = total_items
            for j, meal in enumerate(meal_choices):
                if j == len(meal_choices) - 1:
                    meals[meal] = remaining
                else:
                    qty = random.randint(1, max(1, remaining - (len(meal_choices) - j - 1)))
                    meals[meal] = qty
                    remaining -= qty

            deadline_day = random.randint(3, 5)  # Thu-Sat

            order = Order(
                client_name=random.choice(CLIENT_NAMES),
                meals=meals,
                arrived_week=week,
                deadline_day=deadline_day,
            )
            orders.append(order)
        return orders

    # ------------------------------------------------------------------
    # Item spawning
    # ------------------------------------------------------------------

    def _spawn_items(self, order: Order) -> None:
        """Create Item objects for each meal unit and place them in Receiving."""
        receiving_dept = self._tilemap.departments.get("receiving")
        if not receiving_dept:
            return

        dp = receiving_dept.get_drop_point()
        wx, wy = self._tilemap.tile_center_world(dp.col, dp.row) if dp else (0.0, 0.0)

        for meal_name, qty in order.meals.items():
            for _ in range(qty):
                item = Item(
                    meal_name=meal_name,
                    order_id=order.order_id,
                    stage="receiving",
                    world_x=float(wx),
                    world_y=float(wy),
                )
                order.items.append(item)
                self._task_manager.on_item_arrived(item)

    # ------------------------------------------------------------------
    # Status update
    # ------------------------------------------------------------------

    def update_order_statuses(self, current_day: int, current_week: int) -> None:
        for order in self.orders:
            order.update_status(current_day, current_week)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_active_orders(self) -> list[Order]:
        return [o for o in self.orders if o.status not in (OrderStatus.DELIVERED,)]

    def get_order_by_id(self, order_id: str) -> Order | None:
        for o in self.orders:
            if o.order_id == order_id:
                return o
        return None

    @property
    def total_orders(self) -> int:
        return len(self.orders)

    @property
    def delivered_count(self) -> int:
        return sum(1 for o in self.orders if o.status == OrderStatus.DELIVERED)
