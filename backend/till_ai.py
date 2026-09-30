"""
Claude's two small jobs in a till import. Both only propose; the owner checks
everything on the review screen, and tills.py does all the counting.

  propose_columns  From the header row and a few sample rows: which column is
                   the date, the item and the quantity, the date format, and
                   how refunds are marked. Skipped when this export layout
                   has been seen before (tills.remembered_mapping).
  suggest_items    For item names not already known: the likely dish from the
                   menu, or "other" for drinks, add-ons and charges.

Privacy: Claude sees the header and SAMPLE_ROWS rows only, with anything that
looks like customer details blanked (redact). The rest of the file never
leaves the machine; item names go only to suggest_items.
"""

import re

from anthropic import Anthropic
from dotenv import load_dotenv

from schemas import TillColumnsDraft, TillItemHints, TillMappingIn
from tills import SAMPLE_ROWS, parse_date, status_columns

load_dotenv()

# Small, text-only work: Haiku is enough, and much cheaper than Sonnet.
MODEL = "claude-haiku-4-5-20251001"
DATE_FORMATS = ["%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y"]
# Columns blanked before Claude sees the sample rows: customer details, and free text or staff
# names that often hold them ("Notes": "call 07700 900123 when ready").
PERSONAL = re.compile(r"customer|e-?mail|phone|mobile|card|address|postcode|note|comment|staff|server|employee|"
                      r"cashier|operator|waiter", re.IGNORECASE)

_client = None


def client():
    """Created on first use, so importing this file never needs the API key."""
    global _client
    if _client is None:
        _client = Anthropic()
    return _client


def redact(header, rows):
    """The sample rows with customer details blanked (columns like "Customer Name", "Card Brand")."""
    personal = {i for i, h in enumerate(header) if PERSONAL.search(h)}
    return [["" if i in personal else cell for i, cell in enumerate(row)] for row in rows]


def build_columns_prompt(header, rows):
    table = "\n".join(",".join(row) for row in [header] + redact(header, rows[:SAMPLE_ROWS]))
    return f"""These are the header and first rows of a sales export from a restaurant's till (a CSV file):

{table}

Say which column holds each of these, using the column names exactly as in the header:
- date_column: the date of the sale (if the date and time are in one column, that column).
- item_column: the name of the item sold (the menu item, not a category or modifier).
- quantity_column: how many were sold on that row.
- date_format: how the dates are written, one of {", ".join(DATE_FORMATS)}. UK tills usually write the day first.
- refund_column and refund_value: only if refunds are marked by a column value (e.g. "Event Type" = "Refund") rather than a negative quantity. Otherwise leave both empty.
- size_column: only if a separate column holds the size or variation of the item (e.g. "Price Point Name" with Regular / Small). Otherwise empty.
- skip_column and skip_values: only if a column marks rows that aren't sales, such as voids or cancelled orders (e.g. "Status" with "Cancelled"). skip_values: the values seen in the sample rows or usual for this till that mean "not a sale", comma-separated (e.g. "Void, Cancelled"). Never refunds (those are netted) or ordinary sales values.

Leave a field empty if no column fits. Don't guess.
"""


def build_items_prompt(items, dish_names):
    return f"""These are item names from a restaurant's till:
{chr(10).join("- " + item for item in items)}

The restaurant's menu has these dishes: {", ".join(dish_names)}.

For every item name, in the same order:
- kind: "dish" for any food dish (a size or variant counts, e.g. "MARG 12" for Margherita), even one that
  isn't in the list below; "other" for drinks, add-ons, extras, service charges and anything else that isn't a dish.
- likely_dish: for a "dish", the menu dish it is, written exactly as in the list above; empty if none fits.
"""


def check_columns(draft, header, rows):
    """
    Claude's proposal, checked against the file. None if a required column
    doesn't exist. If the proposed date format can't read the sample dates,
    the first format that reads them all is used instead.
    """
    required = (draft.date_column, draft.item_column, draft.quantity_column)
    if any(c not in header for c in required):
        return None
    refund = draft.refund_column if draft.refund_column in header and draft.refund_value else None

    dates = [row[header.index(draft.date_column)] for row in rows[:SAMPLE_ROWS]
             if header.index(draft.date_column) < len(row)]
    formats = [draft.date_format] + [f for f in DATE_FORMATS if f != draft.date_format] if draft.date_format else DATE_FORMATS
    date_format = next((f for f in formats if dates and all(parse_date(d, f) for d in dates)), None)
    if date_format is None:
        return None

    size = draft.size_column if draft.size_column in header and draft.size_column != draft.item_column else None
    # Claude sees 5 rows, which rarely include a refund or a void: fill any gap from the whole file.
    found = status_columns(header, rows, skip=required)
    if refund is None and found[0]:
        draft = draft.model_copy(update={"refund_column": found[0], "refund_value": found[1]})
        refund = found[0]
    if not (draft.skip_column in header and draft.skip_values) and found[2]:
        draft = draft.model_copy(update={"skip_column": found[2], "skip_values": found[3]})
    # Rows to leave out, never including the refund value (refunds are netted, not dropped).
    skip, skip_values = None, None
    if draft.skip_column in header and draft.skip_values:
        refund_value = (draft.refund_value or "").strip().lower() if refund == draft.skip_column else None
        values = [v.strip() for v in draft.skip_values.split(",") if v.strip() and v.strip().lower() != refund_value]
        if values:
            skip, skip_values = draft.skip_column, ", ".join(values)

    return TillMappingIn(date_column=draft.date_column, item_column=draft.item_column,
                         quantity_column=draft.quantity_column, date_format=date_format,
                         refund_column=refund, refund_value=draft.refund_value if refund else None,
                         size_column=size, skip_column=skip, skip_values=skip_values)


def propose_columns(header, rows):
    response = client().messages.parse(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": build_columns_prompt(header, rows)}],
        output_format=TillColumnsDraft,
    )
    return check_columns(response.parsed_output, header, rows)


def suggest_items(items, dish_names):
    if not items:
        return []
    response = client().messages.parse(
        model=MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": build_items_prompt(items, dish_names)}],
        output_format=TillItemHints,
    )
    return response.parsed_output.items
