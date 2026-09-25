"""
Tests for the share of a plate cost that comes from the restaurant's own prices
(own_prices.py).

Worked example: two £1.00 ingredients. The cost item stays on its benchmark
price; the invoiced one gets an invoice price of £2.00.
    Margherita: 2 cost items (£2.00, benchmark) + 1 invoiced (£2.00, own)
                -> £2.00 of £4.00 own = 50%
    Diavola:    1 invoiced (£2.00, own)  -> 100%
    Menu, one plate each: £4.00 own of £6.00 = 66.7%
"""

from datetime import date

import pytest

import main
from models import DishType, PriceSource, UnitType
from own_prices import menu_own_share, own_share


@pytest.fixture
def menu(add_dish, add_ingredient, add_price, cost_item):
    invoiced = add_ingredient('Invoiced item', UnitType.EACH, 1.00)
    add_price(invoiced, 2.00, PriceSource.INVOICE, date(2026, 9, 1))
    return {
        'margherita': add_dish('Margherita', 10.00, DishType.MAIN, recipe=[(cost_item, 2), (invoiced, 1)]),
        'diavola': add_dish('Diavola', 12.00, DishType.MAIN, recipe=[(invoiced, 1)]),
    }


def test_the_share_of_a_plate_cost_on_own_prices(db, menu):
    assert own_share(db, menu['margherita'].id, as_of=date(2026, 9, 25)) == 50.0
    assert own_share(db, menu['diavola'].id, as_of=date(2026, 9, 25)) == 100.0


def test_before_the_invoice_everything_is_benchmark(db, menu):
    assert own_share(db, menu['margherita'].id, as_of=date(2026, 8, 25)) == 0.0


def test_a_dish_without_a_recipe_has_no_share(db, add_dish):
    dish = add_dish('Calzone', 13.00, DishType.MAIN)
    assert own_share(db, dish.id) is None


def test_typed_in_prices_count_as_own(db, menu, cost_item, add_price):
    add_price(cost_item, 1.00, PriceSource.MANUAL, date(2026, 9, 2))
    assert own_share(db, menu['margherita'].id, as_of=date(2026, 9, 25)) == 100.0


def test_the_whole_menu_one_plate_each(db, menu):
    assert menu_own_share(db, today=date(2026, 9, 25)) == pytest.approx(66.7)


def test_the_recipes_table_shows_each_dishes_share(db, menu):
    rows = {r.name: r for r in main.list_recipes(db=db)}
    assert rows['Diavola'].own_share_percent == 100.0
