"""
Writes samples/sample-menu.pdf: a made-up "Autumn menu" for the demo pizzeria,
for trying the menu import by hand (Imports -> Upload menu, starting 1 Oct 2026).

Compared with the demo data it has:
- a price rise (Diavola £13.00 -> £13.50);
- a new dish that uses guanciale (Carbonara Pizza), tying in with the sample invoice;
- a rename ("Nduja & Hot Honey" -> "'Nduja, Hot Honey & Fior di Latte");
- a returning dish (Marinara, off the menu since 31 July);
- one dish dropped (Cannoli);
- drinks, add-ons and a lunch deal, which aren't dishes.
The demo dishes have no stored descriptions yet, so this first import fills
them in; a later menu with a changed description would flag "Check recipe".

Standard library only (uses the PDF writer in make_sample_invoice.py).
Run from backend/:
    .\\venv\\Scripts\\python.exe samples\\make_sample_menu.py
"""

from pathlib import Path

from make_sample_invoice import escape, pdf_bytes

SECTIONS = [
    ("Antipasti", [
        ("Garlic Pizza Bread", 6.50, "Wood-fired dough, garlic butter, parsley"),
        ("Arancini", 7.50, "Saffron risotto balls, mozzarella, tomato sauce"),
        ("Burrata", 9.50, "Burrata, heritage tomatoes, basil oil"),
        ("Bruschetta", 6.00, "Tomato, garlic, basil on toasted sourdough"),
    ]),
    ("Pizze", [
        ("Margherita", 11.50, "San Marzano tomato, fior di latte, basil"),
        ("Marinara", 9.50, "Tomato, garlic, oregano, olive oil"),
        ("Diavola", 13.50, "Tomato, fior di latte, spicy salami"),
        ("Funghi", 12.00, "Fior di latte, mushrooms, thyme"),
        ("'Nduja, Hot Honey & Fior di Latte", 14.00, "Tomato, 'nduja, fior di latte, hot honey"),
        ("Prosciutto e Rucola", 14.50, "Tomato, fior di latte, prosciutto, rocket, parmesan"),
        ("Salsiccia e Friarielli", 14.00, "Fior di latte, fennel sausage, friarielli"),
        ("Quattro Formaggi", 13.50, "Fior di latte, gorgonzola, parmesan, fontina"),
        ("Mortadella & Pistachio", 15.00, "Fior di latte, mortadella, pistachio pesto, burrata"),
        ("Carbonara Pizza", 14.50, "Guanciale, egg yolk, pecorino, black pepper"),
    ]),
    ("Contorni", [
        ("Rosemary Fries", 4.50, "Skin-on fries, rosemary salt"),
        ("Dough Balls", 5.00, "With garlic butter"),
        ("Rocket & Parmesan Salad", 5.00, "Rocket, parmesan, balsamic"),
        ("Friarielli", 6.00, "Sauteed with garlic and chilli"),
    ]),
    ("Dolci", [
        ("Tiramisu", 7.00, "Mascarpone, espresso, cocoa"),
        ("Nutella Calzone", 7.50, "Folded pizza, Nutella, icing sugar"),
        ("Affogato", 5.00, "Vanilla gelato, espresso"),
        ("Panna Cotta", 7.00, "Vanilla panna cotta, berry compote"),
    ]),
    ("Extras", [
        ("Add burrata", 3.00, ""),
        ("Add 'nduja", 2.00, ""),
        ("Lunch deal: any pizza + soft drink", 12.00, "Mon-Fri, 12-3pm"),
    ]),
    ("Drinks", [
        ("Peroni 330ml", 5.00, ""),
        ("Coca-Cola 330ml", 3.00, ""),
        ("House red 175ml", 7.00, ""),
    ]),
]


def build_page():
    ops = []

    def text(x, y, s, size=10, bold=False, right=False):
        if right:
            x -= len(s) * size * 0.5
        ops.append(f"BT /{'F2' if bold else 'F1'} {size} Tf {x:.1f} {y:.1f} Td ({escape(s)}) Tj ET")

    text(297 - 4 * 18 * 0.55, 800, "DEMO PIZZERIA", 18, bold=True)
    text(297 - 13 * 11 * 0.5, 780, "Autumn menu 2026", 11)

    # Two columns: food on the left, the rest on the right.
    columns = [(50, SECTIONS[:2]), (320, SECTIONS[2:])]
    for x, sections in columns:
        y = 745
        for heading, items in sections:
            text(x, y, heading.upper(), 11, bold=True)
            y -= 17
            for name, price, description in items:
                text(x, y, name, 9, bold=True)
                text(x + 235, y, f"£{price:.2f}", 9, right=True)
                y -= 11
                if description:
                    text(x, y, description, 7.5)
                    y -= 11
                y -= 3
            y -= 10

    text(50, 60, "Please tell us about any allergies. A discretionary 12.5% service charge is added to tables of 6 or more.", 7)
    return "\n".join(ops)


if __name__ == "__main__":
    target = Path(__file__).parent / "sample-menu.pdf"
    target.write_bytes(pdf_bytes(build_page()))
    print(f"Wrote {target}")
