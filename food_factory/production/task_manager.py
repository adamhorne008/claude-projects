# production/task_manager.py — generates and coordinates all factory tasks

from __future__ import annotations
from typing import Optional, TYPE_CHECKING

from production.task import Task, TaskType, TaskStatus
from settings import STAGE_ORDER, WORKER_WORK_DURATION

if TYPE_CHECKING:
    from world.tilemap import TileMap
    from world.department import Department
    from items.item import Item
    from workers.worker import Worker
    from core.event_bus import EventBus


class TaskManager:
    """
    The central coordinator between items and workers.

    Workers call get_task_for_worker() when idle.
    OrderManager calls on_item_arrived() when new items enter Receiving.
    Workers call complete_task() or fail_task() when done.

    Data flow:
      Item arrives at dept → task created → worker picks it up →
      worker processes (PROCESS task) → item marked ready_to_carry →
      CARRY task created → carrier worker delivers → item advances stage →
      new PROCESS task created at next dept
    """

    def __init__(self, tilemap: TileMap, event_bus: EventBus) -> None:
        self._tilemap = tilemap
        self._bus = event_bus
        self.departments = tilemap.departments

        self._tasks: dict[str, Task] = {}
        self._pending: list[Task] = []     # unassigned, sorted by priority

    # ------------------------------------------------------------------
    # Called by OrderManager
    # ------------------------------------------------------------------

    def on_item_arrived(self, item) -> None:
        """Item has been placed in a department's buffer. Create a PROCESS task."""
        dept = self.departments.get(item.stage)
        if dept:
            dept.add_item(item)
            self._try_create_process_task(item, dept)

    # ------------------------------------------------------------------
    # Called by WorkerManager / Worker
    # ------------------------------------------------------------------

    def get_task_for_worker(self, worker) -> Optional[Task]:
        """
        Return the highest-priority unassigned task matching the worker's dept.
        Workers only do tasks in their home department (or carry from it).
        """
        for task in self._pending:
            if task.status != TaskStatus.QUEUED:
                continue
            if task.dept == worker.home_dept:
                return task
        return None

    def on_item_picked_up(self, item_id: str, worker_id: int) -> None:
        """Worker has picked up the item at the pick-up point."""
        item = self._find_item(item_id)
        if item:
            item.carrier_id = worker_id

    def complete_task(self, task_id: str) -> None:
        task = self._tasks.get(task_id)
        if not task:
            return

        task.complete()
        self._pending = [t for t in self._pending if t.task_id != task_id]

        item = self._find_item(task.item_id)
        if not item:
            return

        if task.task_type == TaskType.PROCESS:
            # Item has been processed at current stage
            item.being_processed = False
            item.processed = True
            item.ready_to_carry = True
            dept = self.departments.get(item.stage)
            if dept:
                dept.items_processed += 1
            self._try_create_carry_task(item)

        elif task.task_type == TaskType.CARRY:
            # Item delivered to next dept
            old_dept = self.departments.get(item.stage)
            if old_dept:
                old_dept.remove_item(item)
            item.advance_stage()
            new_dept = self.departments.get(item.stage)
            if new_dept:
                # Set item world position to new dept's drop point
                dp = new_dept.get_drop_point()
                if dp:
                    item.world_x, item.world_y = self._tilemap.tile_center_world(dp.col, dp.row)
                self.on_item_arrived(item)
            else:
                # Item has left the factory (delivered)
                self._bus.publish("ITEM_DELIVERED", {"item": item})

    def fail_task(self, task_id: str) -> None:
        task = self._tasks.get(task_id)
        if not task:
            return
        task.fail()
        # Reset item state so task can be recreated
        item = self._find_item(task.item_id)
        if item:
            if task.task_type == TaskType.PROCESS:
                item.being_processed = False
            elif task.task_type == TaskType.CARRY:
                item.ready_to_carry = True
                item.carrier_id = None
        # Re-queue
        task.status = TaskStatus.QUEUED
        task.assigned_worker_id = None
        if task not in self._pending:
            self._pending.append(task)

    # ------------------------------------------------------------------
    # Task creation
    # ------------------------------------------------------------------

    def _try_create_process_task(self, item, dept) -> Optional[Task]:
        if item.being_processed or item.processed:
            return None
        workstation = dept.get_free_workstation()
        if not workstation:
            return None

        item.being_processed = True
        task = Task(
            task_type=TaskType.PROCESS,
            item_id=item.item_id,
            dept=dept.name,
            target_col=workstation.col,
            target_row=workstation.row,
            work_duration=WORKER_WORK_DURATION,
        )
        self._tasks[task.task_id] = task
        self._pending.append(task)
        self._bus.publish("TASK_CREATED", {"task": task})
        return task

    def _try_create_carry_task(self, item) -> Optional[Task]:
        current_dept = self.departments.get(item.stage)
        if not current_dept:
            return None

        next_stage = item.next_stage
        if next_stage is None:
            return None

        next_dept = self.departments.get(next_stage)
        if not next_dept:
            return None

        # Pick-up: exit drop point of current dept
        pick_up_tile = current_dept.drop_point_tiles[-1] if len(current_dept.drop_point_tiles) > 1 else current_dept.get_drop_point()
        # Delivery: entry drop point of next dept
        deliver_tile = next_dept.drop_point_tiles[0] if next_dept.drop_point_tiles else next_dept.get_drop_point()

        if not pick_up_tile or not deliver_tile:
            return None

        item.ready_to_carry = True
        item.carrier_id = None

        task = Task(
            task_type=TaskType.CARRY,
            item_id=item.item_id,
            dept=item.stage,       # carry task belongs to the source dept's workers
            target_col=pick_up_tile.col,
            target_row=pick_up_tile.row,
            deliver_col=deliver_tile.col,
            deliver_row=deliver_tile.row,
            deliver_dept=next_stage,
        )
        self._tasks[task.task_id] = task
        self._pending.append(task)
        self._bus.publish("TASK_CREATED", {"task": task})
        return task

    # ------------------------------------------------------------------
    # Tick — check for stalled items and retry task creation
    # ------------------------------------------------------------------

    def tick(self) -> None:
        """Called each frame. Retry process task creation for items with no task."""
        for dept in self.departments.values():
            pending_item = dept.get_pending_item()
            if pending_item:
                already_queued = any(
                    t.item_id == pending_item.item_id and t.status == TaskStatus.QUEUED
                    for t in self._pending
                )
                if not already_queued:
                    self._try_create_process_task(pending_item, dept)

            carry_item = dept.get_ready_to_carry_item()
            if carry_item:
                already_queued = any(
                    t.item_id == carry_item.item_id
                    and t.task_type.value == "CARRY"
                    and t.status == TaskStatus.QUEUED
                    for t in self._pending
                )
                if not already_queued:
                    self._try_create_carry_task(carry_item)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_pending_count(self, dept_name: str) -> int:
        return sum(1 for t in self._pending if t.dept == dept_name and t.status == TaskStatus.QUEUED)

    def _find_item(self, item_id: str):
        for dept in self.departments.values():
            for item in dept.item_buffer:
                if item.item_id == item_id:
                    return item
        return None
