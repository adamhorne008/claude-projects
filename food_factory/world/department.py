# world/department.py — a production zone on the factory floor

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from world.tile import Tile
    from items.item import Item


@dataclass
class Department:
    """
    Represents one production zone. Holds references to its workstation and
    drop-point tiles, and manages the item buffer awaiting processing.
    """
    name: str
    display_name: str
    color: tuple

    # Tile region on the map (in tile coords)
    zone_col: int   = 0
    zone_row: int   = 0
    zone_w: int     = 0
    zone_h: int     = 0

    workstation_tiles: list = field(default_factory=list)  # list[Tile]
    drop_point_tiles: list  = field(default_factory=list)  # list[Tile]

    # Items waiting to be processed at this dept
    item_buffer: list = field(default_factory=list)   # list[Item]

    worker_count: int = 0
    max_workers: int  = 8

    # Throughput stats
    items_processed: int = 0

    def add_item(self, item) -> None:
        if item not in self.item_buffer:
            self.item_buffer.append(item)

    def remove_item(self, item) -> None:
        if item in self.item_buffer:
            self.item_buffer.remove(item)

    def has_pending_items(self) -> bool:
        """Items waiting that haven't started processing yet."""
        return any(
            not i.being_processed and not i.processed
            for i in self.item_buffer
        )

    def get_pending_item(self):
        """Return the first unprocessed item in buffer."""
        for item in self.item_buffer:
            if not item.being_processed and not item.processed:
                return item
        return None

    def get_ready_to_carry_item(self):
        """Return an item that has been processed and needs carrying to next dept."""
        for item in self.item_buffer:
            if item.ready_to_carry and item.carrier_id is None:
                return item
        return None

    def get_free_workstation(self):
        """Return a workstation tile not currently occupied."""
        for tile in self.workstation_tiles:
            if tile.occupied_by is None:
                return tile
        return None

    def get_drop_point(self):
        """Return any drop point tile for this dept."""
        if self.drop_point_tiles:
            return self.drop_point_tiles[0]
        return None

    @property
    def entry_tile(self):
        """The primary drop point — where incoming items are deposited."""
        return self.get_drop_point()

    def __repr__(self) -> str:
        return f"Department({self.name} workers={self.worker_count} buffer={len(self.item_buffer)})"
