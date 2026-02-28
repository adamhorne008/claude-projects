# ui/recipe_menu.py — modal recipe management and procurement overlay

from __future__ import annotations
import pygame
from typing import Optional, TYPE_CHECKING
from ui.button import Button
from production.recipe import Recipe, Ingredient
from settings import (
    SCREEN_W, SCREEN_H, VIEWPORT_H,
    COL_PANEL_BG, COL_PANEL_BORDER, COL_WHITE, COL_BTN_NORMAL,
    FONT_SM, FONT_MD, FONT_LG,
)

if TYPE_CHECKING:
    from production.recipe_manager import RecipeManager
    from production.order_manager import OrderManager


class RecipeMenu:
    """
    Full-screen modal overlay (press M to toggle).

    Layout:
      Left (280px): recipe list + [New] [Delete]
      Center (420px): selected recipe detail / edit form
      Right (280px): procurement list for active orders
    """

    W = 980
    H = 500

    def __init__(self, recipe_manager: RecipeManager, order_manager: OrderManager) -> None:
        self._rm = recipe_manager
        self._om = order_manager
        self.visible = False

        self._selected: Optional[str] = None   # selected recipe name
        self._editing = False                   # True when in edit/new mode
        self._edit_recipe: Optional[Recipe] = None
        self._scroll = 0
        self._tab = "recipes"   # "recipes" or "procurement"

        # Edit form state
        self._form: dict = {}
        self._ing_inputs: list[dict] = []      # [{name, qty, unit}]
        self._form_error = ""

        # Fonts
        self._font_lg = pygame.font.SysFont("Arial", FONT_LG, bold=True)
        self._font_md = pygame.font.SysFont("Arial", FONT_MD, bold=True)
        self._font_sm = pygame.font.SysFont("Arial", FONT_SM)

        # Layout rects (computed in draw relative to modal rect)
        rx = (SCREEN_W - self.W) // 2
        ry = (VIEWPORT_H - self.H) // 2
        self._modal_rect = pygame.Rect(rx, ry, self.W, self.H)

        self._list_rect  = pygame.Rect(rx + 8,       ry + 48, 260, self.H - 56)
        self._detail_rect = pygame.Rect(rx + 276,    ry + 48, 420, self.H - 56)
        self._proc_rect   = pygame.Rect(rx + 704,    ry + 48, 268, self.H - 56)

        # Buttons
        btn_y = ry + 8
        self._btn_close   = Button(pygame.Rect(rx + self.W - 70, btn_y, 62, 28), "Close", self.hide)
        self._btn_new     = Button(pygame.Rect(rx + 8,  ry + self.H - 34, 80, 26), "New",    self._start_new)
        self._btn_delete  = Button(pygame.Rect(rx + 94, ry + self.H - 34, 80, 26), "Delete", self._delete_selected)
        self._btn_tab_r   = Button(pygame.Rect(rx + 704, ry + 8, 130, 26), "Recipes",    lambda: self._set_tab("recipes"))
        self._btn_tab_p   = Button(pygame.Rect(rx + 840, ry + 8, 130, 26), "Procurement", lambda: self._set_tab("procurement"))
        self._btn_save    = Button(pygame.Rect(rx + 276, ry + self.H - 34, 80, 26), "Save",   self._save_form)
        self._btn_cancel  = Button(pygame.Rect(rx + 362, ry + self.H - 34, 80, 26), "Cancel", self._cancel_edit)
        self._btn_add_ing = Button(pygame.Rect(rx + 448, ry + self.H - 34, 120, 26), "+ Ingredient", self._add_ingredient_row)

    # ------------------------------------------------------------------
    # Visibility
    # ------------------------------------------------------------------

    def show(self) -> None:
        self.visible = True
        self._editing = False
        self._form_error = ""

    def hide(self) -> None:
        self.visible = False
        self._editing = False

    def toggle(self) -> None:
        if self.visible:
            self.hide()
        else:
            self.show()

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.Event) -> bool:
        if not self.visible:
            return False

        self._btn_close.handle_event(event)
        self._btn_new.handle_event(event)
        self._btn_delete.handle_event(event)
        self._btn_tab_r.handle_event(event)
        self._btn_tab_p.handle_event(event)

        if self._editing:
            self._btn_save.handle_event(event)
            self._btn_cancel.handle_event(event)
            self._btn_add_ing.handle_event(event)
            self._handle_form_input(event)
        else:
            self._handle_list_click(event)

        return True   # consume all events when visible

    def _handle_list_click(self, event: pygame.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if self._list_rect.collidepoint(mx, my):
                names = self._rm.recipe_names()
                row_h = 28
                idx = (my - self._list_rect.y + self._scroll) // row_h
                if 0 <= idx < len(names):
                    self._selected = names[idx]
                    self._editing = False
        if event.type == pygame.MOUSEWHEEL:
            if self._list_rect.collidepoint(pygame.mouse.get_pos()):
                self._scroll = max(0, self._scroll - event.y * 28)

    def _handle_form_input(self, event: pygame.Event) -> None:
        # Simple text field editing via keyboard for active field
        if event.type == pygame.KEYDOWN and self._form.get("_active"):
            field = self._form["_active"]
            val = str(self._form.get(field, ""))
            if event.key == pygame.K_BACKSPACE:
                self._form[field] = val[:-1]
            elif event.unicode and event.unicode.isprintable():
                self._form[field] = val + event.unicode

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            # Check which field was clicked
            for field, frect in self._form.get("_field_rects", {}).items():
                if frect.collidepoint(mx, my):
                    self._form["_active"] = field

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _set_tab(self, tab: str) -> None:
        self._tab = tab

    def _start_new(self) -> None:
        self._edit_recipe = Recipe(name="New Recipe")
        self._form = {"name": "", "cook_time": "4.0", "rrp": "8.50", "weight": "0.5", "_active": "name", "_field_rects": {}}
        self._ing_inputs = []
        self._editing = True
        self._form_error = ""

    def _delete_selected(self) -> None:
        if self._selected:
            self._rm.delete_recipe(self._selected)
            self._selected = None

    def _save_form(self) -> None:
        name = self._form.get("name", "").strip()
        if not name:
            self._form_error = "Name is required."
            return
        try:
            cook = float(self._form.get("cook_time", "4.0"))
            rrp  = float(self._form.get("rrp", "8.50"))
            wt   = float(self._form.get("weight", "0.5"))
        except ValueError:
            self._form_error = "Cook time, RRP, and weight must be numbers."
            return

        recipe = Recipe(name=name, cook_time_seconds=cook, rrp_price=rrp, weight_kg=wt)
        for row in self._ing_inputs:
            try:
                qty = float(row.get("qty", "1"))
            except ValueError:
                qty = 1.0
            recipe.add_ingredient(row.get("name", ""), qty, row.get("unit", "units"))

        self._rm.add_recipe(recipe)
        self._selected = name
        self._editing = False
        self._form_error = ""

    def _cancel_edit(self) -> None:
        self._editing = False
        self._form_error = ""

    def _add_ingredient_row(self) -> None:
        self._ing_inputs.append({"name": "", "qty": "1", "unit": "units"})

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self, screen: pygame.Surface) -> None:
        if not self.visible:
            return

        # Dim background
        overlay = pygame.Surface((SCREEN_W, VIEWPORT_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        screen.blit(overlay, (0, 0))

        # Modal background
        pygame.draw.rect(screen, (22, 22, 36), self._modal_rect, border_radius=8)
        pygame.draw.rect(screen, COL_PANEL_BORDER, self._modal_rect, 2, border_radius=8)

        # Title
        title = self._font_lg.render("Recipe Menu", True, COL_WHITE)
        screen.blit(title, (self._modal_rect.x + 12, self._modal_rect.y + 10))

        self._btn_close.draw(screen)
        self._btn_tab_r.active = (self._tab == "recipes")
        self._btn_tab_p.active = (self._tab == "procurement")
        self._btn_tab_r.draw(screen)
        self._btn_tab_p.draw(screen)

        # Left: recipe list
        self._draw_recipe_list(screen)
        self._btn_new.draw(screen)
        self._btn_delete.enabled = self._selected is not None
        self._btn_delete.draw(screen)

        # Center: detail or edit
        if self._editing:
            self._draw_edit_form(screen)
        else:
            self._draw_recipe_detail(screen)

        # Right: procurement (always visible)
        self._draw_procurement(screen)

    def _draw_recipe_list(self, screen: pygame.Surface) -> None:
        pygame.draw.rect(screen, COL_PANEL_BG, self._list_rect)
        pygame.draw.rect(screen, COL_PANEL_BORDER, self._list_rect, 1)

        clip = screen.get_clip()
        screen.set_clip(self._list_rect)
        names = self._rm.recipe_names()
        row_h = 28
        for i, name in enumerate(names):
            ry = self._list_rect.y + i * row_h - self._scroll
            if ry + row_h < self._list_rect.y or ry > self._list_rect.bottom:
                continue
            row_rect = pygame.Rect(self._list_rect.x + 2, ry + 1, self._list_rect.width - 4, row_h - 2)
            bg = (50, 80, 120) if name == self._selected else COL_BTN_NORMAL
            pygame.draw.rect(screen, bg, row_rect, border_radius=3)
            surf = self._font_sm.render(name, True, COL_WHITE)
            screen.blit(surf, (row_rect.x + 6, row_rect.y + (row_h - surf.get_height()) // 2))
        screen.set_clip(clip)

    def _draw_recipe_detail(self, screen: pygame.Surface) -> None:
        pygame.draw.rect(screen, COL_PANEL_BG, self._detail_rect)
        pygame.draw.rect(screen, COL_PANEL_BORDER, self._detail_rect, 1)

        if not self._selected:
            hint = self._font_sm.render("Select a recipe from the list", True, (120, 120, 140))
            screen.blit(hint, (self._detail_rect.x + 10, self._detail_rect.y + 10))
            return

        recipe = self._rm.get_by_name(self._selected)
        if not recipe:
            return

        x, y = self._detail_rect.x + 10, self._detail_rect.y + 10
        name_s = self._font_md.render(recipe.name, True, COL_WHITE)
        screen.blit(name_s, (x, y)); y += name_s.get_height() + 6

        for label, val in [
            ("RRP:", f"£{recipe.rrp_price:.2f}"),
            ("Cook Time:", f"{recipe.cook_time_seconds:.1f}s"),
            ("Weight:", f"{recipe.weight_kg:.3f} kg"),
        ]:
            ls = self._font_sm.render(label, True, (160, 160, 180))
            vs = self._font_sm.render(val, True, COL_WHITE)
            screen.blit(ls, (x, y))
            screen.blit(vs, (x + 100, y))
            y += ls.get_height() + 4

        y += 8
        head = self._font_sm.render("Ingredients:", True, (160, 200, 160))
        screen.blit(head, (x, y)); y += head.get_height() + 4
        for ing in recipe.ingredients:
            s = self._font_sm.render(f"  • {ing.display()}", True, (180, 180, 200))
            screen.blit(s, (x, y)); y += s.get_height() + 2

    def _draw_edit_form(self, screen: pygame.Surface) -> None:
        pygame.draw.rect(screen, COL_PANEL_BG, self._detail_rect)
        pygame.draw.rect(screen, COL_PANEL_BORDER, self._detail_rect, 1)

        x, y = self._detail_rect.x + 10, self._detail_rect.y + 10
        field_rects = {}

        def draw_field(label, key, field_y):
            ls = self._font_sm.render(label, True, (160, 160, 180))
            screen.blit(ls, (x, field_y))
            fr = pygame.Rect(x + 110, field_y - 2, 180, 20)
            active = self._form.get("_active") == key
            pygame.draw.rect(screen, (40, 40, 60) if not active else (60, 60, 100), fr)
            pygame.draw.rect(screen, COL_PANEL_BORDER, fr, 1)
            val_s = self._font_sm.render(str(self._form.get(key, "")), True, COL_WHITE)
            screen.blit(val_s, (fr.x + 4, fr.y + 2))
            field_rects[key] = fr
            return field_y + 26

        y = draw_field("Name:",      "name",      y)
        y = draw_field("Cook (s):",  "cook_time", y)
        y = draw_field("RRP (£):",   "rrp",       y)
        y = draw_field("Weight (kg):", "weight",  y)

        self._form["_field_rects"] = field_rects

        y += 4
        head = self._font_sm.render("Ingredients:", True, (160, 200, 160))
        screen.blit(head, (x, y)); y += head.get_height() + 4

        for row in self._ing_inputs[:4]:
            line = f"  {row['name']}  {row['qty']} {row['unit']}"
            s = self._font_sm.render(line, True, (180, 180, 200))
            screen.blit(s, (x, y)); y += s.get_height() + 2

        if self._form_error:
            err = self._font_sm.render(self._form_error, True, (220, 80, 80))
            screen.blit(err, (x, self._detail_rect.bottom - 50))

        self._btn_save.draw(screen)
        self._btn_cancel.draw(screen)
        self._btn_add_ing.draw(screen)

    def _draw_procurement(self, screen: pygame.Surface) -> None:
        pygame.draw.rect(screen, COL_PANEL_BG, self._proc_rect)
        pygame.draw.rect(screen, COL_PANEL_BORDER, self._proc_rect, 1)

        head = self._font_md.render("Procurement", True, COL_WHITE)
        screen.blit(head, (self._proc_rect.x + 6, self._proc_rect.y + 6))

        active_orders = self._om.get_active_orders()
        procurement = self._rm.calculate_procurement(active_orders)

        if not procurement:
            hint = self._font_sm.render("No active orders", True, (100, 100, 120))
            screen.blit(hint, (self._proc_rect.x + 6, self._proc_rect.y + 34))
            return

        y = self._proc_rect.y + 34
        clip = screen.get_clip()
        screen.set_clip(self._proc_rect)
        for key, info in procurement.items():
            qty_str = f"{info['quantity']:g} {info['unit']}"
            line = f"{info['name']}: {qty_str}"
            s = self._font_sm.render(line, True, (200, 200, 220))
            if y + s.get_height() > self._proc_rect.bottom - 4:
                break
            screen.blit(s, (self._proc_rect.x + 6, y))
            y += s.get_height() + 3
        screen.set_clip(clip)
