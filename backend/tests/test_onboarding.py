"""
Tests for starting fresh / loading the demo, and the setup checklist's counts.

reset_database runs against the in-memory test engine, never menu.db.
The reset route is only called with a wrong confirmation, which it must
refuse before touching anything.
"""

from datetime import date

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import sessionmaker

from main import reset
from models import Dish, DishType, Ingredient, IngredientPrice, PriceSource, SalesRecord, UnitType
from onboarding import setup_status
from schemas import ResetIn
from benchmarks import read_benchmarks
from seed_demo import DISHES, reset_database

BENCHMARK_COUNT = len(read_benchmarks())

TODAY = date(2026, 9, 24)


def fresh_session(engine):
    # A new session after a reset, so nothing cached from before is seen.
    return sessionmaker(bind=engine)()


def test_dishes_needing_a_recipe_come_in_menu_order(db, add_dish, cost_item):
    # Starters before mains, no category last, then by name. Dishes with a recipe, or off the menu, aren't listed.
    tiramisu = add_dish("Tiramisu", 7.00, DishType.DESSERT)
    diavola = add_dish("Diavola", 13.00, DishType.MAIN)
    arancini = add_dish("Arancini", 7.50, DishType.STARTER)
    special = add_dish("Special", 10.00, None)
    add_dish("Margherita", 11.00, DishType.MAIN, recipe=[(cost_item, 2)])
    add_dish("Marinara", 9.00, DishType.MAIN, on_menu_until=date(2026, 7, 31))

    status = setup_status(db, today=TODAY)
    assert status.needs_recipe == [arancini.id, diavola.id, tiramisu.id, special.id]


def test_start_fresh_keeps_only_the_benchmark_ingredients(engine):
    reset_database(engine, with_demo=False)
    db = fresh_session(engine)

    assert db.query(Dish).count() == 0
    assert db.query(SalesRecord).count() == 0
    assert db.query(Ingredient).count() == BENCHMARK_COUNT
    # One benchmark price each, and nothing else.
    assert db.query(IngredientPrice).count() == BENCHMARK_COUNT
    assert {p.source for p in db.query(IngredientPrice).all()} == {PriceSource.BENCHMARK}


def test_start_fresh_wipes_what_was_there(engine, db, add_dish, cost_item):
    add_dish("Old dish", 10.00, DishType.MAIN, recipe=[(cost_item, 2)], units_sold=40)

    reset_database(engine, with_demo=False)

    assert fresh_session(engine).query(Dish).count() == 0


def test_load_demo_restores_the_pizzeria(engine):
    reset_database(engine, with_demo=True)
    db = fresh_session(engine)

    assert db.query(Dish).count() == len(DISHES)
    assert db.query(SalesRecord).count() > 0
    assert db.query(IngredientPrice).filter(IngredientPrice.source == PriceSource.INVOICE).count() > 0


def test_status_of_a_fresh_start_is_empty(engine):
    reset_database(engine, with_demo=False)

    status = setup_status(fresh_session(engine), today=TODAY)

    assert (status.dishes, status.dishes_with_recipe, status.ingredients_in_use, status.has_sales) == (0, 0, 0, False)


def test_status_counts_what_has_been_entered(db, add_dish, add_ingredient, add_price):
    # Two dishes on the menu: one with a recipe (flour, own invoice price;
    # basil, benchmark only), one without. One dish that came off the menu
    # doesn't count. Sales exist.
    flour = add_ingredient("00 flour", UnitType.GRAM, 0.0013)
    basil = add_ingredient("Basil", UnitType.GRAM, 0.025)
    add_price(flour, 0.00125, PriceSource.INVOICE, date(2026, 6, 3))
    add_dish("Margherita", 11.00, DishType.MAIN, recipe=[(flour, 150), (basil, 4)], units_sold=40)
    add_dish("New special", 15.00, DishType.MAIN)
    add_dish("Old special", 12.00, None, recipe=[(flour, 150)], on_menu_until=date(2026, 7, 31))

    status = setup_status(db, today=TODAY)

    assert status.dishes == 2
    assert status.dishes_with_recipe == 1
    assert status.dishes_with_category == 2
    assert status.ingredients_in_use == 2
    assert status.ingredients_with_own_price == 1
    assert status.has_sales is True


def test_reset_refuses_without_confirmation():
    with pytest.raises(HTTPException) as error:
        reset(ResetIn(mode="fresh", confirm="yes please"))
    assert error.value.status_code == 422
