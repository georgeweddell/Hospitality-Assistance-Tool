# CLAUDE.md — Mise (Menu & Margin Engine)

This file gives Claude Code the context it needs to work on this project. Read it fully at the start of every session.

## What this project is

**Mise** (from *mise en place*) is a web app for small independent UK restaurants. A restaurant brings its data in whatever form it has: a menu PDF or photo, supplier invoices, till exports. The app keeps a **live model of the menu**: it estimates each dish's cost and margin, and keeps them up to date as prices and sales change. It then suggests changes, both to the menu and to the business as a whole.

### The target journey (what we're building towards)

1. **Setup:** the user describes the business (type of restaurant, location, rough covers per day) and uploads a menu (PDF, photo or website link). Claude extracts dishes (name, price, category, description), and the user checks the list before it's saved.
2. **Recipes:** Claude estimates each dish's recipe from its name and description, grounded in the ingredient list. The user checks each one in the recipe editor on the dish page ("AI proposes, human verifies").
3. **Costs:** ingredients start on benchmark prices. The user uploads supplier invoices, Claude extracts the lines, and they're matched to ingredients and normalised to base units. **Every price records its source and date**, and costing uses the best available. Each dish shows how much of its cost comes from the restaurant's own data. Price changes raise alerts.
4. **Sales:** the user uploads a till export (CSV/Excel). Claude identifies which column is which, then code reads the numbers and matches items to dishes. A direct connection to Square's test environment is a stretch goal.
5. **Results:** Kasavana-Smith menu engineering (Star / Plowhorse / Puzzle / Dog), a ranked action list with £ impact, a menu summary, and rule-based business-wide suggestions.

### Where it is now

Step 2 works (dish page with recipe editor and AI draft), and step 5 works at menu level. Dishes are added one at a time on the Menu page. Prices have history and sources, and the Ingredients page lets owners enter them from invoices by hand (no invoice upload yet). Sales are stored per dish per day (or as a total for a period), and every analysis runs over a chosen date range; the Sales page shows which days have data and takes manual totals (no till-file upload yet). The demo database comes from `seed_demo.py`.

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
  - `costing.py`: costing engine (`cost_dish`), and `best_price`, which chooses which dated price to use.
  - Changing `models.py` needs the database rebuilt (`seed_demo.py`), because there's no migration tool yet (Alembic is needed before deployment). Restart the backend afterwards, because `--reload` can leave it running a half-updated copy.
  - `menu_engineering.py`: classification, action list, incomplete-dish detection, all for a date range (`start`, `end`). The rules for which sales and dishes count are in the comment at the top of the file. `get_category_stats` costs each dish and counts its units **once per category**; the helpers and `classify_dish` read from it. Don't reintroduce per-dish recalculation of category totals, which made the dashboard about 6× slower.
  - `recipe_ai.py`: recipe-estimation prompt and the Anthropic call.
  - `matching.py`: exact match first, then `difflib` fuzzy suggestions.
  - `periods.py`: month maths and the default range (the month containing the latest sale). Analysis routes take `?from=YYYY-MM-DD&to=YYYY-MM-DD`; without them they use that default.
  - `units.py`: converts a pack price ("£93.60 for 12 kg") into a price per base unit. **Every price input path goes through it** (the price routes do via `base_unit_price` in `main.py`, and invoice import must too).
  - `seed_demo.py`: wipes and rebuilds `menu.db` with realistic demo data (June–August 2026 of daily sales at a small UK pizzeria, hand-written recipes; June's days add up to the original June totals). It backs up the old database to `menu.backup-<timestamp>.db` first. This is the way to reset the demo.
  - `seed_recipes.py`: re-estimates every dish's recipe with the real API and auto-accepts matches. It overwrites the hand-written demo recipes, so it's for AI testing only.
  - `ai_test_v1.py`, `ai_test_v2.py`, `dish_check.py`, `match_check.py`, `costing_check.py`, `ingredient_list.py`: one-off scripts written during development. They are **not** pytest tests. Don't name scripts `test_*.py`, or pytest will run them.
  - `tests/`: pytest tests. `conftest.py` gives every test a fresh in-memory database. Tests never read or write `menu.db` data (importing `main` runs `create_all`, which only creates missing tables). `pytest.ini` sets the test path.
  - The SQLite database is `backend/menu.db` (git-ignored). The API key lives in `backend/.env` (git-ignored).
  - The Python virtual environment is at `backend/venv/`.
  - Use `backend/venv/Scripts/python.exe`, not the system Python.
- `frontend/` holds the React app.
  - `src/App.jsx` loads the shared data once and picks the page. Pages are switched by the URL hash via `src/useHashRoute.js`, with no router library: Overview (`#/overview`), Menu (`#/menu`), a dish page (`#/menu/12`), Ingredients (`#/ingredients`), Sales (`#/sales`) and Insights (`#/analysis`). `components/Layout.jsx` holds the sidebar navigation.
  - The dish page (`DishPage.jsx`) loads its own detail (`GET /dishes/{id}/detail` plus `/ingredients`). `RecipeEditor.jsx` edits the recipe there. "Estimate with AI" fills the editor as a draft, and nothing is saved until Save. The editor's plate cost is a live preview; the saved figures always come from the backend costing engine.
  - `IngredientsPage.jsx` loads `/ingredients` itself (current price, source, date and `used_in` count). Prices are entered as a pack price (`PriceFields.jsx`, helpers in `src/prices.js`). The £/kg shown while typing is only a preview; the backend does the real conversion.
  - The chosen period lives in `App.jsx` (kept in session storage) and is picked with `RangePicker.jsx`. Presets are relative to the latest sale, not today (`src/dateRange.js`), so an old dataset still opens on data.
  - **Design system (Mise): `src/index.css`.** Every colour (tokens on `:root`), the fonts (Fraunces for headings and figures, Instrument Sans for everything else) and the shared component classes live there: `btn btn-primary|secondary|danger|sm`, `input`, `field` + `label`, `card` / `card-header` / `card-body`, `table` (+ `row-link`), `chip chip-warn|muted|accent`, `count`, `tabs` / `tab`, `segmented`, `alert-error`, `alert-info`, `empty`, `page-title`, `section-title`, `stat-value`, `num`, `link`. **Use these; don't write one-off button, input, table or card styles in a component.** Change a look in `index.css`, once.
  - Light theme only (cream paper, tomato accent). Quadrant colours (basil, saffron, cobalt, aubergine) are in `src/quadrants.js`, with a darker `text` shade for badge text contrast.
  - Keep visible subtext to a minimum: labels and figures, not explanatory sentences.
  - Chart labels are positioned by `src/labelPlacement.js` so dish names don't overlap.
  - Components live in `src/components/`. Quadrant colours live in `src/quadrants.js`, menu categories in `src/categories.js`, and number and unit formatting in `src/format.js` (prices are shown as £/kg, £/l or each).
  - All API calls go through `src/api.js`, using the `getJson` / `postJson` / `putJson` / `deleteJson` helpers. Don't call `fetch` directly from components.
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
- **The API serves the dashboard efficiently.** The app loads its shared data in a fixed number of calls, never one per dish: `/dishes/classifications`, `/dishes/action-list`, `/dishes/incomplete` and `/sales/coverage` (all for the chosen range), plus `/dishes`. The dish page makes its own call for the one dish it shows. Don't reintroduce per-dish calls on list pages.
- **Validation happens before saving.** Routes check failure conditions first and save last.
- **SQLAlchemy JSON columns must be reassigned, not mutated in place.** Otherwise changes aren't detected. This applies to e.g. `skipped_ingredients`.
- **AI output is never trusted raw.** It is always validated with Pydantic, and always shown to the user as an editable draft. This applies to every import (menus, invoices, sales), not only recipes.
- **AI for understanding messy input, code for arithmetic.** Claude reads documents and maps columns. Plain Python does every calculation.
- **Analysis is always for a date range.** Only sales records wholly inside the range count; partly-overlapping ones are left out, not shared across days (the coverage route reports them). Only dishes on the menu for the whole range are analysed; part-range dishes are listed with a reason. A dish on the menu with no sales has sold 0 and is analysed. A total can't be entered for a period that already has other sales for that dish (it would double-count).
- **Every number records where it came from.** Prices carry a source (invoice / supplier list / benchmark) and a date. Keep history rather than overwriting, so "live" figures can be explained and traced.
- **Structured tables, not loose storage.** The flexibility comes from history and sources, not from JSON blobs. Calculations must stay testable.
- **No scraping third-party sites.** Data comes from the restaurant's own files, its own website, or a curated benchmark list.

## Known open items

1. **VAT decision (George).** Menu prices include 20% VAT, but margin % is currently calculated on the VAT-inclusive price. Industry reports gross margin excluding VAT. This would change the costing engine.

## Roadmap (in order)

Done: tests for costing and menu engineering (`backend/tests/`), and the frontend redesign (pages, summary, action list). New tests should keep to small hand-checkable examples, with the working in comments.

1. ~~**Price history and sources.**~~ Done. `IngredientPrice` holds one row per price seen (source, supplier, date). `costing.best_price` picks the price: the restaurant's own most recent, else the most recent benchmark, ignoring future-dated prices. Routes: `GET/POST /ingredients/{id}/prices`. Next small follow-up: show each dish's "% of cost from your own data".
**Principle: build the manual editors first, then the AI imports on top.** Every import ends in "check what the AI found before saving", and that check happens in the same editor. The app should be fully usable by hand after step 5. The owner's real routine is **monthly**: add invoices and sales → see what changed → act → check next month.

2. ~~**Menu.**~~ Done: menu list with status, add/edit/delete dishes, a dish page with the recipe editor (manual entry, AI draft, suggested matches, unit warnings, checks before saving). The recipe save route now rejects unknown or duplicate ingredients and quantities ≤ 0 before touching the saved recipe.
3. ~~**Ingredients page.**~~ Done: prices with source, date and history; record a new price as a pack price ("£93.60 for 12 kg"); add ingredients (duplicate names rejected); "X of Y ingredients on your menu use your own prices".
4. ~~**Sales and date ranges.**~~ Done: dishes have on-the-menu dates; sales are daily (or period totals); analysis runs over any date range with presets (latest month by default); Sales page with a coverage strip and manual totals.
5. **Home setup checklist and empty states**, plus a "start fresh" option (benchmark prices, no demo dishes). The demo stays the default database until login exists.
6. **Broaden the benchmark price list** beyond Italian, to a few cuisines done well.
7. **AI imports:** menu upload (PDF/photo/URL), invoice upload, sales file upload (CSV/Excel). Each ends in the matching editor from steps 2–4.
8. **Monthly routine:** "what changed since last period", price-rise alerts, and each dish's "% of cost from your own data".
9. **Business-wide suggestions:** rule-based and hand-checkable (e.g. GP vs typical for the restaurant type). Claude may reword them but doesn't invent them.
10. **Authentication:** JWT login with per-user data isolation. **Use plan mode and get approval before starting.** It touches every query, and it's required before deployment because the app spends API credit.
11. **Deployment**, so the app is reachable by a public link.
12. **README write-up:** what the app does, how it works, which parts George wrote, and how Claude Code was used.

**Out of scope for now:** review analysis, demand/rota forecasting, a free-form AI narrative layer, menu-gap analysis, scraping supplier/supermarket sites, and live integrations beyond one Square sandbox. Don't start these.

## How to work

- **For anything touching more than a couple of files, propose a plan first.** Wait for approval.
- **Make small, focused changes.** Suggest a commit after each logical step, with a clear one-line message (e.g. "Add error handling to recipe estimation").
- **Explain changes after making them.** Briefly say what changed, why, and how to check it works.
- **Run the tests after changes to backend logic.** All must pass before committing.
- **The main branch is `main`** (renamed from `master` in September 2026).
- **Never commit secrets.** The Anthropic API key stays in an environment variable / `.env` file that is git-ignored.
- **If something George asks for would break a design decision above, say so** before doing it.
- **If you're unsure what George intended, ask.** Don't guess.
