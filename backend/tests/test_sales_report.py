"""
Tests for the Sales page's money figures (sales_report.py).
"""

from datetime import date

import pytest

import main
from models import DishType
from sales_report import sales_summary

SEP_10_TO_20 = (date(2026, 9, 10), date(2026, 9, 20))


@pytest.fixture
def menu(add_dish, add_menu_price, cost_item):
    # Margherita £10.00, rising to £12.00 on 15 Sep. Tiramisu £7.00.
    margherita = add_dish("Margherita", 10.00, DishType.MAIN, recipe=[(cost_item, 2)])
    add_menu_price(margherita, 12.00, date(2026, 9, 15))
    tiramisu = add_dish("Tiramisu", 7.00, DishType.DESSERT, recipe=[(cost_item, 1)])
    return {"margherita": margherita, "tiramisu": tiramisu}


def test_each_day_is_priced_at_what_was_charged(db, menu, add_sales):
    # 10 Sep: 3 Margherita at £10 = £30; 16 Sep: 2 at £12 = £24; 16 Sep: 4 Tiramisu at £7 = £28
    add_sales(menu["margherita"], 3, date(2026, 9, 10))
    add_sales(menu["margherita"], 2, date(2026, 9, 16))
    add_sales(menu["tiramisu"], 4, date(2026, 9, 16))

    s = sales_summary(db, *SEP_10_TO_20)
    days = {d.day: d for d in s.days}

    assert (days[date(2026, 9, 10)].sales, days[date(2026, 9, 16)].sales) == (30.00, 52.00)
    assert (s.total_sales, s.total_units) == (82.00, 9)
    assert len(s.days) == 11                       # every day, including the empty ones
    assert days[date(2026, 9, 12)].sales == 0


def test_categories_and_dishes_are_ranked_by_sales(db, menu, add_sales):
    add_sales(menu["margherita"], 3, date(2026, 9, 10))   # £30
    add_sales(menu["tiramisu"], 5, date(2026, 9, 11))     # £35

    s = sales_summary(db, *SEP_10_TO_20)

    assert [(d.name, d.sales) for d in s.dishes] == [("Tiramisu", 35.00), ("Margherita", 30.00)]
    assert [(c.category, c.sales) for c in s.categories] == [(DishType.DESSERT, 35.00), (DishType.MAIN, 30.00)]


def test_a_period_total_is_spread_across_its_days(db, menu, add_sales):
    # 10 Margherita over 10-19 Sep, 1 a day: 5 days at £10 (10-14) + 5 at £12 (15-19) = £110
    add_sales(menu["margherita"], 10, date(2026, 9, 10), date(2026, 9, 19))

    s = sales_summary(db, *SEP_10_TO_20)
    assert s.total_sales == pytest.approx(110.00)
    assert {d.day: d.units for d in s.days}[date(2026, 9, 12)] == 1


def test_records_only_partly_in_the_period_are_left_out(db, menu, add_sales):
    add_sales(menu["tiramisu"], 30, date(2026, 9, 1), date(2026, 9, 30))   # a September total

    assert sales_summary(db, *SEP_10_TO_20).total_sales == 0


def test_the_route_uses_the_chosen_period(db, menu, add_sales):
    add_sales(menu["tiramisu"], 2, date(2026, 9, 11))

    s = main.get_sales_summary(*SEP_10_TO_20, db=db)
    assert (s.start, s.end, s.total_sales) == (date(2026, 9, 10), date(2026, 9, 20), 14.00)
