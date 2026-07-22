from database import SessionLocal
from matching import match_ingredient, suggest_ingredients

db = SessionLocal()

print(match_ingredient(db, "Butter"))       # should find your seeded row
print(match_ingredient(db, "nonexistent thing")) # should print None
print(suggest_ingredients(db, "puter"))       # typo — should suggest mozzarella