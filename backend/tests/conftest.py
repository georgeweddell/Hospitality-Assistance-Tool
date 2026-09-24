"""
Shared setup for all tests. pytest loads this file automatically.

Every test gets a brand-new, empty database that lives only in memory,
so tests never touch menu.db and can't affect each other.
"""

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base
from models import Dish, DishIngredient, Ingredient, IngredientPrice, MenuPrice, MenuPriceSource, PriceSource, SalesRecord, UnitType


@pytest.fixture
def engine():
    # StaticPool keeps one connection open, so the in-memory database
    # survives for the whole test instead of vanishing between queries.
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def db(engine):
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def add_price(db):
    """add_price(flour, 0.002, PriceSource.INVOICE, date(2026, 3, 1)) -> saved IngredientPrice"""
    def _add(ingredient, price_per_unit, source, effective_date):
        price = IngredientPrice(ingredient_id=ingredient.id, price_per_unit=price_per_unit,
                                source=source, effective_date=effective_date)
        db.add(price)
        db.commit()
        return price
    return _add


@pytest.fixture
def add_ingredient(db, add_price):
    """
    add_ingredient("Flour", UnitType.GRAM, 0.002) -> saved Ingredient
    with one benchmark price, dated in the past so it's always in effect.
    """
    def _add(name, unit, price_per_unit):
        ingredient = Ingredient(name=name, unit=unit)
        db.add(ingredient)
        db.commit()
        add_price(ingredient, price_per_unit, PriceSource.BENCHMARK, date(2026, 1, 1))
        return ingredient
    return _add


@pytest.fixture
def add_dish(db):
    """
    add_dish("Margherita", 10.00, DishType.MAIN,
             recipe=[(flour, 200), (mozzarella, 100)],
             units_sold=40) -> saved Dish

    recipe is a list of (Ingredient, quantity in base units).
    units_sold=0 means no sales record is created at all.
    Sales are recorded for 1-7 Sep 2026 (inside SEPTEMBER below). Dishes are on
    the menu from 1 Jan 2026 unless on_menu_from / on_menu_until say otherwise,
    and menu_price is their price from that date (see add_menu_price for changes).
    """
    def _add(name, menu_price, category, recipe=(), units_sold=0,
             on_menu_from=date(2026, 1, 1), on_menu_until=None):
        dish = Dish(name=name, category=category,
                    on_menu_from=on_menu_from, on_menu_until=on_menu_until)
        db.add(dish)
        db.commit()
        db.add(MenuPrice(dish_id=dish.id, price=menu_price, source=MenuPriceSource.MANUAL,
                         effective_date=on_menu_from))
        for ingredient, quantity in recipe:
            db.add(DishIngredient(dish_id=dish.id, ingredient_id=ingredient.id, quantity=quantity))
        if units_sold:
            db.add(SalesRecord(dish_id=dish.id, units_sold=units_sold,
                               period_start=date(2026, 9, 1), period_end=date(2026, 9, 7)))
        db.commit()
        return dish
    return _add


@pytest.fixture
def add_menu_price(db):
    """add_menu_price(dish, 11.50, date(2026, 9, 15)) -> a price change from that day"""
    def _add(dish, price, effective_date):
        row = MenuPrice(dish_id=dish.id, price=price, source=MenuPriceSource.MANUAL, effective_date=effective_date)
        db.add(row)
        db.commit()
        return row
    return _add


@pytest.fixture
def add_sales(db):
    """add_sales(dish, 30, date(2026, 9, 10)) -> sales for one day (or to period_end)"""
    def _add(dish, units_sold, period_start, period_end=None):
        record = SalesRecord(dish_id=dish.id, units_sold=units_sold,
                             period_start=period_start, period_end=period_end or period_start)
        db.add(record)
        db.commit()
        return record
    return _add


@pytest.fixture
def cost_item(add_ingredient):
    """
    A £1.00-each ingredient. A recipe of [(cost_item, 2)] gives a plate cost of
    exactly £2.00, which makes menu-engineering margins easy to set by hand.
    """
    return add_ingredient("Test cost unit", UnitType.EACH, 1.00)


# The analysis period the tests use: all of September 2026.
SEPTEMBER = (date(2026, 9, 1), date(2026, 9, 30))
