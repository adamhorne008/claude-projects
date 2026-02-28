# workers/pathfinder.py — A* grid pathfinder

import heapq
from typing import Optional


class AStar:
    """
    A* pathfinding on a boolean walkability grid.
    Returns a list of (col, row) waypoints from start to goal (start excluded).
    Uses Manhattan distance heuristic (4-directional movement only).
    """

    def find_path(
        self,
        walkable: list[list[bool]],
        start: tuple[int, int],
        goal: tuple[int, int],
    ) -> list[tuple[int, int]]:
        """
        walkable[row][col] — True if passable.
        Returns list of (col, row) tuples (not including start), or [] if no path.
        """
        if start == goal:
            return []

        rows = len(walkable)
        cols = len(walkable[0]) if rows else 0

        sc, sr = start
        gc, gr = goal

        # Ensure goal is reachable
        if not (0 <= gr < rows and 0 <= gc < cols and walkable[gr][gc]):
            # Try to find nearest walkable neighbour to goal
            goal = self._nearest_walkable(walkable, gc, gr, rows, cols)
            if goal is None:
                return []
            gc, gr = goal

        open_set: list[tuple[float, tuple[int, int]]] = []
        heapq.heappush(open_set, (0.0, start))

        came_from: dict[tuple[int, int], tuple[int, int]] = {}
        g_score: dict[tuple[int, int], float] = {start: 0.0}

        while open_set:
            _, current = heapq.heappop(open_set)
            cc, cr = current

            if current == (gc, gr):
                return self._reconstruct(came_from, current, start)

            for nc, nr in self._neighbors(cc, cr, cols, rows):
                if not walkable[nr][nc]:
                    continue
                tentative_g = g_score[current] + 1.0
                if tentative_g < g_score.get((nc, nr), float("inf")):
                    came_from[(nc, nr)] = current
                    g_score[(nc, nr)] = tentative_g
                    f = tentative_g + self._heuristic((nc, nr), (gc, gr))
                    heapq.heappush(open_set, (f, (nc, nr)))

        return []  # No path found

    def _heuristic(self, a: tuple[int, int], b: tuple[int, int]) -> float:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def _neighbors(self, c: int, r: int, cols: int, rows: int) -> list[tuple[int, int]]:
        result = []
        for dc, dr in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            nc, nr = c + dc, r + dr
            if 0 <= nc < cols and 0 <= nr < rows:
                result.append((nc, nr))
        return result

    def _reconstruct(
        self,
        came_from: dict,
        current: tuple[int, int],
        start: tuple[int, int],
    ) -> list[tuple[int, int]]:
        path = []
        while current in came_from:
            path.append(current)
            current = came_from[current]
        path.reverse()
        return path

    def _nearest_walkable(
        self, walkable, gc, gr, rows, cols
    ) -> Optional[tuple[int, int]]:
        """BFS outward from goal to find nearest walkable tile."""
        from collections import deque
        visited = set()
        q = deque([(gc, gr)])
        visited.add((gc, gr))
        while q:
            c, r = q.popleft()
            if 0 <= r < rows and 0 <= c < cols and walkable[r][c]:
                return (c, r)
            for dc, dr in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                nc, nr = c + dc, r + dr
                if (nc, nr) not in visited:
                    visited.add((nc, nr))
                    q.append((nc, nr))
        return None
