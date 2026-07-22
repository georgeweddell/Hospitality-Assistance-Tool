from database import SessionLocal
from models import Dish
from costing import cost_dish

db = SessionLocal()

dish = db.query(Dish).filter(Dish.name == "Margherita").first()
plate_cost, margin, margin_percent = cost_dish(db, dish.id)

print(f"Plate cost: £{plate_cost}")
print(f"Margin: £{margin}")
print(f"Margin %: {margin_percent}%")