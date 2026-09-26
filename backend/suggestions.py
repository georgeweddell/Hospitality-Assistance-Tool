"""
Business checks: plain rules over the restaurant's own figures, each compared
with a rule of thumb from data/business_rules.csv (a check with no rule there
doesn't run) (roadmap step 9, agreed with
George 25 Sep 2026). No AI: every figure is worked out here, and a check
either fires or it doesn't. The report agent may choose and word them
(report_tools.business_checks) but doesn't invent them.

Each check returns a Check: a short title, whether it fires, the action if it
does, its figures (label, value, unit, formatted like the report's facts) and
the rule of thumb it was judged against.

The nine checks, for the chosen period:
  1 food_cost       food cost % of sales EX-VAT (sales / 1.2) against the band
                    for the restaurant type. Ex-VAT for this comparison only,
                    because trade rules of thumb are quoted ex-VAT; the rest
                    of the app still works VAT-inclusive (open item 1).
  2-3 attach        desserts, starters and sides sold for each main.
  4 midweek         Mon-Thu sales a day as a share of Fri-Sun sales a day.
  5 menu_size       dishes per category, and each category's share of Dogs.
  6 cheapest_top    the cheapest dish in a category is also its best seller.
  7 one_ingredient  one ingredient's share of the whole food cost.
  8 cost_basis      recipe cost on the restaurant's own prices.
  9 unmatched_rise  an ingredient rise (an alert) with no menu price change
                    since on the dishes it hit.
"""

import csv
import os
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from costing import best_price
from menu_engineering import classify_all_dishes
from models import BusinessProfile, Dish, DishIngredient, DishType, Ingredient, QuadrantType
from own_prices import menu_own_share
from price_changes import find_menu_price_changes, find_price_changes
from report_tools import format_value
from sales_report import sales_summary

RULES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'business_rules.csv')
RESTAURANT_TYPES = ['pizzeria', 'gastropub', 'cafe', 'indian', 'other']
VAT = 1.20
PLURAL = {DishType.STARTER: 'starters', DishType.MAIN: 'mains', DishType.SIDE: 'sides', DishType.DESSERT: 'desserts'}


def load_rules(path=RULES_FILE) -> dict:
    """{(rule, type): (low, high, note)} from the CSV; blank low/high -> None."""
    rules = {}
    with open(path, encoding='utf-8', newline='') as f:
        lines = (line for line in f if line.strip() and not line.lstrip().startswith('#'))
        for record in csv.DictReader(lines):
            number = lambda v: float(v) if v and v.strip() else None
            rules[(record['rule'].strip(), record['type'].strip())] = (
                number(record['low']), number(record['high']), record['note'].strip())
    return rules


def restaurant_type(db) -> str:
    profile = db.query(BusinessProfile).first()
    return profile.restaurant_type if profile else 'other'


@dataclass
class Figure:
    label: str
    value: float | list
    unit: str

    def out(self) -> dict:
        return {'label': self.label, 'value': self.value, 'unit': self.unit,
                'display': format_value(self.value, self.unit)}


@dataclass
class Check:
    key: str
    title: str
    fires: bool
    action: str = ''                      # what to do, when it fires (a short label)
    figures: list[Figure] = field(default_factory=list)
    rule_of_thumb: str = ''               # e.g. "at least 0.35 per main"
    note: str = ''                        # how it's worked out, shown on hover

    def out(self) -> dict:
        return {'key': self.key, 'title': self.title, 'fires': self.fires, 'action': self.action,
                'figures': [f.out() for f in self.figures], 'rule_of_thumb': self.rule_of_thumb, 'note': self.note}


class Checks:
    """Works out every check for a period. `today` fixes "now" for tests."""

    def __init__(self, db, start: date, end: date, today: date | None = None, rules: dict | None = None):
        self.db, self.start, self.end = db, start, end
        self.today = today or date.today()
        self.rules = rules if rules is not None else load_rules()
        self.type = restaurant_type(db)
        self.dishes = classify_all_dishes(db, start, end)

    def rule(self, key):
        """(low, high, note) for the restaurant's type, else the 'all' row."""
        return self.rules.get((key, self.type)) or self.rules.get((key, 'all')) or (None, None, '')

    def units_by_category(self) -> dict:
        units = defaultdict(int)
        for d in self.dishes:
            units[d.category] += d.units_sold
        return units

    # --- the checks ---------------------------------------------------------------

    def food_cost(self) -> Check | None:
        low, high, note = self.rule('food_cost_percent')
        if low is None or high is None:
            return None   # no rule of thumb for it (a row missing from the CSV): the check doesn't run
        cost = sum(d.plate_cost * d.units_sold for d in self.dishes)
        sales_ex_vat = sum(d.menu_price * d.units_sold for d in self.dishes) / VAT
        percent = cost / sales_ex_vat * 100
        fires = (low is not None and percent < low) or (high is not None and percent > high)
        figures = [Figure('Food cost, ex-VAT', percent, '%')]
        action = ''
        if high is not None and percent > high:
            worst = sorted(self.dishes, key=lambda d: -d.plate_cost / (d.menu_price / VAT))[:3]
            figures += [Figure(f'{d.dish_name}: food cost, ex-VAT', d.plate_cost / (d.menu_price / VAT) * 100, '%') for d in worst]
            action = 'Reprice or rework the dearest plates'
        elif low is not None and percent < low:
            action = 'Check recipes are complete and portions are right'
        return Check('food_cost', 'Food cost', fires, action, figures,
                     f'{low:g}–{high:g}% for a {self.type}' if self.type != 'other' else f'{low:g}–{high:g}%',
                     'Plate cost x plates sold, over sales without VAT (menu prices / 1.2). ' + note)

    def attach(self, category: DishType, rule_key: str, action: str) -> Check | None:
        units = self.units_by_category()
        if not units.get(DishType.MAIN) or category not in units:
            return None
        low, _, note = self.rule(rule_key)
        if low is None:
            return None
        ratio = units[category] / units[DishType.MAIN]
        name = PLURAL[category]
        return Check(f'{name}_per_main', f'{name.capitalize()} per main', ratio < low, action if ratio < low else '',
                     [Figure(f'{name.capitalize()} per main', ratio, 'per main'),
                      Figure(f'{name.capitalize()} sold', units[category], 'count'),
                      Figure('Mains sold', units[DishType.MAIN], 'count')],
                     f'at least {low:.2f} per main', note)

    def midweek(self) -> Check | None:
        low, _, note = self.rule('midweek_share')
        if low is None:
            return None
        days = [d for d in sales_summary(self.db, self.start, self.end).days if d.sales > 0]
        weekday = [d.sales for d in days if d.day.weekday() < 4]
        weekend = [d.sales for d in days if d.day.weekday() >= 4]
        if not weekday or not weekend:
            return None
        a, b = sum(weekday) / len(weekday), sum(weekend) / len(weekend)
        share = a / b
        return Check('midweek', 'Midweek trade', share < low, 'A midweek offer or event' if share < low else '',
                     [Figure('Mon–Thu sales a day', a, '£'), Figure('Fri–Sun sales a day', b, '£'),
                      Figure('Midweek as a share of the weekend', share * 100, '%')],
                     f'at least {low * 100:.0f}% of a weekend day', note)

    def menu_size(self) -> Check | None:
        _, most, note = self.rule('dishes_per_category')
        _, dog_most, dog_note = self.rule('dog_share')
        if most is None and dog_most is None:
            return None
        on_menu = defaultdict(int)
        for dish in self.db.query(Dish).all():
            if dish.category and dish.on_menu_from <= self.today and (dish.on_menu_until is None or dish.on_menu_until >= self.today):
                on_menu[dish.category] += 1
        figures, problems = [], []
        for category, count in on_menu.items():
            if most is not None and count > most:
                problems.append(f'{PLURAL[category]}: {count} dishes')
                figures.append(Figure(f'{PLURAL[category].capitalize()} on the menu', count, 'count'))
        for category in {d.category for d in self.dishes}:
            analysed = [d for d in self.dishes if d.category == category]
            dogs = [d for d in analysed if d.quadrant == QuadrantType.DOG]
            share = len(dogs) / len(analysed)
            if dog_most is not None and share > dog_most and len(analysed) >= 3:
                problems.append(f'{PLURAL[category]}: {len(dogs)} of {len(analysed)} are Dogs')
                figures.append(Figure(f'{PLURAL[category].capitalize()}: share that are Dogs', share * 100, '%'))
        rule_of_thumb = '; '.join(([f'at most {most:g} dishes a category'] if most is not None else [])
                                  + ([f'Dogs under {dog_most * 100:.0f}% of one'] if dog_most is not None else []))
        return Check('menu_size', 'Menu size', bool(problems), 'Trim the menu: ' + '; '.join(problems) if problems else '',
                     figures, rule_of_thumb, f'{note} {dog_note}'.strip())

    def cheapest_top(self) -> Check:
        figures, dishes = [], []
        for category in {d.category for d in self.dishes}:
            group = [d for d in self.dishes if d.category == category]
            if len(group) < 3:
                continue
            cheapest = min(group, key=lambda d: d.menu_price)
            top = max(group, key=lambda d: d.units_sold)
            if cheapest.dish_id == top.dish_id:
                dishes.append(cheapest.dish_name)
                figures += [Figure(f'{cheapest.dish_name}: average price, the cheapest {category.value.lower()}', cheapest.menu_price, '£'),
                            Figure(f'{cheapest.dish_name}: plates sold, the most', cheapest.units_sold, 'count')]
        return Check('cheapest_top', 'Cheapest is the best seller', bool(dishes),
                     f'Price {", ".join(dishes)} up, or add a cheaper dish to anchor it' if dishes else '', figures,
                     'the cheapest dish in a category shouldn\'t be its best seller',
                     'In a category of three or more, the dish at the lowest menu price is also the one sold most.')

    def one_ingredient(self) -> Check | None:
        _, most, note = self.rule('ingredient_share')
        if most is None:
            return None
        cost = defaultdict(float)
        for d in self.dishes:
            for line in self.db.query(DishIngredient).filter(DishIngredient.dish_id == d.dish_id):
                price = best_price(self.db, line.ingredient_id, as_of=self.today)
                if price:
                    cost[line.ingredient_id] += line.quantity * price.price_per_unit * d.units_sold
        total = sum(cost.values())
        if not total:
            return None
        top_id, top_cost = max(cost.items(), key=lambda kv: kv[1])
        share = top_cost / total
        name = self.db.get(Ingredient, top_id).name
        return Check('one_ingredient', 'Biggest single ingredient', share > most,
                     f'Watch the {name} price: get a second quote' if share > most else '',
                     [Figure(f'{name}: share of food cost', share * 100, '%'), Figure(f'{name}: cost over the period', top_cost, '£')],
                     f'no one ingredient over {most * 100:.0f}% of food cost', note)

    def cost_basis(self) -> Check | None:
        low, _, note = self.rule('own_price_share')
        share = menu_own_share(self.db, self.today)
        if low is None or share is None:
            return None
        return Check('cost_basis', 'Costs on your own prices', share < low, 'Upload supplier invoices' if share < low else '',
                     [Figure('Recipe cost on your own prices', share, '%')], f'at least {low:g}%', note)

    def unmatched_rises(self) -> Check:
        rises = [c for c in find_price_changes(self.db, self.start, self.today) if c.is_alert]
        repriced = defaultdict(list)
        for m in find_menu_price_changes(self.db, self.start, self.today):
            repriced[m.dish_id].append(m.day)
        figures, names = [], []
        for c in rises:
            behind = [e for e in c.dishes if not any(day >= c.day for day in repriced[e.dish_id])]
            if behind:
                names.append(c.name)
                figures.append(Figure(f'{c.name}: price change', c.change_percent, 'change %'))
                figures.append(Figure(f'{c.name}: dishes not repriced since', len(behind), 'count'))
        return Check('unmatched_rise', 'Price rises not passed on', bool(names),
                     f'Review menu prices on the dishes using {", ".join(names)}' if names else '', figures,
                     'a rise of 5% or more is followed by a menu price review',
                     'Ingredient rises of 5% or more since the period began, on dishes with no menu price change since.')

    def all(self) -> list[Check]:
        if not self.dishes:
            return []
        checks = [
            self.food_cost(),
            self.attach(DishType.DESSERT, 'desserts_per_main', 'Dessert board or table upsell'),
            self.attach(DishType.STARTER, 'starters_per_main', 'Sharing starters or a starter bundle'),
            self.attach(DishType.SIDE, 'sides_per_main', 'Suggest a side with each main'),
            self.midweek(), self.menu_size(), self.cheapest_top(), self.one_ingredient(),
            self.cost_basis(), self.unmatched_rises(),
        ]
        return [c for c in checks if c is not None]
