"""
Tests for the dish routes the Menu and dish pages use: edit, delete,
detail, and the checks the recipe save route makes before saving.

The route functions are called directly with the in-memory test database.
(Importing main also runs create_all against menu.db, which only creates
tables that are missing; it doesn't change any data.)
"""

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from costing import menu_price_on
from main import delete_dish, get_dish_detail, save_recipe, update_dish
from models import Dish, DishIngredient, DishType, SalesRecord, UnitType
from schemas import ConfirmedIngredient, DishUpdate, RecipeConfirm
from conftest import SEPTEMBER


@pytest.fixture
def pizza(db, add_ingredient, add_dish):
    # 200 g flour at £0.002/g = £0.40, 100 g mozzarella at £0.01/g = £1.00.
    # Plate cost £1.40 on a £10.00 menu price.
    flour = add_ingredient("00 flour", UnitType.GRAM, 0.002)
    mozzarella = add_ingredient("Mozzarella", UnitType.GRAM, 0.01)
    dish = add_dish("Margherita", 10.00, DishType.MAIN,
                    recipe=[(flour, 200), (mozzarella, 100)], units_sold=40)
    return {"dish": dish, "flour": flour, "mozzarella": mozzarella}


def recipe(*lines, skipped=()):
    return RecipeConfirm(
        ingredients=[ConfirmedIngredient(ingredient_id=i, quantity=q) for i, q in lines],
        skipped_ingredients=list(skipped),
    )


# --- Detail ------------------------------------------------------------------

def test_detail_lists_each_line_with_its_cost(db, pizza):
    detail = get_dish_detail(pizza["dish"].id, *SEPTEMBER, db=db)

    assert [(l.name, l.quantity, l.line_cost) for l in detail.lines] == [
        ("00 flour", 200, 0.40),
        ("Mozzarella", 100, 1.00),
    ]
    assert detail.cost.plate_cost == 1.40
    assert detail.units_sold == 40


# --- Edit and delete -----------------------------------------------------------

def test_update_changes_name_price_and_category(db, pizza):
    update_dish(pizza["dish"].id, DishUpdate(name="Margherita DOP", menu_price=12.00,
                                             category=DishType.MAIN), db)

    dish = db.query(Dish).filter(Dish.id == pizza["dish"].id).first()
    assert (dish.name, menu_price_on(db, dish.id)) == ("Margherita DOP", 12.00)


def test_price_must_be_positive_and_name_not_empty():
    with pytest.raises(ValidationError):
        DishUpdate(name="Margherita", menu_price=0)
    with pytest.raises(ValidationError):
        DishUpdate(name="", menu_price=10.00)


def test_delete_removes_dish_recipe_and_sales(db, pizza):
    dish_id = pizza["dish"].id
    delete_dish(dish_id, db)

    assert db.query(Dish).filter(Dish.id == dish_id).count() == 0
    assert db.query(DishIngredient).filter(DishIngredient.dish_id == dish_id).count() == 0
    assert db.query(SalesRecord).filter(SalesRecord.dish_id == dish_id).count() == 0


# --- Saving a recipe -----------------------------------------------------------

def test_save_replaces_recipe_and_returns_new_cost(db, pizza):
    # New recipe: 250 g flour (£0.50) + 120 g mozzarella (£1.20) = £1.70.
    # Margin £8.30, 83.0%.
    result = save_recipe(pizza["dish"].id,
                         recipe((pizza["flour"].id, 250), (pizza["mozzarella"].id, 120),
                                skipped=["basil"]), db)

    assert (result.cost.plate_cost, result.cost.margin_pounds, result.cost.margin_percent) == (1.70, 8.30, 83.0)
    assert db.query(Dish).filter(Dish.id == pizza["dish"].id).first().skipped_ingredients == ["basil"]


def test_save_rejects_unknown_ingredient_and_keeps_old_recipe(db, pizza):
    with pytest.raises(HTTPException) as error:
        save_recipe(pizza["dish"].id, recipe((pizza["flour"].id, 250), (999, 10)), db)

    assert error.value.status_code == 422
    # The check runs before anything is deleted, so the old recipe survives.
    assert get_dish_detail(pizza["dish"].id, *SEPTEMBER, db=db).cost.plate_cost == 1.40


def test_save_rejects_the_same_ingredient_twice(db, pizza):
    with pytest.raises(HTTPException) as error:
        save_recipe(pizza["dish"].id, recipe((pizza["flour"].id, 100), (pizza["flour"].id, 100)), db)

    assert error.value.status_code == 422


def test_quantity_must_be_positive():
    with pytest.raises(ValidationError):
        ConfirmedIngredient(ingredient_id=1, quantity=0)
