# CLAUDE.md — Menu & Margin Engine

This file gives Claude Code the context it needs to work on this project. Read it fully at the start of every session.

## What this project is

A web app for small independent UK restaurants. A restaurant brings its data in whatever form it has: a menu PDF or photo, supplier invoices, till exports. The app keeps a **live model of the menu**: it estimates each dish's cost and margin, and keeps them up to date as prices and sales change. It then suggests changes, both to the menu and to the business as a whole.

### The target journey (what we're building towards)

1. **Setup:** the user describes the business (type of restaurant, location, rough covers per day) and uploads a menu (PDF, photo or website link). Claude extracts dishes (name, price, category, description), and the user checks the list before it's saved.
2. **Recipes:** Claude estimates each dish's recipe from its name and description, grounded in the ingredient list. The user checks each one on the Recipe Review screen ("AI proposes, human verifies").
3. **Costs:** ingredients start on benchmark prices. The user uploads supplier invoices, Claude extracts the lines, and they're matched to ingredients and normalised to base units. **Every price records its source and date**, and costing uses the best available. Each dish shows how much of its cost comes from the restaurant's own data. Price changes raise alerts.
4. **Sales:** the user uploads a till export (CSV/Excel). Claude identifies which column is which, then code reads the numbers and matches items to dishes. A direct connection to Square's test environment is a stretch goal.
5. **Results:** Kasavana-Smith menu engineering (Star / Plowhorse / Puzzle / Dog), a ranked action list with £ impact, a menu summary, and rule-based business-wide suggestions.

### Where it is now

Steps 2 (estimate only, since the review screen is unfinished) and 5 (menu-level only) exist. Dishes are typed in one at a time, prices are a single fixed table, and sales can only be added through the API. The demo database comes from `seed_demo.py`.

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
  - `costing.py`: costing engine (`cost_dish`).
  - `menu_engineering.py`: classification, action list, incomplete-dish detection.
  - `recipe_ai.py`: recipe-estimation prompt and the Anthropic call.
  - `matching.py`: exact match first, then `difflib` fuzzy suggestions.
  - `seed_demo.py`: wipes and rebuilds `menu.db` with realistic demo data (a month at a small UK pizzeria, hand-written recipes). It backs up the old database to `menu.backup-<timestamp>.db` first. This is the way to reset the demo.
  - `seed_recipes.py`: re-estimates every dish's recipe with the real API and auto-accepts matches. It overwrites the hand-written demo recipes, so it's for AI testing only.
  - `ai_test_v1.py`, `ai_test_v2.py`, `dish_check.py`, `match_check.py`, `costing_check.py`, `ingredient_list.py`: one-off scripts written during development. They are **not** pytest tests. Don't name scripts `test_*.py`, or pytest will run them.
  - `tests/`: pytest tests. `conftest.py` gives every test a fresh in-memory database, never `menu.db`. `pytest.ini` sets the test path.
  - The SQLite database is `backend/menu.db` (git-ignored). The API key lives in `backend/.env` (git-ignored).
  - The Python virtual environment is at `backend/venv/`.
  - Use `backend/venv/Scripts/python.exe`, not the system Python.
- `frontend/` holds the React app.
  - `src/App.jsx` loads all dashboard data once and picks the page. Pages (Overview, Analysis, Dishes, Menu setup) are switched by the URL hash (`#/dishes`) via `src/useHashRoute.js`, with no router library. `components/Layout.jsx` holds the sidebar navigation.
  - Components live in `src/components/`. Quadrant colours live in `src/quadrants.js`, and number formatting lives in `src/format.js`.
  - All API calls go through `src/api.js`, using the `getJson` / `postJson` helpers. Don't call `fetch` directly from components.
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

- **Units are normalised at data-entry time.** Everything is stored in base units, so the costing function has no conversion logic. Keep it that way. Any new input path must normalise units before saving.
- **Excluded dishes come out of the denominator too.** When a dish is excluded from analysis (e.g. its recipe is incomplete), it must also be removed from the totals used for thresholds. Otherwise every other dish's popularity threshold silently shifts.
- **Every number in the action list is the same kind of number.** Every £ impact is a *change* (delta) in contribution, not a current level. For example, Dog impact = (category weighted-average margin − dish margin) × units. "Weighted" means each dish's margin counts in proportion to its units sold (the Kasavana-Smith method). Plowhorse impact deliberately uses the same formula.
- **The recipe prompt is grounded in the live ingredient list.** That list is fetched from the database on every call, so AI output uses the same ingredient names as the table.
- **The API serves the dashboard efficiently.** The dashboard loads with a fixed number of calls, never one per dish: `/dishes/classifications`, `/dishes/action-list` and `/dishes/incomplete` (plus `/dishes` for the Recipe Review dropdown). Don't reintroduce per-dish calls.
- **Validation happens before saving.** Routes check failure conditions first and save last.
- **SQLAlchemy JSON columns must be reassigned, not mutated in place.** Otherwise changes aren't detected. This applies to e.g. `skipped_ingredients`.
- **AI output is never trusted raw.** It is always validated with Pydantic, and always shown to the user as an editable draft. This applies to every import (menus, invoices, sales), not only recipes.
- **AI for understanding messy input, code for arithmetic.** Claude reads documents and maps columns. Plain Python does every calculation.
- **Every number records where it came from.** Prices carry a source (invoice / supplier list / benchmark) and a date. Keep history rather than overwriting, so "live" figures can be explained and traced.
- **Structured tables, not loose storage.** The flexibility comes from history and sources, not from JSON blobs. Calculations must stay testable.
- **No scraping third-party sites.** Data comes from the restaurant's own files, its own website, or a curated benchmark list.

## Known open items

1. **Recipe Review screen is unfinished.** "Estimate recipe" returns a draft, but it isn't displayed, editable or saveable (`rows` in `RecipeReview.jsx` is unused).
2. **VAT decision (George).** Menu prices include 20% VAT, but margin % is currently calculated on the VAT-inclusive price. Industry reports gross margin excluding VAT. This would change the costing engine.
3. **The dashboard endpoints are slow** (several seconds): `menu_engineering.py` runs many small queries per dish. Worth fixing before deployment. That file is core logic, so propose the change first.

## Roadmap (in order)

Done: tests for costing and menu engineering (`backend/tests/`), and the frontend redesign (pages, summary, action list). New tests should keep to small hand-checkable examples, with the working in comments.

1. **Price history and sources:** database changes so each ingredient can have many dated prices with a source, and costing uses the best one. This changes the costing engine: plan first, George approves.
2. **Finish Recipe Review:** show the draft, edit quantities, pick between suggested matches, flag unit mismatches, save.
3. **Broaden the benchmark price list** beyond Italian, to a few cuisines done well.
4. **Invoice upload:** Claude extracts lines, then matching, unit normalisation and review before saving.
5. **Menu upload:** PDF/photo/URL, then Claude extracts dishes, then review.
6. **Sales upload:** CSV/Excel, then column mapping, then dish matching, then review.
7. **Guided setup flow** tying 5, 2, 4 and 6 together, plus a business profile.
8. **Business-wide suggestions:** rule-based and hand-checkable (e.g. GP vs typical for the restaurant type). Claude may reword them but doesn't invent them.
9. **Authentication:** JWT login with per-user data isolation. **Use plan mode and get approval before starting.** It touches every query, and it's required before deployment because the app spends API credit.
10. **Deployment**, so the app is reachable by a public link.
11. **README write-up:** what the app does, how it works, which parts George wrote, and how Claude Code was used.

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
