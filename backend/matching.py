import models
import schemas
import database
from difflib import get_close_matches

def match_ingredient(db, name: str) -> models.Ingredient | None:
    ingredients = db.query(models.Ingredient).all()
    for ingredient in ingredients:
        if ingredient.name.strip().lower() == name.strip().lower():
            return(ingredient)
    return None

def suggest_ingredients(db, name: str, limit: int = 3) -> list[models.Ingredient]:
    ingredients = db.query(models.Ingredient).all()
    names = [ingredient.name for ingredient in ingredients]
    matches = get_close_matches(name, names, n=limit, cutoff=0.6)
    suggestions = []
    for match_name in matches:
        suggestions.append(match_ingredient(db, match_name))
    return suggestions 