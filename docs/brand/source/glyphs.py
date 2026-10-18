"""Turn brand text into SVG path data (shaped with HarfBuzz, outlined with fontTools)."""
import io
import os
from pathlib import Path
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen

F = Path(os.environ["USTAAD_BRAND_FONTS"])
FONTS = {
    "deva800": F / "fontsource-noto-sans-devanagari-5.3.0/package/files/noto-sans-devanagari-devanagari-800-normal.woff2",
    "deva500": F / "fontsource-noto-sans-devanagari-5.3.0/package/files/noto-sans-devanagari-devanagari-500-normal.woff2",
    "noto400": F / "fontsource-noto-sans-5.3.0/package/files/noto-sans-latin-400-normal.woff2",
    "noto600": F / "fontsource-noto-sans-5.3.0/package/files/noto-sans-latin-600-normal.woff2",
    "archivo": F / "fontsource-variable-archivo-5.3.0/package/files/archivo-latin-wdth-normal.woff2",
}
_cache = {}


def load(key):
    if key in _cache:
        return _cache[key]
    f = TTFont(FONTS[key])
    if key == "archivo":
        f = instancer.instantiateVariableFont(f, {"wght": 800, "wdth": 88})
    f.flavor = None
    buf = io.BytesIO()
    f.save(buf)
    data = buf.getvalue()
    tt = TTFont(io.BytesIO(data))
    face = hb.Face(data)
    _cache[key] = (tt, hb.Font(face))
    return _cache[key]


def text_path(key, text, size, x=0.0, baseline=0.0, tracking=0.0):
    """Return (path_d, bbox) for text placed with its pen start at x and baseline y (SVG coords)."""
    tt, font = load(key)
    upm = tt["head"].unitsPerEm
    s = size / upm
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf, {})
    order = tt.getGlyphOrder()
    gs = tt.getGlyphSet()
    svg = SVGPathPen(gs)
    bounds = BoundsPen(gs)
    pen_x = 0.0
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        name = order[info.codepoint]
        ox = x + (pen_x + pos.x_offset) * s
        oy = baseline - pos.y_offset * s
        t = (s, 0, 0, -s, ox, oy)
        gs[name].draw(TransformPen(svg, t))
        gs[name].draw(TransformPen(bounds, t))
        pen_x += pos.x_advance + tracking * upm
    return svg.getCommands(), bounds.bounds  # bounds: (xMin, yMin, xMax, yMax) in SVG coords


def centered(key, text, size, cx, cy, tracking=0.0):
    """Path whose ink box is centred on (cx, cy)."""
    _, b = text_path(key, text, size, 0, 0, tracking)
    w, h = b[2] - b[0], b[3] - b[1]
    x = cx - w / 2 - b[0]
    y = cy - h / 2 - b[1]
    return text_path(key, text, size, x, y, tracking)
