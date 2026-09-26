"""
Tests for the business checks (suggestions.py), on a small hand-worked menu.
The rules of thumb are passed in, so the tests don't depend on the CSV.

Plate costs from the £1.00-each cost item:
    Margherita  main     £10.00, cost £2.00, 30 plates on Monday 7 Sep
    Diavola     main     £12.00, cost £2.00, 10 plates on Saturday 12 Sep
    Funghi      main     £13.00, cost £2.00,  5 plates on Saturday 12 Sep
    Tiramisu    dessert   £6.00, cost £1.00,  9 plates on Monday 7 Sep
Mains sold 45, desserts 9.
Food cost = 30x2 + 10x2 + 5x2 + 9x1 = £99
Sales = 300 + 120 + 65 + 54 = £539, ex-VAT £539 / 1.2 = £449.17
Food cost ex-VAT = 99 / 449.17 = 22.0%
"""

from datetime import date

import pytest

from models import BusinessProfile, DishType, PriceSource
from suggestions import Checks, load_rules

SEPTEMBER = (date(2026, 9, 1), date(2026, 9, 30))
TODAY = date(2026, 9, 25)
MONDAY, SATURDAY = date(2026, 9, 7), date(2026, 9, 12)


@pytest.fixture
def menu(add_dish, cost_item, add_sales):
    dishes = {
        'margherita': add_dish('Margherita', 10.00, DishType.MAIN, recipe=[(cost_item, 2)]),
        'diavola': add_dish('Diavola', 12.00, DishType.MAIN, recipe=[(cost_item, 2)]),
        'funghi': add_dish('Funghi', 13.00, DishType.MAIN, recipe=[(cost_item, 2)]),
        'tiramisu': add_dish('Tiramisu', 6.00, DishType.DESSERT, recipe=[(cost_item, 1)]),
    }
    add_sales(dishes['margherita'], 30, MONDAY)
    add_sales(dishes['diavola'], 10, SATURDAY)
    add_sales(dishes['funghi'], 5, SATURDAY)
    add_sales(dishes['tiramisu'], 9, MONDAY)
    return dishes


def checks(db, **rules):
    """Checks with just these rules: rule=(low, high), for every restaurant type."""
    return {c.key: c for c in Checks(db, *SEPTEMBER, today=TODAY,
                                     rules={(k, 'all'): (lo, hi, '') for k, (lo, hi) in rules.items()}).all()}


def figure(check, label):
    return next(f.value for f in check.figures if f.label == label)


def test_food_cost_is_worked_out_ex_vat(db, menu):
    c = checks(db, food_cost_percent=(20, 25))['food_cost']
    assert figure(c, 'Food cost, ex-VAT') == pytest.approx(22.04, abs=0.01)
    assert not c.fires                                        # inside 20-25%


def test_food_cost_above_the_band_names_the_dearest_plates(db, menu):
    c = checks(db, food_cost_percent=(15, 20))['food_cost']
    assert c.fires and c.action == 'Reprice or rework the dearest plates'
    # Ex-VAT food cost per dish: Margherita £2 / (£10 / 1.2) = 24.0%, Tiramisu £1 / £5 = 20.0%,
    # Diavola £2 / £10 = 20.0%, Funghi £2 / £10.83 = 18.5%: Margherita is the dearest plate
    assert [f.label for f in c.figures[1:]][0] == 'Margherita: food cost, ex-VAT'


def test_food_cost_below_the_band_asks_whether_recipes_are_complete(db, menu):
    c = checks(db, food_cost_percent=(25, 32))['food_cost']
    assert c.fires and c.action == 'Check recipes are complete and portions are right'


def test_desserts_per_main(db, menu):
    c = checks(db, desserts_per_main=(0.30, None))['desserts_per_main']
    assert figure(c, 'Desserts per main') == pytest.approx(0.2)    # 9 / 45
    assert c.fires


def test_midweek_share(db, menu):
    # Monday: 300 + 54 = £354. Saturday: 120 + 65 = £185. Midweek is 191% of the weekend: fine.
    c = checks(db, midweek_share=(0.70, None))['midweek']
    assert figure(c, 'Midweek as a share of the weekend') == pytest.approx(191.35, abs=0.01)
    assert not c.fires


def test_the_cheapest_main_is_the_best_seller(db, menu):
    c = checks(db)['cheapest_top']
    assert c.fires
    assert 'Margherita' in c.action


def test_one_ingredient_is_the_whole_food_cost(db, menu):
    c = checks(db, ingredient_share=(None, 0.25))['one_ingredient']
    assert figure(c, 'Test cost unit: share of food cost') == 100.0
    assert figure(c, 'Test cost unit: cost over the period') == 99.0
    assert c.fires


def test_costs_all_on_benchmarks(db, menu):
    c = checks(db, own_price_share=(50, None))['cost_basis']
    assert figure(c, 'Recipe cost on your own prices') == 0.0
    assert c.fires


def test_a_rise_not_passed_on(db, menu, cost_item, add_price, add_menu_price):
    add_price(cost_item, 1.50, PriceSource.INVOICE, date(2026, 9, 10))     # +50%
    c = checks(db)['unmatched_rise']
    assert c.fires and figure(c, 'Test cost unit: dishes not repriced since') == 4
    # Repricing three of them after the rise leaves one behind
    for key in ('margherita', 'diavola', 'funghi'):
        add_menu_price(menu[key], 14.00, date(2026, 9, 15))
    c = checks(db)['unmatched_rise']
    assert figure(c, 'Test cost unit: dishes not repriced since') == 1


def test_the_restaurant_types_own_rule_beats_the_general_one(db, menu):
    db.add(BusinessProfile(restaurant_type='pizzeria'))
    db.commit()
    rules = {('food_cost_percent', 'all'): (25, 32, ''), ('food_cost_percent', 'pizzeria'): (20, 28, '')}
    c = next(c for c in Checks(db, *SEPTEMBER, today=TODAY, rules=rules).all() if c.key == 'food_cost')
    assert not c.fires                                  # 22% is inside the pizzeria band
    assert c.rule_of_thumb == '20–28% for a pizzeria'


def test_the_rules_file_loads():
    rules = load_rules()
    assert rules[('food_cost_percent', 'pizzeria')][:2] == (20.0, 28.0)
    assert rules[('midweek_share', 'all')][0] == 0.70


def test_a_check_without_a_rule_of_thumb_does_not_run(db, menu):
    found = checks(db)   # no rules at all: only the checks that need none
    assert set(found) == {'cheapest_top', 'unmatched_rise'}


def test_no_sales_means_no_checks(db):
    assert Checks(db, *SEPTEMBER, today=TODAY, rules={}).all() == []


def test_the_restaurant_type_setting(db):
    import main
    import schemas
    assert main.get_business(db)['restaurant_type'] == 'other'      # nothing set yet
    main.put_business(schemas.BusinessIn(restaurant_type='gastropub'), db)
    assert main.get_business(db)['restaurant_type'] == 'gastropub'
    with pytest.raises(ValueError):
        schemas.BusinessIn(restaurant_type='steakhouse')             # not a type the rules know
