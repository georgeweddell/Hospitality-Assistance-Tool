"""
Tests for analysing a date range (the rules George approved):

  A. Sales are stored per dish per day (or as a total for a period).
  B. Only records wholly inside the range count; partly-overlapping ones are left out.
  C. A dish on the menu for only part of the range is left out, with a reason.
  D. A dish on the menu for the whole range with no sales has sold 0, and is analysed.

Worked example: two mains, both with a £2.00 plate cost, on the menu all of 2026.

    Dish      Price  Margin   June units   July units
    Pizza A   £12    £10      30           10
    Pizza B   £6     £4       10           30

June: 40 units. A has 75% of sales. Threshold = 0.7 x (100% / 2) = 35%.
      Weighted avg margin = (10x30 + 4x10) / 40 = 340 / 40 = £8.50
      A: 75% >= 35%, £10 >= £8.50 -> Star.   B: 25% < 35%, £4 < £8.50 -> Dog.
July: the other way round.
      Weighted avg margin = (10x10 + 4x30) / 40 = 220 / 40 = £5.50
      A: 25% < 35%, £10 >= £5.50 -> Puzzle.  B: 75% >= 35%, £4 < £5.50 -> Plowhorse.
"""

from datetime import date

import pytest
from fastapi import HTTPException

from main import get_sales_coverage, get_sales_entries, save_sales_entries
from menu_engineering import classify_all_dishes, list_incomplete_dishes
from models import DishType, QuadrantType, SalesRecord
from periods import default_range, month_bounds
from schemas import SalesEntryIn

JUNE = (date(2026, 6, 1), date(2026, 6, 30))
JULY = (date(2026, 7, 1), date(2026, 7, 31))


@pytest.fixture
def two_pizzas(db, add_dish, cost_item):
    plate = [(cost_item, 2)]
    a = add_dish("Pizza A", 12.00, DishType.MAIN, recipe=plate)
    b = add_dish("Pizza B", 6.00, DishType.MAIN, recipe=plate)
    for dish, june, july in [(a, 30, 10), (b, 10, 30)]:
        db.add(SalesRecord(dish_id=dish.id, units_sold=june, period_start=JUNE[0], period_end=JUNE[1]))
        db.add(SalesRecord(dish_id=dish.id, units_sold=july, period_start=JULY[0], period_end=JULY[1]))
    db.commit()
    return {"A": a, "B": b}


def quadrants(db, start, end):
    return {c.dish_name: c.quadrant for c in classify_all_dishes(db, start, end)}


def test_each_month_only_counts_its_own_sales(db, two_pizzas):
    assert quadrants(db, *JUNE) == {"Pizza A": QuadrantType.STAR, "Pizza B": QuadrantType.DOG}
    assert quadrants(db, *JULY) == {"Pizza A": QuadrantType.PUZZLE, "Pizza B": QuadrantType.PLOWHORSE}


def test_a_range_spanning_both_months_adds_them(db, two_pizzas):
    # June + July: A = 40, B = 40, so 50% each, both popular.
    # Weighted avg = (10x40 + 4x40) / 80 = £7.00 -> A Star, B Plowhorse.
    results = {c.dish_name: c for c in classify_all_dishes(db, JUNE[0], JULY[1])}
    assert results["Pizza A"].units_sold == 40
    assert results["Pizza A"].profitability_threshold == pytest.approx(7.00)
    assert results["Pizza B"].quadrant == QuadrantType.PLOWHORSE


def test_daily_records_add_up_inside_the_range(db, add_dish, cost_item):
    # Three daily records for 1, 2 and 3 June, and one for 1 July (outside June).
    dish = add_dish("Daily pizza", 10.00, DishType.MAIN, recipe=[(cost_item, 2)])
    for day, units in [(1, 5), (2, 7), (3, 9)]:
        db.add(SalesRecord(dish_id=dish.id, units_sold=units,
                           period_start=date(2026, 6, day), period_end=date(2026, 6, day)))
    db.add(SalesRecord(dish_id=dish.id, units_sold=100, period_start=date(2026, 7, 1), period_end=date(2026, 7, 1)))
    db.commit()

    assert classify_all_dishes(db, *JUNE)[0].units_sold == 5 + 7 + 9


def test_record_only_partly_inside_the_range_is_left_out(db, two_pizzas):
    # 10-20 June: the June records cover all of June, so they're only partly
    # inside. They're left out (not shared across days), so there's nothing to analyse,
    # and coverage reports 2 records left out.
    part_of_june = (date(2026, 6, 10), date(2026, 6, 20))

    assert classify_all_dishes(db, *part_of_june) == []
    coverage = get_sales_coverage(*part_of_june, db=db)
    assert coverage.partial_records == 2
    assert coverage.days_with_sales == []


def test_dish_on_menu_for_part_of_the_range_is_left_out_with_a_reason(db, two_pizzas, add_dish, cost_item):
    # A special launched on 15 July: on the menu for only part of July.
    special = add_dish("Special", 15.00, DishType.MAIN, recipe=[(cost_item, 2)],
                       on_menu_from=date(2026, 7, 15))
    db.add(SalesRecord(dish_id=special.id, units_sold=50, period_start=date(2026, 7, 15), period_end=date(2026, 7, 31)))
    db.commit()

    assert "Special" not in quadrants(db, *JULY)
    # ...and it doesn't shift the others: still 2 dishes, threshold 35%.
    assert [c.popularity_threshold for c in classify_all_dishes(db, *JULY)] == pytest.approx([35.0, 35.0])
    incomplete = {i.dish_name: i.reasons for i in list_incomplete_dishes(db, *JULY)}
    assert incomplete == {"Special": ["Only on the menu for part of this period"]}


def test_dish_not_on_the_menu_at_all_is_not_part_of_the_range(db, two_pizzas, add_dish, cost_item):
    add_dish("Winter stew", 14.00, DishType.MAIN, recipe=[(cost_item, 2)],
             on_menu_from=date(2026, 1, 1), on_menu_until=date(2026, 3, 31))

    assert "Winter stew" not in quadrants(db, *JULY)
    assert list_incomplete_dishes(db, *JULY) == []


def test_dish_on_the_menu_with_no_sales_has_sold_zero(db, two_pizzas, add_dish, cost_item):
    # On the menu all of June, nothing recorded -> 0 sold, analysed.
    # 3 mains now: threshold 0.7 x 33.3% = 23.3%. Its mix is 0%, so it's unpopular.
    # Its margin £13 is above the June average (£8.50, unchanged: 0 units add nothing),
    # so it's a Puzzle with impact 13 x (23.3% x 40 - 0) = 13 x 9.33 = £121.33.
    add_dish("Nobody orders it", 15.00, DishType.MAIN, recipe=[(cost_item, 2)])

    results = {c.dish_name: c for c in classify_all_dishes(db, *JUNE)}
    zero = results["Nobody orders it"]
    assert zero.units_sold == 0
    assert zero.menu_mix_percent == 0
    assert zero.profitability_threshold == pytest.approx(8.50)
    assert zero.quadrant == QuadrantType.PUZZLE


def test_no_sales_in_the_range_at_all_gives_nothing_to_analyse(db, two_pizzas):
    assert classify_all_dishes(db, date(2026, 9, 1), date(2026, 9, 30)) == []


# --- Default range and month maths -------------------------------------------------------

def test_month_bounds_include_short_months_and_leap_years():
    assert month_bounds(date(2026, 2, 14)) == (date(2026, 2, 1), date(2026, 2, 28))
    assert month_bounds(date(2028, 2, 14)) == (date(2028, 2, 1), date(2028, 2, 29))
    assert month_bounds(date(2026, 12, 31)) == (date(2026, 12, 1), date(2026, 12, 31))


def test_default_range_is_the_latest_month_with_sales(db, two_pizzas):
    assert default_range(db) == JULY


# --- Entering a total for a period ----------------------------------------------------------

def test_saving_a_period_twice_replaces_rather_than_adds(db, add_dish, cost_item):
    dish = add_dish("Pizza C", 10.00, DishType.MAIN, recipe=[(cost_item, 2)])
    august = (date(2026, 8, 1), date(2026, 8, 31))

    save_sales_entries([SalesEntryIn(dish_id=dish.id, units_sold=50)], *august, db=db)
    save_sales_entries([SalesEntryIn(dish_id=dish.id, units_sold=60)], *august, db=db)

    entries = {e.dish_name: e.units_sold for e in get_sales_entries(*august, db=db)}
    assert entries["Pizza C"] == 60


def test_blank_removes_the_total(db, add_dish, cost_item):
    dish = add_dish("Pizza C", 10.00, DishType.MAIN, recipe=[(cost_item, 2)])
    august = (date(2026, 8, 1), date(2026, 8, 31))

    save_sales_entries([SalesEntryIn(dish_id=dish.id, units_sold=50)], *august, db=db)
    save_sales_entries([SalesEntryIn(dish_id=dish.id, units_sold=None)], *august, db=db)

    assert db.query(SalesRecord).count() == 0


def test_total_is_rejected_when_daily_data_already_covers_the_period(db, add_dish, cost_item):
    # Daily till data for 5 August exists, so a total for all of August would
    # count those sales twice. Nothing is saved.
    dish = add_dish("Pizza C", 10.00, DishType.MAIN, recipe=[(cost_item, 2)])
    db.add(SalesRecord(dish_id=dish.id, units_sold=8, period_start=date(2026, 8, 5), period_end=date(2026, 8, 5)))
    db.commit()

    with pytest.raises(HTTPException) as error:
        save_sales_entries([SalesEntryIn(dish_id=dish.id, units_sold=50)], date(2026, 8, 1), date(2026, 8, 31), db=db)
    assert error.value.status_code == 422
    assert db.query(SalesRecord).count() == 1
