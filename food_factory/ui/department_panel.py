# ui/department_panel.py — per-department worker count with +/- controls

from __future__ import annotations
import pygame
from typing import TYPE_CHECKING
from ui.button import Button
from settings import (
    STAGE_ORDER, DEPT_NAMES, DEPT_COLORS,
    COL_PANEL_BG, COL_PANEL_BORDER, COL_WHITE, FONT_SM, FONT_MD
)

if TYPE_CHECKING:
    from workers.worker_manager import WorkerManager
    from production.task_manager import TaskManager
    from core.event_bus import EventBus


class DepartmentPanel:
    """
    Shows one row per department:
      [color swatch] [name]  [tasks]  [-] [count] [+]
    """

    def __init__(
        self,
        rect: pygame.Rect,
        worker_manager: WorkerManager,
        task_manager: TaskManager,
        event_bus: EventBus,
    ) -> None:
        self.rect = rect
        self._wm = worker_manager
        self._tm = task_manager
        self._bus = event_bus

        self._font_md = pygame.font.SysFont("Arial", FONT_MD, bold=True)
        self._font_sm = pygame.font.SysFont("Arial", FONT_SM)

        self._buttons: dict[str, dict[str, Button]] = {}
        self._build_buttons()

    def _build_buttons(self) -> None:
        row_h = (self.rect.height - 8) // len(STAGE_ORDER)
        btn_w, btn_h = 22, 20

        for i, dept_name in enumerate(STAGE_ORDER):
            ry = self.rect.y + 4 + i * row_h
            plus_rect  = pygame.Rect(self.rect.right - btn_w - 4,      ry + (row_h - btn_h) // 2, btn_w, btn_h)
            minus_rect = pygame.Rect(self.rect.right - btn_w * 2 - 12, ry + (row_h - btn_h) // 2, btn_w, btn_h)

            d = dept_name  # capture
            self._buttons[dept_name] = {
                "plus":  Button(plus_rect,  "+", callback=lambda d=d: self._bus.publish("REQUEST_HIRE", {"dept": d})),
                "minus": Button(minus_rect, "-", callback=lambda d=d: self._bus.publish("REQUEST_FIRE", {"dept": d})),
            }

    def handle_event(self, event: pygame.Event) -> bool:
        for btns in self._buttons.values():
            for btn in btns.values():
                if btn.handle_event(event):
                    return True
        return False

    def update(self) -> None:
        for dept_name, btns in self._buttons.items():
            from world.department import Department
            dept = self._wm._tilemap.departments.get(dept_name)
            if dept:
                btns["minus"].enabled = dept.worker_count > 0
                btns["plus"].enabled  = dept.worker_count < dept.max_workers

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, COL_PANEL_BG, self.rect)
        pygame.draw.rect(surface, COL_PANEL_BORDER, self.rect, 1)

        row_h = (self.rect.height - 8) // len(STAGE_ORDER)

        for i, dept_name in enumerate(STAGE_ORDER):
            ry = self.rect.y + 4 + i * row_h
            color = DEPT_COLORS[dept_name]
            name  = DEPT_NAMES[dept_name]
            count = self._wm.get_worker_count(dept_name)
            tasks = self._tm.get_pending_count(dept_name)

            # Color swatch
            swatch = pygame.Rect(self.rect.x + 6, ry + row_h // 2 - 7, 14, 14)
            pygame.draw.rect(surface, color, swatch)

            # Dept name
            name_surf = self._font_sm.render(name, True, COL_WHITE)
            surface.blit(name_surf, (self.rect.x + 26, ry + row_h // 2 - name_surf.get_height() // 2))

            # Pending tasks
            task_surf = self._font_sm.render(f"tasks: {tasks}", True, (160, 160, 180))
            surface.blit(task_surf, (self.rect.x + 140, ry + row_h // 2 - task_surf.get_height() // 2))

            # Worker count between buttons
            btns = self._buttons[dept_name]
            btns["minus"].draw(surface)
            count_surf = self._font_sm.render(str(count), True, COL_WHITE)
            cx = btns["minus"].rect.right + (btns["plus"].rect.left - btns["minus"].rect.right) // 2
            surface.blit(count_surf, (cx - count_surf.get_width() // 2, ry + row_h // 2 - count_surf.get_height() // 2))
            btns["plus"].draw(surface)
