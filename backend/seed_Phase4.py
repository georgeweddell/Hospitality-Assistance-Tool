"""
Seed script for Phase 4 testing.
Creates a spread of dishes across all four categories, each with one
sales record showing deliberately uneven units sold — so the classifier
has clear stars, plowhorses, puzzles, and dogs to sort.

Run once with your venv active:
    python seed_phase4.py
"""

from datetime import date
from database import SessionLocal   # <-- check this matches your database.py
from models import Dish, DishType, SalesRecord

db = SessionLocal()

# (name, category, menu_price, units_sold)
dishes_to_seed = [
    # Starters
    ("Garlic Bread", DishType.STARTER, 4.50, 80),
    ("Bruschetta", DishType.STARTER, 5.50, 15),
    ("Arancini", DishType.STARTER, 6.00, 45),

    # Sides
    ("Fries", DishType.SIDE, 3.50, 200),
    ("Side Salad", DishType.SIDE, 3.50, 30),
    ("Garlic Knots", DishType.SIDE, 4.00, 70),

    # Mains (pizzas)
    ("Margherita", DishType.MAIN, 9.00, 180),
    ("Pepperoni", DishType.MAIN, 10.50, 150),
    ("Quattro Formaggi", DishType.MAIN, 12.00, 40),
    ("Diavola", DishType.MAIN, 11.00, 90),
    ("Marinara", DishType.MAIN, 8.00, 20),
    ("Prosciutto e Funghi", DishType.MAIN, 12.50, 60),

    # Desserts
    ("Tiramisu", DishType.DESSERT, 6.00, 60),
    ("Panna Cotta", DishType.DESSERT, 5.50, 10),
    ("Cannoli", DishType.DESSERT, 5.00, 35),
]

period_start = date(2026, 6, 1)
period_end = date(2026, 6, 30)

for name, category, menu_price, units_sold in dishes_to_seed:
    dish = Dish(name=name, category=category, menu_price=menu_price)
    db.add(dish)
    db.commit()
    db.refresh(dish)

    sales = SalesRecord(
        dish_id=dish.id,
        units_sold=units_sold,
        period_start=period_start,
        period_end=period_end,
    )
    db.add(sales)
    db.commit()

    print(f"Seeded: {name} ({category.value}) — {units_sold} units")

db.close()
print("Done.")