"""Her as text: nine keyframes traced once from the sprites, posed every frame by string operations only.

  keyframe(pose)                        Frame loaded from poses/<pose>.txt
  frame(pose, flip, m, cols, rows)      Frame of cols x rows: the keyframe with her feet on the bottom row, centred
                                        on cols // 2, moved by the Motion
  trace(pose=None)                      (re)write poses/<pose>.txt from the sprites; offline, the only Pillow use

A Frame is three layers of equal size, lists of str, ' ' = empty:
  art    the drawing: structural glyphs on the outline and the features, ':' for plain interior cells (the glyph
         renderer fills those with lyric text)
  shade  brightness 0-7 per cell
  part   h head/face, w headdress, H long hair, a arm/hand, b body/apron, s skirt, m hem, t tail, f legs/shoes

Grid: one cell is 5 x 10 px on screen (Consolas Bold 9 px, 1:2). Every keyframe is KROWS x KCOLS at one scale: the
neutral figure is FIG_ROWS rows from the headdress to the shoe bottoms, feet on the last row, the body centre line
between columns KCOLS // 2 - 1 and KCOLS // 2, so switching pose never jumps.

Motion in cell units (ch / cw = 2, so a lean a at r rows above the feet moves that row by tan(a) * r * 2 columns):
  sway    row shift growing with the height above the feet        bend   extra shift growing with height^2
  hop     rows up by round(hop * 40), negative sinks               shift  columns by round(shift * 80)
  squash  a few rows dropped evenly between neck and feet, centre columns duplicated to widen
  head    rows above the neck (head, headdress, hair) sheared around the neck, 3 columns at the top at 8 deg
  hair    long-hair cells moved sideways up to 3 columns, most at the tips, behind the body; where the hair lay
          over the body, the body shows through
  hem     hem cells moved sideways up to 3 columns, most at the bottom row, over the legs
  tail    tail cells moved sideways up to 3 columns growing to the fluke, behind the skirt; the fluke rises or
          dips a row at the extremes
  turn    width squeezed to |cos(pi turn)| by dropping columns evenly around the centre; past 0.5 mirrored
All parameters act in screen space: + is right / clockwise whatever flip and turn are.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from operator import itemgetter
from pathlib import Path

from motion import POSES, Motion

POSE_DIR = Path(__file__).with_name("poses")
FIG_ROWS = 40              # headdress top to shoe bottoms
KROWS = FIG_ROWS + 2       # two rows above for the ahoge and starry's hand
KCOLS = 48
AXIS_COL = KCOLS // 2      # the centre line runs between AXIS_COL - 1 and AXIS_COL
MIRROR = str.maketrans("/\\()<>[]{}`'bdpq", "\\/)(><][}{'`dbqp")

# local moves, in cells
HEAD_TOP = 3               # head shift at the top row at head = 8 degrees, columns
SWING = 3                  # hair, hem and tail at +-1

# what a moved part may be drawn over (' ' = background): the tail goes behind everything, the long hair behind
# the body except where it lay over it, the hem over the legs, the head over the hair and the collar but behind a
# hand held up to the face
STAND_IN = "hwHabsmtf"     # body left behind by moving hair is tagged with its index here until the merge is done
COVER = {"head": " Hbs", "hair": " 012345678", "hem": " ft", "tail": " "}
_UNSTAND = str.maketrans({str(i): c for i, c in enumerate(STAND_IN)})


@dataclass
class Frame:
    art: list[str]
    shade: list[str]
    part: list[str]


# ---------------------------------------------------------------- keyframes

def _read(path: Path) -> Frame:
    layers, cur = {}, None
    for line in path.read_text(encoding="utf-8").split("\n"):
        if line.strip() in ("[art]", "[shade]", "[part]"):
            cur = layers.setdefault(line.strip()[1:-1], [])
        elif cur is not None and (line or len(cur) < KROWS):
            cur.append(line)
    out = [[(r + " " * KCOLS)[:KCOLS] for r in (layers[k] + [""] * KROWS)[:KROWS]] for k in ("art", "shade", "part")]
    return Frame(*out)


@lru_cache(None)
def keyframe(pose: str) -> Frame:
    return _read(POSE_DIR / f"{pose}.txt")


class _Key:
    """A keyframe prepared for frame(): per moving group and row, the cells that move (other cells blank), and every
    row with all moving cells blanked, so a local move is a slice, a pad and a short merge."""

    def __init__(self, pose: str, mirror: bool):
        k = keyframe(pose)
        art, shade, part = k.art, k.shade, k.part
        if mirror:
            art = [r[::-1].translate(MIRROR) for r in art]
            shade, part = [r[::-1] for r in shade], [r[::-1] for r in part]
        self.rows = (art, shade, part)
        rows_with = lambda tags: [r for r, p in enumerate(part) if any(c in tags for c in p)]  # noqa: E731
        head_rows = rows_with("hw")
        self.neck = max(head_rows) if head_rows else 0
        self.top = min(head_rows) if head_rows else 0
        hair_rows = [r for r in rows_with("H") if r > self.neck]
        self.hair_tip = max(hair_rows) if hair_rows else self.neck + 1
        hem_rows = rows_with("m")
        self.hem = (min(hem_rows), max(hem_rows)) if hem_rows else (KROWS, KROWS)
        tail_rows = rows_with("t")
        self.tail = (min(tail_rows), max(tail_rows)) if tail_rows else (KROWS, KROWS)
        # the fluke: the upper half of the tail, which rises or dips a row at the extremes; which way it points
        self.fluke_low = (self.tail[0] + self.tail[1]) // 2
        tcols = [c for r in tail_rows for c, p in enumerate(part[r]) if p == "t"]
        self.fluke_side = 1 if tcols and sum(tcols) / len(tcols) >= AXIS_COL else -1

        groups = {"head": lambda r, p: r <= self.neck and p in "hwH", "hair": lambda r, p: r > self.neck and p == "H",
                  "hem": lambda r, p: p == "m", "tail": lambda r, p: p == "t"}
        self.moving = {g: {} for g in groups}
        self.blank = []
        for r in range(KROWS):
            tags = [next((g for g, f in groups.items() if f(r, p)), None) for p in part[r]]
            a, s, p = ([" " if g else ch for ch, g in zip(layer[r], tags)] for layer in (art, shade, part))
            # long hair lying over the body leaves body behind: a vacated hair cell with body on both sides of it
            # in the row gets the nearest body cell's shade and part (as a stand-in digit, so the hair still
            # covers it, see _local)
            body = [c for c, g in enumerate(tags) if g is None and p[c] != " "]
            for c, g in enumerate(tags):
                if g == "hair" and body and body[0] < c < body[-1]:
                    n = min(body, key=lambda b: abs(b - c))
                    a[c], s[c], p[c] = ":", s[n], str(STAND_IN.index(p[n]))
            self.blank.append(("".join(a), "".join(s), "".join(p)))
            for g in groups:
                cols = [c for c, t in enumerate(tags) if t == g]
                if cols:
                    cells = tuple("".join(ch if t == g else " " for ch, t in zip(layer[r], tags))
                                  for layer in (art, shade, part))
                    self.moving[g][r] = (cells, cols[0], cols[-1] + 1)


@lru_cache(None)
def _key(pose: str, mirror: bool) -> _Key:
    return _Key(pose, mirror)


def _paste(row: list, cells: tuple, lo: int, hi: int, d: int, cover: str) -> None:
    """Merge the moving cells (columns lo..hi, shifted by d) into row = [art, shade, part] where the cell under
    them is one of `cover`."""
    a, s, p = row
    lo2, hi2 = max(0, lo + d), min(KCOLS, hi + d)
    if lo2 >= hi2:
        return
    ma, ms, mp = cells
    na, ns, np_ = list(a[lo2:hi2]), list(s[lo2:hi2]), list(p[lo2:hi2])
    for i in range(lo2, hi2):
        if ma[i - d] != " " and p[i] in cover:
            k = i - lo2
            na[k], ns[k], np_[k] = ma[i - d], ms[i - d], mp[i - d]
    row[0] = a[:lo2] + "".join(na) + a[hi2:]
    row[1] = s[:lo2] + "".join(ns) + s[hi2:]
    row[2] = p[:lo2] + "".join(np_) + p[hi2:]


def _local(K: _Key, m: Motion) -> tuple[list[str], list[str], list[str]]:
    """The keyframe rows with the head, hair, hem and tail moved: start from the rows with every moving cell
    blanked and paste the groups back shifted, the ones behind first."""
    grid = [list(b) for b in K.blank]
    moves = K.moving
    t0, t1 = K.tail
    for r, (cells, lo, hi) in moves["tail"].items():
        f = (t1 - r) / max(1, t1 - t0)                      # 0 at the base, 1 at the top of the fluke
        d = round(m.tail * SWING * (0.3 + 0.7 * f))
        dr = 0
        if abs(m.tail) > 0.66 and r <= K.fluke_low:
            dr = (1 if m.tail > 0 else -1) * K.fluke_side   # clockwise dips a fluke that points right
            if dr < 0 and r == K.fluke_low:                 # a rising fluke stays joined to the stem
                _paste(grid[r], cells, lo, hi, d, COVER["tail"])
        if 0 <= r + dr < KROWS:
            _paste(grid[r + dr], cells, lo, hi, d, COVER["tail"])
    span = max(1, K.hair_tip - K.neck - 2)                  # the two rows under the neck stay at the root
    for r, (cells, lo, hi) in moves["hair"].items():
        f = min(1.0, max(0.0, (r - K.neck - 2) / span))
        _paste(grid[r], cells, lo, hi, round(m.hair * SWING * f ** 1.5), COVER["hair"])
    h0, h1 = K.hem
    for r, (cells, lo, hi) in moves["hem"].items():
        _paste(grid[r], cells, lo, hi, round(m.hem * SWING * (r - h0 + 0.5) / (h1 - h0 + 0.5)), COVER["hem"])
    lean = HEAD_TOP * math.tan(math.radians(m.head)) / math.tan(math.radians(8)) / max(1, K.neck - K.top + 0.5)
    for r, (cells, lo, hi) in moves["head"].items():
        d = max(-HEAD_TOP - 1, min(HEAD_TOP + 1, round(lean * (K.neck - r + 0.5))))
        _paste(grid[r], cells, lo, hi, d, COVER["head"])
    return [g[0] for g in grid], [g[1] for g in grid], [g[2].translate(_UNSTAND) for g in grid]


def frame(pose: str, flip: bool, m: Motion | None, cols: int, rows: int) -> Frame:
    """Her in `pose` (mirrored if flip) moved by m on a cols x rows grid, feet on the bottom row."""
    m = m or Motion()
    turn = min(1.0, max(0.0, m.turn))
    K = _key(pose, flip != (turn > 0.5))
    if m.head or m.hair or m.hem or m.tail:
        art, shade, part = _local(K, m)
    else:
        art, shade, part = K.rows
    width, axis, ground = KCOLS, float(AXIS_COL), KROWS - 1

    # turn: keep columns evenly around the centre
    k = abs(math.cos(math.pi * turn))
    if k < 0.999:
        n = max(1, round(KCOLS * k))
        keep = [min(KCOLS - 1, max(0, int(AXIS_COL + (j + 0.5 - n / 2) / max(k, 1e-3)))) for j in range(n)]
        get = itemgetter(*keep) if n > 1 else (lambda s: (s[keep[0]],))
        art, shade, part = (["".join(get(r)) for r in layer] for layer in (art, shade, part))
        width, axis = n, n / 2

    # squash: drop rows evenly between the neck and the feet, duplicate the centre columns
    if m.squash > 0:
        drop = round(m.squash * 0.08 * FIG_ROWS)
        lo, hi = K.neck + 1, ground - 1
        gone = {round(lo + (i + 1) * (hi - lo) / (drop + 1)) for i in range(drop)} if hi > lo else set()
        art, shade, part = ([r for i, r in enumerate(layer) if i not in gone] for layer in (art, shade, part))
        ground -= len(gone)
        ins = round(m.squash * 0.05 * width)
        if ins:
            c, a0 = int(axis), ins // 2
            art, shade, part = ([r[:c] + r[c - a0:c - a0 + ins] + r[c:] for r in layer] for layer in (art, shade, part))
            width, axis = width + ins, axis + ins / 2

    # place: feet on the bottom row (minus hop), centre on cols // 2, each row leaning with sway and bend
    hop = round(m.hop * FIG_ROWS)
    x0 = cols // 2 - round(axis) + round(m.shift * FIG_ROWS * 2)
    ts, tb = 2.0 * math.tan(math.radians(m.sway)), 2.0 * math.tan(math.radians(m.bend)) / FIG_ROWS
    blank = " " * cols
    out = ([blank] * rows, [blank] * rows, [blank] * rows)
    for r in range(len(art)):
        y = rows - 1 - (ground - r) - hop
        if not 0 <= y < rows:
            continue
        h = ground - r
        x = x0 + round(ts * h + tb * h * h)
        for layer, src in zip(out, (art[r], shade[r], part[r])):
            layer[y] = ((" " * x + src) if x >= 0 else src[-x:])[:cols].ljust(cols)
    return Frame(*out)


# ---------------------------------------------------------------- tracing (offline: the only image work)

SRC = Path(__file__).resolve().parents[2].joinpath("third_party_references/whale_maid_expanded_20260926")
CANVAS = (935, 1682)       # the shared sprite canvas
GROUND = 1672              # shoe bottoms after alignment (median of the nine)
TOP = 30                   # headdress top
AXIS = 458                 # body centre line (heads and feet centre within ~15 px of it in every pose)
RH = (GROUND - TOP) / FIG_ROWS
CW = RH / 2
SX, SY = 6, 12             # samples per cell while tracing
WAIST = 630                # apron sash: below it the dark cloth is skirt, above it sleeves and bodice

# Per pose, in the sprite's own canvas pixels (read off the images):
#   foot   lowest shoe pixel; the pose moves down by GROUND - foot (the heads already line up as drawn)
#   neck   where the chin meets the collar; head = ellipse (hx, neck - 150) with half-width hr, half-height 300,
#          cut at the neck line
#   hem    bottom of the skirt frill at the centre; the hem part is the lowest quarter of the skirt
#   tail   (base, fluke box, stem radius): the base is where it comes out from behind the skirt, the box holds the
#          fluke and stops short of the skirt beside it (cheerful shows one lobe above the lifted skirt)
#   face   eyes and mouth: (x, y, glyph)
FIT = {
    "cheerful": dict(foot=1657, neck=(450, 335), head=(445, 200), hem=1465,
                     tail=((905, 960), (879, 818, 935, 915), 25),
                     face=[(415, 246, "^"), (503, 231, "^"), (457, 292, "v")]),
    "shy": dict(foot=1672, neck=(455, 340), head=(455, 215), hem=1478,
                tail=((790, 1085), (720, 812, 932, 978), 50),
                face=[(418, 265, "o"), (487, 238, "o"), (445, 313, "-")]),
    "serious": dict(foot=1666, neck=(478, 338), head=(475, 215), hem=1462,
                    tail=((768, 1060), (677, 788, 915, 968), 50),
                    face=[(417, 231, "o"), (502, 223, "o"), (455, 273, "o")]),
    "confused": dict(foot=1673, neck=(470, 340), head=(465, 215), hem=1487,
                     tail=((800, 1095), (707, 782, 932, 965), 50),
                     face=[(441, 231, "o"), (522, 200, "o"), (465, 269, "~")]),
    "angry": dict(foot=1670, neck=(455, 352), head=(455, 225), hem=1467,
                  tail=((795, 960), (710, 712, 930, 885), 50),
                  face=[(405, 262, "o"), (491, 258, "o"), (405, 222, "\\"), (491, 218, "/"), (458, 323, "O")]),
    "frightened": dict(foot=1638, neck=(478, 345), head=(470, 215), hem=1447,
                       tail=((785, 1095), (682, 772, 933, 968), 50),
                       face=[(405, 242, "O"), (478, 231, "O"), (463, 308, "~")]),
    "exasperated": dict(foot=1676, neck=(465, 340), head=(460, 215), hem=1495,
                        tail=((790, 1085), (700, 795, 928, 972), 50),
                        face=[(422, 223, "-"), (511, 208, "-"), (476, 265, "_")]),
    "starry": dict(foot=1682, neck=(505, 345), head=(530, 150), hem=1508,
                   tail=((800, 1105), (693, 783, 924, 982), 50),
                   face=[(452, 258, "@"), (537, 227, "@"), (498, 315, "v")]),
    "skirt": dict(foot=1678, neck=(462, 338), head=(458, 215), hem=1487,
                  tail=((792, 1115), (702, 803, 936, 985), 50),
                  face=[(402, 246, "o"), (486, 219, "o"), (459, 300, "v")]),
}
assert set(FIT) == set(POSES)


def _sprite(pose: str):
    from PIL import Image
    if pose == "skirt":
        return Image.open(SRC / "maid-left.webp").convert("RGBA").resize(CANVAS, Image.LANCZOS)
    return Image.open(SRC / "expressions" / f"whale-{pose}.webp").convert("RGBA").crop((0, 0) + CANVAS)


def _pixels(im) -> list:
    return list(im.get_flattened_data() if hasattr(im, "get_flattened_data") else im.getdata())


def _samples(pose: str):
    """The pose resampled to SX x SY samples per cell over the keyframe grid (aligned: its feet on the last row),
    with the mappings sample -> sprite pixel and sprite pixel -> sample."""
    from PIL import Image
    fit = FIT[pose]
    dy = GROUND - fit["foot"]
    x0, x1 = AXIS - AXIS_COL * CW, AXIS + (KCOLS - AXIS_COL) * CW
    y0, y1 = GROUND - KROWS * RH - dy, GROUND - dy          # in the sprite's own coordinates
    pad = 200
    big = Image.new("RGBA", (CANVAS[0] + 2 * pad, CANVAS[1] + 2 * pad), (0, 0, 0, 0))
    big.paste(_sprite(pose), (pad, pad))
    img = big.resize((KCOLS * SX, KROWS * SY), Image.LANCZOS, box=(x0 + pad, y0 + pad, x1 + pad, y1 + pad))
    sx, sy = (x1 - x0) / (KCOLS * SX), (y1 - y0) / (KROWS * SY)
    to_src = lambda gx, gy: (x0 + (gx + 0.5) * sx, y0 + (gy + 0.5) * sy)  # noqa: E731
    to_grid = lambda x, y: ((x - x0) / sx, (y - y0) / sy)  # noqa: E731
    return img, to_src, to_grid


def _tail_mask(pose: str, img, to_grid):
    """Samples of the tail: connected to the stem inside a capsule from 20% up the stem to the fluke box, found on
    the eroded silhouette so thin anti-aliased bridges to the skirt do not count, then regrown 2 samples."""
    from PIL import Image, ImageChops, ImageDraw, ImageFilter
    (bx, by), (kx0, ky0, kx1, ky1), sr = FIT[pose]["tail"]
    b0 = to_grid(bx, by)
    f0, f1 = to_grid(kx0, ky0), to_grid(kx1, ky1)
    b1 = ((f0[0] + f1[0]) / 2, (f0[1] + f1[1]) / 2)
    ln = math.hypot(b1[0] - b0[0], b1[1] - b0[1])
    ux, uy = (b1[0] - b0[0]) / ln, (b1[1] - b0[1]) / ln
    r = sr / (CW / SX)
    c0 = (b0[0] + ux * 0.2 * ln, b0[1] + uy * 0.2 * ln)
    cap = Image.new("L", img.size, 0)
    d = ImageDraw.Draw(cap)
    d.polygon([(c0[0] - uy * r, c0[1] + ux * r), (c0[0] + uy * r, c0[1] - ux * r),
               (b1[0] + uy * r, b1[1] - ux * r), (b1[0] - uy * r, b1[1] + ux * r)], fill=255)
    d.rectangle([f0[0], f0[1], f1[0], f1[1]], fill=255)
    alpha = img.getchannel("A")
    solid = ImageChops.multiply(alpha.point(lambda v: 255 if v > 60 else 0), cap).filter(ImageFilter.MinFilter(3))
    seeds = [(round(b0[0] + ux * t * ln), round(b0[1] + uy * t * ln)) for t in (0.5, 0.6, 0.7, 0.4, 0.8)]
    seed = next((p for p in seeds if 0 <= p[0] < img.width and 0 <= p[1] < img.height and solid.getpixel(p)), None)
    if seed is None:
        return set()
    ImageDraw.floodfill(solid, seed, 128)
    tail = solid.point(lambda v: 255 if v == 128 else 0)
    inside = ImageChops.multiply(alpha.point(lambda v: 255 if v > 8 else 0), cap)
    for _ in range(2):
        tail = ImageChops.multiply(tail.filter(ImageFilter.MaxFilter(3)), inside)
    return {i for i, v in enumerate(_pixels(tail)) if v}


def _classify(pose: str, img, to_src, tail: set) -> list[str]:
    """Part letter per sample ('' where empty)."""
    fit = FIT[pose]
    (nx, ny), (hx, hr) = fit["neck"], fit["head"]
    hem = fit["hem"]
    hem_top = hem - 0.25 * (hem - WAIST)
    w = img.width
    rgba = _pixels(img)
    hsv = _pixels(img.convert("RGB").convert("HSV"))
    out = []
    for i, ((r, g, b, a), (hh, ss, vv)) in enumerate(zip(rgba, hsv)):
        if a < 100:
            out.append("")
            continue
        x, y = to_src(i % w, i // w)
        blue = 110 <= hh <= 195 and ss > 60
        white = ss < 45 and vv > 170
        skin = (hh < 30 or hh > 235) and 25 < ss < 150 and vv > 150
        ex, ey = (x - hx) / hr, (y - (ny - 150)) / 300
        if i in tail:
            out.append("t")
        elif ex * ex + ey * ey < 1 and y < ny + 10:
            out.append("w" if white and y < ny - 190 else "h")
        elif blue and vv > 100 and y < 900:
            out.append("H")
        elif skin:
            out.append("a")
        elif y >= hem - 5:
            out.append("f")
        elif y >= hem_top:
            out.append("m")
        elif y >= WAIST:
            out.append("b" if white else "s")
        elif abs(x - nx) > (120 if y > ny + 60 else 100):  # sleeves beside the torso, or raised beside the head
            out.append("a")
        else:
            out.append("b")
    return out


def _tensor(vals: list[float], w: int, x0: int, y0: int, grow: int = 0) -> tuple[float, float, float, float]:
    """Structure tensor of one cell's samples (grown by `grow` samples into the neighbours): (strength, coherence,
    screen angle of the edge line 0..180, centroid row of the edge 0..1)."""
    h = len(vals) // w
    jxx = jyy = jxy = m = my = 0.0
    for yy in range(max(1, y0 + 1 - grow), min(h - 1, y0 + SY - 1 + grow)):
        for xx in range(max(1, x0 + 1 - grow), min(w - 1, x0 + SX - 1 + grow)):
            gx = vals[yy * w + xx + 1] - vals[yy * w + xx - 1]
            gy = vals[(yy + 1) * w + xx] - vals[(yy - 1) * w + xx]
            jxx += gx * gx
            jyy += gy * gy
            jxy += gx * gy
            g = abs(gx) + abs(gy)
            m += g
            my += g * (yy - y0)
    tr = jxx + jyy
    if tr <= 1e-9:
        return 0.0, 0.0, 0.0, 0.5
    coh = math.sqrt((jxx - jyy) ** 2 + 4 * jxy * jxy) / tr
    theta = 0.5 * math.atan2(2 * jxy, jxx - jyy)            # gradient direction, image coords (y down)
    line = (-(math.degrees(theta) + 90.0)) % 180.0           # edge line, screen coords (y up)
    return tr / ((SX - 2) * (SY - 2)), coh, line, (my / m) / SY if m else 0.5


def _line_glyph(angle: float, cy: float, side: int) -> str:
    """Glyph for an edge line at `angle` (0 horizontal, 90 vertical, screen), edge centroid cy (0 top .. 1 bottom),
    side = +1 if the figure lies to the right of a vertical outline, -1 to the left, 0 inside."""
    if angle < 24 or angle >= 156:
        return "_" if cy > 0.62 else "-"
    if angle < 72:
        return "/"
    if angle < 108:
        return "(" if side > 0 else ")" if side < 0 else "|"
    return "\\"


def trace(pose: str | None = None) -> None:
    """Write poses/<pose>.txt (all nine if pose is None) from the sprites."""
    for p in ([pose] if pose else list(POSES)):
        _write(p, _trace(p))


def _colour_class(rgba, hsv) -> int:
    """0 empty, 1 dark (dress, sleeves, shoes, tail), 2 blue (hair, underskirt), 3 skin, 4 white (apron, lace)"""
    (r, g, b, a), (hh, ss, vv) = rgba, hsv
    if a < 100:
        return 0
    if (hh < 30 or hh > 235) and 20 < ss < 160 and vv > 145:
        return 3
    if ss < 55:
        return 4 if vv > 130 else 1
    if vv < 105:
        return 1
    return 2


def _trace(pose: str) -> Frame:
    img, to_src, to_grid = _samples(pose)
    w = img.width
    tail = _tail_mask(pose, img, to_grid)
    parts = _classify(pose, img, to_src, tail)
    rgba = _pixels(img)
    cls = [_colour_class(p, q) for p, q in zip(rgba, _pixels(img.convert("RGB").convert("HSV")))]
    alpha = [a / 255 for (_, _, _, a) in rgba]
    lum = [(0.3 * r + 0.59 * g + 0.11 * b) / 255 if a > 20 else 0.0 for (r, g, b, a) in rgba]

    # per cell: coverage, part, shade, colour classes
    part, shade, classes = {}, {}, {}
    for row in range(KROWS):
        for col in range(KCOLS):
            idx = [(row * SY + j) * w + col * SX + i for j in range(SY) for i in range(SX)]
            c = sum(alpha[k] for k in idx) / len(idx)
            ps = [parts[k] for k in idx if parts[k]]
            if c < 0.42 or not ps:
                continue
            counts = {}
            for q in ps:
                counts[q] = counts.get(q, 0) + 1
            best = max(counts, key=counts.get)
            for q in "thw":  # thin features win with a third of the cell
                if counts.get(q, 0) * 3 >= len(ps) and best not in "thw":
                    best = q
            part[row, col] = best
            lv = sum(lum[k] * alpha[k] for k in idx) / max(1e-6, sum(alpha[k] for k in idx))
            shade[row, col] = min(7, max(0, round(7 * lv ** 0.9)))
            cc = {}
            for k in idx:
                if cls[k]:
                    cc[cls[k]] = cc.get(cls[k], 0) + 1
            classes[row, col] = sorted(((n / len(idx), q) for q, n in cc.items()), reverse=True)
    # drop wisps: cells with at most two filled neighbours
    for cell in [c for c in part if sum((c[0] + dr, c[1] + dc) in part for dr in (-1, 0, 1) for dc in (-1, 0, 1)) <= 3]:
        del part[cell], shade[cell], classes[cell]

    # the face: between the eyes and the mouth only the traced features are drawn
    face = [(int(gy // SY), int(gx // SX), g) for gx, gy, g in
            ((*to_grid(fx, fy), g) for fx, fy, g in FIT[pose]["face"])]
    fr0, fr1 = min(f[0] for f in face), max(f[0] for f in face)
    fc0, fc1 = min(f[1] for f in face) - 1, max(f[1] for f in face) + 1

    # glyphs: outline cells follow the silhouette; inner cells where two colour regions meet (apron and dress,
    # face and hair, cuffs, collar, skirt panels) follow that boundary; the rest is ':'
    art, indicator = {}, {}
    for (row, col) in part:
        x0, y0 = col * SX, row * SY
        edge = any((row + dr, col + dc) not in part for dr, dc in ((0, 1), (0, -1), (1, 0), (-1, 0)))
        if edge:
            st, coh, ang, cy = _tensor(alpha, w, x0, y0)
            if st < 0.004 or coh < 0.25:
                art[row, col] = "." if cy > 0.5 else "'"
                continue
            left = sum(alpha[(y0 + j) * w + x0 + i] for j in range(SY) for i in range(SX // 2))
            right = sum(alpha[(y0 + j) * w + x0 + i] for j in range(SY) for i in range(SX // 2, SX))
            art[row, col] = _line_glyph(ang, cy, 1 if right > left else -1)
            continue
        if fr0 <= row <= fr1 and fc0 <= col <= fc1:
            art[row, col] = ":"
            continue
        cl = classes[row, col]
        top = cl[0][1]
        mixed = len(cl) >= 2 and cl[1][0] >= 0.28
        # a brighter region carries the line where it meets a darker one on the next cell
        meets = any(0 < classes[n][0][1] < top for n in ((row + dr, col + dc) for dr, dc in
                                                          ((0, 1), (0, -1), (1, 0), (-1, 0))) if n in classes)
        if mixed or meets:
            ind = indicator.setdefault(top, [1.0 if q == top else 0.0 for q in cls])
            st, coh, ang, cy = _tensor(ind, w, x0, y0, 0 if mixed else SX // 2)
            art[row, col] = _line_glyph(ang, cy, 0) if coh > 0.45 and st > 0.002 else ":"
        else:
            art[row, col] = ":"
    for row, col, g in face:
        if (row, col) in part:
            art[row, col] = g

    grid = lambda d: ["".join(d.get((r, c), " ") for c in range(KCOLS)) for r in range(KROWS)]  # noqa: E731
    return Frame(grid(art), ["".join(str(shade[r, c]) if (r, c) in shade else " " for c in range(KCOLS))
                             for r in range(KROWS)], grid(part))


def _write(pose: str, f: Frame) -> None:
    POSE_DIR.mkdir(exist_ok=True)
    text = "\n".join(["[art]"] + f.art + ["[shade]"] + f.shade + ["[part]"] + f.part) + "\n"
    (POSE_DIR / f"{pose}.txt").write_text(text, encoding="utf-8")
    keyframe.cache_clear()
    _key.cache_clear()
