# workers/worker_manager.py — manages all worker instances

from __future__ import annotations
import pygame
from typing import Optional, TYPE_CHECKING

from settings import DEPT_COLORS, STAGE_ORDER, INITIAL_WORKERS_PER_DEPT
from workers.worker import Worker
from workers.pathfinder import AStar

if TYPE_CHECKING:
    from world.tilemap import TileMap
    from core.clock import SimClock
    from core.event_bus import EventBus


class WorkerManager:
    """
    Creates, removes, and ticks all Worker instances.
    Responds to UI hire/fire requests via the event bus.
    """

    def __init__(
        self,
        tilemap: TileMap,
        task_manager,       # avoid circular import
        clock: SimClock,
        event_bus: EventBus,
    ) -> None:
        self._tilemap = tilemap
        self._task_manager = task_manager
        self._clock = clock
        self._bus = event_bus
        self._pathfinder = AStar()

        self._workers: dict[int, Worker] = {}

        event_bus.subscribe("REQUEST_HIRE", self._on_hire)
        event_bus.subscribe("REQUEST_FIRE", self._on_fire)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def seed_initial_workers(self) -> None:
        for dept_name in STAGE_ORDER:
            for _ in range(INITIAL_WORKERS_PER_DEPT):
                self.hire_worker(dept_name)

    def hire_worker(self, dept_name: str) -> Optional[Worker]:
        dept = self._tilemap.departments.get(dept_name)
        if not dept:
            return None
        if dept.worker_count >= dept.max_workers:
            return None

        # Spawn at the dept's drop point tile
        spawn_tile = dept.get_drop_point()
        if spawn_tile is None:
            # Fallback: use any interior tile
            spawn_tile = self._find_spawn_tile(dept)
        if spawn_tile is None:
            return None

        color = DEPT_COLORS[dept_name]
        worker = Worker(
            home_dept=dept_name,
            color=color,
            tilemap=self._tilemap,
            pathfinder=self._pathfinder,
            task_manager=self._task_manager,
            clock=self._clock,
            spawn_col=spawn_tile.col,
            spawn_row=spawn_tile.row,
        )
        self._workers[worker.worker_id] = worker
        dept.worker_count += 1
        self._bus.publish("WORKER_HIRED", {"dept": dept_name, "worker": worker})
        return worker

    def fire_worker(self, dept_name: str) -> bool:
        dept = self._tilemap.departments.get(dept_name)
        if not dept or dept.worker_count == 0:
            return False

        # Remove the most recently idle worker in this dept
        for wid in reversed(list(self._workers.keys())):
            w = self._workers[wid]
            if w.home_dept == dept_name:
                from workers.worker import WorkerState
                if w.state == WorkerState.IDLE:
                    self._remove_worker(wid, dept)
                    return True

        # If none idle, remove most recently hired
        for wid in reversed(list(self._workers.keys())):
            w = self._workers[wid]
            if w.home_dept == dept_name:
                self._remove_worker(wid, dept)
                return True

        return False

    def _remove_worker(self, worker_id: int, dept) -> None:
        w = self._workers.pop(worker_id, None)
        if w:
            # Release tile occupancy
            t = self._tilemap.get_tile(w.tile_col, w.tile_row)
            if t:
                t.clear_occupant()
            dept.worker_count -= 1
            self._bus.publish("WORKER_FIRED", {"dept": dept.name})

    # ------------------------------------------------------------------
    # Event bus callbacks
    # ------------------------------------------------------------------

    def _on_hire(self, data: dict) -> None:
        self.hire_worker(data["dept"])

    def _on_fire(self, data: dict) -> None:
        self.fire_worker(data["dept"])

    # ------------------------------------------------------------------
    # Update / Draw
    # ------------------------------------------------------------------

    def update(self, dt: float) -> None:
        for worker in list(self._workers.values()):
            worker.update(dt)

    def draw_all(self, screen: pygame.Surface, camera) -> None:
        for worker in self._workers.values():
            wx, wy = worker.world_pos
            if camera.is_visible(wx, wy):
                worker.draw(screen, camera)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_workers_in_dept(self, dept_name: str) -> list[Worker]:
        return [w for w in self._workers.values() if w.home_dept == dept_name]

    def get_worker_count(self, dept_name: str) -> int:
        return sum(1 for w in self._workers.values() if w.home_dept == dept_name)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_spawn_tile(self, dept):
        dc, dr, dw, dh = dept.zone_col, dept.zone_row, dept.zone_w, dept.zone_h
        for r in range(dr + 1, dr + dh - 1):
            for c in range(dc + 1, dc + dw - 1):
                t = self._tilemap.get_tile(c, r)
                if t and t.walkable and t.occupied_by is None:
                    return t
        return None
