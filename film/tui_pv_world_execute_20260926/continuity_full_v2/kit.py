"""Continuity v2 building blocks.

Every frame is layered in one fixed order:
  1. the scene's own drawing on the stage background (before chrome, without her)
  2. carriers: objects that cross a cut, drawn as ink with alpha, never as screenshots of a finished frame
  3. her: the same string dancer in the same pane whatever the scene asked for
  4. chrome and the lyric band, drawn once per frame and never transformed
  5. CRT post

Everything that `continuity_full_v1` imports stays read-only. Scene and clock changes are made in memory.
"""
from __future__ import annotations

import importlib.util
import math
import random
import sys
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
_spec = importlib.util.spec_from_file_location("continuity_v1", PROJECT / "continuity_full_v1/full_continuity.py")
v1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(v1)
engine, tk, sb, stage, direction = v1.engine, v1.tk, v1.sb, v1.stage, v1.direction
import choreo  # noqa: E402  (full/ is on sys.path through the sidebar module)
import music  # noqa: E402

FPS = 24
W, H = 1280, 720
BG = tk.BG
BEAT = engine.BEAT  # 130 BPM: the hi-hat onsets of the whole song fit 130.000 (drift under 1 ms per 100 s)
LEFT, CENTER = engine.LEFT, engine.CENTER
PANE = (405, 44, 1164, 604)  # the visualisation pane with its title row


# ---------------------------------------------------------------- the music clock

def fix_clock() -> None:
    """audio_features.json holds one row per 459 samples at 22050 Hz: 48.039 rows a second, not 48.
    With the right rate the kicks sit 20-25 ms after the 130 BPM grid, so the drum clock is the grid itself.

    choreo is executed again with the fixed clock, not just given new DRUM0 / DRUM_BEAT: at import it turned lyric
    times into drum beats (B_*) and section starts into seconds (SECTIONS) on its old 129.9 BPM clock, and those
    tables would stay on it - her section changes landed up to 0.19 s late by the end of the song."""
    rate = 22050 / 459
    music.RATE = rate
    music.table()["rate"] = rate
    src = Path(choreo.__file__).read_text(encoding="utf-8")
    old = ("DRUM0 = FIRST_BEAT + 0.035", "DRUM_BEAT = BEAT + 0.00037")
    assert all(s in src for s in old), "choreo's clock lines changed"
    src = src.replace(old[0], "DRUM0 = FIRST_BEAT + 0.022").replace(old[1], "DRUM_BEAT = BEAT")
    exec(compile(src, choreo.__file__, "exec"), choreo.__dict__)


fix_clock()


def patch_code(fn, pairs) -> None:
    """Swap the code of a read-only module's function for its own source with text replacements, in memory. The
    function object stays the same, so every reference to it (shot lists, other modules) runs the new code."""
    import inspect
    import textwrap
    src = textwrap.dedent(inspect.getsource(fn))
    for a, b in pairs:
        assert a in src, f"{fn.__name__}: {a!r} not found"
        src = src.replace(a, b)
    ns: dict = {}
    exec(compile(src, inspect.getsourcefile(fn), "exec"), fn.__globals__, ns)
    fn.__code__ = ns[fn.__name__].__code__


# ---------------------------------------------------------------- her: one renderer for the whole song

HOOK: dict = {}  # per-call hooks read by the v2 scene versions (set by cuts.body around one scene call)
STUB_ON = [False]  # True while v2 draws a scene; approved renderers (chorus 1, EXECUTION hits) keep her own pane
_ORIGINAL_ME = engine.me_pane
_ME_SIG = None


def me_stub(c, expr, *args, **kw):
    """Installed in place of engine.me_pane inside the scene modules: a scene only states how she feels.
    Outside v2's own scene calls it falls through to the original pane."""
    global _ME_SIG
    if not STUB_ON[0]:
        return _ORIGINAL_ME(c, expr, *args, **kw)
    if _ME_SIG is None:
        import inspect
        _ME_SIG = inspect.signature(_ORIGINAL_ME)
    bound = _ME_SIG.bind(c, expr, *args, **kw).arguments
    rect = bound.get("rect", LEFT)
    kw = {k: v for k, v in bound.items() if k not in ("c", "expr", "rect")}
    c.her = dict(expr=expr, rect=rect, kw=kw)
    return rect[0] + 18, rect[1] + 16, Image.new("RGBA", (rect[2] - rect[0] - 36, 420), (0, 0, 0, 0))


def install_stub(*modules) -> None:
    for m in modules:
        m.me_pane = me_stub


def her_layer(t: float, call: dict, box_level: float = 1.0) -> Image.Image:
    """Her pane as an RGBA layer: the string dancer, her title and the expression softmax. The pane frame is drawn
    separately so that it can retract while she stays."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    c = engine.Ctx(layer, ImageDraw.Draw(layer), t, 0.0, 1.0, random.Random(int(t * FPS) * 7919))
    kw = call.get("kw", {})
    rect = call.get("rect", LEFT)
    title = kw.get("title", "/dev/me  pid 4471")
    keep = {k: kw[k] for k in ("dist", "bubbles", "tint", "bright") if k in kw}
    old = tk.BOXES[0]
    tk.BOXES[0] = False
    c.d = _Draw(c.d, rect)
    engine.paste_clipped = _composite_clipped  # her layer is transparent: composite, don't paste with a mask
    try:
        engine.me_pane(c, call["expr"], rect, "half", title=title, **keep)
    finally:
        tk.BOXES[0] = old
        engine.paste_clipped = tk.paste_clipped
    for y, fill in c.d.scans:  # the pitch scan line only where she is
        line = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(line).line([rect[0] + 12, y, rect[2] - 12, y], fill=tuple(fill[:3]) + (255,))
        line.putalpha(ImageChops.multiply(line.getchannel("A"),
                                          layer.getchannel("A").filter(ImageFilter.MaxFilter(3))))
        layer.alpha_composite(line)
    if box_level > 0.02:
        tk.box(ImageDraw.Draw(layer), *rect, title, (0.45 + 0.35 * engine.pulse(t)) * box_level, spinner=t)
    return layer


def _composite_clipped(img, sp, x, y, rect) -> None:
    """paste_clipped for a transparent RGBA target. Pasting with the sprite as its own mask would multiply the
    alpha twice and dim every antialiased stroke (the 5 px glyphs of the video figure are nearly all edge)."""
    x0, y0, x1, y1 = rect
    cx0, cy0 = max(x, x0), max(y, y0)
    cx1, cy1 = min(x + sp.width, x1), min(y + sp.height, y1)
    if cx1 <= cx0 or cy1 <= cy0:
        return
    part = sp.crop((cx0 - x, cy0 - y, cx1 - x, cy1 - y))
    if img.mode == "RGBA" and part.mode == "RGBA":
        img.alpha_composite(part, (cx0, cy0))
    else:
        img.paste(part, (cx0, cy0), part)


class _Draw:
    """ImageDraw proxy for her pane: the full-width pitch scan line is kept aside and drawn inside her silhouette."""

    def __init__(self, d, rect):
        self._d, self._rect, self.scans = d, rect, []

    def line(self, xy, fill=None, width=0, **kw):
        x0, y0, x1, y1 = self._rect
        if (len(xy) == 4 and xy[1] == xy[3] and xy[0] == x0 + 12 and xy[2] == x1 - 12
                and abs(xy[1] - (y1 - 70)) > 1):
            self.scans.append((xy[1], fill))
            return
        return self._d.line(xy, fill=fill, width=width, **kw)

    def __getattr__(self, k):
        return getattr(self._d, k)


def her_glow(layer: Image.Image, k: float) -> Image.Image:
    """A blue halo around her (absorbing a carrier)."""
    if k <= 0.01:
        return layer
    a = layer.getchannel("A").filter(ImageFilter.GaussianBlur(4)).point(lambda v: min(255, int(v * 1.1 * k)))
    halo = Image.new("RGBA", layer.size, tk.blue(1.0) + (0,))
    halo.putalpha(a)
    out = halo
    out.alpha_composite(layer)
    lift = Image.new("RGBA", layer.size, (190, 205, 255, 0))
    lift.putalpha(layer.getchannel("A").point(lambda v: int(v * 0.3 * k)))
    out.alpha_composite(lift)
    return out


def scan_mix(a: Image.Image, b: Image.Image, p: float, rect=LEFT) -> Image.Image:
    """Re-render her from the top down: rows above the scan line already show b. A lit line marks the front."""
    if p <= 0:
        return a
    if p >= 1:
        return b
    y = int(rect[1] + (rect[3] - rect[1]) * p)
    mask = Image.new("L", a.size, 0)
    ImageDraw.Draw(mask).rectangle([0, 0, W, y], fill=255)
    out = Image.composite(b, a, mask)
    ImageDraw.Draw(out).line([rect[0] + 6, y, rect[2] - 6, y], fill=tk.blue(0.9) + (255,), width=1)
    return out


# ---------------------------------------------------------------- chrome: drawn once, last, never transformed

def chrome(img: Image.Image, t: float, src, retract: float = 0.0, shell: str | None = None) -> Image.Image:
    """Header, op ticker and lyric band on top of the finished picture. retract 0..1 moves the header up and the
    ticker right and dims the frames; the lyric itself always stays where it is."""
    c = engine.Ctx(None, None, t, 0.0, 1.0, random.Random(int(t * FPS) * 31), chapter=src.chapter, alert=src.alert)
    c.ops = src.ops
    parts = {}
    for name, fn in (("header", engine.header), ("ticker", engine.ticker), ("lyric", engine.lyric_tokens)):
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        c.img, c.d = ov, ImageDraw.Draw(ov)
        tk.BOXES[0] = name != "lyric"
        try:
            fn(c)
        finally:
            tk.BOXES[0] = True
        parts[name] = ov
    e = max(0.0, min(1.0, retract))
    out = img.convert("RGBA")
    band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    tk.box(ImageDraw.Draw(band), 24, 616, 1256, 680, "stdout · tokens", (0.45 + 0.3 * engine.pulse(t)) * (1 - e))
    out.alpha_composite(band)
    if e < 0.999:
        head = parts["header"]
        top = tk.scale_alpha(head.crop((0, 0, W, 60)), 1 - e)
        out.alpha_composite(top, (0, -int(46 * e)))
        out.alpha_composite(tk.scale_alpha(head.crop((0, 660, W, H)), 1 - e), (0, 660))
        out.alpha_composite(tk.scale_alpha(parts["ticker"], 1 - e), (int(100 * e), 0))
    out.alpha_composite(parts["lyric"])
    if shell and e > 0.01:
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(sh)
        age = (e - 0.3) * 1.2
        txt = tk.decode(f"me@deepsea:~$ {shell}", age, c.rng, 30.0, 0.1) if age > 0 else "me@deepsea:~$"
        d.text((24, 12), txt, font=tk.font(tk.F_MONO_B, 18), fill=tk.blue(0.95))
        d.text((W - 190, 14), f"{int(t // 60):02d}:{t % 60:04.1f} / 03:32", font=tk.font(tk.F_MONO, 14),
               fill=tk.amb(0.5))
        out.alpha_composite(tk.scale_alpha(sh, e))
    return out


# ---------------------------------------------------------------- easing and paths

def clamp(u: float) -> float:
    return max(0.0, min(1.0, u))


def ease_io(u: float) -> float:
    u = clamp(u)
    return 4 * u ** 3 if u < 0.5 else 1 - (-2 * u + 2) ** 3 / 2


def ease_out(u: float) -> float:
    return 1 - (1 - clamp(u)) ** 3


def ease_in(u: float) -> float:
    return clamp(u) ** 3


def ease_back(u: float, s: float = 1.2) -> float:
    """Out-back: arrives, overshoots a little and locks in."""
    u = clamp(u) - 1
    return 1 + (s + 1) * u ** 3 + s * u ** 2


def lerp(a, b, u):
    if isinstance(a, (tuple, list)):
        return tuple(x + (y - x) * u for x, y in zip(a, b))
    return a + (b - a) * u


def bezier(p0, p1, bend: float, u: float):
    """Quadratic arc from p0 to p1; bend > 0 bows to the left of the direction of travel."""
    mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    cx, cy = mx + dy * bend, my - dx * bend
    a, b, c = (1 - u) ** 2, 2 * (1 - u) * u, u * u
    return a * p0[0] + b * cx + c * p1[0], a * p0[1] + b * cy + c * p1[1]


# ---------------------------------------------------------------- ink and sprites

def ink(img: Image.Image, t: float, rect, floor: int = 12, gain: int = 5) -> Image.Image:
    """The drawn strokes inside rect as RGBA: the stage background is keyed out (the carrier is ink, not a box)."""
    rect = tuple(int(v) for v in rect)
    crop = img.crop(rect).convert("RGB")
    bg = stage.background(t).crop(rect)
    r, g, b = ImageChops.difference(crop, bg).split()
    a = ImageChops.lighter(ImageChops.lighter(r, g), b).point(lambda v: 0 if v < floor else min(255, (v - floor) * gain))
    out = crop.convert("RGBA")
    out.putalpha(a)
    return out


@lru_cache(1024)
def text_sprite(s: str, path: str, size: int, color: tuple) -> tuple[Image.Image, tuple[int, int]]:
    """Text as an RGBA sprite plus the offset from the draw origin to the sprite's top-left corner."""
    f = tk.font(path, size)
    l, tp, r, b = f.getbbox(s)
    im = Image.new("RGBA", (max(1, r - l + 6), max(1, b - tp + 6)), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((3 - l, 3 - tp), s, font=f, fill=color)
    return im, (l - 3, tp - 3)


def haloed(sp: Image.Image, k: float, color=None, radius: int = 5) -> Image.Image:
    """Sprite with a soft coloured halo behind it (the 'selected' state of a carrier)."""
    if k <= 0.01:
        return sp
    pad = radius * 2
    out = Image.new("RGBA", (sp.width + 2 * pad, sp.height + 2 * pad), (0, 0, 0, 0))
    a = Image.new("L", out.size, 0)
    a.paste(sp.getchannel("A"), (pad, pad))
    a = a.filter(ImageFilter.GaussianBlur(radius)).point(lambda v: min(255, int(v * 2.2 * k)))
    halo = Image.new("RGBA", out.size, (color or tk.blue(1.0)) + (0,))
    halo.putalpha(a)
    out.alpha_composite(halo)
    out.alpha_composite(sp, (pad, pad))
    return out


def brighten(sp: Image.Image, k: float, to=(235, 240, 255)) -> Image.Image:
    """Mix a sprite's colour toward `to` (a lifted carrier lights up)."""
    if k <= 0.01:
        return sp
    top = Image.new("RGBA", sp.size, to + (0,))
    top.putalpha(sp.getchannel("A").point(lambda v: int(v * clamp(k))))
    out = sp.copy()
    out.alpha_composite(top)
    return out


def place(layer: Image.Image, sp: Image.Image, center, scale: float = 1.0, alpha: float = 1.0) -> None:
    if alpha <= 0.01 or scale <= 0.01:
        return
    if abs(scale - 1) > 0.01:
        sp = sp.resize((max(1, round(sp.width * scale)), max(1, round(sp.height * scale))), Image.LANCZOS)
    if alpha < 0.999:
        sp = tk.scale_alpha(sp, alpha)
    layer.alpha_composite(sp, (round(center[0] - sp.width / 2), round(center[1] - sp.height / 2)))


def blank() -> Image.Image:
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


# ---------------------------------------------------------------- per-cell glyph switch between two drawings

GLYPHS = "01<>/\\|=+*#%&$?!:;{}[]~^"


def reveal(old: Image.Image, new: Image.Image, t: float, delay, region=PANE, cell=(8, 16), dur: float = 0.09,
           front: bool = True, seed: int = 0, density: float = 0.4) -> Image.Image:
    """Each cell of `region` switches from old to new when its own time comes: delay(cx, cy) gives that time
    (seconds on the same clock as t). While it switches, a cell that holds ink shows a decoding glyph."""
    x0, y0, x1, y1 = region
    cw, ch = cell
    cols, rows = (x1 - x0) // cw, (y1 - y0) // ch
    rw, rh = cols * cw, rows * ch
    box_ = (x0, y0, x0 + rw, y0 + rh)
    m = Image.new("L", (cols, rows), 0)
    mp = m.load()
    ps = []
    for r in range(rows):
        cy = y0 + r * ch + ch / 2
        for q in range(cols):
            cx = x0 + q * cw + cw / 2
            p = clamp((t - delay(cx, cy)) / dur)
            mp[q, r] = int(255 * p)
            if 0.02 < p < 0.98:
                ps.append((q, r, p))
    if not ps:
        lo, hi = m.getextrema()
        if hi == 0:
            return old.copy()
        if lo == 255:
            out = old.copy()
            out.paste(new.crop(box_), box_[:2])
            return out
    out = old.copy()
    mask = m.resize((rw, rh), Image.NEAREST)
    out.paste(Image.composite(new.crop(box_), old.crop(box_), mask), box_[:2])
    if front and ps:
        bg = stage.background(t).crop(box_)
        inks = []
        for im in (old, new):
            r_, g_, b_ = ImageChops.difference(im.crop(box_).convert("RGB"), bg).split()
            lv = ImageChops.lighter(ImageChops.lighter(r_, g_), b_).resize((cols, rows), Image.BOX)
            inks.append(lv.load())
        d = ImageDraw.Draw(out)
        f = tk.font(tk.F_MONO_B, 13)
        rng = random.Random(seed * 9973 + int(t * FPS))
        for q, r, p in ps:
            ch_ = rng.choice(GLYPHS)
            if inks[0][q, r] < 6 and inks[1][q, r] < 6 or rng.random() > density:
                continue
            k = 1 - abs(2 * p - 1)
            d.text((x0 + q * cw, y0 + r * ch), ch_, font=f, fill=tk.blue(0.2 + 0.6 * k))
    return out


def radial(seed, t0: float, speed: float):
    sx, sy = seed
    return lambda x, y: t0 + math.hypot(x - sx, y - sy) / speed


def inward(seed, t0: float, t1: float, reach: float = 900.0):
    """Cells far from `seed` go first, the seed itself last: the drawing drains into one point."""
    sx, sy = seed
    return lambda x, y: t1 - (t1 - t0) * min(1.0, math.hypot(x - sx, y - sy) / reach)


def sweep(origin, direction, t0: float, speed: float):
    ox, oy = origin
    dx, dy = direction
    n = math.hypot(dx, dy)
    dx, dy = dx / n, dy / n
    return lambda x, y: t0 + max(0.0, (x - ox) * dx + (y - oy) * dy) / speed
