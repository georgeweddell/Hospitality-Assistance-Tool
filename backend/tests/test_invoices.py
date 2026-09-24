"""
Tests for invoice import (invoices.py): pack maths, the arithmetic check,
matching (remembered matches first), and apply / undo.

Claude isn't involved: each test starts from an InvoiceDraft, i.e. what
Claude would have read off the invoice.
"""

from datetime import date

import pytest
from fastapi import HTTPException

from costing import best_price
from invoices import ImportProblem, apply_invoice, line_price, review_invoice, totals_agree, undo_import
from main import apply_invoice_route, list_imports, undo_import_route
from models import (DishType, Import, ImportStatus, Ingredient, IngredientPrice, PriceSource,
                    SupplierAlias, UnitType)
from schemas import InvoiceApplyIn, InvoiceApplyLine, InvoiceDraft, InvoiceLineDraft

SUPPLIER = "Vesuvio Foods Ltd"
TODAY = date(2026, 9, 24)
INVOICE_DATE = date(2026, 9, 20)


@pytest.fixture
def stock(add_ingredient):
    # Benchmark prices: mozzarella £7.20/kg, 00 flour £1.30/kg, eggs £0.30 each.
    return {
        "mozzarella": add_ingredient("mozzarella", UnitType.GRAM, 0.0072),
        "flour": add_ingredient("00 flour", UnitType.GRAM, 0.0013),
        "egg": add_ingredient("egg", UnitType.EACH, 0.30),
    }


def mozz_line(**changes):
    # 2 cases of 12 x 1 kg at £93.60 a case = £187.20
    fields = dict(description="MOZZ FDL 1KG x12", pack_count=12, pack_size=1, pack_unit="kg",
                  quantity=2, unit_price=93.60, line_total=187.20, kind="food",
                  likely_ingredient="mozzarella")
    return InvoiceLineDraft(**{**fields, **changes})


def draft(*lines, number="INV-1001"):
    return InvoiceDraft(supplier=SUPPLIER, invoice_number=number, invoice_date=INVOICE_DATE, lines=list(lines))


def apply_in(*lines, number="INV-1001", invoice_date=INVOICE_DATE, file_hash=None):
    return InvoiceApplyIn(supplier=SUPPLIER, invoice_number=number, invoice_date=invoice_date,
                          file_hash=file_hash, lines=list(lines))


def mozz_apply(stock, **changes):
    fields = dict(description="MOZZ FDL 1KG x12", action="update", ingredient_id=stock["mozzarella"].id,
                  pack_count=12, pack_size=1, pack_unit="kg", unit_price=93.60)
    return InvoiceApplyLine(**{**fields, **changes})


# --- Pack maths and arithmetic --------------------------------------------------------

def test_price_per_gram_from_a_case():
    # £93.60 / (12 x 1 kg) = £93.60 / 12,000 g = £0.0078/g
    assert line_price(12, 1, "kg", 93.60, UnitType.GRAM) == pytest.approx(0.0078)


def test_price_per_gram_from_small_packs():
    # 6 x 400 g at £9.00 = £9.00 / 2,400 g = £0.00375/g
    assert line_price(6, 400, "g", 9.00, UnitType.GRAM) == pytest.approx(0.00375)


def test_price_each_from_a_tray():
    # A tray of 30 eggs at £8.40 = £0.28 each
    assert line_price(1, 30, "each", 8.40, UnitType.EACH) == pytest.approx(0.28)


def test_a_pack_that_doesnt_fit_the_ingredient_is_refused():
    with pytest.raises(ValueError):
        line_price(1, 5, "l", 10.00, UnitType.GRAM)


def test_line_totals_must_add_up():
    assert totals_agree(2, 93.60, 187.20)        # 2 x £93.60 = £187.20
    assert totals_agree(3, 3.33, 10.00)          # £9.99 vs £10.00: rounding, within 1p
    assert not totals_agree(2, 93.60, 93.60)     # quantity misread


# --- Review ------------------------------------------------------------------------

def test_review_matches_and_prices_a_line(db, stock):
    # New £0.0078/g vs benchmark £0.0072/g = +8.3%
    [line] = review_invoice(db, draft(mozz_line())).lines

    assert (line.action, line.ingredient_id, line.flags) == ("update", stock["mozzarella"].id, [])
    assert line.price_per_unit == pytest.approx(0.0078)
    assert line.change_percent == pytest.approx(8.33, abs=0.01)


def test_review_flags_problems(db, stock):
    lines = review_invoice(db, draft(
        mozz_line(line_total=93.60),                          # 2 x £93.60 isn't £93.60
        mozz_line(description="MOZZ ?", pack_unit=None),      # pack not read
        mozz_line(description="MOZZ L", pack_unit="l"),       # litres for a weighed ingredient
        mozz_line(description="MOZZ 1", pack_count=1, unit_price=93.60, line_total=187.20, quantity=2),
    )).lines
    # Last line: £93.60 for 1 kg = £0.0936/g, 13x the current price -> big change

    assert [l.flags for l in lines] == [["totals"], ["pack"], ["unit"], ["big_change"]]


def test_unknown_food_becomes_a_new_ingredient_and_non_food_is_ignored(db, stock):
    lines = review_invoice(db, draft(
        mozz_line(description="GUANC 1.5KG", likely_ingredient="guanciale", pack_count=1, pack_size=1.5,
                  quantity=1, unit_price=24.00, line_total=24.00),
        mozz_line(description="BLUE ROLL x6", kind="non_food", likely_ingredient=None, pack_unit=None),
    )).lines

    assert (lines[0].action, lines[0].new_ingredient_name) == ("new", "guanciale")
    assert lines[0].price_per_unit == pytest.approx(0.016)   # £24.00 / 1,500 g
    assert (lines[1].action, lines[1].flags) == ("ignore", [])


def test_a_remembered_match_beats_claudes_guess(db, stock):
    # Last time the owner said this line is flour, whatever Claude now thinks.
    apply_invoice(db, apply_in(mozz_apply(stock, ingredient_id=stock["flour"].id, pack_size=1, pack_count=12,
                                          unit_price=15.60)), today=TODAY)

    [line] = review_invoice(db, draft(mozz_line(), number="INV-1002")).lines
    assert (line.ingredient_id, line.remembered) == (stock["flour"].id, True)


def test_remembered_matches_belong_to_one_supplier(db, stock):
    apply_invoice(db, apply_in(mozz_apply(stock, ingredient_id=stock["flour"].id, unit_price=15.60)), today=TODAY)

    other = InvoiceDraft(supplier="Another Supplier", invoice_number="A1", invoice_date=INVOICE_DATE,
                         lines=[mozz_line()])
    [line] = review_invoice(db, other).lines
    assert (line.ingredient_id, line.remembered) == (stock["mozzarella"].id, False)


def test_ignored_lines_are_remembered(db, stock):
    apply_invoice(db, apply_in(mozz_apply(stock),
                               InvoiceApplyLine(description="DELIVERY", action="ignore")), today=TODAY)

    [line] = review_invoice(db, draft(mozz_line(description="Delivery", kind="food"), number="INV-1002")).lines
    assert (line.action, line.remembered) == ("ignore", True)


def test_review_spots_an_invoice_already_imported(db, stock):
    record = apply_invoice(db, apply_in(mozz_apply(stock)), today=TODAY)

    assert review_invoice(db, draft(mozz_line())).already_imported == record.id


# --- Apply -------------------------------------------------------------------------

def test_apply_records_a_dated_invoice_price(db, stock):
    record = apply_invoice(db, apply_in(mozz_apply(stock)), today=TODAY)

    price = best_price(db, stock["mozzarella"].id)
    assert (price.source, price.supplier, price.effective_date, price.import_id) == (
        PriceSource.INVOICE, SUPPLIER, INVOICE_DATE, record.id)
    assert price.price_per_unit == pytest.approx(0.0078)
    assert (record.lines_applied, record.lines_ignored) == (1, 0)


def test_apply_can_create_an_ingredient(db, stock):
    apply_invoice(db, apply_in(InvoiceApplyLine(description="GUANC 1.5KG", action="new", new_ingredient_name="Guanciale",
                                                pack_count=1, pack_size=1.5, pack_unit="kg", unit_price=24.00)),
                  today=TODAY)

    guanciale = db.query(Ingredient).filter(Ingredient.name == "guanciale").one()
    assert guanciale.unit == UnitType.GRAM
    assert best_price(db, guanciale.id).price_per_unit == pytest.approx(0.016)


def test_one_bad_line_means_nothing_is_saved(db, stock):
    with pytest.raises(ImportProblem):
        apply_invoice(db, apply_in(mozz_apply(stock),
                                   mozz_apply(stock, description="EGGS", ingredient_id=stock["egg"].id)),   # kg for eggs
                      today=TODAY)

    assert db.query(Import).count() == 0
    assert db.query(IngredientPrice).filter(IngredientPrice.source == PriceSource.INVOICE).count() == 0


@pytest.mark.parametrize("problem", [
    "duplicate invoice", "same file", "future date", "same ingredient twice", "nothing to save", "name taken",
])
def test_apply_refuses(db, stock, problem):
    if problem in ("duplicate invoice", "same file"):
        apply_invoice(db, apply_in(mozz_apply(stock), file_hash="abc"), today=TODAY)
    data = {
        "duplicate invoice": apply_in(mozz_apply(stock)),
        "same file": apply_in(mozz_apply(stock), number="INV-9999", file_hash="abc"),
        "future date": apply_in(mozz_apply(stock), invoice_date=date(2026, 9, 25)),
        "same ingredient twice": apply_in(mozz_apply(stock), mozz_apply(stock, description="MOZZ 2")),
        "nothing to save": apply_in(InvoiceApplyLine(description="DELIVERY", action="ignore")),
        "name taken": apply_in(InvoiceApplyLine(description="EGGS", action="new", new_ingredient_name="Egg",
                                                pack_count=1, pack_size=30, pack_unit="each", unit_price=8.40)),
    }[problem]

    with pytest.raises(ImportProblem):
        apply_invoice(db, data, today=TODAY)


def test_the_apply_route_turns_problems_into_a_422(db, stock):
    with pytest.raises(HTTPException) as e:
        apply_invoice_route(apply_in(InvoiceApplyLine(description="DELIVERY", action="ignore")), db)
    assert e.value.status_code == 422


# --- Undo --------------------------------------------------------------------------

def test_undo_falls_back_to_the_previous_price(db, stock):
    record = apply_invoice(db, apply_in(mozz_apply(stock)), today=TODAY)
    undo_import_route(record.id, db)

    assert best_price(db, stock["mozzarella"].id).source == PriceSource.BENCHMARK
    assert db.get(Import, record.id).status == ImportStatus.UNDONE
    # The invoice can then be imported again
    apply_invoice(db, apply_in(mozz_apply(stock)), today=TODAY)


def test_undo_removes_an_ingredient_it_created_but_keeps_remembered_matches(db, stock):
    record = apply_invoice(db, apply_in(
        mozz_apply(stock),
        InvoiceApplyLine(description="GUANC 1.5KG", action="new", new_ingredient_name="guanciale",
                         pack_count=1, pack_size=1.5, pack_unit="kg", unit_price=24.00)), today=TODAY)
    undo_import(db, record.id)

    assert db.query(Ingredient).filter(Ingredient.name == "guanciale").count() == 0
    assert db.query(SupplierAlias).filter(SupplierAlias.ingredient_id == stock["mozzarella"].id).count() == 1


def test_undo_is_refused_if_a_created_ingredient_is_in_a_recipe(db, stock, add_dish):
    record = apply_invoice(db, apply_in(InvoiceApplyLine(
        description="GUANC 1.5KG", action="new", new_ingredient_name="guanciale",
        pack_count=1, pack_size=1.5, pack_unit="kg", unit_price=24.00)), today=TODAY)
    guanciale = db.query(Ingredient).filter(Ingredient.name == "guanciale").one()
    add_dish("Carbonara", 14.00, DishType.MAIN, recipe=[(guanciale, 80)])

    with pytest.raises(HTTPException) as e:
        undo_import_route(record.id, db)
    assert e.value.status_code == 422
    assert best_price(db, guanciale.id) is not None   # nothing was removed


def test_imports_are_listed_newest_first(db, stock):
    apply_invoice(db, apply_in(mozz_apply(stock), number="A"), today=TODAY)
    apply_invoice(db, apply_in(mozz_apply(stock), number="B"), today=TODAY)

    assert [i.reference for i in list_imports(db)] == ["B", "A"]
