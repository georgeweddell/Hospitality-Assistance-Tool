"""
Tests for the report agent's tools (report_tools.py): the facts they record,
worked out by hand on a tiny menu. No Claude calls anywhere.
"""

from datetime import date

import pytest

from models import DishType, PriceSource, UnitType
from report_tools import (Facts, ReportContext, format_value, previous_range, run_tool, tool_definitions)

SEPTEMBER = (date(2026, 9, 1), date(2026, 9, 30))
TODAY = date(2026, 9, 25)


def facts_by_label(ctx):
    return {f.label: f.value for f in ctx.facts.items.values()}


@pytest.fixture
def menu(add_dish, cost_item, add_sales):
    # Plate cost £2.00 each (2 x the £1.00 cost item).
    # Margherita £10 -> margin £8. Diavola £12 -> margin £10.
    margherita = add_dish('Margherita', 10.00, DishType.MAIN, recipe=[(cost_item, 2)])
    diavola = add_dish('Diavola', 12.00, DishType.MAIN, recipe=[(cost_item, 2)])
    # August: 20 Margherita, 10 Diavola. September: 30 Margherita, 10 Diavola.
    add_sales(margherita, 20, date(2026, 8, 3))
    add_sales(diavola, 10, date(2026, 8, 3))
    add_sales(margherita, 30, date(2026, 9, 7))    # a Monday
    add_sales(diavola, 10, date(2026, 9, 12))      # a Saturday
    return {'margherita': margherita, 'diavola': diavola}


def test_the_previous_period_is_the_month_before_or_the_same_number_of_days():
    assert previous_range(*SEPTEMBER) == (date(2026, 8, 1), date(2026, 8, 31))
    # 10-19 Sep is 10 days, so the 10 days before: 31 Aug - 9 Sep
    assert previous_range(date(2026, 9, 10), date(2026, 9, 19)) == (date(2026, 8, 31), date(2026, 9, 9))


def test_facts_are_numbered_in_order_and_formatted_by_code():
    facts = Facts()
    assert facts.add('Contribution', 36036.4, '£') == '[f1] Contribution: £36,036'
    assert facts.add('Margin', 9.814, '£') == '[f2] Margin: £9.81'       # under £100: pence shown
    assert facts.add('GP change', -0.34, 'pts') == '[f3] GP change: -0.3 pts'
    assert list(facts.items) == ['f1', 'f2', 'f3']
    assert format_value(8.2, '£/kg') == '£8.20/kg'
    assert format_value(-168.4, '£') == '-£168'


def test_period_summary_against_the_previous_month(db, menu):
    ctx = ReportContext(db, *SEPTEMBER, today=TODAY)
    run_tool(ctx, 'period_summary', {})
    f = facts_by_label(ctx)

    # September: contribution 30 x £8 + 10 x £10 = £340; sales 30 x £10 + 10 x £12 = £420
    assert f['Contribution (margin x units, all analysed dishes)'] == 340
    assert f['Sales (menu price x units, incl. VAT)'] == 420
    assert f['Gross margin'] == pytest.approx(80.95, abs=0.01)          # 340 / 420
    # August: 20 x £8 + 10 x £10 = £260, so +30.77%; GP 260 / 320 = 81.25%, so -0.30 pts
    assert f['Contribution, previous period'] == 260
    assert f['Contribution change'] == pytest.approx(30.77, abs=0.01)
    assert f['Gross margin change'] == pytest.approx(-0.30, abs=0.01)


def test_dish_detail_finds_a_dish_by_name_whatever_the_case(db, menu):
    ctx = ReportContext(db, *SEPTEMBER, today=TODAY)
    text = run_tool(ctx, 'dish_detail', {'dish': 'margherita'})
    f = facts_by_label(ctx)

    assert text.startswith('Margherita (Main).')
    assert f['Margherita margin per plate'] == 8.00
    assert f['Margherita units sold'] == 30
    assert f['Margherita units sold, previous period'] == 20
    # 30 of the 40 mains sold = 75%
    assert f["Margherita share of its category's units"] == 75.0


def test_an_unknown_dish_comes_back_as_a_message_not_an_error(db, menu):
    ctx = ReportContext(db, *SEPTEMBER, today=TODAY)
    assert run_tool(ctx, 'dish_detail', {'dish': 'Calzone'}) == 'No dish called "Calzone".'
    assert run_tool(ctx, 'dish_detail', {'dish': 'Diavolo'}).startswith('Diavola (Main).')   # one close match
    assert ctx.facts.items  # the close match recorded its facts


def test_a_price_rise_shows_its_effect_on_each_dish_and_the_period(db, menu, cost_item, add_price):
    # The cost item goes from £1.00 to £1.50 each on 10 Sep, from an invoice.
    add_price(cost_item, 1.50, PriceSource.INVOICE, date(2026, 9, 10))
    ctx = ReportContext(db, *SEPTEMBER, today=TODAY)
    run_tool(ctx, 'price_changes', {})
    f = facts_by_label(ctx)

    name = 'Test cost unit'
    assert (f[f'{name} price before'], f[f'{name} price after']) == (1.00, 1.50)
    assert f[f'{name} price change'] == 50.0
    # Each dish uses 2, so +£1.00 per plate
    assert f[f'Margherita plate cost change from {name}'] == 1.00
    # 30 + 10 = 40 plates sold in September x £1.00 = £40 less contribution
    assert f[f'{name}: effect on contribution over the period'] == -40.00


def test_a_price_before_the_period_is_not_a_change(db, menu, cost_item, add_price):
    add_price(cost_item, 1.50, PriceSource.INVOICE, date(2026, 8, 20))
    ctx = ReportContext(db, *SEPTEMBER, today=TODAY)
    assert run_tool(ctx, 'price_changes', {}).startswith('No ingredient price changes')


def test_sales_by_weekday_averages_the_days_that_traded(db, menu):
    ctx = ReportContext(db, *SEPTEMBER, today=TODAY)
    run_tool(ctx, 'sales_pattern', {'by': 'weekday'})
    f = facts_by_label(ctx)
    # Monday 7 Sep: 30 x £10 = £300. Saturday 12 Sep: 10 x £12 = £120.
    assert f['Average Monday sales'] == 300
    assert f['Average Saturday sales'] == 120
    assert 'Average Tuesday sales' not in f       # no trading Tuesdays


def test_data_gaps_lists_dishes_left_out_of_the_analysis(db, menu, add_dish):
    add_dish('Calzone', 13.00, DishType.MAIN)   # no recipe
    ctx = ReportContext(db, *SEPTEMBER, today=TODAY)
    text = run_tool(ctx, 'data_gaps', {})
    assert 'Not analysed: Calzone (No recipe saved).' in text


def test_mistakes_in_a_tool_call_come_back_as_messages(db, menu):
    ctx = ReportContext(db, *SEPTEMBER, today=TODAY)
    assert run_tool(ctx, 'guess_the_future', {}).startswith('Unknown tool')
    assert run_tool(ctx, 'dish_detail', {}) == 'Bad input for dish_detail: missing dish'
    assert run_tool(ctx, 'actions', {'colour': 'red'}) == 'Bad input for actions: unexpected colour'
    assert not ctx.facts.items


def test_every_tool_is_described_for_the_api():
    definitions = {d['name']: d for d in tool_definitions()}
    assert set(definitions) == {'period_summary', 'actions', 'dish_detail', 'price_changes', 'sales_pattern', 'data_gaps'}
    assert definitions['dish_detail']['input_schema']['required'] == ['dish']
    assert definitions['sales_pattern']['input_schema']['properties']['by']['enum'] == ['weekday', 'category', 'dish']
