# production/recipe_manager.py — central registry for all recipes

from __future__ import annotations
from production.recipe import Recipe, Ingredient


_DEFAULT_RECIPES = [
    Recipe("Burger",   cook_time_seconds=5.0,  rrp_price=9.50,  weight_kg=0.35),
    Recipe("Salad",    cook_time_seconds=2.0,  rrp_price=7.00,  weight_kg=0.25),
    Recipe("Pasta",    cook_time_seconds=6.0,  rrp_price=8.50,  weight_kg=0.40),
    Recipe("Sandwich", cook_time_seconds=2.5,  rrp_price=6.50,  weight_kg=0.20),
    Recipe("Soup",     cook_time_seconds=7.0,  rrp_price=7.50,  weight_kg=0.50),
    Recipe("Pizza",    cook_time_seconds=10.0, rrp_price=12.00, weight_kg=0.60),
    Recipe("Wrap",     cook_time_seconds=3.0,  rrp_price=7.00,  weight_kg=0.22),
]

# Default ingredients per recipe
_DEFAULT_INGREDIENTS = {
    "Burger":   [("Beef Patty", 0.2, "kg"), ("Bun", 1, "units"), ("Lettuce", 0.05, "kg"), ("Sauce", 0.03, "kg")],
    "Salad":    [("Mixed Leaves", 0.1, "kg"), ("Tomato", 0.08, "kg"), ("Dressing", 0.03, "litres")],
    "Pasta":    [("Pasta", 0.15, "kg"), ("Sauce", 0.1, "kg"), ("Cheese", 0.04, "kg")],
    "Sandwich": [("Bread", 2, "units"), ("Filling", 0.1, "kg"), ("Butter", 0.01, "kg")],
    "Soup":     [("Stock", 0.3, "litres"), ("Vegetables", 0.15, "kg"), ("Seasoning", 0.01, "kg")],
    "Pizza":    [("Dough", 0.25, "kg"), ("Tomato Base", 0.1, "kg"), ("Cheese", 0.15, "kg"), ("Toppings", 0.1, "kg")],
    "Wrap":     [("Tortilla", 1, "units"), ("Filling", 0.12, "kg"), ("Sauce", 0.02, "litres")],
}


class RecipeManager:
    """
    Central registry for Recipe objects. Provides CRUD and procurement calculation.
    """

    def __init__(self) -> None:
        self._recipes: dict[str, Recipe] = {}
        for r in _DEFAULT_RECIPES:
            for name, qty, unit in _DEFAULT_INGREDIENTS.get(r.name, []):
                r.add_ingredient(name, qty, unit)
            self._recipes[r.name] = r

    # --- CRUD ---

    def get_by_name(self, name: str) -> Recipe | None:
        return self._recipes.get(name)

    def all_recipes(self) -> list[Recipe]:
        return list(self._recipes.values())

    def add_recipe(self, recipe: Recipe) -> None:
        self._recipes[recipe.name] = recipe

    def delete_recipe(self, name: str) -> bool:
        if name in self._recipes:
            del self._recipes[name]
            return True
        return False

    def recipe_names(self) -> list[str]:
        return list(self._recipes.keys())

    # --- Procurement ---

    def calculate_procurement(self, orders: list) -> dict[str, dict]:
        """
        Sum all ingredients needed across a list of Order objects.
        Returns: {"flour": {"quantity": 2.5, "unit": "kg"}, ...}
        """
        totals: dict[str, dict] = {}
        for order in orders:
            for meal_name, qty in order.meals.items():
                recipe = self.get_by_name(meal_name)
                if not recipe:
                    continue
                for ing in recipe.ingredients:
                    key = ing.name.lower()
                    if key not in totals:
                        totals[key] = {"name": ing.name, "quantity": 0.0, "unit": ing.unit}
                    totals[key]["quantity"] += ing.quantity * qty
        return totals
