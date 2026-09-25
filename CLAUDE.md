# CLAUDE.md — Docket (Menu & Margin Engine)

This file gives Claude Code the context it needs to work on this project. Read it fully at the start of every session.

## What this project is

**Docket** (the UK kitchen word for an order ticket) is a web app for small independent UK restaurants. It was briefly called Mise; that name was dropped because mise.cooking already exists. A restaurant brings its data in whatever form it has: a menu PDF or photo, supplier invoices, till exports. The app keeps a **live model of the menu**: it estimates each dish's cost and margin, and keeps them up to date as prices and sales change. It then suggests changes, both to the menu and to the business as a whole.

### The target journey (what we're building towards)

1. **Setup:** the user describes the business (type of restaurant, location, rough covers per day) and uploads a menu (PDF, photo or website link). Claude extracts dishes (name, price, category, description), and the user checks the list before it's saved.
2. **Recipes:** Claude estimates each dish's recipe from its name and description, grounded in the ingredient list. The user checks each one in the recipe editor on the dish page ("AI proposes, human verifies").
3. **Costs:** ingredients start on benchmark prices. The user uploads supplier invoices, Claude extracts the lines, and they're matched to ingredients and normalised to base units. **Every price records its source and date**, and costing uses the best available. Each dish shows how much of its cost comes from the restaurant's own data. Price changes raise alerts.
4. **Sales:** the user uploads a till export (CSV/Excel). Claude identifies which column is which, then code reads the numbers and matches items to dishes. A direct connection to Square's test environment is a stretch goal.
5. **Results:** Kasavana-Smith menu engineering (Star / Plowhorse / Puzzle / Dog), a ranked action list with £ impact, a menu summary, and rule-based business-wide suggestions.

### Where it is now

Step 2 works (dish page with recipe editor and AI draft), and step 5 works at menu level. Dishes are added one at a time on the Menu page, or from an uploaded menu (PDF or photo) on the Imports page: Claude reads it, the differences from the stored dishes are shown for the owner to confirm, and applying dates every change from the menu's start date. Menu prices have dated history (edit a dish's price and pick when it starts; the dish page lists the history). Ingredient prices have history and sources. Owners enter them by hand on the Ingredients page, or upload a supplier invoice on the Imports page: Claude reads it, the owner checks the lines, and applying saves dated invoice prices (undoable). Sales are stored per dish per day (or as a total for a period), and every analysis runs over a chosen date range; the Sales page shows which days have data and takes manual totals, and a till export (CSV) can be uploaded on the Imports page: Claude proposes the columns and item matches, the owner checks them, and applying saves daily totals per dish (undoable). The demo database comes from `seed_demo.py`.

**Purpose:** a portfolio piece for Forward Deployed Engineer / Solutions Engineer interviews. It is NOT being built as a commercial product. Clarity, correctness and explainability matter more than features. The aim is **one complete journey that works end to end and can be demoed in five minutes**, not every possible integration.

## About the developer (George)

- He is not an experienced software engineer. **Explain what you're doing and why in plain English, and define technical terms the first time you use them.**
- He wrote the core logic himself and must be able to defend it in interviews. He is from a kitchen background and uses that knowledge to sanity-check outputs.
- He works on **Windows in VS Code**.
- He prefers short, direct explanations, concrete rules, and step-by-step reasoning. No padding, no buzzwords.

## Stack

- **Backend:** Python, FastAPI, SQLAlchemy (manual-query style, no ORM relationships), Pydantic v2, SQLite
- **Frontend:** React + Vite, Recharts, Tailwind CSS v4 via `@tailwindcss/vite`
- **AI:** Anthropic Python SDK, Claude Haiku for recipe estimation
- **Ports:** backend on 8000, frontend on 5173

## Project layout

- `backend/` holds the FastAPI app. The files are flat, with no sub-packages.
  - `main.py`: every API route.
  - `models.py`: SQLAlchemy tables. `schemas.py`: Pydantic request/response models.
  - `database.py`: the engine, `get_db`, and a stub `get_current_user` (placeholder for auth).
  - `costing.py`: costing engine (`cost_dish`), and `best_price`, which chooses which dated ingredient price to use. Menu prices are dated too (`MenuPrice`; `Dish` has no price column): `menu_price_on` gives the price on a day, and `average_menu_price` gives the price analysis uses for a range, the price charged each day weighted by that day's units (a multi-day total spanning a change is split evenly over its days; no sales → the price on the range's last day). `cost_dish(db, id, menu_price=None)` defaults to today's price; `get_category_stats` passes the range's average.
  - Changing `models.py` needs the database rebuilt (`seed_demo.py`), because there's no migration tool yet (Alembic is needed before deployment). Restart the backend afterwards, because `--reload` can leave it running a half-updated copy.
  - `menu_engineering.py`: classification, action list, incomplete-dish detection, all for a date range (`start`, `end`). The rules for which sales and dishes count are in the comment at the top of the file. `get_category_stats` costs each dish and counts its units **once per category**; the helpers and `classify_dish` read from it. Don't reintroduce per-dish recalculation of category totals, which made the dashboard about 6× slower.
  - `recipe_ai.py`: recipe-estimation prompt and the Anthropic call.
  - `matching.py`: exact match first, then `difflib` fuzzy suggestions.
  - `periods.py`: month maths and the default range (the month containing the latest sale). Analysis routes take `?from=YYYY-MM-DD&to=YYYY-MM-DD`; without them they use that default.
  - `units.py`: converts a pack price ("£93.60 for 12 kg") into a price per base unit. **Every price input path goes through it** (the price routes do via `base_unit_price` in `main.py`; invoice import via `invoices.line_price`).
  - `invoices.py`: invoice import after Claude has read the invoice, all plain Python: `review_invoice` (price per base unit from pack count × size, totals check, matching, flags; saves nothing), `apply_invoice` (checks everything, then saves `invoice` prices dated on the invoice date, each carrying `import_id`, and remembers matches in `SupplierAlias`), `undo_import` (all or nothing; refused if an ingredient the invoice created is now in a recipe). Matching order: remembered match for this supplier and description → exact match on Claude's `likely_ingredient` → fuzzy suggestions from `matching.py` (never auto-chosen).
  - `invoice_ai.py`: the invoice-reading prompt and the Claude call (Sonnet 5; PDFs sent as documents, photos as images). Claude only reads: numbers as printed, pack as count/size/unit, line kind, likely ingredient from the live list. Routes: `POST /imports/invoice/read` (upload; checks type, size and file signature, keeps the file in git-ignored `backend/uploads/<sha256>.<ext>`), `/imports/invoice/review`, `/imports/invoice/apply`, `GET /imports`, `POST /imports/{id}/undo`.
  - `tills.py`: till (sales) import, all plain Python: `read_csv` (comma/semicolon/tab), `parse_sales` (dates in one of six formats, time ignored; refunds netted as negative quantities or via a refund column; only the item column is read, so modifiers are ignored; bad rows counted by reason), `plan_sales` (item → dish choices, daily totals per dish, overlap status), `review_sales`, `apply_sales`, `undo_sales_import`. Overlap rules (agreed with George): a dish-day from an earlier till import is **replaced**; a dish-day covered by sales entered another way (typed totals, seeded demo data) is **skipped and listed**, never deleted or doubled; sales outside a dish's menu dates are saved with an "off the menu" flag; a sale's date is the calendar date on the till. Undo removes the import's rows (days it replaced don't come back). Remembered: `TillMapping` (columns, keyed by the header row) and `TillItemAlias` (item → dish or ignore).
  - `till_ai.py`: two small Haiku calls, each skipped when not needed: `propose_columns` (header + 5 sample rows, customer-looking columns blanked by `redact`; skipped for a remembered layout; checked by `check_columns`, which rejects missing columns and fixes a date format that can't read the samples) and `suggest_items` (only item names not remembered or exactly a dish name). If Claude is unreachable, the review still opens and the owner picks the columns. Routes: `POST /imports/sales/read` (CSV upload), `/imports/sales/review` (re-reads the stored file by hash with the owner's columns and choices), `/imports/sales/apply`. `main.load_upload` only accepts a 64-hex-character hash (the hash becomes a file path).
  - `menus.py`: menu import, all plain Python. `review_menu` sorts each item into new / same / price / renamed? / returning / not a dish and lists the dishes on the menu now that the new menu lacks; `apply_menu` checks everything, then saves. Rules (agreed with George): new dishes and new prices are dated from the start date; a dish missing from the new menu comes off the day before (never deleted) unless the owner keeps it; a close name (difflib ≥ 0.6, or Claude's `likely_existing`) is always a question, never merged, and "same dish, renamed" keeps the dish's recipe, sales and prices; a changed description sets `Dish.recipe_check` (a reminder only, cleared when the recipe is saved); existing dishes keep their category; a returning dish becomes a new record with the old recipe copied (and till matches moved), so the old record's months off stay correct; ignored items are remembered (`MenuIgnoredItem`); menu imports can't be undone.
  - `menu_ai.py`: the menu-reading prompt (Sonnet 5, like invoices). Claude reads names, prices, descriptions, sections (mapped to Starter/Main/Side/Dessert), sizes as separate items, whether each is a dish, and which stored dish a renamed item probably is. Routes: `POST /imports/menu/read` (upload + `start_date`), `/imports/menu/review` (compare again, e.g. for a new start date; no AI call), `/imports/menu/apply`. Dishes store their menu `description`, which Estimate with AI adds to the recipe prompt (approved by George).
  - `samples/make_sample_menu.py` writes `samples/sample-menu.pdf`, a made-up "Autumn menu" for the demo (start it on 1 Oct 2026): a price rise (Diavola), a new dish (Carbonara Pizza, uses guanciale), a rename (Nduja), a returning dish (Marinara), one dropped (Cannoli), and drinks/add-ons/a lunch deal. It uses the PDF writer in `make_sample_invoice.py`.
  - `samples/make_sample_sales.py` writes `samples/sample-sales.csv`, a made-up Square-style export for 1-21 Sep 2026 (the demo data ends 31 Aug): renamed dishes, drinks, add-ons, a service charge, a refund marked in "Event Type" (not in the first 5 rows, so the owner sets the refund column by hand), and two Marinara sales after it came off the menu.
  - `samples/make_sample_invoice.py` writes `samples/sample-invoice.pdf`, a made-up invoice (fictional supplier) for trying the import by hand against the demo data: it includes a new ingredient (guanciale), a line whose total doesn't add up (ricotta) and two lines to ignore.
  - `benchmarks.py` + `data/benchmark_prices.csv`: the benchmark ingredient list (~250 items: Italian, British pub, Indian and general staples; 2026 UK wholesale estimates, not supplier quotes). The CSV is written as a kitchen reads prices (`beef mince,gram,8.50,kg`) and converted through `units.py` on load. `sync_benchmarks` adds missing ingredients and records changed benchmark prices as new dated rows; it never deletes, never touches own prices, and skips (reports) unit conflicts. Settings → Benchmark prices → Update runs it (`POST /setup/benchmarks`). Edit the CSV to change or add benchmarks.
  - `sales_report.py`: `sales_summary` for the Sales page (`GET /sales/summary?from&to`): sales £ by day (every day in the period), by category and by dish, each day priced at the menu price charged that day (`price_on`). Same rules as the analysis: only records wholly inside the period; a multi-day total is spread evenly over its days. For a period where every dish is analysed, its total equals the Overview's Sales figure (checked on August's demo data: £42,107.50 both ways).
  - `onboarding.py`: `setup_status` (counts for the setup checklist, plus `needs_recipe`: dishes on the menu without a recipe, in menu order Starter → Main → Side → Dessert, which the Setup page's Recipes step works through). Routes: `GET /setup/status`, and `POST /setup/reset` with `{"mode": "fresh" | "demo", "confirm": "reset"}`, which backs up `menu.db` and then rebuilds it (the Settings page calls it).
  - `seed_demo.py`: wipes and rebuilds `menu.db` with realistic demo data (June–August 2026 of daily sales at a small UK pizzeria, hand-written recipes; June's days add up to the original June totals). It backs up the old database to `menu.backup-<timestamp>.db` first. `reset_database(engine, with_demo)` is the shared function: `with_demo=False` is "start fresh" (benchmark ingredients only). It takes the engine as a parameter so tests run it on the in-memory database. Run as a script, or use Settings in the app.
  - `seed_recipes.py`: re-estimates every dish's recipe with the real API and auto-accepts matches. It overwrites the hand-written demo recipes, so it's for AI testing only.
  - `ai_test_v1.py`, `ai_test_v2.py`, `dish_check.py`, `match_check.py`, `costing_check.py`, `ingredient_list.py`: one-off scripts written during development. They are **not** pytest tests. Don't name scripts `test_*.py`, or pytest will run them.
  - `tests/`: pytest tests. `conftest.py` gives every test a fresh in-memory database. Tests never read or write `menu.db` data (importing `main` runs `create_all`, which only creates missing tables). `pytest.ini` sets the test path.
  - The SQLite database is `backend/menu.db` (git-ignored). The API key lives in `backend/.env` (git-ignored).
  - The Python virtual environment is at `backend/venv/`.
  - Use `backend/venv/Scripts/python.exe`, not the system Python.
- `frontend/` holds the React app.
  - `src/App.jsx` loads the shared data once and picks the page. Pages are switched by the URL hash via `src/useHashRoute.js`, with no router library: Overview (`#/overview`), Actions (`#/actions`), Menu (`#/menu`), a dish page (`#/menu/12`), Ingredients (`#/ingredients`), Sales (`#/sales`), Imports (`#/imports`) and Insights (`#/analysis`).
  - `ImportsPage.jsx`: Upload menu, Upload invoice, Upload sales, and the import history (with Undo for invoices and sales). After a menu upload it shows `MenuReview.jsx` (start date, then groups: Renamed? / New / Back on the menu / Price changes / Not dishes / Unchanged, and Coming off the menu with a Take off tick per dish). After a sales upload it shows `SalesReview.jsx` (columns with sample rows, then items with a dish or Ignore each; every change re-reads the file on the server). After an invoice upload it shows `InvoiceReview.jsx`, where every line can be edited before Apply; the prices and warning chips there are a live preview (`src/invoices.js`), and the backend works them out again on Apply.
  - Overview (`OverviewPage.jsx`) is deliberately light: a big tomato tile for contribution (shortened to "£36k", full figure underneath) and tiles for sales, dishes sold and gross margin, each with its change since the previous period; **recommended changes** (the top three actions on the ticket rail); and **quadrants** (four tinted tiles laid out like the chart, dishes as pills, moves since the previous period marked ↑ / ↓ / → / new). The full ranked list lives on the Actions page (`ActionList.jsx`: the top five on the rail, the rest in a "more changes" table). Action wording shared by both is in `src/actionText.js`. `components/Layout.jsx` is the header row: the `docket.` wordmark, nav pills (lowercase; below 1280px they drop to their own row and scroll sideways), the period picker and a Settings gear.
  - The dish page (`DishPage.jsx`) loads its own detail (`GET /dishes/{id}/detail` plus `/ingredients`): the name with its quadrant `Stamp`, tiles for menu price, plate cost, margin and units sold, the recipe editor, and beside it the dish's own recommended-change ticket (from the action list App already has) and its price history. `RecipeEditor.jsx` edits the recipe there. "Estimate with AI" fills the editor as a draft, and nothing is saved until Save. The editor's plate cost is a live preview; the saved figures always come from the backend costing engine.
  - `SalesPage.jsx` starts with `SalesMoney.jsx` (its own call to `/sales/summary`): dish sales, dishes sold, busiest and average day, a daily bar chart with a 7-day average line, sales by category, and best/lowest sellers; then the coverage strip and manual totals.
  - `IngredientsPage.jsx` loads `/ingredients` itself (current price, source, date and `used_in` count). Prices are entered as a pack price (`PriceFields.jsx`, helpers in `src/prices.js`). The £/kg shown while typing is only a preview; the backend does the real conversion.
  - The chosen period lives in `App.jsx` (kept in session storage) and is picked with `RangePicker.jsx`. Presets are relative to the latest sale, not today (`src/dateRange.js`), so an old dataset still opens on data. A chosen preset follows the data: when new sales arrive, "Latest month" moves on to the new month (a custom range stays as chosen).
  - **Design system (Docket): `src/index.css`.** Every colour (tokens on `:root`), the fonts (Bricolage Grotesque for headings, figures and text; DM Mono for labels, buttons and table numbers) and the shared component classes live there: `btn btn-primary|secondary|danger|sm` (pills with an ink outline; primary is mustard), `input` (+ `input-pill` for a select drawn as a pill), `field` + `label`, `card` / `card-header` / `card-body` (paper, 2px ink outline), `table` (+ `row-link`; mono headers, dashed rows), `chip chip-warn|muted|accent`, `count`, `tabs` / `tab` and `segmented` (pills), `tile tile-tomato|mustard|basil|outline` + `tile-label` + `figure` (flat colour tiles with big narrow figures; `corner-tl|tr|bl|br` gives a tile or card its one odd corner; **not** `block`, which is a Tailwind utility), `rail` / `ticket` (the ticket rail, `TicketRail.jsx`), `stamp` (`Stamp.jsx`), `alert-error`, `alert-info`, `empty`, `progress` + `progress-bar`, `chart-tip` (dark ink tooltips: `--tip-edge` sets the coloured top strip; shown without the Recharts glide, `isAnimationActive={false}`), `page-title`, `section-title`, `stat-value`, `num`, `link`. Lowercase: nav, page titles, section titles, tabs, segmented buttons and tile labels are lowercase (CSS does it for section titles, tabs and tile labels); dish names keep their capitals, and a section title holding a name opts out with `normal-case` (as `ConfirmDialog` does). No glyphs on buttons (no ✦ sparkles or ✎ pencils): buttons say what they do in words. **Use these; don't write one-off button, input, table or card styles in a component.** Change a look in `index.css`, once.
  - Light theme only: cream page, paper cards, ink, with tomato, mustard and basil (plus light `*-soft` versions). Quadrant colours are in `src/quadrants.js`: `color` for dots, a `text` shade for small text, and a light `tint` for zones, tiles and badges.
  - **No explanatory sentences on screen.** Screens show labels, figures and short chips ("Puzzle → Star", "▲70%", "Check unit"), never chatty lines like "worth £X together", "Promote it" or "Was a Dog". **This includes AI-sounding asides and reassurances** such as "usually about 25 s", "this may take a moment", "don't worry…", "tip:", "great, …" or estimates tacked onto labels. A figure on its own ("6 s") is fine. George has asked for this repeatedly: check every new piece of on-screen text against it before finishing. Explanations are available on demand through `components/Hint.jsx` (hover, keyboard focus, or click to pin), either wrapping an element (e.g. a quadrant badge) or as an ⓘ icon. Explanation text for actions lives in `src/actionText.js`.
  - **Insights** (`InsightsPage.jsx`): one menu-engineering chart (`QuadrantChart.jsx`) with a dropdown filter that starts on **All categories**; the highlights and figures follow the filter. Because each category is judged against its own lines, the All view plots every dish **relative to its own category's lines** (across: its share as a % of the popularity line, 100% = on the line; up: margin above or below its category's average, £0 = on the line), so one pair of lines is right for every dish and each colour matches its zone. A single category shows real shares and £ margins. The chart is re-keyed per filter (Recharts otherwise asks for labels of dots that have gone). Only the highlighted dishes are named on the chart, in dark pills (every dish shows on hover; a click opens it), placed by `src/labelPlacement.js`; the zones are filled with each quadrant's tint. Beside it: Top earner (a basil tile; margin × units), Biggest opportunity (a tomato tile; top £ action), and quadrant moves since the previous period; underneath, the category's contribution, sales, margin per dish sold and units against the previous period. The totals come from `src/figures.js` (`summarise`, shared with the Overview); the ▲/▼ marker is `components/Delta.jsx`.
  - **Never use `window.confirm` / `alert` / `prompt`.** The app's embedded browser pane blocks them (confirm silently returns false). Destructive actions use `components/ConfirmDialog.jsx` (an in-page `<dialog>`).
  - **Recipes table** (`RecipesTable.jsx`, one call: `GET /recipes`): every dish on the menu with price, plate cost, food cost %, status (No recipe / AI · unchecked / Checked) and checks. Per row, small text buttons: estimate (with AI), edit (inline `RecipeEditor`), looks right (unchecked only). **Estimate all** (after a confirm box, as for every AI estimate here) calls `POST /dishes/{id}/estimate-and-save` three at a time with a real progress bar and Stop. Used on the Setup page's Recipes step and the Menu page's **Recipes** tab; the Overview shows an "N unchecked AI recipes" chip linking to it.
  - `recipe_checks.py`: the checks, plain rules with George's thresholds (food cost under 8% or over 40% of the menu price; a line over 500 g / 500 ml / 12 each; fewer than 2 ingredients; an ingredient left out of the cost; a unit clash). Shown only on unchecked AI recipes. `Dish.recipe_status` is CHECKED (saved in the editor, or Looks right) or AI_UNCHECKED (bulk estimate); `DishIngredient.unit_check` marks an AI line given in a different unit (kept as given, flagged).
  - **Guided setup** (`#/setup`, `SetupPage.jsx`): a row of numbered step tiles, menu → your prices (optional) → recipes → sales → results (prices first, so invoice ingredients are there for recipes); the open step is ink, done steps basil, the rest outlined. An upload step is one big colour tile (its figure, its upload button, the by-hand route as a small link), with Next (or Skip, for prices) underneath. Each step reuses an existing screen: the menu/invoice/sales review via `ImportReview.jsx`, and the Recipes table. Progress comes from the data (setup status), never a stored wizard position, so leaving and returning just works. Start fresh opens it; until the required steps are done the Overview shows `SetupChecklist.jsx` with Continue setup (step logic and `firstUnfinished` in `src/setup.js`). Settings (`SettingsPage.jsx`, the gear at the end of the header) has Start fresh and Load demo data.
  - Uploads share `src/imports.js` (`UPLOADS`, `readUpload`), `components/UploadButton.jsx` and `components/ImportReview.jsx` between the Imports and Setup pages. Invoices can be picked several at once: `src/useUploadQueue.js` reviews them one after another (the next file is read while the current one is checked; Cancel skips one; an unreadable file shows its error with Skip), shown by `components/QueueReview.jsx`. Menus and till exports stay one file at a time.
  - Components live in `src/components/`. Quadrant colours live in `src/quadrants.js`, menu categories in `src/categories.js`, and number and unit formatting in `src/format.js` (prices are shown as £/kg, £/l or each).
  - All API calls go through `src/api.js`, using the `getJson` / `postJson` / `putJson` / `deleteJson` helpers (and `postFile` for uploads). Don't call `fetch` directly from components.
  - The backend URL comes from `VITE_API_URL`, defaulting to `http://localhost:8000`.

### Starting the app

Run each server in its own terminal (PowerShell), starting from the project root.

Backend (http://localhost:8000, API docs at http://localhost:8000/docs):

```powershell
cd backend
.\venv\Scripts\python.exe -m uvicorn main:app --reload
```

Always start the backend from inside `backend/`. The database path is relative (`sqlite:///./menu.db`), so starting it from anywhere else silently creates a new, empty database.

Frontend (http://localhost:5173):

```powershell
cd frontend
npm run dev
```

If Tailwind classes used in a newly created component don't take effect (the element keeps the shared class's width, for example), restart the frontend dev server: it can keep serving a stylesheet built before the file existed.

Tests (from inside `backend/`):

```powershell
cd backend
.\venv\Scripts\python.exe -m pytest
```

## Core logic — do not change without asking first

George wrote these parts and must be able to explain them. **Propose changes and explain them; don't just make them.**

- **Costing engine:** plate cost and margin calculation.
- **Menu-engineering classification:** the quadrant thresholds, and the Dog/Plowhorse impact formulas.
- **Recipe-estimation prompt:** the prompt sent to Claude.
- **Fuzzy-matching pipeline:** the two-tier matching of AI ingredient names to the ingredient table.
- **Recipe save route:** the validation logic.

## Design decisions to preserve

These were hard-won. Don't undo them.

- **Units are normalised at data-entry time.** Everything is stored in base units, so the costing function has no conversion logic. Keep it that way. Any new input path must normalise units before saving, using `units.py`.
- **Excluded dishes come out of the denominator too.** When a dish is excluded from analysis (e.g. its recipe is incomplete), it must also be removed from the totals used for thresholds. Otherwise every other dish's popularity threshold silently shifts.
- **Every number in the action list is the same kind of number.** Every £ impact is a *change* (delta) in contribution, not a current level. For example, Dog impact = (category weighted-average margin − dish margin) × units. "Weighted" means each dish's margin counts in proportion to its units sold (the Kasavana-Smith method). Plowhorse impact deliberately uses the same formula.
- **The recipe prompt is grounded in the live ingredient list.** That list is fetched from the database on every call, so AI output uses the same ingredient names as the table.
- **The API serves the dashboard efficiently.** The app loads its shared data in a fixed number of calls, never one per dish: `/dishes/classifications`, `/dishes/action-list`, `/dishes/incomplete` and `/sales/coverage` (all for the chosen range), `/dishes`, and `/dishes/classifications` for the previous period (for the Overview's comparisons; `previousRange` in `src/dateRange.js`). The dish page makes its own call for the one dish it shows. Don't reintroduce per-dish calls on list pages.
- **Validation happens before saving.** Routes check failure conditions first and save last.
- **SQLAlchemy JSON columns must be reassigned, not mutated in place.** Otherwise changes aren't detected. This applies to e.g. `skipped_ingredients`.
- **AI output is never trusted raw.** It is always validated with Pydantic, and always shown to the user as an editable draft. This applies to every import (menus, invoices, sales), not only recipes. **One agreed exception (George, 25 Sep 2026):** bulk recipe estimates ("Estimate all") are saved straight away, through the normal recipe save route, but marked **AI · unchecked**, flagged by `recipe_checks.py`, and counted in the analysis with an "N unchecked" chip until the owner saves or confirms each one. Every AI estimate asks for confirmation first.
- **AI for understanding messy input, code for arithmetic.** Claude reads documents and maps columns. Plain Python does every calculation.
- **Analysis is always for a date range.** Only sales records wholly inside the range count; partly-overlapping ones are left out, not shared across days (the coverage route reports them). Only dishes on the menu for the whole range are analysed; part-range dishes are listed with a reason. A dish on the menu with no sales has sold 0 and is analysed. A total can't be entered for a period that already has other sales for that dish (it would double-count).
- **Every number records where it came from.** Prices carry a source (invoice / supplier list / benchmark) and a date. Keep history rather than overwriting, so "live" figures can be explained and traced.
- **Structured tables, not loose storage.** The flexibility comes from history and sources, not from JSON blobs. Calculations must stay testable.
- **No scraping third-party sites.** Data comes from the restaurant's own files, its own website, or a curated benchmark list.

## Known open items

1. **VAT decision (George).** Menu prices include 20% VAT, but margin % is currently calculated on the VAT-inclusive price. Industry reports gross margin excluding VAT. This would change the costing engine.

2. **Messier menus (parked by George).** Test menu import on real, messy menus (chalkboard photos, two-column layouts, decorative fonts) and report what breaks.
3. **Matcher cutoff (left as is by George).** `matching.suggest_ingredients` uses difflib cutoff 0.45, which gives poor "Or use:" suggestions (e.g. guanciale → ground coriander). Raising to ~0.6 would cut noise; core logic, George's call.

## Roadmap (in order)

Done: tests for costing and menu engineering (`backend/tests/`), and the frontend redesign (pages, summary, action list). New tests should keep to small hand-checkable examples, with the working in comments.

1. ~~**Price history and sources.**~~ Done. `IngredientPrice` holds one row per price seen (source, supplier, date). `costing.best_price` picks the price: the restaurant's own most recent, else the most recent benchmark, ignoring future-dated prices. Routes: `GET/POST /ingredients/{id}/prices`. Next small follow-up: show each dish's "% of cost from your own data".
**Principle: build the manual editors first, then the AI imports on top.** Every import ends in "check what the AI found before saving", and that check happens in the same editor. The app should be fully usable by hand after step 5. The owner's real routine is **monthly**: add invoices and sales → see what changed → act → check next month.

2. ~~**Menu.**~~ Done: menu list with status, add/edit/delete dishes, a dish page with the recipe editor (manual entry, AI draft, suggested matches, unit warnings, checks before saving). The recipe save route now rejects unknown or duplicate ingredients and quantities ≤ 0 before touching the saved recipe.
3. ~~**Ingredients page.**~~ Done: prices with source, date and history; record a new price as a pack price ("£93.60 for 12 kg"); add ingredients (duplicate names rejected); "X of Y ingredients on your menu use your own prices".
4. ~~**Sales and date ranges.**~~ Done: dishes have on-the-menu dates; sales are daily (or period totals); analysis runs over any date range with presets (latest month by default); Sales page with a coverage strip and manual totals.
5. ~~**Setup checklist, start fresh, empty states.**~~ Done: Settings → Start fresh / Load demo data (both back up first), a setup checklist on the Overview, short empty states.
6. ~~**Broaden the benchmark price list.**~~ Done: `data/benchmark_prices.csv`, ~250 ingredients across Italian, British pub, Indian and staples, with an update button in Settings.
7. ~~**AI imports**~~ Done (planned with George 24 Sep 2026, see "Step 7 plan" below): (a) menu price history, (b) invoice import, (c) till import, (d) menu import, (e) guided setup.
8. **Monthly routine:** "what changed since last period", price-rise alerts, and each dish's "% of cost from your own data".
9. **Business-wide suggestions:** rule-based and hand-checkable (e.g. GP vs typical for the restaurant type). Claude may reword them but doesn't invent them.
10. **Authentication:** JWT login with per-user data isolation. **Use plan mode and get approval before starting.** It touches every query, and it's required before deployment because the app spends API credit.
11. **Deployment**, so the app is reachable by a public link.
12. **README write-up:** what the app does, how it works, which parts George wrote, and how Claude Code was used.

**Out of scope for now:** review analysis, demand/rota forecasting, a free-form AI narrative layer, menu-gap analysis, scraping supplier/supermarket sites, and live integrations beyond one Square sandbox. Don't start these.

## Step 7 plan: AI imports (agreed 24 Sep 2026)

**Core principle: imports reconcile, they don't insert.** Owners re-upload menus, invoices and till exports repeatedly, so every import answers "what's different from what's stored?". Uploading the same thing twice must never double anything.

**One pipeline for all three:** Upload → **Extract** (Claude reads the document into structured rows, validated with Pydantic) → **Match** (code: remembered aliases first, then the existing two-tier matching) → **Review** (a table of changes with proposed actions, all editable; nothing saved yet) → **Apply** (one transaction, validation before saving, recorded as an `Import`; every row it creates carries `import_id`).

**Remembered aliases:** when the owner confirms a match ("MOZZ FDL 1KG" from a supplier → mozzarella (fior di latte); till item "MARG 12" → Margherita; a till's column mapping; lines to ignore such as cleaning or delivery), it's stored and pre-filled next time, shown as "remembered", still reviewable.

**Shared:** an `Import` record (kind, filename, source/supplier, effective date, status, summary); the original file kept in a git-ignored `backend/uploads/` with a hash; an Imports page listing history; friendly errors when Claude is unreachable; file size/type limits. Tests cover the deterministic parts (diffing, pack parsing, invoice arithmetic, column mapping, aggregation, aliases, apply/undo) with Claude mocked, plus made-up sample files (menu PDF, invoice, Square CSV) for manual end-to-end runs. Document/photo extraction uses a vision-capable model stronger than Haiku (confirm the current model ID when building).

**George's decisions:**
1. **Menu price history (core logic, approved):** a dish's menu price gets dated history, like ingredient prices. For a period spanning a price change, analysis uses the price in effect on each day, weighted by that day's units. Formulas unchanged; only how the price is found.
2. **Renames:** always ask the owner "same dish (renamed) or new dish?" when names are close. Never auto-merge.
3. **Drinks and non-dish items** (add-ons, set menus): ignored by default and remembered. No Drinks category for now.
4. **Size variants** (10" / 12"): each is its own dish.
5. **Undo:** invoice and sales imports can be undone (delete the rows carrying that `import_id`). Menu imports can't in v1; their changes stay editable by hand.
6. **Build order:** (a) menu price history → (b) invoice import → (c) till import → (d) menu import → (e) guided setup flow tying them together.

**Menu import rules** (the owner picks "this menu starts on [date]"; everything is dated from it):
- New dish → created, on the menu from the start date; shows as Needs recipe; Claude drafts its recipe using the menu description.
- Same dish, new price → new dated menu price; old price kept.
- Dish missing from the new menu → `on_menu_until` = day before the start date. Never deleted.
- Close name match → owner chooses renamed-same-dish vs new dish.
- Description changed → dish kept, recipe flagged "check recipe".
- Menu sections mapped to Starter / Main / Side / Dessert by Claude; the owner corrects them.

**Invoice import rules:** Claude extracts supplier, invoice number and date, and lines (description, pack as printed, quantity, unit price, line total). Code parses the pack ("12 x 1kg" → 12,000 g) through `units.py`, checks quantity × unit price ≈ line total (flag if not), matches lines (supplier alias → fuzzy → create ingredient → ignore), blocks a duplicate supplier + invoice number, and shows the change against the current price. Apply records `invoice` prices dated on the invoice date. Prices are ex-VAT.

**Till import rules:** Claude sees only the header and about 5 sample rows (cost, and keeps customer data out) and proposes a column mapping (date, item, quantity, refunds/voids, date format). Code parses every row, aggregates to per-dish daily totals, nets refunds, ignores modifiers, and remembers the mapping per till. Items are matched like invoices (drinks ignored by default). Re-importing a period replaces that source's daily totals for those dates; overlaps with manual totals follow the existing no-double-count rule and are shown as conflicts.

## The 5-minute demo (built for this)

Start from Settings → **Start fresh** (it backs up the database first; Load demo data restores the demo afterwards). Sample files are in `backend/samples/`.

1. **Menu:** the Setup page opens. Upload `sample-menu.pdf` (about 25 s). Set **Starts on** to 1 June 2026 so September's sales count. 22 dishes are found; drinks, add-ons and the lunch deal are ignored. Apply.
2. **Recipes:** "Recipe 1 of 22: Arancini". Press Estimate with AI, check the draft (it used the menu description), Save. The next dish opens with its draft already prepared. Do two or three, then go on (the rest stay "needs recipe").
3. **Your prices:** upload `sample-invoice.pdf`. Point out the pack maths (12 × 1 kg → £/kg), the ricotta "Totals don't add up" flag, guanciale as a new ingredient, and blue roll/delivery ignored. Apply.
4. **Sales:** upload `sample-sales.csv`. Claude maps the columns from 5 rows (customer columns blanked) and matches renamed till items ("Garlic Bread" → Garlic Pizza Bread); drinks are ignored. Set "Refunds marked in" to Event Type / Refund. Apply.
5. **Results:** See your results → the Overview for September: quadrants, ranked actions with £ impact, and the Continue setup card while recipes remain.

Talking points: every AI step ends in an editable review; code does all arithmetic; uploads reconcile rather than insert (re-upload the same file to show "Already imported"); undo on invoices and sales.

## Done: "deli counter" redesign (agreed and built 25 Sep 2026)

George chose design C from the mockups canvas (claude.ai/artifact/QNewzNGtSRNfS5haAHXXcJ, private): Bricolage Grotesque (narrow, heavy figures) + DM Mono, cream/paper/ink with tomato, mustard and basil blocks, pills, 2px ink outlines, dashed dividers, and A's **ticket rail** for recommended changes (tickets hanging off an ink rail, mustard clip, slight tilt, rotated quadrant stamp, dashed tear line, £ impact). Decisions: nav and page titles lowercase (dish names keep capitals); the top nav row scrolls sideways on narrow screens; figures not built yet ("% from your invoices", "latest invoice price") stay out until step 8; no sparkle/pencil glyphs on buttons.

Done (steps 1-5): tokens, fonts and shared classes; the header nav; tiles, ticket rail and stamps; every page (the Menu page's All view shows each category as a tinted block; the Recipes tab stays a table); these notes. The import review screens only picked up the shared classes and were not checked with a real upload.

Mobile (later, not a priority): responsive pass after the redesign, same app. Nav pills scroll or become a bottom bar; grids stack to one column; tables become stacked rows on phones except the heavy editors (recipe editor, reviews), which scroll sideways; the ticket rail swipes. Priorities: Overview, Actions, and invoice photos from the phone camera.

## Next: report agent (proposed 25 Sep 2026, awaiting George's "go")

George asked for a "Generate report" button on the Overview: Claude writes a report across all the data and suggests next actions, with "real thought" (an agent). This is an exception to "no free-form AI narrative" (out of scope) and needs recording as such once approved. Proposed design:

- **Agent with read-only tools** (plain Python over the data, each result stored as facts with ids): `period_summary` (contribution, sales, GP %, units vs previous period), `actions` (ranked £ actions, optional category), `dish_detail(dish)` (recipe lines and costs, price history, weekly sales, quadrant now vs last), `price_changes` (ingredient rises/falls in the period, dishes hit, £ margin effect), `sales_pattern(by: weekday|category|dish)`, `data_gaps` (missing recipes, unchecked AI recipes, days without sales).
- **Hand-written loop** (not an SDK runner), Sonnet 5, max 12 tool calls, ~1-2 min, ~20-50p per report.
- **Numbers rule:** Claude ends with a `write_report` tool (next steps + findings, each citing fact ids). Code checks every cited id exists and **no digits appear in Claude's text**; on failure the error goes back to Claude once. Every number on the page is drawn by code from the cited facts.
- **Runs as a background job**; the page polls each second and shows the live trail (tool calls, labelled by code), then the report (next steps first, findings with their numbers), printable / Save as PDF. **Finished reports are stored** (snapshot: period, date, facts, text) with a list of past reports.
- **Build order:** (1) tools + fact store + tests, no AI; (2) agent loop, checks, background job, tested with a scripted fake Claude (incl. a rule-breaking draft it must fix); (3) report page, Overview button, past reports; (4) CLAUDE.md + real run.
- **Decisions awaiting George:** hand-written loop; live trail via background job + polling; store reports; record the exception in CLAUDE.md.

After that: step 8 (price-rise alerts, "% of cost from your own data"; the report's `price_changes` covers part of it).

## How to work

- **For anything touching more than a couple of files, propose a plan first.** Wait for approval.
- **Make small, focused changes.** Suggest a commit after each logical step, with a clear one-line message (e.g. "Add error handling to recipe estimation").
- **Explain changes after making them.** Briefly say what changed, why, and how to check it works.
- **Run the tests after changes to backend logic.** All must pass before committing.
- **The main branch is `main`** (renamed from `master` in September 2026).
- **Never commit secrets.** The Anthropic API key stays in an environment variable / `.env` file that is git-ignored.
- **If something George asks for would break a design decision above, say so** before doing it.
- **If you're unsure what George intended, ask.** Don't guess.
