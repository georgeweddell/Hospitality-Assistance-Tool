from models import SalesRecord, Dish, DishIngredient, DishType, QuadrantType
from costing import cost_dish
from schemas import DishClassificationOut, ActionItemOut, IncompleteDishOut

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

def get_incomplete_reasons(db, dish) -> list[str]:
    """
    Reasons a dish can't be meaningfully classified.
    An empty list means the dish is complete and safe to analyse.
    """
    reasons = []

    if dish.category is None:
        reasons.append("No category set")

    has_recipe = db.query(DishIngredient).filter(
        DishIngredient.dish_id == dish.id
    ).count() > 0
    if not has_recipe:
        reasons.append("No recipe saved")

    if get_dish_units_sold(db, dish.id) == 0:
        reasons.append("No sales data")

    return reasons


def get_eligible_dishes(db, category: DishType) -> list[Dish]:
    """
    Dishes in a category that are complete enough to classify.
    This set defines the analysis population — it drives both the
    classifications returned and the denominators the thresholds use.
    """
    dishes = db.query(Dish).filter(Dish.category == category).all()
    return [d for d in dishes if not get_incomplete_reasons(db, d)]


def list_incomplete_dishes(db) -> list[IncompleteDishOut]:
    """
    Every dish excluded from analysis, with the reasons why.
    Outstanding work, not findings.
    """
    results = []

    for dish in db.query(Dish).all():
        reasons = get_incomplete_reasons(db, dish)
        if reasons:
            results.append(IncompleteDishOut(
                dish_id=dish.id,
                dish_name=dish.name,
                category=dish.category,
                reasons=reasons,
            ))

    return results

def get_category_stats(db, dishes: list[Dish]) -> dict:
    """
    Costs and units sold for every dish in a set, worked out ONCE.

    The helpers below all read from this instead of querying the database
    themselves. Before, every dish re-costed its whole category, so a category
    of n dishes was costed n x n times. Now it's n. The formulas are unchanged.

    Returns {"units": {dish_id: units},
             "costs": {dish_id: (plate_cost, margin_pounds, margin_percent)},
             "margins": {dish_id: margin_pounds}}.
    """
    units = {}
    costs = {}
    margins = {}
    for dish in dishes:
        units[dish.id] = get_dish_units_sold(db, dish.id)
        costs[dish.id] = cost_dish(db, dish.id)
        plate_cost, margin_pounds, margin_percent = costs[dish.id]
        margins[dish.id] = margin_pounds

    return {"units": units, "costs": costs, "margins": margins}


def get_category_units_sold(stats: dict) -> int:
    """
    Sums units sold across a given set of dishes.
    """
    total = 0
    for dish_units in stats["units"].values():
        total += dish_units

    return total


def get_dish_menu_mix_percent(dish_id: int, stats: dict) -> float:
    """
    A dish's share of units sold within its category, as a percentage.
    Returns 0 if the category has no recorded sales at all.
    """
    dish_units = stats["units"][dish_id]
    category_units = get_category_units_sold(stats)

    if category_units == 0:
        return 0

    return (dish_units / category_units) * 100


def get_category_weighted_avg_margin(stats: dict) -> float:
    """
    Weighted average contribution margin (£) across a set of dishes,
    weighted by each dish's units sold.
    Returns 0 if the set has no recorded sales at all.
    """
    weighted_margin_total = 0
    for dish_id, margin_pounds in stats["margins"].items():
        dish_units = stats["units"][dish_id]
        weighted_margin_total += margin_pounds * dish_units

    category_units = get_category_units_sold(stats)

    if category_units == 0:
        return 0

    return weighted_margin_total / category_units

def classify_dish(db, dish_id: int, category: DishType,
                  eligible_dishes: list[Dish], stats: dict) -> DishClassificationOut:
    """
    Classifies a single dish into one of four menu-engineering quadrants:
    Star, Plowhorse, Puzzle, or Dog.

    eligible_dishes is the analysis population for the category — passed in
    rather than queried, so the caller decides once who's in. stats is
    get_category_stats for that same population, worked out once by the caller.
    """
    n = len(eligible_dishes)
    popularity_threshold = 0.7 * (100 / n)

    dish_menu_mix = get_dish_menu_mix_percent(dish_id, stats)
    weighted_avg_margin = get_category_weighted_avg_margin(stats)

    dish = db.query(Dish).filter(Dish.id == dish_id).first()

    plate_cost, margin_pounds, margin_percent = stats["costs"][dish_id]

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
        dish_id=dish_id,
        dish_name=dish.name,
        category=category,
        menu_price=dish.menu_price,
        plate_cost=plate_cost,
        margin_pounds=margin_pounds,
        margin_percent=margin_percent,
        units_sold=stats["units"][dish_id],
        menu_mix_percent=dish_menu_mix,
        popularity_threshold=popularity_threshold,
        profitability_threshold=weighted_avg_margin,
        quadrant=quadrant,
        skipped_ingredients=dish.skipped_ingredients,
    )


def classify_all_dishes(db) -> list[DishClassificationOut]:
    """
    Classifies every eligible dish, category by category.
    Incomplete dishes are excluded — see list_incomplete_dishes.
    """
    results = []

    for category in DishType:
        eligible = get_eligible_dishes(db, category)
        stats = get_category_stats(db, eligible)

        for dish in eligible:
            results.append(classify_dish(db, dish.id, category, eligible, stats))

    return results

def build_action_list(db) -> list[ActionItemOut]:
    """
    Turns quadrant classifications into a ranked action list with £ impact.

    Cutting a Dog assumes its covers transfer to a category-average dish
    rather than being lost entirely.
    """
    actions = []

    for category in DishType:
        eligible = get_eligible_dishes(db, category)
        if not eligible:
            continue

        stats = get_category_stats(db, eligible)
        category_units = get_category_units_sold(stats)

        for dish in eligible:
            c = classify_dish(db, dish.id, category, eligible, stats)
            dish_units = stats["units"][dish.id]

            if c.quadrant == QuadrantType.STAR:
                continue  # no action needed

            elif c.quadrant == QuadrantType.PLOWHORSE:
                impact = (c.profitability_threshold - c.margin_pounds) * dish_units
                action = "Reprice or re-engineer recipe to close margin gap"

            elif c.quadrant == QuadrantType.DOG:
                impact = (c.profitability_threshold - c.margin_pounds) * dish_units
                action = "Consider cutting from menu"

            elif c.quadrant == QuadrantType.PUZZLE:
                threshold_units = (c.popularity_threshold / 100) * category_units
                impact = c.margin_pounds * (threshold_units - dish_units)
                action = "Promote or reposition on menu"

            else:
                raise ValueError(f"Unrecognised quadrant: {c.quadrant}")

            actions.append(ActionItemOut(
                dish_id=c.dish_id,
                dish_name=dish.name,
                quadrant=c.quadrant,
                action=action,
                impact_pounds=round(impact, 2),
            ))

    actions.sort(key=lambda a: a.impact_pounds, reverse=True)
    return actions