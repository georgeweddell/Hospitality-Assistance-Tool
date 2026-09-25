"""
Money on the Sales page: sales £ by day, by category and by dish for a period.

Sales £ for a day = units sold that day x the menu price charged that day
(costing.price_on), so a price change part-way through is counted correctly.
Menu prices include VAT, as everywhere else in the app.

Same rules as the analysis: only records wholly inside the period count, and
a multi-day total (e.g. a typed monthly figure) is spread evenly across its
days, the assumption agreed for average_menu_price.
"""

from collections import defaultdict
from datetime import timedelta

from costing import menu_prices, price_on
from models import Dish, SalesRecord
from schemas import SalesByCategoryOut, SalesByDayOut, SalesByDishOut, SalesSummaryOut


def sales_summary(db, start, end):
    records = db.query(SalesRecord).filter(SalesRecord.period_start >= start, SalesRecord.period_end <= end).all()
    dishes = {d.id: d for d in db.query(Dish).all()}
    prices = {}   # dish id -> its menu prices, fetched once

    by_day = defaultdict(lambda: [0.0, 0.0])    # day -> [sales, units]
    by_dish = defaultdict(lambda: [0.0, 0.0])   # dish id -> [sales, units]
    for r in records:
        if r.dish_id not in prices:
            prices[r.dish_id] = menu_prices(db, r.dish_id)
        days = (r.period_end - r.period_start).days + 1
        for offset in range(days):
            day = r.period_start + timedelta(days=offset)
            units = r.units_sold / days
            sales = units * price_on(prices[r.dish_id], day)
            by_day[day][0] += sales
            by_day[day][1] += units
            by_dish[r.dish_id][0] += sales
            by_dish[r.dish_id][1] += units

    by_category = defaultdict(lambda: [0.0, 0.0])
    for dish_id, (sales, units) in by_dish.items():
        category = dishes[dish_id].category
        by_category[category][0] += sales
        by_category[category][1] += units

    every_day = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    return SalesSummaryOut(
        start=start, end=end,
        total_sales=round(sum(s for s, _ in by_dish.values()), 2),
        total_units=round(sum(u for _, u in by_dish.values()), 1),
        days=[SalesByDayOut(day=d, sales=round(by_day[d][0], 2), units=round(by_day[d][1], 1)) for d in every_day],
        categories=sorted((SalesByCategoryOut(category=c, sales=round(s, 2), units=round(u, 1))
                           for c, (s, u) in by_category.items()), key=lambda c: -c.sales),
        dishes=sorted((SalesByDishOut(dish_id=i, name=dishes[i].name, category=dishes[i].category,
                                      sales=round(s, 2), units=round(u, 1))
                       for i, (s, u) in by_dish.items()), key=lambda d: -d.sales),
    )
