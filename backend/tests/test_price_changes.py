"""
Tests for ingredient price changes and their effect on dishes (price_changes.py).

A £1.00-each cost item; Margherita uses 2 a plate (plate cost £2.00) and sells
30 plates in September. A £0.50 rise therefore adds £1.00 a plate and takes
30 x £1.00 = £30 off September's contribution.
"""

from datetime import date

import pytest

import main
from models import DishType, PriceSource, UnitType
from price_changes import find_menu_price_changes, find_price_changes

SEPTEMBER = (date(2026, 9, 1), date(2026, 9, 30))
TODAY = date(2026, 10, 20)


@pytest.fixture
def margherita(add_dish, cost_item, add_sales):
    dish = add_dish('Margherita', 10.00, DishType.MAIN, recipe=[(cost_item, 2)])
    add_sales(dish, 30, date(2026, 9, 7))
    return dish


def test_a_rise_adds_to_each_plate_and_costs_contribution(db, margherita, cost_item, add_price):
    add_price(cost_item, 1.50, PriceSource.INVOICE, date(2026, 9, 10))
    [change] = find_price_changes(db, SEPTEMBER[0], TODAY, {margherita.id: 30})

    assert (change.old_price, change.new_price, change.change_percent) == (1.00, 1.50, 50.0)
    assert change.is_alert
    assert [(e.name, e.per_plate) for e in change.dishes] == [('Margherita', 1.00)]
    assert change.period_effect == -30.00


def test_a_small_rise_or_a_fall_is_listed_but_not_an_alert(db, margherita, cost_item, add_price):
    # £1.00 -> £1.04 is +4%, under the 5% alert line; then back down to £0.90
    add_price(cost_item, 1.04, PriceSource.INVOICE, date(2026, 9, 10))
    add_price(cost_item, 0.90, PriceSource.INVOICE, date(2026, 9, 20))
    changes = {c.day: c for c in find_price_changes(db, SEPTEMBER[0], TODAY)}

    assert changes[date(2026, 9, 10)].change_percent == 4.0
    assert not changes[date(2026, 9, 10)].is_alert
    assert changes[date(2026, 9, 20)].change_percent == pytest.approx(-13.5)   # 1.04 -> 0.90
    assert not changes[date(2026, 9, 20)].is_alert


def test_a_new_benchmark_is_not_a_change_when_the_restaurant_has_its_own_price(db, margherita, cost_item, add_price):
    add_price(cost_item, 1.20, PriceSource.INVOICE, date(2026, 8, 1))      # own price, before the window
    add_price(cost_item, 2.00, PriceSource.BENCHMARK, date(2026, 9, 15))   # costing still uses the invoice
    assert find_price_changes(db, SEPTEMBER[0], TODAY) == []


def test_only_ingredients_of_dishes_on_the_menu_today_count(db, add_dish, add_ingredient, add_price):
    truffle = add_ingredient('Truffle', UnitType.GRAM, 1.00)
    add_dish('Truffle Pizza', 20.00, DishType.MAIN, recipe=[(truffle, 5)], on_menu_until=date(2026, 9, 5))
    add_price(truffle, 1.50, PriceSource.INVOICE, date(2026, 9, 10))
    assert find_price_changes(db, SEPTEMBER[0], TODAY) == []


def test_the_route_marks_changes_after_the_period(db, margherita, cost_item, add_price):
    # The route's "today" is the real date, so the period is 1-8 Sep and the change 10 Sep:
    # after the period, before today.
    add_price(cost_item, 1.50, PriceSource.INVOICE, date(2026, 9, 10))
    [change] = main.get_price_changes(date(2026, 9, 1), date(2026, 9, 8), db=db)
    assert change.after_period and change.is_alert
    assert change.dishes[0].per_plate == 1.00
    assert change.period_effect == -30.00   # at the period's 30 plates (sold 7 Sep)


def test_menu_price_changes_in_the_window(db, margherita, add_menu_price):
    # Margherita was £10.00 from 1 Jan; £11.00 from 15 Sep; £11.50 from 5 Oct
    add_menu_price(margherita, 11.00, date(2026, 9, 15))
    add_menu_price(margherita, 11.50, date(2026, 10, 5))
    changes = find_menu_price_changes(db, SEPTEMBER[0], TODAY)
    assert [(c.day, c.old_price, c.new_price) for c in changes] == [
        (date(2026, 10, 5), 11.00, 11.50),     # newest first
        (date(2026, 9, 15), 10.00, 11.00),
    ]
