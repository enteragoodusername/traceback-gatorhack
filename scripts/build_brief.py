"""Build the one-page judge brief from the shipped measurement records."""

import json
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/pdf/traceback-brief.pdf"
OUT.parent.mkdir(parents=True, exist_ok=True)
for name, filename in (
    ("DM", "dm-sans-400.ttf"),
    ("DMBold", "dm-sans-700.ttf"),
    ("Manrope", "manrope-700.ttf"),
):
    pdfmetrics.registerFont(TTFont(name, str(ROOT / "public/fonts" / filename)))
INK = HexColor("#203c36")
MUTED = HexColor("#65746c")
GREEN = HexColor("#244f42")
LIME = HexColor("#d6ed9a")
PAPER = HexColor("#f6f7f3")
BORDER = HexColor("#dfe5da")
DEMO = "https://enteragoodusername.github.io/traceback-gatorhack/"
REPO = "https://github.com/enteragoodusername/traceback-gatorhack"
eval = json.loads((ROOT / "public/evaluation.json").read_text())
extra = json.loads((ROOT / "public/validation/cross-work.json").read_text())
c = canvas.Canvas(str(OUT), pagesize=(612, 792), pageCompression=1)
c.setTitle("Traceback - a judge's brief")
c.setAuthor("Traceback contributors")
c.setSubject("Local video provenance with measured, inspectable evidence")
c.setFillColor(PAPER)
c.rect(0, 0, 612, 792, fill=1, stroke=0)


def label(text, x, y, size=8, color=MUTED, font="DMBold"):
    c.setFillColor(color)
    c.setFont(font, size)
    c.drawString(x, y, text)


def paragraph(text, x, top, width, size=9.3, leading=13.3, color=INK):
    style = ParagraphStyle(
        "body", fontName="DM", fontSize=size, leading=leading, textColor=color
    )
    p = Paragraph(text, style)
    _, height = p.wrap(width, 500)
    p.drawOn(c, x, top - height)
    return top - height


label("GATOR HACK V  /  OCTOBER 2026", 38, 754, 8, GREEN)
label("traceback.", 38, 712, 36, INK, "Manrope")
label("Find the source behind the edit.", 39, 687, 15, GREEN, "Manrope")
paragraph(
    "A local video provenance workbench for researchers, filmmakers, and archives. Find an indexed source, inspect the correspondence, and share the measured evidence.",
    39,
    670,
    438,
    10,
    14,
)
qr = QrCodeWidget(DEMO)
x0, y0, x1, y1 = qr.getBounds()
size = 72
qr_drawing = Drawing(
    size, size, transform=[size / (x1 - x0), 0, 0, size / (y1 - y0), 0, 0]
)
qr_drawing.add(qr)
renderPDF.draw(qr_drawing, c, 500, 688)
label("OPEN THE DEMO", 501, 677, 6.9, GREEN)
c.linkURL(DEMO, (497, 674, 575, 763), relative=0, thickness=0)

# Native PDF evidence diagram from the exact measured frames and coordinates.
report = json.loads((ROOT / "public/evidence/vertical/report.json").read_text())
match = report["results"][0]
pair = match["evidence"][0]
c.setFillColor(HexColor("#ffffff"))
c.roundRect(38, 322, 536, 304, 9, fill=1, stroke=0)
label("MEASURED FRAME CORRESPONDENCE", 55, 607, 8, GREEN)
label(f"QUERY  /  {pair['queryTime']:.2f}s", 64, 584, 7.8, GREEN)
label(f"INDEXED SOURCE  /  {pair['sourceTime']:.2f}s", 235, 584, 7.8, GREEN)
for key, side, box in (
    ("queryImage", "query", (58, 376, 149, 194)),
    ("sourceImage", "source", (231, 376, 326, 194)),
):
    image = ImageReader(str(ROOT / "public/evidence/vertical" / pair[key]))
    iw, ih = image.getSize()
    bx, by, bw, bh = box
    scale = min(bw / iw, bh / ih)
    w, h = iw * scale, ih * scale
    x, y = bx + (bw - w) / 2, by + (bh - h) / 2
    c.setFillColor(HexColor("#edf0e8"))
    c.roundRect(bx, by, bw, bh, 5, fill=1, stroke=0)
    c.drawImage(image, x, y, width=w, height=h)
    c.setFillColor(LIME)
    c.setStrokeColor(GREEN)
    c.setLineWidth(0.4)
    for point in pair["points"]:
        px, py = point[side]
        c.circle(x + px * w, y + (1 - py) * h, 2.2, fill=1, stroke=1)
    if side == "source":
        path = c.beginPath()
        for i, (px, py) in enumerate(pair["quad"]):
            if i == 0:
                path.moveTo(x + px * w, y + (1 - py) * h)
            else:
                path.lineTo(x + px * w, y + (1 - py) * h)
        path.close()
        c.setStrokeColor(LIME)
        c.setLineWidth(1)
        c.drawPath(path)
for x, heading, value in (
    (58, "SUPPORTED QUERY FRAMES", str(match["alignment"]["support"])),
    (231, "PLAYBACK ESTIMATE", f"{match['alignment']['speed']:.2f}x"),
    (420, "THIS FRAME PAIR", f"{pair['inliers']} inliers"),
):
    label(heading, x, 359, 6.8, MUTED)
    label(value, x, 337, 16, INK, "Manrope")
label(
    "ACTUAL PIPELINE OUTPUT  /  Cropped, graded, captioned, and sped up",
    42,
    309,
    7.3,
    GREEN,
)

left, right, col = 39, 316, 257
label("WHY THE NEW MODEL MATTERS", left, 285, 8, GREEN)
paragraph(
    "<b>Qwen3-VL-Embedding-2B</b>, released in January 2026, retrieves moments from pixels and natural language. Source filenames and captions are not embedded.",
    left,
    273,
    col,
)
paragraph(
    "Geometry and appearance checks verify shared imagery. Temporal fitting estimates the source interval and playback change, with explicit ambiguity when the evidence is weak.",
    left,
    215,
    col,
)

label("MEASURED RESULTS, WITH THEIR SCOPE", right, 285, 8, GREEN)
paragraph(
    f"<b>{eval['recovered']}/{eval['positiveCount']} edited queries recovered</b><br/><b>{eval['rejected']}/{eval['negativeCount']} negatives rejected</b><br/>Four-source controlled evaluation; no false source matches. Synthetic edits, not an internet-wide accuracy estimate.",
    right,
    273,
    col,
)
paragraph(
    f"Additional-film check: <b>{extra['recovered']}/{extra['positiveCount']} edits verified</b>, <b>{extra['rejected']}/{extra['negativeCount']} negatives rejected</b>. One correctly retrieved clip failed temporal verification. No thresholds were changed after that result.",
    right,
    201,
    col,
    9.0,
    12.7,
)

c.setStrokeColor(BORDER)
c.line(39, 140, 573, 140)
label("TRY IT IN 60 SECONDS", 39, 125, 8, GREEN)
paragraph(
    "Trace the cropped repost. Inspect two frame pairs. Export its packet, then open <b>Verify a packet</b> to check the included files in your browser. The hosted demo shows real saved runs; the local service accepts new sources and queries.",
    39,
    115,
    534,
    9.1,
    13,
)
label("Interactive demo", 39, 63, 8.4, GREEN)
label("Source code + reproduction", 198, 63, 8.4, GREEN)
label("Captioned 2:15 walkthrough", 402, 63, 8.4, GREEN)
for x, width, link in ((39, 135, DEMO), (198, 180, REPO), (402, 171, DEMO + "demo/")):
    c.linkURL(link, (x, 59, x + width, 73), relative=0, thickness=0)
paragraph(
    "A match establishes shared imagery, not ownership, infringement, or first publication. Checksums are not signatures.",
    39,
    49,
    534,
    7.1,
    9.2,
    MUTED,
)
paragraph(
    "Figure: real measured evidence, not a browser screenshot. Tears of Steel: (CC) Blender Foundation | mango.blender.org, CC BY 3.0. Application: MIT; dependencies retain their own licenses.",
    39,
    27,
    534,
    6.3,
    8.2,
    MUTED,
)
c.showPage()
c.save()
print(OUT)
