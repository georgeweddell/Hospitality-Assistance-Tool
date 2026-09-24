"""
Reads a supplier invoice (PDF or photo) into an InvoiceDraft with Claude.

Claude only reads: it copies numbers as printed and says what each line is.
All arithmetic (price per gram, totals check) happens in invoices.py.
The output is validated against InvoiceDraft and shown to the owner as an
editable review before anything is saved.
"""

import base64

import models
from anthropic import Anthropic
from dotenv import load_dotenv
from schemas import InvoiceDraft

load_dotenv()

# Stronger than Haiku at reading tables from photos and PDFs.
MODEL = "claude-sonnet-5"

_client = None


def client():
    """Created on first use, so importing this file never needs the API key."""
    global _client
    if _client is None:
        _client = Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    return _client


def build_invoice_prompt(ingredient_names: list[str]) -> str:
    ingredient_list_text = ", ".join(ingredient_names)

    return f"""This is a supplier invoice for a UK restaurant. Read it into structured data.

    Header: the supplier's name, the invoice number, and the invoice date (not the delivery or due date).

    Then every line item, in order:
    - description: exactly as printed, including any codes or pack text.
    - The pack that the unit price is for, as three parts: pack_count x pack_size pack_unit.
      "12x1kg" is 12, 1, "kg". "2.5KG" is 1, 2.5, "kg". "6 x 400g" is 6, 400, "g". "Tray 30" or "30 eggs" is 1, 30, "each". "5L" is 1, 5, "l".
      pack_unit must be one of kg, g, l, ml, each. If the pack isn't clear, leave all three empty. Don't guess.
    - quantity, unit_price and line_total exactly as printed, excluding VAT. Don't calculate or correct anything.
    - kind: "food" for ingredients used in cooking; "non_food" for cleaning, packaging, equipment and drinks for sale; "charge" for delivery, fees, deposits and discounts.
    - likely_ingredient (food lines only): the plain ingredient this is. This business already stocks: {ingredient_list_text}.
      If the line reasonably matches one of these, use its exact name as written above.
      Otherwise give a short generic name in lower case, e.g. "guanciale", without brand, pack size or codes.

    Set prices_include_vat to true only if the invoice shows prices including VAT and no ex-VAT figures.
    """


def document_block(content: bytes, media_type: str) -> dict:
    """The file as a message content block: PDFs as a document, photos as an image."""
    data = base64.standard_b64encode(content).decode("ascii")
    block_type = "document" if media_type == "application/pdf" else "image"
    return {"type": block_type, "source": {"type": "base64", "media_type": media_type, "data": data}}


def read_invoice(db, content: bytes, media_type: str) -> InvoiceDraft:
    ingredient_names = [ingredient.name for ingredient in db.query(models.Ingredient).all()]
    prompt = build_invoice_prompt(ingredient_names)

    response = client().messages.parse(
        model=MODEL,
        max_tokens=8192,
        messages=[{"role": "user", "content": [document_block(content, media_type), {"type": "text", "text": prompt}]}],
        output_format=InvoiceDraft,
    )

    return response.parsed_output
