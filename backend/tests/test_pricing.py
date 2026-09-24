"""
Tests for choosing which price to cost with (costing.best_price).

Rule:
  1. The restaurant's own price (invoice / supplier list / manual), most recent.
  2. Otherwise the most recent benchmark.
  Prices dated after the costing date are ignored.

Every test uses one ingredient, "Mozzarella", priced per gram. add_ingredient
gives it a benchmark of £0.0070/g dated 1 Jan 2026. Costing date is 1 Oct 2026
unless stated.
"""

from datetime import date

import pytest

from costing import best_price, cost_dish
from models import DishType, PriceSource, UnitType

AS_OF = date(2026, 10, 1)


@pytest.fixture
def mozzarella(add_ingredient):
    return add_ingredient("Mozzarella", UnitType.GRAM, 0.0070)


def test_benchmark_used_when_no_own_price(db, mozzarella):
    price = best_price(db, mozzarella.id, as_of=AS_OF)

    assert price.source == PriceSource.BENCHMARK
    assert price.price_per_unit == 0.0070


def test_own_price_beats_newer_benchmark(db, mozzarella, add_price):
    # Invoice from March vs a benchmark updated in September.
    # The invoice is what the restaurant actually pays, so it wins despite being older.
    add_price(mozzarella, 0.0080, PriceSource.INVOICE, date(2026, 3, 1))
    add_price(mozzarella, 0.0065, PriceSource.BENCHMARK, date(2026, 9, 1))

    price = best_price(db, mozzarella.id, as_of=AS_OF)

    assert price.source == PriceSource.INVOICE
    assert price.price_per_unit == 0.0080


def test_newest_own_price_wins(db, mozzarella, add_price):
    # Two invoices and a manual price: the most recent of the three wins,
    # whichever kind of own price it is.
    add_price(mozzarella, 0.0074, PriceSource.INVOICE, date(2026, 6, 3))
    add_price(mozzarella, 0.0082, PriceSource.INVOICE, date(2026, 9, 12))
    add_price(mozzarella, 0.0078, PriceSource.MANUAL, date(2026, 8, 1))

    assert best_price(db, mozzarella.id, as_of=AS_OF).price_per_unit == 0.0082


def test_future_prices_are_ignored(db, mozzarella, add_price):
    # An invoice dated after the costing date isn't in effect yet,
    # so costing falls back to the benchmark.
    add_price(mozzarella, 0.0090, PriceSource.INVOICE, date(2026, 12, 1))

    price = best_price(db, mozzarella.id, as_of=AS_OF)

    assert price.source == PriceSource.BENCHMARK


def test_same_date_last_entered_wins(db, mozzarella, add_price):
    # A corrected invoice entered the same day replaces the first one.
    add_price(mozzarella, 0.0080, PriceSource.INVOICE, date(2026, 9, 1))
    add_price(mozzarella, 0.0079, PriceSource.INVOICE, date(2026, 9, 1))

    assert best_price(db, mozzarella.id, as_of=AS_OF).price_per_unit == 0.0079


def test_cost_dish_uses_the_best_price(db, mozzarella, add_price, add_dish):
    # 100 g mozzarella on a £5.00 dish.
    # Benchmark £0.0070/g -> £0.70. Invoice £0.0080/g -> £0.80.
    # With the invoice in effect: plate cost £0.80, margin £4.20, 84.0%.
    add_price(mozzarella, 0.0080, PriceSource.INVOICE, date(2026, 3, 1))
    dish = add_dish("Caprese", 5.00, DishType.STARTER, recipe=[(mozzarella, 100)])

    assert cost_dish(db, dish.id) == (0.80, 4.20, 84.0)


def test_ingredient_with_no_price_is_an_error(db, add_dish):
    # A missing price must never be costed as £0, which would inflate the margin.
    from models import Ingredient
    unpriced = Ingredient(name="Truffle", unit=UnitType.GRAM)
    db.add(unpriced)
    db.commit()
    dish = add_dish("Truffle pizza", 20.00, DishType.MAIN, recipe=[(unpriced, 5)])

    with pytest.raises(ValueError):
        cost_dish(db, dish.id)
