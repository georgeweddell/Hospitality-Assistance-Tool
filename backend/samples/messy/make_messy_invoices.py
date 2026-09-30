"""
Writes samples/messy/invoices/: 15 made-up supplier documents for "The
Tidewater (sample)", a fictional coastal bistro, June-August 2026. Every
supplier is fictional. What each file tests is listed in samples/messy/README.md.

The mess, on purpose:
- catch-weight lines (4.37 kg @ £/kg), dozens, bunches, trays, boxes, sacks,
  pounds, ounces and pints; lines with no weight at all;
- a credit note, a "COPY INVOICE" of one already sent, a statement of account
  (not an invoice) and a cash-and-carry till receipt priced with VAT;
- phone photos (tilted, shadowed, grainy) with handwritten notes;
- a line whose total doesn't add up, substitutions and "not available" lines,
  a two-page invoice, a two-digit year, and delivery/due dates beside the
  invoice date;
- real price rises (butter +40%) that should be flagged.

Photos need Pillow; without it they're skipped (the PDFs still get written).
Run from backend/:
    .\\venv\\Scripts\\python.exe samples\\messy\\make_messy_invoices.py
"""

from pathlib import Path

from render import pdf_bytes, photo_bytes

OUT = Path(__file__).parent / "invoices"
CUSTOMER = ["The Tidewater (sample)", "2 Quay Street, Porthsample", "Cornwall TR0 0AA"]


def L(code, desc, qty, unit, price, vat=0, total=None, note=None):
    """One invoice line. The total is qty x price unless a (deliberately wrong) one is given."""
    return {"code": code, "desc": desc, "qty": qty, "unit": unit, "price": price, "vat": vat,
            "total": round(qty * price, 2) if total is None else total, "note": note}


def money(value, sign="£"):
    text = f"{sign}{abs(value):,.2f}"
    return f"-{text}" if value < 0 else text


def qty_text(q):
    return f"{q:g}" if q == int(q) else f"{q:.2f}"


# --- Suppliers -----------------------------------------------------------------------------

FISH = {"name": "Harbour Fish Co (sample)", "font": "sans",
        "address": ["The Fish Quay, Porthsample TR0 1FQ", "Tel 01000 000000 · VAT GB 000 0001 00 (sample)"]}
MEAT = {"name": "MOORLAND MEATS LTD (SAMPLE)", "font": "mono",
        "address": ["FAMILY BUTCHERS SINCE 1962", "UNIT 7 MOOR LANE IND EST, SAMPLETON SA1 7MM",
                    "VAT NO GB 000 0002 00 (SAMPLE)"]}
VEG = {"name": "Greenacre Produce (sample)", "font": "serif",
       "address": ["Wholesale fruit & vegetables", "Market Hall, Sampleford SF2 3GP"]}
DAIRY = {"name": "Dales Dairy (sample)", "font": "sans",
         "address": ["Dairy & cheese to the trade", "Dale Farm, Sampledale SD4 5DD", "VAT GB 000 0003 00 (sample)"]}


def invoice_pages(supplier, title, number, date_fields, lines, notes=(), hand=(), per_page=40,
                  stamp=None, account="TIDE01"):
    """Drawing steps for an invoice or credit note (one or more A4 pages)."""
    font = supplier["font"]
    bold = f"{font}-bold"
    chunks = [lines[i:i + per_page] for i in range(0, len(lines), per_page)] or [[]]
    pages = []
    for page_no, chunk in enumerate(chunks, start=1):
        s = []
        s.append(("text", 50, 790, supplier["name"], bold, 16, "left"))
        for i, line in enumerate(supplier["address"]):
            s.append(("text", 50, 774 - i * 11, line, font, 8, "left"))
        s.append(("text", 545, 790, title, bold, 18, "right"))
        y = 770
        for label, value in [("Number", number)] + list(date_fields) + [("Account", account)]:
            s.append(("text", 440, y, f"{label}:", font, 8, "right"))
            s.append(("text", 545, y, value, bold, 8, "right"))
            y -= 11
        s.append(("text", 50, 712, "INVOICE TO:" if title != "CREDIT NOTE" else "CREDIT TO:", bold, 8, "left"))
        for i, line in enumerate(CUSTOMER):
            s.append(("text", 50, 700 - i * 11, line, font, 9, "left"))
        if len(chunks) > 1:
            s.append(("text", 545, 700, f"Page {page_no} of {len(chunks)}", font, 8, "right"))

        # Column headings, then the lines.
        y = 650
        s.append(("box", 48, y - 4, 499, 14, 0.88))
        for x, heading, align in [(52, "Code", "left"), (100, "Description", "left"), (350, "Qty", "right"),
                                  (358, "Unit", "left"), (440, "Price", "right"), (495, "Net", "right"),
                                  (542, "VAT", "right")]:
            s.append(("text", x, y, heading, bold, 8, align))
        y -= 18
        for line in chunk:
            s.append(("text", 52, y, line["code"], font, 8, "left"))
            s.append(("text", 100, y, line["desc"], font, 8, "left"))
            s.append(("text", 350, y, qty_text(line["qty"]), font, 8, "right"))
            s.append(("text", 358, y, line["unit"], font, 8, "left"))
            s.append(("text", 440, y, f"{line['price']:.2f}", font, 8, "right"))
            s.append(("text", 495, y, f"{line['total']:.2f}", font, 8, "right"))
            s.append(("text", 542, y, f"{line['vat']}%" if line["vat"] else "Z", font, 8, "right"))
            if line["note"]:
                y -= 10
                s.append(("text", 100, y, line["note"], font, 7, "left"))
            y -= 14
        s.append(("line", 48, y + 6, 547, y + 6, 0.5))

        if page_no < len(chunks):
            s.append(("text", 545, y - 10, "Continued overleaf...", font, 8, "right"))
        else:
            net = round(sum(l["total"] for l in lines), 2)
            vat = round(sum(l["total"] * l["vat"] / 100 for l in lines), 2)
            for label, value in [("Net", net), ("VAT", vat), ("TOTAL", round(net + vat, 2))]:
                y -= 14
                s.append(("text", 470, y, label, bold, 9, "right"))
                s.append(("text", 545, y, money(value), bold, 9, "right"))
            y -= 24
            for note in notes:
                s.append(("text", 50, y, note, font, 7, "left"))
                y -= 10
        if stamp:
            s.append(("text", 300, 420, stamp, bold, 40, "centre"))
        s.append(("text", 50, 40, "Made-up sample document for testing Docket. Not a real business.", font, 6, "left"))
        pages.append(s)
    for page_index, x, y, text, size in hand:
        pages[page_index].append(("hand", x, y, text, size))
    return pages


def receipt_steps():
    """A cash-and-carry till receipt: prices include VAT, no invoice number, narrow thermal paper."""
    s, x0, x1 = [], 150, 440
    y = 800

    def row(left, right="", bold=False, size=8):
        nonlocal y
        f = "mono-bold" if bold else "mono"
        s.append(("text", x0, y, left, f, size, "left"))
        if right:
            s.append(("text", x1, y, right, f, size, "right"))
        y -= 12

    s.append(("box", 140, 90, 310, 730, 1.0))
    row("   BAYSIDE CASH & CARRY (SAMPLE)", bold=True, size=9)
    row("   Harbour Road, Sampleport")
    row("   VAT No: GB 000 0004 00 (SAMPLE)")
    y -= 6
    row("22/06/26  14:37   TILL 03   OP 112")
    row("RECEIPT 0045        CUST CARD 55120")
    row("-" * 48)
    for desc, price, code in [
        ("PLAIN FLOUR 16KG", "14.99", "Z"), ("RAPESEED OIL 20LTR", "32.49", "Z"),
        ("EXTRA V OLIVE OIL 5LTR TIN", "38.99", "Z"), ("CASTER SUGAR 5KG", "6.49", "Z"),
        ("DARK CHOC 70% CALLETS 2.5KG", "27.99", "Z"), ("TRUFFLE OIL 250ML", "11.49", "Z"),
        ("PANKO BREADCRUMBS 1KG", "4.29", "Z"),
    ]:
        row(f"{desc}", f"{price} {code}")
    row("SOY SAUCE 1LTR")
    row("   2 @ 3.19", "6.38 Z")
    for desc, price in [
        ("COCA COLA 24X330ML", "17.99 S"), ("BLUE ROLL 2PLY 6PK", "13.99 S"), ("REFUSE SACKS 200", "9.99 S"),
    ]:
        row(desc, price)
    row("  PROMO SAVING COCA COLA", "-3.00 S")
    row("-" * 48)
    row("BALANCE DUE", "£182.08", bold=True)
    row("CARD                    ************0000", "£182.08")
    y -= 6
    row("VAT  RATE     NET       VAT")
    row("S    20%     32.47      6.50")
    row("Z     0%    143.11      0.00")
    y -= 6
    row("ITEMS 13       THANK YOU FOR SHOPPING")
    row("MADE-UP SAMPLE RECEIPT - NOT A REAL BUSINESS", size=6)
    s.append(("hand", 160, y - 20, "Tidewater - dry store", 12))
    return s


def statement_pages():
    """A statement of account: it lists invoices and a balance, but has no lines to price."""
    s = []
    f, b = "mono", "mono-bold"
    s.append(("text", 50, 790, MEAT["name"], b, 16, "left"))
    for i, line in enumerate(MEAT["address"]):
        s.append(("text", 50, 774 - i * 11, line, f, 8, "left"))
    s.append(("text", 545, 790, "STATEMENT", b, 18, "right"))
    s.append(("text", 545, 770, "DATE: 31/07/2026   ACCOUNT: TIDE01", b, 8, "right"))
    for i, line in enumerate(CUSTOMER):
        s.append(("text", 50, 700 - i * 11, line, f, 9, "left"))
    y = 640
    s.append(("text", 50, y, "DATE        REF        DETAIL              DEBIT      CREDIT    BALANCE", b, 8, "left"))
    y -= 16
    rows = [("01/06/2026", "", "BALANCE B/FWD", "", "", "0.00"),
            ("02/06/2026", "44120", "INVOICE", "456.98", "", "456.98"),
            ("30/06/2026", "", "PAYMENT - THANK YOU", "", "456.98", "0.00"),
            ("30/07/2026", "44377", "INVOICE", "660.51", "", "660.51")]
    for r in rows:
        s.append(("text", 50, y, f"{r[0]:<12}{r[1]:<11}{r[2]:<20}{r[3]:>7}   {r[4]:>9}  {r[5]:>9}", f, 8, "left"))
        y -= 13
    y -= 10
    s.append(("text", 50, y, "CURRENT   30 DAYS   60 DAYS   90+ DAYS      AMOUNT DUE", b, 8, "left"))
    s.append(("text", 50, y - 13, " 660.51      0.00      0.00       0.00    £660.51", f, 8, "left"))
    s.append(("text", 50, y - 40, "PLEASE REMIT TO: SAMPLE BANK  SORT 00-00-00  ACC 00000000", f, 8, "left"))
    s.append(("text", 50, 40, "Made-up sample document for testing Docket. Not a real business.", f, 6, "left"))
    return [s]


# --- The documents -------------------------------------------------------------------------

def documents():
    """(filename, pages or a single page of steps, "pdf" | "jpg" | "png", photo tilt)."""
    docs = []

    # Harbour Fish: catch weights, fish sold whole (each), dozens, a pound, deposits.
    fish1 = [
        L("HAD01", "Haddock fillet skin on, pin boned", 6.0, "kg", 16.80),
        L("HAK02", "Hake fillet", 3.2, "kg", 18.50),
        L("SQU05", "Squid tubes cleaned U/5", 2.0, "kg", 11.40),
        L("MUS05", "Mussels rope grown 5kg bag", 1, "bag", 12.50),
        L("LSO01", "Lemon sole whole 400-500g", 6, "each", 9.50),
        L("OYS03", "Rock oysters No.3", 4, "doz", 10.80),
        L("SHR05", "Brown shrimp peeled 500g tub", 2, "tub", 14.20),
        L("SAM01", "Samphire", 1.0, "kg", 12.00),
        L("MAC15", "Smoked mackerel fillets", 1.5, "kg", 13.60),
        L("BOX", "Polybox deposit", 3, "each", 3.00, vat=20),
        L("DEL", "Delivery - FREE over £150", 1, "", 0.00),
    ]
    docs.append(("harbour-fish-HFC-10233.pdf",
                 invoice_pages(FISH, "INVOICE", "HFC-10233", [("Date", "05/06/2026")], fish1,
                               notes=["Payment 14 days. Boxes remain our property."]), "pdf", 0))

    fish2 = [
        L("HAD01", "Haddock fillet skin on, pin boned", 8.0, "kg", 16.80),
        L("HAK02", "Hake fillet", 2.85, "kg", 18.50),
        L("SQU05", "Squid tubes cleaned U/5", 2.0, "kg", 11.40),
        L("MUS05", "Mussels rope grown 5kg bag", 1, "bag", 12.50),
        L("CRB01", "White crab meat 1lb tub", 2, "tub", 21.50),
        L("OYS03", "Rock oysters No.3", 3, "doz", 10.80),
        L("LSO01", "Lemon sole whole 400-500g", 4, "each", 9.80),
        L("SAM01", "Samphire", 1.0, "kg", 12.00),
    ]
    docs.append(("IMG_4471.jpg",
                 invoice_pages(FISH, "INVOICE", "HFC-10301", [("Date", "19/06/2026")], fish2,
                               hand=[(0, 360, 640, "short 1kg - cr to follow", 11),
                                     (0, 360, 570, "for crab special", 10)])[0], "jpg", 3.5))

    credit = [
        L("HAD01", "Haddock fillet - short delivery inv HFC-10301", -1.0, "kg", 16.80),
        L("BOX", "Polybox deposit returned", -3, "each", 3.00, vat=20),
    ]
    docs.append(("harbour-fish-credit-CN-0081.pdf",
                 invoice_pages(FISH, "CREDIT NOTE", "CN-0081",
                               [("Date", "26/06/2026"), ("Against", "HFC-10301")], credit), "pdf", 0))

    fish3 = [
        L("HAD01", "Haddock fillet skin on, pin boned", 7.0, "kg", 19.20),
        L("HAK02", "Hake fillet", 3.1, "kg", 19.90),
        L("SQU05", "Squid tubes cleaned U/5", 2.0, "kg", 12.10),
        L("MUS05", "Mussels rope grown 5kg bag", 1, "bag", 12.50),
        L("CRB02", "White crab meat 454g tub", 2, "tub", 21.50),
        L("OYS03", "Rock oysters No.3", 4, "doz", 11.40),
        L("LSO01", "Lemon sole whole 400-500g", 5, "each", 9.80),
        L("MAC15", "Smoked mackerel fillets", 1.5, "kg", 13.60),
        L("SAM01", "Samphire", 1.0, "kg", 12.50),
    ]
    docs.append(("harbour-fish-HFC-10388.pdf",
                 invoice_pages(FISH, "INVOICE", "HFC-10388", [("Date", "03/07/2026")], fish3,
                               notes=["Haddock and hake up this week - landings down after the storms."]), "pdf", 0))
    docs.append(("harbour-fish-HFC-10388-COPY.pdf",
                 invoice_pages(FISH, "COPY INVOICE", "HFC-10388",
                               [("Date", "03/07/2026"), ("Printed", "10/07/2026")], fish3,
                               stamp="COPY"), "pdf", 0))

    fish4 = [
        L("HAD01", "Haddock fillet skin on, pin boned", 9.0, "kg", 19.20),
        L("HAK02", "Hake fillet", 4.25, "kg", 20.40),
        L("SQU05", "Squid tubes cleaned U/5", 3.0, "kg", 12.10),
        L("CRB02", "White crab meat 454g tub", 3, "tub", 22.00),
        L("SHR05", "Brown shrimp peeled 500g tub", 3, "tub", 14.60),
        L("OYS03", "Rock oysters No.3", 5, "doz", 11.40),
        L("LSO01", "Lemon sole whole 400-500g", 4, "each", 10.20),
        L("MAC15", "Smoked mackerel fillets", 1.5, "kg", 13.90),
        L("BOX", "Polybox deposit", 4, "each", 3.00, vat=20),
    ]
    docs.append(("harbour-fish-HFC-10512.pdf",
                 invoice_pages(FISH, "INVOICE", "HFC-10512", [("Date", "07/08/2026")], fish4), "pdf", 0))

    # Moorland Meats: dot-matrix style, ounces, catch weights, a two-page invoice, a statement.
    meat1 = [
        L("FI08", "FLAT IRON STK 8OZ PORTION", 20, "EA", 5.40),
        L("LR01", "LAMB RUMP (AVG 220G) CW", 1.38, "KG", 21.50),
        L("PB02", "PORK BELLY B/LESS CW", 3.45, "KG", 8.90),
        L("CS24", "CHICKEN SUPREME 200-220G", 24, "EA", 2.35),
        L("BM20", "BEEF MINCE 20% VL", 5, "KG", 8.20),
        L("SB05", "STREAKY BACON SLICED 5LB", 1, "PK", 17.95),
        L("BP06", "BURGER PATTY 6OZ HANDMADE", 40, "EA", 1.65),
        L("SJ01", "SIRLOIN JOINT (ROAST) CW", 4.10, "KG", 24.50),
        L("BD02", "BEEF DRIPPING 2KG", 1, "TUB", 6.80),
    ]
    docs.append(("moorland-44120.pdf",
                 invoice_pages(MEAT, "INVOICE", "44120", [("DATE", "02/06/2026"), ("DEL", "02/06/2026")], meat1,
                               notes=["CW = CATCH WEIGHT, PRICED PER KG AS WEIGHED."]), "pdf", 0))

    meat2 = [
        L("FI08", "FLAT IRON STK 8OZ PORTION", 24, "EA", 5.60),
        L("LR01", "LAMB RUMP (AVG 220G) CW", 1.52, "KG", 23.80),
        L("CS24", "CHICKEN SUPREME 200-220G", 24, "EA", 2.49),
        L("BM20", "BEEF MINCE 20% VL", 5, "KG", 8.60),
        L("SB05", "STREAKY BACON SLICED 5LB", 1, "PK", 18.40),
        L("BP06", "BURGER PATTY 6OZ HANDMADE", 60, "EA", 1.79),
        L("SJ01", "SIRLOIN JOINT (ROAST) CW", 4.35, "KG", 25.90),
        L("SJ01", "SIRLOIN JOINT (ROAST) CW", 3.90, "KG", 25.90),
        L("BD02", "BEEF DRIPPING 2KG", 1, "TUB", 6.80),
        L("CH10", "CHIPOLATAS 10 PER LB", 2, "LB", 4.20),
        L("CK01", "CHICKEN THIGH B/LESS 5KG", 1, "CS", 32.50),
        L("VEN", "PS - PRICE INCREASE FROM 01/08 SEE LETTER", 0, "", 0.00),
    ]
    docs.append(("moorland-44377.pdf",
                 invoice_pages(MEAT, "INVOICE", "44377", [("DATE", "30/07/2026"), ("DEL", "30/07/2026")], meat2,
                               per_page=7), "pdf", 0))
    docs.append(("moorland-statement-2026-07.pdf", statement_pages(), "pdf", 0))

    # Greenacre Produce: boxes, bunches, trays, subs, not-available lines, a scan, a 2-digit year.
    veg1 = [
        L("POT25", "Potatoes Maris Piper", 2, "25kg sack", 14.50),
        L("TOMH", "Heritage tomatoes", 2, "tray", 11.00),
        L("WGAR", "Wild garlic", 10, "bunch", 0.85),
        L("LEM80", "Lemons", 1, "box (80)", 18.00),
        L("LEE5", "Leeks", 1, "5kg", 7.50),
        L("PEAF", "Garden peas frozen", 2, "2.5kg", 5.60),
        L("TEN11", "Tenderstem broccoli", 1, "11x200g", 19.80),
        L("MUSW", "Wild mushroom mix", 2, "1kg punnet", 16.50),
        L("LEAF", "Mixed leaf", 2, "box", 6.20),
        L("PARS", "Flat leaf parsley", 6, "bunch", 0.75),
        L("CARB", "Carrots bunched", 1, "2.5kg", 4.80, note="** SUB ** Chantenay carrots supplied"),
        L("SAMP", "Samphire", 0, "kg", 12.00, note="NOT AVAILABLE"),
        L("SHAL", "Shallots banana", 1, "5kg", 9.20),
        L("GARL", "Garlic", 1, "1kg", 5.40),
        L("ONIB", "Onions brown", 1, "10kg", 8.00),
    ]
    docs.append(("greenacre-GP-2026-0611.pdf",
                 invoice_pages(VEG, "INVOICE", "GP/2026/0611", [("Date", "1 June 2026")], veg1), "pdf", 0))

    veg2 = [
        L("POT25", "Potatoes Maris Piper", 2, "25kg sack", 15.20),
        L("TOMH", "Heritage tomatoes", 3, "tray", 12.50),
        L("MINT", "Mint", 8, "bunch", 0.80),
        L("PEAF", "Garden peas frozen", 3, "2.5kg", 5.60),
        L("CAUL", "Cauliflower", 12, "each", 1.05),
        L("LEM80", "Lemons", 1, "box (80)", 18.50),
        L("TEN11", "Tenderstem broccoli", 1, "11x200g", 19.80),
        L("LEAF", "Mixed leaf", 3, "box", 6.20),
        L("PARS", "Flat leaf parsley", 6, "bunch", 0.75),
        L("GARL", "Garlic", 1, "1kg", 5.40),
    ]
    docs.append(("scan_0715.png",
                 invoice_pages(VEG, "INVOICE", "GP/2026/0719", [("Date", "15 July 2026")], veg2,
                               hand=[(0, 360, 505, "cauli for Korean trial", 10)])[0], "png", -2.0))

    veg3 = [
        L("POT25", "Potatoes Maris Piper", 2, "25kg sack", 15.20),
        L("STRW", "Strawberries", 3, "5lb tray", 9.50),
        L("MERN", "Meringue nests", 2, "box of 24", 7.80),
        L("MINT", "Mint", 8, "bunch", 0.80),
        L("PEAF", "Garden peas frozen", 3, "2.5kg", 5.90),
        L("CAUL", "Cauliflower", 24, "each", 1.10),
        L("PEAS", "Pea shoots", 4, "punnet", 2.40),
        L("PEAC", "Peaches", 2, "tray (20)", 8.60),
        L("TOMH", "Heritage tomatoes", 1, "tray", 12.50),
        L("LEM80", "Lemons", 1, "box (80)", 18.50),
    ]
    docs.append(("greenacre-GP-2026-0802.pdf",
                 invoice_pages(VEG, "INVOICE", "GP/2026/0802",
                               [("Invoice date", "01/08/26"), ("Delivered", "31/07/26")], veg3), "pdf", 0))

    # Dales Dairy: a case of butter, pints, eggs by the dozen, a wrong total, delivery/due dates, +40% butter.
    dairy1 = [
        L("BUT40", "Butter unsalted 40 x 250g", 1, "case", 88.00),
        L("CRD2", "Double cream 2 ltr", 4, "each", 7.20),
        L("MLK4", "Whole milk 4 pint", 6, "each", 1.95),
        L("BUR125", "Burrata 125g", 12, "each", 2.10),
        L("PAR1", "Parmesan 24 month", 1, "kg", 18.50),
        L("ICV4", "Vanilla ice cream 4L", 1, "tub", 12.80),
        L("CHD25", "Mature cheddar 2.5kg", 1, "block", 17.25),
        L("STL", "Stilton quarter CW", 2.05, "kg", 14.20),
        L("BRI1", "Somerset brie 1kg", 1, "each", 13.40),
        L("EGG15", "Free range eggs 15 dozen", 1, "tray", 29.25),
    ]
    docs.append(("dales-dairy-DD-7781.pdf",
                 invoice_pages(DAIRY, "INVOICE", "DD-7781", [("Invoice date", "04/06/2026")], dairy1), "pdf", 0))

    dairy2 = [
        L("BUT40", "Butter unsalted 40 x 250g", 1, "case", 88.00),
        L("CRD2", "Double cream 2 ltr", 4, "each", 7.20, total=21.60),
        L("MLK4", "Whole milk 4 pint", 6, "each", 1.95),
        L("BUR125", "Burrata 125g", 16, "each", 2.10),
        L("PAR1", "Parmesan 24 month", 1, "kg", 18.50),
        L("ICV4", "Vanilla ice cream 4L", 2, "tub", 12.80),
        L("EGG15", "Free range eggs 15 dozen", 1, "tray", 29.25),
    ]
    docs.append(("dales-dairy-DD-7902.pdf",
                 invoice_pages(DAIRY, "INVOICE", "DD-7902",
                               [("Delivered", "06/07/2026"), ("Invoice date", "07/07/2026"), ("Due", "06/08/2026")],
                               dairy2), "pdf", 0))

    dairy3 = [
        L("BUT40", "Butter unsalted 40 x 250g", 1, "case", 123.20),
        L("CRD2", "Double cream 2 ltr", 5, "each", 7.60),
        L("MLK4", "Whole milk 4 pint", 6, "each", 1.99),
        L("BUR125", "Burrata 125g", 20, "each", 2.25),
        L("ICV4", "Vanilla ice cream 4L", 2, "tub", 12.80),
        L("EGG15", "Free range eggs 15 dozen", 1, "tray", 30.00),
        L("CRF1", "Creme fraiche 1kg", 2, "tub", 4.90),
    ]
    docs.append(("dales-dairy-DD-8034.pdf",
                 invoice_pages(DAIRY, "INVOICE", "DD-8034", [("Invoice date", "07/08/2026")], dairy3,
                               notes=["Butter: national shortage. Prices under weekly review."]), "pdf", 0))

    # Bayside Cash & Carry: a phone photo of a till receipt, VAT included, no invoice number.
    docs.append(("WhatsApp Image 2026-06-22 at 15.02.11.jpeg", receipt_steps(), "jpg", -4.0))
    return docs


def main():
    OUT.mkdir(exist_ok=True)
    skipped = []
    for i, (name, content, kind, tilt) in enumerate(documents()):
        if kind == "pdf":
            data = pdf_bytes(content)
        else:
            steps = content
            crop = 842
            if name.startswith("WhatsApp"):
                crop = 842 - 60   # just the receipt's length of page
            data = photo_bytes(steps, fmt="JPEG" if kind == "jpg" else "PNG", tilt=tilt, seed=i, crop_height=crop)
            if data is None:
                skipped.append(name)
                continue
        (OUT / name).write_bytes(data)
        print(f"  {name:48} {len(data) / 1024:7.0f} KB")
    if skipped:
        print(f"Skipped {len(skipped)} photos (install Pillow to make them): {', '.join(skipped)}")


if __name__ == "__main__":
    main()
