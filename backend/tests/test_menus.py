"""
Tests for menu import (menus.py): comparing a new menu with the stored dishes,
and applying what the owner confirmed, all dated from the menu's start date.

Claude isn't involved: each test starts from a MenuDraft, i.e. what Claude
would have read off the menu.
"""

from datetime import date

import pytest

from costing import menu_price_on
from menus import ImportProblem, apply_menu, review_menu
from models import Dish, DishIngredient, DishType, Import, MenuIgnoredItem, TillItemAlias
from recipe_ai import build_recipe_prompt
from schemas import MenuApplyIn, MenuApplyItem, MenuDraft, MenuItemDraft

START = date(2026, 10, 1)


@pytest.fixture
def menu(db, add_dish, cost_item):
    dishes = {
        "margherita": add_dish("Margherita", 11.00, DishType.MAIN, recipe=[(cost_item, 2)]),
        "diavola": add_dish("Diavola", 13.00, DishType.MAIN, recipe=[(cost_item, 2)]),
        "nduja": add_dish("Nduja & Hot Honey", 14.00, DishType.MAIN, recipe=[(cost_item, 2)]),
        "cannoli": add_dish("Cannoli", 7.00, DishType.DESSERT, recipe=[(cost_item, 1)]),
        # Came off the menu at the end of July
        "marinara": add_dish("Marinara", 9.00, DishType.MAIN, recipe=[(cost_item, 1)], on_menu_until=date(2026, 7, 31)),
    }
    dishes["margherita"].description = "Tomato, fior di latte, basil"
    db.commit()
    return dishes


def item(name, price, **kw):
    return MenuItemDraft(name=name, price=price, **kw)


AUTUMN = MenuDraft(items=[
    item("Margherita", 11.00, description="Tomato, fior di latte, basil"),          # same
    item("Diavola", 13.50, category=DishType.MAIN),                                 # price rise
    item("'Nduja, Hot Honey & Fior di Latte", 14.00, category=DishType.MAIN),       # renamed?
    item("Carbonara Pizza", 14.50, category=DishType.MAIN, description="Guanciale, egg, pecorino"),   # new
    item("Marinara", 9.50, category=DishType.MAIN),                                 # returning
    item("Peroni 330ml", 5.00, kind="other"),                                       # not a dish
])


def by_name(review):
    return {i.name: i for i in review.items}


# --- Review ------------------------------------------------------------------------

def test_each_item_is_sorted_by_what_changed(db, menu):
    review = by_name(review_menu(db, AUTUMN, START))

    assert review["Margherita"].status == "same"
    assert (review["Diavola"].status, review["Diavola"].current_price) == ("price", 13.00)
    assert review["Carbonara Pizza"].status == "new"
    assert (review["Peroni 330ml"].status, review["Peroni 330ml"].action) == ("not_a_dish", "ignore")


def test_a_close_name_is_asked_about_never_merged(db, menu):
    nduja = by_name(review_menu(db, AUTUMN, START))["'Nduja, Hot Honey & Fior di Latte"]

    assert (nduja.status, nduja.action, nduja.dish_id) == ("renamed", None, menu["nduja"].id)


def test_claudes_guess_is_offered_when_names_differ_a_lot(db, menu):
    draft = MenuDraft(items=[item("Spicy Salami Pizza", 13.00, likely_existing="Diavola")])
    review = review_menu(db, draft, START).items[0]

    assert (review.status, review.dish_id) == ("renamed", menu["diavola"].id)


def test_a_dish_that_came_off_is_returning(db, menu):
    marinara = by_name(review_menu(db, AUTUMN, START))["Marinara"]

    assert (marinara.status, marinara.action, marinara.copy_from) == ("returning", "new", menu["marinara"].id)


def test_dishes_missing_from_the_new_menu_are_listed(db, menu):
    # Cannoli isn't on the new menu. Nduja is only a possible rename, so it's listed too
    # (the screen hides it if the owner says "same dish, renamed"). Marinara is already off.
    leaving = {d.name for d in review_menu(db, AUTUMN, START).leaving}

    assert leaving == {"Cannoli", "Nduja & Hot Honey"}


def test_a_changed_description_is_spotted(db, menu):
    draft = MenuDraft(items=[item("Margherita", 11.00, description="Tomato, buffalo mozzarella, basil")])
    assert review_menu(db, draft, START).items[0].description_changed


def test_size_variants_are_separate_dishes(db, menu):
    draft = MenuDraft(items=[item('Margherita 10"', 9.50), item('Margherita 12"', 11.00)])
    review = review_menu(db, draft, START).items

    assert [i.status for i in review] == ["renamed", "renamed"]   # both asked about, not merged


# --- Apply -------------------------------------------------------------------------

def confirmed(menu, **changes):
    """The autumn menu as the owner confirms it: Nduja renamed, Cannoli off."""
    items = [
        MenuApplyItem(name="Margherita", price=11.00, action="match", dish_id=menu["margherita"].id,
                      description="Tomato, fior di latte, basil"),
        MenuApplyItem(name="Diavola", price=13.50, action="match", dish_id=menu["diavola"].id),
        MenuApplyItem(name="'Nduja, Hot Honey & Fior di Latte", price=14.00, action="match", dish_id=menu["nduja"].id),
        MenuApplyItem(name="Carbonara Pizza", price=14.50, category=DishType.MAIN, action="new",
                      description="Guanciale, egg, pecorino"),
        MenuApplyItem(name="Marinara", price=9.50, category=DishType.MAIN, action="new", copy_from=menu["marinara"].id),
        MenuApplyItem(name="Peroni 330ml", price=5.00, action="ignore"),
    ]
    return MenuApplyIn(start_date=START, items=changes.get("items", items), take_off=changes.get("take_off", [menu["cannoli"].id]))


def test_a_price_change_is_dated_from_the_start(db, menu):
    apply_menu(db, confirmed(menu))

    assert menu_price_on(db, menu["diavola"].id, date(2026, 9, 30)) == 13.00   # old price kept
    assert menu_price_on(db, menu["diavola"].id, START) == 13.50


def test_a_new_dish_starts_on_the_start_date(db, menu):
    record = apply_menu(db, confirmed(menu))
    carbonara = db.query(Dish).filter(Dish.name == "Carbonara Pizza").one()

    assert (carbonara.on_menu_from, carbonara.import_id, carbonara.description) == (START, record.id, "Guanciale, egg, pecorino")
    assert menu_price_on(db, carbonara.id, START) == 14.50


def test_a_rename_keeps_the_dish_and_its_history(db, menu):
    apply_menu(db, confirmed(menu))
    nduja = db.get(Dish, menu["nduja"].id)

    assert nduja.name == "'Nduja, Hot Honey & Fior di Latte"
    assert db.query(DishIngredient).filter(DishIngredient.dish_id == nduja.id).count() == 1


def test_a_dish_taken_off_ends_the_day_before_and_isnt_deleted(db, menu):
    apply_menu(db, confirmed(menu))

    assert db.get(Dish, menu["cannoli"].id).on_menu_until == date(2026, 9, 30)


def test_a_returning_dish_is_a_new_record_with_the_old_recipe(db, menu, cost_item):
    db.add(TillItemAlias(item="marinara", dish_id=menu["marinara"].id))
    db.commit()
    apply_menu(db, confirmed(menu))

    old, new = db.query(Dish).filter(Dish.name == "Marinara").order_by(Dish.id).all()
    assert (old.on_menu_until, new.on_menu_from) == (date(2026, 7, 31), START)   # the gap stays a gap
    assert [(r.ingredient_id, r.quantity) for r in db.query(DishIngredient).filter(DishIngredient.dish_id == new.id)] == [(cost_item.id, 1)]
    assert db.query(TillItemAlias).one().dish_id == new.id   # till sales now go to the new record


def test_a_changed_description_flags_the_recipe_until_its_saved(db, menu):
    items = [MenuApplyItem(name="Margherita", price=11.00, action="match", dish_id=menu["margherita"].id,
                           description="Tomato, buffalo mozzarella, basil")]
    apply_menu(db, confirmed(menu, items=items, take_off=[]))

    assert db.get(Dish, menu["margherita"].id).recipe_check


def test_ignored_items_are_remembered(db, menu):
    apply_menu(db, confirmed(menu))

    peroni = review_menu(db, MenuDraft(items=[item("Peroni 330ml", 5.00)]), START).items[0]   # Claude now says "dish"
    assert (peroni.action, peroni.remembered) == ("ignore", True)
    assert db.query(MenuIgnoredItem).count() == 1


@pytest.mark.parametrize("problem", [
    "no price", "undecided rename", "matched twice", "name clash", "take off a dish on the menu", "nothing to change", "same file",
])
def test_apply_refuses(db, menu, problem):
    m = menu
    items = {
        "no price": [MenuApplyItem(name="Carbonara Pizza", action="new")],
        "undecided rename": [MenuApplyItem(name="'Nduja, Hot Honey", price=14.00, action="match")],
        "matched twice": [MenuApplyItem(name="Diavola", price=13.50, action="match", dish_id=m["diavola"].id),
                          MenuApplyItem(name="Diavola 2", price=13.50, action="match", dish_id=m["diavola"].id)],
        "name clash": [MenuApplyItem(name="Diavola", price=13.00, action="new")],   # Diavola stays on
        "take off a dish on the menu": [MenuApplyItem(name="Diavola", price=13.50, action="match", dish_id=m["diavola"].id)],
        "nothing to change": [MenuApplyItem(name="Margherita", price=11.00, action="match", dish_id=m["margherita"].id,
                                            description="Tomato, fior di latte, basil")],
        "same file": None,
    }[problem]
    take_off = [m["diavola"].id] if problem == "take off a dish on the menu" else []
    if problem == "same file":
        apply_menu(db, MenuApplyIn(start_date=START, file_hash="h", items=confirmed(m).items, take_off=[]))
        data = MenuApplyIn(start_date=START, file_hash="h", items=confirmed(m).items)
    else:
        data = MenuApplyIn(start_date=START, items=items, take_off=take_off)

    with pytest.raises(ImportProblem):
        apply_menu(db, data)
    assert db.query(Import).count() == (1 if problem == "same file" else 0)


# --- Recipe prompt (decision 3) ---------------------------------------------------------

def test_the_recipe_prompt_includes_the_menu_description():
    prompt = build_recipe_prompt("Carbonara Pizza", DishType.MAIN, ["guanciale"], "Guanciale, egg, pecorino")
    assert "Menu description: Guanciale, egg, pecorino" in prompt
    assert "Menu description" not in build_recipe_prompt("Margherita", DishType.MAIN, ["basil"])
