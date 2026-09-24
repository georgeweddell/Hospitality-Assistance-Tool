"""
Till import: sales from a CSV exported by the till (Square, Zettle, SumUp...).

Claude only proposes which column is which and what each item name probably
is (see till_ai.py). Everything here is plain Python, so it can be tested:

  parse_sales        reads every row with the chosen columns, nets refunds,
                     and adds up units per till item per day.
  review_sales       matches items to dishes and works out, for every dish
                     and day, whether the sale is new, replaces an earlier
                     till import, or clashes with sales entered another way.
                     Saves nothing.
  apply_sales        saves daily totals per dish (each carrying import_id)
                     after checking everything, and remembers the choices.
  undo_sales_import  removes the daily totals an import added.

The overlap rules (agreed with George):
  - A dish-day already covered by an earlier till import is REPLACED
    (owners export "month to date" again and again).
  - A dish-day covered by sales entered another way (a typed total, or the
    demo's seeded data) is SKIPPED and listed: never deleted, never doubled.
  - A sale's date is the calendar date on the till (00:30 is the next day).
"""

import csv
import io
from collections import defaultdict
from datetime import date, datetime
from difflib import get_close_matches

from invoices import ImportProblem, normalise
from models import Dish, Import, ImportKind, ImportStatus, SalesRecord, TillItemAlias, TillMapping
from schemas import DishSuggestion, SalesItemOut, SalesReviewOut, TillMappingIn

SAMPLE_ROWS = 5   # rows shown to help choose columns (and, in till_ai.py, all Claude sees)


# --- Reading the file ------------------------------------------------------------------

def decode(content: bytes) -> str:
    """Tills export UTF-8 (sometimes with a byte-order mark) or, in older ones, Windows-1252."""
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return content.decode("cp1252")


def read_csv(text):
    """(header, rows). Works out whether the file uses commas, semicolons or tabs."""
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    lines = [row for row in csv.reader(io.StringIO(text), dialect) if any(cell.strip() for cell in row)]
    if not lines:
        raise ImportProblem("The file is empty")
    header = [cell.strip() for cell in lines[0]]
    return header, lines[1:]


def header_signature(header):
    """The header row, normalised. The same export layout gives the same signature."""
    return "|".join(normalise(h) for h in header)


def parse_date(value, date_format):
    """
    "18/09/2026" with "%d/%m/%Y" -> 18 Sep 2026. A time after the date is
    ignored ("2026-09-18 12:30:00", "2026-09-18T12:30"). None if it doesn't parse.
    """
    text = (value or "").strip()
    for candidate in (text, text.replace("T", " ").split(" ")[0]):
        try:
            return datetime.strptime(candidate, date_format).date()
        except ValueError:
            continue
    return None


def parse_quantity(value):
    """ "2", "2.0", "-1", "1,200" -> a number. None if it isn't one."""
    try:
        return float((value or "").strip().replace(",", ""))
    except ValueError:
        return None


def parse_sales(header, rows, mapping):
    """
    Reads every row with the chosen columns.

    Returns (totals, skipped):
      totals  {till item name: {day: net units}}
      skipped {reason: rows skipped}

    Refunds are netted: a negative quantity already is, and a row whose refund
    column holds the refund value counts as minus its quantity. Only the item
    column is read, so modifiers in other columns are ignored.
    """
    missing = [c for c in (mapping.date_column, mapping.item_column, mapping.quantity_column, mapping.refund_column)
               if c and c not in header]
    if missing:
        raise ImportProblem(f"The file has no column called '{missing[0]}'")
    col = {name: header.index(name) for name in header}

    def cell(row, name):
        i = col[name]
        return row[i] if i < len(row) else ""

    totals = defaultdict(lambda: defaultdict(float))
    skipped = defaultdict(int)
    for row in rows:
        item = cell(row, mapping.item_column).strip()
        if not item:
            skipped["No item name"] += 1
            continue
        day = parse_date(cell(row, mapping.date_column), mapping.date_format)
        if day is None:
            skipped["Date not readable"] += 1
            continue
        quantity = parse_quantity(cell(row, mapping.quantity_column))
        if quantity is None:
            skipped["Quantity not a number"] += 1
            continue
        if mapping.refund_column and mapping.refund_value and \
                normalise(cell(row, mapping.refund_column)) == normalise(mapping.refund_value):
            quantity = -abs(quantity)
        totals[item][day] += quantity
    return totals, dict(skipped)


# --- Matching and overlaps ------------------------------------------------------------------

def remembered_mapping(db, header):
    row = db.query(TillMapping).filter(TillMapping.header_signature == header_signature(header)).first()
    return TillMappingIn.model_validate(row) if row else None


def dish_suggestions(dishes, name, limit=3):
    names = [d.name for d in dishes]
    by_name = {d.name: d for d in dishes}
    return [DishSuggestion(id=by_name[n].id, name=n) for n in get_close_matches(name, names, n=limit, cutoff=0.45)]


def default_choice(db, item, dishes, hint):
    """
    What an item starts as, in this order:
      1. a remembered match (or ignore) for this item name
      2. a dish with exactly this name
      3. Claude's suggested dish (it must be an exact dish name)
      4. Claude says it's a drink or other non-dish: ignore
      5. otherwise the owner must choose (fuzzy suggestions offered, never chosen)
    Returns (action, dish_id, remembered).
    """
    by_name = {d.name.lower(): d for d in dishes}
    alias = db.query(TillItemAlias).filter(TillItemAlias.item == normalise(item)).first()
    if alias and (alias.ignore or alias.dish_id in {d.id for d in dishes}):
        return ("ignore", None, True) if alias.ignore else ("dish", alias.dish_id, True)
    if item.strip().lower() in by_name:
        return "dish", by_name[item.strip().lower()].id, False
    if hint and hint.likely_dish and hint.likely_dish.strip().lower() in by_name:
        return "dish", by_name[hint.likely_dish.strip().lower()].id, False
    if hint and hint.kind == "other":
        return "ignore", None, False
    return "dish", None, False


def existing_sales(db, dish_ids, first, last):
    """{dish_id: [records]} for records overlapping first..last, fetched in one query."""
    found = defaultdict(list)
    if dish_ids:
        for r in db.query(SalesRecord).filter(SalesRecord.dish_id.in_(dish_ids),
                                              SalesRecord.period_start <= last,
                                              SalesRecord.period_end >= first).all():
            found[r.dish_id].append(r)
    return found


def day_status(records, day):
    """
    "conflict": sales entered another way cover this day, so it's skipped.
    "replace":  an earlier till import has this day, so it's replaced.
    "new":      nothing yet.
    """
    covering = [r for r in records if r.period_start <= day <= r.period_end]
    if any(r.import_id is None for r in covering):
        return "conflict"
    return "replace" if covering else "new"


def plan_sales(db, text, mapping, choices=(), hints=None):
    """
    Everything review and apply need, worked out once:
      header, rows, totals, skipped, items (SalesItemOut), and to_save:
      [(dish_id, day, units, records to replace)].
    """
    header, rows = read_csv(text)
    totals, skipped = parse_sales(header, rows, mapping)
    dishes = db.query(Dish).all()
    dishes_by_id = {d.id: d for d in dishes}
    hints = {h.item: h for h in (hints or [])}
    chosen = {c.item: c for c in choices}

    items = []
    for item in sorted(totals, key=lambda i: -sum(totals[i].values())):
        hint = hints.get(item)
        action, dish_id, remembered = default_choice(db, item, dishes, hint)
        if item in chosen:
            action, dish_id = chosen[item].action, chosen[item].dish_id
        items.append(SalesItemOut(
            item=item, units=round(sum(totals[item].values())), days=len(totals[item]),
            action=action, dish_id=dish_id if action == "dish" else None, remembered=remembered,
            kind=hint.kind if hint else "dish",
            suggestions=dish_suggestions(dishes, item) if dish_id is None and action == "dish" else [],
        ))

    # Add up per dish per day: two till names for one dish are combined.
    per_dish = defaultdict(lambda: defaultdict(float))
    for it in items:
        if it.action == "dish" and it.dish_id in dishes_by_id:
            for day, units in totals[it.item].items():
                per_dish[it.dish_id][day] += units

    all_days = [day for days in totals.values() for day in days]
    first, last = (min(all_days), max(all_days)) if all_days else (None, None)
    existing = existing_sales(db, list(per_dish), first, last) if all_days else {}

    status = {}   # (dish_id, day) -> "new" | "replace" | "conflict"
    to_save = []
    for dish_id, days in per_dish.items():
        for day, units in days.items():
            s = day_status(existing.get(dish_id, []), day)
            status[(dish_id, day)] = s
            if s == "conflict" or round(units) <= 0:
                continue   # a day refunded to nothing leaves no record, like a day with no sales
            replaced = [r for r in existing.get(dish_id, []) if r.period_start <= day <= r.period_end]
            to_save.append((dish_id, day, round(units), replaced))

    for it in items:
        flags = []
        if it.action == "dish" and it.dish_id is None:
            flags.append("choose")
        if it.action == "dish" and it.dish_id in dishes_by_id:
            dish = dishes_by_id[it.dish_id]
            days = totals[it.item]
            if any(d < dish.on_menu_from or (dish.on_menu_until and d > dish.on_menu_until) for d in days):
                flags.append("off_menu")
            it.conflict_days = sum(1 for d in days if status.get((dish.id, d)) == "conflict")
            it.replace_days = sum(1 for d in days if status.get((dish.id, d)) == "replace")
            if it.conflict_days:
                flags.append("conflict")
            if it.replace_days:
                flags.append("replaces")
        it.flags = flags

    return {"header": header, "rows": rows, "totals": totals, "skipped": skipped, "items": items,
            "to_save": to_save, "first": first, "last": last}


def items_needing_hints(db, text, mapping):
    """Item names in the file that aren't remembered or exactly a dish name: only these go to Claude."""
    totals, _ = parse_sales(*read_csv(text), mapping)
    dish_names = {d.name.strip().lower() for d in db.query(Dish).all()}
    known = {a.item for a in db.query(TillItemAlias).all()}
    return [item for item in totals if item.strip().lower() not in dish_names and normalise(item) not in known]


def already_imported(db, file_hash):
    return db.query(Import).filter(Import.kind == ImportKind.SALES, Import.status == ImportStatus.APPLIED,
                                   Import.file_hash == file_hash).first()


def review_sales(db, text, file_hash, filename=None, mapping=None, choices=(), hints=None):
    """What the owner checks before applying. Without a mapping, only the columns are shown."""
    header, rows = read_csv(text)
    remembered = remembered_mapping(db, header)
    mapping = mapping or remembered
    duplicate = already_imported(db, file_hash)
    review = SalesReviewOut(file_hash=file_hash, filename=filename, header=header, samples=rows[:SAMPLE_ROWS],
                            mapping=mapping, mapping_remembered=remembered is not None and mapping == remembered,
                            already_imported=duplicate.id if duplicate else None, rows=len(rows))
    if mapping is None:
        return review

    plan = plan_sales(db, text, mapping, choices, hints)
    review.skipped = plan["skipped"]
    review.first_date, review.last_date = plan["first"], plan["last"]
    review.items = plan["items"]
    review.dish_days = len(plan["to_save"])
    review.units = sum(units for _, _, units, _ in plan["to_save"])
    review.replace_days = sum(1 for *_, replaced in plan["to_save"] if replaced)
    review.conflict_days = sum(it.conflict_days for it in plan["items"] if it.action == "dish")
    return review


# --- Saving ---------------------------------------------------------------------------------

def remember(db, header, mapping, items):
    signature = header_signature(header)
    row = db.query(TillMapping).filter(TillMapping.header_signature == signature).first()
    if row is None:
        row = TillMapping(header_signature=signature)
        db.add(row)
    for field in ("date_column", "item_column", "quantity_column", "date_format", "refund_column", "refund_value"):
        setattr(row, field, getattr(mapping, field))

    for it in items:
        alias = db.query(TillItemAlias).filter(TillItemAlias.item == normalise(it.item)).first()
        if alias is None:
            alias = TillItemAlias(item=normalise(it.item))
            db.add(alias)
        alias.ignore = it.action == "ignore"
        alias.dish_id = None if alias.ignore else it.dish_id


def apply_sales(db, text, data, today=None):
    """
    Saves a confirmed till import. Everything is checked first; if anything is
    wrong, ImportProblem is raised and nothing is saved. Returns the new Import.
    """
    today = today or date.today()

    # --- Check everything ---------------------------------------------------------
    duplicate = already_imported(db, data.file_hash)
    if duplicate:
        raise ImportProblem(f"This file was already imported on {duplicate.created_at:%d %b %Y}. "
                            "Undo that import first to import it again.")
    known = {d.id for d in db.query(Dish).all()}
    for c in data.choices:
        if c.action == "dish" and c.dish_id not in known:
            raise ImportProblem(f"'{c.item}': choose a dish or Ignore")

    plan = plan_sales(db, text, data.mapping, data.choices)
    undecided = [it.item for it in plan["items"] if "choose" in it.flags]
    if undecided:
        raise ImportProblem(f"'{undecided[0]}': choose a dish or Ignore")
    future = [day for _, day, _, _ in plan["to_save"] if day > today]
    if future:
        raise ImportProblem(f"The file has sales dated in the future ({min(future):%d %b %Y}). Check the date format.")
    if not plan["to_save"]:
        raise ImportProblem("There are no sales to save (everything is ignored or already entered another way)")

    # --- Save --------------------------------------------------------------------
    record = Import(kind=ImportKind.SALES, filename=data.filename, file_hash=data.file_hash,
                    effective_date=plan["first"], period_end=plan["last"], status=ImportStatus.APPLIED,
                    lines_applied=len(plan["to_save"]),
                    lines_ignored=sum(1 for it in plan["items"] if it.action == "ignore"))
    db.add(record)
    db.flush()   # assigns record.id

    for dish_id, day, units, replaced in plan["to_save"]:
        for old in replaced:
            db.delete(old)
        db.add(SalesRecord(dish_id=dish_id, units_sold=units, period_start=day, period_end=day, import_id=record.id))

    remember(db, plan["header"], data.mapping, plan["items"])
    db.commit()
    return record


def undo_sales_import(db, record):
    """
    Removes the daily totals this import added. Days it replaced from an
    earlier import don't come back: re-upload that earlier file to restore them.
    """
    if record.status != ImportStatus.APPLIED:
        raise ImportProblem("This import has already been undone")
    db.query(SalesRecord).filter(SalesRecord.import_id == record.id).delete()
    record.status = ImportStatus.UNDONE
    db.commit()
    return record
