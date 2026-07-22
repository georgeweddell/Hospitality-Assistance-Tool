from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from costing import cost_dish
from database import Base, engine
import models
from fastapi import Depends
from sqlalchemy.orm import Session
from database import get_db
from schemas import DishCostOut, IngredientCreate, IngredientOut, DishType, DishCreate, DishOut
from models import Dish, Ingredient

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message":"Hello World"}

@app.get("/ingredients",  response_model=list[IngredientOut])
def list_ingredients(db: Session = Depends(get_db)):
    return db.query(Ingredient).all()

@app.post("/ingredients", response_model=IngredientOut)
def create_ingredient(ingredient: IngredientCreate, db: Session = Depends(get_db)):
    new_ingredient = Ingredient(
        name = ingredient.name,
        unit = ingredient.unit,
        price_per_unit = ingredient.price_per_unit)
    db.add(new_ingredient)
    db.commit()
    db.refresh(new_ingredient)

    return new_ingredient

@app.get("/dishes", response_model=list[DishOut])
def fetch_dish(db: Session = Depends(get_db)):
    return db.query(Dish).all()

@app.post("/dishes", response_model=DishOut)
def create_dish(dish: DishCreate, db: Session = Depends(get_db)):
    new_dish = Dish(**dish.model_dump())
    db.add(new_dish)
    db.commit()
    db.refresh(new_dish)

    return new_dish

@app.get("/dishes/{dish_id}/cost", response_model=DishCostOut)
def get_dish_cost(dish_id: int, db: Session = Depends(get_db)):
    plate_cost, margin_pounds, margin_percent = cost_dish(db, dish_id)
    return DishCostOut(
        plate_cost=plate_cost,
        margin_pounds=margin_pounds,
        margin_percent=margin_percent
    )