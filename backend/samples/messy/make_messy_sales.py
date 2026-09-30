"""
Writes samples/messy/sales/: till exports for "The Tidewater (sample)",
21 May - 20 Sep 2026, from the till it started with (Square-style), the till
it switched to on 1 Aug (SumUp-style), a delivery platform and a hand tally.

Trade is simulated table by table: covers by weekday and season, closed on
Mondays and for a staff holiday (10-16 Aug), lunch and dinner services, set
lunches, kids' meals, drinks. The same fixed random seed gives the same files.

The files (what each one tests is in samples/messy/README.md):
  popup-tally-may.csv                    typed by hand: one column per day (wide)
  square-items-2026-05-28-to-06-30.csv   starts before the menu does
  square-items-2026-07-01-to-07-15.csv   July "month to date"...
  square-items-2026-07.csv               ...then all of July (overlaps it)
  deliveroo-orders-2026-07.csv           several dishes in one cell per order
  SumUp_Transactions_August_2026.csv     report lines above the header, semicolons,
                                         Windows encoding, decimal commas, truncated
                                         CAPITAL names, cancelled orders, a total row,
                                         a row dated 2027
  sept-daily-items-EXCEL.csv             re-saved in Excel: subtotal rows, "Grand Total"

Run from backend/:
    .\\venv\\Scripts\\python.exe samples\\messy\\make_messy_sales.py
"""

import csv
import io
import random
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

OUT = Path(__file__).parent / "sales"
rng = random.Random(2026)

SUMMER = date(2026, 8, 1)          # the summer menu and the new till start
HOLIDAY = (date(2026, 8, 10), date(2026, 8, 16))
CHICKEN_LAST_DAY = date(2026, 8, 7)   # "86" on the summer menu, but the till sold it for a week

# dish key -> (price, category) on the spring menu; summer changes below
PRICE = {
    "soup": 7, "mackerel": 8.5, "squid": 9.5, "porkbelly": 8, "burrata": 10, "oysters3": 9, "oysters6": 16,
    "haddock": 17.5, "haddock_small": 13, "steak": 24, "hake": 22, "lamb": 26, "burger": 16.5, "risotto": 15,
    "sole": 0, "chicken": 19, "crab": 18, "chips": 4.5, "truffle": 6, "tenderstem": 5, "salad": 4.5, "bread": 4,
    "stp": 8, "brulee": 7.5, "tart": 8, "affogato": 6, "cheese3": 11, "cheese5": 16, "roast": 24,
    "kids_fish": 8, "kids_burger": 7.5, "kids_icecream": 3.5, "setlunch2": 20, "setlunch3": 25,
    "cauli": 8, "eton": 7.5,
}
SUMMER_PRICE = {"squid": 10.5, "burrata": 10.5, "oysters3": 9.5, "oysters6": 17, "haddock": 18.5, "hake": 23,
                "burger": 17, "crab": 21, "chips": 5, "tart": 8.5, "roast": 25}
DRINKS = [("lager", 6.2, 30), ("white", 7, 16), ("red", 7, 12), ("coke", 3, 14), ("water", 4, 8),
          ("espresso", 2.8, 9), ("flatwhite", 3.4, 7)]

# How each till names things. None: that till never rings it up.
SQUARE = {
    "soup": ("Soup of the Day", ""), "mackerel": ("Mackerel Pate", ""), "squid": ("Salt & Pepper Squid", ""),
    "porkbelly": ("Pork Belly Bites", ""), "burrata": ("Burrata", ""),
    "oysters3": ("Rock Oysters", "x3"), "oysters6": ("Rock Oysters", "x6"),
    "haddock": ("Fish & Chips", "Regular"), "haddock_small": ("Fish & Chips", "Small"),
    "steak": ("Steak Frites", ""), "hake": ("Hake", ""), "lamb": ("Lamb Rump", ""),
    "burger": ("Tidewater Burger", ""), "risotto": ("Mushroom Risotto", ""), "sole": ("Lemon Sole (MP)", ""),
    "chicken": ("Chicken Supreme", ""), "crab": ("SPECIAL - Crab Linguine", ""),
    "chips": ("Chips", ""), "truffle": ("Truffle Fries", ""), "tenderstem": ("Tenderstem", ""),
    "salad": ("House Salad", ""), "bread": ("Bread & Butter", ""),
    "stp": ("Sticky Toffee Pudding", ""), "brulee": ("Crème Brûlée", ""), "tart": ("Choc Tart", ""),
    "affogato": ("Affogato", ""), "cheese3": ("Cheeseboard", "3"), "cheese5": ("Cheeseboard", "5"),
    "roast": ("Sunday Roast", ""), "kids_fish": ("Kids Fish & Chips", ""), "kids_burger": ("Kids Burger", ""),
    "kids_icecream": ("Kids Ice Cream", ""), "setlunch2": ("Set Lunch - 2 Courses", ""),
    "setlunch3": ("Set Lunch - 3 Courses", ""),
    "lager": ("Lager Pint", ""), "white": ("House White 175ml", ""), "red": ("House Red 175ml", ""),
    "coke": ("Coke", ""), "water": ("Sparkling Water 750ml", ""), "espresso": ("Espresso", ""),
    "flatwhite": ("Flat White", ""), "pepper": ("Peppercorn Sauce", ""),
}
# The bar iPad's item library was set up separately and names some things differently.
SQUARE_BAR = {"burger": ("Burger", ""), "brulee": ("Creme Brulee", ""), "chips": ("Fries", "")}
SUMUP = {
    "soup": "SOUP OF THE DAY", "mackerel": "MACKEREL PATE", "squid": "S&P SQUID", "cauli": "KOREAN CAULI",
    "burrata": "BURRATA PEACH", "oysters3": "OYSTERS X3", "oysters6": "OYSTERS X6",
    "haddock": "HADDOCK & CHIPS", "haddock_small": "HADDOCK & CHIPS SMALL", "steak": "FLAT IRON STEAK",
    "hake": "HAKE BROWN SHRIMP", "burger": "SMASH BURGER", "risotto": "PEA & MINT RISOTTO",
    "sole": "LEMON SOLE", "chicken": "CHICKEN SUPREME", "crab": "CRAB LINGUINE", "chips": "CHIPS",
    "truffle": "TRUFFLE PARM FRIES", "tenderstem": "TENDERSTEM", "salad": "HOUSE SALAD",
    "bread": "BREAD & BUTTER", "stp": "STICKY TOFFEE PUDDING", "brulee": "CRÈME BRÛLÉE",
    "tart": "DARK CHOC TART", "affogato": "AFFOGATO", "eton": "ETON MESS", "cheese3": "CHEESEBOARD 3",
    "cheese5": "CHEESEBOARD 5", "roast": "SUNDAY ROAST SIRLOIN", "kids_fish": "KIDS FISH & CHIPS",
    "kids_burger": "KIDS BURGER", "kids_icecream": "KIDS ICE CREAM", "setlunch2": "SET LUNCH 2 COURSE",
    "setlunch3": "SET LUNCH 3 COURSE", "lager": "LAGER PINT", "white": "HOUSE WHITE 175",
    "red": "HOUSE RED 175", "coke": "COKE", "water": "SPARKLING WATER", "espresso": "ESPRESSO",
    "flatwhite": "FLAT WHITE", "pepper": "PEPPERCORN SAUCE",
}
SUMUP_WIDTH = 20   # the new till cuts item names at 20 characters

CATEGORY = {**{k: "Starters" for k in ("soup", "mackerel", "squid", "porkbelly", "burrata", "oysters3",
                                         "oysters6", "cauli")},
            **{k: "Mains" for k in ("haddock", "haddock_small", "steak", "hake", "lamb", "burger", "risotto",
                                      "sole", "chicken", "crab", "roast")},
            **{k: "Sides" for k in ("chips", "truffle", "tenderstem", "salad", "bread", "pepper")},
            **{k: "Desserts" for k in ("stp", "brulee", "tart", "affogato", "cheese3", "cheese5", "eton")},
            **{k: "Kids" for k in ("kids_fish", "kids_burger", "kids_icecream")},
            **{k: "Set Menu" for k in ("setlunch2", "setlunch3")},
            **{k: "Drinks" for k, _, _ in DRINKS}}


def price(key, day):
    if key in SUMMER_PRICE and day >= SUMMER:
        return SUMMER_PRICE[key]
    return PRICE.get(key) or dict((k, p) for k, p, _ in DRINKS).get(key, 3)


def pick(weights):
    keys, w = zip(*[(k, v) for k, v in weights.items() if v > 0])
    return rng.choices(keys, w)[0]


# --- What was sold ---------------------------------------------------------------------------

def menu_weights(day):
    """Popularity of each dish on this day (0: not available)."""
    summer = day >= SUMMER
    special_crab = day.weekday() in (3, 4, 5)   # a Thursday-Saturday special before it joined the menu
    starters = {"soup": 18 if not summer else 12, "mackerel": 10, "squid": 24, "burrata": 9 if not summer else 11,
                "porkbelly": 0 if summer else 14, "cauli": 13 if summer else 0}
    mains = {"haddock": 28, "burger": 22 if not summer else 20, "steak": 12, "hake": 9 if not summer else 10,
             "risotto": 7 if not summer else 6, "sole": 3, "lamb": 0 if summer else 5,
             "chicken": 10 if day <= CHICKEN_LAST_DAY else 0,
             "crab": 9 if summer else (7 if special_crab else 0)}
    desserts = {"stp": 34, "brulee": 20, "tart": 17, "affogato": 9, "cheese3": 6, "cheese5": 4,
                "eton": 16 if summer else 0}
    sides = {"chips": 30, "truffle": 18, "tenderstem": 9, "salad": 7}
    return starters, mains, desserts, sides


def covers_for(day, service):
    """How many people eat in, by weekday, season and service. Closed Mondays and on holiday."""
    if day.weekday() == 0 or HOLIDAY[0] <= day <= HOLIDAY[1]:
        return 0
    base = {1: (10, 22), 2: (12, 24), 3: (14, 30), 4: (18, 46), 5: (26, 50), 6: (44, 14)}[day.weekday()]
    covers = base[0] if service == "lunch" else base[1]
    if day < date(2026, 6, 1):
        covers *= 0.6                        # soft launch
    elif day.month == 8 or (day.month == 7 and day.day > 20):
        covers *= 1.3                        # school holidays by the sea
    elif day.month == 9:
        covers *= 0.95
    return max(0, round(covers * rng.uniform(0.8, 1.2)))


def party_sizes(covers):
    sizes = []
    while covers > 0:
        size = min(covers, rng.choices([1, 2, 3, 4, 5, 6], [8, 46, 14, 22, 5, 5])[0])
        sizes.append(size)
        covers -= size
    return sizes


def order_for(day, service, size):
    """A table's order: {"items": Counter(key -> qty), "set_parts": [dish keys inside set lunches]}."""
    starters, mains, desserts, sides = menu_weights(day)
    items, set_parts = Counter(), []
    kids = rng.randint(1, size - 2) if size >= 3 and rng.random() < 0.3 else 0
    for _ in range(kids):
        items[rng.choices(["kids_fish", "kids_burger"], [55, 45])[0]] += 1
        if rng.random() < 0.6:
            items["kids_icecream"] += 1
    for _ in range(size - kids):
        if service == "lunch" and day.weekday() in (1, 2, 3, 4) and rng.random() < 0.35:
            three = rng.random() < 0.35
            items["setlunch3" if three else "setlunch2"] += 1
            set_parts += [rng.choice(["soup", "mackerel"]), rng.choice(["haddock_small", "risotto"])]
            if three:
                set_parts.append(rng.choice(["stp", "kids_icecream"]))
            continue
        if rng.random() < 0.45:
            items[pick(starters)] += 1
        if rng.random() < 0.07:
            items["oysters6" if rng.random() < 0.4 else "oysters3"] += 1
        if rng.random() < 0.93:
            if day.weekday() == 6 and rng.random() < 0.45:
                main = "roast"
            else:
                main = pick(mains)
                if main == "haddock" and rng.random() < 0.2:
                    main = "haddock_small"
            items[main] += 1
            if main == "steak" and rng.random() < 0.4:
                items["pepper"] += 1
        if rng.random() < 0.35:
            items[pick(sides)] += 1
        if rng.random() < 0.33:
            items[pick(desserts)] += 1
    if rng.random() < 0.4:
        items["bread"] += 1
    for key, _, weight in DRINKS:
        items[key] += sum(1 for _ in range(size) if rng.random() < weight / 60)
    return {"items": +items, "set_parts": set_parts}


def trade(first, last):
    """Every table from first to last: (datetime, table number, size, order)."""
    tables = []
    day = first
    while day <= last:
        for service, (open_h, close_h) in (("lunch", (12, 15)), ("dinner", (18, 23))):
            for size in party_sizes(covers_for(day, service)):
                minute = rng.randint(open_h * 60, close_h * 60 + (50 if service == "dinner" else 0))
                if service == "dinner" and day.weekday() == 5 and rng.random() < 0.03:
                    minute = 24 * 60 + rng.randint(0, 40)   # a late Saturday table paid after midnight
                when = datetime.combine(day, datetime.min.time()) + timedelta(minutes=minute)
                tables.append((when, rng.randint(1, 16), size, order_for(day, service, size)))
        day += timedelta(days=1)
    return sorted(tables, key=lambda t: t[0])


# --- Writers ---------------------------------------------------------------------------------

def write(name, text, encoding="utf-8"):
    (OUT / name).write_bytes(text.encode(encoding))
    print(f"  {name:42} {len(text.encode(encoding)) / 1024:7.0f} KB")


def csv_text(rows, delimiter=","):
    buf = io.StringIO()
    csv.writer(buf, delimiter=delimiter, lineterminator="\r\n").writerows(rows)
    return buf.getvalue()


def square_rows(tables):
    header = ["Date", "Time", "Time Zone", "Category", "Item", "Qty", "Price Point Name", "Modifiers Applied",
              "Gross Sales", "Discounts", "Net Sales", "Tax", "Transaction ID", "Device Name", "Notes",
              "Event Type", "Dining Option", "Customer ID", "Customer Name"]
    rows = [header]
    for n, (when, table, size, order) in enumerate(tables):
        device = "Bar iPad" if rng.random() < 0.18 else "Counter iPad"
        txn = f"T{rng.randint(10**7, 10**8 - 1)}"
        customer = ("", "")
        if rng.random() < 0.12:
            c = rng.randint(100, 999)
            customer = (f"C{c}", f"Sample Customer {c}")
        note = ""
        if rng.random() < 0.02:
            note = f"Table {table} - call {'07700 900' + str(rng.randint(100, 999))} when ready"
        elif rng.random() < 0.02:
            note = rng.choice(["birthday - candle on pud", "nut allergy table", "regulars"])
        day = when.date()
        set_parts = list(order["set_parts"])
        for key, qty in order["items"].items():
            name, point = (SQUARE_BAR.get(key) if device == "Bar iPad" else None) or SQUARE[key]
            unit = price(key, day) if key != "sole" else rng.choice([24, 26, 27])
            modifiers = ""
            if key == "burger" and rng.random() < 0.3:
                modifiers = rng.choice(["Add Bacon", "Add Cheese", "Add Bacon, Add Cheese"])
            if key.startswith("setlunch"):
                courses = 3 if key == "setlunch3" else 2
                parts, set_parts = set_parts[:courses * qty], set_parts[courses * qty:]
                modifiers = ", ".join(SQUARE[p][0] + (" (Small)" if p == "haddock_small" else "") for p in parts)
            gross = round(unit * qty, 2)
            discount, row_note, event = 0.0, note, "Payment"
            if rng.random() < 0.005 and CATEGORY.get(key) != "Drinks":
                discount, row_note = gross, "comp - long wait"
            rows.append([day.isoformat(), when.strftime("%H:%M:%S"), "Europe/London", CATEGORY.get(key, "Other"),
                         name, qty, point or "Regular", modifiers, f"{gross:.2f}", f"{0 - discount:.2f}",
                         f"{gross - discount:.2f}", f"{(gross - discount) / 6:.2f}", txn, device, row_note,
                         event, rng.choice(["Eat in", "Eat in", "Eat in", "Takeaway"]), *customer])
            if rng.random() < 0.004:   # refunded later (sent back)
                rows.append([day.isoformat(), (when + timedelta(minutes=40)).strftime("%H:%M:%S"),
                             "Europe/London", CATEGORY.get(key, "Other"), name, 1, point or "Regular", "",
                             f"{-unit:.2f}", "0.00", f"{-unit:.2f}", f"{-unit / 6:.2f}", txn, device,
                             "sent back", "Refund", "Eat in", *customer])
            elif rng.random() < 0.004:  # rung up by mistake and voided
                rows.append([day.isoformat(), (when + timedelta(minutes=2)).strftime("%H:%M:%S"),
                             "Europe/London", CATEGORY.get(key, "Other"), name, 1, point or "Regular", "",
                             "0.00", "0.00", "0.00", "0.00", txn, device, "wrong table", "Void", "Eat in", *customer])
        if rng.random() < 0.05 and size >= 6:
            rows.append([day.isoformat(), when.strftime("%H:%M:%S"), "Europe/London", "Other",
                         "Service Charge 12.5%", 1, "Regular", "", "0.00", "0.00", "0.00", "0.00", txn, device,
                         "", "Payment", "Eat in", *customer])
        if n % 37 == 0:  # a staff meal, rung up at full price and discounted to nothing
            rows.append([day.isoformat(), "16:30:00", "Europe/London", "Other", "Staff Meal", 1, "Regular",
                         rng.choice(["Burger", "Fish & Chips", "Risotto"]), "10.00", "-10.00", "0.00", "0.00",
                         f"T{rng.randint(10**7, 10**8 - 1)}", "Counter iPad", "", "Payment", "Eat in", "", ""])
        if rng.random() < 0.01:
            rows.append([day.isoformat(), when.strftime("%H:%M:%S"), "Europe/London", "Other", "Custom Amount", 1,
                         "Regular", "", "5.00", "0.00", "5.00", "0.83", txn, device, "", "Payment", "Eat in", *customer])
    return rows


def sumup_text(tables):
    """The new till's transaction report: semicolons, decimal commas, Windows encoding, a preamble."""
    lines = ["SumUp Sales Report", "Merchant;The Tidewater (sample)", "Period;01.08.2026 - 31.08.2026",
             "Exported;01.09.2026 08:14", ""]
    rows = [["Date", "Transaction ID", "Receipt No.", "Payment type", "Status", "Description", "Quantity",
             "Price (gross)", "VAT", "Total", "Staff", "Table"]]
    staff = ["Jess", "Tom", "Priya", "Sam"]
    total_qty, total = 0.0, 0.0

    def comma(x):
        return f"{x:.2f}".replace(".", ",")

    for n, (when, table, size, order) in enumerate(tables):
        status = "Cancelled" if rng.random() < 0.01 else "Paid"
        receipt = f"S-{4000 + n}"
        stamp = when.strftime("%d.%m.%Y %H:%M")
        if n == 300:
            stamp = when.replace(year=2027).strftime("%d.%m.%Y %H:%M")   # a device with the wrong year
        for key, qty in order["items"].items():
            name = SUMUP[key][:SUMUP_WIDTH]
            unit = price(key, when.date()) if key != "sole" else rng.choice([26, 27, 28])
            rows.append([stamp, f"TX{rng.randint(10**9, 10**10 - 1)}", receipt,
                         rng.choice(["Card", "Card", "Card", "Cash"]), status, name, comma(qty), f"£{comma(unit)}",
                         "20%", f"£{comma(unit * qty)}", rng.choice(staff), f"T{table}"])
            if status == "Paid":
                total_qty += qty
                total += unit * qty
            if rng.random() < 0.004:
                rows.append([stamp, f"TX{rng.randint(10**9, 10**10 - 1)}", receipt, "Card", "Refunded", name,
                             comma(-1), f"£{comma(unit)}", "20%", f"£{comma(-unit)}", rng.choice(staff), f"T{table}"])
                total_qty -= 1
                total -= unit
        if rng.random() < 0.01:
            rows.append([stamp, f"TX{rng.randint(10**9, 10**10 - 1)}", receipt, "Card", "Paid", "OPEN FOOD",
                         comma(1), f"£{comma(6)}", "20%", f"£{comma(6)}", rng.choice(staff), f"T{table}"])
    rows.append(["", "", "", "", "", "TOTAL", comma(total_qty), "", "", f"£{comma(total)}", "", ""])
    return "\r\n".join(lines) + "\r\n" + csv_text(rows, delimiter=";")


def sept_excel_rows(tables):
    """A daily item summary after a round trip through Excel: d/m/yyyy dates, subtotal rows, a grand total."""
    per_day = {}
    for when, _, _, order in tables:
        day = when.date()
        for key, qty in order["items"].items():
            per_day.setdefault(day, Counter())[SUMUP[key][:SUMUP_WIDTH]] += qty
    rows = [["Date", "Item", "Qty Sold", "Net Sales (£)"], ]
    grand = 0
    for day in sorted(per_day):
        d = f"{day.day}/{day.month}/{day.year}"
        for item, qty in sorted(per_day[day].items()):
            rows.append([d, item, qty, ""])
        day_total = sum(per_day[day].values())
        grand += day_total
        rows.append([d, "Total", day_total, ""])
        rows.append(["", "", "", ""])
    rows.append(["", "Grand Total", grand, ""])
    return rows


def deliveroo_rows(first, last):
    """Delivery orders: every dish in one cell ("1x Fish & Chips; 2x Chips")."""
    names = {"haddock": "Fish & Chips (Regular)", "burger": "Tidewater Burger", "risotto": "Mushroom Risotto",
             "chips": "Chips", "truffle": "Truffle Fries", "stp": "Sticky Toffee Pudding",
             "squid": "Salt & Pepper Squid", "kids_fish": "Kids Fish & Chips"}
    weights = {"haddock": 40, "burger": 30, "risotto": 10, "squid": 12, "kids_fish": 8}
    rows = [["Order ID", "Date", "Time", "Status", "Customer First Name", "Delivery Postcode", "Items",
             "Subtotal (£)", "Commission (£)", "Payout (£)"]]
    day = first
    while day <= last:
        if day.weekday() != 0:
            for _ in range(rng.randint(3, 9)):
                basket = Counter()
                for _ in range(rng.randint(1, 3)):
                    basket[pick(weights)] += 1
                if rng.random() < 0.6:
                    basket[rng.choice(["chips", "truffle"])] += rng.randint(1, 2)
                if rng.random() < 0.25:
                    basket["stp"] += 1
                subtotal = sum(price(k, day) * q for k, q in basket.items())
                status = rng.choices(["Delivered", "Cancelled", "Rejected"], [95, 3, 2])[0]
                rows.append([f"GB-{rng.randint(10**6, 10**7 - 1)}", day.strftime("%d/%m/%Y"),
                             f"{rng.randint(17, 21)}:{rng.randint(0, 59):02d}", status,
                             rng.choice(["Alex", "Sam", "Jo", "Chris", "Pat"]), "AB1 2CD",
                             "; ".join(f"{q}x {names[k]}" for k, q in basket.items()),
                             f"{subtotal:.2f}", f"{subtotal * 0.3:.2f}", f"{subtotal * 0.7:.2f}"])
        day += timedelta(days=1)
    return rows


def popup_tally():
    """The owner's hand tally from the pop-up week before the till: one row per dish, one column per day."""
    days = ["Thu 21/5", "Fri 22/5", "Sat 23/5", "Sun 24/5", "Tue 26/5", "Wed 27/5"]
    dishes = ["fish n chips", "burger", "squid", "steak frites", "risotto", "soup", "chips", "STP", "brulee"]
    rows = [["Pop-up week - covers & dishes (rough)"], ["Dish"] + days + ["Total"]]
    for dish in dishes:
        counts = [rng.randint(3, 22) for _ in days]
        cells = [str(c) for c in counts]
        if dish == "risotto":
            cells[1] = "-"
        if dish == "soup":
            cells[3] = "approx 10"
        if dish == "brulee":
            cells[4] = ""
        rows.append([dish] + cells + [str(sum(counts))])
    rows.append(["covers"] + [str(rng.randint(30, 70)) for _ in days] + [""])
    return rows


def main():
    OUT.mkdir(exist_ok=True)
    write("popup-tally-may.csv", csv_text(popup_tally()))

    june = trade(date(2026, 5, 28), date(2026, 6, 30))
    july = trade(date(2026, 7, 1), date(2026, 7, 31))
    write("square-items-2026-05-28-to-06-30.csv", csv_text(square_rows(june)))
    month_to_date = [t for t in july if t[0].date() <= date(2026, 7, 15)]
    july_rows = square_rows(july)
    write("square-items-2026-07.csv", csv_text(july_rows))
    # The month-to-date export has the same first half of July (exported on the 16th).
    write("square-items-2026-07-01-to-07-15.csv",
          csv_text([july_rows[0]] + [r for r in july_rows[1:] if r[0] <= "2026-07-15"]))
    write("deliveroo-orders-2026-07.csv", csv_text(deliveroo_rows(date(2026, 7, 1), date(2026, 7, 31))))

    august = trade(date(2026, 8, 1), date(2026, 8, 31))
    write("SumUp_Transactions_August_2026.csv", sumup_text(august), encoding="cp1252")

    september = trade(date(2026, 9, 1), date(2026, 9, 20))
    write("sept-daily-items-EXCEL.csv", "﻿" + csv_text(sept_excel_rows(september)))
    print(f"  ({len(month_to_date)} tables in the month-to-date export)")


if __name__ == "__main__":
    main()
