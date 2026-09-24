"""
Tests for uploading a till export (POST /imports/sales/read) and for what
Claude is sent. Claude is replaced by fakes: no API credit, same result every time.
"""

import io
from datetime import date

import anthropic
import httpx
import pytest
from fastapi import HTTPException, UploadFile

import main
from models import DishType
from schemas import SalesApplyIn, TillColumnsDraft, TillItemHint, TillMappingIn
from till_ai import build_columns_prompt, build_items_prompt, check_columns, redact
from tills import apply_sales, read_csv

CSV = """Date,Time,Item,Qty,Event Type,Customer Name,Card Brand
18/09/2026,12:01,Margherita,2,Payment,Jo Bloggs,Visa
18/09/2026,12:40,Margherita,1,Refund,,
18/09/2026,13:05,Peroni 330ml,3,Payment,Sam Smith,Amex
19/09/2026,19:30,MARG 12,4,Payment,,
19/09/2026,19:45,Diavola,2,Payment,,
20/09/2026,19:45,Diavola,1,Payment,Row Six,
"""
MAPPING = TillMappingIn(date_column="Date", item_column="Item", quantity_column="Qty", date_format="%d/%m/%Y",
                        refund_column="Event Type", refund_value="Refund")


@pytest.fixture
def menu(add_dish, cost_item):
    return {
        "margherita": add_dish("Margherita", 11.00, DishType.MAIN, recipe=[(cost_item, 2)]),
        "diavola": add_dish("Diavola", 12.50, DishType.MAIN, recipe=[(cost_item, 2)]),
    }


@pytest.fixture
def uploads(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "UPLOAD_DIR", tmp_path)
    return tmp_path


@pytest.fixture
def fake_claude(monkeypatch):
    """Records what each call was sent; proposes MAPPING and knows MARG 12 and Peroni."""
    calls = {"columns": [], "items": []}

    def propose_columns(header, rows):
        calls["columns"].append(header)
        return MAPPING

    def suggest_items(items, dish_names):
        calls["items"].append(sorted(items))
        known = {"MARG 12": TillItemHint(item="MARG 12", likely_dish="Margherita"),
                 "Peroni 330ml": TillItemHint(item="Peroni 330ml", kind="other")}
        return [known[i] for i in items if i in known]

    monkeypatch.setattr(main, "propose_columns", propose_columns)
    monkeypatch.setattr(main, "suggest_items", suggest_items)
    return calls


def upload(text=CSV, filename="sales.csv"):
    return UploadFile(file=io.BytesIO(text.encode("utf-8")), filename=filename)


# --- What Claude is sent -------------------------------------------------------------

def test_customer_details_are_blanked():
    header, rows = read_csv(CSV)
    first = redact(header, rows)[0]

    assert first[header.index("Item")] == "Margherita"
    assert first[header.index("Customer Name")] == "" and first[header.index("Card Brand")] == ""


def test_claude_sees_only_the_header_and_five_rows():
    prompt = build_columns_prompt(*read_csv(CSV))

    assert "Date,Time,Item,Qty" in prompt
    assert "20/09/2026" not in prompt          # row 6
    assert "Jo Bloggs" not in prompt and "Sam Smith" not in prompt


def test_the_items_prompt_lists_the_menu():
    assert "Margherita, Diavola" in build_items_prompt(["MARG 12"], ["Margherita", "Diavola"])


# --- Checking Claude's proposal ------------------------------------------------------------

def test_a_proposed_column_that_doesnt_exist_is_rejected():
    header, rows = read_csv(CSV)
    draft = TillColumnsDraft(date_column="Date", item_column="Product", quantity_column="Qty", date_format="%d/%m/%Y")

    assert check_columns(draft, header, rows) is None


def test_a_wrong_date_format_is_corrected_from_the_data():
    # "18/09/2026" can't be month-first (there's no month 18), so day-first is used.
    header, rows = read_csv(CSV)
    draft = TillColumnsDraft(date_column="Date", item_column="Item", quantity_column="Qty", date_format="%m/%d/%Y")

    assert check_columns(draft, header, rows).date_format == "%d/%m/%Y"


def test_a_refund_column_needs_a_value():
    header, rows = read_csv(CSV)
    draft = TillColumnsDraft(date_column="Date", item_column="Item", quantity_column="Qty",
                             date_format="%d/%m/%Y", refund_column="Event Type")

    assert check_columns(draft, header, rows).refund_column is None


# --- The upload route ------------------------------------------------------------------------

def test_an_upload_is_mapped_matched_and_kept(db, menu, uploads, fake_claude):
    review = main.read_sales_route(upload(), db)
    items = {it.item: it for it in review.items}

    assert review.mapping == MAPPING
    assert items["MARG 12"].dish_id == menu["margherita"].id       # Claude's suggestion
    assert (items["Peroni 330ml"].action, items["Peroni 330ml"].kind) == ("ignore", "other")
    assert fake_claude["items"] == [["MARG 12", "Peroni 330ml"]]   # exact dish names aren't sent
    assert (uploads / f"{review.file_hash}.csv").exists()


def test_a_known_layout_and_known_items_skip_claude(db, menu, uploads, fake_claude):
    first = main.read_sales_route(upload(), db)
    choices = [{"item": it.item, "action": it.action, "dish_id": it.dish_id} for it in first.items]
    apply_sales(db, CSV, SalesApplyIn(file_hash=first.file_hash, mapping=first.mapping, choices=choices),
                today=date(2026, 9, 24))

    later = main.read_sales_route(upload(CSV + "21/09/2026,12:00,Margherita,1,Payment,,\n"), db)

    assert later.mapping_remembered
    assert len(fake_claude["columns"]) == 1       # not asked again
    assert all(asked == [] for asked in fake_claude["items"][1:])   # nothing unknown to ask about


def test_claude_unreachable_still_opens_the_review(db, menu, uploads, monkeypatch):
    def unreachable(header, rows):
        raise anthropic.APIConnectionError(request=httpx.Request("POST", "https://api.anthropic.com"))

    monkeypatch.setattr(main, "propose_columns", unreachable)
    review = main.read_sales_route(upload(), db)

    assert (review.ai_unavailable, review.mapping) == (True, None)
    assert review.header[:4] == ["Date", "Time", "Item", "Qty"]


@pytest.mark.parametrize("text, filename", [
    (CSV, "sales.xlsx"),              # not a CSV
    ("just one line\n", "sales.csv"),  # no rows, too few columns
], ids=["not csv", "not an export"])
def test_unsuitable_files_are_refused(db, uploads, fake_claude, text, filename):
    with pytest.raises(HTTPException) as e:
        main.read_sales_route(upload(text, filename), db)
    assert e.value.status_code == 422
    assert fake_claude["columns"] == []
