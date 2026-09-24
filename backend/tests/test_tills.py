"""
Tests for till import (tills.py): reading a CSV, netting refunds, adding up
per dish per day, matching items, the overlap rules, apply and undo.

Claude isn't involved: each test gives the column mapping directly (in the
app, Claude proposes it and the owner checks it).
"""

from datetime import date

import pytest
from fastapi import HTTPException

import main
from menu_engineering import get_dish_units_sold
from models import DishType, Import, ImportStatus, SalesRecord, TillItemAlias
from schemas import SalesApplyIn, TillItemChoice, TillMappingIn
from tills import (ImportProblem, apply_sales, parse_date, parse_sales, read_csv, review_sales,
                   undo_sales_import)

TODAY = date(2026, 9, 24)
SEP = (date(2026, 9, 1), date(2026, 9, 30))

# A small Square-style export. 18 Sep: 2 + 1 Margherita, 1 refunded.
CSV = """Date,Time,Item,Qty,Modifiers Applied,Event Type,Customer Name
18/09/2026,12:01,Margherita,2,,Payment,Jo Bloggs
18/09/2026,12:15,Margherita,1,Extra basil,Payment,
18/09/2026,12:40,Margherita,1,,Refund,
18/09/2026,13:05,Peroni 330ml,3,,Payment,
19/09/2026,19:30,MARG 12,4,,Payment,
19/09/2026,19:45,Diavola,2,,Payment,
"""
MAPPING = TillMappingIn(date_column="Date", item_column="Item", quantity_column="Qty", date_format="%d/%m/%Y",
                        refund_column="Event Type", refund_value="Refund")
HASH = "a" * 64


@pytest.fixture
def menu(add_dish, cost_item):
    return {
        "margherita": add_dish("Margherita", 11.00, DishType.MAIN, recipe=[(cost_item, 2)]),
        "diavola": add_dish("Diavola", 12.50, DishType.MAIN, recipe=[(cost_item, 2)]),
    }


def choices(menu, **extra):
    """The owner's choices: MARG 12 is the Margherita, Peroni is ignored."""
    base = [TillItemChoice(item="MARG 12", action="dish", dish_id=menu["margherita"].id),
            TillItemChoice(item="Peroni 330ml", action="ignore")]
    return base + [TillItemChoice(item=k, **v) for k, v in extra.items()]


def apply(db, menu, text=CSV, file_hash=HASH, **kw):
    return apply_sales(db, text, SalesApplyIn(file_hash=file_hash, mapping=kw.get("mapping", MAPPING),
                                              choices=kw.get("choices", choices(menu))), today=TODAY)


# --- Reading the file ----------------------------------------------------------------

@pytest.mark.parametrize("value, fmt, expected", [
    ("18/09/2026", "%d/%m/%Y", date(2026, 9, 18)),
    ("2026-09-18", "%Y-%m-%d", date(2026, 9, 18)),
    ("2026-09-18 23:59:00", "%Y-%m-%d", date(2026, 9, 18)),   # the time is ignored
    ("2026-09-18T00:30", "%Y-%m-%d", date(2026, 9, 18)),
    ("09/18/2026", "%m/%d/%Y", date(2026, 9, 18)),
    ("18/09/26", "%d/%m/%y", date(2026, 9, 18)),
    ("not a date", "%d/%m/%Y", None),
])
def test_dates(value, fmt, expected):
    assert parse_date(value, fmt) == expected


def test_refunds_are_netted_and_modifiers_ignored():
    # 18 Sep Margherita: 2 + 1 (the "Extra basil" row still counts once) - 1 refunded = 2
    totals, skipped = parse_sales(*read_csv(CSV), MAPPING)

    assert totals["Margherita"] == {date(2026, 9, 18): 2}
    assert totals["MARG 12"] == {date(2026, 9, 19): 4}
    assert skipped == {}


def test_negative_quantities_are_refunds_too():
    text = "Date,Item,Qty\n2026-09-18,Margherita,3\n2026-09-18,Margherita,-1\n"
    mapping = TillMappingIn(date_column="Date", item_column="Item", quantity_column="Qty", date_format="%Y-%m-%d")

    totals, _ = parse_sales(*read_csv(text), mapping)
    assert totals["Margherita"] == {date(2026, 9, 18): 2}


def test_bad_rows_are_counted_not_guessed():
    text = CSV + "32/09/2026,12:00,Margherita,1,,Payment,\n19/09/2026,12:00,,1,,Payment,\n19/09/2026,12:00,Diavola,two,,Payment,\n"

    _, skipped = parse_sales(*read_csv(text), MAPPING)
    assert skipped == {"Date not readable": 1, "No item name": 1, "Quantity not a number": 1}


def test_semicolon_files_are_read():
    header, rows = read_csv("Date;Item;Qty\n18/09/2026;Margherita;2\n")
    assert header == ["Date", "Item", "Qty"] and rows == [["18/09/2026", "Margherita", "2"]]


def test_a_missing_column_is_reported():
    wrong = MAPPING.model_copy(update={"quantity_column": "Quantity"})
    with pytest.raises(ImportProblem, match="Quantity"):
        parse_sales(*read_csv(CSV), wrong)


# --- Review ------------------------------------------------------------------------

def test_review_matches_exact_names_and_asks_about_the_rest(db, menu):
    review = review_sales(db, CSV, HASH, mapping=MAPPING)
    items = {it.item: it for it in review.items}

    assert (items["Margherita"].dish_id, items["Diavola"].dish_id) == (menu["margherita"].id, menu["diavola"].id)
    assert (items["MARG 12"].dish_id, items["MARG 12"].flags) == (None, ["choose"])
    assert review.samples[0][2] == "Margherita"
    assert (review.first_date, review.last_date) == (date(2026, 9, 18), date(2026, 9, 19))


def test_two_till_names_for_one_dish_are_combined(db, menu):
    # Margherita: 2 on 18 Sep (as the till names it) + 4 on 19 Sep (as MARG 12)
    # Diavola: 2 on 19 Sep.  3 daily totals, 8 units. Peroni ignored.
    review = review_sales(db, CSV, HASH, mapping=MAPPING, choices=choices(menu))

    assert (review.dish_days, review.units) == (3, 8)


def test_an_unknown_layout_asks_for_columns(db, menu):
    review = review_sales(db, CSV, HASH)
    assert (review.mapping, review.items) == (None, [])


# --- Apply -------------------------------------------------------------------------

def test_apply_saves_daily_totals_per_dish(db, menu):
    record = apply(db, menu)

    assert get_dish_units_sold(db, menu["margherita"].id, *SEP) == 6
    assert get_dish_units_sold(db, menu["diavola"].id, *SEP) == 2
    saved = db.query(SalesRecord).filter(SalesRecord.import_id == record.id).all()
    assert all(r.period_start == r.period_end for r in saved)   # one record per dish per day
    assert (record.effective_date, record.period_end, record.lines_applied) == (date(2026, 9, 18), date(2026, 9, 19), 3)


def test_the_mapping_and_choices_are_remembered(db, menu):
    apply(db, menu)

    review = review_sales(db, CSV.replace("12:01", "12:02"), "b" * 64)   # a later export, same layout
    items = {it.item: it for it in review.items}
    assert review.mapping_remembered
    assert (items["MARG 12"].dish_id, items["MARG 12"].remembered) == (menu["margherita"].id, True)
    assert (items["Peroni 330ml"].action, items["Peroni 330ml"].remembered) == ("ignore", True)


def test_a_later_export_replaces_the_days_it_covers(db, menu):
    apply(db, menu)
    # Month to date again: 19 Sep Diavola is now 5 (a late tab was added).
    later = CSV.replace("19/09/2026,19:45,Diavola,2", "19/09/2026,19:45,Diavola,5")

    review = review_sales(db, later, "b" * 64, mapping=MAPPING, choices=choices(menu))
    assert review.replace_days == 3
    apply(db, menu, text=later, file_hash="b" * 64)

    assert get_dish_units_sold(db, menu["diavola"].id, *SEP) == 5   # replaced, not 2 + 5


def test_sales_entered_another_way_are_skipped_not_doubled(db, menu, add_sales):
    add_sales(menu["diavola"], 30, date(2026, 9, 1), date(2026, 9, 30))   # a typed September total

    review = review_sales(db, CSV, HASH, mapping=MAPPING, choices=choices(menu))
    diavola = next(it for it in review.items if it.item == "Diavola")
    assert (diavola.conflict_days, diavola.flags) == (1, ["conflict"])
    apply(db, menu)

    assert get_dish_units_sold(db, menu["diavola"].id, *SEP) == 30   # the typed total, untouched
    assert get_dish_units_sold(db, menu["margherita"].id, *SEP) == 6


def test_sales_outside_the_menu_dates_are_saved_with_a_warning(db, add_dish, cost_item):
    add_dish("Margherita", 11.00, DishType.MAIN, recipe=[(cost_item, 2)])
    add_dish("Diavola", 12.50, DishType.MAIN, recipe=[(cost_item, 2)], on_menu_until=date(2026, 8, 31))

    review = review_sales(db, CSV, HASH, mapping=MAPPING)
    diavola = next(it for it in review.items if it.item == "Diavola")
    assert diavola.flags == ["off_menu"]


@pytest.mark.parametrize("problem", ["undecided item", "future date", "same file", "nothing to save"])
def test_apply_refuses(db, menu, problem):
    if problem == "undecided item":
        kw = {"choices": []}                     # MARG 12 has no dish
    elif problem == "future date":
        kw = {"text": CSV.replace("19/09/2026", "25/09/2026")}
    elif problem == "same file":
        apply(db, menu)
        kw = {}
    else:
        kw = {"choices": [TillItemChoice(item=i, action="ignore")
                          for i in ("Margherita", "MARG 12", "Diavola", "Peroni 330ml")]}

    with pytest.raises(ImportProblem):
        apply(db, menu, **kw)
    assert db.query(Import).filter(Import.status == ImportStatus.APPLIED).count() == (1 if problem == "same file" else 0)


def test_nothing_is_saved_when_apply_is_refused(db, menu):
    with pytest.raises(ImportProblem):
        apply(db, menu, choices=[])

    assert db.query(SalesRecord).count() == 0
    assert db.query(TillItemAlias).count() == 0


# --- Undo and routes -------------------------------------------------------------------

def test_undo_removes_the_imported_sales(db, menu):
    record = apply(db, menu)
    main.undo_import_route(record.id, db)

    assert db.query(SalesRecord).count() == 0
    assert db.get(Import, record.id).status == ImportStatus.UNDONE
    with pytest.raises(ImportProblem):
        undo_sales_import(db, record)


def test_uploads_are_found_by_hash_only(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "UPLOAD_DIR", tmp_path)
    (tmp_path / f"{HASH}.csv").write_bytes(b"\xef\xbb\xbfDate,Item,Qty\n")   # with a byte-order mark

    assert main.load_upload(HASH, ".csv").startswith("Date")
    for bad in ("../secrets", "A" * 64, "b" * 64):
        with pytest.raises(HTTPException):
            main.load_upload(bad, ".csv")
