"""
The benchmark ingredient price list (data/benchmark_prices.csv).

Benchmarks are estimates used until a restaurant enters its own prices
(costing.best_price always prefers the restaurant's own). The file is written
the way a kitchen reads prices ("£8.50 per kg"); units.py converts each one to
a price per gram / ml / each as it's loaded, so the units rule holds here too.
"""

import csv
import os
from datetime import date

from sqlalchemy import func

from models import Ingredient, IngredientPrice, PriceSource, UnitType
from units import price_per_base_unit

BENCHMARK_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'benchmark_prices.csv')
BENCHMARK_DATE = date(2026, 6, 1)   # the date these prices apply from


def read_benchmarks(path=BENCHMARK_FILE):
    """
    The list as [(name, UnitType, price per base unit)], in file order.
    Raises ValueError, naming the line, on anything it can't use.
    """
    rows, seen = [], set()
    with open(path, encoding='utf-8', newline='') as f:
        lines = (line for line in f if line.strip() and not line.lstrip().startswith('#'))
        for n, record in enumerate(csv.DictReader(lines), start=1):
            name = record['name'].strip()
            try:
                unit = UnitType(record['measured_by'].strip())
                price = price_per_base_unit(float(record['price']), 1, record['per'].strip(), unit)
            except ValueError as e:
                raise ValueError(f"Benchmark row {n} ({name}): {e}") from e
            if name.lower() in seen:
                raise ValueError(f"Benchmark row {n}: '{name}' appears twice")
            seen.add(name.lower())
            rows.append((name, unit, price))
    return rows


def sync_benchmarks(db, rows=None, as_of=BENCHMARK_DATE):
    """
    Brings the database in line with the benchmark list, without removing anything.

    - An ingredient not in the database is added, with its benchmark price.
    - One that exists (same name, ignoring case) whose latest benchmark differs
      gets a new benchmark price row dated `as_of`; its history is kept.
    - One whose unit disagrees (e.g. litres here, grams in the database) is
      left alone and reported, since converting it would break its recipes.

    Returns counts plus the conflicting names.
    """
    rows = read_benchmarks() if rows is None else rows
    summary = {'added': 0, 'updated': 0, 'unchanged': 0, 'conflicts': []}

    for name, unit, price in rows:
        ingredient = db.query(Ingredient).filter(func.lower(Ingredient.name) == name.lower()).first()
        if ingredient is None:
            ingredient = Ingredient(name=name, unit=unit)
            db.add(ingredient)
            db.flush()   # gives it an id for its price row
            db.add(IngredientPrice(ingredient_id=ingredient.id, price_per_unit=price,
                                   source=PriceSource.BENCHMARK, effective_date=as_of))
            summary['added'] += 1
            continue

        if ingredient.unit != unit:
            summary['conflicts'].append(name)
            continue

        latest = (db.query(IngredientPrice)
                  .filter(IngredientPrice.ingredient_id == ingredient.id,
                          IngredientPrice.source == PriceSource.BENCHMARK)
                  .order_by(IngredientPrice.effective_date.desc(), IngredientPrice.id.desc())
                  .first())
        if latest is not None and abs(latest.price_per_unit - price) < 1e-12:
            summary['unchanged'] += 1
        else:
            db.add(IngredientPrice(ingredient_id=ingredient.id, price_per_unit=price,
                                   source=PriceSource.BENCHMARK, effective_date=as_of))
            summary['updated'] += 1

    db.commit()
    return summary
