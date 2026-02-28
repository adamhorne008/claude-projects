# items/item.py — a single meal-unit moving through the factory pipeline

from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional
from settings import STAGE_ORDER


class ItemStage(Enum):
    RECEIVING  = "receiving"
    PREP       = "prep"
    COOKING    = "cooking"
    QC         = "qc"
    PACKAGING  = "packaging"
    DISPATCH   = "dispatch"
    DELIVERED  = "delivered"


@dataclass
class Item:
    """
    One meal-unit from an Order, physically moving through the factory.
    Tracks which production stage it is at and who (if anyone) is carrying it.
    """
    item_id: str     = field(default_factory=lambda: str(uuid.uuid4())[:8])
    meal_name: str   = ""
    order_id: str    = ""
    stage: str       = "receiving"   # current dept name
    carrier_id: Optional[int] = None  # worker id, or None if not carried

    # Pixel position in world space (set when dropped at a dept)
    world_x: float = 0.0
    world_y: float = 0.0

    # Processing state
    being_processed: bool = False   # True while a worker is working on it
    processed: bool       = False   # True when processing at current stage done
    ready_to_carry: bool  = False   # True when needs a carrier to next dept

    @property
    def next_stage(self) -> Optional[str]:
        """Returns the next dept name in the pipeline, or None if fully dispatched."""
        if self.stage == "delivered":
            return None
        try:
            idx = STAGE_ORDER.index(self.stage)
            if idx + 1 < len(STAGE_ORDER):
                return STAGE_ORDER[idx + 1]
            return "delivered"
        except ValueError:
            return None

    @property
    def is_complete(self) -> bool:
        return self.stage == "delivered"

    def advance_stage(self) -> None:
        """Move to the next stage in the pipeline."""
        nxt = self.next_stage
        if nxt:
            self.stage = nxt
            self.being_processed = False
            self.processed = False
            self.ready_to_carry = False
            self.carrier_id = None

    def __repr__(self) -> str:
        return f"Item({self.item_id} {self.meal_name} @{self.stage})"
