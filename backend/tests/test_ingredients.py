"""
Tests for entering prices the way invoices show them, and the ingredient routes.

Prices are stored per base unit (g / ml / each). units.price_per_base_unit
converts a pack price at entry, so costing never has to.
"""

from datetime import date

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from costing import best_price
from main import add_ingredient_price, create_ingredient, list_ingredients
from models import DishType, PriceSource, UnitType
from schemas import IngredientCreate, IngredientPriceCreate
from units import price_per_base_unit


# --- Converting pack prices -------------------------------------------------------

def test_kilo_pack_to_price_per_gram():
    # £93.60 for 12 x 1 kg = £93.60 / 12,000 g = £0.0078/g (£7.80/kg)
    assert price_per_base_unit(93.60, 12, "kg", UnitType.GRAM) == pytest.approx(0.0078)


def test_litre_pack_to_price_per_ml():
    # £27.00 for a 3 l tin = £27.00 / 3,000 ml = £0.009/ml (£9.00/l)
    assert price_per_base_unit(27.00, 3, "l", UnitType.ML) == pytest.approx(0.009)


def test_count_pack_to_price_each():
    # £54.00 for a tray of 180 eggs = £0.30 each
    assert price_per_base_unit(54.00, 180, "each", UnitType.EACH) == pytest.approx(0.30)


def test_unit_that_measures_something_else_is_rejected():
    # Litres can't price something measured by weight.
    with pytest.raises(ValueError):
        price_per_base_unit(10.00, 1, "l", UnitType.GRAM)


def test_price_given_both_ways_or_neither_is_rejected():
    with pytest.raises(ValidationError):
        IngredientPriceCreate(price_per_unit=0.01, pack_price=10, pack_quantity=1, pack_unit="kg")
    with pytest.raises(ValidationError):
        IngredientPriceCreate()
    with pytest.raises(ValidationError):
        IngredientPriceCreate(pack_price=10, pack_unit="kg")   # quantity missing


# --- Routes --------------------------------------------------------------------------

def test_adding_a_pack_price_becomes_the_price_costing_uses(db, add_ingredient):
    mozzarella = add_ingredient("Mozzarella", UnitType.GRAM, 0.0075)   # benchmark £7.50/kg

    add_ingredient_price(mozzarella.id, IngredientPriceCreate(
        pack_price=93.60, pack_quantity=12, pack_unit="kg",
        source=PriceSource.INVOICE, effective_date=date(2026, 9, 1)), db)

    price = best_price(db, mozzarella.id)
    assert price.source == PriceSource.INVOICE
    assert price.price_per_unit == pytest.approx(0.0078)


def test_wrong_pack_unit_is_rejected_by_the_route(db, add_ingredient):
    mozzarella = add_ingredient("Mozzarella", UnitType.GRAM, 0.0075)

    with pytest.raises(HTTPException) as error:
        add_ingredient_price(mozzarella.id, IngredientPriceCreate(
            pack_price=10, pack_quantity=1, pack_unit="l"), db)
    assert error.value.status_code == 422


def test_create_ingredient_from_pack_price(db):
    created = create_ingredient(IngredientCreate(
        name="Guanciale", unit=UnitType.GRAM, pack_price=24.00, pack_quantity=1.5, pack_unit="kg"), db)

    # £24.00 / 1,500 g = £0.016/g
    assert created.price_per_unit == pytest.approx(0.016)
    assert created.price_source == PriceSource.MANUAL


def test_duplicate_ingredient_name_is_rejected(db, add_ingredient):
    add_ingredient("Mozzarella", UnitType.GRAM, 0.0075)

    with pytest.raises(HTTPException) as error:
        create_ingredient(IngredientCreate(name="mozzarella", unit=UnitType.GRAM, price_per_unit=0.008), db)
    assert error.value.status_code == 422


def test_list_counts_how_many_dishes_use_each_ingredient(db, add_ingredient, add_dish):
    flour = add_ingredient("00 flour", UnitType.GRAM, 0.0013)
    basil = add_ingredient("Basil", UnitType.GRAM, 0.025)
    add_ingredient("Saffron", UnitType.GRAM, 5.0)
    add_dish("Margherita", 11.00, DishType.MAIN, recipe=[(flour, 150), (basil, 4)])
    add_dish("Marinara", 9.00, DishType.MAIN, recipe=[(flour, 150)])

    used_in = {i.name: i.used_in for i in list_ingredients(db)}

    assert used_in == {"00 flour": 2, "Basil": 1, "Saffron": 0}
