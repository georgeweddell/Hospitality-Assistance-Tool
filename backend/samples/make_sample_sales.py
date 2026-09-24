"""
Writes samples/sample-sales.csv: a made-up, Square-style item sales export
for 1-21 September 2026, for trying the till import by hand
(Imports -> Upload sales) against the demo data, which ends on 31 August.

It's built to exercise the review screen:
- some till names differ from the menu ("Garlic Bread", "Nduja + Hot Honey"),
  so Claude's suggestions are needed; the rest match exactly;
- drinks, add-ons and a service charge, which should be ignored;
- a refund (Event Type = Refund) and modifiers, which must not add units;
- two Marinara sales, though it came off the menu on 31 July (flagged);
- customer columns with made-up names, which are blanked before Claude sees
  the sample rows.

Volumes follow the demo's August trade, spread by weekday like seed_demo.py.
The same file is written every run (fixed random seed).
Run from backend/:
    .\\venv\\Scripts\\python.exe samples\\make_sample_sales.py
"""

import csv
import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # to import seed_demo
from seed_demo import DISHES, PRICE_CHANGES, month_total, spread_over_days  # noqa: E402

DAYS = [date(2026, 9, 1) + timedelta(days=i) for i in range(21)]

# How this till names some dishes; others are exactly the menu name.
TILL_NAMES = {
    "Garlic Pizza Bread": "Garlic Bread",
    "Rosemary Fries": "Fries (Rosemary)",
    "Rocket & Parmesan Salad": "Rocket Salad",
    "Prosciutto e Rucola": "Prosciutto Rucola",
    "Nduja & Hot Honey": "Nduja + Hot Honey",
}
# Not dishes: (till name, category, price, sold per day)
OTHER = [
    ("Peroni 330ml", "Drinks", 5.00, 38),
    ("Coca-Cola 330ml", "Drinks", 3.00, 22),
    ("San Pellegrino 500ml", "Drinks", 3.50, 12),
    ("House Red 175ml", "Wine", 7.00, 15),
    ("Espresso", "Coffee", 2.50, 14),
    ("Extra Nduja", "Add-ons", 2.00, 6),
    ("Service Charge 12.5%", "Service", 0.00, 4),
]
HEADER = ["Date", "Time", "Time Zone", "Category", "Item", "Qty", "Price Point Name", "Modifiers Applied",
          "Gross Sales", "Discounts", "Net Sales", "Tax", "Transaction ID", "Device Name", "Event Type",
          "Dining Option", "Customer ID", "Customer Name"]


def price_on(name, day, price):
    for new_price, start in PRICE_CHANGES.get(name, []):
        if day >= start:
            price = new_price
    return price


def rows():
    rng = random.Random(7)
    out = []

    def add(day, category, item, qty, price, event="Payment", modifiers=""):
        gross = round(qty * price, 2)
        customer = rng.random() < 0.15
        out.append([day.isoformat(), f"{rng.randint(12, 22):02d}:{rng.randint(0, 59):02d}:00", "Europe/London",
                    category, item, qty, "Regular", modifiers, f"{gross:.2f}", "0.00", f"{gross:.2f}",
                    f"{gross / 6:.2f}", f"T{rng.randint(100000, 999999)}", "Counter iPad", event,
                    rng.choice(["Eat in", "Eat in", "Takeaway"]),
                    f"C{rng.randint(1000, 9999)}" if customer else "",
                    f"Sample Customer {rng.randint(1, 99)}" if customer else ""])

    for name, category, price, june_units, *_ in DISHES:
        if name in ("Marinara", "Mortadella & Pistachio"):
            continue
        september = round(month_total(name, june_units, 8) * len(DAYS) / 31)   # August's pace
        for day, units in spread_over_days(september, DAYS):
            while units > 0:   # a day's sales arrive as several till lines
                qty = min(units, rng.randint(1, 3))
                modifiers = "Extra basil" if category.value == "Main" and rng.random() < 0.05 else ""
                add(day, category.value, TILL_NAMES.get(name, name), qty, price_on(name, day, price), modifiers=modifiers)
                units -= qty

    for day, units in spread_over_days(round(160 * len(DAYS) / 31), DAYS):   # the Mortadella special
        if units:
            add(day, "Main", "Mortadella & Pistachio", units, 15.00)
    for item, category, price, per_day in OTHER:
        for day in DAYS:
            add(day, category, item, max(1, per_day + rng.randint(-4, 4)), price)

    add(date(2026, 9, 5), "Main", "Marinara", 1, 9.00)    # off the menu since 31 July
    add(date(2026, 9, 12), "Main", "Marinara", 1, 9.00)
    add(date(2026, 9, 13), "Main", "Diavola", 1, 13.00, event="Refund")

    out.sort(key=lambda r: (r[0], r[1]))
    return out


if __name__ == "__main__":
    target = Path(__file__).parent / "sample-sales.csv"
    with open(target, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(HEADER)
        writer.writerows(rows())
    print(f"Wrote {target}")
