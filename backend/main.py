from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from menu_engineering import classify_all_dishes, build_action_list, list_incomplete_dishes, get_dish_units_sold, on_menu_during
from costing import cost_dish, best_price, menu_price_on, menu_prices
from database import Base, engine
import models
import schemas
from fastapi import Depends, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session
from database import get_db
from schemas import DishClassificationOut, DishCostOut, IngredientCreate, IngredientOut, IngredientPriceCreate, IngredientPriceOut, DishType, DishCreate, DishUpdate, DishOut, DishDetailOut, MenuPriceOut, RecipeLineOut, MatchedIngredientDraft, RecipeSaveOut, SalesRecordCreate, SalesRecordOut, ActionItemOut, IncompleteDishOut, SalesCoverageOut, SalesEntryIn, SalesEntryOut, SetupStatusOut, ResetIn, BenchmarkSyncOut, InvoiceDraft, InvoiceReviewOut, InvoiceApplyIn, ImportOut, SalesReviewIn, SalesReviewOut, SalesApplyIn
from models import Dish, DishIngredient, Import, ImportKind, Ingredient, IngredientPrice, MenuPrice, MenuPriceSource, SalesRecord, TillItemAlias
from recipe_ai import estimate_recipe
from matching import match_recipe_ingredients
from datetime import date, timedelta
import anthropic
from sqlalchemy import func
from units import price_per_base_unit
from periods import resolve_range
from onboarding import setup_status
from seed_demo import backup_database, reset_database
from benchmarks import sync_benchmarks
from invoices import ImportProblem, apply_invoice, review_invoice, undo_import
from invoice_ai import read_invoice
from tills import apply_sales, decode, review_sales, undo_sales_import
import re
import hashlib
from pathlib import Path


Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message":"Hello World"}

def ingredient_out(db, ingredient, used_in=0):
    """An ingredient with the price costing currently uses for it."""
    price = best_price(db, ingredient.id)
    return IngredientOut(
        id=ingredient.id,
        name=ingredient.name,
        unit=ingredient.unit,
        price_per_unit=price.price_per_unit if price else None,
        price_source=price.source if price else None,
        price_date=price.effective_date if price else None,
        used_in=used_in,
    )

def base_unit_price(price_input, ingredient_unit):
    """The price per gram / ml / each, however it was entered (see units.py)."""
    if price_input.price_per_unit is not None:
        return price_input.price_per_unit
    try:
        return price_per_base_unit(price_input.pack_price, price_input.pack_quantity,
                                   price_input.pack_unit, ingredient_unit)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

@app.get("/ingredients",  response_model=list[IngredientOut])
def list_ingredients(db: Session = Depends(get_db)):
    # How many dishes use each ingredient, in one query rather than one per ingredient.
    used_in = dict(
        db.query(DishIngredient.ingredient_id, func.count(func.distinct(DishIngredient.dish_id)))
        .group_by(DishIngredient.ingredient_id)
        .all()
    )
    return [ingredient_out(db, i, used_in.get(i.id, 0)) for i in db.query(Ingredient).all()]

@app.post("/ingredients", response_model=IngredientOut)
def create_ingredient(ingredient: IngredientCreate, db: Session = Depends(get_db)):
    # Names must be unique (ignoring case): matching looks ingredients up by name.
    name = ingredient.name.strip()
    if db.query(Ingredient).filter(func.lower(Ingredient.name) == name.lower()).first():
        raise HTTPException(status_code=422, detail=f"There's already an ingredient called '{name}'")
    price_per_unit = base_unit_price(ingredient, ingredient.unit)

    # Every ingredient starts with a price, so costing never meets one without.
    new_ingredient = Ingredient(
        name = name,
        unit = ingredient.unit)
    db.add(new_ingredient)
    db.flush()  # assigns new_ingredient.id without committing yet

    db.add(IngredientPrice(
        ingredient_id = new_ingredient.id,
        price_per_unit = price_per_unit,
        source = ingredient.source,
        supplier = ingredient.supplier,
        effective_date = date.today()))
    db.commit()

    return ingredient_out(db, new_ingredient)

@app.get("/ingredients/{ingredient_id}/prices", response_model=list[IngredientPriceOut])
def list_ingredient_prices(ingredient_id: int, db: Session = Depends(get_db)):
    ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    return (db.query(IngredientPrice)
            .filter(IngredientPrice.ingredient_id == ingredient_id)
            .order_by(IngredientPrice.effective_date.desc(), IngredientPrice.id.desc())
            .all())

@app.post("/ingredients/{ingredient_id}/prices", response_model=IngredientPriceOut)
def add_ingredient_price(ingredient_id: int, price: IngredientPriceCreate, db: Session = Depends(get_db)):
    ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    new_price = IngredientPrice(
        ingredient_id=ingredient_id,
        price_per_unit=base_unit_price(price, ingredient.unit),
        source=price.source,
        supplier=price.supplier,
        effective_date=price.effective_date,
    )
    db.add(new_price)
    db.commit()
    db.refresh(new_price)

    return new_price

def dish_out(db, dish):
    """A dish with its menu price today."""
    return DishOut(id=dish.id, name=dish.name, menu_price=menu_price_on(db, dish.id), category=dish.category,
                   on_menu_from=dish.on_menu_from, on_menu_until=dish.on_menu_until)

@app.get("/dishes", response_model=list[DishOut])
def fetch_dish(db: Session = Depends(get_db)):
    return [dish_out(db, d) for d in db.query(Dish).all()]

@app.post("/dishes", response_model=DishOut)
def create_dish(dish: DishCreate, db: Session = Depends(get_db)):
    new_dish = Dish(**dish.model_dump(exclude={"menu_price"}))
    db.add(new_dish)
    db.flush()  # assigns new_dish.id without committing yet

    # The first price runs from the day the dish went on the menu.
    db.add(MenuPrice(dish_id=new_dish.id, price=dish.menu_price, source=MenuPriceSource.MANUAL,
                     effective_date=dish.on_menu_from))
    db.commit()

    return dish_out(db, new_dish)

@app.put("/dishes/{dish_id}", response_model=DishOut)
def update_dish(dish_id: int, changes: DishUpdate, db: Session = Depends(get_db)):
    dish = db.query(Dish).filter(Dish.id == dish_id).first()
    if not dish:
        raise HTTPException(status_code=404, detail="Dish not found")

    # A changed price is a new dated row, not an overwrite, so the days before
    # it are still analysed at the price that was actually charged.
    price_from = changes.price_from or date.today()
    if menu_price_on(db, dish_id, price_from) != changes.menu_price:
        db.add(MenuPrice(dish_id=dish_id, price=changes.menu_price, source=MenuPriceSource.MANUAL,
                         effective_date=price_from))

    dish.name = changes.name
    dish.category = changes.category
    dish.on_menu_from = changes.on_menu_from
    dish.on_menu_until = changes.on_menu_until
    db.commit()

    return dish_out(db, dish)

@app.delete("/dishes/{dish_id}/prices/{price_id}", status_code=204)
def delete_menu_price(dish_id: int, price_id: int, db: Session = Depends(get_db)):
    """Removes a price entered by mistake. A dish always keeps at least one price."""
    price = db.query(MenuPrice).filter(MenuPrice.id == price_id, MenuPrice.dish_id == dish_id).first()
    if not price:
        raise HTTPException(status_code=404, detail="Price not found")
    if db.query(MenuPrice).filter(MenuPrice.dish_id == dish_id).count() == 1:
        raise HTTPException(status_code=422, detail="A dish needs at least one price")

    db.delete(price)
    db.commit()

@app.delete("/dishes/{dish_id}", status_code=204)
def delete_dish(dish_id: int, db: Session = Depends(get_db)):
    dish = db.query(Dish).filter(Dish.id == dish_id).first()
    if not dish:
        raise HTTPException(status_code=404, detail="Dish not found")

    # No ORM cascades in this project, so remove the dish's rows explicitly.
    db.query(DishIngredient).filter(DishIngredient.dish_id == dish_id).delete()
    db.query(SalesRecord).filter(SalesRecord.dish_id == dish_id).delete()
    db.query(MenuPrice).filter(MenuPrice.dish_id == dish_id).delete()
    db.query(TillItemAlias).filter(TillItemAlias.dish_id == dish_id).delete()
    db.delete(dish)
    db.commit()

@app.get("/dishes/{dish_id}/detail", response_model=DishDetailOut)
def get_dish_detail(dish_id: int, start: date | None = Query(None, alias="from"), end: date | None = Query(None, alias="to"),
                    db: Session = Depends(get_db)):
    dish = db.query(Dish).filter(Dish.id == dish_id).first()
    if not dish:
        raise HTTPException(status_code=404, detail="Dish not found")

    lines = []
    for row in db.query(DishIngredient).filter(DishIngredient.dish_id == dish_id).all():
        ingredient = db.query(Ingredient).filter(Ingredient.id == row.ingredient_id).first()
        price = best_price(db, row.ingredient_id)
        lines.append(RecipeLineOut(
            ingredient_id=ingredient.id,
            name=ingredient.name,
            unit=ingredient.unit,
            quantity=row.quantity,
            price_per_unit=price.price_per_unit,
            price_source=price.source,
            line_cost=round(row.quantity * price.price_per_unit, 2),
        ))

    plate_cost, margin_pounds, margin_percent = cost_dish(db, dish_id)
    return DishDetailOut(
        id=dish.id,
        name=dish.name,
        menu_price=menu_price_on(db, dish_id),
        category=dish.category,
        on_menu_from=dish.on_menu_from,
        on_menu_until=dish.on_menu_until,
        skipped_ingredients=dish.skipped_ingredients,
        prices=list(reversed(menu_prices(db, dish_id))),
        lines=lines,
        cost=DishCostOut(plate_cost=plate_cost, margin_pounds=margin_pounds, margin_percent=margin_percent),
        units_sold=get_dish_units_sold(db, dish_id, *resolve_range(db, start, end)),
    )

@app.get("/dishes/{dish_id}/cost", response_model=DishCostOut)
def get_dish_cost(dish_id: int, db: Session = Depends(get_db)):
    plate_cost, margin_pounds, margin_percent = cost_dish(db, dish_id)
    return DishCostOut(
        plate_cost=plate_cost,
        margin_pounds=margin_pounds,
        margin_percent=margin_percent
    )

@app.post("/dishes/{dish_id}/estimate-recipe", response_model=list[MatchedIngredientDraft])
def estimate_recipe_route(dish_id: int, db: Session = Depends(get_db)):
    dish = db.query(Dish).filter(Dish.id == dish_id).first()
    if not dish:
        raise HTTPException(status_code=404, detail="Dish not found")

    try:
        recipe = estimate_recipe(db, dish.name, dish.category)
    except anthropic.APIConnectionError:
        # Never reached Anthropic: no internet, DNS failure, or timeout.
        raise HTTPException(status_code=503, detail="Couldn't reach the AI recipe service. Check your internet connection and try again.")
    except anthropic.APIStatusError as e:
        # Reached Anthropic, but it returned an error (bad API key, rate limit, overloaded).
        raise HTTPException(status_code=502, detail=f"The AI recipe service returned an error ({e.status_code}). Try again in a moment.")
    matched = match_recipe_ingredients(db, recipe)
    return matched

@app.post("/dishes/{dish_id}/recipe", response_model=RecipeSaveOut)
def save_recipe(dish_id: int, confirmed: schemas.RecipeConfirm, db: Session = Depends(get_db)):
    dish = db.query(Dish).filter(Dish.id == dish_id).first()
    if not dish:
        raise HTTPException(status_code=404, detail="Dish not found")

    # Check every line before touching the saved recipe.
    # (Quantities > 0 are already enforced by the ConfirmedIngredient schema.)
    ingredient_ids = [item.ingredient_id for item in confirmed.ingredients]
    if len(ingredient_ids) != len(set(ingredient_ids)):
        raise HTTPException(status_code=422, detail="The same ingredient appears twice. Combine it into one line.")
    for ingredient_id in ingredient_ids:
        if db.query(Ingredient).filter(Ingredient.id == ingredient_id).first() is None:
            raise HTTPException(status_code=422, detail=f"Ingredient {ingredient_id} doesn't exist")
        if best_price(db, ingredient_id) is None:
            raise HTTPException(status_code=422, detail=f"Ingredient {ingredient_id} has no price yet")

    recipe = []

    dish.skipped_ingredients = confirmed.skipped_ingredients

    db.query(models.DishIngredient).filter(models.DishIngredient.dish_id == dish_id).delete()

    for item in confirmed.ingredients:
        confirmed_ingredient = DishIngredient(dish_id=dish_id, ingredient_id=item.ingredient_id, quantity=item.quantity)
        recipe.append(confirmed_ingredient)
        db.add(confirmed_ingredient)
    db.commit()

    plate_cost, margin_pounds, margin_percent = cost_dish(db, dish_id)
    cost_out = DishCostOut(
            plate_cost=plate_cost,
            margin_pounds=margin_pounds,
            margin_percent=margin_percent
        )
    return RecipeSaveOut(
        ingredients = recipe,
        cost = cost_out
    )

@app.post("/dishes/{dish_id}/sales", response_model=SalesRecordOut)
def save_sales_record(sales: SalesRecordCreate, dish_id: int, db: Session = Depends(get_db)):
    dish = db.query(Dish).filter(Dish.id == dish_id).first()
    if not dish:
        raise HTTPException(status_code=404, detail="Dish not found")
    if sales.period_start > sales.period_end:
        raise HTTPException(status_code=422, detail="The start date is after the end date")
    if overlapping_records(db, dish_id, sales.period_start, sales.period_end):
        raise HTTPException(status_code=422, detail=f"{dish.name} already has sales recorded that overlap this period. Adding more would count them twice.")

    new_sales_record = SalesRecord(
        dish_id = dish_id,
        units_sold = sales.units_sold,
        period_start= sales.period_start,
        period_end = sales.period_end
    )
    db.add(new_sales_record)
    db.commit()
    db.refresh(new_sales_record)

    return new_sales_record

@app.get("/dishes/{dish_id}/sales", response_model=list[SalesRecordOut])
def get_sales_record(dish_id: int, db: Session = Depends(get_db)):
    dish = db.query(Dish).filter(Dish.id == dish_id).first()
    if not dish:
        raise HTTPException(status_code=404, detail="Dish not found")

    sales_record = db.query(SalesRecord).filter(SalesRecord.dish_id == dish_id).all()
    return sales_record

# Every analysis route takes ?from=YYYY-MM-DD&to=YYYY-MM-DD. Without them it
# uses the latest month with sales (periods.default_range).

@app.get("/dishes/classifications", response_model=list[DishClassificationOut])
def get_dish_classifications(start: date | None = Query(None, alias="from"), end: date | None = Query(None, alias="to"),
                             db: Session = Depends(get_db)):
    return classify_all_dishes(db, *resolve_range(db, start, end))

@app.get("/dishes/action-list", response_model=list[ActionItemOut])
def get_action_list(start: date | None = Query(None, alias="from"), end: date | None = Query(None, alias="to"),
                    db: Session = Depends(get_db)):
    return build_action_list(db, *resolve_range(db, start, end))

@app.get("/dishes/incomplete", response_model=list[IncompleteDishOut])
def get_incomplete_dishes(start: date | None = Query(None, alias="from"), end: date | None = Query(None, alias="to"),
                          db: Session = Depends(get_db)):
    return list_incomplete_dishes(db, *resolve_range(db, start, end))


# --- Sales for a period ------------------------------------------------------------

def overlapping_records(db, dish_id, start, end, except_exact=False):
    """A dish's sales records that overlap start..end (optionally ignoring one covering exactly that period)."""
    records = db.query(SalesRecord).filter(
        SalesRecord.dish_id == dish_id,
        SalesRecord.period_start <= end,
        SalesRecord.period_end >= start,
    ).all()
    if except_exact:
        records = [r for r in records if not (r.period_start == start and r.period_end == end)]
    return records

@app.get("/sales/coverage", response_model=SalesCoverageOut)
def get_sales_coverage(start: date | None = Query(None, alias="from"), end: date | None = Query(None, alias="to"),
                       db: Session = Depends(get_db)):
    start, end = resolve_range(db, start, end)
    first_date = db.query(func.min(SalesRecord.period_start)).scalar()
    last_date = db.query(func.max(SalesRecord.period_end)).scalar()

    overlapping = db.query(SalesRecord).filter(SalesRecord.period_start <= end, SalesRecord.period_end >= start).all()
    inside = [r for r in overlapping if r.period_start >= start and r.period_end <= end]

    days = set()
    for r in inside:
        day = r.period_start
        while day <= r.period_end:
            days.add(day)
            day += timedelta(days=1)

    return SalesCoverageOut(first_date=first_date, last_date=last_date, start=start, end=end,
                            days_with_sales=sorted(days), partial_records=len(overlapping) - len(inside))

@app.get("/sales/entries", response_model=list[SalesEntryOut])
def get_sales_entries(start: date = Query(alias="from"), end: date = Query(alias="to"), db: Session = Depends(get_db)):
    """Every dish on the menu during the period, with any total entered for exactly that period."""
    start, end = resolve_range(db, start, end)
    entries = []
    for dish in db.query(Dish).order_by(Dish.name).all():
        if not on_menu_during(dish, start, end):
            continue
        records = overlapping_records(db, dish.id, start, end)
        exact = [r for r in records if r.period_start == start and r.period_end == end]
        entries.append(SalesEntryOut(
            dish_id=dish.id, dish_name=dish.name, category=dish.category,
            units_sold=exact[0].units_sold if exact else None,
            other_records=len(records) - len(exact),
        ))
    return entries

@app.put("/sales/entries", response_model=list[SalesEntryOut])
def save_sales_entries(entries: list[SalesEntryIn], start: date = Query(alias="from"), end: date = Query(alias="to"),
                       db: Session = Depends(get_db)):
    """
    Save a total per dish for exactly this period, replacing any total already
    entered for it. units_sold None removes that dish's total.
    Every line is checked before anything is saved.
    """
    start, end = resolve_range(db, start, end)
    dish_ids = [e.dish_id for e in entries]
    if len(dish_ids) != len(set(dish_ids)):
        raise HTTPException(status_code=422, detail="The same dish appears twice")
    for e in entries:
        dish = db.query(Dish).filter(Dish.id == e.dish_id).first()
        if dish is None:
            raise HTTPException(status_code=422, detail=f"Dish {e.dish_id} doesn't exist")
        if e.units_sold is not None and overlapping_records(db, e.dish_id, start, end, except_exact=True):
            raise HTTPException(status_code=422, detail=(
                f"{dish.name} already has sales recorded inside this period (e.g. daily till data). "
                "Entering a total as well would count them twice."))

    for e in entries:
        db.query(SalesRecord).filter(SalesRecord.dish_id == e.dish_id, SalesRecord.period_start == start,
                                     SalesRecord.period_end == end).delete()
        if e.units_sold is not None:
            db.add(SalesRecord(dish_id=e.dish_id, units_sold=e.units_sold, period_start=start, period_end=end))
    db.commit()

    return get_sales_entries(start, end, db)

# --- Setup --------------------------------------------------------------------------

@app.get("/setup/status", response_model=SetupStatusOut)
def get_setup_status(db: Session = Depends(get_db)):
    return setup_status(db)

@app.post("/setup/reset")
def reset(request: ResetIn):
    """
    Wipes the database and rebuilds it: "fresh" = benchmark ingredients only,
    "demo" = the demo pizzeria. The current database is backed up first.
    """
    if request.confirm != "reset":
        raise HTTPException(status_code=422, detail='Send confirm: "reset" to wipe the database')

    backup = backup_database()
    result = reset_database(engine, with_demo=request.mode == "demo")
    return {"mode": request.mode, "backup": backup, **result}

@app.post("/setup/benchmarks", response_model=BenchmarkSyncOut)
def update_benchmarks(db: Session = Depends(get_db)):
    """
    Adds new ingredients from the benchmark list and records changed benchmark
    prices. Never removes anything or touches the restaurant's own prices.
    """
    return sync_benchmarks(db)

# --- Imports ------------------------------------------------------------------------

@app.get("/imports", response_model=list[ImportOut])
def list_imports(db: Session = Depends(get_db)):
    return db.query(Import).order_by(Import.created_at.desc(), Import.id.desc()).all()

# Uploaded files are kept here (git-ignored), named by their SHA-256 hash, so
# the same file uploaded twice is stored once and can be recognised.
UPLOAD_DIR = Path(__file__).parent / "uploads"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
# Extension -> (media type, how the file's first bytes must start)
UPLOAD_TYPES = {
    ".pdf": ("application/pdf", [b"%PDF"]),
    ".jpg": ("image/jpeg", [b"\xff\xd8"]),
    ".jpeg": ("image/jpeg", [b"\xff\xd8"]),
    ".png": ("image/png", [b"\x89PNG"]),
    ".webp": ("image/webp", [b"RIFF"]),
}

def read_upload(file):
    """Checks an uploaded document and keeps a copy. Returns (content, media type, hash)."""
    extension = Path(file.filename or "").suffix.lower()
    if extension not in UPLOAD_TYPES:
        raise HTTPException(status_code=422, detail="Upload a PDF or a photo (JPG, PNG or WebP)")
    content = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=422, detail="That file is over 10 MB")
    media_type, signatures = UPLOAD_TYPES[extension]
    if not any(content.startswith(s) for s in signatures):
        raise HTTPException(status_code=422, detail=f"That file isn't a readable {extension[1:].upper()}")

    file_hash = hashlib.sha256(content).hexdigest()
    UPLOAD_DIR.mkdir(exist_ok=True)
    saved = UPLOAD_DIR / f"{file_hash}{extension}"
    if not saved.exists():
        saved.write_bytes(content)
    return content, media_type, file_hash

@app.post("/imports/invoice/read", response_model=InvoiceReviewOut)
def read_invoice_route(file: UploadFile, db: Session = Depends(get_db)):
    """Claude reads an uploaded invoice; code then matches and checks it. Saves nothing but the file."""
    content, media_type, file_hash = read_upload(file)
    try:
        draft = read_invoice(db, content, media_type)
    except anthropic.APIConnectionError:
        raise HTTPException(status_code=503, detail="Couldn't reach the AI service to read the invoice. Check your internet connection and try again.")
    except anthropic.APIStatusError as e:
        raise HTTPException(status_code=502, detail=f"The AI service returned an error ({e.status_code}) reading the invoice. Try again in a moment.")
    return review_invoice(db, draft, filename=file.filename, file_hash=file_hash)

@app.post("/imports/invoice/review", response_model=InvoiceReviewOut)
def review_invoice_draft(draft: InvoiceDraft, db: Session = Depends(get_db)):
    """Matches and checks an invoice already read into lines. Saves nothing."""
    return review_invoice(db, draft)

@app.post("/imports/invoice/apply", response_model=ImportOut)
def apply_invoice_route(data: InvoiceApplyIn, db: Session = Depends(get_db)):
    try:
        return apply_invoice(db, data)
    except ImportProblem as e:
        raise HTTPException(status_code=422, detail=str(e))

def load_upload(file_hash, extension):
    """The text of a file uploaded earlier, found by its hash."""
    # The hash comes from the browser and becomes part of a file path, so it
    # must be exactly a SHA-256 hex string (no "../" tricks).
    if not re.fullmatch(r"[0-9a-f]{64}", file_hash or ""):
        raise HTTPException(status_code=422, detail="Unknown file")
    path = UPLOAD_DIR / f"{file_hash}{extension}"
    if not path.exists():
        raise HTTPException(status_code=422, detail="That upload has gone. Upload the file again.")
    return decode(path.read_bytes())

@app.post("/imports/sales/review", response_model=SalesReviewOut)
def review_sales_route(data: SalesReviewIn, db: Session = Depends(get_db)):
    """Reads an uploaded till export with the chosen columns and matches it. Saves nothing."""
    text = load_upload(data.file_hash, ".csv")
    try:
        return review_sales(db, text, data.file_hash, data.filename, data.mapping, data.choices)
    except ImportProblem as e:
        raise HTTPException(status_code=422, detail=str(e))

@app.post("/imports/sales/apply", response_model=ImportOut)
def apply_sales_route(data: SalesApplyIn, db: Session = Depends(get_db)):
    text = load_upload(data.file_hash, ".csv")
    try:
        return apply_sales(db, text, data)
    except ImportProblem as e:
        raise HTTPException(status_code=422, detail=str(e))

@app.post("/imports/{import_id}/undo", response_model=ImportOut)
def undo_import_route(import_id: int, db: Session = Depends(get_db)):
    record = db.get(Import, import_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Import not found")
    try:
        if record.kind == ImportKind.SALES:
            return undo_sales_import(db, record)
        return undo_import(db, import_id)
    except ImportProblem as e:
        raise HTTPException(status_code=422, detail=str(e))
