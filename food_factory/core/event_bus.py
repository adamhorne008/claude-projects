# core/event_bus.py — lightweight publish/subscribe event system

from collections import defaultdict
from typing import Callable


class EventBus:
    """
    Decouples modules by letting them communicate through named events.
    Any module can publish without knowing who is listening.

    Events used across the system:
      "NEW_WEEK"          data: {"week": int}
      "NEW_ORDER"         data: {"order": Order}
      "ORDER_COMPLETE"    data: {"order": Order}
      "TASK_COMPLETE"     data: {"task": Task}
      "WORKER_HIRED"      data: {"dept": str, "worker": Worker}
      "WORKER_FIRED"      data: {"dept": str}
      "SIM_TICK"          data: {"sim_time": SimTime}
    """

    def __init__(self) -> None:
        self._listeners: dict[str, list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: str, callback: Callable) -> None:
        self._listeners[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable) -> None:
        listeners = self._listeners[event_type]
        if callback in listeners:
            listeners.remove(callback)

    def publish(self, event_type: str, data: dict = None) -> None:
        for callback in list(self._listeners[event_type]):
            callback(data or {})


# Global singleton
bus = EventBus()
