# CLAUDE.md — Menu & Margin Engine

This file gives Claude Code the context it needs to work on this project. Read it fully at the start of every session.

## What this project is

A web app for small independent UK restaurants. It turns a menu into a costed, ranked set of actions:

1. The user enters dishes (name, menu price, category).
2. Claude (Anthropic API, Haiku model) estimates each dish's recipe as structured JSON.
3. The user reviews and corrects that estimate on the Recipe Review screen ("AI proposes, human verifies").
4. Each ingredient is costed against an ingredient price table. The app computes plate cost and gross margin per dish.
5. The user enters a sales mix (units sold per dish).
6. The app classifies each dish using Kasavana-Smith menu engineering (Star / Plowhorse / Puzzle / Dog). It then produces a ranked action list with a £ impact for each action.
7. A dashboard shows a popularity-vs-margin scatter chart, per-dish cards and the action list.

**Purpose:** a portfolio piece for Forward Deployed Engineer / Solutions Engineer interviews. It is NOT being built as a commercial product. Clarity, correctness and explainability matter more than features.

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
  - `seed.py`, `seed_Phase4.py`, `seed_dish.py`, `seed_recipes.py`: seed scripts. `seed_recipes.py` calls the real API and auto-accepts matches (test data only).
  - `ai_test_v1.py`, `ai_test_v2.py`, `dish_check.py`, `match_check.py`, `costing_check.py`, `ingredient_list.py`: one-off scripts written during development. They are **not** pytest tests. Don't name scripts `test_*.py`, or pytest will run them.
  - `tests/`: pytest tests. `conftest.py` gives every test a fresh in-memory database, never `menu.db`. `pytest.ini` sets the test path.
  - The SQLite database is `backend/menu.db` (git-ignored). The API key lives in `backend/.env` (git-ignored).
  - The Python virtual environment is at `backend/venv/`.
  - Use `backend/venv/Scripts/python.exe`, not the system Python.
- `frontend/` holds the React app.
  - `src/App.jsx` is the single page. Components live in `src/components/`.
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
- **AI output is never trusted raw.** It is always validated with Pydantic, and always shown to the user as an editable draft.

## Known open items

None at the moment.

## Roadmap (in order)

1. Fix the open items above.
2. ~~Add automated tests (pytest) for the costing engine and menu-engineering logic.~~ Done (`backend/tests/`). New tests should keep to small hand-checkable examples, with the working in comments.
3. Visual polish / styling pass on the frontend.
4. Authentication: JWT-based login with per-user data isolation. **Use plan mode and get approval before starting.** This touches every query.
5. Deployment, so the app is reachable by a public link.
6. README write-up covering what the app does, how it works, which parts George wrote, and how Claude Code was used.

**Out of scope for now:** review analysis, demand/rota forecasting, an AI narrative layer, menu-gap analysis. Don't start these.

## How to work

- **For anything touching more than a couple of files, propose a plan first.** Wait for approval.
- **Make small, focused changes.** Suggest a commit after each logical step, with a clear one-line message (e.g. "Add error handling to recipe estimation").
- **Explain changes after making them.** Briefly say what changed, why, and how to check it works.
- **Run the tests after changes to backend logic.** All must pass before committing.
- **The main branch is `main`** (renamed from `master` in September 2026).
- **Never commit secrets.** The Anthropic API key stays in an environment variable / `.env` file that is git-ignored.
- **If something George asks for would break a design decision above, say so** before doing it.
- **If you're unsure what George intended, ask.** Don't guess.
