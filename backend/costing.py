from datetime import date, timedelta
from models import Dish, DishIngredient, IngredientPrice, MenuPrice, OWN_PRICE_SOURCES, PriceSource, SalesRecord
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

def menu_prices(db, dish_id):
    """A dish's menu prices, oldest first (same date: the one entered last comes last)."""
    return (db.query(MenuPrice)
            .filter(MenuPrice.dish_id == dish_id)
            .order_by(MenuPrice.effective_date, MenuPrice.id)
            .all())

def price_on(prices, day):
    """
    The menu price in effect on a day, from a dish's prices oldest first:
    the latest one dated on or before that day. Before its first price, the
    first price (a dish's first price is dated when it went on the menu, and
    that date can later be edited to earlier).
    """
    in_effect = prices[0].price
    for p in prices:
        if p.effective_date <= day:
            in_effect = p.price
    return in_effect

def menu_price_on(db, dish_id, day=None):
    """A dish's menu price on a day (default today). None if it has no price at all."""
    prices = menu_prices(db, dish_id)
    if not prices:
        return None
    return price_on(prices, day or date.today())

def average_menu_price(db, dish_id, start, end):
    """
    The menu price to analyse a dish at over start..end: the price charged on
    each day, weighted by that day's units sold.

    Example: 100 sold at £11.00, then 50 at £11.50 after a price rise
             -> (100 x 11.00 + 50 x 11.50) / 150 = £11.1667

    Margin is price minus plate cost, so margin at this average price is
    exactly the units-weighted average margin across those days. The
    menu-engineering formulas don't change; only the price they're given does.

    - Uses the same sales records as get_dish_units_sold (wholly inside the range).
    - A multi-day total (e.g. a monthly figure) that spans a price change is
      assumed to have sold evenly across its days. Daily records need no assumption.
    - No sales in the range: the price on the last day of the range.
    """
    prices = menu_prices(db, dish_id)
    records = db.query(SalesRecord).filter(
        SalesRecord.dish_id == dish_id,
        SalesRecord.period_start >= start,
        SalesRecord.period_end <= end,
    ).all()

    units_at = {}   # {price: units sold at that price}
    for record in records:
        days = (record.period_end - record.period_start).days + 1
        for offset in range(days):
            price = price_on(prices, record.period_start + timedelta(days=offset))
            units_at[price] = units_at.get(price, 0) + record.units_sold / days

    total_units = sum(units_at.values())
    if total_units == 0:
        return price_on(prices, end)
    if len(units_at) == 1:
        return next(iter(units_at))   # one price all period: that price, exactly
    return sum(price * units for price, units in units_at.items()) / total_units

def cost_dish(db, dish_id, menu_price=None):
    """
    (plate cost, margin £, margin %) for a dish, rounded to 2 decimal places.
    menu_price: the price to work the margin from. Default: today's menu price.
    Analysis over a date range passes average_menu_price instead.
    """
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
    if menu_price is None:
        menu_price = menu_price_on(db, dish_id)
    margin = menu_price - plate_cost
    margin_percent = (margin/menu_price) *100
    return round(plate_cost,2), round(margin,2), round(margin_percent,2)
