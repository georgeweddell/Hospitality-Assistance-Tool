# CLAUDE.md — Docket (Menu & Margin Engine)

Read this at the start of every session. It holds the rules and a map; the detail lives in `docs/`, read on demand:
- **`docs/architecture.md`**: what every backend and frontend file does, and the rules each module follows. **Read the part for a module before changing it.**
- **`docs/decisions.md`**: the agreed plans and George's decisions with dates (imports, redesign, report agent, roadmap detail).
- **`docs/demo.md`**: the 5-minute demo script.
- **`docs/deploy.md`**: the live site on Render (setup, updating, backups, limits).

## What this project is

**Docket** (the kitchen word for an order ticket) is a web app for small independent UK restaurants. A restaurant brings its data in whatever form it has (menu PDF or photo, supplier invoices, till exports); the app keeps a **live model of the menu** (each dish's cost and margin, kept up to date as prices and sales change) and suggests changes: Kasavana-Smith menu engineering (Star / Plowhorse / Puzzle / Dog) with a ranked £ action list, price-rise alerts, business checks against rules of thumb, and an AI-written report.

**Purpose:** a portfolio piece for Forward Deployed Engineer / Solutions Engineer interviews, not a commercial product. Clarity, correctness and explainability matter more than features. The aim is **one complete journey that works end to end and can be demoed in five minutes** (`docs/demo.md`).

## About the developer (George)

- Not an experienced software engineer. **Explain what you're doing and why in plain English; define technical terms the first time.**
- He wrote the core logic himself and must defend it in interviews. Kitchen background: he sanity-checks outputs with it.
- **Windows, VS Code.** Short, direct explanations, concrete rules, step-by-step reasoning. No padding, no buzzwords.

## Stack

- **Backend:** Python, FastAPI, SQLAlchemy (manual queries, no ORM relationships), Pydantic v2, SQLite. Flat files in `backend/`.
- **Frontend:** React + Vite, Recharts, Tailwind CSS v4. Hash routing, no router library.
- **AI:** Anthropic SDK. Haiku for recipes and till mapping; Sonnet 5 for invoices, menus and the report agent. Confirm model ids with the claude-api skill before changing them.
- **Ports:** backend 8000, frontend 5173.

## Map (detail in docs/architecture.md)

- **Backend (`backend/`):** `main.py` every route · `models.py` tables · `schemas.py` request/response shapes · `auth.py` logins, one database per account · `database.py` `get_db` (the logged-in account's database) · `costing.py` plate cost, `best_price`, dated menu prices · `menu_engineering.py` quadrants, action list, `proposed_change` · `units.py` pack price → base unit · imports: `invoices.py`/`invoice_ai.py`, `tills.py`/`till_ai.py`, `menus.py`/`menu_ai.py` · `recipe_ai.py`, `matching.py`, `recipe_checks.py` · `price_changes.py`, `own_prices.py` · `suggestions.py` + `data/business_rules.csv` · `report_tools.py`, `report_agent.py` · `sales_report.py` · `onboarding.py` · `benchmarks.py` + `data/benchmark_prices.csv` · `periods.py` · `seed_demo.py` (demo data, `reset_database`) · `create_account.py` · `tests/`.
- **Frontend (`frontend/src/`):** `App.jsx` (login gate, shared data, page choice) · `api.js` (all calls; the login is an httpOnly cookie) · `index.css` (the design system) · `components/` one file per page and piece · helpers `format.js`, `dateRange.js`, `actionText.js`, `quadrants.js`, `priceChanges.js`, `suggestions.js`.
- **Data:** each account's data is `backend/accounts/<id>/menu.db` (+ `uploads/`, `backups/`); accounts in `backend/auth.db`; `backend/menu.db` is what `seed_demo.py` builds. All git-ignored. `backend/.env` (git-ignored) holds `ANTHROPIC_API_KEY`, `SECRET_KEY`, `INVITE_CODE`, `GUEST_AI_CALLS`, `GUEST_REPORTS`. Settings for the live site (step 11, in `render.yaml`): `DATA_DIR` (where `auth.db` and `accounts/` live; default `backend/`), `COOKIE_SECURE=1`, `DEMO_ENABLED=0`, `ALLOWED_ORIGINS` (dev CORS only).

## Running it

Each server in its own terminal (PowerShell), from the project root.

```powershell
cd backend
.\venv\Scripts\python.exe -m uvicorn main:app --reload     # http://localhost:8000 (docs at /docs)
```
```powershell
cd frontend
npm run dev                                                  # http://localhost:5173
```
```powershell
cd backend
.\venv\Scripts\python.exe -m pytest                          # all tests
.\venv\Scripts\python.exe create_account.py you@example.com --from-db menu.db   # an owner account from existing data
```

- Always start the backend from inside `backend/` and use `backend\venv\Scripts\python.exe`, not the system Python.
- Restart the backend after changing `models.py` or adding routes (`--reload` can leave it half-updated). **Any schema change (a new table or column) needs an Alembic migration:** change `models.py`, then from `backend/` run `.\venv\Scripts\alembic.exe revision --autogenerate -m "what changed"`, read the new file in `migrations/versions/`, restart the backend, and commit it. It compares the models with `backend/menu.db`, so write the migration before restarting. Each account catches up when it's next opened (`migrate.py`).
- If new Tailwind classes don't apply, restart the frontend dev server.
- One-off scripts are never named `test_*.py` (pytest would run them).

## Core logic — do not change without asking first

George wrote these and must be able to explain them. **Propose and explain; don't just change.**
- **Costing engine:** plate cost and margin.
- **Menu-engineering classification:** quadrant thresholds, and the Dog/Plowhorse/Puzzle impact formulas.
- **Recipe-estimation prompt.**
- **Fuzzy-matching pipeline** (AI ingredient names → the ingredient table).
- **Recipe save route** validation.

## Design decisions to preserve

- **Units are normalised at entry** (base units: gram / ml / each) through `units.py`. Costing has no conversion logic.
- **Excluded dishes come out of the denominator too**, or every other dish's thresholds shift.
- **Every £ in the action list is a change (delta) in contribution**, not a level (Dog/Plowhorse impact = (category weighted-average margin − dish margin) × units).
- **The recipe prompt is grounded in the live ingredient list**, fetched on every call.
- **The dashboard loads in a fixed number of calls**, never one per dish.
- **Validate before saving.** Routes check failure conditions first, save last.
- **SQLAlchemy JSON columns are reassigned, never mutated in place.**
- **AI output is never trusted raw:** Pydantic-validated and shown as an editable draft before saving. One agreed exception: bulk "Estimate all" recipes are saved as **AI · unchecked** and flagged until checked. Every AI estimate asks for confirmation first.
- **AI reads messy input; code does every calculation.** In the report, Claude cites fact ids and writes no digits; every number is a code-made fact.
- **Analysis is always for a date range;** only sales wholly inside it count; only dishes on the menu for the whole range are analysed.
- **Every number records where it came from** (price source and date); keep history, don't overwrite.
- **Structured tables, not loose storage.** Calculations stay testable.
- **One database per account** (step 10): routes get data only through `get_db`; never read another account's files.
- **No scraping third-party sites.**

## Frontend rules

- **Use the design system in `src/index.css`** (tokens and shared classes: `btn`, `input`, `card`, `table`, `chip`, `tile`, `ticket`, `stamp`, `chart-tip`…). No one-off button, input, table or card styles in components; change a look in `index.css`, once. Light theme only (cream, paper, ink; tomato, mustard, basil). Not the class name `block` (a Tailwind utility).
- **No explanatory sentences on screen:** labels, figures and short chips only. **No AI-sounding asides** ("usually about 25 s", "this may take a moment", "tip:", "great, …"). Explanations go in `components/Hint.jsx` (hover / click). Check every new piece of on-screen text against this.
- **Reports and checks (any kind, AI report included): no tip or rule-of-thumb lines.** A benchmark is a short **target** figure beside the real one ("≥ 0.35 per main"); the reasoning goes in the Hint; the action is one short instruction ("Upsell desserts"), with no "or …" alternatives.
- **Lowercase** nav, page titles, section titles, tabs, buttons and tile labels (mostly done by CSS); dish names keep their capitals. **No glyphs on buttons** (no ✦ or ✎): buttons say what they do in words.
- **Never `window.confirm` / `alert` / `prompt`** (the app's browser pane blocks them): use `components/ConfirmDialog.jsx`.
- **All API calls through `src/api.js`**, never `fetch` in a component.

## Known open items

1. **VAT (George's decision).** Margins use VAT-inclusive menu prices; the trade reports GP ex-VAT. Changing it changes the costing engine. (The business checks' food cost check alone works ex-VAT.)
2. **Messier menus (parked).** Test menu import on real messy menus and report what breaks.
3. **Matcher cutoff (left as is).** difflib 0.45 gives poor "Or use:" suggestions; ~0.6 would be cleaner. Core logic.
4. **Rules of thumb to review (George).** `backend/data/business_rules.csv` holds starting values, not researched figures.
5. **`auth.db` has no migrations.** It uses `create_all` (new tables only); changing an `Account` column needs Alembic set up for it too.
6. **One server process only.** Login limits, open databases and report jobs live in memory; don't run more than one instance or worker.

## Roadmap

1–10 done (detail in `docs/decisions.md`): price history · menu editor · ingredients · sales and date ranges · setup and reset · benchmark list · AI imports (menu, invoice, till, guided setup) · monthly routine (price-rise alerts, own-price share) · business checks · logins (one database per account, invite code, Try the demo). Also done: the "deli counter" redesign and the report agent.

11. **Deployment** on Render: built (28 Sep 2026): httpOnly login cookie, login-attempt limits, `DEMO_ENABLED` switch (off live), Alembic migrations, one server for page and API, `DATA_DIR` on a persistent disk, `Dockerfile` + `render.yaml`. **George to deploy** (`docs/deploy.md`).
12. **README write-up:** what the app does, how it works, which parts George wrote, how Claude Code was used.

**Out of scope:** review analysis, demand/rota forecasting, menu-gap analysis, scraping supplier sites, live integrations beyond one Square sandbox.

## How to work

- **Anything touching more than a couple of files: propose a plan first** and wait for approval. Big or risky steps (like logins) in plan mode.
- **Small, focused changes.** Suggest a commit after each logical step with a clear one-line message. **Commit and push only when George asks.** Commit messages end with a blank line, then the Co-Authored-By line.
- **Explain changes after making them:** what changed, why, how to check it.
- **Run the tests after backend changes;** all must pass before committing. New tests use small hand-checkable examples with the working in comments. Tests call route functions directly (FastAPI's TestClient doesn't work with these library versions).
- **Check UI changes in the browser** (read page text; screenshots only when the look matters).
- **Keep the context small:** read only the parts of files needed; put long scripts in scratch files, not the chat; keep replies short. Record lasting decisions in `docs/decisions.md` and module detail in `docs/architecture.md`, not here.
- **Main branch is `main`.** **Never commit secrets** (`.env`, `auth.db`, `accounts/`).
- **If something George asks for would break a decision above, say so first.** If unsure what he meant, ask.
