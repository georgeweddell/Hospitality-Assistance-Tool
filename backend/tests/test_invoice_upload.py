"""
Tests for uploading an invoice (POST /imports/invoice/read) and the prompt
Claude is given. Claude is replaced by a fake, so no API credit is spent and
the results are always the same.
"""

import io
from datetime import date

import anthropic
import httpx
import pytest
from fastapi import HTTPException, UploadFile

import main
from invoice_ai import build_invoice_prompt, document_block
from models import UnitType
from schemas import InvoiceDraft, InvoiceLineDraft

PDF = b"%PDF-1.4 a made-up invoice"


@pytest.fixture
def uploads(tmp_path, monkeypatch):
    """Uploaded files go to a throwaway folder, not backend/uploads."""
    monkeypatch.setattr(main, "UPLOAD_DIR", tmp_path)
    return tmp_path


@pytest.fixture
def fake_claude(monkeypatch):
    """Replaces the Claude call. Records what it was sent and returns one mozzarella line."""
    calls = []

    def fake_read_invoice(db, content, media_type):
        calls.append((content, media_type))
        return InvoiceDraft(supplier="Vesuvio Foods Ltd", invoice_number="INV-1001", invoice_date=date(2026, 9, 20),
                            lines=[InvoiceLineDraft(description="MOZZ FDL 1KG x12", pack_count=12, pack_size=1,
                                                    pack_unit="kg", quantity=2, unit_price=93.60, line_total=187.20,
                                                    likely_ingredient="mozzarella")])

    monkeypatch.setattr(main, "read_invoice", fake_read_invoice)
    return calls


def upload(content, filename="invoice.pdf"):
    return UploadFile(file=io.BytesIO(content), filename=filename)


def test_an_uploaded_invoice_is_read_matched_and_kept(db, add_ingredient, uploads, fake_claude):
    mozzarella = add_ingredient("mozzarella", UnitType.GRAM, 0.0072)

    review = main.read_invoice_route(upload(PDF), db)

    assert fake_claude[0] == (PDF, "application/pdf")
    assert (review.filename, review.lines[0].ingredient_id) == ("invoice.pdf", mozzarella.id)
    assert review.lines[0].price_per_unit == pytest.approx(0.0078)
    assert (uploads / f"{review.file_hash}.pdf").read_bytes() == PDF


@pytest.mark.parametrize("content, filename", [
    (b"hello", "notes.txt"),                        # not a PDF or photo
    (b"not really a pdf", "invoice.pdf"),           # named .pdf but isn't one
    (b"%PDF" + b"x" * (10 * 1024 * 1024), "big.pdf"),   # over 10 MB
], ids=["wrong type", "not really a pdf", "too big"])
def test_unsuitable_files_are_refused_before_claude_sees_them(db, uploads, fake_claude, content, filename):
    with pytest.raises(HTTPException) as e:
        main.read_invoice_route(upload(content, filename), db)

    assert e.value.status_code == 422
    assert fake_claude == []


def test_a_photo_is_accepted(db, uploads, fake_claude):
    main.read_invoice_route(upload(b"\xff\xd8\xff\xe0 jpeg data", "Invoice.JPG"), db)

    assert fake_claude[0][1] == "image/jpeg"


def test_claude_unreachable_gives_a_503(db, uploads, monkeypatch):
    def unreachable(db, content, media_type):
        raise anthropic.APIConnectionError(request=httpx.Request("POST", "https://api.anthropic.com"))

    monkeypatch.setattr(main, "read_invoice", unreachable)
    with pytest.raises(HTTPException) as e:
        main.read_invoice_route(upload(PDF), db)
    assert e.value.status_code == 503


# --- What Claude is sent ------------------------------------------------------------

def test_the_prompt_lists_the_ingredients_to_match_against():
    prompt = build_invoice_prompt(["mozzarella", "00 flour"])

    assert "mozzarella, 00 flour" in prompt


def test_pdfs_are_sent_as_documents_and_photos_as_images():
    assert document_block(PDF, "application/pdf")["type"] == "document"
    assert document_block(b"\xff\xd8", "image/jpeg")["type"] == "image"
