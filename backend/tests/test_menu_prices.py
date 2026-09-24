"""
Tests for menu price history: a dish's price changes are kept as dated rows,
and analysis over a period uses the price actually charged on each day,
weighted by that day's units (costing.average_menu_price).
"""

from datetime import date

import pytest
from fastapi import HTTPException

from costing import average_menu_price, menu_price_on
from main import create_dish, delete_menu_price, get_dish_detail, update_dish
from menu_engineering import build_action_list, classify_all_dishes
from models import DishType, MenuPrice
from schemas import DishCreate, DishUpdate
from conftest import SEPTEMBER


@pytest.fixture
def pizza(add_dish, cost_item, add_menu_price):
    # £10.00 from 1 Jan, £12.00 from 15 Sep. Plate cost £2.00.
    dish = add_dish("Margherita", 10.00, DishType.MAIN, recipe=[(cost_item, 2)])
    add_menu_price(dish, 12.00, date(2026, 9, 15))
    return dish


# --- Which price is in effect ------------------------------------------------------

def test_the_price_changes_on_its_date(db, pizza):
    assert menu_price_on(db, pizza.id, date(2026, 9, 14)) == 10.00
    assert menu_price_on(db, pizza.id, date(2026, 9, 15)) == 12.00


def test_before_the_first_price_the_first_price_is_used(db, pizza):
    # e.g. the "on the menu from" date was later edited to earlier
    assert menu_price_on(db, pizza.id, date(2025, 6, 1)) == 10.00


def test_a_future_price_isnt_used_yet(db, pizza, add_menu_price):
    add_menu_price(pizza, 13.00, date(2099, 1, 1))
    assert menu_price_on(db, pizza.id, date(2026, 10, 1)) == 12.00


# --- The price analysis uses over a period -------------------------------------------

def test_units_are_weighted_by_the_price_on_each_day(db, pizza, add_sales):
    # 30 sold on 10 Sep at £10.00 = £300
    # 10 sold on 20 Sep at £12.00 = £120
    # (300 + 120) / 40            = £10.50
    add_sales(pizza, 30, date(2026, 9, 10))
    add_sales(pizza, 10, date(2026, 9, 20))

    assert average_menu_price(db, pizza.id, *SEPTEMBER) == 10.50


def test_one_price_all_period_is_that_price_exactly(db, pizza, add_sales):
    add_sales(pizza, 7, date(2026, 9, 1))
    add_sales(pizza, 3, date(2026, 9, 2))

    assert average_menu_price(db, pizza.id, *SEPTEMBER) == 10.00


def test_a_total_spanning_a_change_is_split_evenly_across_its_days(db, pizza, add_sales):
    # 20 sold over 10-19 Sep (10 days, 2 a day):
    #   10-14 Sep: 5 days x 2 = 10 at £10.00 = £100
    #   15-19 Sep: 5 days x 2 = 10 at £12.00 = £120
    # (100 + 120) / 20                       = £11.00
    add_sales(pizza, 20, date(2026, 9, 10), date(2026, 9, 19))

    assert average_menu_price(db, pizza.id, *SEPTEMBER) == pytest.approx(11.00)


def test_no_sales_uses_the_price_on_the_last_day(db, pizza):
    assert average_menu_price(db, pizza.id, *SEPTEMBER) == 12.00
    assert average_menu_price(db, pizza.id, date(2026, 9, 1), date(2026, 9, 10)) == 10.00


def test_classification_margin_uses_the_weighted_price(db, pizza, add_sales):
    # Price £10.50 (as above) - plate cost £2.00 = £8.50 margin
    # Margin % = 8.50 / 10.50                    = 80.95%
    # Takings = £10.50 x 40 = £420, what was actually charged.
    add_sales(pizza, 30, date(2026, 9, 10))
    add_sales(pizza, 10, date(2026, 9, 20))

    [c] = classify_all_dishes(db, *SEPTEMBER)
    assert (c.menu_price, c.margin_pounds, c.margin_percent) == (10.50, 8.50, 80.95)
    assert c.menu_price * c.units_sold == 420


def test_a_dog_impact_uses_the_price_actually_charged(db, add_dish, cost_item, add_menu_price, add_sales):
    # Star: £10 all month, 90 sold, margin £8.
    # Dog: £9 until 15 Sep then £7, plate cost £2.
    #   5 sold on 10 Sep at £9, 5 on 20 Sep at £7 -> price £8, margin £6.
    # Weighted average margin = (8 x 90 + 6 x 10) / 100 = £7.80
    # Dog impact = (7.80 - 6.00) x 10 = £18.00
    # (At today's £7 alone it would have been (7.70 - 5.00) x 10 = £27.00, overstated.)
    star = add_dish("Star", 10.00, DishType.MAIN, recipe=[(cost_item, 2)])
    dog = add_dish("Dog", 9.00, DishType.MAIN, recipe=[(cost_item, 2)])
    add_menu_price(dog, 7.00, date(2026, 9, 15))
    add_sales(star, 90, date(2026, 9, 10))
    add_sales(dog, 5, date(2026, 9, 10))
    add_sales(dog, 5, date(2026, 9, 20))

    [action] = build_action_list(db, *SEPTEMBER)
    assert (action.dish_name, action.impact_pounds) == ("Dog", 18.00)


# --- Routes -----------------------------------------------------------------------

def test_a_new_dish_starts_priced_from_its_first_day(db):
    out = create_dish(DishCreate(name="Calzone", menu_price=13.00, category=DishType.MAIN,
                                 on_menu_from=date(2026, 9, 1)), db)

    [price] = db.query(MenuPrice).filter(MenuPrice.dish_id == out.id).all()
    assert (price.price, price.effective_date) == (13.00, date(2026, 9, 1))


def test_changing_the_price_keeps_the_old_one(db, pizza):
    update_dish(pizza.id, DishUpdate(name="Margherita", menu_price=12.50, category=DishType.MAIN,
                                     on_menu_from=date(2026, 1, 1), price_from=date(2026, 10, 1)), db)

    assert menu_price_on(db, pizza.id, date(2026, 9, 30)) == 12.00
    assert menu_price_on(db, pizza.id, date(2026, 10, 1)) == 12.50
    assert db.query(MenuPrice).filter(MenuPrice.dish_id == pizza.id).count() == 3


def test_saving_without_changing_the_price_adds_nothing(db, pizza):
    update_dish(pizza.id, DishUpdate(name="Margherita DOP", menu_price=12.00, category=DishType.MAIN,
                                     on_menu_from=date(2026, 1, 1), price_from=date(2026, 10, 1)), db)

    assert db.query(MenuPrice).filter(MenuPrice.dish_id == pizza.id).count() == 2


def test_the_dish_page_lists_prices_newest_first(db, pizza):
    detail = get_dish_detail(pizza.id, *SEPTEMBER, db=db)

    assert [p.price for p in detail.prices] == [12.00, 10.00]


def test_a_mistaken_price_can_be_removed_but_not_the_last_one(db, pizza):
    newest, first = db.query(MenuPrice).filter(MenuPrice.dish_id == pizza.id).order_by(MenuPrice.effective_date.desc()).all()
    delete_menu_price(pizza.id, newest.id, db)

    assert menu_price_on(db, pizza.id, date(2026, 9, 30)) == 10.00
    with pytest.raises(HTTPException) as e:
        delete_menu_price(pizza.id, first.id, db)
    assert e.value.status_code == 422
