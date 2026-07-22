import models
import schemas
from models import DishType
from schemas import RecipeDraft
from anthropic import Anthropic
from dotenv import load_dotenv
load_dotenv()

client = Anthropic()  # reads ANTHROPIC_API_KEY from the environment
def build_recipe_prompt(dish_name: str, category: DishType) -> str:

    if category == DishType.MAIN:
        portion_note = "NOTE: this is a Main Course for 1"
    elif category == DishType.STARTER:
        portion_note = "NOTE: this is a Starter for 1"
    elif category == DishType.SIDE:
        portion_note = "NOTE: this is a Side Dish for 1"
    elif category == DishType.DESSERT:
        portion_note = "NOTE: this is a Dessert for 1"
    else:
        portion_note = ""
    
    return f"""Determine the ingredients and quantities needed to make one portion of {dish_name}.

    Estimate for a single serving (for a pizza, assume roughly a 12-inch pizza).

    All quantities must be in grams, millilitres, or a plain numeric count — no vague measures like "a pinch" or "to taste."
    
    {portion_note}

    List ingredients as raw components you'd buy from a wholesaler, not prepared items — for example, list flour, water, yeast, and salt individually rather than 'pizza dough' or 'pizza base.'
    """


def estimate_recipe(dish_name: str, category: DishType) -> RecipeDraft:
    prompt = build_recipe_prompt(dish_name, category)

    response = client.messages.parse(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
        output_format= RecipeDraft 
    )

    return response.parsed_output