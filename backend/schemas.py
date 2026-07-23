from pydantic import BaseModel
from models import UnitType, DishType
from typing import Optional

class IngredientCreate(BaseModel):
    name: str
    unit: UnitType
    price_per_unit: float

class IngredientOut(BaseModel):
    id: int
    name: str
    unit: UnitType
    price_per_unit: float

    class Config:
        from_attributes = True  # lets this schema read straight off a SQLAlchemy object

class DishCreate(BaseModel):
    name: str
    menu_price: float
    category: Optional[DishType] = None

class DishOut(BaseModel):
    id: int
    name: str
    menu_price: float
    category: Optional[DishType] = None

    class Config:
        from_attributes = True

class DishCostOut(BaseModel):
    plate_cost: float
    margin_pounds: float
    margin_percent: float

class RecipeIngredientDraft(BaseModel):
    name: str
    quantity: float
    unit: UnitType

class RecipeDraft(BaseModel):
    dish_name: str
    ingredients: list[RecipeIngredientDraft]

class IngredientSuggestion(BaseModel):
    id: int
    name: str

class MatchedIngredientDraft(BaseModel):
    name: str
    quantity: float
    unit: UnitType
    matched_ingredient_id: int | None
    suggestions: list[IngredientSuggestion]

class ConfirmedIngredient(BaseModel):
    ingredient_id: int
    quantity: float

class RecipeConfirm(BaseModel):
    ingredients: list[ConfirmedIngredient]

class DishIngredientOut(BaseModel):
    ingredient_id: int
    quantity: float

    class Config:
        from_attributes = True

class RecipeSaveOut(BaseModel):
    ingredients: list[DishIngredientOut]
    cost: DishCostOut