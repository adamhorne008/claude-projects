# production/task.py — a unit of work to be assigned to a worker

from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from items.item import Item


class TaskType(Enum):
    PROCESS = "PROCESS"   # work on an item at a workstation
    CARRY   = "CARRY"     # pick up item and deliver to next dept


class TaskStatus(Enum):
    QUEUED      = "QUEUED"
    ASSIGNED    = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE    = "COMPLETE"
    FAILED      = "FAILED"


@dataclass
class Task:
    """
    A discrete unit of work. TaskManager creates tasks; workers claim and complete them.
    """
    task_id: str      = field(default_factory=lambda: str(uuid.uuid4())[:8])
    task_type: TaskType   = TaskType.PROCESS
    status: TaskStatus    = TaskStatus.QUEUED

    item_id: str          = ""          # which Item this task is for
    dept: str             = ""          # home department for PROCESS tasks

    # Target tile coordinates (world tile col/row)
    target_col: int       = 0
    target_row: int       = 0

    # For CARRY tasks: where to deliver
    deliver_col: int      = 0
    deliver_row: int      = 0
    deliver_dept: str     = ""

    assigned_worker_id: Optional[int] = None
    work_duration: float  = 4.0         # sim seconds required

    priority: int         = 0           # higher = assigned first

    def assign(self, worker_id: int) -> None:
        self.assigned_worker_id = worker_id
        self.status = TaskStatus.ASSIGNED

    def start(self) -> None:
        self.status = TaskStatus.IN_PROGRESS

    def complete(self) -> None:
        self.status = TaskStatus.COMPLETE

    def fail(self) -> None:
        self.status = TaskStatus.FAILED
        self.assigned_worker_id = None

    def __repr__(self) -> str:
        return f"Task({self.task_id} {self.task_type.value} item={self.item_id} @{self.dept})"
