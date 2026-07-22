from database import SessionLocal
from models import Dish, Ingredient, UnitType, DishIngredient, DishType
from models import User

db = SessionLocal()

margherita = Dish(name="Margherita", menu_price=10.00, category=DishType.MAIN)
db.add(margherita)
db.commit()

flour = db.query(Ingredient).filter(Ingredient.name == "00 flour").first()
assert flour is not None, "flour not found"
basil = db.query(Ingredient).filter(Ingredient.name == "fresh basil").first()
assert basil is not None, "basil not found"
tomatoes = db.query(Ingredient).filter(Ingredient.name == "san marzano tomatoes").first()
assert tomatoes is not None, "tomatoes not found"
mozzarella = db.query(Ingredient).filter(Ingredient.name == "mozzarella (fior di latte)").first()
assert mozzarella is not None, "mozzarella not found"

db.add(DishIngredient(dish_id=margherita.id, ingredient_id=flour.id, quantity=250))
db.add(DishIngredient(dish_id=margherita.id, ingredient_id=basil.id, quantity=5))
db.add(DishIngredient(dish_id=margherita.id, ingredient_id=tomatoes.id, quantity=100))
db.add(DishIngredient(dish_id=margherita.id, ingredient_id=mozzarella.id, quantity=150))
db.commit()