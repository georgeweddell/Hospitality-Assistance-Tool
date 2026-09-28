---
name: demo-check
description: Check the 5-minute demo (docs/demo.md) still works end to end in the in-app browser. `quick` (default) is free and makes no AI calls; `full` walks the whole demo script with real Claude calls.
argument-hint: "[quick | full]"
disable-model-invocation: true
---

# /demo-check: is the 5-minute demo ready?

Run the demo the way George will show it, in the built-in browser, and report what's broken or off-script. **This is a check, not a fix:** change no code. List problems and wait for George.

Mode: `$ARGUMENTS` (empty means `quick`).
- **quick**: free. Try the demo, then every page of the demo pizzeria renders with sensible figures. No Claude calls.
- **full**: George asked for paid Claude calls by typing `full` (about 8 calls and one report). It runs `docs/demo.md` steps 1–6 in a fresh **Try the demo guest account**, never an owner account.

## Setup (both modes)

1. Build the app: `npm --prefix frontend run build`. The backend serves `frontend/dist` at http://localhost:8000, the same way as the live site. If the build fails, stop and report the error.
2. `preview_start` with name `backend` (from `.claude/launch.json`). It takes a few seconds to start: poll `curl -s http://127.0.0.1:8000/health` until it answers `{"ok":true}`.
3. Navigate the tab to **http://127.0.0.1:8000/** (not `localhost`: the browser may hold George's own login cookie for `localhost`, and this check must never use his account). The login page shows; press **Try the demo**. This makes a guest: a private copy of the demo pizzeria (June–August 2026), deleted after 7 days, with a small AI allowance. **Check the header shows the "guest · N AI left" chip before going on.** If it doesn't, stop.

Read pages with `get_page_text` / `read_page` (use `max_chars` of about 800 to keep context small; batch several pages in one `browser_batch`). Take screenshots only for a layout problem. At the end, check `read_console_messages` (errors only) and `read_network_requests` for 4xx/5xx responses. The one 401 on `/auth/me` before Try the demo is expected.

## Quick mode

Visit each page (hash routes), set the range to **August 2026** where there is a date picker, and check:

| Page | Expect |
|---|---|
| `#/overview` | Sales, margin and quadrant tiles filled; Star / Plowhorse / Puzzle / Dog all populated; no setup checklist |
| `#/actions` | Ranked list, each action with a £ figure (a change in contribution) |
| `#/menu` | Dishes with price, plate cost, margin; open one dish: recipe lines and price history |
| `#/ingredients` | Prices with a source and date on each |
| `#/sales` | Daily chart for August, totals by category and dish |
| `#/analysis` | Quadrant chart renders |
| `#/reports/suggestions` | Business checks listed, each with a target figure |
| `#/imports`, `#/settings` | Load without errors; Settings shows Start fresh and Load demo data |

Also check that the three sample files exist in `backend/samples/`: `sample-menu.pdf`, `sample-invoice.pdf`, `sample-sales.csv`.

## Full mode

Follow `docs/demo.md` and read it first; it's the source of truth. Check each point below as you go.

**Uploads:** the in-app browser can't use a file picker. Copy the samples into the served folder: `mkdir -p frontend/dist/demo-samples && cp backend/samples/sample-* frontend/dist/demo-samples/`. Then, on the page with the upload button, run with `javascript_tool`:

```js
const name = 'sample-menu.pdf'                                // the file for this step
const blob = await fetch('/demo-samples/' + name).then(r => r.blob())
const input = document.querySelector('input[type=file]')      // if several, pick the one in the open step's tile
const dt = new DataTransfer(); dt.items.add(new File([blob], name, { type: blob.type }))
input.files = dt.files
input.dispatchEvent(new Event('change', { bubbles: true }))
```

AI steps take 20–60 s. Wait with `computer` `wait`, then read the page again. Don't upload twice.

| Step | Check |
|---|---|
| 0. Settings → Start fresh | Only with the guest chip showing (Settings → account says "Demo account"). Confirm dialog, then the Setup page opens |
| 1. Menu (`sample-menu.pdf`) | Set Starts on to 1 June 2026. **22 dishes** found; drinks, add-ons, lunch deal ignored. Apply |
| 2. Recipes | "Recipe 1 of 22: Arancini"; Estimate with AI gives an editable draft that uses the menu description; Save; the next dish opens with a draft ready. Do 2–3, then move on |
| 3. Your prices (`sample-invoice.pdf`) | Pack maths (12 × 1 kg → £/kg); ricotta "Totals don't add up" flag; guanciale as new; blue roll and delivery ignored. Apply |
| 4. Sales (`sample-sales.csv`) | Columns mapped; "Garlic Bread" → Garlic Pizza Bread; drinks ignored; set Refunds marked in = Event Type / Refund. Apply |
| 5. Results | September Overview: quadrants, ranked actions with £, Continue setup card (recipes remain) |
| 6. Report | Generate report: the trail of what Claude looks at, then next steps and findings with number chips (about a minute) |
| Talking points | Re-upload `sample-invoice.pdf` shows "Already imported"; do this **before** any undo. Undo exists on the invoice and sales imports |

A guest past its allowance gets a 429; report it rather than switching accounts.

**Clean up:** `rm -rf frontend/dist/demo-samples`. Leave the guest; it expires by itself.

## Report

Keep it short and in plain English. Start with one line: **demo ready** or **N problems**. Then:
- Each problem: the step, what the script expects, what happened (quote the page text or error), and the likely file if obvious.
- Anything slow (over 60 s for an AI step, over 3 s for a page).
- Anything on screen that breaks the CLAUDE.md frontend rules (explanatory sentences, AI-sounding asides, glyphs on buttons).

Stop the backend with `preview_stop` when done.
