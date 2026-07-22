import enum
from sqlalchemy import Column, ForeignKey, Integer, String, Float, Enum
from database import Base

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
    price_per_unit = Column(Float, nullable=False)

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
    menu_price = Column(Float, nullable=False)
    category = Column(Enum(DishType))

class DishIngredient(Base):
    __tablename__ = "dish_ingredients"
    id = Column(Integer, primary_key=True)
    dish_id = Column(Integer, ForeignKey(Dish.id), nullable=False)
    ingredient_id = Column(Integer, ForeignKey(Ingredient.id), nullable=False)
    quantity = Column(Float, nullable=False)

