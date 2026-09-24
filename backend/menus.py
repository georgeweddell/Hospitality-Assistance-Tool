"""
Menu import: everything after Claude has read the menu (see menu_ai.py).

Owners upload their menu whenever it changes, so an import RECONCILES: it
compares the new menu with the dishes already stored and proposes only the
differences, all dated from the day the new menu starts.

  review_menu  sorts every menu item into: new, same, price change, renamed?
               (a close match: the owner must answer), returning (a dish that
               came off the menu before), or not a dish; and lists the dishes
               on the menu now that the new menu doesn't have. Saves nothing.
  apply_menu   saves what the owner confirmed, after checking everything.

Rules (agreed with George):
  - A new dish goes on the menu from the start date, priced from that date.
  - A price change is a new dated menu price; the old one is kept.
  - A dish missing from the new menu comes off the day before (never deleted),
    unless the owner keeps it (e.g. it's on a specials board).
  - A close name is never merged automatically: "same dish, renamed" or "new dish".
  - A changed description keeps the dish and sets recipe_check (a reminder only).
  - Existing dishes keep the category the owner set; new ones get Claude's.
  - A returning dish becomes a new dish record with the old recipe copied, so the
    old record's history (and the months it was off) stays correct.
  - Menu imports can't be undone; their changes can be edited by hand.
"""

from datetime import date, timedelta
from difflib import get_close_matches

from sqlalchemy import func

from costing import menu_price_on
from invoices import ImportProblem, normalise
from models import (Dish, DishIngredient, Import, ImportKind, ImportStatus, MenuIgnoredItem, MenuPrice,
                    MenuPriceSource, SalesRecord, TillItemAlias)
from schemas import DishSuggestion, MenuLeavingOut, MenuReviewItem, MenuReviewOut

RENAME_CUTOFF = 0.6   # how alike two names must be (0-1, difflib) to ask "renamed?"


def on_menu_at(dish, day):
    """Still on the menu on `day` (or due to come on later)."""
    return dish.on_menu_until is None or dish.on_menu_until >= day


def already_imported(db, file_hash):
    if not file_hash:
        return None
    return db.query(Import).filter(Import.kind == ImportKind.MENU, Import.status == ImportStatus.APPLIED,
                                   Import.file_hash == file_hash).first()


def review_menu(db, draft, start_date, filename=None, file_hash=None):
    """Compares a menu with the stored dishes. Saves nothing."""
    dishes = db.query(Dish).all()
    current = [d for d in dishes if on_menu_at(d, start_date)]
    current_by_name = {d.name.strip().lower(): d for d in current}
    ignored = {row.name for row in db.query(MenuIgnoredItem).all()}

    # Exact matches first, so a dish matched exactly isn't also offered as a rename.
    exact_ids = {current_by_name[i.name.strip().lower()].id for i in draft.items
                 if i.kind == "dish" and i.name.strip().lower() in current_by_name}
    unmatched = [d for d in current if d.id not in exact_ids]

    items = []
    for item in draft.items:
        review = MenuReviewItem(**item.model_dump(), status="new", action="new")
        key = item.name.strip().lower()

        if item.kind == "other" or normalise(item.name) in ignored:
            review.status, review.action = "not_a_dish", "ignore"
            review.remembered = normalise(item.name) in ignored
        elif key in current_by_name:
            dish = current_by_name[key]
            price = menu_price_on(db, dish.id, start_date)
            review.action, review.dish_id = "match", dish.id
            review.current_name, review.current_price, review.current_category = dish.name, price, dish.category
            review.status = "price" if item.price is not None and abs(item.price - price) >= 0.005 else "same"
            review.description_changed = bool(dish.description and item.description
                                              and normalise(dish.description) != normalise(item.description))
        else:
            # Close to a dish on the menu now that nothing matched exactly? Ask; never merge.
            names = [d.name for d in unmatched]
            close = get_close_matches(item.name, names, n=3, cutoff=RENAME_CUTOFF)
            if item.likely_existing in names and item.likely_existing not in close:
                close = [item.likely_existing] + close
            gone = [d for d in dishes if d.name.strip().lower() == key and not on_menu_at(d, start_date)]
            if close:
                candidate = next(d for d in unmatched if d.name == close[0])
                review.status, review.action, review.dish_id = "renamed", None, candidate.id
                review.current_name = candidate.name
                review.current_price = menu_price_on(db, candidate.id, start_date)
                review.current_category = candidate.category
                review.suggestions = [DishSuggestion(id=d.id, name=d.name) for d in unmatched if d.name in close]
            elif gone:
                old = max(gone, key=lambda d: d.on_menu_until)
                review.status, review.copy_from, review.current_name = "returning", old.id, old.name
        items.append(review)

    # On the menu now, but not matched exactly by anything on the new menu.
    # (A dish the owner confirms as "renamed" is removed from this list on screen.)
    leaving = [MenuLeavingOut(dish_id=d.id, name=d.name, category=d.category,
                              price=menu_price_on(db, d.id, start_date)) for d in unmatched]

    duplicate = already_imported(db, file_hash)
    return MenuReviewOut(filename=filename, file_hash=file_hash, start_date=start_date,
                         already_imported=duplicate.id if duplicate else None,
                         latest_sale=db.query(func.max(SalesRecord.period_end)).scalar(),
                         items=items, leaving=leaving)


def apply_menu(db, data):
    """
    Saves a confirmed menu. Everything is checked first; if anything is wrong,
    ImportProblem is raised and nothing is saved. Returns the new Import.
    """
    start = data.start_date
    dishes = {d.id: d for d in db.query(Dish).all()}

    # --- Check everything ---------------------------------------------------------
    duplicate = already_imported(db, data.file_hash)
    if duplicate:
        raise ImportProblem(f"This menu was already imported on {duplicate.created_at:%d %b %Y}")

    kept = [i for i in data.items if i.action != "ignore"]
    matched = [i.dish_id for i in kept if i.action == "match"]
    for item in kept:
        if not item.name.strip():
            raise ImportProblem("Every dish needs a name")
        if item.price is None or item.price <= 0:
            raise ImportProblem(f"{item.name}: enter a price above £0")
        if item.action == "match" and item.dish_id not in dishes:
            raise ImportProblem(f"{item.name}: choose which dish it is, or add it as new")
    if len(matched) != len(set(matched)):
        raise ImportProblem("Two menu items are matched to the same dish")
    for dish_id in data.take_off:
        if dish_id not in dishes:
            raise ImportProblem("A dish to take off doesn't exist")
        if dish_id in matched:
            raise ImportProblem(f"{dishes[dish_id].name} is on the new menu, so it can't come off")
        if dishes[dish_id].on_menu_from > start - timedelta(days=1):
            raise ImportProblem(f"{dishes[dish_id].name} only goes on the menu on or after this menu starts. "
                                "Change its dates on the dish page instead.")

    # Names that will be on the menu after this: matched dishes (by their new
    # names), new dishes, and current dishes that aren't matched or taken off.
    staying = [d.name for d in dishes.values()
               if on_menu_at(d, start) and d.id not in matched and d.id not in data.take_off]
    names = [n.strip().lower() for n in staying] + [i.name.strip().lower() for i in kept]
    clash = next((n for n in names if names.count(n) > 1), None)
    if clash:
        raise ImportProblem(f"Two dishes on the menu would be called '{clash}'")

    changes = sum(1 for i in kept if i.action == "new") + len(data.take_off)
    for item in kept:
        if item.action == "match":
            dish = dishes[item.dish_id]
            changes += (dish.name != item.name.strip()
                        or abs(menu_price_on(db, dish.id, start) - item.price) >= 0.005
                        or normalise(dish.description) != normalise(item.description))
    if changes == 0:
        raise ImportProblem("This menu matches what's stored: there's nothing to change")

    # --- Save --------------------------------------------------------------------
    record = Import(kind=ImportKind.MENU, filename=data.filename, file_hash=data.file_hash, effective_date=start,
                    status=ImportStatus.APPLIED, lines_applied=len(kept), lines_ignored=len(data.items) - len(kept))
    db.add(record)
    db.flush()

    def price_from_start(dish_id, price):
        db.add(MenuPrice(dish_id=dish_id, price=price, source=MenuPriceSource.MENU,
                         effective_date=start, import_id=record.id))

    for item in kept:
        if item.action == "match":
            dish = dishes[item.dish_id]
            dish.name = item.name.strip()   # a rename keeps the dish: recipe, sales and prices stay
            if abs(menu_price_on(db, dish.id, start) - item.price) >= 0.005:
                price_from_start(dish.id, item.price)
            if dish.description and item.description and normalise(dish.description) != normalise(item.description):
                dish.recipe_check = True
            if item.description:
                dish.description = item.description
            if dish.category is None:
                dish.category = item.category
        else:
            dish = Dish(name=item.name.strip(), category=item.category, description=item.description,
                        on_menu_from=start, import_id=record.id)
            db.add(dish)
            db.flush()
            price_from_start(dish.id, item.price)
            old = dishes.get(item.copy_from)
            if old is not None:   # a returning dish: bring its recipe and till matches across
                for row in db.query(DishIngredient).filter(DishIngredient.dish_id == old.id).all():
                    db.add(DishIngredient(dish_id=dish.id, ingredient_id=row.ingredient_id, quantity=row.quantity))
                dish.skipped_ingredients = list(old.skipped_ingredients or [])
                db.query(TillItemAlias).filter(TillItemAlias.dish_id == old.id).update({"dish_id": dish.id})

    for dish_id in data.take_off:
        dishes[dish_id].on_menu_until = start - timedelta(days=1)

    # Remember what was ignored; forget any the owner has now added back.
    for item in data.items:
        name = normalise(item.name)
        known = db.query(MenuIgnoredItem).filter(MenuIgnoredItem.name == name).first()
        if item.action == "ignore" and known is None:
            db.add(MenuIgnoredItem(name=name))
        elif item.action != "ignore" and known is not None:
            db.delete(known)

    db.commit()
    return record
