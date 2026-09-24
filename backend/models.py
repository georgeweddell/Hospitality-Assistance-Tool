import enum
from sqlalchemy import Column, ForeignKey, Integer, String, Float, Enum, Date, JSON
from database import Base
from datetime import date

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=True)  # unused until Phase 6 — real login isn't built yet

class UnitType(enum.Enum):
    GRAM = "gram"   # base unit for anything by mass
    ML = "ml"       # base unit for anything by volume
    EACH = "each"   # base unit for countable things (1 egg, 1 lemon)

class Ingredient(Base):
    __tablename__ = "ingredients"
    id = Column(Integer, primary_key = True)
    name = Column(String, nullable=False)
    unit = Column(Enum(UnitType), nullable=False)
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

class DishIngredient(Base):
    __tablename__ = "dish_ingredients"
    id = Column(Integer, primary_key=True)
    dish_id = Column(Integer, ForeignKey(Dish.id), nullable=False)
    ingredient_id = Column(Integer, ForeignKey(Ingredient.id), nullable=False)
    quantity = Column(Float, nullable=False)

class SalesRecord(Base):
    __tablename__ = "sales_records"
    id = Column(Integer, primary_key=True)
    dish_id = Column(Integer, ForeignKey(Dish.id), nullable=False)
    units_sold = Column(Integer, nullable=False)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)

class QuadrantType(enum.Enum):
    STAR = "Star"
    PLOWHORSE = "Plowhorse"
    PUZZLE = "Puzzle"
    DOG = "Dog"