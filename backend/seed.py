from database import SessionLocal
from models import Ingredient, UnitType
from models import User

db = SessionLocal()

ingredients = [
    # --- flour / leavening ---
    Ingredient(name="00 flour", unit=UnitType.GRAM, price_per_unit=0.0012),        # £1.20/kg
    Ingredient(name="semolina", unit=UnitType.GRAM, price_per_unit=0.001),         # £1.00/kg
    Ingredient(name="fine sea salt", unit=UnitType.GRAM, price_per_unit=0.0006),   # £0.60/kg
    Ingredient(name="fresh yeast", unit=UnitType.GRAM, price_per_unit=0.003),      # £3.00/kg

    # --- dairy / cheese ---
    Ingredient(name="mozzarella (fior di latte)", unit=UnitType.GRAM, price_per_unit=0.0065),  # £6.50/kg
    Ingredient(name="buffalo mozzarella", unit=UnitType.GRAM, price_per_unit=0.011),            # £11.00/kg
    Ingredient(name="parmesan", unit=UnitType.GRAM, price_per_unit=0.011),                      # £11.00/kg
    Ingredient(name="gorgonzola", unit=UnitType.GRAM, price_per_unit=0.009),                    # £9.00/kg
    Ingredient(name="ricotta", unit=UnitType.GRAM, price_per_unit=0.005),                       # £5.00/kg
    Ingredient(name="mascarpone", unit=UnitType.GRAM, price_per_unit=0.0055),                   # £5.50/kg
    Ingredient(name="butter", unit=UnitType.GRAM, price_per_unit=0.005),                        # £5.00/kg

    # --- tomato / sauce base ---
    Ingredient(name="san marzano tomatoes", unit=UnitType.GRAM, price_per_unit=0.0035),  # £3.50/kg
    Ingredient(name="tomato passata", unit=UnitType.ML, price_per_unit=0.0018),          # £1.80/l
    Ingredient(name="tomato puree", unit=UnitType.GRAM, price_per_unit=0.003),           # £3.00/kg

    # --- cured meats ---
    Ingredient(name="pepperoni", unit=UnitType.GRAM, price_per_unit=0.014),      # £14.00/kg
    Ingredient(name="prosciutto crudo", unit=UnitType.GRAM, price_per_unit=0.028),  # £28.00/kg
    Ingredient(name="nduja", unit=UnitType.GRAM, price_per_unit=0.016),          # £16.00/kg
    Ingredient(name="pancetta", unit=UnitType.GRAM, price_per_unit=0.012),       # £12.00/kg
    Ingredient(name="milano salami", unit=UnitType.GRAM, price_per_unit=0.013), # £13.00/kg

    # --- fresh produce ---
    Ingredient(name="fresh basil", unit=UnitType.GRAM, price_per_unit=0.02),     # £20.00/kg
    Ingredient(name="garlic", unit=UnitType.GRAM, price_per_unit=0.003),        # £3.00/kg
    Ingredient(name="onion", unit=UnitType.GRAM, price_per_unit=0.0009),        # £0.90/kg
    Ingredient(name="red onion", unit=UnitType.GRAM, price_per_unit=0.0012),    # £1.20/kg
    Ingredient(name="cherry tomatoes", unit=UnitType.GRAM, price_per_unit=0.0025),  # £2.50/kg
    Ingredient(name="rocket", unit=UnitType.GRAM, price_per_unit=0.008),        # £8.00/kg
    Ingredient(name="chestnut mushrooms", unit=UnitType.GRAM, price_per_unit=0.0035),  # £3.50/kg
    Ingredient(name="courgette", unit=UnitType.GRAM, price_per_unit=0.0018),    # £1.80/kg
    Ingredient(name="aubergine", unit=UnitType.GRAM, price_per_unit=0.002),     # £2.00/kg
    Ingredient(name="spinach", unit=UnitType.GRAM, price_per_unit=0.004),       # £4.00/kg
    Ingredient(name="fresh red chilli", unit=UnitType.GRAM, price_per_unit=0.004),  # £4.00/kg
    Ingredient(name="lemon", unit=UnitType.EACH, price_per_unit=0.35),          # £0.35 each

    # --- oils / pantry / misc ---
    Ingredient(name="olive oil", unit=UnitType.ML, price_per_unit=0.006),           # £6.00/l
    Ingredient(name="extra virgin olive oil", unit=UnitType.ML, price_per_unit=0.009),  # £9.00/l
    Ingredient(name="balsamic vinegar", unit=UnitType.ML, price_per_unit=0.004),    # £4.00/l
    Ingredient(name="black pepper", unit=UnitType.GRAM, price_per_unit=0.012),      # £12.00/kg
    Ingredient(name="dried oregano", unit=UnitType.GRAM, price_per_unit=0.015),     # £15.00/kg
    Ingredient(name="capers", unit=UnitType.GRAM, price_per_unit=0.008),            # £8.00/kg
    Ingredient(name="anchovy fillets", unit=UnitType.GRAM, price_per_unit=0.018),   # £18.00/kg
    Ingredient(name="black olives", unit=UnitType.GRAM, price_per_unit=0.005),      # £5.00/kg
    Ingredient(name="pine nuts", unit=UnitType.GRAM, price_per_unit=0.022),         # £22.00/kg
    Ingredient(name="chilli flakes", unit=UnitType.GRAM, price_per_unit=0.01),      # £10.00/kg

    # --- eggs, dessert basics ---
    Ingredient(name="egg", unit=UnitType.EACH, price_per_unit=0.30),                # £0.30 each
    Ingredient(name="savoiardi biscuits", unit=UnitType.GRAM, price_per_unit=0.005), # £5.00/kg
    Ingredient(name="cocoa powder", unit=UnitType.GRAM, price_per_unit=0.008),      # £8.00/kg
    Ingredient(name="caster sugar", unit=UnitType.GRAM, price_per_unit=0.001),      # £1.00/kg

    ## --- No Cost/Utilities ---
    Ingredient(name="water", unit = UnitType.ML, price_per_unit=0.0)
]

db.add_all(ingredients)
db.commit()
db.close()

print(f"Seeded {len(ingredients)} ingredients.")

dev_user = User(email="dev@example.com")
db.add(dev_user)
db.commit()