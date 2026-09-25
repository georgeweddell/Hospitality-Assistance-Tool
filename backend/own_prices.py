"""
How much of a plate cost comes from the restaurant's own prices.

A trust signal next to every margin: 90% means the plate cost rests on the
restaurant's own invoices, supplier lists or typed-in prices; 20% means it is
mostly benchmark estimates. Typed-in prices count as the restaurant's own, as
they do in costing.best_price (agreed with George, 25 Sep 2026).

Share = own-priced line costs / all line costs, each line = quantity x the price
costing uses today. Example: Margherita, plate cost £1.46, of which flour £0.19,
tomatoes £0.30 and mozzarella £0.82 are from invoices -> £1.31 / £1.46 = 90%.
"""

from datetime import date

from costing import best_price
from models import Dish, DishIngredient, OWN_PRICE_SOURCES


def cost_split(db, dish_id: int, as_of: date | None = None) -> tuple[float, float]:
    """(own-priced cost, total cost) of one plate, from today's prices (or as_of)."""
    own = total = 0.0
    for line in db.query(DishIngredient).filter(DishIngredient.dish_id == dish_id):
        price = best_price(db, line.ingredient_id, as_of=as_of)
        if price is None:
            continue
        cost = line.quantity * price.price_per_unit
        total += cost
        if price.source in OWN_PRICE_SOURCES:
            own += cost
    return own, total


def own_share(db, dish_id: int, as_of: date | None = None) -> float | None:
    """The % of a plate cost from the restaurant's own prices; None without a costed recipe."""
    own, total = cost_split(db, dish_id, as_of)
    return round(own / total * 100, 1) if total else None


def menu_own_share(db, today: date | None = None) -> float | None:
    """
    The same across the dishes on the menu today, one plate of each: the share of
    the menu's recipe cost that rests on the restaurant's own prices.
    """
    today = today or date.today()
    own = total = 0.0
    for dish in db.query(Dish).all():
        if dish.on_menu_from <= today and (dish.on_menu_until is None or dish.on_menu_until >= today):
            o, t = cost_split(db, dish.id, today)
            own, total = own + o, total + t
    return round(own / total * 100, 1) if total else None
