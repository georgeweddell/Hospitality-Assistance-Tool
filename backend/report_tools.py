"""
The report agent's tools: read-only questions Claude can ask about the data.

How the report works (see report_agent.py for the loop): Claude is given a
brief and these tools, and chooses which to call. Each tool is plain Python
over the database, like the rest of the app, and saves nothing.

The numbers rule: every number a tool finds is stored as a FACT with an id
(f1, f2, ...) and a unit. Claude sees the facts (it needs the values to
reason), but its report must cite fact ids instead of writing numbers, and
code checks that no digit appears in its text. The page then shows each
number from the fact itself, formatted here by code. So a number in the
report can only be wrong if the code that worked it out is wrong.

Periods: the report covers one period (e.g. August) and compares it with the
one before, chosen as on the Overview: the previous calendar month for a
month, otherwise the same number of days just before.
"""

import difflib
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta

from costing import best_price, menu_prices
from menu_engineering import build_action_list, classify_all_dishes, list_incomplete_dishes
from models import Dish, DishIngredient, Ingredient, IngredientPrice, PriceSource, SalesRecord, UnitType
from onboarding import setup_status
from periods import month_bounds
from sales_report import sales_summary

WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
VERB = {'Plowhorse': 'reprice', 'Puzzle': 'promote', 'Dog': 'review for cutting'}


# --- Periods ------------------------------------------------------------------

def previous_range(start: date, end: date) -> tuple[date, date]:
    """The period to compare with (same rule as previousRange in the frontend's dateRange.js)."""
    if (start, end) == month_bounds(start):
        return month_bounds(start - timedelta(days=1))
    days = (end - start).days + 1
    return start - timedelta(days=days), start - timedelta(days=1)


def describe(start: date, end: date) -> str:
    """'August 2026' for a whole month, else '1 Aug 2026 to 20 Aug 2026'."""
    if (start, end) == month_bounds(start):
        return start.strftime('%B %Y')
    return f"{start.day} {start.strftime('%b %Y')} to {end.day} {end.strftime('%b %Y')}"


# --- Facts --------------------------------------------------------------------

@dataclass
class Fact:
    id: str
    label: str      # what it is, e.g. "Margherita margin per plate"
    value: float | str
    unit: str       # '£', '%', 'change %' (signed), 'pts', 'count', '£/kg', '£/l', '£ each', 'date' or 'text'


def format_value(value, unit) -> str:
    """How a fact appears on the page. The only place report numbers are formatted."""
    if unit == '£':
        sign = '-' if value < 0 else ''
        return f'{sign}£{abs(value):,.0f}' if abs(value) >= 100 else f'{sign}£{abs(value):,.2f}'
    if unit == '%':
        return f'{value:.1f}%'
    if unit == 'change %':
        return f'{value:+.1f}%'
    if unit == 'pts':
        return f'{value:+.1f} pts'
    if unit == 'count':
        return f'{value:,.0f}'
    if unit in ('£/kg', '£/l'):
        return f'£{value:,.2f}/{unit[2:]}'
    if unit == '£ each':
        return f'£{value:,.2f} each'
    return str(value)


@dataclass
class Facts:
    """Every number found during one report, numbered in the order found."""
    items: dict = field(default_factory=dict)

    def add(self, label, value, unit) -> str:
        """Stores a fact and returns '[f7] label: value', the line Claude sees."""
        fact_id = f'f{len(self.items) + 1}'
        if isinstance(value, float):
            value = round(value, 2)
        self.items[fact_id] = Fact(fact_id, label, value, unit)
        return f'[{fact_id}] {label}: {format_value(value, unit)}'

    def as_list(self) -> list[dict]:
        return [vars(f) for f in self.items.values()]


# --- Shared context for one report ---------------------------------------------

class ReportContext:
    """The database, the periods and the facts for one report. Classifications are worked out once."""

    def __init__(self, db, start: date, end: date, today: date | None = None):
        self.db = db
        self.start, self.end = start, end
        self.prev_start, self.prev_end = previous_range(start, end)
        self.today = today or date.today()
        self.facts = Facts()
        self._now = self._prev = None

    @property
    def now(self):
        if self._now is None:
            self._now = classify_all_dishes(self.db, self.start, self.end)
        return self._now

    @property
    def prev(self):
        if self._prev is None:
            self._prev = classify_all_dishes(self.db, self.prev_start, self.prev_end)
        return self._prev


def summarise(dishes) -> dict:
    """Contribution, sales, units and gross margin % for a set of classified dishes (as figures.js)."""
    contribution = sum(d.margin_pounds * d.units_sold for d in dishes)
    sales = sum(d.menu_price * d.units_sold for d in dishes)
    units = sum(d.units_sold for d in dishes)
    return {'contribution': contribution, 'sales': sales, 'units': units,
            'gp': contribution / sales * 100 if sales else 0.0}


def pct_change(now, before):
    return (now - before) / before * 100 if before else None


def price_display(price_per_unit, unit) -> tuple[float, str]:
    """A per-gram or per-ml price as £/kg or £/l, the way a kitchen reads it."""
    if unit == UnitType.GRAM:
        return price_per_unit * 1000, '£/kg'
    if unit == UnitType.ML:
        return price_per_unit * 1000, '£/l'
    return price_per_unit, '£ each'


def quantity_display(quantity, unit) -> str:
    return f"{quantity:g} {'g' if unit == UnitType.GRAM else 'ml' if unit == UnitType.ML else 'each'}"


# --- The tools --------------------------------------------------------------------

def period_summary(ctx: ReportContext) -> str:
    """Contribution, sales, gross margin and dishes sold, this period against the previous one."""
    f = ctx.facts
    now, before = summarise(ctx.now), summarise(ctx.prev)
    lines = [f'Period: {describe(ctx.start, ctx.end)}. Compared with: {describe(ctx.prev_start, ctx.prev_end)}.']
    if not ctx.now:
        return lines[0] + ' No sales recorded in this period, so there is nothing to analyse.'
    lines += [
        f.add('Contribution (margin x units, all analysed dishes)', now['contribution'], '£'),
        f.add('Sales (menu price x units, incl. VAT)', now['sales'], '£'),
        f.add('Gross margin', now['gp'], '%'),
        f.add('Dishes sold', now['units'], 'count'),
        f.add('Dishes analysed', len(ctx.now), 'count'),
    ]
    if ctx.prev:
        lines += [
            f.add('Contribution, previous period', before['contribution'], '£'),
            f.add('Contribution change', pct_change(now['contribution'], before['contribution']), 'change %'),
            f.add('Sales change', pct_change(now['sales'], before['sales']), 'change %'),
            f.add('Gross margin change', now['gp'] - before['gp'], 'pts'),
            f.add('Dishes sold change', pct_change(now['units'], before['units']), 'change %'),
        ]
    else:
        lines.append('No sales in the previous period, so no comparison.')
    excluded = list_incomplete_dishes(ctx.db, ctx.start, ctx.end)
    if excluded:
        lines.append(f.add('Dishes on the menu but not analysed (see data_gaps)', len(excluded), 'count'))
    return '\n'.join(lines)


def actions(ctx: ReportContext, category: str | None = None) -> str:
    """The ranked recommended changes with their £ impact (a change in contribution over the period)."""
    f = ctx.facts
    by_id = {d.dish_id: d for d in ctx.now}
    ranked = [a for a in build_action_list(ctx.db, ctx.start, ctx.end)
              if category is None or by_id[a.dish_id].category.value.lower() == category.lower()]
    if not ranked:
        return 'No recommended changes' + (f' for {category}' if category else '') + '.'
    lines = [f.add('Total impact of all these changes', sum(a.impact_pounds for a in ranked), '£')]
    for rank, a in enumerate(ranked[:8], start=1):
        q = a.quadrant.value
        d = by_id[a.dish_id]
        lines.append(f'{rank}. {a.dish_name} ({d.category.value}, {q}): {VERB[q]}. '
                     + f.add(f'{a.dish_name} impact', a.impact_pounds, '£'))
    if len(ranked) > 8:
        lines.append(f'...and {len(ranked) - 8} smaller ones.')
    lines.append('Impact: Plowhorse = margin brought up to the category average; Puzzle = sales brought up to '
                 'the popularity line; Dog = if cut, its customers switch to an average-margin dish.')
    return '\n'.join(lines)


def find_dish(db, name: str):
    """A dish by name: exact (ignoring case), else the single close match. Returns (dish, suggestions)."""
    dishes = db.query(Dish).all()
    for d in dishes:
        if d.name.lower() == name.strip().lower():
            return d, []
    close = difflib.get_close_matches(name.strip().lower(), [d.name.lower() for d in dishes], n=3, cutoff=0.6)
    if len(close) == 1:
        return next(d for d in dishes if d.name.lower() == close[0]), []
    return None, [next(d.name for d in dishes if d.name.lower() == c) for c in close]


def spread_units(db, dish_id, start, end) -> dict:
    """Units per day for a dish, from records wholly inside the period (a multi-day total spread evenly)."""
    per_day = defaultdict(float)
    for r in db.query(SalesRecord).filter(SalesRecord.dish_id == dish_id, SalesRecord.period_start >= start,
                                          SalesRecord.period_end <= end):
        days = (r.period_end - r.period_start).days + 1
        for i in range(days):
            per_day[r.period_start + timedelta(days=i)] += r.units_sold / days
    return per_day


def dish_detail(ctx: ReportContext, dish: str) -> str:
    """One dish: quadrant now and before, price history, costs, recipe lines, sales by week."""
    f = ctx.facts
    found, suggestions = find_dish(ctx.db, dish)
    if not found:
        return f'No dish called "{dish}".' + (f' Did you mean: {", ".join(suggestions)}?' if suggestions else '')
    name = found.name
    now = next((d for d in ctx.now if d.dish_id == found.id), None)
    before = next((d for d in ctx.prev if d.dish_id == found.id), None)
    lines = [f'{name} ({found.category.value if found.category else "no category"}).']

    if now is None:
        reasons = next((i.reasons for i in list_incomplete_dishes(ctx.db, ctx.start, ctx.end) if i.dish_id == found.id), [])
        lines.append('Not analysed this period' + (f': {"; ".join(reasons)}.' if reasons else ' (not on the menu).'))
    else:
        was = f', was {before.quadrant.value}' if before and before.quadrant != now.quadrant else \
              ', same as before' if before else ', new this period'
        lines += [
            f'Quadrant: {now.quadrant.value}{was}.',
            f.add(f'{name} menu price (average charged this period)', now.menu_price, '£'),
            f.add(f'{name} plate cost', now.plate_cost, '£'),
            f.add(f'{name} margin per plate', now.margin_pounds, '£'),
            f.add(f'{name} gross margin', now.margin_percent, '%'),
            f.add(f'{name} units sold', now.units_sold, 'count'),
            f.add(f'{name} share of its category\'s units', now.menu_mix_percent, '%'),
            f.add(f'{found.category.value} popularity line (70% of an equal share)', now.popularity_threshold, '%'),
            f.add(f'{found.category.value} average margin per plate (the profitability line)',
                  now.profitability_threshold, '£'),
        ]
        if before:
            lines.append(f.add(f'{name} units sold, previous period', before.units_sold, 'count'))

    prices = menu_prices(ctx.db, found.id)
    if len(prices) > 1:
        lines.append('Menu price history:')
        lines += ['  ' + f.add(f'{name} price from {p.effective_date:%d %b %Y}', p.price, '£') for p in prices]

    recipe = []
    for row in ctx.db.query(DishIngredient).filter(DishIngredient.dish_id == found.id):
        ingredient = ctx.db.get(Ingredient, row.ingredient_id)
        price = best_price(ctx.db, row.ingredient_id, as_of=ctx.today)
        if price:
            recipe.append((row.quantity * price.price_per_unit, ingredient, row.quantity, price))
    if recipe:
        lines.append('Most expensive recipe lines:')
        for cost, ingredient, quantity, price in sorted(recipe, key=lambda r: -r[0])[:5]:
            lines.append(f'  {ingredient.name}, {quantity_display(quantity, ingredient.unit)} '
                         f'({price.source.value} price): ' + f.add(f'{name}: {ingredient.name} cost per plate', cost, '£'))

    per_day = spread_units(ctx.db, found.id, ctx.start, ctx.end)
    if per_day:
        lines.append('Units sold by week:')
        week_start = ctx.start
        while week_start <= ctx.end:
            week_end = min(week_start + timedelta(days=6), ctx.end)
            units = sum(u for day, u in per_day.items() if week_start <= day <= week_end)
            lines.append('  ' + f.add(f'{name} units {week_start:%d %b} to {week_end:%d %b}', units, 'count'))
            week_start = week_end + timedelta(days=1)
    return '\n'.join(lines)


def price_changes(ctx: ReportContext) -> str:
    """
    Ingredient price changes from the start of the period to today, for ingredients
    in current recipes: old and new price, and the £ effect on each dish using it.
    A change is when the price costing uses (costing.best_price) moves on a day.
    """
    f = ctx.facts
    in_use = defaultdict(list)   # ingredient id -> [(dish, quantity)]
    for row in ctx.db.query(DishIngredient):
        in_use[row.ingredient_id].append((ctx.db.get(Dish, row.dish_id), row.quantity))
    units = {d.dish_id: d.units_sold for d in ctx.now}

    changes = []
    for ingredient_id in in_use:
        new_rows = ctx.db.query(IngredientPrice).filter(
            IngredientPrice.ingredient_id == ingredient_id,
            IngredientPrice.effective_date >= ctx.start, IngredientPrice.effective_date <= ctx.today)
        for day in sorted({p.effective_date for p in new_rows}):
            old = best_price(ctx.db, ingredient_id, as_of=day - timedelta(days=1))
            new = best_price(ctx.db, ingredient_id, as_of=day)
            if old and new and new.effective_date == day and new.price_per_unit != old.price_per_unit:
                changes.append((day, ingredient_id, old, new))
    if not changes:
        return f'No ingredient price changes since {ctx.start:%d %b %Y} for ingredients in your recipes.'

    rows = []
    for day, ingredient_id, old, new in changes:
        ingredient = ctx.db.get(Ingredient, ingredient_id)
        delta = new.price_per_unit - old.price_per_unit
        effects = [(dish, quantity * delta) for dish, quantity in in_use[ingredient_id]]
        period_effect = sum(per_plate * units.get(dish.id, 0) for dish, per_plate in effects)
        rows.append((abs(period_effect), day, ingredient, old, new, effects, period_effect))

    lines = [f'Price changes since {ctx.start:%d %b %Y} (the period effect uses this period\'s units sold):']
    for _, day, ingredient, old, new, effects, period_effect in sorted(rows, key=lambda r: -r[0])[:8]:
        old_v, unit = price_display(old.price_per_unit, ingredient.unit)
        new_v, _ = price_display(new.price_per_unit, ingredient.unit)
        lines.append(f'{ingredient.name}, from {day:%d %b %Y} ({new.source.value}'
                     + (f', {new.supplier}' if new.supplier else '') + '):')
        lines.append('  ' + f.add(f'{ingredient.name} price before', old_v, unit))
        lines.append('  ' + f.add(f'{ingredient.name} price after', new_v, unit))
        lines.append('  ' + f.add(f'{ingredient.name} price change', pct_change(new_v, old_v), 'change %'))
        for dish, per_plate in sorted(effects, key=lambda e: -abs(e[1]))[:4]:
            lines.append('  ' + f.add(f'{dish.name} plate cost change from {ingredient.name}', per_plate, '£'))
        lines.append('  ' + f.add(f'{ingredient.name}: effect on contribution over the period', -period_effect, '£'))
    return '\n'.join(lines)


def sales_pattern(ctx: ReportContext, by: str) -> str:
    """Sales £ by weekday, by category, or the best and worst selling dishes."""
    f = ctx.facts
    summary = sales_summary(ctx.db, ctx.start, ctx.end)
    if summary.total_sales == 0:
        return 'No sales recorded in this period.'

    if by == 'weekday':
        totals, counts = defaultdict(float), defaultdict(int)
        for d in summary.days:
            if d.sales > 0:
                totals[d.day.weekday()] += d.sales
                counts[d.day.weekday()] += 1
        lines = ['Average sales per trading day, by weekday:']
        for w in range(7):
            if counts[w]:
                lines.append(f'  {WEEKDAYS[w]} ({counts[w]} days): ' + f.add(f'Average {WEEKDAYS[w]} sales', totals[w] / counts[w], '£'))
        return '\n'.join(lines)

    if by == 'category':
        lines = ['Sales by category:']
        for c in summary.categories:
            label = c.category.value if c.category else 'No category'
            lines.append(f'  {label}: ' + f.add(f'{label} sales', c.sales, '£') + '; '
                         + f.add(f'{label} share of sales', c.sales / summary.total_sales * 100, '%') + '; '
                         + f.add(f'{label} units', c.units, 'count'))
        return '\n'.join(lines)

    if by == 'dish':
        ranked = sorted(summary.dishes, key=lambda d: -d.units)
        lines = ['Best sellers by units:']
        lines += [f'  {d.name}: ' + f.add(f'{d.name} units', d.units, 'count') + '; ' + f.add(f'{d.name} sales', d.sales, '£')
                  for d in ranked[:5]]
        lines.append('Lowest sellers by units:')
        lines += [f'  {d.name}: ' + f.add(f'{d.name} units', d.units, 'count') + '; ' + f.add(f'{d.name} sales', d.sales, '£')
                  for d in ranked[-5:][::-1]]
        return '\n'.join(lines)

    return f'Unknown breakdown "{by}". Use weekday, category or dish.'


def data_gaps(ctx: ReportContext) -> str:
    """What's missing or uncertain: dishes not analysed, unchecked AI recipes, days without sales, benchmark prices."""
    f = ctx.facts
    lines = []
    for i in list_incomplete_dishes(ctx.db, ctx.start, ctx.end):
        lines.append(f'Not analysed: {i.dish_name} ({"; ".join(i.reasons)}).')
    status = setup_status(ctx.db, today=ctx.today)
    if status.unchecked_recipes:
        lines.append(f.add('Recipes estimated by AI and not yet checked by the owner', status.unchecked_recipes, 'count'))
    summary = sales_summary(ctx.db, ctx.start, ctx.end)
    empty = [d.day for d in summary.days if d.sales == 0]
    if empty:
        lines.append(f.add('Days in the period with no sales recorded', len(empty), 'count')
                     + f' ({", ".join(d.strftime("%d %b") for d in empty[:10])}' + (', ...' if len(empty) > 10 else '') + ')')
    if status.ingredients_in_use:
        benchmark = status.ingredients_in_use - status.ingredients_with_own_price
        lines.append(f.add('Ingredients in recipes still costed on benchmark prices (not the restaurant\'s own)', benchmark, 'count'))
        lines.append(f.add('Share of ingredients in recipes on the restaurant\'s own prices',
                           status.ingredients_with_own_price / status.ingredients_in_use * 100, '%'))
    return '\n'.join(lines) if lines else 'No gaps: every dish is analysed, recipes are checked and every day has sales.'


# --- The registry the agent uses ----------------------------------------------------

TOOLS = {
    'period_summary': (period_summary, 'The headline figures for the period against the previous one: contribution, '
                                       'sales, gross margin, dishes sold. Start here.', {}),
    'actions': (actions, 'The ranked recommended changes (reprice, promote, review for cutting) with £ impact. '
                         'Optionally for one category: Starter, Main, Side or Dessert.',
                {'category': {'type': 'string', 'enum': ['Starter', 'Main', 'Side', 'Dessert']}}),
    'dish_detail': (dish_detail, 'Everything about one dish: quadrant now and before, costs, price history, '
                                 'most expensive recipe lines, units by week.',
                    {'dish': {'type': 'string', 'description': 'The dish name, as on the menu'}}),
    'price_changes': (price_changes, 'Ingredient price changes since the period began and their £ effect '
                                     'on the dishes using them.', {}),
    'sales_pattern': (sales_pattern, 'Sales broken down by weekday, by category, or best and worst sellers.',
                      {'by': {'type': 'string', 'enum': ['weekday', 'category', 'dish']}}),
    'data_gaps': (data_gaps, 'What is missing or uncertain in the data: dishes not analysed, unchecked AI recipes, '
                             'days without sales, ingredients still on benchmark prices.', {}),
}
REQUIRED = {'dish_detail': ['dish'], 'sales_pattern': ['by']}


def tool_definitions() -> list[dict]:
    """The tools as the Anthropic API expects them: name, description and a JSON schema for the input."""
    return [{'name': name, 'description': description,
             'input_schema': {'type': 'object', 'properties': properties, 'required': REQUIRED.get(name, [])}}
            for name, (_, description, properties) in TOOLS.items()]


def run_tool(ctx: ReportContext, name: str, tool_input: dict) -> str:
    """
    Runs one tool call from Claude. Never raises for Claude's mistakes: an unknown
    tool or a bad input comes back as a message, so Claude can correct itself.
    """
    if name not in TOOLS:
        return f'Unknown tool "{name}". Available: {", ".join(TOOLS)}.'
    function, _, properties = TOOLS[name]
    unexpected = set(tool_input) - set(properties)
    missing = [k for k in REQUIRED.get(name, []) if not tool_input.get(k)]
    if unexpected or missing:
        return f'Bad input for {name}: ' + '; '.join(
            ([f'unexpected {", ".join(sorted(unexpected))}'] if unexpected else [])
            + ([f'missing {", ".join(missing)}'] if missing else []))
    return function(ctx, **tool_input)
