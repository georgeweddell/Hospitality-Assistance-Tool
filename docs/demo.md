# Docket: the 5-minute demo

Start from Settings → **Start fresh** (it backs up the database first; Load demo data restores the demo afterwards). Sample files are in `backend/samples/`.

1. **Menu:** the Setup page opens. Upload `sample-menu.pdf` (about 25 s). Set **Starts on** to 1 June 2026 so September's sales count. 22 dishes are found; drinks, add-ons and the lunch deal are ignored. Apply.
2. **Recipes:** "Recipe 1 of 22: Arancini". Press Estimate with AI, check the draft (it used the menu description), Save. The next dish opens with its draft already prepared. Do two or three, then go on (the rest stay "needs recipe").
3. **Your prices:** upload `sample-invoice.pdf`. Point out the pack maths (12 × 1 kg → £/kg), the ricotta "Totals don't add up" flag, guanciale as a new ingredient, and blue roll/delivery ignored. Apply.
4. **Sales:** upload `sample-sales.csv`. Claude maps the columns from 5 rows (customer columns blanked) and matches renamed till items ("Garlic Bread" → Garlic Pizza Bread); drinks are ignored. Set "Refunds marked in" to Event Type / Refund. Apply.
5. **Results:** See your results → the Overview for September: quadrants, ranked actions with £ impact, and the Continue setup card while recipes remain.

6. **Report:** Overview → Generate report. The trail shows what Claude looks at (headline figures, ranked changes, sales patterns, ingredient prices, gaps, then a few dishes), about a minute; then next steps and findings, each with its numbers as chips. Point out that the numbers come from code, not Claude.

Talking points: every AI step ends in an editable review; code does all arithmetic; uploads reconcile rather than insert (re-upload the same file to show "Already imported"); undo on invoices and sales.
