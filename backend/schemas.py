from pydantic import BaseModel, Field, model_validator
from models import UnitType, DishType, QuadrantType, PriceSource, MenuPriceSource, ImportKind, ImportStatus
from typing import Literal, Optional
from datetime import datetime
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
    # When a changed menu_price starts (default today). The old price is kept
    # for the days before, so past periods are still analysed at what was charged.
    price_from: Optional[date] = None

class MenuPriceOut(BaseModel):
    id: int
    price: float
    source: MenuPriceSource
    effective_date: date

    class Config:
        from_attributes = True

class DishOut(BaseModel):
    id: int
    name: str
    menu_price: float
    category: Optional[DishType] = None
    on_menu_from: date
    on_menu_until: Optional[date] = None
    description: Optional[str] = None
    recipe_check: bool = False

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
    description: Optional[str] = None
    recipe_check: bool = False
    skipped_ingredients: list[str] = []
    prices: list[MenuPriceOut]   # newest first
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

class PriceChangeDishOut(BaseModel):
    dish_id: int
    name: str
    per_plate: float

class PriceChangeOut(BaseModel):
    """An ingredient price change (price_changes.py); prices per base unit, like everywhere."""
    ingredient_id: int
    name: str
    unit: UnitType
    day: date
    old_price: float
    new_price: float
    source: str
    supplier: Optional[str] = None
    change_percent: float
    is_alert: bool                 # a rise of price_changes.ALERT_PERCENT or more
    after_period: bool             # dated after the chosen period ended
    dishes: list[PriceChangeDishOut]
    period_effect: float           # £ change in contribution at the period's plates sold

class MenuPriceChangeOut(BaseModel):
    dish_id: int
    name: str
    day: date
    old_price: float
    new_price: float

class BusinessIn(BaseModel):
    restaurant_type: Literal["pizzeria", "gastropub", "cafe", "indian", "other"]

class ReportIn(BaseModel):
    """Starting a report: an optional focus or question from the owner."""
    focus: Optional[str] = Field(default=None, max_length=500)

class ActionItemOut(BaseModel):
    dish_id: int
    dish_name: str
    quadrant: QuadrantType
    action: str
    impact_pounds: float
    # The concrete change (menu_engineering.proposed_change). Plowhorse and Dog:
    # the margin gap per plate at today's price, and the price that closes it.
    # Puzzle: the extra plates over the period to reach the popularity line.
    current_price: Optional[float] = None
    margin_gap: Optional[float] = None       # £ per plate: a price rise, or a plate-cost cut
    target_price: Optional[float] = None     # current_price + margin_gap
    extra_units: Optional[int] = None
    extra_per_day: Optional[float] = None

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
    # Dishes on the menu still without a recipe, in menu order: the setup
    # page's Recipes step works through them one at a time.
    needs_recipe: list[int] = []
    unchecked_recipes: int = 0   # AI estimates saved in bulk, not yet checked by the owner
    own_cost_share: Optional[float] = None   # % of the menu's recipe cost on own prices (own_prices.menu_own_share)

class ResetIn(BaseModel):
    mode: Literal["fresh", "demo"]
    confirm: str   # must be "reset": guards against wiping the database by accident

class BenchmarkSyncOut(BaseModel):
    """What updating the benchmark list changed."""
    added: int
    updated: int
    unchanged: int
    conflicts: list[str]   # names whose unit disagrees with the list, left alone


# --- Invoice import ------------------------------------------------------------------

PackUnit = Literal["kg", "g", "l", "ml", "each"]
LineKind = Literal["food", "non_food", "charge"]
LineAction = Literal["update", "new", "ignore"]

class InvoiceLineDraft(BaseModel):
    """One invoice line as Claude read it. Numbers exactly as printed; code does the maths."""
    description: str                           # as printed, e.g. "MOZZ FDL 1KG x12"
    pack_count: Optional[float] = None         # "12 x 1kg" -> 12
    pack_size: Optional[float] = None          # "12 x 1kg" -> 1
    pack_unit: Optional[PackUnit] = None       # "12 x 1kg" -> "kg"
    quantity: Optional[float] = None           # packs bought
    unit_price: Optional[float] = None         # price per pack, ex VAT
    line_total: Optional[float] = None         # ex VAT
    kind: LineKind = "food"
    likely_ingredient: Optional[str] = None    # Claude's guess, from the ingredient list where possible

class InvoiceDraft(BaseModel):
    supplier: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    prices_include_vat: bool = False
    lines: list[InvoiceLineDraft]

class InvoiceReviewLine(InvoiceLineDraft):
    """A line ready for the owner to check, with what code worked out."""
    action: LineAction
    ingredient_id: Optional[int] = None        # for "update"
    remembered: bool = False                   # the match (or ignore) came from a previous invoice
    suggestions: list["IngredientSuggestion"] = []
    new_ingredient_name: Optional[str] = None  # for "new"
    price_per_unit: Optional[float] = None     # per g / ml / each
    current_price_per_unit: Optional[float] = None
    change_percent: Optional[float] = None
    flags: list[Literal["totals", "pack", "unit", "big_change"]] = []

class InvoiceReviewOut(BaseModel):
    supplier: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    prices_include_vat: bool = False
    already_imported: Optional[int] = None     # id of an applied import of the same invoice
    filename: Optional[str] = None
    file_hash: Optional[str] = None
    lines: list[InvoiceReviewLine]

class InvoiceApplyLine(BaseModel):
    """A line as the owner confirmed it. The price is worked out again on the server."""
    description: str
    action: LineAction
    ingredient_id: Optional[int] = None
    new_ingredient_name: Optional[str] = None
    pack_count: Optional[float] = None
    pack_size: Optional[float] = None
    pack_unit: Optional[PackUnit] = None
    unit_price: Optional[float] = None

class InvoiceApplyIn(BaseModel):
    supplier: str = Field(min_length=1)
    invoice_number: str = Field(min_length=1)
    invoice_date: date
    filename: Optional[str] = None
    file_hash: Optional[str] = None
    lines: list[InvoiceApplyLine]

class ImportOut(BaseModel):
    id: int
    kind: ImportKind
    filename: Optional[str] = None
    supplier: Optional[str] = None
    reference: Optional[str] = None
    effective_date: date
    period_end: Optional[date] = None
    status: ImportStatus
    lines_applied: int
    lines_ignored: int
    created_at: datetime

    class Config:
        from_attributes = True


# --- Till (sales) import -------------------------------------------------------------

# The date formats a till export can use. Claude picks one; code does the parsing.
DateFormat = Literal["%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y"]

class TillMappingIn(BaseModel):
    """Which column is which in a till export (column names as in its header row)."""
    date_column: str = Field(min_length=1)
    item_column: str = Field(min_length=1)
    quantity_column: str = Field(min_length=1)
    date_format: DateFormat
    refund_column: Optional[str] = None     # a column marking refunds, if any
    refund_value: Optional[str] = None      # the value in it that means "refund", e.g. "Refund"

    class Config:
        from_attributes = True

class TillItemChoice(BaseModel):
    item: str                               # the till's item name, as in the file
    action: Literal["dish", "ignore"]
    dish_id: Optional[int] = None

class TillItemHint(BaseModel):
    """Claude's suggestion for one till item name."""
    item: str
    kind: Literal["dish", "other"] = "dish"   # "other": drinks, add-ons, service charges
    likely_dish: Optional[str] = None         # a dish name from the menu, exactly as written

class SalesReviewIn(BaseModel):
    file_hash: str
    filename: Optional[str] = None
    mapping: Optional[TillMappingIn] = None   # None: the remembered mapping for this layout
    choices: list[TillItemChoice] = []        # the owner's changes; items not listed use the defaults

class DishSuggestion(BaseModel):
    id: int
    name: str

class SalesItemOut(BaseModel):
    item: str
    units: int                                # net units across the file
    days: int                                 # days it sold on
    action: Literal["dish", "ignore"]
    dish_id: Optional[int] = None
    remembered: bool = False
    kind: Literal["dish", "other"] = "dish"
    suggestions: list[DishSuggestion] = []
    conflict_days: int = 0                    # days skipped: sales already entered another way
    replace_days: int = 0                     # days replacing an earlier till import
    flags: list[Literal["choose", "off_menu", "conflict", "replaces"]] = []

class SalesReviewOut(BaseModel):
    file_hash: str
    filename: Optional[str] = None
    header: list[str]
    samples: list[list[str]]                  # the first rows, to help choose columns
    mapping: Optional[TillMappingIn] = None
    mapping_remembered: bool = False
    already_imported: Optional[int] = None
    rows: int = 0
    skipped: dict[str, int] = {}              # reason -> rows skipped
    first_date: Optional[date] = None
    last_date: Optional[date] = None
    units: int = 0                            # units that will be saved
    dish_days: int = 0                        # daily totals that will be saved
    replace_days: int = 0
    conflict_days: int = 0
    items: list[SalesItemOut] = []
    ai_unavailable: bool = False              # Claude couldn't be reached: columns chosen by hand

class SalesApplyIn(BaseModel):
    file_hash: str
    filename: Optional[str] = None
    mapping: TillMappingIn
    choices: list[TillItemChoice]

class TillColumnsDraft(BaseModel):
    """Claude's proposed column mapping. Checked against the file before use (till_ai.py)."""
    date_column: Optional[str] = None
    item_column: Optional[str] = None
    quantity_column: Optional[str] = None
    date_format: Optional[DateFormat] = None
    refund_column: Optional[str] = None
    refund_value: Optional[str] = None

class TillItemHints(BaseModel):
    items: list[TillItemHint]


# --- Menu import ---------------------------------------------------------------------

class MenuItemDraft(BaseModel):
    """One item as Claude read it off the menu. Sizes are separate items."""
    name: str
    price: Optional[float] = None
    section: Optional[str] = None             # the menu's own heading, e.g. "Pizze Rosse"
    category: Optional[DishType] = None       # Claude's mapping of the section
    description: Optional[str] = None
    kind: Literal["dish", "other"] = "dish"   # "other": drinks, set menus, add-ons
    likely_existing: Optional[str] = None     # a stored dish this is probably a renamed version of

class MenuDraft(BaseModel):
    items: list[MenuItemDraft]

class MenuReviewItem(MenuItemDraft):
    """A menu item compared with what's stored."""
    status: Literal["new", "same", "price", "renamed", "returning", "not_a_dish"]
    action: Optional[Literal["match", "new", "ignore"]] = None   # None: the owner must choose
    dish_id: Optional[int] = None             # the stored dish it is ("match") or might be ("renamed")
    copy_from: Optional[int] = None           # a returning dish: copy this old dish's recipe
    current_name: Optional[str] = None
    current_price: Optional[float] = None
    current_category: Optional[DishType] = None
    description_changed: bool = False
    remembered: bool = False                  # ignored because the owner ignored it before
    suggestions: list[DishSuggestion] = []

class MenuLeavingOut(BaseModel):
    """A dish on the menu now that isn't on the new one."""
    dish_id: int
    name: str
    category: Optional[DishType] = None
    price: Optional[float] = None

class MenuReviewOut(BaseModel):
    filename: Optional[str] = None
    file_hash: Optional[str] = None
    start_date: date
    already_imported: Optional[int] = None
    latest_sale: Optional[date] = None        # a start date on or before this changes past analysis
    items: list[MenuReviewItem]
    leaving: list[MenuLeavingOut]

class MenuApplyItem(BaseModel):
    name: str
    price: Optional[float] = None
    category: Optional[DishType] = None
    description: Optional[str] = None
    action: Literal["match", "new", "ignore"]
    dish_id: Optional[int] = None             # for "match"
    copy_from: Optional[int] = None           # for a returning dish

class MenuApplyIn(BaseModel):
    filename: Optional[str] = None
    file_hash: Optional[str] = None
    start_date: date
    items: list[MenuApplyItem]
    take_off: list[int] = []                  # dishes to take off the menu from start_date

class MenuReviewIn(BaseModel):
    """Compare a menu Claude has already read again, e.g. for a different start date."""
    items: list[MenuItemDraft]
    start_date: date
    filename: Optional[str] = None
    file_hash: Optional[str] = None


# --- Recipes table -------------------------------------------------------------------

class RecipeRowOut(BaseModel):
    """One dish in the Recipes table (Setup and the Menu page's Recipes tab)."""
    dish_id: int
    name: str
    category: Optional[DishType] = None
    menu_price: float
    status: Literal["none", "checked", "ai_unchecked"]
    lines: int
    plate_cost: Optional[float] = None
    food_cost_percent: Optional[float] = None   # plate cost as a % of the menu price
    checks: list[Literal["food_cost_high", "food_cost_low", "big_line", "few_ingredients", "left_out", "unit"]] = []
    recipe_check: bool = False                  # the menu description changed (menu import)
    own_share_percent: Optional[float] = None   # % of the plate cost from the restaurant's own prices (own_prices.py)


# --- Sales money (Sales page) -------------------------------------------------------------

class SalesByDayOut(BaseModel):
    day: date
    sales: float    # £, at the menu price charged that day (VAT included)
    units: float

class SalesByCategoryOut(BaseModel):
    category: Optional[DishType] = None
    sales: float
    units: float

class SalesByDishOut(BaseModel):
    dish_id: int
    name: str
    category: Optional[DishType] = None
    sales: float
    units: float

class SalesSummaryOut(BaseModel):
    start: date
    end: date
    total_sales: float
    total_units: float
    days: list[SalesByDayOut]              # every day in the period, including days with no sales
    categories: list[SalesByCategoryOut]   # highest sales first
    dishes: list[SalesByDishOut]           # highest sales first
