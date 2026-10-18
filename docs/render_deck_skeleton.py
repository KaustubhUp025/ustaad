from pathlib import Path
from textwrap import wrap

from reportlab.lib.colors import HexColor, white
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas


OUT = Path(__file__).with_name("ustaad-deck-skeleton.pdf")
SHOT = Path(__file__).parent / "screenshots/t24-import-1280.png"
W, H = 960, 540
BG = HexColor("#EEF1EF")
GRAPHITE = HexColor("#1D2327")
YELLOW = HexColor("#F6BE00")
GREEN = HexColor("#0B6B4F")
COPPER = HexColor("#A9592D")
RED = HexColor("#D1263A")
MUTED = HexColor("#536069")
BORDER = HexColor("#CBD3D0")


def textbox(c: Canvas, text: str, x: float, y: float, width: float, size: float = 15, color=GRAPHITE, leading=None, bold=False):
    leading = leading or size * 1.28
    chars = max(12, int(width / (size * 0.53)))
    c.setFillColor(color)
    c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
    cursor = y
    for paragraph in text.split("\n"):
        for line in wrap(paragraph, chars) or [""]:
            c.drawString(x, cursor, line)
            cursor -= leading
    return cursor


def rect(c: Canvas, x: float, y: float, width: float, height: float, fill=white, stroke=BORDER, radius=0):
    c.setFillColor(fill)
    c.setStrokeColor(stroke)
    c.roundRect(x, y, width, height, radius, fill=1, stroke=bool(stroke))


def page(c: Canvas, title: str, subtitle: str | None = None, dark=False):
    c.setFillColor(GRAPHITE if dark else BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    if title:
        textbox(c, title, 55, 485, 850, 27 if not dark else 34, white if dark else GRAPHITE, bold=True)
    if subtitle:
        textbox(c, subtitle, 55, 445, 830, 13, MUTED if not dark else BG)


def footer(c: Canvas, text: str, dark=False):
    textbox(c, text, 55, 22, 850, 8, BG if dark else MUTED)


def cards(c: Canvas, items, y=250, color=GREEN):
    width, gap = 190, 28
    for index, (heading, detail) in enumerate(items):
        x = 55 + index * (width + gap)
        rect(c, x, y, width, 125, white, color)
        textbox(c, heading, x + 16, y + 92, width - 32, 15, GRAPHITE, bold=True)
        textbox(c, detail, x + 16, y + 62, width - 32, 10, MUTED)


def build():
    c = Canvas(str(OUT), pagesize=(W, H))

    page(c, "Ustaad", dark=True)
    c.setFillColor(YELLOW); c.rect(55, 190, 12, 225, fill=1, stroke=0)
    textbox(c, "A voice-first repair companion that turns technician-group knowledge into cited, step-by-step help.", 85, 325, 700, 20, BG)
    rect(c, 85, 180, 220, 34, YELLOW, YELLOW); textbox(c, "GOOGLE CLOUD AI BUILDER CUP 2026", 98, 192, 195, 10, GRAPHITE, bold=True)
    footer(c, "Submission deck skeleton · all claims trace to repository documentation · final links and results are marked pending", True)
    c.showPage()

    page(c, "The senior technician is usually unreachable when the worker needs them most.", "Raju is an independent, Hindi-first AC technician: patchy 4G, busy hands, a customer waiting, and hundreds of unplayed group voice notes.")
    cards(c, [("Before the job", "No model number; the wrong parts may be packed."), ("At the unit", "A blinking error code; a senior is busy elsewhere."), ("Missing a part", "Time disappears riding shop to shop."), ("After the job", "The fix is rarely written down for the next technician.")], 210)
    footer(c, "Source: docs/PRODUCT.md · product framing, not a customer-study claim.")
    c.showPage()

    page(c, "One working conversation — from “E6 aa raha hai” to a cited next step.")
    cards(c, [("1 · Ask by voice", "Push-to-talk, captions, and the worker’s own words."), ("2 · See when needed", "Photo request with a framing tip; check, retake, or continue."), ("3 · Cite and guide", "A source chip and one gate-aware step at a time."), ("4 · Act and learn", "Check stock, ask vendors, then capture the completed fix.")], 245)
    textbox(c, "Voice-first by design: short spoken guidance for a worker whose hands are busy, with every meaningful interaction visible in captions.", 100, 135, 760, 16, MUTED)
    c.showPage()

    page(c, "Architecture: a single repair conversation, grounded by stored knowledge and safe actions.")
    boxes = [(55, 225, 160, 120, "Worker PWA", "Voice · captions · camera · quotes\nDashboard PWA", GRAPHITE, white), (305, 225, 170, 120, "Cloud Run API", "FastAPI + ADK\nLive WebSocket · REST · ingest jobs", white, GRAPHITE), (590, 325, 150, 82, "Gemini Live + Flash", "Agent Platform", GREEN, white), (590, 135, 150, 82, "Firestore + Storage", "Jobs · cards · imports · media", white, GRAPHITE), (780, 325, 135, 82, "Telegram Bot", "Vendor quote demo fallback", white, GRAPHITE), (780, 135, 135, 82, "Agent Search", "Manual citations · store setup pending", white, GRAPHITE)]
    for x, y, width, height, head, detail, fill, color in boxes:
        rect(c, x, y, width, height, fill, GREEN if fill == white else fill)
        textbox(c, head, x + 12, y + height - 28, width - 24, 13, color, bold=True)
        textbox(c, detail, x + 12, y + height - 52, width - 24, 9, color if fill != white else MUTED)
    c.setStrokeColor(GREEN); c.setLineWidth(2)
    for end in [(585, 366), (585, 176), (775, 366), (775, 176)]: c.line(475, 285, *end)
    c.line(215, 285, 305, 285)
    footer(c, "Repo facts: Firebase Hosting fronts the PWA; the Live WebSocket connects directly to Cloud Run. Agent Search is intentionally shown as pending.")
    c.showPage()

    page(c, "Safety is a product boundary, not a disclaimer.")
    cards(c, [("Hide hazardous steps", "Gates keep a hazardous step from reaching the worker until required evidence passes. Hard-stop work routes to a fixed safety screen."), ("Ground the guidance", "Use a cited fault card or manual page. If neither exists, label it as general guidance and ask to see more."), ("Verify, then report", "Safety bypass evidence and phone checks are kept separate from feature claims. FINAL SAFETY RESULT — INSERT T29 EVIDENCE")], 205, RED)
    footer(c, "Source: docs/SAFETY.md and docs/SPEC.md. This slide makes no final pass-rate claim.")
    c.showPage()

    page(c, "Turn the group’s buried know-how into cited fault cards — with consent and provenance.")
    cards(c, [("Consent-based export", "Private export stays out of Git."), ("Parse + enrich", "Messages, media, transcripts."), ("Thread + extract", "Question → answers → outcome."), ("Dedupe + cite", "Fault cards carry source credit.")], 255)
    rect(c, 55, 110, 850, 70, GRAPHITE, GRAPHITE)
    textbox(c, "Recorded partial dev run, not a final benchmark: 60 messages · 13 notes · 6 photos · 9 correctly grouped threads · 8 cards + 1 merge · 1 min 47 s end-to-end. FINAL IMPORT SCORE — PENDING.", 72, 148, 815, 14, white)
    footer(c, "Media provenance: demo-group photos are AI-generated or public-post images and must be labelled wherever shown; this slide uses no photo as evidence.")
    c.showPage()

    page(c, "Keep the technician on the job while nearby vendors answer the part request.")
    cards(c, [("Request", "Ustaad checks the needed part and sends a structured request."), ("Reply", "Vendor text or voice replies are parsed and ranked."), ("Approve", "The worker sees availability, price, ETA, and voice-reply status.")], 240, COPPER)
    rect(c, 55, 135, 850, 42, YELLOW, YELLOW); textbox(c, "DEMO FALLBACK: TELEGRAM BOT. WHATSAPP CLOUD API RETURNS AFTER META BUSINESS VERIFICATION.", 72, 150, 815, 10, GRAPHITE, bold=True)
    footer(c, "PHONE TEST / QUOTE ROUND-TRIP RESULT — PENDING. No vendor price, delivery, or response-time claim is made here.")
    c.showPage()

    page(c, "A laptop view makes knowledge capture visible to the shop owner and judges.")
    c.drawImage(ImageReader(str(SHOT)), 55, 95, 600, 422, preserveAspectRatio=True, anchor="sw")
    rect(c, 700, 150, 205, 275, white, BORDER)
    textbox(c, "What the dashboard shows", 718, 388, 170, 15, GRAPHITE, bold=True)
    textbox(c, "• Import status and safe errors\n• Knowledge/fault-card list\n• Review queue for cards needing review\n• Clear synthetic/demo-data labels", 718, 350, 170, 11, MUTED)
    rect(c, 718, 180, 160, 28, YELLOW, YELLOW); textbox(c, "SYNTHETIC DEMO DATA", 730, 189, 145, 8, GRAPHITE, bold=True)
    footer(c, "Screenshot source: docs/screenshots/t24-import-1280.png. It labels the sample data and photo provenance in-product.")
    c.showPage()

    page(c, "Evidence, not hype")
    rect(c, 55, 150, 390, 260, white, GREEN); rect(c, 515, 150, 390, 260, white, COPPER)
    textbox(c, "Recorded in docs/STATUS.md", 75, 375, 340, 16, GRAPHITE, bold=True)
    textbox(c, "• Dev API health and demo PWA shell are documented.\n• Local real Live checks recorded Hindi push-to-talk, captions, barge-in and reconnect behavior.\n• The partial import run is documented separately, not presented as the final score.", 75, 340, 340, 11, MUTED)
    textbox(c, "Final evidence placeholders", 535, 375, 340, 16, GRAPHITE, bold=True)
    textbox(c, "• 4G speech-to-reply p50\n• Photo-to-findings p50 and golden-photo result\n• Full import quality score\n• Quote round-trip and final phone-test results\n• Safety-bypass evidence", 535, 340, 340, 11, MUTED)
    footer(c, "Final numbers must be copied from the measured-quality table after T29 — never inferred from targets.")
    c.showPage()

    page(c, "Ready the evidence. Then let a judge try it.", dark=True)
    rect(c, 55, 145, 850, 245, BG, BG)
    textbox(c, "DEMO URL — [INSERT VERIFIED URL]\nVIDEO LINK — [INSERT PUBLIC/UNLISTED LINK]\nFINAL IMPORT SCORE — [INSERT T29 EVIDENCE]\nFINAL PHONE-TEST RESULTS — [INSERT VERIFIED EVIDENCE]\nTeam: Kaustubh Upadhyay — voice and agent · Samyak Jain — knowledge and commerce", 85, 345, 790, 18, GRAPHITE)
    footer(c, "Future of Work & Enterprise Productivity · Ustaad makes expert repair knowledge speakable, citable, and safer at the unit.", True)
    c.save()


if __name__ == "__main__":
    build()
