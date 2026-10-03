"""Her as dynamic strings.

She is a character grid, and every move is a string operation. The nine poses are text keyframes (poses/*.txt,
traced once from the pose illustrations); every frame the choreography (choreo.at) picks a pose and a Motion,
and the rig (rig.frame) shifts, drops, mirrors and splices rows and parts of rows to pose her. This module draws
that grid:

  art        outline and feature glyphs as traced; `:` cells are her body, filled with the lyric she is singing
             (the current line and the next ones, in reading order) and flowing on at choreo's flow speed
  shade      the brightness level of every cell: glyph colour, plus a dim cell background like a terminal's
  morph      a pose change flips the cells from the old keyframe to the new one in a random order, each cell
             scrambling for a moment
  scramble   glitch parts: random symbols and torn rows

Shots that pin an overlay onto her keep the old half-block portrait (the overlay is placed on it), with the lyric
streaming through it (strings()).
"""

from __future__ import annotations

import math
import random
from functools import lru_cache

from PIL import Image, ImageChops, ImageDraw

from engine import FPS, LYRICS, SONG_LEN
from motion import Motion, Step
from tuikit import BLUE_HI, F_MONO_B, TINTS, font, grid_mask, tint_colorize

FS = 9                       # glyph size
CPS = 7.0                    # characters per second at flow 1
UNDER = 0.5                  # brightness of the half-block body under the strings
SCRAMBLE = "#%&@$*+=<>/\\|?!01"


@lru_cache(None)
def _cell() -> tuple[int, int]:
    f = font(F_MONO_B, FS)
    return max(4, int(math.ceil(f.getlength("M")))), FS + 1


@lru_cache(4096)
def _glyph(ch: str) -> Image.Image:
    cw, chh = _cell()
    m = Image.new("L", (cw, chh), 0)
    ImageDraw.Draw(m).text((0, -1), ch, font=font(F_MONO_B, FS), fill=255)
    return m


@lru_cache(None)
def _ramp(tint: str) -> list[tuple[int, int, int]]:
    lo, hi, mid = TINTS[tint]
    lum = Image.new("L", (256, 1))
    lum.putdata(list(range(256)))
    return list(tint_colorize(lum, tint).getdata())


def _premul_resize(img: Image.Image, size) -> Image.Image:
    return img.convert("RGBa").resize(size, Image.BOX).convert("RGBA")


def underlay(img: Image.Image, px: int, tint: str, level: float) -> Image.Image:
    """The body at half-block resolution (px squares), dimmed to `level`."""
    cols, rows = max(1, img.width // px), max(2, img.height // px)
    small = _premul_resize(img, (cols, rows))
    lum = small.convert("L").point(lambda v: int(round((0.16 + 0.84 * v / 255) * 7)) * 36)
    alpha = small.getchannel("A").point(lambda a: int(255 * level) if a > 100 else 0)
    size = (cols * px, rows * px)
    rgb = tint_colorize(lum.resize(size, Image.NEAREST), tint).convert("RGBA")
    rgb.putalpha(ImageChops.multiply(alpha.resize(size, Image.NEAREST), grid_mask(size[0], size[1], px)))
    return rgb


def _text_at(t: float) -> str:
    """The line being sung and the ones after it (the last line before, in the gaps)."""
    i = next((k for k, (a, b, s) in enumerate(LYRICS) if a <= t < b), None)
    if i is None:
        i = max([k for k, (a, b, s) in enumerate(LYRICS) if a <= t] or [0])
    txt = " / ".join(s for _, _, s in LYRICS[i:i + 4] if s.strip()) or "world.execute(me);"
    return txt.replace(" ", "·") + "·//·"


@lru_cache(None)
def _flow_table() -> list[float]:
    """Cumulative text offset (in characters) at every video frame, integrating choreo's flow speed."""
    try:
        import choreo
        speed = lambda t: choreo.at(t).flow  # noqa: E731
    except ImportError:
        speed = lambda t: 1.0  # noqa: E731
    out, acc = [], 0.0
    for i in range(int(SONG_LEN * FPS) + 2):
        out.append(acc)
        acc += CPS * speed(i / FPS) / FPS
    return out


def flow_offset(t: float) -> int:
    tb = _flow_table()
    return int(tb[max(0, min(len(tb) - 1, int(t * FPS)))])


def _grid(img: Image.Image, cols: int, rows: int):
    small = _premul_resize(img, (cols, rows))
    return list(small.getchannel("A").getdata()), list(small.convert("L").getdata())


def strings(img: Image.Image, t: float, tint: str = "blue", prev: Image.Image | None = None, morph: float = 1.0,
            scramble: float = 0.0, offset: int | None = None, seed: int = 0) -> Image.Image:
    """The glyph layer for a posed image (and, during a pose change, the pose it comes from)."""
    cw, chh = _cell()
    cols, rows = img.width // cw, img.height // chh
    alpha, lum = _grid(img, cols, rows)
    if prev is not None and morph < 1.0:
        alpha_p, lum_p = _grid(prev, cols, rows)
    else:
        prev = None
    ramp = _ramp(tint)
    text = _text_at(t)
    n = len(text)
    off = flow_offset(t) if offset is None else offset
    rnd = random.Random(seed)
    order = random.Random(7)  # the same flip order for every pose change
    out = Image.new("RGBA", (cols * cw, rows * chh), (0, 0, 0, 0))
    k = 0
    for r in range(rows):
        tear = 0
        if scramble > 0 and rnd.random() < scramble * 0.12:
            tear = rnd.randint(-3, 3)
        for c in range(cols):
            i = r * cols + c
            a, v = alpha[i], lum[i]
            flipping = False
            if prev is not None:
                th = order.random()
                if th > morph:
                    a, v = alpha_p[i], lum_p[i]
                flipping = abs(th - morph) < 0.12
            else:
                order.random()
            if a < 90:
                continue
            ch = text[(k + off) % n]
            k += 1
            if flipping or (scramble > 0 and rnd.random() < scramble * 0.35):
                ch = SCRAMBLE[rnd.randrange(len(SCRAMBLE))]
            lv = int(55 + 200 * (v / 255) ** 1.25) if ch != "·" else int(30 + v * 0.3)
            col = ramp[lv] if not flipping else BLUE_HI
            x = (c + tear) * cw
            if 0 <= x < out.width:
                out.paste(col + (255,), (x, r * chh), _glyph(ch))
    return out


@lru_cache(64)
def _stub_pose(pose: str, flip: bool, size) -> Image.Image:
    """Until the text keyframes exist: the pose sprite, resized."""
    from tuikit import EXPR_DIR
    path = EXPR_DIR / f"whale-{pose}.webp" if pose != "skirt" else EXPR_DIR.parent / "maid-left.webp"
    im = Image.open(path).convert("RGBA")
    if pose == "skirt":
        im = im.resize((935, 1682), Image.LANCZOS)
    im = im.crop((0, 0, 935, 1682))
    s = min(size[0] / im.width, size[1] / im.height)
    im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    if flip:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    out.paste(im, ((size[0] - im.width) // 2, size[1] - im.height))
    return out


def draw(fr, t: float, tint: str = "blue", prev=None, morph: float = 1.0, scramble: float = 0.0,
         seed: int = 0) -> Image.Image:
    """A rig Frame as coloured glyphs on dim cell backgrounds."""
    cw, chh = _cell()
    rows, cols = len(fr.art), len(fr.art[0]) if fr.art else 0
    ramp = _ramp(tint)
    text = _text_at(t)
    n = len(text)
    off = flow_offset(t)
    rnd = random.Random(seed)
    order = random.Random(7)
    out = Image.new("RGBA", (cols * cw, rows * chh), (0, 0, 0, 0))
    d = ImageDraw.Draw(out)
    k = 0
    for r in range(rows):
        tear = rnd.randint(-3, 3) if scramble > 0 and rnd.random() < scramble * 0.12 else 0
        for c in range(cols):
            ch, sh = fr.art[r][c], fr.shade[r][c]
            flipping = False
            if prev is not None:
                th = order.random()
                if th > morph:
                    ch, sh = prev.art[r][c], prev.shade[r][c]
                flipping = abs(th - morph) < 0.12
            if ch == " ":
                continue
            lv = int(sh) if sh.isdigit() else 4
            x, y = (c + tear) * cw, r * chh
            if not 0 <= x < out.width:
                continue
            if lv >= 5:
                d.rectangle([x, y, x + cw - 1, y + chh - 1], fill=ramp[int(lv * 15)] + (255,))
            if ch == ":":
                ch = text[(k + off) % n]
                k += 1
                glyph_lv = int(60 + lv * 26) if ch != "\u00b7" else int(40 + lv * 10)
            else:
                glyph_lv = min(255, int(110 + lv * 21))
            if flipping or (scramble > 0 and rnd.random() < scramble * 0.35):
                ch = SCRAMBLE[rnd.randrange(len(SCRAMBLE))]
            out.paste((BLUE_HI if flipping else ramp[glyph_lv]) + (255,), (x, y), _glyph(ch))
    return out


def render(t: float, size: tuple[int, int], base: str = "shy", pinned: bool = False, tint: str = "blue",
           under: float = UNDER) -> tuple[Image.Image, object]:
    """Her at time t as an RGBA image of `size`. Returns (image, step)."""
    try:
        import choreo
        st = choreo.at(t, base, pinned)
    except ImportError:
        st = Step(pose=base)
    m = st.motion or Motion()
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    try:
        import rig
        has_frames = hasattr(rig, "frame")
    except ImportError:
        has_frames = False
    if has_frames:
        cw, chh = _cell()
        cols, rows = size[0] // cw, size[1] // chh
        fr = rig.frame(st.pose, st.flip, m, cols, rows)
        prev = rig.frame(st.prev, st.prev_flip, m, cols, rows) if st.prev and st.morph < 1.0 else None
        g = draw(fr, t, tint, prev, st.morph, st.scramble, seed=int(t * FPS))
        out.alpha_composite(g, ((size[0] - g.width) // 2, size[1] - g.height))
        return out, st
    img = _stub_pose(st.pose, st.flip, size)
    if under > 0:
        out.alpha_composite(underlay(img, 4, tint, under), (0, 0))
    out.alpha_composite(strings(img, t, tint, seed=int(t * FPS)), (0, 0))
    return out, st
