from models import SalesRecord, Dish, DishType, QuadrantType
from costing import cost_dish
from schemas import DishClassificationOut, ActionItemOut

def get_dish_units_sold(db, dish_id: int) -> int:
    """
    Sums units_sold across all SalesRecord rows for a given dish.
    Returns 0 if the dish has no sales records.
    """
    records = db.query(SalesRecord).filter(SalesRecord.dish_id ==dish_id ).all()

    total = 0
    for record in records:
        total += record.units_sold

    return total

def get_category_units_sold(db, category: DishType) -> int:
    """
    Sums units sold across every dish in a given category.
    """
    dishes = db.query(Dish).filter(Dish.category == category).all()

    total = 0
    for dish in dishes:
        total += get_dish_units_sold(db, dish.id)

    return total

def get_dish_menu_mix_percent(db, dish_id: int, category: DishType) -> float:
    """
    A dish's share of units sold within its category, as a percentage.
    Returns 0 if the category has no recorded sales at all.
    """
    dish_units = get_dish_units_sold(db, dish_id)
    category_units = get_category_units_sold(db, category)

    if category_units == 0:
        return 0

    return (dish_units/category_units) * 100

def get_category_weighted_avg_margin(db, category: DishType) -> float:
    """
    Weighted average contribution margin (£) across all dishes in a category,
    weighted by each dish's units sold.
    Returns 0 if the category has no recorded sales at all.
    """
    dishes = db.query(Dish).filter(Dish.category == category).all()

    weighted_margin_total = 0
    for dish in dishes:
        plate_cost, margin_pounds, margin_percent = cost_dish(db, dish.id)
        dish_units = get_dish_units_sold(db, dish.id)
        weighted_margin_total += margin_pounds * dish_units

    category_units = get_category_units_sold(db, category)

    if category_units == 0:
        return 0

    return weighted_margin_total / category_units

def classify_dish(db, dish_id: int, category: DishType) -> DishClassificationOut:
    """
    Classifies a single dish into one of four menu-engineering quadrants:
    Star, Plowhorse, Puzzle, or Dog.
    """
    n = db.query(Dish).filter(Dish.category == category).count()
    popularity_threshold = 0.7 * (100 / n)

    dish_menu_mix = get_dish_menu_mix_percent(db, dish_id, category)
    weighted_avg_margin = get_category_weighted_avg_margin(db, category)

    dish = db.query(Dish).filter(Dish.id == dish_id).first()

    plate_cost, margin_pounds, margin_percent = cost_dish(db, dish_id)

    is_popular = dish_menu_mix >= popularity_threshold
    is_profitable = margin_pounds >= weighted_avg_margin

    if is_popular and is_profitable:
        quadrant = QuadrantType.STAR
    elif is_popular and not is_profitable:
        quadrant = QuadrantType.PLOWHORSE
    elif not is_popular and is_profitable:
        quadrant = QuadrantType.PUZZLE
    else:
        quadrant = QuadrantType.DOG

    return DishClassificationOut(
    dish_id= dish_id,
    dish_name= dish.name,
    category= category,
    menu_price= dish.menu_price,
    plate_cost= plate_cost,
    margin_pounds= margin_pounds,
    margin_percent= margin_percent,
    units_sold= get_dish_units_sold(db, dish_id),
    menu_mix_percent= dish_menu_mix,
    popularity_threshold= popularity_threshold,
    profitability_threshold= weighted_avg_margin,
    quadrant= quadrant)

def classify_all_dishes(db) -> list[DishClassificationOut]:
    """
    Classifies every dish on the menu into its quadrant, category by category.
    """
    results = []

    for category in DishType:
        dishes = db.query(Dish).filter(Dish.category == category).all()

        for dish in dishes:
            classification = classify_dish(db, dish.id, category)
            results.append(classification)

    return results

def build_action_list(db) -> list[ActionItemOut]:
    """
    Turns quadrant classifications into a ranked action list with £ impact.

    cutting a Dog assumes its covers transfer to a category-average dish rather than being lost entirely.
    """
    classifications = classify_all_dishes(db)
    actions = []

    for c in classifications:
        dish_units = get_dish_units_sold(db, c.dish_id)
        dish = db.query(Dish).filter(Dish.id == c.dish_id).first()
        dish_name = dish.name
        dish_category = dish.category

        if c.quadrant == QuadrantType.STAR:
            continue  # no action needed

        elif c.quadrant == QuadrantType.PLOWHORSE:
            impact = (c.profitability_threshold - c.margin_pounds) * dish_units
            action = "Reprice or re-engineer recipe to close margin gap"

        elif c.quadrant == QuadrantType.DOG:
            impact = (c.profitability_threshold - c.margin_pounds) * dish_units 
            action = "Consider cutting from menu"

        elif c.quadrant == QuadrantType.PUZZLE:
            category_units = get_category_units_sold(db, dish_category) 
            threshold_units = (c.popularity_threshold / 100) * category_units
            impact = c.margin_pounds * (threshold_units - dish_units)
            action = "Promote or reposition on menu"

        else:
            raise ValueError(f"Unrecognised quadrant: {c.quadrant}")

        actions.append(ActionItemOut(
            dish_id=c.dish_id,
            dish_name=dish_name,
            quadrant=c.quadrant,
            action=action,
            impact_pounds=round(impact, 2)
        ))

    actions.sort(key=lambda a: a.impact_pounds, reverse=True)
    return actions