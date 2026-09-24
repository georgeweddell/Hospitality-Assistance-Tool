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


def already_imported(db, supplier, invoice_number, file_hash=None):
    """An applied invoice import of the same supplier + invoice number, or the same file. None if there isn't one."""
    applied = db.query(Import).filter(Import.kind == ImportKind.INVOICE, Import.status == ImportStatus.APPLIED)
    if supplier and invoice_number:
        same = applied.filter(func.lower(Import.supplier) == supplier.strip().lower(),
                              Import.reference == invoice_number.strip()).first()
        if same:
            return same
    if file_hash:
        return applied.filter(Import.file_hash == file_hash).first()
    return None


def review_line(db, supplier, invoice_date, line):
    """
    Matches one line and works out its price. Matching order:
      1. a remembered match for this supplier and description
      2. an exact match on Claude's likely ingredient name
      3. suggestions from the fuzzy matcher (offered, never chosen automatically)
    Non-food lines and charges are ignored unless a remembered match says otherwise.
    """
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
    duplicate = already_imported(db, draft.supplier, draft.invoice_number, file_hash)
    return InvoiceReviewOut(
        supplier=draft.supplier,
        invoice_number=draft.invoice_number,
        invoice_date=draft.invoice_date,
        prices_include_vat=draft.prices_include_vat,
        already_imported=duplicate.id if duplicate else None,
        filename=filename,
        file_hash=file_hash,
        lines=[review_line(db, draft.supplier, draft.invoice_date, line) for line in draft.lines],
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
    duplicate = already_imported(db, data.supplier, data.invoice_number, data.file_hash)
    if duplicate:
        raise ImportProblem(f"This invoice was already imported on {duplicate.created_at:%d %b %Y}. "
                            "Undo that import first to import it again.")

    kept = [line for line in data.lines if line.action != "ignore"]
    if not kept:
        raise ImportProblem("Every line is set to Ignore, so there's nothing to save")

    planned = []   # (line, ingredient or None for new, unit, price per unit)
    seen_ids, seen_names = set(), set()
    for line in kept:
        if line.action == "update":
            ingredient = db.get(Ingredient, line.ingredient_id) if line.ingredient_id else None
            if ingredient is None:
                raise ImportProblem(f"'{line.description}': choose an ingredient")
            if ingredient.id in seen_ids:
                raise ImportProblem(f"{ingredient.name} appears on two lines. Ignore one of them.")
            seen_ids.add(ingredient.id)
            unit = ingredient.unit
        else:
            name = (line.new_ingredient_name or "").strip().lower()
            if not name:
                raise ImportProblem(f"'{line.description}': enter a name for the new ingredient")
            if db.query(Ingredient).filter(func.lower(Ingredient.name) == name).first():
                raise ImportProblem(f"There's already an ingredient called '{name}'. Choose it instead of adding a new one.")
            if name in seen_names:
                raise ImportProblem(f"'{name}' appears on two lines. Ignore one of them.")
            if line.pack_unit is None:
                raise ImportProblem(f"'{line.description}': enter the pack size")
            seen_names.add(name)
            ingredient = None
            unit = PACK_UNITS[line.pack_unit][0]
        try:
            price = line_price(line.pack_count, line.pack_size, line.pack_unit, line.unit_price, unit)
        except ValueError as e:
            raise ImportProblem(f"'{line.description}': {e}")
        planned.append((line, ingredient, unit, price))

    # --- Save --------------------------------------------------------------------
    record = Import(kind=ImportKind.INVOICE, filename=data.filename, file_hash=data.file_hash,
                    supplier=data.supplier.strip(), reference=data.invoice_number.strip(),
                    effective_date=data.invoice_date, status=ImportStatus.APPLIED,
                    lines_applied=len(kept), lines_ignored=len(data.lines) - len(kept))
    db.add(record)
    db.flush()   # assigns record.id

    for line, ingredient, unit, price in planned:
        if ingredient is None:
            ingredient = Ingredient(name=line.new_ingredient_name.strip().lower(), unit=unit, import_id=record.id)
            db.add(ingredient)
            db.flush()
        db.add(IngredientPrice(ingredient_id=ingredient.id, price_per_unit=price, source=PriceSource.INVOICE,
                               supplier=record.supplier, effective_date=data.invoice_date, import_id=record.id))
        remember(db, data.supplier, line.description, ingredient_id=ingredient.id)

    for line in data.lines:
        if line.action == "ignore":
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
