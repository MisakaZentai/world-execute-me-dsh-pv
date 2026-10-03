"""tuikit: terminal-look drawing primitives for the AI-mascot TUI PVs.

PIL only (no numpy). Everything draws onto a 1280x720 RGB canvas.

Colours are semantic and come from a palette picked by the TUI_PALETTE environment variable:
  UI   (kept under the old name AMBER) - the system, i.e. "your" terminal
  ME   (BLUE_*)                        - the whale girl and anything that is her will
  ERR  (RED)                           - errors
  ANOM                                 - anomalies / warnings
"""

from __future__ import annotations

import math
import os
import random
import re
import zlib
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

W, H = 1280, 720

DS_BLUE = (77, 107, 254)  # DeepSeek brand blue, #4D6BFE
PALETTES = {
    # v2 look: amber phosphor system, anomalies in phosphor green
    "amber": dict(BG=(8, 6, 4), UI=(255, 176, 0), ERR=(255, 58, 40), ANOM=(70, 255, 140),
                  ME_LO=(4, 8, 34), ME_MID=DS_BLUE, ME_HI=(196, 212, 255), ME_TEXT=(126, 152, 255)),
    # deep-sea night: cold white-steel system on navy black, log-level yellow for anomalies
    "deepsea": dict(BG=(4, 7, 15), UI=(200, 214, 234), ERR=(255, 59, 48), ANOM=(255, 204, 0),
                    ME_LO=(4, 8, 34), ME_MID=DS_BLUE, ME_HI=(196, 212, 255), ME_TEXT=(120, 148, 255)),
    # green phosphor system, yellow anomalies
    "phosphor": dict(BG=(3, 8, 5), UI=(92, 255, 140), ERR=(255, 58, 40), ANOM=(255, 214, 0),
                     ME_LO=(4, 8, 34), ME_MID=DS_BLUE, ME_HI=(196, 212, 255), ME_TEXT=(126, 152, 255)),
}
PALETTE = os.environ.get("TUI_PALETTE", "amber")
_P = PALETTES[PALETTE]

BG = _P["BG"]
AMBER = UI = _P["UI"]
RED = ERR = _P["ERR"]
ANOM = _P["ANOM"]
BLUE_LO = _P["ME_LO"]
BLUE_MID = _P["ME_MID"]
BLUE_HI = _P["ME_HI"]
BLUE_TEXT = _P["ME_TEXT"]

MV = Path(__file__).resolve().parents[1].joinpath("ai_mascot_mv_world_execute_20260926")
EXPR_DIR = Path(__file__).resolve().parents[1].joinpath("third_party_references/whale_maid_expanded_20260926/expressions")
F_MONO = os.environ.get("PV_F_MONO", "C:/Windows/Fonts/consola.ttf")
F_MONO_B = os.environ.get("PV_F_MONO_B", "C:/Windows/Fonts/consolab.ttf")
F_HEAD = str(MV / "fonts" / "SpaceMono-Bold.ttf")
F_BANNER = str(MV / "fonts" / "Anton-Regular.ttf")
F_CJK = os.environ.get("PV_F_CJK", "C:/Windows/Fonts/msyh.ttc")
F_SYM = os.environ.get("PV_F_SYM", "C:/Windows/Fonts/seguisym.ttf")  # math glyphs Consolas lacks: ∃ ⟨ ⟩ ⊢ ∀

SCR = "!<>-_\\/[]{}=+*^?#%$&@01|~:;"
EXPRS = ["cheerful", "starry", "shy", "serious", "confused", "frightened", "angry", "exasperated"]


def mix(c, level, base=BG):
    level = max(0.0, min(1.0, level))
    return tuple(int(base[i] + (c[i] - base[i]) * level) for i in range(3))


UI_GAIN = [1.0]  # set per frame by the engine; < 1 drains the system colour ("you have left")
BOXES = [True]   # False in the bare-shell layout: panels lose their frames


def amb(level):
    return mix(AMBER, level * UI_GAIN[0])


def red(level):
    return mix(RED, level)


def blue(level):
    return mix(BLUE_TEXT, level)


def anom(level):
    return mix(ANOM, level)


def ease(u: float) -> float:
    u = max(0.0, min(1.0, u))
    return 1 - (1 - u) ** 3


def smooth(u: float) -> float:
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


@lru_cache(None)
def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


# ---------------------------------------------------------------- text effects

def decode(s: str, age: float, rng: random.Random, rate: float = 45.0, settle: float = 0.12,
           corrupt: float = 0.0) -> str:
    """Typewriter where each new character flickers through random glyphs for `settle` seconds."""
    if age is None:
        n = len(s)
        age = 1e9
    else:
        n = min(len(s), max(0, int(age * rate)))
    out = []
    for i in range(n):
        ch = s[i]
        a = age - i / rate
        if ch != " " and (a < settle or (corrupt > 0 and rng.random() < corrupt)):
            ch = rng.choice(SCR)
        out.append(ch)
    return "".join(out)


def tokenize(s: str) -> list[str]:
    """Toy BPE-looking split: words and punctuation; long words break into two pieces."""
    toks = []
    for w in re.findall(r"[A-Za-z']+|[^\sA-Za-z']", s):
        if len(w) > 7:
            k = len(w) // 2 + 1
            toks += [w[:k], w[k:]]
        else:
            toks.append(w)
    return toks


def token_id(tok: str) -> int:
    return zlib.crc32(tok.lower().encode()) % 100000


# ---------------------------------------------------------------- sprites

CROPS = {"full": None, "upper": (0.10, 0.0, 0.90, 0.47), "face": (0.20, 0.0, 0.78, 0.26),
         "bust": (0.16, 0.0, 0.84, 0.34)}


@lru_cache(None)
def sprite_src(expr: str, crop: str) -> Image.Image:
    im = Image.open(EXPR_DIR / f"whale-{expr}.webp").convert("RGBA")
    if CROPS[crop] is None:
        return im.crop(im.getchannel("A").getbbox())
    w, h = im.size
    a, b, c, e = CROPS[crop]
    return im.crop((int(w * a), int(h * b), int(w * c), int(h * e)))


@lru_cache(None)
def grid_mask(w: int, h: int, px: int) -> Image.Image:
    m = Image.new("L", (w, h), 255)
    d = ImageDraw.Draw(m)
    if px >= 3:
        for x in range(px - 1, w, px):
            d.line([x, 0, x, h], fill=0)
    for y in range(2 * px - 1, h, 2 * px):
        d.line([0, y, w, y], fill=70)
    return m


TINTS = {"blue": (BLUE_LO, BLUE_HI, BLUE_MID), "amber": (BG, AMBER, None), "red": (BG, RED, None),
         "anom": (BG, ANOM, None)}


def tint_colorize(lum: Image.Image, tint: str) -> Image.Image:
    lo, hi, mid = TINTS[tint]
    if mid is None:
        return ImageOps.colorize(lum, black=lo, white=hi)
    return ImageOps.colorize(lum, black=lo, white=hi, mid=mid)


@lru_cache(None)
def halfblock_lum(expr: str, crop: str, max_w: int, max_h: int, px: int = 4, levels: int = 8):
    """Quantised luminance + alpha at half-block resolution (one value per px*px square)."""
    src = sprite_src(expr, crop)
    aspect = src.height / src.width
    cols = max(2, int(min(max_w / px, (max_h / px) / aspect)))
    rows = max(2, int(round(cols * aspect)))
    rows -= rows % 2
    small = src.resize((cols, rows), Image.LANCZOS)
    step = 255 / (levels - 1)
    lum = small.convert("L").point(lambda v: int(round((0.16 + 0.84 * v / 255) * (levels - 1)) * step))
    alpha = small.getchannel("A").point(lambda a: 255 if a > 100 else 0)
    return lum, alpha


@lru_cache(None)
def halfblock(expr: str, crop: str, max_w: int, max_h: int, px: int = 4, levels: int = 8,
              tint: str = "blue") -> Image.Image:
    lum, alpha = halfblock_lum(expr, crop, max_w, max_h, px, levels)
    size = (lum.width * px, lum.height * px)
    lum = lum.resize(size, Image.NEAREST)
    alpha = ImageChops.multiply(alpha.resize(size, Image.NEAREST), grid_mask(size[0], size[1], px))
    rgb = tint_colorize(lum, tint).convert("RGBA")
    rgb.putalpha(alpha)
    return rgb


def scale_alpha(sp: Image.Image, k: float) -> Image.Image:
    if k >= 0.999:
        return sp
    out = sp.copy()
    out.putalpha(sp.getchannel("A").point(lambda a: int(a * max(0.0, k))))
    return out


def paste_clipped(img: Image.Image, sp: Image.Image, x: int, y: int, rect: tuple[int, int, int, int]) -> None:
    x0, y0, x1, y1 = rect
    cx0, cy0 = max(x, x0), max(y, y0)
    cx1, cy1 = min(x + sp.width, x1), min(y + sp.height, y1)
    if cx1 <= cx0 or cy1 <= cy0:
        return
    part = sp.crop((cx0 - x, cy0 - y, cx1 - x, cy1 - y))
    img.paste(part, (cx0, cy0), part)


def glitch_paste(img: Image.Image, sp: Image.Image, x: int, y: int, amount: float, rng: random.Random,
                 rect=None, strip: int = 8) -> None:
    for sy in range(0, sp.height, strip):
        off = int(rng.gauss(0, 22 * amount)) if rng.random() < amount else 0
        part = sp.crop((0, sy, sp.width, min(sp.height, sy + strip)))
        if rect:
            paste_clipped(img, part, x + off, y + sy, rect)
        else:
            img.paste(part, (x + off, y + sy), part)


# ---------------------------------------------------------------- glyph ascii art

GLYPH_RAMP = " .:-=+*#%@"


@lru_cache(None)
def glyph_grid(expr: str, crop: str, cols: int, rows: int) -> tuple[list[str], Image.Image]:
    """ASCII art of the sprite: edge cells get a directional stroke, interior cells a density glyph.
    Returns the text rows and a per-cell brightness image (cols x rows)."""
    src = sprite_src(expr, crop)
    small = src.resize((cols, rows), Image.LANCZOS)
    lum = small.convert("L")
    alpha = small.getchannel("A")
    gx = lum.filter(ImageFilter.Kernel((3, 3), [-1, 0, 1, -2, 0, 2, -1, 0, 1], scale=4, offset=128))
    gy = lum.filter(ImageFilter.Kernel((3, 3), [-1, -2, -1, 0, 0, 0, 1, 2, 1], scale=4, offset=128))
    L, A, X, Y = lum.load(), alpha.load(), gx.load(), gy.load()
    bright = Image.new("L", (cols, rows), 0)
    B = bright.load()
    lines = []
    for r in range(rows):
        row = []
        for c in range(cols):
            if A[c, r] < 110:
                row.append(" ")
                continue
            v = L[c, r] / 255
            ex, ey = (X[c, r] - 128) / 32, (Y[c, r] - 128) / 32
            mag = math.hypot(ex, ey)
            if mag > 1.1:
                ang = (math.degrees(math.atan2(ey, ex)) + 180) % 180
                row.append("|" if ang < 22.5 or ang >= 157.5 else "\\" if ang < 67.5 else "-" if ang < 112.5 else "/")
                B[c, r] = 255
            else:
                row.append(GLYPH_RAMP[min(len(GLYPH_RAMP) - 1, 1 + int(v * (len(GLYPH_RAMP) - 1)))])
                B[c, r] = int(255 * (0.35 + 0.65 * v))
        lines.append("".join(row))
    return lines, bright


def glyph_sprite(expr: str, crop: str, cols: int, rows: int, size: int = 11, scramble: float = 0.0,
                 rng: random.Random | None = None, tint: str = "blue", reveal: float = 1.0) -> Image.Image:
    """Render the glyph art as an RGBA image. `scramble` swaps that fraction of glyphs for noise;
    `reveal` < 1 hides a random subset of cells (used for resolving and disintegrating)."""
    f = font(F_MONO_B, size)
    cw, ch = f.getlength("M"), round(size * 1.15)
    lines, bright = glyph_grid(expr, crop, cols, rows)
    if (scramble > 0 or reveal < 1) and rng is not None:
        out = []
        for r, line in enumerate(lines):
            row = []
            for ch_ in line:
                if ch_ == " ":
                    row.append(" ")
                elif reveal < 1 and rng.random() > reveal:
                    row.append(" ")
                elif scramble > 0 and rng.random() < scramble:
                    row.append(rng.choice(SCR))
                else:
                    row.append(ch_)
            out.append("".join(row))
        lines = out
    size_px = (int(cols * cw) + 2, rows * ch)
    txt = Image.new("L", size_px, 0)
    d = ImageDraw.Draw(txt)
    for r, line in enumerate(lines):
        d.text((0, r * ch), line, font=f, fill=255)
    b = bright.resize(size_px, Image.NEAREST)
    lum = ImageChops.multiply(txt, b)
    rgb = tint_colorize(lum, tint).convert("RGBA")
    rgb.putalpha(txt)
    return rgb


# ---------------------------------------------------------------- big letters

@lru_cache(None)
def banner_bits(text: str, rows: int, cell_aspect: float) -> Image.Image:
    f = font(F_BANNER, 220)
    tmp = Image.new("L", (int(f.getlength(text)) + 60, 300), 0)
    ImageDraw.Draw(tmp).text((30, 10), text, font=f, fill=255)
    tmp = tmp.crop(tmp.getbbox())
    cols = max(1, int(round(tmp.width / tmp.height * rows * cell_aspect)))
    return tmp.resize((cols, rows), Image.LANCZOS).point(lambda v: 255 if v > 110 else 0)


@lru_cache(None)
def banner_block(text: str, rows2: int, px: int, fg: tuple, bg: tuple, max_w: int = 1200) -> Image.Image:
    bits = banner_bits(text, rows2, 1.0)
    px = max(2, min(px, max_w // bits.width))
    size = (bits.width * px, bits.height * px)
    big = bits.resize(size, Image.NEAREST)
    alpha = ImageChops.multiply(big, grid_mask(size[0], size[1], px))
    rgb = ImageOps.colorize(big, black=bg, white=fg).convert("RGBA")
    rgb.putalpha(alpha)
    return rgb


# ---------------------------------------------------------------- widgets

def box(d: ImageDraw.ImageDraw, x0, y0, x1, y1, title: str = "", level: float = 0.5, color=AMBER,
        spinner: float | None = None) -> None:
    if not BOXES[0]:
        return
    d.rectangle([x0, y0, x1, y1], outline=mix(color, level))
    L = 7
    for (px, py, sx, sy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        d.line([px, py, px + sx * L, py], fill=mix(color, min(1.0, level + 0.4)), width=2)
        d.line([px, py, px, py + sy * L], fill=mix(color, min(1.0, level + 0.4)), width=2)
    if title:
        if spinner is not None:
            title = "|/-\\"[int(spinner * 8) % 4] + " " + title
        f = font(F_HEAD, 13)
        tw = d.textlength(f" {title} ", font=f)
        d.rectangle([x0 + 12, y0 - 9, x0 + 12 + tw, y0 + 9], fill=BG)
        d.text((x0 + 12, y0 - 10), f" {title} ", font=f, fill=mix(color, min(1.0, level + 0.35)))


def dot_chart(d: ImageDraw.ImageDraw, x, y, w, h, fn, progress: float, color, sx: int = 5, sy: int = 5,
              clip_top: bool = True, axis: bool = True):
    cols, rows = w // sx, h // sy
    if axis:
        for i in range(0, cols, 2):
            d.point((x + i * sx, y + h), fill=amb(0.28))
        for r in range(0, rows, 3):
            d.point((x - 4, y + r * sy), fill=amb(0.28))
    prev, last = None, None
    for i in range(cols):
        u = i / (cols - 1)
        if u > progress:
            break
        v = fn(u)
        if clip_top:
            v = min(1.0, v)
        r = int(round((1 - max(0.0, v)) * (rows - 1)))
        span = range(min(prev, r), max(prev, r) + 1) if prev is not None else [r]
        for rr in span:
            d.rectangle([x + i * sx, y + rr * sy, x + i * sx + 1, y + rr * sy + 1], fill=color)
        prev, last = r, (x + i * sx, y + r * sy)
    return last


def heat_cell(d, x, y, w, h, v, color=AMBER) -> None:
    """One heat-map cell drawn as a shade block, so the matrix still reads as terminal text."""
    v = max(0.0, min(1.0, v))
    d.rectangle([x, y, x + w - 2, y + h - 2], fill=mix(color, 0.06 + 0.94 * v))


@lru_cache(None)
def dot_field(w: int, h: int, step: int = 16) -> Image.Image:
    im = Image.new("RGB", (w, h + step), BG)
    d = ImageDraw.Draw(im)
    for y in range(0, h + step, step):
        for x in range(0, w, step):
            d.point((x, y), fill=mix(UI, 0.1))
    return im


@lru_cache(None)
def conv_maps(expr: str, crop: str, cols: int, rows: int) -> list[tuple[str, Image.Image]]:
    """Feature maps of the sprite for the convolution shot, at cell resolution."""
    src = sprite_src(expr, crop)
    flat = Image.new("RGBA", src.size, (0, 0, 0, 255))
    flat.alpha_composite(src)
    small = flat.convert("L").resize((cols, rows), Image.LANCZOS)
    kernels = [
        ("sobel_x", [-1, 0, 1, -2, 0, 2, -1, 0, 1]),
        ("sobel_y", [-1, -2, -1, 0, 0, 0, 1, 2, 1]),
        ("laplace", [0, 1, 0, 1, -4, 1, 0, 1, 0]),
        ("sharpen", [0, -1, 0, -1, 5, -1, 0, -1, 0]),
        ("emboss", [-2, -1, 0, -1, 1, 1, 0, 1, 2]),
        ("blur", [1, 2, 1, 2, 4, 2, 1, 2, 1]),
    ]
    out = []
    for name, k in kernels:
        if name == "blur":
            fm = small.filter(ImageFilter.Kernel((3, 3), k, scale=16))
        elif name == "emboss":
            fm = small.filter(ImageFilter.Kernel((3, 3), k, scale=1, offset=128))
        elif name == "sharpen":
            fm = small.filter(ImageFilter.Kernel((3, 3), k, scale=1))
        else:  # signed response -> magnitude
            pos = small.filter(ImageFilter.Kernel((3, 3), k, scale=1))
            neg = small.filter(ImageFilter.Kernel((3, 3), [-v for v in k], scale=1))
            fm = ImageChops.add(pos, neg)
        out.append((name, ImageOps.autocontrast(fm, cutoff=1)))
    return out


def tile_from_lum(lum: Image.Image, px: int, tint: str = "amber", reveal_rows: int | None = None) -> Image.Image:
    if reveal_rows is not None:
        lum = lum.copy()
        ImageDraw.Draw(lum).rectangle([0, reveal_rows, lum.width, lum.height], fill=0)
    size = (lum.width * px, lum.height * px)
    big = lum.resize(size, Image.NEAREST)
    alpha = ImageChops.multiply(big.point(lambda v: 255 if v > 18 else 0), grid_mask(size[0], size[1], px))
    rgb = tint_colorize(big, tint).convert("RGBA")
    rgb.putalpha(alpha)
    return rgb


def noise_tile(cols: int, rows: int, px: int, tint: str = "blue") -> Image.Image:
    n = Image.effect_noise((cols, rows), 90).point(lambda v: max(0, min(255, int((v - 60) * 1.6))))
    return tile_from_lum(n, px, tint)


# ---------------------------------------------------------------- post

@lru_cache(None)
def scanlines() -> Image.Image:
    s = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(s)
    for y in range(0, H, 3):
        d.line([0, y, W, y], fill=(0, 0, 0, 55))
    return s


LYRIC_LIFT = [False]  # set by the engine: keep the vignette off the bottom lyric band


@lru_cache(None)
def vignette(lift: bool = False) -> Image.Image:
    small = Image.new("L", (64, 36), 0)
    px = small.load()
    for y in range(36):
        # rows 30-35 are y 600-720, where the lyric band sits
        k = 1.0 if not lift or y < 30 else {30: 0.7, 31: 0.45}.get(y, 0.3)
        for x in range(64):
            dx, dy = (x - 31.5) / 32, (y - 17.5) / 18
            px[x, y] = int(255 * k * min(1.0, max(0.0, (dx * dx + dy * dy) - 0.35) * 0.55))
    v = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    v.putalpha(small.resize((W, H), Image.BILINEAR))
    return v


def post(img: Image.Image, prev: Image.Image | None, trail: float = 0.42, bloom: float = 0.35) -> Image.Image:
    if prev is not None and trail > 0:
        img = ImageChops.lighter(img, prev.point(lambda v: int(v * trail)))
    glow = img.filter(ImageFilter.GaussianBlur(4))
    img = ImageChops.add(img, glow.point(lambda v: int(v * bloom)))
    img = img.convert("RGBA")
    img.alpha_composite(scanlines())
    img.alpha_composite(vignette(LYRIC_LIFT[0]))
    return img.convert("RGB")
