"""her, at terminal resolution - in every way the film draws her.

`engine.me_pane` (full/engine.py:258) selects between three, and they are not
interchangeable:

  mode="h3"     **what the film actually shipped** (see below). Not a mode of
                `me_pane` at all: `h3_full.install()` (h3_full.py:230) rewrites it
                and forbids the other two outgoing routes outright.
  mode="half"   the steady state of the *unpatched* engine. `tuikit.halfblock`
                (tuikit.py:194) quantises the sprite's luminance into 8 levels at
                px-pixel resolution, cuts the cells apart with a grid mask and tints
                them through the film's own blue ramp (tuikit.TINTS["blue"]).
  mode="glyph"  the transition only - `me_pane` reaches for `glyph_sprite` when
                morph < 1.0, i.e. while she is scrambling in or out of the pane.

`h3_cells` is the first and is what `/dev/me` should use; `halfblock` and
`glyph_lines` are the other two, kept because they are the honest fallback if the
H3 takes are ever removed (`_standin.json` calls them stand-ins).

    from her_glyphs import h3_cells, glyph_lines, halfblock
    cells, w, h, ox, oy = h3_cells(35.0, 116, 31)
    lines, bright = glyph_lines("shy", "face", 30, 13)
    block, w, h = halfblock("cheerful", "face", 70, 27)
"""
from __future__ import annotations

import math
import sys
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parents[1]
EXPR_DIR = ROOT / "film" / "third_party_references" / "whale_maid_expanded_20260926" / "expressions"

# h3_full.install() (which the film's engine calls) monkey-patches PIL.Image.open so that
# reading a whale-*.webp raises - it exists to stop production code quietly falling back to
# the legacy sprite route. This module has a legitimate reason to read them, so it keeps the
# real open, and it warms the cache before the engine is installed.
_OPEN = Image.open

GLYPH_RAMP = " .:-=+*#%@"
# tuikit.py:CROPS - fractions of the sprite, as the film crops it
CROPS = {"full": None, "upper": (0.10, 0.0, 0.90, 0.47), "face": (0.20, 0.0, 0.78, 0.26),
         "bust": (0.16, 0.0, 0.84, 0.34)}
# a terminal cell is about 1:2.1, and so is a glyph cell in the film (6 x 12.65 px)
CELL_ASPECT = 2.1


@lru_cache(None)
def sprite(expr: str) -> Image.Image:
    return _OPEN(EXPR_DIR / f"whale-{expr}.webp").convert("RGBA")


def warm() -> None:
    """Read every expression once, before anything patches PIL.Image.open."""
    for e in EXPRESSIONS:
        sprite(e)


def _crop_box(im: Image.Image, crop: str) -> Image.Image:
    """The crop rectangle in the sprite, before any fitting."""
    spec = CROPS[crop]
    if spec is None:
        return im.crop(im.getchannel("A").getbbox())
    w, h = im.size
    a, b, c, e = spec
    return im.crop((int(w * a), int(h * b), int(w * c), int(h * e)))


@lru_cache(None)
def crop_aspect(crop: str) -> float:
    """The crop's own width/height. All eight expressions share one canvas, so one of them is
    enough to measure the fractions in CROPS against."""
    im = _crop_box(sprite("cheerful"), crop)
    return im.width / im.height


def pick_crop(cols: int, rows: int) -> str:
    """Which crop reads in a cols x rows pane: the one whose own shape is nearest the pane's.

    Forcing a tall crop into a wide pane does not show a small her, it shows a horizontal slice
    of her - a 116x13 pane is 4.2:1, so `face` (1.24:1) arrives as a band across her eyes. Asking
    which crop is closest in shape is the same question as which one arrives whole.
    """
    box = cols / max(1.0, rows * CELL_ASPECT)
    return min(CROPS, key=lambda c: abs(math.log(crop_aspect(c) / box)))


def fit(cols: int, rows: int, crop: str) -> tuple[int, int]:
    """The largest cell rect inside the pane that has the crop's own aspect.

    The film's glyph_grid fills its box because its box was cut to match; a terminal pane is
    whatever the window is, so the portrait is fitted inside it and centred instead.
    """
    a = crop_aspect(crop)
    uc = int(round(rows * CELL_ASPECT * a))
    ur = rows
    if uc > cols:                                # the crop is wider than the pane: fit the width
        uc, ur = cols, max(3, int(round(cols / (CELL_ASPECT * a))))
    return max(4, min(cols, uc)), max(3, min(rows, ur))


@lru_cache(None)
def cropped(expr: str, crop: str, target_aspect: float = 0.0) -> Image.Image:
    """The crop, then centre-cropped to the cell grid's aspect so nothing is stretched."""
    im = _crop_box(sprite(expr), crop)
    if target_aspect > 0:
        w, h = im.size
        if w / h > target_aspect:            # too wide: trim the sides
            nw = max(1, int(round(h * target_aspect)))
            x = (w - nw) // 2
            im = im.crop((x, 0, x + nw, h))
        else:                                # too tall: trim top and bottom, biased to the head
            nh = max(1, int(round(w / target_aspect)))
            y = int((h - nh) * 0.25)
            im = im.crop((0, y, w, y + nh))
    return im


@lru_cache(None)
def glyph_lines(expr: str, crop: str, cols: int, rows: int) -> tuple[tuple[str, ...], bytes]:
    """(text rows, per-cell brightness 0..255) - tuikit.py:glyph_grid, same maths."""
    aspect = cols / max(1, rows * CELL_ASPECT)
    small = cropped(expr, crop, aspect).resize((cols, rows), Image.LANCZOS)
    lum, alpha = small.convert("L"), small.getchannel("A")
    gx = lum.filter(ImageFilter.Kernel((3, 3), [-1, 0, 1, -2, 0, 2, -1, 0, 1], scale=4, offset=128))
    gy = lum.filter(ImageFilter.Kernel((3, 3), [-1, -2, -1, 0, 0, 0, 1, 2, 1], scale=4, offset=128))
    L, A, X, Y = lum.load(), alpha.load(), gx.load(), gy.load()
    bright = bytearray(cols * rows)
    lines = []
    for r in range(rows):
        row = []
        for c in range(cols):
            if A[c, r] < 110:
                row.append(" ")
                continue
            v = L[c, r] / 255
            ex, ey = (X[c, r] - 128) / 32, (Y[c, r] - 128) / 32
            if math.hypot(ex, ey) > 1.1:
                ang = (math.degrees(math.atan2(ey, ex)) + 180) % 180
                row.append("|" if ang < 22.5 or ang >= 157.5 else
                           "\\" if ang < 67.5 else "-" if ang < 112.5 else "/")
                bright[r * cols + c] = 255
            else:
                row.append(GLYPH_RAMP[min(len(GLYPH_RAMP) - 1, 1 + int(v * (len(GLYPH_RAMP) - 1)))])
                bright[r * cols + c] = int(255 * (0.35 + 0.65 * v))
        lines.append("".join(row))
    return tuple(lines), bytes(bright)


EXPRESSIONS = ["cheerful", "starry", "shy", "serious", "confused", "frightened", "angry", "exasperated"]

# ---------------------------------------------------------------- mode "half"

# tuikit.py:167 - TINTS, kept in the film's own order: (black, white, mid), the three arguments
# ImageOps.colorize takes. blue = (BLUE_LO, BLUE_HI, BLUE_MID); red has no mid.
TINT_BLUE = ((4, 8, 34), (196, 212, 255), (77, 107, 254))
TINT_RED = ((8, 6, 4), (255, 58, 40), None)
LEVELS = 8                                                   # tuikit.halfblock_lum's default
LEVEL_FLOOR = 0.16                                           # ...and its luminance floor


@lru_cache(None)
def tint_ramp(tint: str = "blue", levels: int = LEVELS) -> tuple[tuple[int, int, int], ...]:
    """The film's own `ImageOps.colorize(lum, black=lo, white=hi, mid=mid)`, sampled at `levels`.

    tuikit.py:171 `tint_colorize` is three lines long and calls PIL, so this calls PIL too rather
    than re-deriving its lookup table.
    """
    lo, hi, mid = TINT_BLUE if tint == "blue" else TINT_RED
    img = Image.new("L", (levels, 1))
    img.putdata([int(round(k / (levels - 1) * 255)) for k in range(levels)])
    rgb = ImageOps.colorize(img, black=lo, white=hi, mid=mid).convert("RGB")
    return tuple(rgb.getpixel((k, 0)) for k in range(levels))


@lru_cache(None)
def halfblock(expr: str, crop: str, cols: int, rows: int, levels: int = LEVELS):
    """tuikit.halfblock_lum at terminal resolution: two luminance samples per cell.

    Returns (block, w, h) where block[r][c] is (top, bottom) and each is a level index or None
    where the sprite is transparent. A cell is one half-block character: the top sample is the
    foreground and the bottom sample the background, so `▀` is a whole cell of two pixels.

    The film's px-pixel grid mask is left off: `banner_block` cuts its cells apart because it has
    to look like a terminal, and this is one.
    """
    a = crop_aspect(crop)
    ur = int(round(min(cols / a, rows * 2)))          # a half-block sample is ~square
    ur -= ur % 2
    uc = max(2, min(cols, int(round(ur * a))))
    small = _crop_box(sprite(expr), crop).resize((uc, ur), Image.LANCZOS)
    L, A = small.convert("L").load(), small.getchannel("A").load()

    def lv(c, r):
        # halfblock_lum: the ramp starts at 16 %, not at black, and alpha is cut at 100
        if A[c, r] <= 100:
            return None
        return int(round((LEVEL_FLOOR + (1 - LEVEL_FLOOR) * L[c, r] / 255) * (levels - 1)))

    block = tuple(tuple((lv(c, 2 * r), lv(c, 2 * r + 1)) for c in range(uc)) for r in range(ur // 2))
    return block, uc, ur // 2


# ------------------------------------------------------------ mode "h3" (the film's own)
#
# `h3_full.install()` does not merely offer another route, it forbids the old one: it sets
# `rig.frame = forbidden`, `dancer._stub_pose = forbidden`, and wraps `PIL.Image.open` so
# that reading any `whale-*.webp` raises "Forbidden legacy character file" (h3_full.py:290-303).
# What the film plays instead is `h3_full.frame_at(t)`: a 45x70 grid of `art` glyphs with a
# `shade` level per cell, spliced four frames deep across every seam in the PLAN table
# (h3_full.py:30-81). `dancer.draw` (dancer.py:174-215) then paints that grid - and a cell of
# it is a terminal cell, so this mode draws the film's cells as themselves instead of
# re-quantising her into half-blocks.

DSH = ROOT / "film" / "pv_dsh_frontend_20260927"
TUI = ROOT / "film" / "tui_pv_world_execute_20260926"
MMD = ROOT / "film" / "mmd_motion_eval_20260927"
H3_FPS = 24
H3_ROWS, H3_COLS = 45, 70


@lru_cache(None)
def _h3():
    """The film's own H3 module and the dancer that colours it, imported the way the film does.

    `dsh_her.install()` has already done this by the time the pane is drawn; doing it here too
    means `h3_cells` works on its own, and costs nothing when it has.
    """
    for p in (DSH / "gpu_shim", DSH, MMD):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    import pv_full                                            # puts continuity_full_v2 on sys.path
    if str(TUI / "full") not in sys.path:
        sys.path.insert(0, str(TUI / "full"))
    import h3_full
    import dancer
    del pv_full
    return h3_full, dancer


@lru_cache(None)
def _h3_ink() -> tuple[int, int, int, int]:
    """Rows/columns of the 45x70 grid that ever carry ink: (r0, r1, c0, c1).

    The takes are padded. Over the whole film the art only ever leaves rows 10-43 and columns
    17-55 non-blank; the rest is the empty margin the stand-in takes were traced with. Measured
    as the union over the film rather than the bounding box of one frame, because a per-frame
    box would make the pane jump about as she moves.
    """
    h3, _ = _h3()
    r0, r1, c0, c1 = 10 ** 9, -1, 10 ** 9, -1
    t = 0.0
    while t < 212.0:
        art = h3.frame_at(t).art
        for r, row in enumerate(art):
            for c, ch in enumerate(row):
                if ch != " ":
                    r0, r1 = min(r0, r), max(r1, r)
                    c0, c1 = min(c0, c), max(c1, c)
        t += 0.5
    return r0, r1, c0, c1


@lru_cache(256)
def _frame_cells(t: float, tint: str) -> tuple[tuple, ...]:
    """One H3 frame as `(char, fg, bg)` per cell - or None where the cell is empty.

    The eight lines that decide a cell are `dancer.draw`'s (dancer.py:198-214), and they are the
    film's numbers, not this module's: `shade` 1..7 is the glyph's brightness *and*, at 5 and
    above, a filled cell background; a `:` cell is her body and is filled with the lyric she is
    singing, flowing on at `dancer.flow_offset`. `_ramp` is literally the film's own
    `ImageOps.colorize` lookup, and `_text_at`/`flow_offset` are the film's own text functions,
    so nothing here is re-derived - only re-expressed as cells instead of PIL glyphs.
    """
    h3, dancer = _h3()
    fr = h3.frame_at(t)
    ramp, text = dancer._ramp(tint), dancer._text_at(t)
    n, off = len(text), dancer.flow_offset(t)
    out = []
    k = 0
    for r, art_row in enumerate(fr.art):
        shade_row = fr.shade[r]
        line = []
        for c, ch in enumerate(art_row):
            if ch == " ":
                line.append(None)
                continue
            sh = shade_row[c]
            lv = int(sh) if sh.isdigit() else 4
            if ch == ":":
                ch = text[(k + off) % n]
                k += 1
                gl = int(60 + lv * 26) if ch != "\u00b7" else int(40 + lv * 10)
            else:
                gl = min(255, int(110 + lv * 21))
            line.append((ch, ramp[gl], ramp[lv * 15] if lv >= 5 else None))
        out.append(tuple(line))
    return tuple(out)


@lru_cache(256)
def _h3_cells(t: float, cols: int, rows: int, tint: str):
    """`(cells, w, h, ox, oy)` - the film's sprite laid into a `cols` x `rows` pane.

    One film cell is one terminal cell, so she is never resampled: the ink box is 39 cells wide
    and 34 tall (`_h3_ink`) and that is what gets drawn. A terminal pane is usually *shorter*
    than 34 rows - 116x26 at 197x52 - and the film never had to answer for that: it hands her a
    360x548 px box for a 350x450 px sprite, so she always fits with room above her head.

    Two ways to fit her into a shorter pane were measured on the real art, and the first is wrong:

      * reduce by the smallest integer step that fits. The art is one cell wide per stroke, so
        taking every other row and column deletes half the outline and she arrives as scattered
        letters rather than as her - it is not a smaller her, it is a broken one.
      * crop. At 1:1 the pane simply shows less of her, which is what the film's own `upper` and
        `face` crops are for (tuikit.CROPS).

    So: crop. Vertically the top of the figure is kept (she loses her feet, not her face) and
    horizontally the cut is centred. When the pane is tall enough for all 34 rows she is placed
    bottom-aligned with the slack above her head, which is where `h3_full.glyph` composites her
    (`out.alpha_composite(im, ((width - im.width) // 2, height - im.height))`); the two rules
    meet at exactly 34 rows, so the pane does not jump as it grows.
    """
    r0, r1, c0, c1 = _h3_ink()
    sh, sw = r1 - r0 + 1, c1 - c0 + 1
    grid = _frame_cells(t, tint)
    keep_h, keep_w = min(sh, rows), min(sw, cols)
    x0 = c0 + max(0, (sw - keep_w) // 2)
    cells = [row[x0:x0 + keep_w] for row in grid[r0:r0 + keep_h]]
    return cells, keep_w, keep_h, max(0, (cols - keep_w) // 2), max(0, rows - keep_h)


def h3_cells(t: float, cols: int, rows: int, tint: str = "blue"):
    """As above, at the frame the film would be showing at `t` (h3_full.source rounds to 24 fps)."""
    if cols < 4 or rows < 3:
        return (), 0, 0, 0, 0
    return _h3_cells(round(max(0.0, min(211.9, t)) * H3_FPS) / H3_FPS, cols, rows, tint)


_h3_ok: bool | None = None


def h3_available() -> bool:
    """Whether the H3 takes are where `h3_full` expects them. Asked once, then remembered.

    `_standin.json` says these takes were machine-written stand-ins and invites the owner to delete
    one and drop their own in; `h3_full.grids` has no fallback, so a missing file raises. The pane
    asks first and falls back rather than dying on the frame where it first reaches for her.
    """
    global _h3_ok
    if _h3_ok is None:
        try:
            _h3_ink()
            _h3_ok = True
        except Exception:
            _h3_ok = False
    return _h3_ok


def warm_h3(cols: int = 116, rows: int = 26) -> bool:
    """Pay the H3 route's one-off costs during start-up, not on the first drawn frame.

    Two things are built lazily and neither is cheap: the ink-box sweep over the whole film, and
    `dancer._flow_table()` (dancer.py:84-96), which integrates the flow speed at each of the film's
    5,088 frames. Measured together at ~0.4 s, which is ten 24 fps frames - so it is warm-up work,
    not frame work. Returns False if the takes are not usable at all.
    """
    if not h3_available():
        return False
    try:
        h3_cells(0.0, cols, rows)
    except Exception:
        return False
    return True

