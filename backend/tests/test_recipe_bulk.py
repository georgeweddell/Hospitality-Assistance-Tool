"""
Tests for the Recipes table: the checks (recipe_checks.py), estimating and
saving a recipe as an unchecked AI estimate, and "Looks right".
Claude is replaced by a fake that returns a fixed draft.
"""

from datetime import date

import pytest
from fastapi import HTTPException

import main
from models import DishIngredient, DishType, RecipeStatus, UnitType
from onboarding import setup_status
from recipe_checks import recipe_checks
from schemas import ConfirmedIngredient, RecipeConfirm, RecipeDraft, RecipeIngredientDraft

G, ML, EACH = UnitType.GRAM, UnitType.ML, UnitType.EACH


# --- The checks (thresholds agreed with George) ------------------------------------------

@pytest.mark.parametrize("lines, food_cost, skipped, expected", [
    ([(200, G, False), (100, G, False)], 25, [], []),                    # a sensible recipe
    ([(200, G, False), (100, G, False)], 41, [], ["food_cost_high"]),    # over 40%
    ([(200, G, False), (100, G, False)], 7, [], ["food_cost_low"]),      # under 8%
    ([(600, G, False), (100, G, False)], 25, [], ["big_line"]),          # 600 g in one line
    ([(13, EACH, False), (100, G, False)], 25, [], ["big_line"]),        # 13 eggs
    ([(200, G, False)], 25, [], ["few_ingredients"]),                    # one ingredient
    ([(200, G, False), (100, ML, False)], 25, ["nduja"], ["left_out"]),  # Claude named one not in the list
    ([(200, G, False), (50, G, True)], 25, [], ["unit"]),                # a line in a different unit
    ([], None, [], []),                                                  # no recipe, no flags
])
def test_checks(lines, food_cost, skipped, expected):
    assert recipe_checks(lines, food_cost, skipped) == expected


# --- Estimate and save --------------------------------------------------------------------

@pytest.fixture
def pizza(db, add_ingredient, add_dish):
    # 00 flour £0.002/g, mozzarella £0.01/g, egg £0.30 each. Margherita £10.00, no recipe yet.
    flour = add_ingredient("00 flour", G, 0.002)
    mozzarella = add_ingredient("mozzarella", G, 0.01)
    egg = add_ingredient("egg", EACH, 0.30)
    dish = add_dish("Margherita", 10.00, DishType.MAIN)
    return {"dish": dish, "flour": flour, "mozzarella": mozzarella, "egg": egg}


@pytest.fixture
def fake_claude(monkeypatch):
    def draft(*lines):
        monkeypatch.setattr(main, "estimate_recipe", lambda db, name, category, description=None: RecipeDraft(
            dish_name=name, ingredients=[RecipeIngredientDraft(name=n, quantity=q, unit=u) for n, q, u in lines]))
    return draft


def test_an_estimate_is_saved_unchecked(db, pizza, fake_claude):
    # 150 g + 50 g flour (one line, 200 g) = £0.40; 100 g mozzarella = £1.00; plate cost £1.40.
    # "nduja" isn't in the list, so it's left out and listed. Food cost 1.40 / 10.00 = 14%.
    fake_claude(("00 flour", 150, G), ("mozzarella", 100, G), ("00 flour", 50, G), ("nduja", 30, G))

    row = main.estimate_and_save(pizza["dish"].id, db)

    assert (row.status, row.lines, row.plate_cost, row.food_cost_percent) == ("ai_unchecked", 2, 1.40, 14.0)
    assert row.checks == ["left_out"]   # 14% is fine for a pizza (the floor is 8%)
    assert setup_status(db, today=date(2026, 9, 24)).unchecked_recipes == 1


def test_a_line_in_the_wrong_unit_is_kept_and_flagged(db, pizza, fake_claude):
    # Claude gives egg in grams; egg is counted each. 50 is kept as given (50 eggs!) and flagged.
    fake_claude(("00 flour", 200, G), ("egg", 50, G))

    row = main.estimate_and_save(pizza["dish"].id, db)
    egg = db.query(DishIngredient).filter(DishIngredient.ingredient_id == pizza["egg"].id).one()

    assert (egg.quantity, egg.unit_check) == (50, True)
    assert {"unit", "big_line", "food_cost_high"} <= set(row.checks)


def test_nothing_is_saved_when_no_ingredient_matches(db, pizza, fake_claude):
    fake_claude(("unicorn dust", 5, G))

    with pytest.raises(HTTPException) as e:
        main.estimate_and_save(pizza["dish"].id, db)
    assert e.value.status_code == 422
    assert db.query(DishIngredient).count() == 0


# --- Checking --------------------------------------------------------------------------

def test_looks_right_marks_it_checked_and_clears_unit_flags(db, pizza, fake_claude):
    fake_claude(("00 flour", 200, G), ("egg", 50, G))
    main.estimate_and_save(pizza["dish"].id, db)

    row = main.mark_recipe_checked(pizza["dish"].id, db)

    assert (row.status, "unit" in row.checks) == ("checked", False)
    assert db.get(type(pizza["dish"]), pizza["dish"].id).recipe_status == RecipeStatus.CHECKED


def test_saving_in_the_editor_marks_it_checked(db, pizza, fake_claude):
    fake_claude(("00 flour", 200, G), ("mozzarella", 100, G))
    main.estimate_and_save(pizza["dish"].id, db)

    main.save_recipe(pizza["dish"].id, RecipeConfirm(ingredients=[
        ConfirmedIngredient(ingredient_id=pizza["flour"].id, quantity=250)]), db)

    assert pizza["dish"].recipe_status == RecipeStatus.CHECKED


def test_looks_right_needs_a_recipe(db, pizza):
    with pytest.raises(HTTPException) as e:
        main.mark_recipe_checked(pizza["dish"].id, db)
    assert e.value.status_code == 422


def test_the_table_lists_dishes_on_the_menu(db, pizza, add_dish, cost_item):
    add_dish("Diavola", 13.00, DishType.MAIN, recipe=[(cost_item, 2)])
    add_dish("Marinara", 9.00, DishType.MAIN, on_menu_until=date(2020, 1, 1))   # long gone

    rows = {r.name: r for r in main.list_recipes(db)}

    assert set(rows) == {"Margherita", "Diavola"}
    assert (rows["Margherita"].status, rows["Margherita"].plate_cost) == ("none", None)
    # Diavola: plate cost £2.00 / £13.00 = 15.4%; a recipe with no status yet counts as checked
    assert (rows["Diavola"].status, rows["Diavola"].food_cost_percent) == ("checked", 15.4)
