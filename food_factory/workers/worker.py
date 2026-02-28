# workers/worker.py — autonomous factory worker with state machine

from __future__ import annotations
import pygame
from enum import Enum, auto
from typing import Optional, TYPE_CHECKING

from settings import TILE_SIZE, WORKER_RADIUS, WORKER_SPEED, WORKER_WORK_DURATION

if TYPE_CHECKING:
    from world.tilemap import TileMap
    from world.tile import Tile
    from workers.pathfinder import AStar
    from production.task import Task
    from core.clock import SimClock


class WorkerState(Enum):
    IDLE           = auto()
    MOVING_TO_TASK = auto()   # navigating to workstation
    WORKING        = auto()   # processing item at workstation
    MOVING_TO_PICK = auto()   # moving to pick up processed item
    CARRYING       = auto()   # carrying item to next dept drop point
    DELIVERING     = auto()   # arrived at drop point, depositing
    RETURNING      = auto()   # returning to home dept after delivery


class Worker:
    """
    Autonomous factory worker.

    Movement: interpolates smoothly between tile centres.
    State machine drives behaviour each frame.
    TaskManager is queried for new tasks when IDLE.
    """

    _next_id: int = 0

    def __init__(
        self,
        home_dept: str,
        color: tuple,
        tilemap: TileMap,
        pathfinder: AStar,
        task_manager,       # TaskManager (avoid circular import)
        clock: SimClock,
        spawn_col: int,
        spawn_row: int,
    ) -> None:
        self.worker_id = Worker._next_id
        Worker._next_id += 1

        self.home_dept = home_dept
        self.color = color

        self._tilemap = tilemap
        self._pathfinder = pathfinder
        self._task_manager = task_manager
        self._clock = clock

        # Tile position
        self.tile_col = spawn_col
        self.tile_row = spawn_row

        # Pixel position (world space, sub-tile interpolated)
        cx, cy = tilemap.tile_center_world(spawn_col, spawn_row)
        self.px: float = float(cx)
        self.py: float = float(cy)

        # Movement
        self._path: list[tuple[int, int]] = []
        self._target_px: float = self.px
        self._target_py: float = self.py

        # State
        self.state: WorkerState = WorkerState.IDLE
        self.current_task: Optional[Task] = None
        self.carried_item_id: Optional[str] = None

        # Timers
        self._work_timer: float = 0.0
        self._deliver_timer: float = 0.0
        self._idle_timer: float = 0.0   # small delay before re-querying tasks

    # ------------------------------------------------------------------
    # Main update
    # ------------------------------------------------------------------

    def update(self, dt: float) -> None:
        """dt = real seconds × speed multiplier."""
        {
            WorkerState.IDLE:           self._update_idle,
            WorkerState.MOVING_TO_TASK: self._update_moving,
            WorkerState.WORKING:        self._update_working,
            WorkerState.MOVING_TO_PICK: self._update_moving,
            WorkerState.CARRYING:       self._update_moving,
            WorkerState.DELIVERING:     self._update_delivering,
            WorkerState.RETURNING:      self._update_moving,
        }[self.state](dt)

    # ------------------------------------------------------------------
    # State handlers
    # ------------------------------------------------------------------

    def _update_idle(self, dt: float) -> None:
        self._idle_timer -= dt
        if self._idle_timer > 0:
            return

        task = self._task_manager.get_task_for_worker(self)
        if task:
            self._assign_task(task)
        else:
            self._idle_timer = 0.5   # retry in 0.5 real seconds

    def _update_moving(self, dt: float) -> None:
        if not self._path:
            self._on_arrived()
            return

        speed = WORKER_SPEED * dt
        dx = self._target_px - self.px
        dy = self._target_py - self.py
        dist = (dx * dx + dy * dy) ** 0.5

        if dist <= speed:
            # Snap to target tile
            self.px = self._target_px
            self.py = self._target_py
            prev_col, prev_row = self.tile_col, self.tile_row
            if self._path:
                next_col, next_row = self._path.pop(0)
                self._tilemap.get_tile(prev_col, prev_row).clear_occupant()
                self.tile_col, self.tile_row = next_col, next_row
                t = self._tilemap.get_tile(next_col, next_row)
                if t:
                    t.set_occupant(self.worker_id)
                self._target_px, self._target_py = self._tilemap.tile_center_world(
                    next_col, next_row
                )
            else:
                self._on_arrived()
        else:
            self.px += dx / dist * speed
            self.py += dy / dist * speed

    def _update_working(self, dt: float) -> None:
        self._work_timer -= dt
        if self._work_timer <= 0:
            self._finish_work()

    def _update_delivering(self, dt: float) -> None:
        self._deliver_timer -= dt
        if self._deliver_timer <= 0:
            self._finish_deliver()

    # ------------------------------------------------------------------
    # Task assignment
    # ------------------------------------------------------------------

    def _assign_task(self, task) -> None:
        from production.task import TaskType
        self.current_task = task
        task.assign(self.worker_id)

        if task.task_type == TaskType.PROCESS:
            # Navigate to the workstation tile
            if self._navigate_to(task.target_col, task.target_row):
                self.state = WorkerState.MOVING_TO_TASK
            else:
                self._fail_task()

        elif task.task_type == TaskType.CARRY:
            # Navigate to pick-up drop point
            if self._navigate_to(task.target_col, task.target_row):
                self.state = WorkerState.MOVING_TO_PICK
            else:
                self._fail_task()

    def _navigate_to(self, col: int, row: int) -> bool:
        """Request A* path to (col, row). Returns True if path found."""
        grid = self._tilemap.walkability_grid()
        path = self._pathfinder.find_path(grid, (self.tile_col, self.tile_row), (col, row))
        if path or (col == self.tile_col and row == self.tile_row):
            self._path = list(path)
            if self._path:
                next_col, next_row = self._path[0]
                self._target_px, self._target_py = self._tilemap.tile_center_world(
                    next_col, next_row
                )
            return True
        return False

    # ------------------------------------------------------------------
    # Arrival / completion logic
    # ------------------------------------------------------------------

    def _on_arrived(self) -> None:
        from production.task import TaskType

        if self.current_task is None:
            self.state = WorkerState.IDLE
            return

        task = self.current_task

        if self.state == WorkerState.MOVING_TO_TASK:
            # Arrived at workstation — start processing
            self._work_timer = WORKER_WORK_DURATION
            self.state = WorkerState.WORKING
            task.start()

        elif self.state == WorkerState.MOVING_TO_PICK:
            # Arrived at pick-up point — grab item and head to delivery
            self.carried_item_id = task.item_id
            self._task_manager.on_item_picked_up(task.item_id, self.worker_id)
            if self._navigate_to(task.deliver_col, task.deliver_row):
                self.state = WorkerState.CARRYING
            else:
                self._fail_task()

        elif self.state == WorkerState.CARRYING:
            # Arrived at delivery drop point
            self._deliver_timer = 0.4
            self.state = WorkerState.DELIVERING

        elif self.state == WorkerState.RETURNING:
            self.state = WorkerState.IDLE

    def _finish_work(self) -> None:
        """Processing complete — notify task manager, become IDLE."""
        if self.current_task:
            self._task_manager.complete_task(self.current_task.task_id)
        self.current_task = None
        self.state = WorkerState.IDLE

    def _finish_deliver(self) -> None:
        """Delivery animation done — notify task manager, return home."""
        if self.current_task:
            self._task_manager.complete_task(self.current_task.task_id)
        self.carried_item_id = None
        self.current_task = None

        # Return to home dept
        dept = self._task_manager.departments.get(self.home_dept)
        if dept and dept.drop_point_tiles:
            dp = dept.drop_point_tiles[0]
            if self._navigate_to(dp.col, dp.row):
                self.state = WorkerState.RETURNING
                return
        self.state = WorkerState.IDLE

    def _fail_task(self) -> None:
        if self.current_task:
            self._task_manager.fail_task(self.current_task.task_id)
        self.current_task = None
        self.carried_item_id = None
        self.state = WorkerState.IDLE
        self._idle_timer = 1.0

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def draw(self, screen: pygame.Surface, camera) -> None:
        sx, sy = camera.world_to_screen(self.px, self.py)
        sx, sy = int(sx), int(sy)

        # Body
        pygame.draw.circle(screen, self.color, (sx, sy), WORKER_RADIUS)
        pygame.draw.circle(screen, (200, 200, 200), (sx, sy), WORKER_RADIUS, 2)

        # Carrying indicator
        if self.carried_item_id:
            pygame.draw.circle(screen, (255, 220, 50), (sx, sy - WORKER_RADIUS - 4), 4)

        # State indicator dot
        state_colors = {
            WorkerState.IDLE:           (80, 80, 80),
            WorkerState.MOVING_TO_TASK: (100, 200, 100),
            WorkerState.WORKING:        (255, 180, 0),
            WorkerState.MOVING_TO_PICK: (100, 150, 255),
            WorkerState.CARRYING:       (255, 120, 50),
            WorkerState.DELIVERING:     (200, 80, 200),
            WorkerState.RETURNING:      (120, 120, 120),
        }
        dot_col = state_colors.get(self.state, (255, 255, 255))
        pygame.draw.circle(screen, dot_col, (sx + WORKER_RADIUS - 2, sy - WORKER_RADIUS + 2), 4)

    @property
    def world_pos(self) -> tuple[float, float]:
        return self.px, self.py
