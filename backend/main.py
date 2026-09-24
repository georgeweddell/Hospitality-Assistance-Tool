from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from menu_engineering import classify_all_dishes, build_action_list, list_incomplete_dishes
from costing import cost_dish, best_price
from database import Base, engine
import models
import schemas
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from schemas import DishClassificationOut, DishCostOut, IngredientCreate, IngredientOut, IngredientPriceCreate, IngredientPriceOut, DishType, DishCreate, DishOut, MatchedIngredientDraft, RecipeSaveOut, SalesRecordCreate, SalesRecordOut, ActionItemOut, IncompleteDishOut
from models import Dish, DishIngredient, Ingredient, IngredientPrice, SalesRecord
from recipe_ai import estimate_recipe
from matching import match_recipe_ingredients
from datetime import date
import anthropic


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

def ingredient_out(db, ingredient):
    """An ingredient with the price costing currently uses for it."""
    price = best_price(db, ingredient.id)
    return IngredientOut(
        id=ingredient.id,
        name=ingredient.name,
        unit=ingredient.unit,
        price_per_unit=price.price_per_unit if price else None,
        price_source=price.source if price else None,
        price_date=price.effective_date if price else None,
    )

@app.get("/ingredients",  response_model=list[IngredientOut])
def list_ingredients(db: Session = Depends(get_db)):
    return [ingredient_out(db, i) for i in db.query(Ingredient).all()]

@app.post("/ingredients", response_model=IngredientOut)
def create_ingredient(ingredient: IngredientCreate, db: Session = Depends(get_db)):
    # Every ingredient starts with a price, so costing never meets one without.
    new_ingredient = Ingredient(
        name = ingredient.name,
        unit = ingredient.unit)
    db.add(new_ingredient)
    db.flush()  # assigns new_ingredient.id without committing yet

    db.add(IngredientPrice(
        ingredient_id = new_ingredient.id,
        price_per_unit = ingredient.price_per_unit,
        source = ingredient.source,
        supplier = ingredient.supplier,
        effective_date = date.today()))
    db.commit()

    return ingredient_out(db, new_ingredient)

@app.get("/ingredients/{ingredient_id}/prices", response_model=list[IngredientPriceOut])
def list_ingredient_prices(ingredient_id: int, db: Session = Depends(get_db)):
    ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    return (db.query(IngredientPrice)
            .filter(IngredientPrice.ingredient_id == ingredient_id)
            .order_by(IngredientPrice.effective_date.desc(), IngredientPrice.id.desc())
            .all())

@app.post("/ingredients/{ingredient_id}/prices", response_model=IngredientPriceOut)
def add_ingredient_price(ingredient_id: int, price: IngredientPriceCreate, db: Session = Depends(get_db)):
    ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    new_price = IngredientPrice(ingredient_id=ingredient_id, **price.model_dump())
    db.add(new_price)
    db.commit()
    db.refresh(new_price)

    return new_price

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

@app.post("/dishes/{dish_id}/estimate-recipe", response_model=list[MatchedIngredientDraft])
def estimate_recipe_route(dish_id: int, db: Session = Depends(get_db)):
    dish = db.query(Dish).filter(Dish.id == dish_id).first()
    if not dish:
        raise HTTPException(status_code=404, detail="Dish not found")

    try:
        recipe = estimate_recipe(db, dish.name, dish.category)
    except anthropic.APIConnectionError:
        # Never reached Anthropic: no internet, DNS failure, or timeout.
        raise HTTPException(status_code=503, detail="Couldn't reach the AI recipe service. Check your internet connection and try again.")
    except anthropic.APIStatusError as e:
        # Reached Anthropic, but it returned an error (bad API key, rate limit, overloaded).
        raise HTTPException(status_code=502, detail=f"The AI recipe service returned an error ({e.status_code}). Try again in a moment.")
    matched = match_recipe_ingredients(db, recipe)
    return matched

@app.post("/dishes/{dish_id}/recipe", response_model=RecipeSaveOut)
def save_recipe(dish_id: int, confirmed: schemas.RecipeConfirm, db: Session = Depends(get_db)):
    dish = db.query(Dish).filter(Dish.id == dish_id).first()
    if not dish:
        raise HTTPException(status_code=404, detail="Dish not found")
    recipe = []

    dish.skipped_ingredients = confirmed.skipped_ingredients

    db.query(models.DishIngredient).filter(models.DishIngredient.dish_id == dish_id).delete()

    for item in confirmed.ingredients:
        confirmed_ingredient = DishIngredient(dish_id=dish_id, ingredient_id=item.ingredient_id, quantity=item.quantity)
        recipe.append(confirmed_ingredient)
        db.add(confirmed_ingredient)
    db.commit()

    plate_cost, margin_pounds, margin_percent = cost_dish(db, dish_id)
    cost_out = DishCostOut(
            plate_cost=plate_cost,
            margin_pounds=margin_pounds,
            margin_percent=margin_percent
        )
    return RecipeSaveOut(
        ingredients = recipe,
        cost = cost_out
    )

@app.post("/dishes/{dish_id}/sales", response_model=SalesRecordOut)
def save_sales_record(sales: SalesRecordCreate, dish_id: int, db: Session = Depends(get_db)):
    dish = db.query(Dish).filter(Dish.id == dish_id).first()
    if not dish:
        raise HTTPException(status_code=404, detail="Dish not found")

    new_sales_record = SalesRecord(
        dish_id = dish_id,
        units_sold = sales.units_sold,
        period_start= sales.period_start,
        period_end = sales.period_end
    )
    db.add(new_sales_record)
    db.commit()
    db.refresh(new_sales_record)

    return new_sales_record

@app.get("/dishes/{dish_id}/sales", response_model=list[SalesRecordOut])
def get_sales_record(dish_id: int, db: Session = Depends(get_db)):
    dish = db.query(Dish).filter(Dish.id == dish_id).first()
    if not dish:
        raise HTTPException(status_code=404, detail="Dish not found")

    sales_record = db.query(SalesRecord).filter(SalesRecord.dish_id == dish_id).all()
    return sales_record

@app.get("/dishes/classifications", response_model=list[DishClassificationOut])
def get_dish_classifications(db: Session = Depends(get_db)):
    return classify_all_dishes(db)

@app.get("/dishes/action-list", response_model=list[ActionItemOut])
def get_action_list(db: Session = Depends(get_db)):
    return build_action_list(db)

@app.get("/dishes/incomplete", response_model=list[IncompleteDishOut])
def get_incomplete_dishes(db: Session = Depends(get_db)):
    return list_incomplete_dishes(db)