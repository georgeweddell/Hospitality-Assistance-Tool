"""
Bulk recipe estimation for seed dishes.
Auto-accepts the AI's top-matched ingredients — skips the human-confirmation
step deliberately, for test-data purposes only. Not how the real product works.

Run once with your venv active:
    python seed_recipes.py
"""

from database import SessionLocal
from models import Dish, DishIngredient
from recipe_ai import estimate_recipe
from matching import match_recipe_ingredients
from costing import cost_dish

db = SessionLocal()

dishes = db.query(Dish).all()

for dish in dishes:
    print(f"\n{dish.name} ({dish.category.value})")

    recipe = estimate_recipe(db, dish.name, dish.category)
    matched = match_recipe_ingredients(db, recipe)

    # clear any existing recipe first, same as save_recipe route does
    db.query(DishIngredient).filter(DishIngredient.dish_id == dish.id).delete()

    saved_count = 0
    skipped = []
    unit_mismatches = []

    for item in matched:
        if item.matched_ingredient_id is None:
            skipped.append(item.name)

        elif not item.units_agree:
            unit_mismatches.append(f"{item.name} (AI said {item.unit.value})")

        else:
            db.add(DishIngredient(
                dish_id=dish.id,
                ingredient_id=item.matched_ingredient_id,
                quantity=item.quantity
            ))
            saved_count += 1

    dish.skipped_ingredients = skipped + [m.split(" (")[0] for m in unit_mismatches]
    
    db.commit()

    if skipped:
        print(f"  Skipped (no ingredient match): {', '.join(skipped)}")

    if unit_mismatches:
        print(f"  Skipped (unit mismatch): {', '.join(unit_mismatches)}")

    plate_cost, margin_pounds, margin_percent = cost_dish(db, dish.id)
    print(f"  Saved {saved_count} ingredients — plate cost £{plate_cost}, margin £{margin_pounds} ({margin_percent}%)")

db.close()
print("\nDone.")