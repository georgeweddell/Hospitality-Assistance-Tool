"""
Tests for uploading a menu (POST /imports/menu/read) and the prompt Claude is
given. Claude is replaced by a fake: no API credit, same result every time.
"""

import io
from datetime import date

import anthropic
import httpx
import pytest
from fastapi import HTTPException, UploadFile

import main
from menu_ai import build_menu_prompt
from models import DishType
from schemas import MenuDraft, MenuItemDraft, MenuReviewIn

PDF = b"%PDF-1.4 a made-up menu"


@pytest.fixture
def uploads(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "UPLOAD_DIR", tmp_path)
    return tmp_path


@pytest.fixture
def fake_claude(monkeypatch):
    calls = []

    def fake_read_menu(db, content, media_type):
        calls.append(media_type)
        return MenuDraft(items=[MenuItemDraft(name="Margherita", price=11.50, category=DishType.MAIN),
                                MenuItemDraft(name="Carbonara Pizza", price=14.50, category=DishType.MAIN),
                                MenuItemDraft(name="Peroni 330ml", price=5.00, kind="other")])

    monkeypatch.setattr(main, "read_menu", fake_read_menu)
    return calls


def upload(content=PDF, filename="menu.pdf"):
    return UploadFile(file=io.BytesIO(content), filename=filename)


def test_an_uploaded_menu_is_compared_with_the_stored_dishes(db, add_dish, cost_item, uploads, fake_claude):
    add_dish("Margherita", 11.00, DishType.MAIN, recipe=[(cost_item, 2)])
    add_dish("Cannoli", 7.00, DishType.DESSERT, recipe=[(cost_item, 1)])

    review = main.read_menu_route(upload(), date(2026, 10, 1), db)

    assert [(i.name, i.status) for i in review.items] == [
        ("Margherita", "price"), ("Carbonara Pizza", "new"), ("Peroni 330ml", "not_a_dish")]
    assert [d.name for d in review.leaving] == ["Cannoli"]
    assert review.start_date == date(2026, 10, 1)
    assert (uploads / f"{review.file_hash}.pdf").exists()


def test_changing_the_start_date_compares_again_without_claude(db, add_dish, cost_item, uploads, fake_claude):
    add_dish("Margherita", 11.00, DishType.MAIN, recipe=[(cost_item, 2)])
    first = main.read_menu_route(upload(), date(2026, 10, 1), db)

    again = main.review_menu_route(MenuReviewIn(items=first.items, start_date=date(2026, 11, 1)), db)
    assert again.start_date == date(2026, 11, 1)
    assert [i.status for i in again.items] == [i.status for i in first.items]
    assert len(fake_claude) == 1   # Claude read it once


def test_the_start_date_defaults_to_today(db, uploads, fake_claude):
    assert main.read_menu_route(upload(), None, db).start_date == date.today()


def test_a_photo_is_accepted_and_other_files_refused(db, uploads, fake_claude):
    main.read_menu_route(upload(b"\x89PNG menu photo", "menu.png"), None, db)
    assert fake_claude == ["image/png"]

    with pytest.raises(HTTPException) as e:
        main.read_menu_route(upload(b"hello", "menu.docx"), None, db)
    assert e.value.status_code == 422


def test_claude_unreachable_gives_a_503(db, uploads, monkeypatch):
    def unreachable(db, content, media_type):
        raise anthropic.APIConnectionError(request=httpx.Request("POST", "https://api.anthropic.com"))

    monkeypatch.setattr(main, "read_menu", unreachable)
    with pytest.raises(HTTPException) as e:
        main.read_menu_route(upload(), None, db)
    assert e.value.status_code == 503


def test_the_prompt_lists_the_stored_dishes():
    assert "Margherita, Diavola" in build_menu_prompt(["Margherita", "Diavola"])
    assert "(none yet)" in build_menu_prompt([])
