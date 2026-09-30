"""
Invoice import: everything after Claude has read the invoice.

Claude turns the document into an InvoiceDraft (see invoice_ai.py). From there
it's plain Python, so every step can be tested and explained:

  review_invoice  works out each line's price per g / ml / each, checks the
                  arithmetic, matches it to an ingredient and flags anything
                  odd. Nothing is saved.
  apply_invoice   saves what the owner confirmed, in one go, after checking
                  everything first. Prices are recorded as `invoice` prices
                  dated on the invoice date. Remembers the owner's matches.
  undo_import     removes everything an invoice import added.
"""

from datetime import date

from sqlalchemy import func

from costing import best_price
from matching import match_ingredient, suggest_ingredients
from models import (DishIngredient, Import, ImportKind, ImportStatus, Ingredient, IngredientPrice,
                    PriceSource, SupplierAlias)
from schemas import IngredientSuggestion, InvoiceReviewLine, InvoiceReviewOut
from units import PACK_UNITS, price_per_base_unit

BIG_CHANGE_PERCENT = 25   # a price this far from the current one is flagged: often a misread pack
NO_PRICES = {"credit_note", "statement"}   # documents that record no purchase prices


class ImportProblem(ValueError):
    """Something that stops an import being applied. The message is shown to the owner."""


def normalise(text):
    """ "  MOZZ  FDL 1KG " -> "mozz fdl 1kg", so remembered matches ignore spacing and case."""
    return " ".join((text or "").lower().split())


def line_price(pack_count, pack_size, pack_unit, unit_price, ingredient_unit):
    """
    Price per base unit for one invoice line.

    Example: 12 x 1 kg at £93.60 a pack -> 93.60 / (12 x 1 kg) = 93.60 / 12,000 g = £0.0078/g.

    The pack is count x size, and the conversion goes through units.py like every
    other price. Raises ValueError if the pack is missing or doesn't fit the ingredient.
    """
    if pack_count is None or pack_size is None or pack_unit is None or unit_price is None:
        raise ValueError("The pack or price is missing")
    return price_per_base_unit(unit_price, pack_count * pack_size, pack_unit, ingredient_unit)


def not_delivered(line):
    """Quantity 0 or less: "NOT AVAILABLE", or goods sent back. No purchase price there."""
    return line.quantity is not None and line.quantity <= 0


def totals_agree(quantity, unit_price, line_total):
    """
    Quantity x unit price should equal the line total, to within 1p or 1%
    (invoices round). Example: 2 x £93.60 = £187.20. Lines missing a number pass.
    """
    if quantity is None or unit_price is None or line_total is None:
        return True
    return abs(quantity * unit_price - line_total) <= max(0.01, 0.01 * abs(line_total))


def find_alias(db, supplier, description):
    return db.query(SupplierAlias).filter(
        SupplierAlias.supplier == normalise(supplier),
        SupplierAlias.description == normalise(description),
    ).first()


def already_imported(db, supplier, invoice_number, file_hash=None, invoice_date=None):
    """
    An applied invoice import of the same invoice, or None. The same invoice is:
    the same supplier + invoice number; or the same invoice number on the same
    date, however the supplier's name was read ("Harbour Fish Co" and
    "Harbour Fish Co (sample)" on a reprinted copy); or the same file.
    """
    applied = db.query(Import).filter(Import.kind == ImportKind.INVOICE, Import.status == ImportStatus.APPLIED)
    if invoice_number:
        same_number = applied.filter(func.lower(Import.reference) == invoice_number.strip().lower())
        if supplier:
            same = same_number.filter(func.lower(Import.supplier) == supplier.strip().lower()).first()
            if same:
                return same
        if invoice_date:
            same = same_number.filter(Import.effective_date == invoice_date).first()
            if same:
                return same
    if file_hash:
        return applied.filter(Import.file_hash == file_hash).first()
    return None


def review_line(db, supplier, invoice_date, line, document_type="invoice"):
    """
    Matches one line and works out its price. Matching order:
      1. a remembered match for this supplier and description
      2. an exact match on Claude's likely ingredient name
      3. suggestions from the fuzzy matcher (offered, never chosen automatically)
    Non-food lines and charges are ignored unless a remembered match says otherwise.
    Also ignored by default (the owner can change it): every line of a credit
    note or statement, and a line with nothing delivered (quantity 0 or less,
    e.g. "NOT AVAILABLE" or goods returned), since none is a purchase price.
    """
    if line.quantity is None and line.unit_price is None and line.line_total is not None:
        # A till receipt prints one price per line ("CASTER SUGAR 5KG  6.49"): one pack at that price.
        line = line.model_copy(update={"quantity": 1, "unit_price": line.line_total})
    review = InvoiceReviewLine(**line.model_dump(), action="ignore")
    flags = []
    if not totals_agree(line.quantity, line.unit_price, line.line_total):
        flags.append("totals")

    alias = find_alias(db, supplier, line.description)
    name = line.likely_ingredient or line.description
    if alias:
        review.remembered = True
        review.action = "ignore" if alias.ignore else "update"
        review.ingredient_id = alias.ingredient_id
    else:
        match = match_ingredient(db, name)
        if line.kind != "food":
            review.action = "ignore"
        elif match:
            review.action = "update"
            review.ingredient_id = match.id
        else:
            review.action = "new"
            review.new_ingredient_name = name.strip().lower()
            review.suggestions = [IngredientSuggestion(id=s.id, name=s.name) for s in suggest_ingredients(db, name)]
    if document_type in NO_PRICES or not_delivered(line):
        review.action = "ignore"   # the match is kept, so switching it back on needs no choosing

    # The unit the price is measured in: the matched ingredient's, or (for a
    # new ingredient) whatever the pack is measured in.
    ingredient = db.get(Ingredient, review.ingredient_id) if review.ingredient_id else None
    if ingredient:
        unit = ingredient.unit
    elif line.pack_unit:
        unit = PACK_UNITS[line.pack_unit][0]
    else:
        unit = None

    if review.action != "ignore":
        if (unit is None or line.pack_count is None or line.pack_size is None or line.pack_unit is None
                or line.unit_price is None):
            flags.append("pack")
        else:
            try:
                review.price_per_unit = line_price(line.pack_count, line.pack_size, line.pack_unit,
                                                   line.unit_price, unit)
            except ValueError:
                flags.append("unit")

    if ingredient and review.price_per_unit is not None:
        current = best_price(db, ingredient.id, as_of=invoice_date)
        if current and current.price_per_unit > 0:
            review.current_price_per_unit = current.price_per_unit
            review.change_percent = (review.price_per_unit / current.price_per_unit - 1) * 100
            if abs(review.change_percent) > BIG_CHANGE_PERCENT:
                flags.append("big_change")

    review.flags = flags
    return review


def review_invoice(db, draft, filename=None, file_hash=None):
    """Turns Claude's reading of an invoice into lines for the owner to check. Saves nothing."""
    duplicate = already_imported(db, draft.supplier, draft.invoice_number, file_hash, draft.invoice_date)
    return InvoiceReviewOut(
        supplier=draft.supplier,
        invoice_number=draft.invoice_number,
        invoice_date=draft.invoice_date,
        prices_include_vat=draft.prices_include_vat,
        already_imported=duplicate.id if duplicate else None,
        filename=filename,
        file_hash=file_hash,
        document_type=draft.document_type,
        lines=[review_line(db, draft.supplier, draft.invoice_date, line, draft.document_type) for line in draft.lines],
    )


def remember(db, supplier, description, ingredient_id=None, ignore=False):
    """Stores (or replaces) the remembered match for a supplier's line description."""
    alias = find_alias(db, supplier, description)
    if alias is None:
        alias = SupplierAlias(supplier=normalise(supplier), description=normalise(description))
        db.add(alias)
    alias.ingredient_id = None if ignore else ingredient_id
    alias.ignore = ignore


def apply_invoice(db, data, today=None):
    """
    Saves a confirmed invoice. Every line is checked first; if anything is
    wrong, ImportProblem is raised and nothing is saved.
    Returns the new Import.
    """
    today = today or date.today()

    # --- Check everything ---------------------------------------------------------
    if data.invoice_date > today:
        raise ImportProblem("The invoice date is in the future")
    duplicate = already_imported(db, data.supplier, data.invoice_number, data.file_hash, data.invoice_date)
    if duplicate:
        raise ImportProblem(f"This invoice was already imported on {duplicate.created_at:%d %b %Y}. "
                            "Undo that import first to import it again.")

    kept = [line for line in data.lines if line.action != "ignore"]
    if not kept:
        raise ImportProblem("Every line is set to Ignore, so there's nothing to save")

    # One price per ingredient. Two lines for the same ingredient (two joints
    # of different weights) are combined: what was paid / how much came.
    groups = {}   # ("id", ingredient id) or ("new", name) -> {ingredient, name, unit, paid, amount, lines}
    for line in kept:
        if line.action == "update":
            ingredient = db.get(Ingredient, line.ingredient_id) if line.ingredient_id else None
            if ingredient is None:
                raise ImportProblem(f"'{line.description}': choose an ingredient")
            key, name, unit = ("id", ingredient.id), ingredient.name, ingredient.unit
        else:
            name = (line.new_ingredient_name or "").strip().lower()
            if not name:
                raise ImportProblem(f"'{line.description}': enter a name for the new ingredient")
            if db.query(Ingredient).filter(func.lower(Ingredient.name) == name).first():
                raise ImportProblem(f"There's already an ingredient called '{name}'. Choose it instead of adding a new one.")
            if line.pack_unit is None:
                raise ImportProblem(f"'{line.description}': enter the pack size")
            ingredient, key, unit = None, ("new", name), PACK_UNITS[line.pack_unit][0]
            if key in groups and groups[key]["unit"] != unit:
                raise ImportProblem(f"'{name}' is on two lines measured differently (by weight and by volume or count)")
        try:
            line_price(line.pack_count, line.pack_size, line.pack_unit, line.unit_price, unit)   # checks the line
        except ValueError as e:
            raise ImportProblem(f"'{line.description}': {e}")
        group = groups.setdefault(key, {"ingredient": ingredient, "name": name, "unit": unit,
                                        "paid": 0.0, "amount": 0.0, "lines": []})
        packs = line.quantity if line.quantity and line.quantity > 0 else 1
        group["paid"] += packs * line.unit_price
        group["amount"] += packs * line.pack_count * line.pack_size * PACK_UNITS[line.pack_unit][1]
        group["lines"].append(line)

    planned = []   # (group, price per unit)
    for group in groups.values():
        # Example: sirloin, 4.35 kg at £25.90/kg and 3.90 kg at £27.90/kg:
        # (4.35 x 25.90 + 3.90 x 27.90) / 8,250 g = (112.665 + 108.81) / 8,250 = £0.02685 per g.
        # One line gives exactly its own price: (packs x price) / (packs x pack size).
        planned.append((group, group["paid"] / group["amount"]))

    # --- Save --------------------------------------------------------------------
    record = Import(kind=ImportKind.INVOICE, filename=data.filename, file_hash=data.file_hash,
                    supplier=data.supplier.strip(), reference=data.invoice_number.strip(),
                    effective_date=data.invoice_date, status=ImportStatus.APPLIED,
                    lines_applied=len(kept), lines_ignored=len(data.lines) - len(kept))
    db.add(record)
    db.flush()   # assigns record.id

    for group, price in planned:
        ingredient = group["ingredient"]
        if ingredient is None:
            ingredient = Ingredient(name=group["name"], unit=group["unit"], import_id=record.id)
            db.add(ingredient)
            db.flush()
        db.add(IngredientPrice(ingredient_id=ingredient.id, price_per_unit=price, source=PriceSource.INVOICE,
                               supplier=record.supplier, effective_date=data.invoice_date, import_id=record.id))
        for line in group["lines"]:
            remember(db, data.supplier, line.description, ingredient_id=ingredient.id)

    for line in data.lines:
        # A line with nothing delivered isn't remembered as "ignore": next time it may come.
        if line.action == "ignore" and not not_delivered(line):
            remember(db, data.supplier, line.description, ignore=True)

    db.commit()
    return record


def undo_import(db, import_id):
    """
    Removes the prices an invoice import added, and the ingredients it created.
    Costing falls back to each ingredient's previous price. Remembered matches
    are kept. All or nothing: if a created ingredient is now in a recipe, the
    undo is refused (removing it would leave that recipe uncostable).
    """
    record = db.get(Import, import_id)
    if record is None:
        raise LookupError("Import not found")
    if record.kind != ImportKind.INVOICE:
        raise ImportProblem("Only invoice imports can be undone here")
    if record.status != ImportStatus.APPLIED:
        raise ImportProblem("This import has already been undone")

    created = db.query(Ingredient).filter(Ingredient.import_id == import_id).all()
    for ingredient in created:
        if db.query(DishIngredient).filter(DishIngredient.ingredient_id == ingredient.id).first():
            raise ImportProblem(f"{ingredient.name} was added by this invoice and is now in a recipe. "
                                "Remove it from the recipe first.")

    db.query(IngredientPrice).filter(IngredientPrice.import_id == import_id).delete()
    for ingredient in created:
        # Only if nothing else has priced it since (e.g. a later invoice).
        if db.query(IngredientPrice).filter(IngredientPrice.ingredient_id == ingredient.id).count() == 0:
            db.query(SupplierAlias).filter(SupplierAlias.ingredient_id == ingredient.id).delete()
            db.delete(ingredient)
    record.status = ImportStatus.UNDONE
    db.commit()
    return record
