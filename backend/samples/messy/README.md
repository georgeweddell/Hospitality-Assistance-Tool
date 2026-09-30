# Messy test data: The Tidewater (sample)

A made-up coastal bistro, run through Docket from a fresh start: two menus, 15 supplier
documents and seven sales files covering 21 May to 20 Sep 2026. Every business, person and
number is fictional. The data is messy on purpose, so it tests the imports the way a real
owner's paperwork would.

Regenerate (same files every time, fixed random seed), from `backend/`:

```powershell
.\venv\Scripts\python.exe samples\messy\make_messy_menus.py
.\venv\Scripts\python.exe samples\messy\make_messy_invoices.py
.\venv\Scripts\python.exe samples\messy\make_messy_sales.py
```

The photos (`.jpg`/`.png`) need Pillow (`pip install pillow`); without it they are skipped.

## Order to upload them (a fresh account, Start fresh)

1. **Menu:** `menus/menu-spring-2026.pdf`, start date **1 Jun 2026**.
2. **Invoices (June):** HFC-10233, IMG_4471.jpg, CN-0081, moorland-44120, GP-2026-0611, DD-7781, the WhatsApp receipt.
3. **Recipes:** Estimate all.
4. **Sales:** `popup-tally-may.csv`, `square-items-2026-05-28-to-06-30.csv`, `square-items-2026-07-01-to-07-15.csv`, then `square-items-2026-07.csv`, then `deliveroo-orders-2026-07.csv`.
5. **Invoices (July):** HFC-10388, HFC-10388-COPY, scan_0715.png, DD-7902, moorland-44377, moorland-statement.
6. **Menu:** `menus/menu-summer-2026.jpg`, start date **1 Aug 2026**.
7. **Invoices (August):** GP-2026-0802, HFC-10512, DD-8034.
8. **Sales:** `SumUp_Transactions_August_2026.csv`, then `sept-daily-items-EXCEL.csv`.

## What each file tests (the answer key)

### Menus

| File | The mess | What should happen |
|---|---|---|
| menu-spring-2026.pdf | Two pages, two columns; prices without £ ("9.5"); "17.5 / small 13"; "3 for 9 · 6 for 16"; "3 cheeses 11 / 5 cheeses 16"; Lemon Sole at **MP**; add-ons ("Peppercorn sauce +3", "Add bacon 2"); set lunch; drinks; kids' dishes called "Fish & Chips" and "Burger & Chips"; allergen codes | Sizes become separate dishes; add-ons, set lunch and drinks are "not a dish"; allergen codes left off names; MP has no price, so the owner must type one before Apply |
| menu-summer-2026.jpg | Phone photo. Haddock 17.5 crossed out, **18.5** in pen; Chicken Supreme crossed out with **"86"**; **Eton Mess** added in pen; Burger → "Tidewater Smash Burger" (17); Hake → "Cornish Hake" (23, new description); Burrata → "Burrata, Peach & Basil"; Risotto → "Summer Pea & Mint Risotto"; Pork Belly out, Korean Fried Cauliflower in; Crab Linguine new; **Lamb Rump gone**; price rises (Squid, Oysters, Chips, Tart, Roast) | Handwritten price used; Chicken treated as coming off (question for the owner); Eton Mess new; the renames offered as "Renamed?", never merged silently; Lamb and Pork Belly listed as coming off on 31 Jul |

### Invoices

| File | The mess | What should happen |
|---|---|---|
| harbour-fish-HFC-10233.pdf | Catch weights (6.0 kg @ £/kg); lemon sole **each**; oysters by the **dozen**; mussels "5kg bag"; shrimp "500g tub"; box deposit; £0 delivery | Kg lines priced per kg; dozen = 12 each; deposit and delivery ignored |
| IMG_4471.jpg | Phone photo, tilted. "White crab meat **1lb** tub"; handwritten "short 1kg - cr to follow" | 1 lb = 453.6 g; the handwritten notes aren't lines |
| harbour-fish-credit-CN-0081.pdf | **Credit note**, negative quantities | Should record no new prices |
| harbour-fish-HFC-10388.pdf | Haddock +14%, hake +8% | Prices dated 3 Jul; alerts later |
| harbour-fish-HFC-10388-COPY.pdf | Same invoice number again, "COPY" stamp | Blocked as already imported |
| harbour-fish-HFC-10512.pdf | Clean August invoice | Remembered matches pre-filled |
| moorland-44120.pdf | Dot-matrix capitals; "FLAT IRON STK **8OZ** PORTION" priced each; lamb/pork/sirloin **CW** (catch weight); "STREAKY BACON SLICED **5LB**" | 8 oz = 226.8 g and 5 lb = 2,268 g; each-priced chicken is 1 × 1 each |
| moorland-44377.pdf | **Two pages**, "Continued overleaf"; **two sirloin lines**; "CHIPOLATAS 10 PER LB" priced per LB; a £0 note line | Both pages read; the two sirloin lines combine into one price |
| moorland-statement-2026-07.pdf | A **statement**, not an invoice | Nothing to price |
| greenacre-GP-2026-0611.pdf | Sacks, **trays, boxes and bunches** with no weight; "box (80)" lemons; "11x200g"; a **substitution** note; samphire **"NOT AVAILABLE"** at qty 0; date "1 June 2026" | Weightless packs need the owner; the qty-0 line sets no price |
| scan_0715.png | Scanned, crooked, handwriting | Same as above, harder to read |
| greenacre-GP-2026-0802.pdf | **Two-digit year** (01/08/26) next to a delivered date; "5lb tray" strawberries; "punnet" | Invoice date, not delivery date; 5 lb = 2,268 g |
| dales-dairy-DD-7781.pdf | "40 x 250g" butter case; milk in **pints**; eggs "**15 dozen**" tray; Stilton CW | 10 kg butter; 4 pints = 2,273 ml; 180 eggs |
| dales-dairy-DD-7902.pdf | Delivered / invoice / due dates side by side; the **cream line's total is wrong** (4 × 7.20 printed as 21.60) | Invoice date 7 Jul; cream flagged "totals" |
| dales-dairy-DD-8034.pdf | Butter **+40%** | Flagged as a big change (it's real) |
| WhatsApp Image … .jpeg | A **till receipt**, prices **include VAT**, no invoice number, "2 @ 3.19", a promo line, drinks and cleaning | Receipt; VAT warning; each line is one pack at its price; non-food ignored |

### Sales

| File | The mess | What should happen |
|---|---|---|
| popup-tally-may.csv | Typed by hand: **one column per day**, a title line, "-", "approx 10", blanks | Can't be read as a till export; typed on the Sales page instead |
| square-items-2026-05-28-to-06-30.csv | Starts **4 days before the menu**; sizes in a separate **"Price Point Name"** column (Fish & Chips Regular/Small, Oysters x3/x6, Cheeseboard 3/5); **set lunches** with their dishes only in "Modifiers Applied"; the bar iPad's own names ("Burger", "Creme Brulee", "Fries" = Chips); **voids**; refunds; comps; staff meals; phone numbers in **Notes** | See the results below |
| square-items-2026-07-01-to-07-15.csv, then …-07.csv | A month-to-date export, then the whole month | The second replaces the first's days, no double count |
| deliveroo-orders-2026-07.csv | One row per order, **all dishes in one cell** ("1x Fish & Chips; 2x Chips"), **no quantity column**, cancelled and rejected orders | Can't be mapped |
| SumUp_Transactions_August_2026.csv | New till: **5 report lines above the header**, semicolons, Windows encoding (CRÈME BRÛLÉE), **decimal commas** ("1,00"), names **cut at 20 characters** in capitals, "Cancelled" and "Refunded" status, a **TOTAL row**, **one row dated 2027**, closed 10-16 Aug | See the results below |
| sept-daily-items-EXCEL.csv | Opened and saved in Excel: dates like 1/9/2026, a **"Total" row after every day**, blank rows, a "Grand Total" row | See the results below |

## Results (28 Sep 2026)

Three passes. First the till import code alone, with no AI. Then a paid run: every file in the
order above, from an empty database, through the same functions the upload routes call, with
real Claude reads. Then the fixes, and a second paid run from scratch. The owner's choices on the
review screens were made by the run script (confirm Claude's rename suggestions, type a price for
market price, set aside lines needing a pack typed in).

### What broke, and what happens now

| # | Problem found | Before | Now |
|---|---|---|---|
| 1 | Till "Fish & Chips" (adult) vs the kids' "Fish & Chips" | Exact name match to the kids' dish, no warning | Menu import names kids' dishes "Kids …"; the adult dish is matched by Claude's hint |
| 2 | Decimal commas ("1,00") | 100 units per row (25,100 haddock in August) | 1 unit (251) |
| 3 | Sizes in "Price Point Name" | Regular and Small merged | "Fish & Chips · Regular" / "· Small", matched to the two dishes |
| 4 | Voids and cancelled orders | Counted as sales | Left out and counted: 22 voids in June, 42 cancelled rows in August |
| 5 | Report lines above the header (SumUp) | File read as one column | Header found on line 6 |
| 6 | One row dated 2027 | Whole file refused ("check the date format") | That row left out ("Dated after today: 13" rows of one table) |
| 7 | "Total" / "Grand Total" rows | An item with 3,473 units | Left out ("Total lines") |
| 8 | Capital-letter names | No dish suggestions | Suggestions ignore case |
| 9 | Phone numbers in Notes, staff names | Sent to Claude in the sample rows | Blanked |
| 10 | Refund and void markers not in Claude's 5 sample rows | No refund column chosen: refunds counted as sales | Found by code in the whole file |
| 11 | lb, oz, pints, dozens | Pack left blank | 5 lb bacon, 8 oz steaks, 4-pint milk, 15 dozen eggs priced |
| 12 | Credit note | Would save £16.80/kg haddock as a price | Recognised; nothing priced |
| 13 | Statement | Confusing empty review | Recognised; nothing priced |
| 14 | "COPY INVOICE" with the supplier read differently | Imported twice | Refused as already imported |
| 15 | Two sirloin joints on one invoice | Apply refused | Combined: paid ÷ weight |
| 16 | "NOT AVAILABLE" at quantity 0 | Would save a price | Ignored, not remembered as ignored |
| 17 | Till receipt: one price per line | No unit price, every line needed typing | One pack at that price |
| 18 | Handwritten note on the scan | Read as a line, replacing the garlic line | Ignored |
| 19 | Diet codes in dish names ("Chips (vg)") | Till "Chips" didn't match exactly | Names without codes |
| 20 | "86" and a line through Chicken Supreme | Kept on the menu | Taken off from 1 Aug |

**Checked against the simulated trade:** units saved per dish per month match what the generator
sold, less refunds (netted) and cancelled tables (left out). July and September match exactly.

**Worked from the start:** month-to-date then full month (the full July export replaced the 327
dish-days from the month-to-date one), catch weights, the wrong total on DD-7902 (flagged), butter
+40% (flagged as a big change), the handwritten 18.5 on the summer menu, renames offered as
questions (Hake, Burger, Risotto), Pork Belly and Lamb coming off, Windows encoding (CRÈME BRÛLÉE).

### Still needs the owner (by design)

- Packs with no weight or count: trays, boxes, bunches, punnets (tomatoes, mixed leaf, herbs, pea shoots).
- Lemon Sole at MP: type a price.
- Till items not on the menu: "SPECIAL - Crab Linguine" (a special before it joined the menu), "Fries" on the bar iPad.
- A rename Claude doesn't flag: "Burrata, Peach & Basil" was offered as a new dish once and as a rename once.

### Known limits (parked)

- **Set-menu dishes** are only in the modifiers column, so the dishes inside a set lunch aren't counted.
- **Delivery platforms** (Deliveroo) put a whole order in one cell with no quantity column: can't be read.
- **The hand tally** (one column per day) can't be read: type the totals on the Sales page.
- **Items priced each** (8 oz steaks, whole lemon sole, crab tubs) can't cost a recipe written in grams.
- **VAT-inclusive receipts**: shown with a warning, prices not converted (the food lines here are zero-rated anyway).
- **Claude isn't fully consistent** run to run (a rename flagged once, not the next time); every
  reading still goes through the review screen.
