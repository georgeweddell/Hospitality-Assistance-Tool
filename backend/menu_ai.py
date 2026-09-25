"""
Reads a menu (PDF or photo) into a MenuDraft with Claude.

Claude only reads: names, prices and descriptions as printed, which section
each item is in, and whether it's a dish at all. Comparing with the stored
dishes, and every decision about what changes, happens in menus.py and on the
review screen.
"""

import models
from invoice_ai import client, document_block
from schemas import MenuDraft

# Stronger than Haiku at reading layouts from photos and PDFs (as for invoices).
MODEL = "claude-sonnet-5"


def build_menu_prompt(dish_names: list[str]) -> str:
    stored = ", ".join(dish_names) if dish_names else "(none yet)"

    return f"""This is a UK restaurant's menu. List every item on it, in order.

    For each item:
    - name: as printed, without the price.
    - price: in pounds, as a number. If an item comes in sizes (e.g. 10" and 12"), list each size as its own item,
      with the size in the name (e.g. 'Margherita 12"') and its own price.
    - section: the menu heading it's under, as printed.
    - category: Starter, Main, Side or Dessert. Pizzas, pasta and large plates are Main; small plates and antipasti
      are Starter; sides and contorni are Side; dolci are Dessert. Leave empty for anything that isn't a dish.
    - description: as printed, if there is one.
    - kind: "dish" for food on the menu; "other" for drinks, set menus, add-ons and extras (e.g. "add burrata +£3").
    - likely_existing: the restaurant's dishes are stored as: {stored}.
      If this item looks like one of those under a different name, give that stored name exactly as written above.
      Leave it empty if the name is the same, or if it's a different dish.

    Don't calculate or correct anything, and don't invent items that aren't printed.
    """


def read_menu(db, content: bytes, media_type: str) -> MenuDraft:
    dish_names = [dish.name for dish in db.query(models.Dish).all()]
    prompt = build_menu_prompt(dish_names)

    response = client().messages.parse(
        model=MODEL,
        max_tokens=8192,
        messages=[{"role": "user", "content": [document_block(content, media_type), {"type": "text", "text": prompt}]}],
        output_format=MenuDraft,
    )

    return response.parsed_output
