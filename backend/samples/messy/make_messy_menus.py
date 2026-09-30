"""
Writes samples/messy/menus/: two menus for "The Tidewater (sample)", a
fictional coastal bistro.

  menu-spring-2026.pdf   start it on 1 Jun 2026. Two pages, two columns,
                         prices without £ ("9.5"), two sizes on one line
                         ("17.5 / small 13"), "3 for 9 · 6 for 16", a market
                         price (MP), add-ons, a set lunch, kids' dishes that
                         share names with the adult ones, drinks, allergen codes.
  menu-summer-2026.jpg   start it on 1 Aug 2026. A phone photo with pen on it:
                         a price crossed out and rewritten, a dish crossed out
                         ("86"), a dish added by hand; renames, a new dish,
                         a dish dropped (Lamb Rump), price rises.

Run from backend/:
    .\\venv\\Scripts\\python.exe samples\\messy\\make_messy_menus.py
"""

from pathlib import Path

from render import pdf_bytes, photo_bytes

OUT = Path(__file__).parent / "menus"


def section(steps, x, y, title, items, width=220):
    """A menu section: title, then items (name, price text, description). Returns the next y."""
    steps.append(("text", x, y, title, "serif-bold", 12, "left"))
    steps.append(("line", x, y - 5, x + width, y - 5, 0.4))
    y -= 22
    for name, price, desc in items:
        steps.append(("text", x, y, name, "serif-bold", 10, "left"))
        steps.append(("text", x + width, y, price, "serif", 10, "right"))
        y -= 12
        if desc:
            steps.append(("text", x, y, desc, "serif-italic", 8, "left"))
            y -= 11
        y -= 6
    return y - 10


def header(steps, subtitle):
    steps.append(("text", 297, 790, "THE TIDEWATER", "serif-bold", 24, "centre"))
    steps.append(("text", 297, 772, subtitle, "serif-italic", 10, "centre"))
    steps.append(("line", 60, 760, 535, 760, 0.8))


FOOTER = ["(v) vegetarian  (vg) vegan  (gf) gluten free. Please tell us about any allergies before you order.",
          "A discretionary 12.5% service charge is added to tables of 6 or more. Specials on the board.",
          "Made-up sample menu for testing Docket. Not a real business."]


def spring_pages():
    p1, p2 = [], []
    header(p1, "Seasonal cooking from the quay  ·  Tuesday to Sunday")
    section(p1, 60, 730, "TO START", [
        ("Soup of the Day (v)", "7", "Ask your server, with sourdough"),
        ("Smoked Mackerel Pâté", "8.5", "Pickled cucumber, toast"),
        ("Salt & Pepper Squid", "9.5", "Lime & chilli mayo"),
        ("Crispy Pork Belly Bites", "8", "Apple ketchup, crackling salt"),
        ("Burrata & Heritage Tomato (v)(gf)", "10", "Basil oil, sea salt"),
        ("Rock Oysters (gf)", "3 for 9 · 6 for 16", "Shallot vinegar, lemon"),
    ])
    y = section(p1, 315, 730, "MAINS", [
        ("Beer-Battered Haddock & Chips", "17.5 / small 13", "Mushy peas, tartare sauce"),
        ("Flat Iron Steak Frites", "24", "8oz, watercress, garlic butter. Peppercorn sauce +3"),
        ("Pan-Roasted Hake", "22", "Mussels, samphire, beurre blanc"),
        ("Lamb Rump (gf)", "26", "Crushed peas & mint, lamb jus"),
        ("Tidewater Burger", "16.5", "Brioche, pickles, chips. Add bacon 2 · cheese 1.5"),
        ("Wild Mushroom Risotto (v)", "15", "Parmesan, truffle oil. (vg) on request"),
        ("Whole Lemon Sole", "MP", "Brown butter, capers, new potatoes"),
        ("Chicken Supreme", "19", "Wild garlic, mash, chicken butter sauce"),
    ])
    p1.append(("text", 297, 60, "Please turn over for sides, puddings & more", "serif-italic", 9, "centre"))

    header(p2, "")
    section(p2, 60, 730, "ON THE SIDE", [
        ("Chips (vg)", "4.5", None), ("Truffle & Parmesan Fries (v)", "6", None),
        ("Tenderstem Broccoli (vg)(gf)", "5", "Chilli, garlic"), ("House Salad (vg)", "4.5", None),
        ("Bread & Butter (v)", "4", "Sourdough, whipped butter. For the table"),
    ])
    section(p2, 315, 730, "PUDDINGS", [
        ("Sticky Toffee Pudding (v)", "8", "Toffee sauce, clotted cream"),
        ("Crème Brûlée (v)(gf)", "7.5", "Shortbread"),
        ("Dark Chocolate Tart (v)", "8", "Crème fraîche"),
        ("Affogato (v)", "6", "Vanilla ice cream, espresso. Add Frangelico 3"),
        ("Cheeseboard", "3 cheeses 11 / 5 cheeses 16", "Chutney, crackers, grapes"),
    ])
    y = section(p2, 60, 480, "SUNDAYS", [
        ("Roast Sirloin of Beef", "24", "Yorkshire pudding, roast potatoes, all the trimmings. Sunday only"),
    ])
    section(p2, 60, y, "LITTLE ONES (under 10)", [
        ("Fish & Chips", "8", None), ("Burger & Chips", "7.5", None), ("Ice Cream", "3.5", "Two scoops"),
    ])
    y = section(p2, 315, 480, "SET LUNCH  Tue-Fri 12-3", [
        ("Two courses", "20", "Soup or Mackerel Pâté · Haddock (small) or Risotto"),
        ("Three courses", "25", "... and Sticky Toffee Pudding or Ice Cream"),
    ])
    section(p2, 315, y, "TO DRINK", [
        ("Porthsample Lager, pint", "6.2", None), ("House white / red, 175ml", "7", None),
        ("Soft drinks", "3", None), ("Coffee", "from 2.8", None),
    ])
    for i, line in enumerate(FOOTER):
        p2.append(("text", 297, 90 - i * 11, line, "serif-italic", 7, "centre"))
    return [p1, p2]


def summer_page():
    s = []
    header(s, "Summer  ·  Tuesday to Sunday")
    section(s, 60, 730, "TO START", [
        ("Soup of the Day (v)", "7", "Ask your server, with sourdough"),
        ("Smoked Mackerel Pâté", "8.5", "Pickled cucumber, toast"),
        ("Salt & Pepper Squid", "10.5", "Lime & chilli mayo"),
        ("Korean Fried Cauliflower (vg)", "8", "Gochujang glaze, sesame, spring onion"),
        ("Burrata, Peach & Basil (v)(gf)", "10.5", "Grilled peach, basil oil"),
        ("Rock Oysters (gf)", "3 for 9.5 · 6 for 17", "Shallot vinegar, lemon"),
    ])
    y = section(s, 315, 730, "MAINS", [
        ("Beer-Battered Haddock & Chips", "17.5 / small 13", "Mushy peas, tartare sauce"),
        ("Flat Iron Steak Frites", "24", "8oz, watercress, garlic butter. Peppercorn sauce +3"),
        ("Cornish Hake", "23", "Brown shrimp butter, samphire, new potatoes"),
        ("Tidewater Smash Burger", "17", "Double patty, American cheese, pickles, chips"),
        ("Summer Pea & Mint Risotto (v)", "15", "Pea shoots, parmesan. (vg) on request"),
        ("Whole Lemon Sole", "MP", "Brown butter, capers, new potatoes"),
        ("Chicken Supreme", "19", "Wild garlic, mash, chicken butter sauce"),
        ("Crab Linguine", "21", "Chilli, lemon, parsley"),
    ])
    # Pen on the printed menu: haddock price rewritten, chicken crossed out.
    s.append(("line", 468, 709, 492, 713, 1.2))
    s.append(("hand", 440, 722, "18.5", 13))
    chicken_y = 730 - 22 - 6 * 29
    s.append(("line", 313, chicken_y + 3, 540, chicken_y + 3, 1.4))
    s.append(("hand", 470, chicken_y + 12, "86", 14))
    section(s, 60, 470, "ON THE SIDE", [
        ("Chips (vg)", "5", None), ("Truffle & Parmesan Fries (v)", "6", None),
        ("Tenderstem Broccoli (vg)(gf)", "5", None), ("House Salad (vg)", "4.5", None),
        ("Bread & Butter (v)", "4", None),
    ])
    y = section(s, 315, 470, "PUDDINGS", [
        ("Sticky Toffee Pudding (v)", "8", None), ("Crème Brûlée (v)(gf)", "7.5", None),
        ("Dark Chocolate Tart (v)", "8.5", None), ("Affogato (v)", "6", None),
        ("Cheeseboard", "3 cheeses 11 / 5 cheeses 16", None),
    ])
    s.append(("hand", 315, y + 6, "+ Eton Mess  7.5", 13))
    section(s, 60, 250, "SUNDAYS · LITTLE ONES · SET LUNCH", [
        ("Roast Sirloin of Beef (Sun)", "25", None),
        ("Kids: Fish & Chips 8 · Burger & Chips 7.5 · Ice Cream 3.5", "", None),
        ("Set lunch Tue-Fri: two courses 20 · three courses 25", "", None),
    ], width=475)
    for i, line in enumerate(FOOTER):
        s.append(("text", 297, 90 - i * 11, line, "serif-italic", 7, "centre"))
    return s


def main():
    OUT.mkdir(exist_ok=True)
    (OUT / "menu-spring-2026.pdf").write_bytes(pdf_bytes(spring_pages()))
    print("  menu-spring-2026.pdf")
    photo = photo_bytes(summer_page(), tilt=2.5, seed=7)
    if photo is None:
        print("Skipped menu-summer-2026.jpg (install Pillow to make it)")
    else:
        (OUT / "menu-summer-2026.jpg").write_bytes(photo)
        print("  menu-summer-2026.jpg")


if __name__ == "__main__":
    main()
