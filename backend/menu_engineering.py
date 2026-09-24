from datetime import date
from models import SalesRecord, Dish, DishIngredient, DishType, QuadrantType
from costing import average_menu_price, cost_dish
from schemas import DishClassificationOut, ActionItemOut, IncompleteDishOut

# Every analysis runs over a date range, start to end inclusive.
#
# Which sales count: records that lie wholly inside the range. A record that
# only partly overlaps it (e.g. a monthly total when the range is 10-20 June)
# is left out rather than shared across days, so no numbers are invented.
# The Sales coverage route reports how many were left out.
#
# Which dishes count: those on the menu for the WHOLE range. Menu engineering
# compares dishes over the same period, so a special launched mid-month is left
# out (with a reason) rather than looking unpopular. Dishes not on the menu at
# all during the range are simply not part of it.

def get_dish_units_sold(db, dish_id: int, start: date, end: date) -> int:
    """
    Sums units_sold across the dish's SalesRecord rows that lie wholly inside
    start..end. Returns 0 if there are none: for a dish on the menu for the
    whole range, that's a real zero, not missing data.
    """
    records = db.query(SalesRecord).filter(
        SalesRecord.dish_id == dish_id,
        SalesRecord.period_start >= start,
        SalesRecord.period_end <= end,
    ).all()

    total = 0
    for record in records:
        total += record.units_sold

    return total

def range_has_sales(db, start: date, end: date) -> bool:
    """True if any sales are recorded inside the range. Without any, there's nothing to analyse."""
    return db.query(SalesRecord).filter(
        SalesRecord.period_start >= start,
        SalesRecord.period_end <= end,
    ).first() is not None


def on_menu_during(dish, start: date, end: date) -> bool:
    """On the menu for at least part of the range."""
    return dish.on_menu_from <= end and (dish.on_menu_until is None or dish.on_menu_until >= start)


def get_incomplete_reasons(db, dish, start: date, end: date) -> list[str]:
    """
    Reasons a dish on the menu during the range can't be meaningfully classified.
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

    on_whole_range = dish.on_menu_from <= start and (dish.on_menu_until is None or dish.on_menu_until >= end)
    if not on_whole_range:
        reasons.append("Only on the menu for part of this period")

    return reasons


def get_eligible_dishes(db, category: DishType, start: date, end: date) -> list[Dish]:
    """
    Dishes in a category that are complete enough to classify for the range.
    This set defines the analysis population — it drives both the
    classifications returned and the denominators the thresholds use.
    """
    dishes = db.query(Dish).filter(Dish.category == category).all()
    return [d for d in dishes
            if on_menu_during(d, start, end) and not get_incomplete_reasons(db, d, start, end)]


def list_incomplete_dishes(db, start: date, end: date) -> list[IncompleteDishOut]:
    """
    Every dish on the menu during the range but excluded from analysis,
    with the reasons why. Outstanding work, not findings.
    """
    results = []

    for dish in db.query(Dish).all():
        if not on_menu_during(dish, start, end):
            continue
        reasons = get_incomplete_reasons(db, dish, start, end)
        if reasons:
            results.append(IncompleteDishOut(
                dish_id=dish.id,
                dish_name=dish.name,
                category=dish.category,
                reasons=reasons,
            ))

    return results

def get_category_stats(db, dishes: list[Dish], start: date, end: date) -> dict:
    """
    Costs and units sold for every dish in a set, worked out ONCE.

    The helpers below all read from this instead of querying the database
    themselves. Before, every dish re-costed its whole category, so a category
    of n dishes was costed n x n times. Now it's n. The formulas are unchanged.

    Margins use the menu price actually charged over the range, weighted by
    each day's units (costing.average_menu_price), so a price change part-way
    through is counted correctly.

    Returns {"units": {dish_id: units},
             "prices": {dish_id: menu_price},
             "costs": {dish_id: (plate_cost, margin_pounds, margin_percent)},
             "margins": {dish_id: margin_pounds}}.
    """
    units = {}
    prices = {}
    costs = {}
    margins = {}
    for dish in dishes:
        units[dish.id] = get_dish_units_sold(db, dish.id, start, end)
        prices[dish.id] = average_menu_price(db, dish.id, start, end)
        costs[dish.id] = cost_dish(db, dish.id, prices[dish.id])
        plate_cost, margin_pounds, margin_percent = costs[dish.id]
        margins[dish.id] = margin_pounds

    return {"units": units, "prices": prices, "costs": costs, "margins": margins}


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
        menu_price=stats["prices"][dish_id],
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


def classify_all_dishes(db, start: date, end: date) -> list[DishClassificationOut]:
    """
    Classifies every eligible dish for the range, category by category.
    Incomplete dishes are excluded — see list_incomplete_dishes.
    No sales recorded in the range at all -> nothing to classify.
    """
    results = []
    if not range_has_sales(db, start, end):
        return results

    for category in DishType:
        eligible = get_eligible_dishes(db, category, start, end)
        stats = get_category_stats(db, eligible, start, end)

        for dish in eligible:
            results.append(classify_dish(db, dish.id, category, eligible, stats))

    return results

def build_action_list(db, start: date, end: date) -> list[ActionItemOut]:
    """
    Turns quadrant classifications for the range into a ranked action list with £ impact.

    Cutting a Dog assumes its covers transfer to a category-average dish
    rather than being lost entirely.
    """
    actions = []
    if not range_has_sales(db, start, end):
        return actions

    for category in DishType:
        eligible = get_eligible_dishes(db, category, start, end)
        if not eligible:
            continue

        stats = get_category_stats(db, eligible, start, end)
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