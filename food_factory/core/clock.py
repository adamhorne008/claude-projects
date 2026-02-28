# core/clock.py — simulation time and speed control

from dataclasses import dataclass
from settings import (
    SPEED_STEPS, BASE_MINUTE_MS, MINUTES_PER_HOUR,
    HOURS_PER_DAY, DAYS_PER_WEEK, DAY_NAMES
)


@dataclass
class SimTime:
    week: int   = 1
    day: int    = 0   # 0 = Monday, 6 = Sunday
    hour: int   = 6   # start at 6am Monday
    minute: int = 0

    def day_name(self) -> str:
        return DAY_NAMES[self.day]

    def format(self) -> str:
        return f"{self.day_name()}  {self.hour:02d}:{self.minute:02d}"

    def is_sunday(self) -> bool:
        return self.day == 6

    def total_minutes(self) -> int:
        """Total sim minutes elapsed since start of week."""
        return (self.day * HOURS_PER_DAY + self.hour) * MINUTES_PER_HOUR + self.minute


class SimClock:
    """
    Converts real elapsed milliseconds into simulation time.

    Each real millisecond × speed_multiplier accumulates.
    When accumulator exceeds BASE_MINUTE_MS, one sim minute advances.

    Publishes events via the EventBus:
      "SIM_TICK"  — every sim hour
      "NEW_WEEK"  — when Monday 00:00 ticks over
    """

    def __init__(self, event_bus) -> None:
        self._bus = event_bus
        self._speed_index = 1          # default 1x
        self._accum_ms: float = 0.0    # accumulated real ms
        self.time = SimTime()
        self._prev_day = self.time.day

    # --- Speed control ---

    @property
    def speed(self) -> int:
        return SPEED_STEPS[self._speed_index]

    @property
    def paused(self) -> bool:
        return self.speed == 0

    def cycle_speed(self) -> None:
        self._speed_index = (self._speed_index + 1) % len(SPEED_STEPS)

    def set_speed_index(self, index: int) -> None:
        if 0 <= index < len(SPEED_STEPS):
            self._speed_index = index

    # --- Tick ---

    def tick(self, dt_ms: float) -> None:
        """Advance simulation time. dt_ms = real milliseconds since last frame."""
        if self.paused:
            return

        self._accum_ms += dt_ms * self.speed

        while self._accum_ms >= BASE_MINUTE_MS:
            self._accum_ms -= BASE_MINUTE_MS
            self._advance_minute()

    def _advance_minute(self) -> None:
        t = self.time
        t.minute += 1

        if t.minute >= MINUTES_PER_HOUR:
            t.minute = 0
            t.hour += 1
            self._bus.publish("SIM_TICK", {"sim_time": t})

            if t.hour >= HOURS_PER_DAY:
                t.hour = 0
                t.day += 1

                if t.day >= DAYS_PER_WEEK:
                    t.day = 0
                    t.week += 1
                    self._bus.publish("NEW_WEEK", {"week": t.week})
