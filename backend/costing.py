from datetime import date
from models import Dish, DishIngredient, IngredientPrice, OWN_PRICE_SOURCES, PriceSource
from fastapi import HTTPException

def best_price(db, ingredient_id, as_of=None):
    """
    The price costing should use for an ingredient, as an IngredientPrice row.

    Rule:
      1. The restaurant's own price (invoice / supplier list / manual), most recent.
      2. Otherwise the most recent benchmark price.
      Prices dated after `as_of` (default today) are ignored.
    Same date -> the one entered last wins.
    Returns None if the ingredient has no usable price.
    """
    as_of = as_of or date.today()
    prices = db.query(IngredientPrice).filter(
        IngredientPrice.ingredient_id == ingredient_id,
        IngredientPrice.effective_date <= as_of,
    )
    newest_first = (IngredientPrice.effective_date.desc(), IngredientPrice.id.desc())

    own = prices.filter(IngredientPrice.source.in_(OWN_PRICE_SOURCES)).order_by(*newest_first).first()
    if own:
        return own
    return prices.filter(IngredientPrice.source == PriceSource.BENCHMARK).order_by(*newest_first).first()

def cost_dish(db, dish_id):
    recipe_rows = db.query(DishIngredient).filter(DishIngredient.dish_id == dish_id).all()
    plate_cost = 0
    for row in recipe_rows:
        price = best_price(db, row.ingredient_id)
        if price is None:
            # Never cost a missing price as £0; that would silently inflate the margin.
            raise ValueError(f"Ingredient {row.ingredient_id} has no price")
        plate_cost += row.quantity * price.price_per_unit

    dish = db.query(Dish).filter(Dish.id == dish_id).first()
    if dish is None:
        raise HTTPException(status_code= 404, detail="Dish not found")
    margin = dish.menu_price - plate_cost
    margin_percent = (margin/dish.menu_price) *100
    return round(plate_cost,2), round(margin,2), round(margin_percent,2)
