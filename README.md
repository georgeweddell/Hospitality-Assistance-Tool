# Docket

**A menu and margin engine for small independent UK restaurants.** A restaurant brings the data it already has (a menu PDF or photo, supplier invoices, a till export). Docket builds a live model of the menu: what each dish costs to make, what it earns, and how that changes as prices and sales move. Then it says what to change, in pounds.

*Docket* is the kitchen word for an order ticket.

> **Live:** [docket-u00z.onrender.com](https://docket-u00z.onrender.com/) (accounts by invite; get in touch for access)

I built it as a portfolio project for Forward Deployed Engineer and Solutions Engineer roles. It was inspired by my own time line-cooking in a Neapolitan pizzeria. The aim was one complete journey that works from start to finish: messy real-world input, AI that reads it, code that does the maths, and a person who checks both.

---

## What it does

1. **Bring your data, in whatever form it's in.**
   - **Menu:** a PDF or photo of the menu becomes a list of dishes, prices and categories. Drinks, add-ons and meal deals are recognised and left out.
   - **Recipes:** Claude estimates each dish's ingredients and quantities from its name and menu description, using only ingredients the restaurant actually stocks.
   - **Supplier invoices:** Claude reads a PDF or photo. Code works out the pack maths (12 × 1 kg at £30 → £2.50/kg), flags totals that don't add up, and spots new ingredients.
   - **Till exports:** Claude maps the columns of any CSV export and matches renamed till items to dishes ("Garlic Bread" → Garlic Pizza Bread).
2. **Check before anything is saved.** Every AI step ends in an editable review screen. Nothing the AI reads is trusted until a person confirms it.
3. **See where the money is.** For any date range, every dish gets a plate cost, a margin and a **menu-engineering** quadrant (Kasavana-Smith):
   | | Sells well | Sells poorly |
   |---|---|---|
   | **High margin** | ⭐ Star: keep it | 🧩 Puzzle: promote it |
   | **Low margin** | 🐴 Plowhorse: reprice or rework it | 🐶 Dog: rework or cut it |
4. **Get a ranked list of changes, in £.** For example: "Margherita: £11.50 → £12.40, +£657 a month". Each figure is the *change* in contribution the move would make, so the list can be ranked.
5. **Keep it up to date.**
   - **Price-rise alerts:** when a new invoice raises an ingredient's price, the dishes that use it are shown.
   - **Business suggestions:** checks against trade rules of thumb (food cost %, desserts per main, midweek trade, over-reliance on one ingredient, and more).
   - **AI report:** Claude investigates the data with read-only tools and writes next steps. Every number in the report comes from code, not from Claude.

## How it works

```
 menu PDF · invoice · till CSV          React + Vite (review screens, dashboard)
            │                                        │  one address, httpOnly login cookie
            ▼                                        ▼
   Claude reads it ──► Pydantic-validated draft ──► FastAPI ──► SQLAlchemy ──► SQLite
   (Sonnet 5 / Haiku)   shown for a person to edit     │        one database per account
                                                       ▼
                               costing · menu engineering · checks   (plain Python, tested)
```

**The rule the whole app follows: AI reads messy input; code does every calculation.**

- **AI output is never trusted raw.** It's validated against a schema (Pydantic) and shown as an editable draft. The one exception is bulk "Estimate all" recipes: they're saved, but marked **AI · unchecked** until a person confirms them.
- **The recipe prompt is grounded in the live ingredient list.** An early version let Claude name ingredients freely and matched the names afterwards. "Wheat flour" didn't match "00 flour", the ingredient was silently dropped, and the margin came out badly wrong. Now the restaurant's actual stock list is part of every prompt.
- **In the report, Claude writes no digits.** It cites fact ids ("f7", "f13"). The page shows the numbers code worked out, and code rejects any report that breaks the rule.
- **Units are made consistent at entry.** Every quantity is stored in grams, millilitres or "each", so the costing engine only ever multiplies and never converts.
- **Every £ in the action list is a change, not a level.** For a Plowhorse or a Dog, the impact is (category's weighted-average margin − the dish's margin) × units sold.
- **Analysis is always for a date range.** Only sales wholly inside it count, and only dishes on the menu for the whole range are analysed. A dish taken out of the analysis also comes out of the averages, or every other dish's quadrant would shift.
- **Every number records where it came from** (which invoice or benchmark, and its date). Price history is kept, never overwritten, and imports can be undone.

**Stack:** Python, FastAPI, SQLAlchemy, Pydantic v2, SQLite, Alembic · React, Vite, Tailwind CSS v4, Recharts · Anthropic SDK (Claude Sonnet 5 for invoices, menus and the report agent; Haiku for recipes and till mapping) · pytest (291 tests) · Docker and Render for deployment.

**Accounts:** each restaurant's data is its own SQLite file, opened only through one function (`get_db`) for the logged-in account. No query can leak data between accounts, even if someone forgets a filter. Logins use a signed token in an httpOnly cookie, with limits on login attempts. Schema changes reach every account's database through Alembic migrations.

## Who built what

**I wrote the core logic myself**, typing it by hand, with help on the code from Claude in chat:
- the **costing engine** (plate cost and margin);
- the **menu-engineering classification** (the quadrant thresholds, and the formulas for the £ impact of Dog, Plowhorse and Puzzle changes);
- the **recipe-estimation prompt**, and the **fuzzy matching** that links the AI's ingredient names to the ingredient table;
- the **validation on saving a recipe**.

I wrote the first working version the same way (July 2026): the data models, the costing, AI recipe estimation with matching, menu engineering with the ranked action list, and a first React dashboard.

**Claude Code built most of what came after, under my direction:**
- the AI imports (menu, invoice, till);
- the report agent;
- the "deli counter" redesign;
- logins with one database per account;
- the deployment work;
- most of the tests.

Around 86 of the project's 100 commits are co-authored with it.

## How I used Claude Code

How the work was set up:

- **A written brief it reads every session.** [`CLAUDE.md`](CLAUDE.md) holds the rules: the design decisions above, what counts as core logic (it may **propose** changes there, never just make them), the UI rules, and how to work. Detail lives in [`docs/`](docs/), read when needed.
- **Plan first for anything bigger than a small fix.** Larger steps (logins, deployment) were designed in plan mode and approved before any code was written. Decisions, and my reasons, are recorded with dates in [`docs/decisions.md`](docs/decisions.md).
- **Tests after every backend change.** They use small examples you can check by hand, with the working in comments. All must pass before a commit.
- **Check it in the browser.** UI changes were checked in the running app, not assumed to work.
- **Kitchen knowledge as the check.** Outputs were checked against what a pizzeria actually spends and sells.
- **Small commits,** one per logical step, made only when I asked.

## Running it locally

You'll need Python 3.13, Node 24 and an Anthropic API key.

```bash
# backend: http://localhost:8000 (API docs at /docs)
cd backend
python -m venv venv
venv\Scripts\activate                 # Windows; on macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
# backend/.env: ANTHROPIC_API_KEY=..., SECRET_KEY=<any long random text>, INVITE_CODE=<any phrase>
python seed_demo.py                   # builds the demo pizzeria (menu.db)
uvicorn main:app --reload
```

```bash
# frontend: http://localhost:5173
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and choose **Try the demo** (a private copy of the demo pizzeria), or create an account with your invite code. [`docs/demo.md`](docs/demo.md) is a five-minute walkthrough using the sample files in `backend/samples/`.

**Tests:** `cd backend` then `python -m pytest`.

**Deploying:** [`docs/deploy.md`](docs/deploy.md) (Render: a Docker image, with a persistent disk for account data).

## Project layout

- `backend/`
  - `main.py`: every route.
  - `costing.py`, `menu_engineering.py`: the core logic.
  - `*_ai.py`: Claude calls.
  - `invoices.py`, `menus.py`, `tills.py`: import review and saving.
  - `suggestions.py`: the business checks.
  - `report_agent.py`, `report_tools.py`: the AI report.
  - `auth.py`: accounts.
  - `migrate.py`: schema changes.
  - `tests/`.
- `frontend/src/`
  - `App.jsx`: the login gate and page choice.
  - `api.js`: every API call.
  - `index.css`: the design system.
  - `components/`: one file per page and piece.
- `docs/`: architecture, decisions, the demo script and deployment.

## Known limitations

- **VAT:** margins use VAT-inclusive menu prices; the trade usually reports gross profit ex-VAT. It's an open decision, because changing it changes the costing engine.
- **Starting values:** the business-check rules of thumb are sensible first figures, not researched benchmarks, and the benchmark ingredient prices are estimates. A restaurant's own invoices replace them.
- **Tested on tidy data:** menu import has been tested on clean menus, not yet on really messy ones.
- **One server:** it's built to run as a single server process (login limits and running reports live in memory), which suits a single-restaurant tool.
