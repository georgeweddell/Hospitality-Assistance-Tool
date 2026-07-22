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