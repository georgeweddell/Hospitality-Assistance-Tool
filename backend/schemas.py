from pydantic import BaseModel, Field
from models import UnitType, DishType, QuadrantType, PriceSource
from typing import Optional
from datetime import date

class IngredientCreate(BaseModel):
    name: str
    unit: UnitType
    price_per_unit: float = Field(ge=0)   # starting price, per gram / ml / each
    source: PriceSource = PriceSource.MANUAL
    supplier: Optional[str] = None

class IngredientOut(BaseModel):
    id: int
    name: str
    unit: UnitType
    # The price costing currently uses (see costing.best_price). None if it has no price.
    price_per_unit: Optional[float] = None
    price_source: Optional[PriceSource] = None
    price_date: Optional[date] = None

class IngredientPriceCreate(BaseModel):
    price_per_unit: float = Field(ge=0)   # per gram / ml / each, like the ingredient's unit
    source: PriceSource = PriceSource.MANUAL
    supplier: Optional[str] = None
    effective_date: date = Field(default_factory=date.today)

class IngredientPriceOut(BaseModel):
    id: int
    ingredient_id: int
    price_per_unit: float
    source: PriceSource
    supplier: Optional[str] = None
    effective_date: date

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
    units_agree: bool = True

class ConfirmedIngredient(BaseModel):
    ingredient_id: int
    quantity: float

class RecipeConfirm(BaseModel):
    ingredients: list[ConfirmedIngredient]
    skipped_ingredients: list[str] = []

class DishIngredientOut(BaseModel):
    ingredient_id: int
    quantity: float

    class Config:
        from_attributes = True

class RecipeSaveOut(BaseModel):
    ingredients: list[DishIngredientOut]
    cost: DishCostOut

class SalesRecordCreate(BaseModel):
    units_sold: int
    period_start: date
    period_end: date

class SalesRecordOut(BaseModel):
    id: int
    dish_id: int
    units_sold: int
    period_start: date
    period_end: date

    class Config:
        from_attributes = True 

class DishClassificationOut(BaseModel):
    dish_id: int
    dish_name: str
    category: Optional[DishType] = None
    menu_price: float
    plate_cost: float
    margin_pounds: float
    margin_percent: float
    units_sold: int
    menu_mix_percent: float
    popularity_threshold: float
    profitability_threshold: float
    quadrant: QuadrantType
    skipped_ingredients: list[str] = []

class ActionItemOut(BaseModel):
    dish_id: int
    dish_name: str
    quadrant: QuadrantType
    action: str
    impact_pounds: float

class IncompleteDishOut(BaseModel):
    dish_id: int
    dish_name: str
    category: Optional[DishType] = None
    reasons: list[str]