from database import SessionLocal
from models import Ingredient

db = SessionLocal()
for i in db.query(Ingredient).all():
    print(i.name)