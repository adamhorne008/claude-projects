# production/recipe.py — recipe and ingredient data classes

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Ingredient:
    name: str
    quantity: float
    unit: str   # "kg", "g", "units", "litres"

    def display(self) -> str:
        qty = f"{self.quantity:g}"
        return f"{qty} {self.unit} {self.name}"


@dataclass
class Recipe:
    """
    A named food product with all production parameters.
    cook_time_seconds feeds into Task.work_duration.
    rrp_price is used by FinanceManager when an order is delivered.
    """
    name: str
    ingredients: list[Ingredient] = field(default_factory=list)
    weight_kg: float = 0.5
    cook_time_seconds: float = 4.0
    rrp_price: float = 8.50

    def add_ingredient(self, name: str, quantity: float, unit: str) -> None:
        self.ingredients.append(Ingredient(name=name, quantity=quantity, unit=unit))

    def remove_ingredient(self, index: int) -> None:
        if 0 <= index < len(self.ingredients):
            self.ingredients.pop(index)

    def __repr__(self) -> str:
        return f"Recipe({self.name} £{self.rrp_price:.2f} {self.cook_time_seconds}s)"
