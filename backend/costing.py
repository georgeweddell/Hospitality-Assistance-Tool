from models import Dish, DishIngredient, Ingredient
from fastapi import HTTPException

def cost_dish(db, dish_id):
    recipe_rows = db.query(DishIngredient).filter(DishIngredient.dish_id == dish_id).all()
    plate_cost = 0
    for row in recipe_rows:
        ingredient = db.query(Ingredient).filter(Ingredient.id == row.ingredient_id).first()
        plate_cost += row.quantity * ingredient.price_per_unit
    
    dish = db.query(Dish).filter(Dish.id == dish_id).first()
    if dish is None:
        raise HTTPException(status_code= 404, detail="Dish not found")
    margin = dish.menu_price - plate_cost
    margin_percent = (margin/dish.menu_price) *100
    return round(plate_cost,2), round(margin,2), round(margin_percent,2)