"""
Checks on a saved recipe, for the Recipes table: plain rules (no AI) that pick
out recipes worth a second look, especially bulk AI estimates.

Thresholds agreed with George (kitchen sense, easy to change here):
  - food cost (plate cost as a % of the menu price) under 8% or over 40%
  - a single line over 500 g, 500 ml or 12 each for one portion
  - fewer than 2 ingredients
  - an ingredient left out of the cost (Claude named something not in the list)
  - a line in a different unit from its ingredient (unit_check)

Food cost % uses the menu price as stored (VAT included), like the margins.
"""

from costing import cost_dish
from models import DishIngredient, Ingredient, UnitType
from schemas import RecipeRowOut

FOOD_COST_LOW = 8     # % (pizzerias genuinely run low: garlic bread ~5%)
FOOD_COST_HIGH = 40   # %
MAX_LINE = {UnitType.GRAM: 500, UnitType.ML: 500, UnitType.EACH: 12}
MIN_INGREDIENTS = 2


def recipe_checks(lines, food_cost_percent, skipped):
    """
    lines: [(quantity, unit, unit_check)]. Returns the flags that apply, e.g.
    ["food_cost_high", "big_line"]. A dish without a recipe has no flags.
    """
    if not lines:
        return []
    flags = []
    if food_cost_percent is not None and food_cost_percent > FOOD_COST_HIGH:
        flags.append("food_cost_high")
    if food_cost_percent is not None and food_cost_percent < FOOD_COST_LOW:
        flags.append("food_cost_low")
    if any(quantity > MAX_LINE[unit] for quantity, unit, _ in lines):
        flags.append("big_line")
    if len(lines) < MIN_INGREDIENTS:
        flags.append("few_ingredients")
    if skipped:
        flags.append("left_out")
    if any(unit_check for _, _, unit_check in lines):
        flags.append("unit")
    return flags


def recipe_row(db, dish, menu_price):
    """One row of the Recipes table."""
    rows = (db.query(DishIngredient, Ingredient)
            .join(Ingredient, Ingredient.id == DishIngredient.ingredient_id)
            .filter(DishIngredient.dish_id == dish.id).all())
    lines = [(r.quantity, i.unit, r.unit_check) for r, i in rows]
    plate_cost = food_cost = None
    if lines:
        plate_cost, _, _ = cost_dish(db, dish.id, menu_price)
        food_cost = plate_cost / menu_price * 100
    status = dish.recipe_status.value if dish.recipe_status else ("checked" if lines else "none")
    return RecipeRowOut(
        dish_id=dish.id, name=dish.name, category=dish.category, menu_price=menu_price,
        status=status, lines=len(lines), plate_cost=plate_cost,
        food_cost_percent=round(food_cost, 1) if food_cost is not None else None,
        checks=recipe_checks(lines, food_cost, dish.skipped_ingredients),
        recipe_check=dish.recipe_check,
    )
