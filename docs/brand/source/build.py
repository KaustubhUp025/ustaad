"""Build the Ustaad 'service tag' logo kit: SVG masters, PNG icons, favicon, manifest bits."""
import math
import os
import shutil
import tempfile
from pathlib import Path
import cairosvg
from PIL import Image
from glyphs import text_path, centered

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(tempfile.mkdtemp(prefix="ustaad-brand-"))
SVG_DIR = ROOT / "docs/brand/svg"
PNG_DIR = ROOT / "docs/brand/png"
PUB = ROOT / "web/public"
for d in (SVG_DIR, PNG_DIR, f"{PUB}/brand"):
    os.makedirs(d, exist_ok=True)

# DESIGN.md palette
WHITE, GRAPHITE, GRAPHITE_DARK = "#EEF1EF", "#1D2327", "#182024"
YELLOW, COPPER = "#F6BE00", "#A9592D"
INK_MUTED_LIGHT, INK_MUTED_DARK, TILE_EDGE = "#4A555B", "#A9B4B9", "#3A464C"

TAG = ("M16 24H86A6 6 0 0 1 92 30V70A6 6 0 0 1 86 76H16A6 6 0 0 1 10 70V30A6 6 0 0 1 16 24Z"
       "M27 50A5 5 0 1 0 17 50A5 5 0 1 0 27 50Z")
TAG_SOLID = "M16 24H86A6 6 0 0 1 92 30V70A6 6 0 0 1 86 76H16A6 6 0 0 1 10 70V30A6 6 0 0 1 16 24Z"
CORD = "M22 53C12 44 8 28 16 12"
LETTER, _ = centered("deva800", "उ", 44, 59.5, 50.5)
ROT = "rotate(-6 50 50)"


def ink_bounds(cord=True):
    pts = [(x, y) for x in (10, 92) for y in (24, 76)]
    a = math.radians(-6)
    rot = [(50 + (x - 50) * math.cos(a) - (y - 50) * math.sin(a),
            50 + (x - 50) * math.sin(a) + (y - 50) * math.cos(a)) for x, y in pts]
    if cord:
        for t in [i / 20 for i in range(21)]:
            p0, p1, p2, p3 = (22, 53), (12, 44), (8, 28), (16, 12)
            x = (1-t)**3*p0[0] + 3*(1-t)**2*t*p1[0] + 3*(1-t)*t**2*p2[0] + t**3*p3[0]
            y = (1-t)**3*p0[1] + 3*(1-t)**2*t*p1[1] + 3*(1-t)*t**2*p2[1] + t**3*p3[1]
            rot += [(x - 1.5, y - 1.5), (x + 1.5, y + 1.5)]
    xs, ys = [p[0] for p in rot], [p[1] for p in rot]
    return min(xs), min(ys), max(xs), max(ys)


def mark(cord=True, letter=True, mono=None):
    """Inner SVG for the mark in its 100x100 box."""
    if mono:
        d = TAG + (LETTER if letter else "")
        out = f'<path d="{CORD}" fill="none" stroke="{mono}" stroke-width="3" stroke-linecap="round"/>' if cord else ""
        return out + f'<path transform="{ROT}" fill="{mono}" fill-rule="evenodd" d="{d}"/>'
    out = f'<path d="{CORD}" fill="none" stroke="{COPPER}" stroke-width="3" stroke-linecap="round"/>' if cord else ""
    out += f'<g transform="{ROT}"><path fill="{YELLOW}" fill-rule="evenodd" d="{TAG}"/>'
    if letter:
        out += f'<path fill="{GRAPHITE}" d="{LETTER}"/>'
    return out + "</g>"


def svg(inner, vb, w=None, h=None, title="Ustaad"):
    x, y, vw, vh = vb
    w = w or vw
    h = h or vh
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x:g} {y:g} {vw:g} {vh:g}" '
            f'width="{w:g}" height="{h:g}" role="img" aria-label="{title}"><title>{title}</title>{inner}</svg>\n')


def fmt(v):
    return float(f"{v:.2f}")


def tight_mark(cord=True, letter=True, mono=None, pad=2):
    b = ink_bounds(cord)
    vb = (fmt(b[0] - pad), fmt(b[1] - pad), fmt(b[2] - b[0] + 2 * pad), fmt(b[3] - b[1] + 2 * pad))
    return svg(mark(cord, letter, mono), vb)


def tile(inner_mark, rounded=True, full=False, scale=0.84, tx=8, ty=10):
    bg = (f'<rect width="100" height="100" fill="{GRAPHITE}"/>' if full else
          f'<rect x="1" y="1" width="98" height="98" rx="22" fill="{GRAPHITE}" stroke="{TILE_EDGE}" stroke-width="2"/>')
    return svg(bg + f'<g transform="translate({tx} {ty}) scale({scale})">{inner_mark}</g>', (0, 0, 100, 100))


# ---------- wordmark text ----------
def wordmark(x, cap_top, size, ink, sub_ink, align="start", cx=None):
    """'Ustaad' in Archivo + 'उस्ताद' in Noto Sans Devanagari under it. Returns (svg, bbox)."""
    _, b = text_path("archivo", "Ustaad", size, 0, 0)
    base = cap_top - b[1]
    w_lat = b[2] - b[0]
    hi_size = size * 0.46
    _, hb_ = text_path("deva500", "उस्ताद", hi_size, 0, 0)
    w_hi = hb_[2] - hb_[0]
    hi_top = base + size * 0.2
    hi_base = hi_top - hb_[1]
    if align == "middle":
        xl, xh = cx - w_lat / 2 - b[0], cx - w_hi / 2 - hb_[0]
    else:
        xl, xh = x - b[0], x - hb_[0]
    dl, bl = text_path("archivo", "Ustaad", size, xl, base)
    dh, bh = text_path("deva500", "उस्ताद", hi_size, xh, hi_base)
    out = f'<path fill="{ink}" d="{dl}"/><path fill="{sub_ink}" d="{dh}"/>'
    return out, (min(bl[0], bh[0]), min(bl[1], bh[1]), max(bl[2], bh[2]), max(bl[3], bh[3]))


def lockup(dark=False):
    ink, sub = (WHITE, INK_MUTED_DARK) if dark else (GRAPHITE, INK_MUTED_LIGHT)
    mb = ink_bounds(True)
    m_h = mb[3] - mb[1]
    text, tb = wordmark(mb[2] + 16, 0, 56, ink, sub)
    t_h = tb[3] - tb[1]
    dy = (mb[1] + m_h / 2) - (t_h / 2) - tb[1]
    inner = mark() + f'<g transform="translate(0 {dy:.2f})">{text}</g>'
    x0, y0 = mb[0], min(mb[1], tb[1] + dy)
    x1, y1 = tb[2], max(mb[3], tb[3] + dy)
    pad = 4
    return svg(inner, (fmt(x0 - pad), fmt(y0 - pad), fmt(x1 - x0 + 2 * pad), fmt(y1 - y0 + 2 * pad)))


def lockup_stacked(dark=False):
    ink, sub = (WHITE, INK_MUTED_DARK) if dark else (GRAPHITE, INK_MUTED_LIGHT)
    mb = ink_bounds(True)
    cx = (mb[0] + mb[2]) / 2
    text, tb = wordmark(0, mb[3] + 14, 44, ink, sub, align="middle", cx=cx)
    x0, y0 = min(mb[0], tb[0]), mb[1]
    x1, y1 = max(mb[2], tb[2]), tb[3]
    pad = 4
    return svg(mark() + text, (fmt(x0 - pad), fmt(y0 - pad), fmt(x1 - x0 + 2 * pad), fmt(y1 - y0 + 2 * pad)))


def wordmark_only(dark=False):
    ink, sub = (WHITE, INK_MUTED_DARK) if dark else (GRAPHITE, INK_MUTED_LIGHT)
    text, tb = wordmark(0, 0, 56, ink, sub)
    pad = 4
    return svg(text, (fmt(tb[0] - pad), fmt(tb[1] - pad), fmt(tb[2] - tb[0] + 2 * pad), fmt(tb[3] - tb[1] + 2 * pad)))


def banner(w, h):
    """GitHub social preview / Open Graph image."""
    s = h / 640
    big = 5.6 * s
    tx, ty = w - 92 * big + 40 * s, h / 2 - 50 * big
    inner = f'<rect width="{w}" height="{h}" fill="{GRAPHITE_DARK}"/>'
    inner += f'<g transform="translate({tx:.1f} {ty:.1f}) scale({big:.3f})">{mark()}</g>'
    left = 96 * s
    text, tb = wordmark(left, 150 * s, 104 * s, WHITE, INK_MUTED_DARK)
    inner += text
    y = tb[3] + 72 * s
    for line in ("The senior technician in every", "repair worker’s pocket."):
        d, _ = text_path("noto400", line, 40 * s, left, y)
        inner += f'<path fill="{WHITE}" d="{d}"/>'
        y += 56 * s
    d, _ = text_path("noto400", "Voice-first help for appliance technicians, in their own language", 24 * s, left, h - 72 * s)
    inner += f'<path fill="#8A969C" d="{d}"/>'
    return svg(inner, (0, 0, w, h))


files = {
    "ustaad-mark.svg": tight_mark(),
    "ustaad-mark-simple.svg": tight_mark(cord=False),
    "ustaad-mark-mono-graphite.svg": tight_mark(mono=GRAPHITE),
    "ustaad-mark-mono-white.svg": tight_mark(mono="#FFFFFF"),
    "ustaad-icon.svg": tile(mark()),
    "ustaad-icon-small.svg": tile(mark(cord=False), tx=5, ty=8, scale=0.9),
    "ustaad-icon-16.svg": tile(mark(cord=False, letter=False), tx=2, ty=5, scale=0.96),
    "ustaad-icon-maskable.svg": tile(mark(), full=True, scale=0.68, tx=16, ty=16),
    "ustaad-lockup-light.svg": lockup(False),
    "ustaad-lockup-dark.svg": lockup(True),
    "ustaad-lockup-stacked-light.svg": lockup_stacked(False),
    "ustaad-lockup-stacked-dark.svg": lockup_stacked(True),
    "ustaad-wordmark-light.svg": wordmark_only(False),
    "ustaad-wordmark-dark.svg": wordmark_only(True),
    "social-preview-1280x640.svg": banner(1280, 640),
    "og-image-1200x630.svg": banner(1200, 630),
}
for name, content in files.items():
    with open(f"{SVG_DIR}/{name}", "w") as f:
        f.write(content)


def png(svg_name, out, w, h=None, bg=None):
    cairosvg.svg2png(url=f"{SVG_DIR}/{svg_name}", write_to=out, output_width=w,
                     output_height=h or w, background_color=bg)


def png_w(svg_name, out, w):
    """Render keeping aspect ratio by width."""
    cairosvg.svg2png(url=f"{SVG_DIR}/{svg_name}", write_to=out, output_width=w)


# docs/brand/png
for size in (256, 512, 1024):
    png_w("ustaad-mark.svg", f"{PNG_DIR}/ustaad-mark-{size}.png", size)
png("ustaad-icon.svg", f"{PNG_DIR}/ustaad-icon-1024.png", 1024)
png("ustaad-icon-maskable.svg", f"{PNG_DIR}/github-avatar-500.png", 500)
for n in ("lockup-light", "lockup-dark", "lockup-stacked-light", "lockup-stacked-dark",
          "wordmark-light", "wordmark-dark"):
    png_w(f"ustaad-{n}.svg", f"{PNG_DIR}/ustaad-{n}.png", 1200)
png("social-preview-1280x640.svg", f"{PNG_DIR}/social-preview-1280x640.png", 1280, 640)
png("og-image-1200x630.svg", f"{PNG_DIR}/og-image-1200x630.png", 1200, 630)

# web/public (vite-plugin-pwa conventions)
shutil.copy(f"{SVG_DIR}/ustaad-icon-small.svg", f"{PUB}/favicon.svg")
png("ustaad-icon-maskable.svg", f"{PUB}/apple-touch-icon.png", 180)
png("ustaad-icon.svg", f"{PUB}/pwa-64x64.png", 64)
png("ustaad-icon.svg", f"{PUB}/pwa-192x192.png", 192)
png("ustaad-icon.svg", f"{PUB}/pwa-512x512.png", 512)
png("ustaad-icon-maskable.svg", f"{PUB}/maskable-icon-512x512.png", 512)
shutil.copy(f"{PNG_DIR}/og-image-1200x630.png", f"{PUB}/og-image.png")
for n in ("ustaad-mark.svg", "ustaad-mark-simple.svg", "ustaad-lockup-light.svg",
          "ustaad-lockup-dark.svg", "ustaad-lockup-stacked-light.svg", "ustaad-lockup-stacked-dark.svg"):
    shutil.copy(f"{SVG_DIR}/{n}", f"{PUB}/brand/{n}")

# favicon.ico: hand-tuned 16 px art, then the small tile at 32 and 48
tmp = {}
for size, src in ((16, "ustaad-icon-16.svg"), (32, "ustaad-icon-small.svg"), (48, "ustaad-icon-small.svg")):
    p = f"{OUT}/.ico-{size}.png"
    png(src, p, size)
    tmp[size] = Image.open(p).convert("RGBA")
tmp[48].save(f"{PUB}/favicon.ico", format="ICO", sizes=[(16, 16), (32, 32), (48, 48)],
             append_images=[tmp[16], tmp[32]])
for size in tmp:
    os.remove(f"{OUT}/.ico-{size}.png")
print("built", len(files), "svgs")
