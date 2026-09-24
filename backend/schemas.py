from pydantic import BaseModel, Field, model_validator
from models import UnitType, DishType, QuadrantType, PriceSource
from typing import Literal, Optional
from datetime import date

class PriceInput(BaseModel):
    """
    A price, given either way:
      - as it appears on an invoice: pack_price for pack_quantity pack_unit
        (e.g. 93.60 for 12 kg), converted to a base-unit price by units.py, or
      - directly as price_per_unit (per gram / ml / each).
    Exactly one of the two must be given.
    """
    price_per_unit: Optional[float] = Field(default=None, ge=0)
    pack_price: Optional[float] = Field(default=None, ge=0)
    pack_quantity: Optional[float] = Field(default=None, gt=0)
    pack_unit: Optional[Literal["kg", "g", "l", "ml", "each"]] = None
    source: PriceSource = PriceSource.MANUAL
    supplier: Optional[str] = None

    @model_validator(mode="after")
    def one_way_of_giving_the_price(self):
        pack_fields = [self.pack_price, self.pack_quantity, self.pack_unit]
        has_pack = all(f is not None for f in pack_fields)
        if any(f is not None for f in pack_fields) and not has_pack:
            raise ValueError("A pack price needs pack_price, pack_quantity and pack_unit")
        if has_pack == (self.price_per_unit is not None):
            raise ValueError("Give either price_per_unit or a pack price, not both or neither")
        return self

class IngredientCreate(PriceInput):
    name: str = Field(min_length=1)
    unit: UnitType   # the base unit the ingredient is measured in

class IngredientOut(BaseModel):
    id: int
    name: str
    unit: UnitType
    # The price costing currently uses (see costing.best_price). None if it has no price.
    price_per_unit: Optional[float] = None
    price_source: Optional[PriceSource] = None
    price_date: Optional[date] = None
    used_in: int = 0   # number of dishes whose recipe uses it

class IngredientPriceCreate(PriceInput):
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
    name: str = Field(min_length=1)
    menu_price: float = Field(gt=0)
    category: Optional[DishType] = None
    on_menu_from: date = Field(default_factory=date.today)
    on_menu_until: Optional[date] = None   # None = still on the menu

    @model_validator(mode="after")
    def until_not_before_from(self):
        if self.on_menu_until is not None and self.on_menu_until < self.on_menu_from:
            raise ValueError("A dish can't come off the menu before it goes on")
        return self

class DishUpdate(DishCreate):
    pass

class DishOut(BaseModel):
    id: int
    name: str
    menu_price: float
    category: Optional[DishType] = None
    on_menu_from: date
    on_menu_until: Optional[date] = None

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
    quantity: float = Field(gt=0)   # in the ingredient's base unit (g / ml / each)

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

class RecipeLineOut(BaseModel):
    ingredient_id: int
    name: str
    unit: UnitType
    quantity: float
    price_per_unit: float
    price_source: PriceSource
    line_cost: float

class DishDetailOut(BaseModel):
    """Everything the dish page needs, in one call. units_sold is for the requested range."""
    id: int
    name: str
    menu_price: float
    category: Optional[DishType] = None
    on_menu_from: date
    on_menu_until: Optional[date] = None
    skipped_ingredients: list[str] = []
    lines: list[RecipeLineOut]
    cost: DishCostOut
    units_sold: int

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
class SalesCoverageOut(BaseModel):
    """What sales data exists, overall and inside a range."""
    first_date: Optional[date] = None      # earliest sale on record (any range)
    last_date: Optional[date] = None       # latest sale on record (any range)
    start: date                            # the range this describes
    end: date
    days_with_sales: list[date]            # days in the range covered by at least one record
    partial_records: int                   # records only partly inside the range, so not counted

class SalesEntryIn(BaseModel):
    dish_id: int
    units_sold: Optional[int] = Field(default=None, ge=0)   # None = remove this dish's total for the period

class SalesEntryOut(BaseModel):
    dish_id: int
    dish_name: str
    category: Optional[DishType] = None
    units_sold: Optional[int] = None       # the total entered for exactly this period, if any
    other_records: int                     # other records inside the period (e.g. daily till data)

class SetupStatusOut(BaseModel):
    """What a restaurant has entered so far (dishes currently on the menu)."""
    dishes: int
    dishes_with_recipe: int
    dishes_with_category: int
    ingredients_in_use: int
    ingredients_with_own_price: int
    has_sales: bool

class ResetIn(BaseModel):
    mode: Literal["fresh", "demo"]
    confirm: str   # must be "reset": guards against wiping the database by accident
