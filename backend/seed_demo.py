"""
Rebuilds menu.db with realistic demo data: three months (June-August 2026) of
daily sales at a small independent Neapolitan-style pizzeria in the UK,
roughly 50 covers a day.

- Recipes are hand-written with real portion sizes, so costs are checkable.
- Quadrants come out of the numbers; nothing is forced.
- Sales are stored per dish per day, busier at weekends. June's daily figures
  add up exactly to the June totals in DISHES.
- July and August show the owner acting on the analysis: Marinara (a Dog) comes
  off the menu at the end of July; Nduja & Hot Honey and Burrata (Puzzles) are
  promoted in August; a Mortadella special launches on 15 July.
- Tiramisu's Marsala isn't in the stock list, so it's flagged as not costed.
- Every ingredient has a benchmark price. A few also have invoice prices,
  which costing prefers (see costing.best_price), including a mozzarella
  price rise in September.

WARNING: this wipes the database. The current menu.db is copied to
menu.backup-<timestamp>.db first.

Run from backend/:
    .\\venv\\Scripts\\python.exe seed_demo.py
"""

import os
import shutil
from datetime import date, datetime, timedelta

from database import Base, SessionLocal, engine
from models import (Dish, DishIngredient, DishType, Ingredient, IngredientPrice, PriceSource,
                    SalesRecord, UnitType, User)
from costing import cost_dish

G, ML, EACH = UnitType.GRAM, UnitType.ML, UnitType.EACH

# (name, unit, price per base unit). Prices are 2026 UK wholesale estimates;
# the comment gives the pack price they come from.
INGREDIENTS = [
    # --- dough ---
    ("00 flour", G, 0.0013),                     # £1.30/kg
    ("semolina", G, 0.0011),                     # £1.10/kg
    ("salt", G, 0.0006),                         # £0.60/kg
    ("fresh yeast", G, 0.003),                   # £3.00/kg
    ("water", ML, 0.0),

    # --- dairy / cheese ---
    ("mozzarella (fior di latte)", G, 0.0075),   # £7.50/kg
    ("buffalo mozzarella", G, 0.013),            # £13.00/kg
    ("burrata", G, 0.016),                       # £16.00/kg
    ("parmesan", G, 0.014),                      # £14.00/kg
    ("gorgonzola", G, 0.009),                    # £9.00/kg
    ("ricotta", G, 0.005),                       # £5.00/kg
    ("mascarpone", G, 0.0055),                   # £5.50/kg
    ("butter", G, 0.006),                        # £6.00/kg
    ("double cream", ML, 0.0035),                # £3.50/l
    ("whole milk", ML, 0.0011),                  # £1.10/l
    ("vanilla gelato", ML, 0.008),               # £8.00/l, bought in

    # --- tomato ---
    ("san marzano tomatoes", G, 0.0035),         # £3.50/kg tinned
    ("tomato passata", ML, 0.0018),              # £1.80/l

    # --- meat ---
    ("spicy salami", G, 0.013),                  # £13.00/kg
    ("prosciutto crudo", G, 0.028),              # £28.00/kg
    ("nduja", G, 0.018),                         # £18.00/kg
    ("fennel sausage", G, 0.011),                # £11.00/kg
    ("mortadella", G, 0.016),                    # £16.00/kg
    ("cooked ham", G, 0.009),                    # £9.00/kg

    # --- fresh produce ---
    ("fresh basil", G, 0.025),                   # £25.00/kg
    ("fresh parsley", G, 0.02),                  # £20.00/kg
    ("fresh rosemary", G, 0.02),                 # £20.00/kg
    ("garlic", G, 0.003),                        # £3.00/kg
    ("red onion", G, 0.0012),                    # £1.20/kg
    ("cherry tomatoes", G, 0.0025),              # £2.50/kg
    ("rocket", G, 0.008),                        # £8.00/kg
    ("chestnut mushrooms", G, 0.0035),           # £3.50/kg
    ("friarielli", G, 0.012),                    # £12.00/kg jarred
    ("fresh red chilli", G, 0.004),              # £4.00/kg
    ("potatoes", G, 0.0012),                     # £1.20/kg
    ("lemon", EACH, 0.35),
    ("frozen mixed berries", G, 0.005),          # £5.00/kg

    # --- pantry ---
    ("olive oil", ML, 0.006),                    # £6.00/l
    ("extra virgin olive oil", ML, 0.009),       # £9.00/l
    ("vegetable oil", ML, 0.0022),               # £2.20/l, frying
    ("balsamic vinegar", ML, 0.004),             # £4.00/l
    ("dried oregano", G, 0.015),                 # £15.00/kg
    ("chilli flakes", G, 0.01),                  # £10.00/kg
    ("black pepper", G, 0.012),                  # £12.00/kg
    ("honey", G, 0.008),                         # £8.00/kg
    ("pistachios", G, 0.03),                     # £30.00/kg
    ("arborio rice", G, 0.0025),                 # £2.50/kg
    ("chicken stock", ML, 0.0015),               # £1.50/l
    ("peas", G, 0.002),                          # £2.00/kg frozen
    ("breadcrumbs", G, 0.0018),                  # £1.80/kg
    ("ciabatta", G, 0.004),                      # £4.00/kg

    # --- dessert ---
    ("egg", EACH, 0.30),
    ("sugar", G, 0.001),                         # £1.00/kg
    ("icing sugar", G, 0.0011),                  # £1.10/kg
    ("savoiardi biscuits", G, 0.005),            # £5.00/kg
    ("espresso coffee", ML, 0.005),              # ~15p a 30 ml shot
    ("cocoa powder", G, 0.008),                  # £8.00/kg
    ("vanilla extract", ML, 0.03),               # £30.00/l
    ("gelatine leaves", G, 0.02),                # £20.00/kg
    ("hazelnut chocolate spread", G, 0.006),     # £6.00/kg
    ("cannoli shells", EACH, 0.45),              # bought in
    ("dark chocolate chips", G, 0.008),          # £8.00/kg
    ("candied citrus peel", G, 0.012),           # £12.00/kg
]


# The restaurant's own invoice prices, which override the benchmarks above.
# (ingredient, price per base unit, invoice date). Supplier is made up.
DEMO_SUPPLIER = "Napoli Foods (demo)"
INVOICE_PRICES = [
    ("mozzarella (fior di latte)", 0.0074, date(2026, 6, 3)),   # £7.40/kg
    ("mozzarella (fior di latte)", 0.0082, date(2026, 9, 12)),  # £8.20/kg, price rise
    ("00 flour", 0.00125, date(2026, 6, 3)),                   # £1.25/kg
    ("san marzano tomatoes", 0.0038, date(2026, 7, 15)),       # £3.80/kg
]
BENCHMARK_DATE = date(2026, 6, 1)


def dough(grams):
    """A Neapolitan dough ball (~62% hydration), scaled to its weight."""
    return [
        ("00 flour", grams * 0.61),
        ("water", grams * 0.375),
        ("salt", grams * 0.018),
        ("fresh yeast", grams * 0.0012),
    ]


TOMATO_BASE = [("san marzano tomatoes", 80), ("salt", 1)]
MARGHERITA = dough(250) + TOMATO_BASE + [
    ("mozzarella (fior di latte)", 100),
    ("fresh basil", 4),
    ("extra virgin olive oil", 5),
]

# (name, category, menu price, units sold in June, recipe, skipped ingredients)
# units_sold=None -> not on the menu in June (see MENU_DATES and MONTH_TOTALS).
DISHES = [
    # --- Starters ---
    ("Garlic Pizza Bread", DishType.STARTER, 6.50, 380, dough(150) + [
        ("butter", 15), ("garlic", 6), ("fresh parsley", 2), ("olive oil", 5),
    ], []),
    ("Arancini", DishType.STARTER, 7.50, 260, [
        ("arborio rice", 60), ("chicken stock", 150), ("parmesan", 10),
        ("mozzarella (fior di latte)", 20), ("peas", 15), ("egg", 0.5),
        ("00 flour", 10), ("breadcrumbs", 25), ("vegetable oil", 15),
        ("tomato passata", 50),
    ], []),
    ("Burrata", DishType.STARTER, 9.50, 95, [
        ("burrata", 125), ("cherry tomatoes", 60), ("fresh basil", 2),
        ("extra virgin olive oil", 10), ("ciabatta", 60),
    ], []),
    ("Bruschetta", DishType.STARTER, 6.00, 70, [
        ("ciabatta", 80), ("cherry tomatoes", 100), ("garlic", 3), ("red onion", 10),
        ("fresh basil", 2), ("extra virgin olive oil", 10), ("balsamic vinegar", 5),
    ], []),

    # --- Sides ---
    ("Rosemary Fries", DishType.SIDE, 4.50, 420, [
        ("potatoes", 200), ("vegetable oil", 20), ("salt", 2), ("fresh rosemary", 1),
    ], []),
    ("Dough Balls", DishType.SIDE, 5.00, 240, dough(120) + [
        ("butter", 20), ("garlic", 5), ("fresh parsley", 2),
    ], []),
    ("Rocket & Parmesan Salad", DishType.SIDE, 5.00, 110, [
        ("rocket", 50), ("parmesan", 15), ("cherry tomatoes", 40),
        ("extra virgin olive oil", 10), ("balsamic vinegar", 5),
    ], []),
    ("Friarielli", DishType.SIDE, 6.00, 45, [
        ("friarielli", 100), ("garlic", 4), ("fresh red chilli", 2), ("extra virgin olive oil", 10),
    ], []),

    # --- Mains (12" Neapolitan pizzas) ---
    ("Margherita", DishType.MAIN, 11.00, 520, MARGHERITA, []),
    ("Diavola", DishType.MAIN, 13.00, 380, MARGHERITA + [
        ("spicy salami", 50), ("fresh red chilli", 3),
    ], []),
    ("Prosciutto e Rucola", DishType.MAIN, 14.50, 210, MARGHERITA + [
        ("prosciutto crudo", 50), ("rocket", 15), ("parmesan", 10),
    ], []),
    ("Salsiccia e Friarielli", DishType.MAIN, 14.00, 170, dough(250) + [
        ("mozzarella (fior di latte)", 110), ("fennel sausage", 70),
        ("friarielli", 50), ("extra virgin olive oil", 5),
    ], []),
    ("Nduja & Hot Honey", DishType.MAIN, 14.00, 140, MARGHERITA + [
        ("nduja", 40), ("honey", 10), ("chilli flakes", 1),
    ], []),
    ("Funghi", DishType.MAIN, 12.00, 110, MARGHERITA + [
        ("chestnut mushrooms", 70), ("garlic", 3), ("fresh parsley", 2),
    ], []),
    ("Marinara", DishType.MAIN, 9.00, 90, dough(250) + [
        ("san marzano tomatoes", 100), ("salt", 1), ("garlic", 5),
        ("dried oregano", 1), ("extra virgin olive oil", 10),
    ], []),
    ("Quattro Formaggi", DishType.MAIN, 13.50, 80, dough(250) + [
        ("mozzarella (fior di latte)", 60), ("gorgonzola", 40),
        ("parmesan", 15), ("ricotta", 30),
    ], []),
    # New special, launched 15 July (see MENU_DATES).
    ("Mortadella & Pistachio", DishType.MAIN, 15.00, None, dough(250) + [
        ("mozzarella (fior di latte)", 100), ("mortadella", 60),
        ("pistachios", 10), ("ricotta", 30),
    ], []),

    # --- Desserts ---
    ("Tiramisu", DishType.DESSERT, 7.00, 230, [
        ("mascarpone", 60), ("egg", 1), ("sugar", 20), ("savoiardi biscuits", 40),
        ("espresso coffee", 60), ("cocoa powder", 3),
    ], ["marsala wine"]),
    ("Nutella Calzone", DishType.DESSERT, 7.50, 160, dough(150) + [
        ("hazelnut chocolate spread", 60), ("icing sugar", 5),
    ], []),
    ("Affogato", DishType.DESSERT, 5.00, 70, [
        ("vanilla gelato", 120), ("espresso coffee", 30),
    ], []),
    ("Panna Cotta", DishType.DESSERT, 7.00, 55, [
        ("double cream", 120), ("whole milk", 30), ("sugar", 20), ("vanilla extract", 2),
        ("gelatine leaves", 2), ("frozen mixed berries", 40),
    ], []),
    ("Cannoli", DishType.DESSERT, 7.00, 45, [
        ("cannoli shells", 2), ("ricotta", 80), ("icing sugar", 15),
        ("dark chocolate chips", 10), ("pistachios", 5), ("candied citrus peel", 5),
    ], []),
]

# --- Sales -------------------------------------------------------------------

OPENED = date(2025, 3, 1)   # every dish is on the menu from here unless MENU_DATES says otherwise

# name -> (on the menu from, until). until None = still on the menu.
MENU_DATES = {
    "Mortadella & Pistachio": (date(2026, 7, 15), None),   # summer special
    "Marinara": (OPENED, date(2026, 7, 31)),                # a Dog, cut after July
}

MONTHS = [(2026, 6), (2026, 7), (2026, 8)]

# Monthly totals are June's figure (from DISHES) times these, unless
# MONTH_TOTALS gives the number directly.
MONTH_FACTORS = {7: 1.06, 8: 1.12}           # gentle summer lift
DISH_FACTORS = {
    "Nduja & Hot Honey": {8: 1.80},          # a Puzzle, promoted in August
    "Burrata": {8: 1.50},                     # a Puzzle, promoted in August
    "Marinara": {7: 0.90},
    "Affogato": {7: 0.80, 8: 0.70},
}
MONTH_TOTALS = {
    "Mortadella & Pistachio": {7: 70, 8: 160},
}

# Relative trade by weekday, Monday first. Friday and Saturday are busiest.
WEEKDAY_WEIGHTS = [0.75, 0.80, 0.90, 1.00, 1.40, 1.55, 1.10]


def month_days(year, month):
    day = date(year, month, 1)
    while day.month == month:
        yield day
        day += timedelta(days=1)


def spread_over_days(total, days):
    """
    Split a monthly total across days by weekday weight, as whole numbers that
    add up to exactly `total` (the remainder goes to the days with the largest
    fractions, so it's the same every run).
    """
    weights = [WEEKDAY_WEIGHTS[d.weekday()] for d in days]
    exact = [total * w / sum(weights) for w in weights]
    counts = [int(x) for x in exact]
    by_fraction = sorted(range(len(days)), key=lambda i: (-(exact[i] - counts[i]), i))
    for i in by_fraction[: total - sum(counts)]:
        counts[i] += 1
    return list(zip(days, counts))


def month_total(name, june_units, month):
    if name in MONTH_TOTALS:
        return MONTH_TOTALS[name].get(month, 0)
    if month == 6:
        return june_units or 0
    factor = DISH_FACTORS.get(name, {}).get(month, MONTH_FACTORS[month])
    return round(june_units * factor)


def backup_database():
    if os.path.exists("menu.db"):
        backup = f"menu.backup-{datetime.now():%Y%m%d-%H%M%S}.db"
        shutil.copy("menu.db", backup)
        print(f"Backed up existing database to {backup}")


def seed():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    db.add(User(email="dev@example.com"))

    ingredients = {}
    for name, unit, price in INGREDIENTS:
        ingredients[name] = Ingredient(name=name, unit=unit)
        db.add(ingredients[name])
    db.commit()

    for name, unit, price in INGREDIENTS:
        db.add(IngredientPrice(ingredient_id=ingredients[name].id, price_per_unit=price,
                               source=PriceSource.BENCHMARK, effective_date=BENCHMARK_DATE))
    for name, price, invoice_date in INVOICE_PRICES:
        db.add(IngredientPrice(ingredient_id=ingredients[name].id, price_per_unit=price,
                               source=PriceSource.INVOICE, supplier=DEMO_SUPPLIER,
                               effective_date=invoice_date))
    db.commit()

    for name, category, price, units_sold, recipe, skipped in DISHES:
        on_from, on_until = MENU_DATES.get(name, (OPENED, None))
        dish = Dish(name=name, category=category, menu_price=price, skipped_ingredients=skipped,
                    on_menu_from=on_from, on_menu_until=on_until)
        db.add(dish)
        db.commit()

        # Merge repeated ingredients (e.g. salt in both dough and sauce).
        quantities = {}
        for ingredient_name, quantity in recipe:
            assert ingredient_name in ingredients, f"{name}: unknown ingredient '{ingredient_name}'"
            quantities[ingredient_name] = quantities.get(ingredient_name, 0) + quantity
        for ingredient_name, quantity in quantities.items():
            db.add(DishIngredient(dish_id=dish.id, ingredient_id=ingredients[ingredient_name].id,
                                  quantity=round(quantity, 2)))

        monthly = []
        for year, month in MONTHS:
            on_menu = [d for d in month_days(year, month)
                       if on_from <= d and (on_until is None or d <= on_until)]
            total = month_total(name, units_sold, month) if on_menu else 0
            monthly.append(total)
            for day, units in spread_over_days(total, on_menu):
                if units:   # days with no sales leave no record, as a till export wouldn't list them
                    db.add(SalesRecord(dish_id=dish.id, units_sold=units, period_start=day, period_end=day))
        db.commit()

        plate_cost, margin, margin_percent = cost_dish(db, dish.id)
        sales = "  ".join(f"{m:>4}" for m in monthly)
        print(f"  {name:<26} £{price:>5.2f}  cost £{plate_cost:>4.2f}  GP {margin_percent:>5.1f}%  Jun/Jul/Aug {sales}")

    db.close()
    print(f"\nSeeded {len(INGREDIENTS)} ingredients and {len(DISHES)} dishes.")


if __name__ == "__main__":
    backup_database()
    seed()
