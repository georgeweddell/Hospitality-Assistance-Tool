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
from models import Dish, DishIngredient, Ingredient, SalesRecord, UnitType


@pytest.fixture
def db():
    # StaticPool keeps one connection open, so the in-memory database
    # survives for the whole test instead of vanishing between queries.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def add_ingredient(db):
    """add_ingredient("Flour", UnitType.GRAM, 0.002) -> saved Ingredient"""
    def _add(name, unit, price_per_unit):
        ingredient = Ingredient(name=name, unit=unit, price_per_unit=price_per_unit)
        db.add(ingredient)
        db.commit()
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
    """
    def _add(name, menu_price, category, recipe=(), units_sold=0):
        dish = Dish(name=name, menu_price=menu_price, category=category)
        db.add(dish)
        db.commit()
        for ingredient, quantity in recipe:
            db.add(DishIngredient(dish_id=dish.id, ingredient_id=ingredient.id, quantity=quantity))
        if units_sold:
            db.add(SalesRecord(dish_id=dish.id, units_sold=units_sold,
                               period_start=date(2026, 9, 1), period_end=date(2026, 9, 7)))
        db.commit()
        return dish
    return _add


@pytest.fixture
def cost_item(add_ingredient):
    """
    A £1.00-each ingredient. A recipe of [(cost_item, 2)] gives a plate cost of
    exactly £2.00, which makes menu-engineering margins easy to set by hand.
    """
    return add_ingredient("Test cost unit", UnitType.EACH, 1.00)
