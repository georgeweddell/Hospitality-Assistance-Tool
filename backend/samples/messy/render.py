"""
Draws a made-up document two ways: as a PDF (standard library only), or as a
"phone photo" JPG/PNG (needs Pillow: crooked, shadowed, grainy, like a photo
of paper on a counter).

A document is a list of pages; a page is a list of drawing steps, in PDF
points on an A4 page (595 x 842, origin bottom-left):
  ("text", x, y, string, font, size, align)   align: "left" | "right" | "centre"
  ("line", x1, y1, x2, y2, width)
  ("box", x, y, w, h, grey)                    filled rectangle, grey 0 (black) - 1 (white)
  ("hand", x, y, string, size)                 handwriting in blue pen (italic in a PDF)
Fonts: "sans", "sans-bold", "mono", "mono-bold", "serif", "serif-bold", "serif-italic".
"""

import random

PDF_FONTS = {   # our name -> (PDF resource name, PDF base font)
    "sans": ("F1", "Helvetica"),
    "sans-bold": ("F2", "Helvetica-Bold"),
    "mono": ("F3", "Courier"),
    "mono-bold": ("F4", "Courier-Bold"),
    "serif": ("F5", "Times-Roman"),
    "serif-bold": ("F6", "Times-Bold"),
    "serif-italic": ("F7", "Times-Italic"),
}
PHOTO_FONTS = {   # Windows font files; any missing one falls back to Pillow's own font
    "sans": "arial.ttf", "sans-bold": "arialbd.ttf", "mono": "cour.ttf", "mono-bold": "courbd.ttf",
    "serif": "times.ttf", "serif-bold": "timesbd.ttf", "serif-italic": "timesi.ttf", "hand": "segoepr.ttf",
}
CHAR_WIDTH = {"sans": 0.52, "mono": 0.6, "serif": 0.47}   # rough average width in ems, for aligning in a PDF


# --- PDF --------------------------------------------------------------------------------------

def _escape(text):
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _pdf_width(text, font, size):
    return len(text) * size * CHAR_WIDTH[font.split("-")[0]]


def _pdf_page(steps):
    ops = []
    for step in steps:
        kind = step[0]
        if kind == "text":
            _, x, y, s, font, size, align = step
            if align == "right":
                x -= _pdf_width(s, font, size)
            elif align == "centre":
                x -= _pdf_width(s, font, size) / 2
            ops.append(f"BT /{PDF_FONTS[font][0]} {size} Tf {x:.1f} {y:.1f} Td ({_escape(s)}) Tj ET")
        elif kind == "hand":
            _, x, y, s, size = step
            ops.append(f"0.1 0.2 0.6 rg BT /F7 {size} Tf {x:.1f} {y:.1f} Td ({_escape(s)}) Tj ET 0 0 0 rg")
        elif kind == "line":
            _, x1, y1, x2, y2, width = step
            ops.append(f"{width} w {x1:.1f} {y1:.1f} m {x2:.1f} {y2:.1f} l S")
        elif kind == "box":
            _, x, y, w, h, grey = step
            ops.append(f"{grey} g {x:.1f} {y:.1f} {w:.1f} {h:.1f} re f 0 g")
    return "\n".join(ops).encode("cp1252")   # WinAnsi encoding, so £, é and û print


def pdf_bytes(pages):
    """A multi-page A4 PDF from drawing steps."""
    fonts = list(PDF_FONTS.values())
    first_page = 3 + len(fonts)
    kids = " ".join(f"{first_page + 2 * i} 0 R" for i in range(len(pages)))
    font_refs = " ".join(f"/{res} {3 + i} 0 R" for i, (res, _) in enumerate(fonts))
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>",
               f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode()]
    for _, base in fonts:
        objects.append(f"<< /Type /Font /Subtype /Type1 /BaseFont /{base} /Encoding /WinAnsiEncoding >>".encode())
    for i, steps in enumerate(pages):
        content = _pdf_page(steps)
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
                       f"/Resources << /Font << {font_refs} >> >> /Contents {first_page + 2 * i + 1} 0 R >>".encode())
        objects.append(b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream")

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


# --- Photo ------------------------------------------------------------------------------------

def photo_bytes(steps, fmt="JPEG", tilt=3.0, seed=1, scale=2.4, crop_height=842):
    """
    One page as a phone photo: drawn on off-white paper, tilted, lit unevenly,
    grainy and softly blurred, on a dark counter. crop_height (points) keeps
    only the top of the page, for a narrow till receipt or a half-used page.
    Returns the file's bytes, or None if Pillow isn't installed.
    """
    try:
        from PIL import Image, ImageDraw, ImageFilter, ImageFont
    except ImportError:
        return None
    import io

    rng = random.Random(seed)
    width, height = int(595 * scale), int(842 * scale)
    paper = Image.new("RGB", (width, height), (246, 242, 231))
    draw = ImageDraw.Draw(paper)
    cache = {}

    def font(name, size):
        key = (name, size)
        if key not in cache:
            try:
                cache[key] = ImageFont.truetype(f"C:/Windows/Fonts/{PHOTO_FONTS[name]}", int(size * scale))
            except OSError:
                cache[key] = ImageFont.load_default(int(size * scale))
        return cache[key]

    def xy(x, y):
        return x * scale, (842 - y) * scale

    for step in steps:
        kind = step[0]
        if kind in ("text", "hand"):
            if kind == "text":
                _, x, y, s, name, size, align = step
                colour = (38, 36, 40)
            else:
                _, x, y, s, size = step
                name, align, colour = "hand", "left", (28, 48, 140)
            f = font(name, size)
            px, py = xy(x, y)
            w = draw.textlength(s, font=f)
            if align == "right":
                px -= w
            elif align == "centre":
                px -= w / 2
            draw.text((px, py), s, font=f, fill=colour, anchor="ls")
        elif kind == "line":
            _, x1, y1, x2, y2, lw = step
            draw.line([xy(x1, y1), xy(x2, y2)], fill=(40, 40, 40), width=max(1, int(lw * scale)))
        elif kind == "box":
            _, x, y, w, h, grey = step
            shade = int(255 * grey)
            (ax, ay), (bx, by) = xy(x, y + h), xy(x + w, y)
            draw.rectangle([ax, ay, bx, by], fill=(shade, shade, shade - 6))

    paper = paper.crop((0, 0, width, int(crop_height * scale)))

    # Uneven light: darker towards one corner, like a phone held over the page.
    big = Image.linear_gradient("L").resize((paper.width * 2, paper.height * 2))
    big = big.rotate(rng.choice([35, 145, 215]), resample=Image.BICUBIC)
    shade = big.crop((paper.width // 2, paper.height // 2, paper.width * 3 // 2, paper.height * 3 // 2))
    shadow = Image.new("RGB", paper.size, (150, 140, 120))
    paper = Image.composite(shadow, paper, shade.point(lambda v: int(v * 0.35)))

    # On the counter, tilted.
    margin = int(60 * scale)
    table = Image.new("RGB", (paper.width + 2 * margin, paper.height + 2 * margin), (66, 58, 50))
    table.paste(paper, (margin, margin))
    table = table.rotate(tilt, resample=Image.BICUBIC, fillcolor=(66, 58, 50))

    # Grain and a little blur.
    noise = Image.effect_noise(table.size, 22).convert("RGB")
    table = Image.blend(table, noise, 0.07).filter(ImageFilter.GaussianBlur(0.7))

    out = io.BytesIO()
    table.save(out, fmt, quality=62) if fmt == "JPEG" else table.save(out, fmt, optimize=True)
    return out.getvalue()
