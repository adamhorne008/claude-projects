# world/tile.py — single tile on the factory floor

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Tile:
    col: int
    row: int
    walkable: bool          = True
    dept: Optional[str]     = None   # department name this tile belongs to
    is_workstation: bool    = False  # worker can perform work here
    is_drop_point: bool     = False  # items are deposited/picked up here
    is_wall: bool           = False
    is_corridor: bool       = False
    occupied_by: Optional[int] = None  # worker_id currently standing here

    def clear_occupant(self) -> None:
        self.occupied_by = None

    def set_occupant(self, worker_id: int) -> None:
        self.occupied_by = worker_id

    @property
    def center_pixel(self):
        from settings import TILE_SIZE
        return (self.col * TILE_SIZE + TILE_SIZE // 2,
                self.row * TILE_SIZE + TILE_SIZE // 2)
