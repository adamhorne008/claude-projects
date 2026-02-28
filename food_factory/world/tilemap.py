# world/tilemap.py — tile grid, department layout, and background rendering

from __future__ import annotations
import pygame
from settings import (
    MAP_COLS, MAP_ROWS, TILE_SIZE,
    COL_FLOOR, COL_WALL, COL_CORRIDOR, COL_GRID_LINE,
    DEPT_COLORS, DEPT_NAMES, STAGE_ORDER
)
from world.tile import Tile
from world.department import Department


# --- Department zone definitions (col_start, row_start, width, height) ---
# Map is 80 cols × 60 rows. Six bands separated by 2-tile corridors.
# Layout: [RECV 12][COR 2][PREP 12][COR 2][COOK 12][COR 2][QC 12][COR 2][PACK 12][COR 2][DISP 12] = 80 cols
_ZONE_DEFS = {
    "receiving": (0,  0, 12, 60),
    "prep":      (14, 0, 12, 60),
    "cooking":   (28, 0, 12, 60),
    "qc":        (42, 0, 12, 60),
    "packaging": (56, 0, 12, 60),
    "dispatch":  (68, 0, 12, 60),
}

# Corridors at cols: 12-13, 26-27, 40-41, 54-55, 66-67 (start col, width 2)
_CORRIDOR_COLS = [12, 26, 40, 54, 66]

# Workstations: 4 per dept, evenly spaced vertically within zone interior
_WORKSTATIONS_PER_DEPT = 4
# Drop points: one on each side (entry left edge, exit right edge of zone)
_DROP_POINTS_PER_DEPT = 2


class TileMap:
    """
    Owns the 2D grid of Tile objects and all Department instances.
    Pre-renders the background surface once for fast blitting each frame.
    """

    def __init__(self) -> None:
        self.cols = MAP_COLS
        self.rows = MAP_ROWS
        self.tiles: list[list[Tile]] = []
        self.departments: dict[str, Department] = {}
        self._bg: pygame.Surface | None = None

        self._build_grid()
        self._build_departments()
        self._place_workstations()
        self._place_drop_points()

    # ------------------------------------------------------------------
    # Grid construction
    # ------------------------------------------------------------------

    def _build_grid(self) -> None:
        """Initialize all tiles as walkable floor, then carve walls and corridors."""
        self.tiles = [
            [Tile(col=c, row=r) for c in range(self.cols)]
            for r in range(self.rows)
        ]

        # Mark corridor columns
        corridor_col_set = set()
        for start in _CORRIDOR_COLS:
            for c in range(start, start + 2):
                corridor_col_set.add(c)

        for r in range(self.rows):
            for c in range(self.cols):
                tile = self.tiles[r][c]
                if c in corridor_col_set:
                    tile.is_corridor = True
                    tile.walkable = True
                    tile.dept = None

        # Mark dept zones
        for dept_name, (dc, dr, dw, dh) in _ZONE_DEFS.items():
            for r in range(dr, dr + dh):
                for c in range(dc, dc + dw):
                    tile = self.tiles[r][c]
                    # Wall: perimeter of zone (except corridor-facing sides)
                    on_left  = (c == dc)
                    on_right = (c == dc + dw - 1)
                    on_top   = (r == dr)
                    on_bot   = (r == dr + dh - 1)
                    if on_top or on_bot or on_left or on_right:
                        tile.is_wall = True
                        tile.walkable = False
                    else:
                        tile.dept = dept_name
                        tile.walkable = True

        # Punch doorways in walls (corridor-adjacent wall tiles become walkable)
        for dept_name, (dc, dr, dw, dh) in _ZONE_DEFS.items():
            # Left doorways (connect to left corridor)
            if dc > 0:
                for gap_r in [dr + dh // 3, dr + 2 * dh // 3]:
                    t = self.tiles[gap_r][dc]
                    t.is_wall = False
                    t.walkable = True
                    t.dept = dept_name
            # Right doorways
            if dc + dw < self.cols:
                for gap_r in [dr + dh // 3, dr + 2 * dh // 3]:
                    t = self.tiles[gap_r][dc + dw - 1]
                    t.is_wall = False
                    t.walkable = True
                    t.dept = dept_name

    # ------------------------------------------------------------------
    # Departments
    # ------------------------------------------------------------------

    def _build_departments(self) -> None:
        for dept_name, (dc, dr, dw, dh) in _ZONE_DEFS.items():
            dept = Department(
                name=dept_name,
                display_name=DEPT_NAMES[dept_name],
                color=DEPT_COLORS[dept_name],
                zone_col=dc, zone_row=dr,
                zone_w=dw, zone_h=dh,
            )
            self.departments[dept_name] = dept

    def _place_workstations(self) -> None:
        for dept_name, dept in self.departments.items():
            dc, dr, dw, dh = dept.zone_col, dept.zone_row, dept.zone_w, dept.zone_h
            # Place workstations in two columns inside the zone, evenly spaced rows
            ws_col_offsets = [dw // 4, 3 * dw // 4]
            row_spacing = dh // (_WORKSTATIONS_PER_DEPT // 2 + 1)
            for col_off in ws_col_offsets:
                wc = dc + col_off
                for i in range(1, _WORKSTATIONS_PER_DEPT // 2 + 1):
                    wr = dr + row_spacing * i
                    if 0 <= wr < self.rows and 0 <= wc < self.cols:
                        tile = self.tiles[wr][wc]
                        if not tile.is_wall and not tile.is_corridor:
                            tile.is_workstation = True
                            dept.workstation_tiles.append(tile)

    def _place_drop_points(self) -> None:
        for dept_name, dept in self.departments.items():
            dc, dr, dw, dh = dept.zone_col, dept.zone_row, dept.zone_w, dept.zone_h
            mid_row = dr + dh // 2
            # Entry drop point: just inside left wall
            entry_col = dc + 1
            if 0 <= entry_col < self.cols:
                tile = self.tiles[mid_row][entry_col]
                tile.is_drop_point = True
                dept.drop_point_tiles.append(tile)
            # Exit drop point: just inside right wall
            exit_col = dc + dw - 2
            if 0 <= exit_col < self.cols:
                tile = self.tiles[mid_row][exit_col]
                tile.is_drop_point = True
                dept.drop_point_tiles.append(tile)

    # ------------------------------------------------------------------
    # Background pre-render
    # ------------------------------------------------------------------

    def render_background(self) -> None:
        """Pre-render the entire map to a surface. Call once after layout."""
        w = self.cols * TILE_SIZE
        h = self.rows * TILE_SIZE
        self._bg = pygame.Surface((w, h))
        self._bg.fill((20, 20, 28))

        for r in range(self.rows):
            for c in range(self.cols):
                tile = self.tiles[r][c]
                x = c * TILE_SIZE
                y = r * TILE_SIZE
                rect = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)

                if tile.is_wall:
                    color = COL_WALL
                elif tile.is_corridor:
                    color = COL_CORRIDOR
                elif tile.dept:
                    base = DEPT_COLORS[tile.dept]
                    # Slightly darken interior
                    color = tuple(max(0, v - 30) for v in base)
                    if tile.is_workstation:
                        color = tuple(min(255, v + 40) for v in base)
                    elif tile.is_drop_point:
                        color = tuple(min(255, v + 20) for v in base)
                else:
                    color = COL_FLOOR

                pygame.draw.rect(self._bg, color, rect)

                # Grid lines (only on walkable tiles, faint)
                if tile.walkable:
                    pygame.draw.rect(self._bg, COL_GRID_LINE, rect, 1)

                # Workstation marker
                if tile.is_workstation:
                    cx = x + TILE_SIZE // 2
                    cy = y + TILE_SIZE // 2
                    pygame.draw.circle(self._bg, (255, 255, 255, 60), (cx, cy), 6, 2)

                # Drop point marker
                if tile.is_drop_point:
                    pygame.draw.rect(self._bg, (255, 255, 255), rect.inflate(-20, -20), 2)

        # Department name labels
        font = pygame.font.SysFont("Arial", 14, bold=True)
        for dept_name, dept in self.departments.items():
            dc, dr = dept.zone_col, dept.zone_row
            x = dc * TILE_SIZE + 4
            y = dr * TILE_SIZE + 4
            label = font.render(dept.display_name, True, (255, 255, 255))
            self._bg.blit(label, (x, y))

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self, screen: pygame.Surface, camera) -> None:
        if self._bg is None:
            return
        vp = camera.viewport_rect
        # Clip to only the visible region
        clip_rect = pygame.Rect(
            int(camera.x), int(camera.y),
            min(screen.get_width(), self._bg.get_width() - int(camera.x)),
            min(screen.get_height(), self._bg.get_height() - int(camera.y))
        )
        screen.blit(self._bg, (0, 0), clip_rect)

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def get_tile(self, col: int, row: int) -> Tile | None:
        if 0 <= col < self.cols and 0 <= row < self.rows:
            return self.tiles[row][col]
        return None

    def is_walkable(self, col: int, row: int) -> bool:
        t = self.get_tile(col, row)
        return t is not None and t.walkable

    def tile_center_world(self, col: int, row: int) -> tuple[int, int]:
        return (col * TILE_SIZE + TILE_SIZE // 2,
                row * TILE_SIZE + TILE_SIZE // 2)

    def world_to_tile(self, wx: float, wy: float) -> tuple[int, int]:
        return int(wx // TILE_SIZE), int(wy // TILE_SIZE)

    def walkability_grid(self) -> list[list[bool]]:
        """Returns a 2D grid of booleans for the pathfinder."""
        return [
            [self.tiles[r][c].walkable for c in range(self.cols)]
            for r in range(self.rows)
        ]

    def move_drop_point(self, old_tile: "Tile", new_col: int, new_row: int, dept_name: str) -> bool:
        """
        Move a drop point from old_tile to (new_col, new_row).
        Validates: target must be walkable, inside the dept zone, not a wall.
        Returns True if successfully moved.
        """
        dept = self.departments.get(dept_name)
        if not dept:
            return False

        new_tile = self.get_tile(new_col, new_row)
        if not new_tile:
            return False
        if new_tile.is_wall or not new_tile.walkable:
            return False

        # Must be within dept zone
        if not (dept.zone_col <= new_col < dept.zone_col + dept.zone_w and
                dept.zone_row <= new_row < dept.zone_row + dept.zone_h):
            return False

        # Move drop point
        old_tile.is_drop_point = False
        new_tile.is_drop_point = True
        new_tile.dept = dept_name

        # Update department's drop_point_tiles list
        if old_tile in dept.drop_point_tiles:
            idx = dept.drop_point_tiles.index(old_tile)
            dept.drop_point_tiles[idx] = new_tile

        # Refresh background
        self.render_background()
        return True

    def place_dept_zone(self, dept_name: str, col: int, row: int, w: int, h: int) -> bool:
        """
        Place or replace a department zone at (col, row) with size (w, h).
        Clears old zone tiles, writes new ones, adds workstations and drop points.
        """
        from settings import DEPT_COLORS, DEPT_NAMES

        if w < 4 or h < 4:
            return False

        # Clear old zone if dept already exists
        old_dept = self.departments.get(dept_name)
        if old_dept:
            for r in range(old_dept.zone_row, old_dept.zone_row + old_dept.zone_h):
                for c in range(old_dept.zone_col, old_dept.zone_col + old_dept.zone_w):
                    t = self.get_tile(c, r)
                    if t and t.dept == dept_name:
                        t.dept = None
                        t.is_wall = False
                        t.is_workstation = False
                        t.is_drop_point = False
                        t.walkable = True
                        t.is_corridor = False

        # Create or update department
        from world.department import Department
        dept = Department(
            name=dept_name,
            display_name=DEPT_NAMES.get(dept_name, dept_name.title()),
            color=DEPT_COLORS.get(dept_name, (128, 128, 128)),
            zone_col=col, zone_row=row, zone_w=w, zone_h=h,
        )
        self.departments[dept_name] = dept

        # Write tiles
        for r in range(row, row + h):
            for c in range(col, col + w):
                t = self.get_tile(c, r)
                if not t:
                    continue
                on_edge = (r == row or r == row + h - 1 or c == col or c == col + w - 1)
                if on_edge:
                    t.is_wall = True
                    t.walkable = False
                    t.dept = None
                else:
                    t.dept = dept_name
                    t.walkable = True
                    t.is_wall = False
                    t.is_corridor = False

        # Punch doorways on left and right edges
        for gap_r in [row + h // 3, row + 2 * h // 3]:
            for edge_c in [col, col + w - 1]:
                t = self.get_tile(edge_c, gap_r)
                if t:
                    t.is_wall = False
                    t.walkable = True
                    t.dept = dept_name

        # Place workstations
        ws_positions = [
            (col + w // 4,     row + h // 3),
            (col + w // 4,     row + 2 * h // 3),
            (col + 3 * w // 4, row + h // 3),
            (col + 3 * w // 4, row + 2 * h // 3),
        ]
        for wc, wr in ws_positions:
            t = self.get_tile(wc, wr)
            if t and not t.is_wall:
                t.is_workstation = True
                dept.workstation_tiles.append(t)

        # Place drop points
        mid_r = row + h // 2
        for dp_c in [col + 1, col + w - 2]:
            t = self.get_tile(dp_c, mid_r)
            if t and not t.is_wall:
                t.is_drop_point = True
                dept.drop_point_tiles.append(t)

        self.render_background()
        return True
