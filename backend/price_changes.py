"""
Ingredient price changes and what they do to the dishes that use them.

Shared by the Overview's price-rise alerts, the Ingredients and dish pages,
and the report agent (report_tools.price_changes), so they all agree.

A change is a day when the price costing uses for an ingredient
(costing.best_price) moves: a new invoice, supplier or typed-in price, or a
new benchmark for an ingredient without the restaurant's own price. A new
benchmark for an ingredient that already has its own price changes nothing,
so it isn't a change.

Window (agreed with George, 25 Sep 2026): from the start of the chosen period
to today, so a September invoice shows while August is being looked at; each
change is dated and marked if it came after the period.
Alerts: rises of ALERT_PERCENT or more. Falls and smaller rises are still
listed (the dish and ingredient pages show them), just not as alerts.

Only ingredients in the recipes of dishes on the menu today count, since those
are the plates the owner can still act on.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta

from costing import best_price, menu_prices
from models import Dish, DishIngredient, Ingredient, IngredientPrice

ALERT_PERCENT = 5.0


@dataclass
class DishEffect:
    dish_id: int
    name: str
    per_plate: float        # £ added to (or, if negative, taken off) the plate cost


@dataclass
class PriceChange:
    ingredient_id: int
    name: str
    unit: str               # the ingredient's base unit: gram / ml / each
    day: date
    old_price: float        # per base unit, as stored
    new_price: float
    source: str             # of the new price: invoice / supplier_list / manual / benchmark
    supplier: str | None
    change_percent: float
    dishes: list[DishEffect] = field(default_factory=list)
    period_effect: float = 0.0   # £ change in contribution at the period's plates sold (a rise is negative)

    @property
    def is_alert(self) -> bool:
        return self.change_percent >= ALERT_PERCENT


def on_menu(dish, day: date) -> bool:
    return dish.on_menu_from <= day and (dish.on_menu_until is None or dish.on_menu_until >= day)


def find_price_changes(db, start: date, today: date, units_by_dish: dict[int, int] | None = None) -> list[PriceChange]:
    """
    Every change from `start` to `today` for ingredients in current recipes, biggest
    period effect first (then biggest % change). `units_by_dish` (dish id -> plates
    sold in the period) prices the period effect; without it the effect is 0.

    Example: an ingredient goes from £1.00 to £1.50 each; a dish uses 2 per plate and
    sold 40 plates in the period -> +£1.00 a plate, period effect -£40.
    """
    units_by_dish = units_by_dish or {}
    uses = {}   # ingredient id -> [(dish, quantity)]
    for row in db.query(DishIngredient):
        dish = db.get(Dish, row.dish_id)
        if on_menu(dish, today):
            uses.setdefault(row.ingredient_id, []).append((dish, row.quantity))

    changes = []
    for ingredient_id, used_in in uses.items():
        days = {p.effective_date for p in db.query(IngredientPrice).filter(
            IngredientPrice.ingredient_id == ingredient_id,
            IngredientPrice.effective_date >= start, IngredientPrice.effective_date <= today)}
        for day in sorted(days):
            old = best_price(db, ingredient_id, as_of=day - timedelta(days=1))
            new = best_price(db, ingredient_id, as_of=day)
            if not (old and new and new.effective_date == day and new.price_per_unit != old.price_per_unit):
                continue
            ingredient = db.get(Ingredient, ingredient_id)
            delta = new.price_per_unit - old.price_per_unit
            effects = sorted((DishEffect(d.id, d.name, round(quantity * delta, 2)) for d, quantity in used_in),
                             key=lambda e: -abs(e.per_plate))
            changes.append(PriceChange(
                ingredient_id=ingredient_id, name=ingredient.name, unit=ingredient.unit.value, day=day,
                old_price=old.price_per_unit, new_price=new.price_per_unit,
                source=new.source.value, supplier=new.supplier,
                change_percent=round(delta / old.price_per_unit * 100, 1) if old.price_per_unit else 0.0,
                dishes=effects,
                period_effect=round(-sum(quantity * delta * units_by_dish.get(d.id, 0) for d, quantity in used_in), 2),
            ))
    return sorted(changes, key=lambda c: (-abs(c.period_effect), -abs(c.change_percent)))


@dataclass
class MenuPriceChange:
    dish_id: int
    name: str
    day: date
    old_price: float
    new_price: float


def find_menu_price_changes(db, start: date, today: date) -> list[MenuPriceChange]:
    """
    Menu price changes from `start` to `today` for dishes on the menu today, newest
    first: each dated price after a dish's first, against the price before it.
    """
    changes = []
    for dish in db.query(Dish).all():
        if not on_menu(dish, today):
            continue
        prices = menu_prices(db, dish.id)
        for before, after in zip(prices, prices[1:]):
            if start <= after.effective_date <= today and after.price != before.price:
                changes.append(MenuPriceChange(dish.id, dish.name, after.effective_date, before.price, after.price))
    return sorted(changes, key=lambda c: c.day, reverse=True)
