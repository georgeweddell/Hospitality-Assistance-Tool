# Menu & Margin Engine

A full-stack web application that turns a restaurant's menu into a costed, ranked set of actions — built as a portfolio project for Solutions Engineer / Implementation Engineer / Forward Deployed Engineer roles, and inspired by hands-on experience line-cooking at a Neapolitan pizzeria.

## What it does

1. **Add a menu** — dish name, menu price, category (starter / side / main / dessert).
2. **AI-estimated recipes** — Claude (Anthropic API) proposes ingredients and quantities for a dish from its name alone, grounded against the business's real ingredient stock list so it proposes ingredients the kitchen actually has.
3. **Human-in-the-loop confirmation** — the AI's draft is matched against the ingredient table (exact match, then fuzzy suggestions), and the operator reviews and confirms before anything is saved. The AI proposes; the human verifies.
4. **Costing** — each confirmed recipe is costed against an editable ingredient price table (seeded with realistic UK wholesale prices), producing plate cost, gross margin (£), and gross margin (% of menu price) per dish.
5. **Sales mix** — units sold per dish, per period.
6. **Menu engineering** — each dish is classified into one of four quadrants based on popularity (menu-mix %) and profitability (contribution margin), calculated per category:
   - **Star** — popular and profitable → protect and feature.
   - **Plowhorse** — popular, under-earning → reprice or re-engineer.
   - **Puzzle** — profitable, overlooked → promote and reposition.
   - **Dog** — neither → cut or rework.
7. **Ranked action list** — every non-Star dish gets a recommended action with an estimated £ impact, ranked highest-impact first.

## Why this design

- **AI handles the hard-to-scale part (recipe estimation); humans verify it.** The ingredient table doesn't need to anticipate every dish in advance — the AI bridges an arbitrary dish name to the ingredient set, and the operator corrects the draft using real kitchen knowledge before it's trusted.
- **Prompt grounding, not post-hoc matching.** Early versions let the AI freely name ingredients and tried to reconcile that against the stock list afterward with fuzzy string matching — which silently dropped ingredients whose AI-generated name didn't closely match the table (e.g. "wheat flour" vs. "00 flour"), producing badly wrong margins. The fix: the ingredient table is fetched fresh on every estimate and included in the prompt itself, so the model is asked to use the business's actual vocabulary from the start.
- **Unit normalisation at data-entry time.** All quantities are stored in a fixed base unit (gram / ml / each), so the costing engine never has to convert units — it just multiplies. This eliminates an entire class of silent unit-mismatch bugs from the costing logic itself (though see *Known limitations* below).
- **Classification is category-relative.** A dessert and a main don't compete for the same share of covers, so popularity and profitability thresholds are calculated within each menu category, not across the whole menu.
- **Margin vs. markup.** Gross margin is expressed as a percentage of *menu price*, not of cost — the industry-standard definition, and an easy distinction to get wrong.

## Stack

- **Backend:** FastAPI (Python), SQLAlchemy ORM, Pydantic v2, SQLite
- **Frontend:** React (Vite) — *in progress*
- **AI:** Anthropic API (`claude.messages.parse()` with structured output)
- **Matching:** `difflib` for fuzzy ingredient matching (fallback for anything outside the AI's grounded suggestions)

## Project status

| Phase | Description | Status |
|---|---|---|
| 0 | Frontend/backend skeleton, CORS | ✅ Complete |
| 1 | Data models, ingredient seed table, CRUD | ✅ Complete |
| 2 | Costing engine (plate cost, margin £/%) | ✅ Complete |
| 3 | AI recipe estimation, ingredient matching | ✅ Complete |
| 4 | Sales mix, menu engineering classification, ranked action list | ✅ Complete |
| 5 | React dashboard (scatter plot, dish cards, action list UI) | 🔜 Next |
| 6 | Auth (JWT, per-user data isolation) | Planned |

## Getting started

**Backend**
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
# create a .env file with ANTHROPIC_API_KEY=your_key_here
python seed_demo.py          # build a realistic demo database (backs up any existing one)
uvicorn main:app --reload    # runs on http://localhost:8000
```

**Frontend**
```bash
cd frontend
npm install
npm run dev                  # runs on http://localhost:5173
```

API docs (Swagger UI) available at `http://localhost:8000/docs` once the backend is running.

## Key API routes

| Method | Route | Description |
|---|---|---|
| `GET` / `POST` | `/ingredients` | List / create ingredients |
| `GET` / `POST` | `/dishes` | List / create dishes |
| `GET` | `/dishes/{id}/cost` | Plate cost and margin for a dish |
| `POST` | `/dishes/{id}/estimate-recipe` | AI-proposed recipe draft (not saved) |
| `POST` | `/dishes/{id}/recipe` | Save a confirmed recipe |
| `GET` / `POST` | `/dishes/{id}/sales` | List / record sales for a dish |
| `GET` | `/dishes/classifications` | Star/Plowhorse/Puzzle/Dog for every dish |
| `GET` | `/dishes/action-list` | Ranked actions with £ impact |

## Known limitations

- **No unit-mismatch check between AI-proposed and matched ingredients.** If the AI proposes a gram quantity that matches an ingredient priced per-item (or vice versa), the cost calculation will be wrong without any error being raised. Caught once during development (bread priced per loaf, consumed by the gram); not yet guarded against systematically. Planned for Phase 5/6, alongside surfacing it as a confirmation warning in the UI.
- **Auth is stubbed, not implemented.** All data currently belongs to a single seeded dev user; per-user isolation is a Phase 6 goal.
- **Ingredient prices are estimates**, not verified against current wholesale pricing.

## Roadmap (out of scope for v1)

- Review intelligence — clustering public reviews into operational themes.
- Demand & rota forecasting from weather/events/seasonality.
- LLM-generated narrative summaries of the action list.
