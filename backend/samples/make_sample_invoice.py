"""
Writes samples/sample-invoice.pdf: a made-up supplier invoice for trying the
invoice import by hand (Imports -> Upload invoice). The supplier is fictional.

It's built to exercise the review screen with the demo data:
- most lines match demo ingredients, some with price changes;
- guanciale isn't in the ingredient list, so it becomes a new ingredient;
- the ricotta line's total deliberately doesn't add up (flagged);
- blue roll and delivery are ignored (non-food and a charge).

Standard library only: the PDF is written by hand (one page, Helvetica).
Run from backend/:
    .\\venv\\Scripts\\python.exe samples\\make_sample_invoice.py
"""

from pathlib import Path

SUPPLIER = "Borgo Fine Foods Ltd (sample)"
ADDRESS = ["Unit 4, Example Trading Estate", "Anytown AB1 2CD", "VAT reg. GB 000 0000 00 (sample)"]
CUSTOMER = ["Demo Pizzeria", "1 High Street, Anytown"]
INVOICE_NUMBER = "BFF-20417"
INVOICE_DATE = "18/09/2026"

# (code, description, quantity, unit price, VAT rate). Line total = quantity x unit price,
# except where a total is given (the ricotta line is deliberately wrong).
LINES = [
    ("MZ112", "MOZZ FIOR DI LATTE 12x1KG", 2, 96.00, 0),
    ("FL010", "FARINA 00 CAPUTO 10KG", 3, 13.20, 0),
    ("TM625", "POMODORO SAN MARZANO DOP 6x2.5KG", 1, 61.50, 0),
    ("PR024", "PARMIGIANO REGGIANO 24M 1KG", 2, 16.80, 0),
    ("ND500", "NDUJA CALABRESE 500G", 4, 9.50, 0),
    ("OL005", "EVO OIL 5L", 2, 42.00, 0),
    ("GU150", "GUANCIALE 1.5KG", 1, 24.00, 0),
    ("RC150", "RICOTTA 1.5KG", 2, 7.20, 0, 7.20),
    ("EG030", "EGGS FREE RANGE TRAY 30", 2, 8.40, 0),
    ("BR006", "BLUE ROLL 2PLY x6", 1, 14.50, 20),
    ("DEL", "DELIVERY CHARGE", 1, 7.50, 20),
]


def money(value):
    return f"£{value:,.2f}"


def escape(text):
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_page():
    ops = []

    def text(x, y, s, size=10, bold=False, right=False):
        font = "F2" if bold else "F1"
        if right:   # right-align roughly: Helvetica averages ~0.5 em per character
            x -= len(s) * size * 0.5
        ops.append(f"BT /{font} {size} Tf {x:.1f} {y:.1f} Td ({escape(s)}) Tj ET")

    def rule(y, x1=50, x2=545):
        ops.append(f"0.6 w {x1} {y} m {x2} {y} l S")

    text(50, 790, SUPPLIER, 16, bold=True)
    for i, line in enumerate(ADDRESS):
        text(50, 772 - i * 13, line, 9)
    text(545, 790, "INVOICE", 18, bold=True, right=True)
    text(400, 765, "Invoice no.", 9, bold=True)
    text(470, 765, INVOICE_NUMBER, 9)
    text(400, 752, "Invoice date", 9, bold=True)
    text(470, 752, INVOICE_DATE, 9)
    text(400, 739, "Delivery", 9, bold=True)
    text(470, 739, "17/09/2026", 9)

    text(50, 715, "Invoice to", 9, bold=True)
    for i, line in enumerate(CUSTOMER):
        text(50, 702 - i * 13, line, 9)

    y = 660
    headers = [(50, "Code"), (100, "Description"), (345, "Qty"), (430, "Unit price"), (475, "VAT"), (545, "Total")]
    for x, h in headers:
        text(x, y, h, 9, bold=True, right=h in ("Qty", "Unit price", "Total"))
    rule(y - 6)

    net = vat = 0
    for row in LINES:
        code, description, qty, unit_price, rate = row[:5]
        total = row[5] if len(row) > 5 else round(qty * unit_price, 2)
        y -= 20
        text(50, y, code, 9)
        text(100, y, description, 9)
        text(345, y, str(qty), 9, right=True)
        text(430, y, money(unit_price), 9, right=True)
        text(475, y, f"{rate}%", 9)
        text(545, y, money(total), 9, right=True)
        net += total
        vat += total * rate / 100
    rule(y - 10)

    y -= 30
    for label, value, bold in [("Net", net, False), ("VAT", vat, False), ("Total due", net + vat, True)]:
        text(430, y, label, 10, bold=bold, right=True)
        text(545, y, money(value), 10, bold=bold, right=True)
        y -= 16

    text(50, 90, "Payment terms: 30 days. This is a made-up sample invoice for testing Docket.", 8)
    return "\n".join(ops)


def pdf_bytes(page_ops):
    """A one-page A4 PDF from drawing commands (Helvetica and Helvetica-Bold as F1 / F2)."""
    content = page_ops.encode("cp1252")   # WinAnsi encoding, so the pound sign prints
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
        b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)
    return bytes(out)


if __name__ == "__main__":
    target = Path(__file__).parent / "sample-invoice.pdf"
    target.write_bytes(pdf_bytes(build_page()))
    print(f"Wrote {target}")
