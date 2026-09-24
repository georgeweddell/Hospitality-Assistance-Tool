"""
Tests for the benchmark price list (data/benchmark_prices.csv) and for
syncing it into a database without losing anything.
"""

from datetime import date

import pytest

from benchmarks import read_benchmarks, sync_benchmarks
from costing import best_price
from models import DishType, Ingredient, IngredientPrice, PriceSource, UnitType
from seed_demo import DISHES, MARGHERITA


# --- The file itself -----------------------------------------------------------------

def test_the_list_loads_with_unique_names():
    rows = read_benchmarks()
    names = [name.lower() for name, _, _ in rows]
    assert len(rows) > 200
    assert len(names) == len(set(names))


def test_prices_are_stored_per_base_unit():
    prices = {name: (unit, price) for name, unit, price in read_benchmarks()}
    # "beef mince, gram, 8.50, kg" -> £8.50 / 1,000 g = £0.0085 per gram
    assert prices['beef mince'] == (UnitType.GRAM, pytest.approx(0.0085))
    # "double cream, ml, 3.50, l" -> £3.50 / 1,000 ml = £0.0035 per ml
    assert prices['double cream'] == (UnitType.ML, pytest.approx(0.0035))
    # "egg, each, 0.30, each" -> £0.30 each
    assert prices['egg'] == (UnitType.EACH, pytest.approx(0.30))


def test_every_demo_recipe_ingredient_is_in_the_list():
    names = {name for name, _, _ in read_benchmarks()}
    used = {ingredient for _, _, _, _, recipe, _ in DISHES for ingredient, _ in recipe} | {i for i, _ in MARGHERITA}
    assert used - names == set()


def test_a_bad_line_is_reported(tmp_path):
    bad = tmp_path / 'bad.csv'
    bad.write_text('name,measured_by,price,per\nflour,gram,1.30,litre\n', encoding='utf-8')
    with pytest.raises(ValueError, match='flour'):
        read_benchmarks(bad)


# --- Syncing into a database ---------------------------------------------------------

ROWS = [('00 flour', UnitType.GRAM, 0.0013), ('basil', UnitType.GRAM, 0.025)]


def test_sync_adds_missing_ingredients_with_a_benchmark_price(db):
    summary = sync_benchmarks(db, ROWS)

    assert (summary['added'], summary['updated'], summary['unchanged']) == (2, 0, 0)
    assert best_price(db, db.query(Ingredient).filter_by(name='basil').one().id).source == PriceSource.BENCHMARK


def test_sync_twice_changes_nothing(db):
    sync_benchmarks(db, ROWS)
    summary = sync_benchmarks(db, ROWS)

    assert (summary['added'], summary['updated'], summary['unchanged']) == (0, 0, 2)
    assert db.query(IngredientPrice).count() == 2


def test_a_changed_benchmark_is_added_as_a_new_dated_price(db):
    sync_benchmarks(db, ROWS, as_of=date(2026, 6, 1))
    summary = sync_benchmarks(db, [('00 flour', UnitType.GRAM, 0.0014)], as_of=date(2026, 10, 1))

    flour = db.query(Ingredient).filter_by(name='00 flour').one()
    history = db.query(IngredientPrice).filter_by(ingredient_id=flour.id).all()
    assert summary['updated'] == 1
    assert sorted(p.price_per_unit for p in history) == [0.0013, 0.0014]   # the old price is kept


def test_own_prices_still_win_after_a_sync(db, add_ingredient, add_price):
    flour = add_ingredient('00 flour', UnitType.GRAM, 0.0013)
    add_price(flour, 0.00125, PriceSource.INVOICE, date(2026, 6, 3))

    sync_benchmarks(db, [('00 flour', UnitType.GRAM, 0.0015)], as_of=date(2026, 9, 1))

    assert best_price(db, flour.id).source == PriceSource.INVOICE


def test_matching_ignores_case(db, add_ingredient):
    add_ingredient('Basil', UnitType.GRAM, 0.025)

    summary = sync_benchmarks(db, [('basil', UnitType.GRAM, 0.025)])

    assert summary['added'] == 0
    assert db.query(Ingredient).count() == 1


def test_a_unit_conflict_is_reported_and_left_alone(db, add_ingredient, add_dish):
    # The restaurant measures its cream in grams; the list says millilitres.
    # Changing the unit would break its recipes' quantities, so it's skipped.
    cream = add_ingredient('double cream', UnitType.GRAM, 0.0035)
    add_dish('Panna cotta', 7.00, DishType.DESSERT, recipe=[(cream, 120)])

    summary = sync_benchmarks(db, [('double cream', UnitType.ML, 0.0035)])

    assert summary['conflicts'] == ['double cream']
    assert db.query(Ingredient).filter_by(name='double cream').one().unit == UnitType.GRAM
