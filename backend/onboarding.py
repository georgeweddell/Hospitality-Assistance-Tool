"""
Setup progress for a new restaurant: what's been entered so far. Drives the
checklist on the Overview until the restaurant has its first results.
"""

from datetime import date

from costing import best_price
from models import Dish, DishIngredient, DishType, PriceSource, RecipeStatus, SalesRecord
from schemas import SetupStatusOut


def setup_status(db, today=None) -> SetupStatusOut:
    today = today or date.today()
    # Dishes on the menu now (not ones that have come off it).
    dishes = [d for d in db.query(Dish).all() if d.on_menu_until is None or d.on_menu_until >= today]
    dish_ids = {d.id for d in dishes}

    rows = [r for r in db.query(DishIngredient).all() if r.dish_id in dish_ids]
    with_recipe = {r.dish_id for r in rows}
    in_use = {r.ingredient_id for r in rows}
    own_priced = 0
    for ingredient_id in in_use:
        price = best_price(db, ingredient_id, as_of=today)
        if price is not None and price.source != PriceSource.BENCHMARK:
            own_priced += 1

    return SetupStatusOut(
        dishes=len(dishes),
        dishes_with_recipe=len(with_recipe),
        dishes_with_category=sum(1 for d in dishes if d.category is not None),
        ingredients_in_use=len(in_use),
        ingredients_with_own_price=own_priced,
        has_sales=db.query(SalesRecord).first() is not None,
        needs_recipe=[d.id for d in sorted(dishes, key=menu_order) if d.id not in with_recipe],
        unchecked_recipes=sum(1 for d in dishes if d.recipe_status == RecipeStatus.AI_UNCHECKED and d.id in with_recipe),
    )


MENU_ORDER = [DishType.STARTER, DishType.MAIN, DishType.SIDE, DishType.DESSERT]   # as a menu reads


def menu_order(dish):
    """Starters first, then down the menu; dishes without a category last; then by name."""
    position = MENU_ORDER.index(dish.category) if dish.category else len(MENU_ORDER)
    return position, dish.name.lower()
