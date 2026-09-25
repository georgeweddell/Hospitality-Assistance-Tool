import enum
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float, Enum, Date, DateTime, JSON
from database import Base
from datetime import date, datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=True)  # unused until Phase 6 — real login isn't built yet

class UnitType(enum.Enum):
    GRAM = "gram"   # base unit for anything by mass
    ML = "ml"       # base unit for anything by volume
    EACH = "each"   # base unit for countable things (1 egg, 1 lemon)

class ImportKind(enum.Enum):
    INVOICE = "invoice"
    SALES = "sales"   # step 7c
    MENU = "menu"     # step 7d

class ImportStatus(enum.Enum):
    APPLIED = "applied"
    UNDONE = "undone"

class Import(Base):
    # One uploaded file that was reviewed and applied. Every row it created
    # carries its id, so it can be traced and (for invoices and sales) undone.
    __tablename__ = "imports"
    id = Column(Integer, primary_key=True)
    kind = Column(Enum(ImportKind), nullable=False)
    filename = Column(String, nullable=True)
    file_hash = Column(String, nullable=True)     # SHA-256 of the file; the copy is uploads/<hash>.<ext>
    supplier = Column(String, nullable=True)
    reference = Column(String, nullable=True)     # e.g. the invoice number
    effective_date = Column(Date, nullable=False) # e.g. the invoice date; for sales, the first day
    period_end = Column(Date, nullable=True)      # for sales: the last day the file covers
    status = Column(Enum(ImportStatus), nullable=False, default=ImportStatus.APPLIED)
    lines_applied = Column(Integer, nullable=False, default=0)
    lines_ignored = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

class Ingredient(Base):
    __tablename__ = "ingredients"
    id = Column(Integer, primary_key = True)
    name = Column(String, nullable=False)
    unit = Column(Enum(UnitType), nullable=False)
    import_id = Column(Integer, ForeignKey(Import.id), nullable=True)   # set if an import created it
    # Prices live in IngredientPrice, one row per price seen, never overwritten.

class PriceSource(enum.Enum):
    INVOICE = "invoice"              # from the restaurant's own invoice
    SUPPLIER_LIST = "supplier_list"  # from a supplier's price list
    MANUAL = "manual"                # typed in by the restaurant
    BENCHMARK = "benchmark"          # built-in estimate, used until the restaurant has its own

# The restaurant's own prices beat benchmarks (see costing.best_price).
OWN_PRICE_SOURCES = [PriceSource.INVOICE, PriceSource.SUPPLIER_LIST, PriceSource.MANUAL]

class IngredientPrice(Base):
    __tablename__ = "ingredient_prices"
    id = Column(Integer, primary_key=True)
    ingredient_id = Column(Integer, ForeignKey(Ingredient.id), nullable=False)
    price_per_unit = Column(Float, nullable=False)   # per gram / ml / each, like the ingredient's unit
    source = Column(Enum(PriceSource), nullable=False)
    supplier = Column(String, nullable=True)
    effective_date = Column(Date, nullable=False)
    import_id = Column(Integer, ForeignKey(Import.id), nullable=True)   # set if it came from an import

class SupplierAlias(Base):
    # A remembered match: this supplier's invoice line description means this
    # ingredient (or: ignore it). Pre-filled on the next invoice, still reviewable.
    # supplier and description are stored normalised (invoices.normalise).
    __tablename__ = "supplier_aliases"
    id = Column(Integer, primary_key=True)
    supplier = Column(String, nullable=False)
    description = Column(String, nullable=False)
    ingredient_id = Column(Integer, ForeignKey(Ingredient.id), nullable=True)   # None when ignore is True
    ignore = Column(Boolean, nullable=False, default=False)

class RecipeStatus(enum.Enum):
    CHECKED = "checked"             # entered, or checked, by the owner
    AI_UNCHECKED = "ai_unchecked"   # estimated by AI in bulk and saved, not yet checked

class DishType(enum.Enum):
    STARTER = "Starter"
    SIDE = "Side"
    MAIN = "Main"
    DESSERT = "Dessert"
    
class Dish(Base):
    __tablename__ = "dishes"
    id = Column(Integer, primary_key=True)
    venue_id = Column(Integer, nullable=True)
    name = Column(String, nullable=False)
    # Menu prices live in MenuPrice, one row per price, never overwritten.
    category = Column(Enum(DishType))
    skipped_ingredients = Column(JSON, nullable=False, default=list)
    # When the dish is on the menu. A dish on the menu with no sales recorded
    # has genuinely sold 0; outside these dates it simply isn't analysed.
    on_menu_from = Column(Date, nullable=False, default=date.today)
    on_menu_until = Column(Date, nullable=True)   # None = still on the menu
    description = Column(String, nullable=True)   # as on the menu; helps recipe estimates
    # Set when a menu import finds the description has changed; cleared when the
    # recipe is next saved. Only a reminder: the dish stays in the analysis.
    recipe_check = Column(Boolean, nullable=False, default=False)
    # Who the saved recipe comes from (None: no recipe yet). Bulk AI estimates are
    # saved as AI_UNCHECKED and still count in the analysis; the Recipes table
    # flags them until the owner saves or confirms them (CHECKED).
    recipe_status = Column(Enum(RecipeStatus), nullable=True)
    import_id = Column(Integer, ForeignKey(Import.id), nullable=True)   # set if a menu import created it

class MenuPriceSource(enum.Enum):
    MANUAL = "manual"   # typed in on the Menu or dish page
    MENU = "menu"       # read from an uploaded menu (step 7d)

class MenuPrice(Base):
    # A dish's price from effective_date until the next MenuPrice for it.
    # Kept as history so a period spanning a price change is analysed at the
    # price actually charged on each day (costing.average_menu_price).
    __tablename__ = "menu_prices"
    id = Column(Integer, primary_key=True)
    dish_id = Column(Integer, ForeignKey(Dish.id), nullable=False)
    price = Column(Float, nullable=False)
    source = Column(Enum(MenuPriceSource), nullable=False)
    effective_date = Column(Date, nullable=False)
    import_id = Column(Integer, ForeignKey(Import.id), nullable=True)   # set if it came from a menu import

class MenuIgnoredItem(Base):
    # A menu item the owner chose to ignore (a drink, set menu, add-on), so the
    # next menu import starts it as ignored. Stored normalised (invoices.normalise).
    __tablename__ = "menu_ignored_items"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)

class DishIngredient(Base):
    __tablename__ = "dish_ingredients"
    id = Column(Integer, primary_key=True)
    dish_id = Column(Integer, ForeignKey(Dish.id), nullable=False)
    ingredient_id = Column(Integer, ForeignKey(Ingredient.id), nullable=False)
    quantity = Column(Float, nullable=False)
    # An AI line given in a different unit from the ingredient's (e.g. grams of
    # egg): the quantity is kept as given, and flagged until the recipe is checked.
    unit_check = Column(Boolean, nullable=False, default=False)

class SalesRecord(Base):
    __tablename__ = "sales_records"
    id = Column(Integer, primary_key=True)
    dish_id = Column(Integer, ForeignKey(Dish.id), nullable=False)
    units_sold = Column(Integer, nullable=False)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    import_id = Column(Integer, ForeignKey(Import.id), nullable=True)   # set if it came from a till import

class TillMapping(Base):
    # Remembered column choices for a till export, recognised by its header row
    # (tills.header_signature), so the same export layout is filled in next time.
    __tablename__ = "till_mappings"
    id = Column(Integer, primary_key=True)
    header_signature = Column(String, nullable=False, unique=True)
    date_column = Column(String, nullable=False)
    item_column = Column(String, nullable=False)
    quantity_column = Column(String, nullable=False)
    date_format = Column(String, nullable=False)       # e.g. "%d/%m/%Y"
    refund_column = Column(String, nullable=True)      # a column marking refunds, if the till uses one
    refund_value = Column(String, nullable=True)       # the value in it that means "refund"

class TillItemAlias(Base):
    # A remembered match: this till item name means this dish (or: ignore it).
    # item is stored normalised (invoices.normalise).
    __tablename__ = "till_item_aliases"
    id = Column(Integer, primary_key=True)
    item = Column(String, nullable=False, unique=True)
    dish_id = Column(Integer, ForeignKey(Dish.id), nullable=True)   # None when ignore is True
    ignore = Column(Boolean, nullable=False, default=False)

class QuadrantType(enum.Enum):
    STAR = "Star"
    PLOWHORSE = "Plowhorse"
    PUZZLE = "Puzzle"
    DOG = "Dog"

class ReportStatus(enum.Enum):
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"

class Report(Base):
    # One report written by the report agent (report_agent.py), kept as a
    # snapshot: the facts it used and what Claude wrote, so a past report reads
    # the same later even after the data changes.
    __tablename__ = "reports"
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    focus = Column(String, nullable=True)    # the owner's own question or focus, if they gave one
    status = Column(Enum(ReportStatus), nullable=False, default=ReportStatus.RUNNING)
    # JSON columns are reassigned, never changed in place (SQLAlchemy only notices reassignment).
    trail = Column(JSON, nullable=False, default=list)    # [{"tool", "input", "label"}] as the agent works
    facts = Column(JSON, nullable=False, default=list)    # report_tools.Fact as dicts
    content = Column(JSON, nullable=True)                 # {"next_steps": [...], "findings": [...]} once done
    error = Column(String, nullable=True)
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
