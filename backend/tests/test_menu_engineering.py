"""
Tests for menu-engineering classification and the action list.

Worked example used by most tests: four mains, each with a plate cost of
exactly £2.00, so margin = menu price - £2.00.

    Dish        Price  Margin  Units  Menu mix
    Star        £12    £10     40     40%
    Plowhorse   £7     £5      40     40%
    Puzzle      £14    £12     10     10%
    Dog         £6     £4      10     10%
                               ---
                               100

Popularity threshold = 0.7 x (100% / 4 dishes)       = 17.5%
Profitability threshold (units-weighted avg margin)
    = (10x40 + 5x40 + 12x10 + 4x10) / 100 = 760 / 100 = £7.60

    Star       40% >= 17.5%  and  £10 >= £7.60  -> popular, profitable
    Plowhorse  40% >= 17.5%  but  £5  <  £7.60  -> popular, not profitable
    Puzzle     10% <  17.5%  but  £12 >= £7.60  -> not popular, profitable
    Dog        10% <  17.5%  and  £4  <  £7.60  -> neither
"""

from datetime import date

import pytest

from menu_engineering import build_action_list, classify_all_dishes, list_incomplete_dishes
from models import DishType, QuadrantType
from conftest import SEPTEMBER


@pytest.fixture
def four_mains(add_dish, cost_item):
    plate = [(cost_item, 2)]  # £2.00 plate cost
    return {
        "Star": add_dish("Star", 12.00, DishType.MAIN, recipe=plate, units_sold=40),
        "Plowhorse": add_dish("Plowhorse", 7.00, DishType.MAIN, recipe=plate, units_sold=40),
        "Puzzle": add_dish("Puzzle", 14.00, DishType.MAIN, recipe=plate, units_sold=10),
        "Dog": add_dish("Dog", 6.00, DishType.MAIN, recipe=plate, units_sold=10),
    }


def results_by_name(db):
    return {c.dish_name: c for c in classify_all_dishes(db, *SEPTEMBER)}


# --- Classification ---------------------------------------------------------

def test_each_dish_lands_in_the_expected_quadrant(db, four_mains):
    results = results_by_name(db)

    assert results["Star"].quadrant == QuadrantType.STAR
    assert results["Plowhorse"].quadrant == QuadrantType.PLOWHORSE
    assert results["Puzzle"].quadrant == QuadrantType.PUZZLE
    assert results["Dog"].quadrant == QuadrantType.DOG


def test_thresholds_and_menu_mix(db, four_mains):
    results = results_by_name(db)

    for c in results.values():
        assert c.popularity_threshold == pytest.approx(17.5)
        assert c.profitability_threshold == pytest.approx(7.60)

    assert results["Star"].menu_mix_percent == pytest.approx(40.0)
    assert results["Dog"].menu_mix_percent == pytest.approx(10.0)


def test_excluded_dish_is_removed_from_the_denominator(db, four_mains, add_dish):
    # A fifth main with lots of sales but no recipe. It must be excluded,
    # AND it must not shift the other dishes' thresholds.
    # If it leaked into the totals: 5 dishes -> threshold 0.7 x 20% = 14%,
    # and 200 total units -> Star's mix would drop to 20%.
    add_dish("No recipe yet", 9.00, DishType.MAIN, units_sold=100)

    results = results_by_name(db)

    assert "No recipe yet" not in results
    assert results["Star"].popularity_threshold == pytest.approx(17.5)
    assert results["Star"].menu_mix_percent == pytest.approx(40.0)
    assert results["Star"].profitability_threshold == pytest.approx(7.60)


def test_categories_are_classified_separately(db, four_mains, add_dish, cost_item):
    # A dessert selling 500 units must not affect the mains' numbers.
    # On its own in its category: 1 dish -> threshold 0.7 x 100% = 70%,
    # it has 100% of dessert sales and exactly the average margin -> Star.
    add_dish("Tiramisu", 6.00, DishType.DESSERT, recipe=[(cost_item, 2)], units_sold=500)

    results = results_by_name(db)

    assert results["Star"].menu_mix_percent == pytest.approx(40.0)
    assert results["Star"].profitability_threshold == pytest.approx(7.60)
    assert results["Tiramisu"].popularity_threshold == pytest.approx(70.0)
    assert results["Tiramisu"].quadrant == QuadrantType.STAR


def test_incomplete_dish_lists_every_reason(db, add_dish):
    add_dish("Half-entered", 8.00, category=None)

    incomplete = list_incomplete_dishes(db, *SEPTEMBER)

    assert len(incomplete) == 1
    # No sales is not a reason any more: a dish on the menu that sold nothing
    # has genuinely sold 0 (see test_periods.py).
    assert incomplete[0].reasons == ["No category set", "No recipe saved"]


# --- Action list ------------------------------------------------------------
#
# Every impact is a change in contribution (£), using the numbers above:
#   Plowhorse: (7.60 - 5) x 40                    = £104.00
#   Puzzle:    threshold units = 17.5% x 100      = 17.5
#              12 x (17.5 - 10)                   = £90.00
#   Dog:       (7.60 - 4) x 10                    = £36.00
#   Star:      no action

def test_action_list_impacts_and_ranking(db, four_mains):
    actions = build_action_list(db, *SEPTEMBER)

    assert [(a.dish_name, a.impact_pounds) for a in actions] == [
        ("Plowhorse", 104.00),
        ("Puzzle", 90.00),
        ("Dog", 36.00),
    ]


# --- The concrete change on each action (proposed_change) -------------------
#
# Same worked example, prices unchanged since September (so today's = September's):
#   Plowhorse £7:  margin £5, line £7.60 -> gap £2.60 per plate -> target £9.60
#   Dog £6:        margin £4, line £7.60 -> gap £3.60 per plate -> target £9.60
#   Puzzle:        17.5 plates to reach the line, sold 10 -> 7.5, rounded up to 8;
#                  over September's 30 days, 8 / 30 = 0.27 a day

def test_each_action_says_what_to_change(db, four_mains):
    actions = {a.dish_name: a for a in build_action_list(db, *SEPTEMBER)}

    plowhorse, dog, puzzle = actions["Plowhorse"], actions["Dog"], actions["Puzzle"]
    assert (plowhorse.current_price, plowhorse.margin_gap, plowhorse.target_price) == (7.00, 2.60, 9.60)
    assert (dog.current_price, dog.margin_gap, dog.target_price) == (6.00, 3.60, 9.60)
    assert (puzzle.extra_units, puzzle.extra_per_day) == (8, 0.27)
    assert puzzle.target_price is None


def test_a_target_starts_from_todays_price(db, four_mains, add_menu_price):
    # The Plowhorse went up to £8.00 after September: the gap is now £7.60 - (£8 - £2) = £1.60.
    # The September impact is unchanged (it's about the period); the target uses today's price.
    add_menu_price(four_mains["Plowhorse"], 8.00, date(2026, 10, 1))
    plowhorse = next(a for a in build_action_list(db, *SEPTEMBER, today=date(2026, 10, 15))
                     if a.dish_name == "Plowhorse")

    assert plowhorse.impact_pounds == 104.00
    assert (plowhorse.current_price, plowhorse.margin_gap, plowhorse.target_price) == (8.00, 1.60, 9.60)


def test_a_dish_already_repriced_past_the_line_gets_no_target(db, four_mains, add_menu_price):
    add_menu_price(four_mains["Plowhorse"], 10.00, date(2026, 10, 1))   # margin £8 >= £7.60
    plowhorse = next(a for a in build_action_list(db, *SEPTEMBER, today=date(2026, 10, 15))
                     if a.dish_name == "Plowhorse")
    assert (plowhorse.current_price, plowhorse.target_price) == (10.00, None)


def test_stars_get_no_action(db, four_mains):
    actions = build_action_list(db, *SEPTEMBER)

    assert all(a.quadrant != QuadrantType.STAR for a in actions)


def test_empty_menu_gives_empty_results(db):
    assert classify_all_dishes(db, *SEPTEMBER) == []
    assert build_action_list(db, *SEPTEMBER) == []
