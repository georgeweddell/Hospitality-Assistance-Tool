from database import SessionLocal
from models import Dish, DishIngredient, Ingredient

db = SessionLocal()

dish = db.query(Dish).filter(Dish.name == "Margherita").first()
print(f"{dish.name} — £{dish.menu_price} — {dish.category}")

recipe = db.query(DishIngredient).filter(DishIngredient.dish_id == dish.id).all()
for row in recipe:
    ingredient = db.query(Ingredient).filter(Ingredient.id == row.ingredient_id).first()
    print(f"  {row.quantity}{ingredient.unit.value} {ingredient.name}")