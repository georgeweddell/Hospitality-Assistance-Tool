from database import SessionLocal
from recipe_ai import estimate_recipe
from matching import match_recipe_ingredients
from models import DishType

db = SessionLocal()

recipe = estimate_recipe("Margherita Pizza", DishType.MAIN)
matched = match_recipe_ingredients(db, recipe)

for m in matched:
    print(m)