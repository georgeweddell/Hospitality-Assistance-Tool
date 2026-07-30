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
    matches = get_close_matches(name, names, n=limit, cutoff=0.45)
    suggestions = []
    for match_name in matches:
        suggestions.append(match_ingredient(db, match_name))
    return suggestions 

def match_recipe_ingredients(db, recipe: schemas.RecipeDraft) -> list[schemas.MatchedIngredientDraft]:
    results = []
    for ingredient in recipe.ingredients:
        match = match_ingredient(db, ingredient.name)
        if match:
            matched_id = match.id
            suggestions = []
            units_agree = ingredient.unit == match.unit
        else:
            matched_id = None
            suggestions = [schemas.IngredientSuggestion(name = s.name,id = s.id) for s in suggest_ingredients(db, ingredient.name)]
            units_agree = True

        results.append(schemas.MatchedIngredientDraft(
            name=ingredient.name,
            quantity=ingredient.quantity,
            unit=ingredient.unit,
            matched_ingredient_id=matched_id,
            suggestions=suggestions,
            units_agree=units_agree,
        ))
    return results