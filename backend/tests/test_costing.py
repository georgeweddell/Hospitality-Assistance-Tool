"""
Tests for the costing engine (costing.cost_dish).

Each test uses numbers small enough to check by hand.
The working is written in the comments.
"""

import pytest
from fastapi import HTTPException

from costing import cost_dish
from models import DishType, UnitType


def test_plate_cost_and_margin_by_weight(db, add_ingredient, add_dish):
    # 200 g flour at £0.002/g      = £0.40
    # 100 g mozzarella at £0.01/g  = £1.00
    # Plate cost                   = £1.40
    # Margin = £10.00 - £1.40      = £8.60
    # Margin % = 8.60 / 10.00      = 86.0%
    flour = add_ingredient("00 flour", UnitType.GRAM, 0.002)
    mozzarella = add_ingredient("Mozzarella", UnitType.GRAM, 0.01)
    dish = add_dish("Margherita", 10.00, DishType.MAIN,
                    recipe=[(flour, 200), (mozzarella, 100)])

    assert cost_dish(db, dish.id) == (1.40, 8.60, 86.0)


def test_countable_ingredient_priced_each(db, add_ingredient, add_dish):
    # 2 eggs at £0.25 each   = £0.50
    # Margin = £5.00 - £0.50 = £4.50
    # Margin % = 4.50 / 5.00 = 90.0%
    egg = add_ingredient("Egg", UnitType.EACH, 0.25)
    dish = add_dish("Fried eggs", 5.00, DishType.STARTER, recipe=[(egg, 2)])

    assert cost_dish(db, dish.id) == (0.50, 4.50, 90.0)


def test_margin_percent_is_of_menu_price_not_cost(db, add_ingredient, add_dish):
    # Plate cost £2.00, menu price £8.00, margin £6.00.
    # Margin %  = 6.00 / 8.00 = 75%   <- what cost_dish should return
    # Markup %  = 6.00 / 2.00 = 300%  <- the easy mistake
    item = add_ingredient("Item", UnitType.EACH, 1.00)
    dish = add_dish("Test dish", 8.00, DishType.MAIN, recipe=[(item, 2)])

    plate_cost, margin, margin_percent = cost_dish(db, dish.id)
    assert margin_percent == 75.0


def test_results_are_rounded_to_two_decimal_places(db, add_ingredient, add_dish):
    # 3 g at £0.333/g         = £0.999   -> £1.00
    # Margin = £7.00 - £0.999 = £6.001   -> £6.00
    # Margin % = 6.001 / 7.00 = 85.7286% -> 85.73%
    # Margin is worked out from the unrounded plate cost, then rounded.
    saffron = add_ingredient("Saffron", UnitType.GRAM, 0.333)
    dish = add_dish("Risotto", 7.00, DishType.MAIN, recipe=[(saffron, 3)])

    assert cost_dish(db, dish.id) == (1.00, 6.00, 85.73)


def test_dish_with_no_recipe_costs_nothing(db, add_dish):
    # No ingredients -> plate cost £0, so the whole price is margin.
    dish = add_dish("Empty", 6.00, DishType.SIDE)

    assert cost_dish(db, dish.id) == (0, 6.00, 100.0)


def test_unknown_dish_raises_404(db):
    with pytest.raises(HTTPException) as error:
        cost_dish(db, 999)
    assert error.value.status_code == 404
