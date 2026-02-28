# world/truck.py — delivery truck entity and manager

from __future__ import annotations
import pygame
from enum import Enum, auto
from typing import TYPE_CHECKING

from settings import TILE_SIZE, SCREEN_W, VIEWPORT_H

if TYPE_CHECKING:
    from world.camera import Camera


class TruckState(Enum):
    INCOMING   = auto()   # driving from right edge toward dispatch
    LOADING    = auto()   # waiting at dispatch drop point
    DEPARTING  = auto()   # driving back to right edge
    GONE       = auto()   # off screen, ready to remove


# Truck dimensions in pixels
TRUCK_W = 80
TRUCK_H = 36
TRUCK_SPEED = 180          # pixels per second (real time)
LOAD_DURATION = 6.0        # real seconds waiting at dispatch


class Truck:
    """
    A truck that arrives at the Dispatch zone to collect a completed order.
    Drives in from the right edge, waits, then departs.
    """

    def __init__(self, order_id: str, target_wx: float, target_wy: float) -> None:
        self.order_id = order_id
        self.state = TruckState.INCOMING

        # Start off-screen to the right
        self.wx: float = float(SCREEN_W + TRUCK_W + 100)
        self.wy: float = target_wy - TRUCK_H // 2

        self._target_wx = target_wx
        self._load_timer = LOAD_DURATION
        self._exit_wx = float(SCREEN_W + TRUCK_W + 200)

    def update(self, dt: float) -> None:
        if self.state == TruckState.INCOMING:
            self.wx -= TRUCK_SPEED * dt
            if self.wx <= self._target_wx:
                self.wx = self._target_wx
                self.state = TruckState.LOADING
                self._load_timer = LOAD_DURATION

        elif self.state == TruckState.LOADING:
            self._load_timer -= dt
            if self._load_timer <= 0:
                self.state = TruckState.DEPARTING

        elif self.state == TruckState.DEPARTING:
            self.wx += TRUCK_SPEED * dt
            if self.wx >= self._exit_wx:
                self.state = TruckState.GONE

    def draw(self, screen: pygame.Surface, camera: Camera) -> None:
        sx, sy = camera.world_to_screen(self.wx, self.wy)
        sx, sy = int(sx), int(sy)

        if not (-TRUCK_W < sx < SCREEN_W + TRUCK_W):
            return

        # Truck body (dark grey)
        body_rect = pygame.Rect(sx, sy, TRUCK_W, TRUCK_H)
        pygame.draw.rect(screen, (70, 70, 80), body_rect, border_radius=4)

        # Cab (yellow, on the left when driving right — right when coming in)
        cab_x = sx + TRUCK_W - 22
        cab_rect = pygame.Rect(cab_x, sy - 6, 22, TRUCK_H + 6)
        pygame.draw.rect(screen, (210, 180, 40), cab_rect, border_radius=3)

        # Window
        win_rect = pygame.Rect(cab_x + 3, sy - 3, 16, 12)
        pygame.draw.rect(screen, (160, 210, 230), win_rect, border_radius=2)

        # Wheels
        for wx_off in [8, TRUCK_W - 16]:
            pygame.draw.circle(screen, (30, 30, 30), (sx + wx_off, sy + TRUCK_H), 8)
            pygame.draw.circle(screen, (80, 80, 80), (sx + wx_off, sy + TRUCK_H), 5)

        # Order ID label
        font = pygame.font.SysFont("Arial", 10, bold=True)
        label = font.render(f"#{self.order_id}", True, (220, 220, 220))
        screen.blit(label, (sx + 4, sy + 4))

        # Loading indicator
        if self.state == TruckState.LOADING:
            pct = 1.0 - (self._load_timer / LOAD_DURATION)
            bar_rect = pygame.Rect(sx, sy - 10, TRUCK_W, 5)
            pygame.draw.rect(screen, (50, 50, 70), bar_rect)
            pygame.draw.rect(screen, (80, 200, 80), pygame.Rect(sx, sy - 10, int(TRUCK_W * pct), 5))

    @property
    def is_done(self) -> bool:
        return self.state == TruckState.GONE

    @property
    def has_loaded(self) -> bool:
        return self.state == TruckState.DEPARTING


class TruckManager:
    """
    Manages all active trucks. Subscribes to ORDER_READY to spawn trucks.
    Calls OrderManager.mark_delivered() when a truck finishes loading.
    """

    def __init__(self, tilemap, event_bus, order_manager) -> None:
        self._tilemap = tilemap
        self._bus = event_bus
        self._order_manager = order_manager
        self._trucks: list[Truck] = []
        self._notified: set[str] = set()   # order_ids already dispatched

        event_bus.subscribe("ORDER_READY", self._on_order_ready)

    def _on_order_ready(self, data: dict) -> None:
        order = data.get("order")
        if not order or order.order_id in self._notified:
            return
        self._notified.add(order.order_id)

        dispatch = self._tilemap.departments.get("dispatch")
        if not dispatch:
            return

        dp = dispatch.get_drop_point()
        if dp:
            wx, wy = self._tilemap.tile_center_world(dp.col, dp.row)
        else:
            wx = (dispatch.zone_col + dispatch.zone_w) * TILE_SIZE
            wy = (dispatch.zone_row + dispatch.zone_h // 2) * TILE_SIZE

        truck = Truck(order_id=order.order_id, target_wx=float(wx), target_wy=float(wy))
        self._trucks.append(truck)

    def update(self, dt: float) -> None:
        for truck in self._trucks:
            truck.update(dt)
            # Notify order manager once loading is complete
            if truck.has_loaded and truck.order_id not in self._get_delivered():
                self._order_manager.mark_delivered(truck.order_id)

        # Remove gone trucks
        self._trucks = [t for t in self._trucks if not t.is_done]

    def _get_delivered(self) -> set[str]:
        from production.order import OrderStatus
        return {o.order_id for o in self._order_manager.orders if o.status == OrderStatus.DELIVERED}

    def draw_all(self, screen: pygame.Surface, camera) -> None:
        for truck in self._trucks:
            truck.draw(screen, camera)
