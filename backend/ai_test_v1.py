from recipe_ai import estimate_recipe
from models import DishType

result = estimate_recipe("Tiramisu", DishType.DESSERT)
print(result)