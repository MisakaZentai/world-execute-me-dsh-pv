"""Section 04 DEPLOY (cuts 34-45, 73.5 - 103.1 s): "Given to: you" is handed down the section.

Scenes are in scenes_deploy.py. This module adds:
- the props on her (OVERLAY): an eggplant suit, a tomato suit, cat ears and whiskers, the props she hands to the
  process tree. They are drawn in her own glyph grid (5 x 10 px cells) and anchored to her live figure, so she
  keeps dancing inside them; nothing replaces her;
- a filter on her layer (HER_FILTERS): the fp8 formats posterise her colour ramp (8 -> 4 -> 2 levels, then back),
  and the sampling temperature of 'trance' dissolves her edges while her core stays readable;
- the twelve cuts C34-C45, each staged by hand (see the docstrings).
"""
from __future__ import annotations

import bisect
import math
import random

from PIL import Image, ImageChops, ImageDraw, ImageFilter

import cuts as C
import kit
import scenes_deploy as SD
import sec_verse2
from cuts import Cut, Frame, rgba, text_at
from kit import (BEAT, FPS, H, PANE, W, bezier, blank, brighten, clamp, ease_back, ease_in, ease_io, ease_out,
                 haloed, ink, inward, lerp, place, radial, reveal, sweep, text_sprite, tk)

STUB = [sec_verse2]
REPLACE = SD.REPLACE
SPLIT = SD.SPLIT
SHELL = {"shot_god": "ps -ef --forest"}

ALL = kit.v1.ALL
BY = kit.v1.BYNAME
T34, T35, T36, T37, T38, T39, T40, T41, T42, T43, T44, T45 = (ALL[i].start for i in range(34, 46))
T46 = ALL[46].start
FIRST_BEAT = kit.engine.FIRST_BEAT


def beat_t(k: float) -> float:
    return FIRST_BEAT + k * BEAT


def beat_of(t: float) -> float:
    return (t - FIRST_BEAT) / BEAT


# ================================================================ her figure

def fig_geom(t: float) -> dict:
    """Her figure on screen at time t: bounding box, head, chest and reaching hand (v2.her_anchor)."""
    import v2
    a = v2.her(t).getchannel("A")
    x0, y0, x1, y1 = kit.LEFT
    bx = (x0 + 4, y0 + 14, x1 - 4, y1 - 80)
    bb = a.crop(bx).point(lambda v: 255 if v > 60 else 0).getbbox() or (60, 40, 300, 440)
    box = (bx[0] + bb[0], bx[1] + bb[1], bx[0] + bb[2], bx[1] + bb[3])
    return dict(box=box, head=v2.her_anchor(t, "head"), chest=v2.her_anchor(t, "chest"),
                hand=v2.her_anchor(t, "hand"))


# ================================================================ props in her glyph grid

GX, GY = SD.GRID_XY
CW, CH = SD.CELL
COLS, ROWS = 70, 45
EGG = (150, 118, 255)       # eggplant skin: her blue pushed toward violet
EGG_WASH = (96, 70, 214)
TOM = (255, 104, 84)        # tomato: the palette red, softened
TOM_WASH = (220, 70, 60)
CALYX = (190, 214, 206)


def _glyph(ch):
    import dancer
    return dancer._glyph(ch)


def suit_masks(t: float, kind: str, s: float):
    """Cell masks (COLS x ROWS) of a suit around her at scale s (1 = worn), pivoting on her chest."""
    g = fig_geom(t)
    bx0, by0, bx1, by1 = g["box"]
    hh = by1 - by0
    cx, cy = g["chest"]
    hx = g["head"][0]
    body = Image.new("L", (COLS * CW, ROWS * CH), 0)
    cal = Image.new("L", (COLS * CW, ROWS * CH), 0)
    db, dc = ImageDraw.Draw(body), ImageDraw.Draw(cal)

    def P(x, y):  # screen point scaled about the chest, into grid pixel space
        return cx + (x - cx) * s - GX, cy + (y - cy) * s - GY

    def ell(d, x, y, rx, ry):
        (ax, ay), (bx_, by_) = P(x - rx, y - ry), P(x + rx, y + ry)
        d.ellipse([ax, ay, bx_, by_], fill=255)

    if kind == "eggplant":
        rx = max(92.0, min(150.0, 0.5 * (bx1 - bx0)))
        ell(db, cx, by0 + 0.64 * hh, rx, 0.37 * hh)
        ell(db, cx, by0 + 0.34 * hh, rx * 0.62, 0.2 * hh)
        top = by0 + 4
        pts = []
        for j in range(11):  # the calyx: a five-leaf cap on her head, and its stem
            a = math.pi * j / 10
            r = 58 if j % 2 == 0 else 30
            pts.append(P(hx - r * math.cos(a), top + 10 + 0.45 * r * math.sin(a)))
        dc.polygon(pts, fill=255)
        (ax, ay), (bx_, by_) = P(hx - 5, top - 26), P(hx + 5, top + 12)
        dc.rectangle([ax, ay, bx_, by_], fill=255)
    else:  # tomato
        r = max(118.0, min(150.0, 0.33 * hh))
        ell(db, cx, by0 + 0.56 * hh, r * 1.08, r)
        top = by0 + 2
        pts = []
        for j in range(10):
            a = math.tau * j / 10 - math.pi / 2
            rr = 52 if j % 2 == 0 else 16
            pts.append(P(hx + rr * math.cos(a), top + 12 + 0.55 * rr * math.sin(a)))
        dc.polygon(pts, fill=255)
        (ax, ay), (bx_, by_) = P(hx - 4, top - 18), P(hx + 4, top + 10)
        dc.rectangle([ax, ay, bx_, by_], fill=255)
    b = body.resize((COLS, ROWS), Image.BOX).point(lambda v: 255 if v > 110 else 0)
    c = cal.resize((COLS, ROWS), Image.BOX).point(lambda v: 255 if v > 90 else 0)
    return b, c


def draw_suit(t: float, kind: str, s: float = 1.0, alpha: float = 1.0, peel: float | None = None) -> Image.Image:
    """The suit as glyph cells: a bright skin of the word itself, a translucent wash over her, a pale cap.
    peel (0..1) takes the suit off from the top down, a scrambling row at the front."""
    layer = blank()
    if s <= 0.02 or alpha <= 0.02:
        return layer
    b, c = suit_masks(t, kind, s)
    core = b.filter(ImageFilter.MinFilter(3))
    B, K, Cc = b.load(), core.load(), c.load()
    edge_col, wash_col = (EGG, EGG_WASH) if kind == "eggplant" else (TOM, TOM_WASH)
    word = ("eggplant·" if kind == "eggplant" else "tomato·")
    rows_on = [r for r in range(ROWS) if any(B[q, r] or Cc[q, r] for q in range(COLS))]
    if not rows_on:
        return layer
    r0, r1 = rows_on[0], rows_on[-1]
    front = None if peel is None else r0 + (r1 - r0 + 3) * peel
    rnd = random.Random(int(t * FPS) * 31 + len(kind))
    d = ImageDraw.Draw(layer)
    k = 0
    wa = int(52 * alpha)
    ea = int(255 * alpha)
    for r in range(ROWS):
        if front is not None and r < front - 1:
            continue
        scram = front is not None and r < front + 1
        y = GY + r * CH
        run = None
        for q in range(COLS + 1):
            inb = q < COLS and B[q, r] and K[q, r] and not Cc[q, r]
            if inb and run is None:
                run = q
            elif not inb and run is not None:
                d.rectangle([GX + run * CW, y, GX + q * CW - 1, y + CH - 1], fill=wash_col + (wa,))
                run = None
            if q >= COLS:
                break
            x = GX + q * CW
            if Cc[q, r]:
                ch = "*" if (q + r) % 3 else "^"
                if scram:
                    ch = kit.GLYPHS[rnd.randrange(len(kit.GLYPHS))]
                d.rectangle([x, y, x + CW - 1, y + CH - 1], fill=tk.BG + (int(200 * alpha),))
                layer.paste(CALYX + (ea,), (x, y), _glyph(ch))
            elif B[q, r] and not K[q, r]:
                ch = word[k % len(word)]
                k += 1
                if scram:
                    ch = kit.GLYPHS[rnd.randrange(len(kit.GLYPHS))]
                d.rectangle([x, y, x + CW - 1, y + CH - 1], fill=tk.BG + (int(170 * alpha),))
                layer.paste(edge_col + (ea,), (x, y), _glyph(ch))
    return layer


def ear_geom(t: float):
    """Two ear triangles on her head and three whiskers a side, in screen coordinates."""
    g = fig_geom(t)
    hx = g["head"][0]
    top = g["box"][1]
    hh = g["box"][3] - g["box"][1]
    ears = []
    for side in (-1, 1):
        bx = hx + side * 26
        ears.append([(bx - 20, top + 18), (bx + 20, top + 18), (bx + side * 14, top - 24)])
    fy = top + 0.085 * hh
    whisk = []
    for side in (-1, 1):
        for j, dy in enumerate((-5, 1, 7)):
            whisk.append(((hx + side * 18, fy + dy), (hx + side * 52, fy + dy * 2.2 - 2)))
    return ears, whisk


def draw_ears(t: float, k: float = 1.0, alpha: float = 1.0) -> Image.Image:
    """Cat ears (k = size, 0..1: they grow out of / retract into her head) and whiskers."""
    layer = blank()
    if k <= 0.02 or alpha <= 0.02:
        return layer
    d = ImageDraw.Draw(layer)
    ears, whisk = ear_geom(t)
    for tri in ears:
        (ax, ay), (bx, by), (px, py) = tri
        base = ((ax + bx) / 2, ay)
        tip = (base[0] + (px - base[0]) * k, base[1] + (py - base[1]) * k)
        pts = [(ax, ay), (bx, by), tip]
        d.polygon(pts, fill=tk.blue(0.5) + (int(235 * alpha),), outline=tk.blue(1.0) + (int(255 * alpha),))
        inner = [lerp(p, (base[0], base[1] - 8 * k), 0.45) for p in pts]
        d.polygon(inner, fill=tk.mix(tk.BLUE_HI, 0.55) + (int(200 * alpha),))
    wk = clamp((k - 0.4) / 0.6)
    for (a, b) in whisk:
        e = lerp(a, b, wk)
        d.line([a, e], fill=tk.mix(tk.BLUE_HI, 0.9) + (int(230 * alpha * wk),), width=1)
    return layer


def ear_targets(t: float) -> list:
    """Where the lycopene nodes land: ear vertices and edge midpoints, whisker ends (21 points, left to right)."""
    ears, whisk = ear_geom(t)
    pts = []
    for tri in ears:
        a, b, p = tri
        pts += [a, b, p, lerp(a, p, 0.5), lerp(b, p, 0.5)]
    for a, b in whisk:
        pts += [b, lerp(a, b, 0.4)]
    pts = sorted(pts, key=lambda p: p[0])
    return pts[:21]


# ---------------------------------------------------------------- overlays (whole-shot art over her)

EGG_ON = beat_t(161)  # "egg-plant": the classifier is sure, the suit goes on
PEEL = 8 / FPS
TOM_INFLATE = 10 / FPS


def ov_eggplant(t, n):
    layer = blank()
    # the classifier reads her: an 8x8 patch grid over her figure, the current patch lit
    ga = 1.0 - clamp((t - EGG_ON) / 0.25)
    if ga > 0.02 and t >= T34 + 0.2:
        (x0, y0, x1, y1), _ = SD.patch_grid(t)
        d = ImageDraw.Draw(layer)
        a = int(110 * ga)
        for i in range(9):
            x = x0 + (x1 - x0) * i / 8
            y = y0 + (y1 - y0) * i / 8
            d.line([x, y0, x, y1], fill=tk.amb(0.6) + (a,))
            d.line([x0, y, x1, y], fill=tk.amb(0.6) + (a,))
        k = SD.patch_index(t - T34)
        qx, qy = k % 8, k // 8
        pw, ph = (x1 - x0) / 8, (y1 - y0) / 8
        d.rectangle([x0 + qx * pw, y0 + qy * ph, x0 + (qx + 1) * pw, y0 + (qy + 1) * ph],
                    outline=tk.amb(1.0) + (int(255 * ga),), width=2)
    if t >= EGG_ON:
        u = clamp((t - EGG_ON) / TOM_INFLATE)
        s = lerp(0.3, 1.0, ease_back(u, 1.4))
        layer.alpha_composite(draw_suit(t, "eggplant", s, min(1.0, 0.3 + u)))
    return layer


def ov_nutrients(t, n):
    if t < T35 + PEEL + 0.05:
        return draw_suit(t, "eggplant", 1.0, 1.0, peel=ease_in((t - T35) / PEEL))
    return None


def ov_tomato(t, n):
    u = clamp((t - T36) / TOM_INFLATE)
    return draw_suit(t, "tomato", lerp(0.35, 1.0, ease_back(u, 1.8)), min(1.0, 0.35 + u))


def ov_antioxidants(t, n):
    if t < T37 + 8 / FPS:
        u = ease_in((t - T37) / (8 / FPS))
        return draw_suit(t, "tomato", lerp(1.0, 0.15, u), 1 - u * 0.8)
    return None


def ov_tabby(t, n):
    if t < T38 - 0.02:
        return None
    return draw_ears(t, ease_back(clamp((t - (T38 - 0.02)) / 0.12), 1.5))


def ov_purr(t, n):
    if t < T39 + 6 / FPS:
        return draw_ears(t, 1 - ease_in((t - T39) / (6 / FPS)))
    return None


def ov_god(t, n):
    """She hands the tree its three new children: the props she wore fly from her hand to their rows."""
    layer = blank()
    s = BY["shot_god"]
    for i, name in enumerate(SD.PROCS):
        if name not in SD.ICONS:
            continue
        td = s.start + SD.god_row_t(i)
        tl = td + SD.ICON_LAND
        if not td - 0.1 <= t < tl + 0.02:
            continue
        g = fig_geom(t)
        src = g["hand"]
        dst = SD.icon_xy(i)
        sp = SD.icon_sprite(SD.ICONS[name])
        if t < td:  # lifts in her hand
            k = clamp((t - (td - 0.1)) / 0.1)
            place(layer, haloed(sp, 0.8 * k), src, 1.6, k)
            continue
        u = clamp((t - td) / SD.ICON_LAND)
        pos = bezier(src, dst, -0.25, ease_io(u))
        place(layer, haloed(sp, 0.7 * (1 - u)), pos, lerp(1.6, 1.0, ease_io(u)))
    return layer


OVERLAY = {"shot_eggplant": ov_eggplant, "shot_nutrients": ov_nutrients, "shot_tomato": ov_tomato,
           "shot_antioxidants": ov_antioxidants, "shot_tabby": ov_tabby, "shot_purr": ov_purr, "shot_god": ov_god}


# ================================================================ filters on her layer

_RAMP = None


def _ramp_luma():
    global _RAMP
    if _RAMP is None:
        g = Image.new("L", (256, 1))
        g.putdata(list(range(256)))
        rgb = list(tk.tint_colorize(g, "blue").getdata())
        _RAMP = [0.299 * r + 0.587 * gg + 0.114 * b for r, gg, b in rgb]
    return _RAMP


_LUTS: dict = {}


def poster_lut(levels: int) -> list:
    """Luma of a ramp colour -> the ramp position quantised to `levels` steps."""
    if levels not in _LUTS:
        rl = _ramp_luma()
        lut = []
        for y in range(256):
            i = min(255, bisect.bisect_left(rl, y))
            q = round(i / 255 * (levels - 1)) / (levels - 1)
            lut.append(int(round(q * 255)))
        _LUTS[levels] = lut
    return _LUTS[levels]


FIG_BOX = (kit.LEFT[0] + 4, kit.LEFT[1] + 14, kit.LEFT[2] - 4, kit.LEFT[3] - 78)


def posterize(layer: Image.Image, levels: int) -> Image.Image:
    reg = layer.crop(FIG_BOX)
    a = reg.getchannel("A")
    lum = reg.convert("RGB").convert("L").point(poster_lut(levels))
    rgb = tk.tint_colorize(lum, "blue").convert("RGBA")
    rgb.putalpha(a)
    out = layer.copy()
    out.paste(rgb, FIG_BOX[:2])
    return out


def levels_at(t: float) -> int:
    """Her colour depth: full, then down to the fp8 format's levels (8, 4, 2) in quick steps, then back."""
    if T42 <= t < T43:
        dt = t - T42
        if dt < 6 / FPS:
            return [64, 32, 16, 12, 10, 8][int(dt * FPS)]
        k = SD.fmt_at(t)
        if k >= 1:
            ds = t - SD.FMT_T[k - 1]
            if ds < 3 / FPS:
                return [[6, 5, 4], [3, 3, 2]][k - 1][int(ds * FPS)]
        return SD.LEVELS[k]
    if T43 <= t < T43 + 6 / FPS:
        return [2, 3, 4, 6, 8, 16][int((t - T43) * FPS)]
    return 256


TRANCE_TAIL = SD.TRANCE_TAIL
heat_at = SD.heat_at


SCR = "youmestayloveseadeep"


def dissolve(layer: Image.Image, t: float, heat: float) -> Image.Image:
    """Her core stays; rows tear sideways, edge cells drop out, and sampled letters drift around her."""
    if heat <= 0.01:
        return layer
    rnd = random.Random(int(t * FPS) * 7)
    out = layer.copy()
    x0, y0, x1, y1 = FIG_BOX
    reg = layer.crop(FIG_BOX)
    a = reg.getchannel("A")
    # row tears
    for r in range(0, y1 - y0, CH):
        if rnd.random() < 0.3 * heat:
            off = int(rnd.choice((-1, 1)) * rnd.randint(1, 3) * CW * (0.4 + heat))
            strip = reg.crop((0, r, reg.width, min(reg.height, r + CH)))
            clear = Image.new("RGBA", strip.size, (0, 0, 0, 0))
            out.paste(clear, (x0, y0 + r))
            out.alpha_composite(strip, (x0 + off, y0 + r))
    # edge cells drop out, sampled letters appear around her
    cells = a.resize(((x1 - x0) // CW, (y1 - y0) // CH), Image.BOX)
    halo = cells.point(lambda v: 255 if v > 30 else 0).filter(ImageFilter.MaxFilter(7))
    core = cells.point(lambda v: 255 if v > 30 else 0).filter(ImageFilter.MinFilter(5))
    edge = cells.point(lambda v: 255 if v > 30 else 0)
    Hh, Co, E = halo.load(), core.load(), edge.load()
    d = ImageDraw.Draw(out)
    for r in range(cells.height):
        for q in range(cells.width):
            x, y = x0 + q * CW, y0 + r * CH
            if E[q, r] and not Co[q, r] and rnd.random() < 0.35 * heat:
                d.rectangle([x, y, x + CW - 1, y + CH - 1], fill=(0, 0, 0, 0))
            elif Hh[q, r] and not E[q, r] and rnd.random() < 0.22 * heat:
                lv = rnd.uniform(0.25, 0.75)
                out.paste(tk.mix(tk.BLUE_TEXT, lv) + (int(255 * min(1.0, 0.4 + heat)),), (x, y),
                          _glyph(rnd.choice(SCR)))
    return out


def her_filter(layer: Image.Image, t: float) -> Image.Image:
    lv = levels_at(t)
    if lv < 256:
        layer = posterize(layer, lv)
    hv = heat_at(t)
    if hv > 0.01:
        layer = dissolve(layer, t, hv)
    return layer


def install_filter() -> None:
    """kit.her_layer is wrapped once: inside this section's windows her layer passes through her_filter."""
    if getattr(kit.her_layer, "_deploy", False):
        return
    orig = kit.her_layer

    def her_layer(t, call, box_level=1.0):
        layer = orig(t, call, box_level)
        if T42 <= t < T43 + 0.3 or T45 - 0.3 <= t < T46 + SD.TRANCE_TAIL + 0.05:
            layer = her_filter(layer, t)
        return layer

    her_layer._deploy = True
    kit.her_layer = her_layer


# ================================================================ helpers for the cuts

def fly_text(layer, s, fa, xa, fb, xb, u, bend=0.2, halo=0.0, lift=0.0, big=1.0, sb=None):
    """Text carried from draw origin xa (font fa = (path, size, colour)) to draw origin xb (font fb), along an arc.
    Centres travel; the sprite scales between the two sizes (bigger mid-flight when big > 1) and cross-fades into
    the destination's own glyphs over the last 30 %."""
    spa, offa = text_sprite(s, *fa)
    spb, offb = text_sprite(sb or s, *fb)
    ca = (xa[0] + offa[0] + spa.width / 2, xa[1] + offa[1] + spa.height / 2)
    cb = (xb[0] + offb[0] + spb.width / 2, xb[1] + offb[1] + spb.height / 2)
    pos = bezier(ca, cb, bend, u)
    uc = clamp(u)
    k = fb[1] / fa[1]
    sc = lerp(1.0, k, uc) * (1 + (big - 1) * math.sin(math.pi * uc))
    q = clamp((uc - 0.7) / 0.3)
    a = brighten(spa, lift) if lift > 0 else spa
    if halo > 0:
        a = haloed(a, halo)
    place(layer, a, pos, sc, 1 - q)
    if q > 0:
        place(layer, spb, pos, sc / k, q)


def snap(u: float, over: float = 0.05) -> float:
    """Carrier landing: ease in-out onto the target by 85 % of the flight, overshoot a little, lock in at 100 %."""
    if u < 0.85:
        return ease_io(u / 0.85)
    return 1 + over * math.sin(math.pi * clamp((u - 0.85) / 0.15))


def seg_dist(x, y, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    u = clamp(((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy))
    return math.hypot(x - (ax + u * dx), y - (ay + u * dy))


def compose(t, n, content, ctx, over=None, retract=None, her_layer=None, overlay=True, glow=0.0):
    """What v2.frame does for one frame, before post: content, her, the shot's overlay, carriers, chrome."""
    import v2
    s = kit.engine.shot_at(t)
    r, shell = v2.retract_at(t)
    if retract is not None:
        r = retract
    img = content.convert("RGBA")
    layer = her_layer if her_layer is not None else v2.her(t, n, glow, 1 - r)
    img.alpha_composite(layer)
    if overlay:
        ov = OVERLAY.get(s.fn.__name__)
        if ov is not None:
            lay = ov(t, n)
            if lay is not None:
                img.alpha_composite(lay)
    if over is not None:
        img.alpha_composite(over)
    return kit.chrome(img, t, ctx, r, shell)


# ================================================================ cut 34: the crash line retypes, the UI unfolds

TRAP_XY = (40, 320)
TRAP_F = (tk.F_MONO_B, 28)


class C34(Cut):
    """strange -> eggplant (UNFOLD). The chorus ends on black with 'sim.state = TRAPPED'. On the downbeat of
    "If I'm an eggplant" TRAPPED scrambles into RUNNING and '  role=deploy' is typed after it; on the next half
    beat the line lights up and the UI unfolds from that text row, cell by cell, her pane first. 'role=deploy'
    lifts off the line and lands in her pane title on beat 160. The lyric stays through the black."""
    post = 0.62

    def __init__(self, a, b):
        super().__init__(a, b)
        self.pre = self.T - 1759 / FPS + 1e-4  # the approved chorus goes black on frame 1759
        self.U = beat_t(159.5)       # the unfold starts from the text row
        self.LAND = beat_t(160)      # role=deploy lands in her title

    def line_parts(self, t):
        """(text, colour) runs of the status line at time t, and how much of '  role=deploy' is typed."""
        T = self.T
        if t < T:
            return [("sim.state = ", tk.red(0.95)), ("TRAPPED", tk.red(0.95))], 0, tk.red(0.9)
        k = clamp((t - T) / (3 / FPS))
        rnd = random.Random(int(t * FPS))
        word = "".join("RUNNING"[j] if t - T > 0.03 + j * 0.013 else rnd.choice(tk.SCR) for j in range(7))
        col = tuple(int(v) for v in lerp(tk.red(0.95), tk.amb(1.0), k))
        typed = int(clamp((t - (T + 2 / FPS)) / (3 / FPS)) * len("  role=deploy"))
        return [("sim.state = ", col), (word, col)], typed, tk.amb(0.95)

    def title_slot(self, t):
        f = tk.font(tk.F_HEAD, 13)
        spin = "|/-\\"[int(t * 8) % 4]
        pre = f" {spin} /dev/me  "
        x = kit.LEFT[0] + 12 + f.getlength(pre)
        return (x, kit.LEFT[1] - 10), f.getlength("role=deploy")

    def render(self, t, n):
        T, U, LAND = self.T, self.U, self.LAND
        approved = kit.v1.approved
        if t < T:
            body = approved.raw(t, n, self.a)
            if not body["black"]:
                return approved.render_frame(n)
        nc, nctx = self.new(t, n)
        f = tk.font(*TRAP_F)
        # the old picture: black, the status line, the lyric (chrome fully retracted: only the words stay)
        old = kit.stage.background(t).convert("RGBA")
        d = ImageDraw.Draw(old)
        parts, typed, cur = self.line_parts(t)
        x = TRAP_XY[0]
        lift = clamp((t - (U - 2 / FPS)) / (2 / FPS)) if t < U + 0.1 else 0.0
        for s, col in parts:
            if lift > 0:
                col = tuple(int(v) for v in lerp(col, (235, 240, 255), 0.5 * lift))
            d.text((x, TRAP_XY[1]), s, font=f, fill=col)
            x += f.getlength(s)
        role_x = x + f.getlength("  ")
        if typed and t < U:  # from U on, 'role=deploy' is the carrier
            d.text((x, TRAP_XY[1]), "  role=deploy"[:typed], font=f, fill=tk.blue(1.0))
        if t < U:
            cx = x + (f.getlength("  role=deploy"[:typed]) if typed else 0) + 8
            if t < T:
                cx = 380
            if int(t * 6) % 2 == 0 or T <= t:
                d.rectangle([cx, 324, cx + 14, 354], fill=cur)
        old = kit.chrome(old, t, nctx, 1.0, None)
        if t < U:
            return kit.engine.post(old.convert("RGB"), None)
        # the new picture, complete: content, her (straight into the eggplant pose, no re-render from the chorus)
        import v2
        call = v2.call_of(self.b)
        her_layer = kit.her_layer(t, call, 1.0)
        (sx, sy), sw = self.title_slot(t)
        if t < LAND:  # her title waits for its word
            ImageDraw.Draw(her_layer).rectangle([sx - 1, sy + 1, sx + sw + 2, sy + 19], fill=tk.BG + (255,))
        new = compose(t, n, nc, nctx, her_layer=her_layer, retract=0.0)
        seg = ((TRAP_XY[0], 334), (role_x - 10, 334))
        speed = 2600.0

        def delay(px, py):
            dd = seg_dist(px, py, *seg)
            return U + dd / speed * (0.45 if px < kit.LEFT[2] + 8 else 1.0)

        img = reveal(old, new, t, delay, region=(0, 0, W, H), cell=(8, 16), dur=0.07, seed=34, density=0.5)
        over = blank()
        # the scan line the UI opens from
        k = clamp((t - U) / 0.25)
        if k < 1:
            od = ImageDraw.Draw(over)
            half = lerp(200, 700, ease_out(k))
            mx = (seg[0][0] + seg[1][0]) / 2
            a = int(220 * (1 - k))
            od.line([max(0, mx - half), 335, min(W, mx + half), 335], fill=(230, 238, 255, a), width=2)
        # 'role=deploy' flies into her pane title
        if t < LAND + 0.1:
            u = clamp((t - U) / (LAND - U))
            fly_text(over, "role=deploy", (tk.F_MONO_B, 28, tk.blue(1.0)), (role_x, TRAP_XY[1]),
                     (tk.F_HEAD, 13, tk.mix(tk.AMBER, 0.85)), (sx, sy), snap(u),
                     bend=-0.18, halo=0.8 * (1 - u), lift=0.3 * (1 - u))
        img.alpha_composite(over)
        return kit.engine.post(img.convert("RGB"), None)


# ================================================================ cut 35: me := eggplant heads the table

class C35(Cut):
    """eggplant -> nutrients (CARRY). 'me := eggplant' lights up, then travels on one arc into the table header
    (landing on the next beat) while the classifier drains into it; the table unrolls beneath the header.
    On the 'Then' downbeat the eggplant suit peels off her from the top while she keeps dancing."""
    pre, post = 0.3, 0.62

    def render(self, t, n):
        T = self.T
        land = T + BEAT
        lift = clamp((t - (T - 0.25)) / 0.2)
        oc, octx = self.old(t, n, me_line=t < T - 0.25)
        nc, nctx = self.new(t, n, head=t >= land)
        content = reveal(oc, nc, t, inward((560, 438), T - 0.22, T + 0.18, 820.0), seed=35)
        over = blank()
        if T - 0.25 <= t < land + 0.1:
            u = clamp((t - T) / (land - T))
            fly_text(over, "me := eggplant", (tk.F_HEAD, 34, tk.blue(1.0)), (430, 420),
                     (tk.F_HEAD, 30, tk.blue(1.0)), SD.NUTR_HEAD, snap(u),
                     bend=0.22, halo=0.9 * lift * (1 - u), lift=0.35 * lift * (1 - u))
        return Frame(content, self.pick(t, octx, nctx), over)


# ================================================================ cut 36: you becomes the prompt, the table the noise

class C36(Cut):
    """nutrients -> tomato (CARRY + MORPH). 'you' leaves 'Given to: you' and lands in the prompt
    generate("a tomato", seed=me, for=you). The table re-quantises in place into the generator's first frame
    (same rectangle, 6 px cells), spreading from where 'you' left, then denoises into the tomato.
    She inflates into a tomato."""
    pre, post = 0.3, 0.45

    def table_lum(self, n):
        if not hasattr(self, "_lum"):
            oc, _ = self.old(self.T - 0.01, n, you=False)
            lum = oc.crop(SD.GEN).convert("L").resize((110, 70), Image.BOX)
            self._lum = lum.point(lambda v: min(255, int(v * 3.2)))
        return self._lum

    def render(self, t, n):
        T = self.T
        land = beat_t(beat_of(T) + 0.5)
        lift = clamp((t - (T - 0.25)) / 0.2)
        oc, octx = self.old(t, n, you=t < T - 0.25)
        nc, nctx = self.new(t, n, prompt_you=t >= land, from_lum=self.table_lum(n))
        src = SD.you_xy()
        content = reveal(oc, nc, t, radial((src[0] + 20, src[1] + 12), T - 0.06, 2600.0), seed=36)
        over = blank()
        if T - 0.25 <= t < land + 0.1:
            u = clamp((t - T) / (land - T))
            fly_text(over, "you", (tk.F_MONO_B, 20, tk.blue(1.0)), src, (tk.F_MONO_B, 20, tk.blue(1.0)),
                     SD.prompt_you_xy(), snap(u), bend=0.25,
                     halo=0.9 * lift * (1 - u), lift=0.4 * lift * (1 - u), big=1.7)
        return Frame(content, self.pick(t, octx, nctx), over)


# ================================================================ cut 37: the tomato becomes node C1

class C37(Cut):
    """tomato -> antioxidants (CARRY, kept from v1 with easing and a landing). The generated tomato shrinks cell
    by cell (redrawn at every size, the 6 px cells stay) and lands as the first node of the lycopene chain,
    labelled; the chain grows out of it. Her tomato suit deflates back into her."""
    pre, post = 0.3, 0.8

    def render(self, t, n):
        T = self.T
        land = self.land()
        oc, octx = self.old(t, n, tile=t < T)
        nc, nctx = self.new(t, n)
        node = SD.chain_pts(t)[0]
        content = reveal(oc, nc, t, inward(node, T - 0.05, T + 0.3, 800.0), seed=37)
        over = blank()
        if T - 0.2 <= t < land + 0.02:
            lift = clamp((t - (T - 0.2)) / 0.2)
            u = clamp((t - T) / (land - T))
            e = ease_out(u)
            cols = max(8, round(lerp(70, 8, e)))
            sp = SD.tomato_icon(cols)
            src = (SD.GEN[0] + 55 * 6, SD.GEN[1] + 35 * 6)
            pos = bezier(src, node, 0.18, e)
            place(over, haloed(sp, 0.6 * lift * (1 - e), radius=6), pos)
        return Frame(content, self.pick(t, octx, nctx), over)

    def land(self):
        return self.T + BEAT


# ================================================================ cut 38: the chain becomes her cat ears

class C38(Cut):
    """antioxidants -> tabby (MORPH). The lycopene nodes lift off the chain one after another and fly on arcs
    to her head, where they lock into two ear triangles and six whiskers on the downbeat of "If I'm a tabby ...".
    She keeps dancing; the classifier's top-5 decodes out of where the chain was."""
    pre, post = 0.5, 0.35

    def times(self, i):
        land = self.T - 0.04 + 0.004 * i
        return land - 0.42 - 0.012 * (i % 4), land

    def render(self, t, n):
        T = self.T
        tm = {i: self.times(i) for i in range(1, SD.CHAIN_N)}
        gone = lambda i: clamp((t - tm[i][0]) / 0.05) if i in tm else 0.0  # noqa: E731
        oc, octx = self.old(t, n, gone=gone)
        nc, nctx = self.new(t, n)
        content = reveal(oc, nc, t, radial((780, 250), T - 0.12, 1500.0), seed=38)
        over = blank()
        d = ImageDraw.Draw(over)
        if t < T + 0.08:
            pts = SD.chain_pts(min(t, T))
            tg = ear_targets(t)
            lift = clamp((t - (T - self.pre)) / 0.12)
            for i in range(1, SD.CHAIN_N):
                td, tl = tm[i]
                x, y = pts[i]
                if t < td:
                    if lift > 0:  # lit before they go
                        d.ellipse([x - 10, y - 10, x + 10, y + 10], outline=tk.blue(1.0) + (int(160 * lift),))
                    continue
                u = clamp((t - td) / (tl - td))
                if u >= 1 and t > tl + 0.06:
                    continue
                px, py = bezier((x, y), tg[i - 1], 0.3 if i < 11 else -0.3, ease_in(u))
                r = lerp(7, 3, ease_in(u)) * (1 + 0.5 * math.sin(math.pi * u))
                col = lerp(tk.amb(0.95), tk.blue(1.0), u)
                a = 255 if u < 1 else int(255 * (1 - (t - tl) / 0.06))
                d.ellipse([px - r, py - r, px + r, py + r], fill=rgba(col, a))
                if r > 5:
                    d.text((px - 4, py - 8), "C", font=tk.font(tk.F_MONO_B, 12), fill=tk.BG + (a,))
        glow = max(0.0, 1 - abs(t - T) / 0.2) * 0.5
        return Frame(content, self.pick(t, octx, nctx), over, glow)


# ================================================================ cut 39: 281 names the purr

class C39(Cut):
    """tabby -> purr (CARRY). The big '281' lights up and flies up into the spectrogram's title slot, where it
    reads 'class 281 -> purr.wav'; the spectrogram decodes outward from where the number left. No backing box.
    Her ears fold back into her head over six frames."""
    pre, post = 0.3, 0.6

    def render(self, t, n):
        T = self.T
        land = T + BEAT
        lift = clamp((t - (T - 0.25)) / 0.2)
        oc, octx = self.old(t, n, n281=t < T - 0.25)
        nc, nctx = self.new(t, n, t281=t >= land, title_age=BEAT - 0.05)
        content = reveal(oc, nc, t, radial((530, 380), T - 0.08, 1500.0), seed=39)
        over = blank()
        if T - 0.25 <= t < land + 0.1:
            u = clamp((t - T) / (land - T))
            fly_text(over, "281", (tk.F_HEAD, 120, tk.blue(1.0)), SD.N281, (tk.F_MONO_B, 22, tk.blue(1.0)),
                     SD.purr_281_xy(), snap(u), bend=-0.15,
                     halo=0.9 * lift * (1 - u), lift=0.3 * lift * (1 - u))
        return Frame(content, self.pick(t, octx, nctx), over)


# ================================================================ cut 40: the spectrogram collapses into PID 1

class C40(Cut):
    """purr -> god (UNFOLD, reversed: a collapse into the shell). From six frames before the cut the whole purr
    panel squeezes vertically into one bright row at the top; the chrome retracts into shell staging (automatic);
    the row narrows and decodes into 'PID 1   systemd', the root of the process tree, whose children then type in
    one per sixteenth. The props she wore fly from her hand into the rows cats, tomatoes, eggplants (OVERLAY)."""
    pre, post = 0.26, 0.3
    TY = SD.GOD_ROOT[1] + 12

    def render(self, t, n):
        T = self.T
        if t < T:
            k = ease_in(clamp((t - (T - self.pre)) / self.pre))
            oc, octx = self.old(t, n, squash=(k, self.TY))
            return Frame(oc, octx)
        u = clamp((t - T) / 0.26)
        nc, nctx = self.new(t, n, root=u >= 1, root_age=-1.0)
        over = blank()
        if u < 1:
            d = ImageDraw.Draw(over)
            f = tk.font(tk.F_MONO_B, 22)
            txt = "PID 1   systemd"
            tw = f.getlength(txt)
            x0 = 430
            x1 = lerp(430 + 64 * 11, x0 + tw, ease_io(u))
            hgt = lerp(2, 20, ease_io(u))
            a = 1 - ease_in(u)
            d.rectangle([x0, self.TY - hgt / 2, x1, self.TY + hgt / 2], fill=rgba(tk.amb(0.9), 180 * a))
            d.line([x0, self.TY, x1, self.TY], fill=rgba((235, 240, 255), 255 * a), width=2)
            if u > 0.35:
                rnd = random.Random(int(t * FPS))
                m = int(len(txt) * clamp((u - 0.35) / 0.5))
                s = "".join(txt[j] if j < m - 2 else rnd.choice(tk.SCR) for j in range(min(len(txt), m + 1)))
                d.text((SD.GOD_ROOT[0], SD.GOD_ROOT[1]), s, font=f, fill=rgba(tk.amb(0.95), 255 * clamp(u * 2)))
        return Frame(nc, nctx, over)


# ================================================================ cut 41: the tree folds into the goal

class C41(Cut):
    """god -> proof (CARRY). The chrome and the panel frames draw back (automatic retraction; the prover's
    panel grows from its corners). The tree rows fold one by one, two frames apart, into the goal line
    '⊢ ∃ me, observed_by you me', which types as they arrive; the infoview opens its hypothesis slot, and
    '1049 you' slides into it as 'you : Witness'."""
    pre, post = 0.25, 0.62

    def rows(self, t):
        T = self.T
        ys = {-1: SD.GOD_ROOT[1], 8: 520, **{i: SD.god_row_xy(i)[1] for i in range(7)}}
        order = sorted(ys, key=lambda i: -abs(ys[i] - SD.GOAL_XY[1]))  # the farthest rows set off first

        def col(i):
            if i == 7:  # '1049' stays where it was and fades; its 'you' is the carrier
                return 0, 1.0 - clamp((t - T) / 0.25)
            j = order.index(i)
            ts = T - 0.36 + j / FPS
            u = ease_in(clamp((t - ts) / 0.18))
            dy = (SD.GOAL_XY[1] - ys[i]) * u
            return dy, 1.0 - clamp((u - 0.25) / 0.45)
        return col

    def render(self, t, n):
        T = self.T
        land = T + BEAT
        col = self.rows(t)
        oc, octx = self.old(t, n, collapse=col, you=t < T - 0.02)
        pane = ease_out(clamp((t - T) / 0.3))
        nc, nctx = self.new(t, n, pane=pane, info=ease_out(clamp((t - T - 0.05) / 0.25)), code_age=0.12,
                            goal_age=0.12, witness=t >= land, wit_age=land - T)
        base = oc if t < T else nc
        content = base.copy()
        if t >= T:
            content.paste(ink(oc, t, PANE), (PANE[0], PANE[1]), ink(oc, t, PANE))
        over = blank()
        if T - 0.02 <= t < land + 0.1:
            u = clamp((t - (T - 0.02)) / (land - T + 0.02))
            x, y = SD.god_row_xy(7)
            f19 = tk.font(tk.F_MONO, 19)
            src = (x + f19.getlength("├── 1049  "), y)
            lift = clamp((t - (T - 0.02)) / 0.1)
            fly_text(over, "you", (tk.F_MONO, 19, tk.blue(0.95)), src, (tk.F_SYM, 21, tk.blue(1.0)), SD.WIT_XY,
                     ease_io(u), bend=-0.12, halo=0.8 * lift * (1 - u), lift=0.3 * (1 - u), big=1.5)
        return Frame(content, self.pick(t, octx, nctx), over)


# ================================================================ cut 42: the proof term is encoded

class C42(Cut):
    """proof -> fp8 (CARRY). 'you' lifts out of 'proof term: you' while the theorem drains into it, flies to the
    encoder's input slot encode(y o u), and its first letter falls into the byte row as its eight bits
    ('y' = 0x79), one box per frame. 'E4M3' is typed only after the bits have landed. She is re-quantised in
    place: her colour ramp steps down to 8 levels over six frames (her layer filter)."""
    pre, post = 0.3, 0.95

    def render(self, t, n):
        T = self.T
        land = beat_t(beat_of(T) + 0.5)
        drop = beat_t(beat_of(T) + 1.0)
        bits_done = drop + 8 / FPS + 0.12
        lift = clamp((t - (T - 0.25)) / 0.2)
        nb = sum(1 for i in range(8) if t >= drop + i / FPS + 0.12)
        oc, octx = self.old(t, n, term_you=t < T - 0.25)
        nc, nctx = self.new(t, n, input=t >= land, bits_n=nb, label_age=bits_done - T)
        src = SD.proof_you_xy()
        ox, oy = 440 + tk.font(tk.F_MONO_B, 18).getlength("encode("), SD.ENC_Y
        content = reveal(oc, nc, t, inward((src[0] + 18, src[1] + 12), T - 0.22, T + 0.1, 760.0), seed=42)
        over = blank()
        if T - 0.25 <= t < land + 0.1:
            u = clamp((t - T) / (land - T))
            e = ease_io(u)
            for j, ch in enumerate("you"):
                a = (src[0] + tk.font(tk.F_MONO_B, 22).getlength("you"[:j]), src[1])
                b = (ox + j * 30, oy)
                fly_text(over, ch, (tk.F_MONO_B, 22, tk.blue(1.0)), a, (tk.F_HEAD, 22, tk.blue(1.0)), b,
                         snap(u), bend=0.2 + 0.05 * j, halo=0.8 * lift * (1 - u),
                         lift=0.3 * lift * (1 - u), big=1.5)
        if drop - 0.1 <= t < bits_done:  # 'y' falls into the row and splits into its bits
            bits = SD.bits_of(0)
            for i in range(8):
                t0 = drop + i / FPS - 0.08
                u = clamp((t - t0) / 0.2)
                if u <= 0 or t >= drop + i / FPS + 0.14:
                    continue
                p = bezier((ox + 6, oy + 14), (SD.box_x(i) + 38, 160), 0.1, ease_in(u))
                text_at(over, "01"[bits[i]], tk.F_HEAD, 32, tk.blue(1.0) if i > 4 else tk.amb(1.0),
                        (p[0] - 10, p[1] - 20), lerp(0.7, 1.0, u), 1.0, halo=0.6 * (1 - u))
        return Frame(content, self.pick(t, octx, nctx), over)


# ================================================================ cut 43: the byte row bends into the clock

DIALC = (SD.DIAL["cx"], SD.DIAL["cy"])
PEAKS = SD.F.PEAK_WINDOWS


class C43(Cut):
    """fp8 -> ampm (MORPH). The eight exponent boxes of UE8M0 slide along arcs onto the clock face and each opens
    into one eighth of the dial ring; the hour labels spread from the ring, then 'AM' types in the centre.
    Her colour comes back 2 -> 4 -> 8 -> full over six frames (her layer filter)."""
    pre, post = 0.25, 0.95

    def render(self, t, n):
        T = self.T
        t0, land = T + 0.02, beat_t(beat_of(T) + 1.0)
        ring_done = land + 0.14
        oc, octx = self.old(t, n, row=t < t0)
        labels = clamp((t - ring_done) / 0.28)
        nc, nctx = self.new(t, n, ring=t >= ring_done, labels=labels, hand=t >= ring_done + 0.2,
                            center=t >= ring_done + 0.2, center_age=ring_done + 0.2 - T, side=t >= ring_done + 0.2)
        content = reveal(oc, nc, t, radial(DIALC, T - 0.1, 1200.0), seed=43)
        over = blank()
        d = ImageDraw.Draw(over)
        rr = SD.DIAL["rr"]
        bits = SD.bits_of(2)
        if t < ring_done + 0.02:
            lift = clamp((t - (T - 0.2)) / 0.2)
            for i in range(8):
                ang = math.radians(-90 + 45 * i + 22.5)
                tgt = (DIALC[0] + rr * math.cos(ang), DIALC[1] + rr * math.sin(ang))
                src = (SD.box_x(i) + 38, 160)
                u = clamp((t - t0 - 0.012 * i) / (land - t0))
                e = ease_io(u)
                cx, cy = bezier(src, tgt, 0.25, e)
                w, hgt = lerp(76, 26, e), lerp(80, 26, e)
                col = rgba(lerp(tk.amb(0.95), tk.blue(0.8), e))
                if t < land:
                    if lift > 0 and t < t0:
                        d.rectangle([cx - w / 2 - 3, cy - hgt / 2 - 3, cx + w / 2 + 3, cy + hgt / 2 + 3],
                                    outline=rgba(tk.blue(1.0), 120 * lift), width=1)
                    d.rectangle([cx - w / 2, cy - hgt / 2, cx + w / 2, cy + hgt / 2], outline=col, width=2)
                    text_at(over, str(bits[i]), tk.F_HEAD, 32, tk.amb(1.0), (cx - 10, cy - 20), lerp(1, 0.6, e))
                else:  # each box opens into its eighth of the ring
                    k = ease_out(clamp((t - land) / 0.14))
                    a0 = -90 + 45 * i + 22.5 - 22.5 * k
                    a1 = -90 + 45 * i + 22.5 + 22.5 * k
                    bb = [DIALC[0] - rr, DIALC[1] - rr, DIALC[0] + rr, DIALC[1] + rr]
                    d.arc(bb, a0, a1, fill=rgba(lerp(tk.blue(0.7), tk.blue(0.45), k)), width=10)
                    for h0, h1 in PEAKS:
                        p0, p1 = max(a0, h0 / 24 * 360 - 90), min(a1, h1 / 24 * 360 - 90)
                        if p1 > p0:
                            d.arc(bb, p0, p1, fill=rgba(tk.anom(0.95), 255 * k), width=10)
        return Frame(content, self.pick(t, octx, nctx), over)


# ================================================================ cut 44: the M of PM switches role

class C44(Cut):
    """ampm -> role (CARRY). The M of 'PM' drops from the dial centre to the bottom left and ' -> S' is typed
    after it; the dial ring shrinks and squares off into the first tag box <|System|>; the other tags come in
    only after the dial is gone."""
    pre, post = 0.3, 0.7

    def render(self, t, n):
        T = self.T
        land = beat_t(beat_of(T) + 0.5)
        box_done = T + 0.38
        lift = clamp((t - (T - 0.25)) / 0.2)
        oc, octx = self.old(t, n, center=t < T - 0.25, ring=t < T - 0.05)
        nc, nctx = self.new(t, n, ms=(land - T) if t >= land else False, tags_age=box_done - T + 0.05,
                            first_tag=t >= box_done)
        content = reveal(oc, nc, t, inward(DIALC, T - 0.1, T + 0.2, 500.0), seed=44)
        over = blank()
        d = ImageDraw.Draw(over)
        if T - 0.25 <= t < T + 0.14:  # 'P' stays with the dial and fades with it, 'M' lights up
            text_at(over, "P", tk.F_HEAD, 34, tk.amb(1.0), (DIALC[0] - 40, DIALC[1] - 20), 1.0,
                    1 - clamp((t - T) / 0.14))
        if T - 0.25 <= t < land + 0.1:
            u = clamp((t - T) / (land - T))
            fly_text(over, "M", (tk.F_HEAD, 34, tk.amb(1.0)), SD.PM_M, (tk.F_HEAD, 40, tk.amb(0.9)), SD.MS_XY,
                     ease_in(u) if u < 1 else 1.0, bend=0.12, halo=0.9 * lift * (1 - u), lift=0.3 * lift)
        if T - 0.05 <= t < box_done + 0.02:  # the ring squares off into the first tag
            u = ease_io(clamp((t - (T - 0.05)) / (box_done - T + 0.05)))
            rect, _, _, _ = SD.tag_rect(0, 0)
            rcx, rcy = (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2
            hw, hh = (rect[2] - rect[0]) / 2, (rect[3] - rect[1]) / 2
            rr = SD.DIAL["rr"]
            pts = []
            for j in range(72):
                a = math.tau * j / 72
                ca, sa = math.cos(a), math.sin(a)
                p_c = (DIALC[0] + rr * ca, DIALC[1] + rr * sa)
                s = min(hw / max(1e-6, abs(ca)), hh / max(1e-6, abs(sa)))
                p_r = (rcx + s * ca, rcy + s * sa)
                pts.append(lerp(p_c, p_r, u))
            wdt = max(2, round(lerp(10, 2, u)))
            col = rgba(lerp(tk.blue(0.45), tk.amb(0.6), u))
            d.line(pts + [pts[0]], fill=col, width=wdt)
            pa = 1 - clamp(u / 0.35)  # the peak windows ride along and fade
            if pa > 0.02:
                for h0, h1 in PEAKS:
                    a0, a1 = (h0 / 24 * 360 - 90) % 360, (h1 / 24 * 360 - 90) % 360
                    seg = [pts[j] for j in range(72) if a0 <= j * 5 <= a1]
                    if len(seg) > 1:
                        d.line(seg, fill=rgba(tk.anom(0.95), 255 * pa), width=wdt)
        return Frame(content, self.pick(t, octx, nctx), over)


# ================================================================ cut 45: the template spirals into the sampler

class C45(Cut):
    """role -> trance (CAMERA, inside the visualisation pane only). The chat template's ink spins and is drawn
    inward into the spiral's centre, the outer rings turning faster (a swirl, 12 frames ease-in-out); the
    sampling spiral then grows out of the same centre and keeps turning. Her pane, the chrome and the lyric
    band do not move; her temperature dissolve starts with the same parameter (her layer filter)."""
    pre, post = 0.46, 0.45
    IN = (406, 58, 1163, 603)

    def render(self, t, n):
        T = self.T
        p = ease_io(clamp((t - (T - self.pre)) / (self.pre + 0.06)))
        T0 = T - 0.12  # the spiral starts to grow from the centre while the template is still spiralling in
        grow = clamp((t - T0) / 0.5)
        oc, octx = self.old(t, n)
        nc, nctx = self.new(t, n, spiral_n=int(160 * ease_out(grow)))
        x0, y0, x1, y1 = self.IN
        if t < T0:  # the old pane frame and title stay put; its content is drawn spinning below
            content = oc.copy()
            content.paste(kit.stage.background(t).crop(self.IN), (x0, y0))
        else:  # the new pane's title decodes in from the left; the spiral grows inside
            content = reveal(oc, nc, t, sweep((PANE[0], 0), (1, 0), T0, 6000.0), region=(PANE[0], 44, PANE[2], 70),
                             seed=45)
            content.paste(nc.crop(self.IN), (x0, y0))
        if p < 0.999:
            ik = ink(oc, t, self.IN)
            cx, cy = SD.SPIRAL_C[0] - x0, SD.SPIRAL_C[1] - y0
            layer = Image.new("RGBA", ik.size, (0, 0, 0, 0))
            rmax = math.hypot(max(cx, ik.width - cx), max(cy, ik.height - cy))
            bands = 7
            scale = lerp(1.0, 0.04, p)
            for j in range(bands):
                r0, r1 = rmax * j / bands, rmax * (j + 1) / bands
                m = Image.new("L", ik.size, 0)
                md = ImageDraw.Draw(m)
                md.ellipse([cx - r1, cy - r1, cx + r1, cy + r1], fill=255)
                if r0 > 0:
                    md.ellipse([cx - r0, cy - r0, cx + r0, cy + r0], fill=0)
                part = ik.copy()
                part.putalpha(ImageChops.multiply(ik.getchannel("A"), m))
                ang = -(300 * p) * (0.35 + 0.65 * (j + 0.5) / bands)
                part = part.rotate(ang, resample=Image.BICUBIC, center=(cx, cy))
                if scale < 0.999:
                    sw, sh = max(1, int(ik.width * scale)), max(1, int(ik.height * scale))
                    small = part.resize((sw, sh), Image.BILINEAR)
                    part = Image.new("RGBA", ik.size, (0, 0, 0, 0))
                    part.alpha_composite(small, (int(cx - cx * scale), int(cy - cy * scale)))
                layer.alpha_composite(part)
            if p > 0.75:
                layer = tk.scale_alpha(layer, 1 - (p - 0.75) / 0.25)
            content = content.convert("RGBA")
            content.alpha_composite(layer, (x0, y0))
            content = content.convert("RGB")
        return Frame(content, self.pick(t, octx, nctx))


CUTS = {34: C34, 35: C35, 36: C36, 37: C37, 38: C38, 39: C39, 40: C40, 41: C41, 42: C42, 43: C43, 44: C44, 45: C45}

# what a transition leaves behind for the rest of the incoming shot
C.DELAY["shot_nutrients"] = BEAT          # the table unrolls once its header has landed
C.SHOT_HOOKS["shot_antioxidants"] = {"grow_t": T37 + BEAT}
C.SHOT_HOOKS["shot_purr"] = {"title_age": BEAT - 0.05}
C.SHOT_HOOKS["shot_god"] = {"root_age": -1.0}
C.SHOT_HOOKS["shot_proof"] = {"code_age": 0.12, "goal_age": 0.12, "wit_age": BEAT}
C.SHOT_HOOKS["shot_fp8"] = {"label_age": beat_t(beat_of(T42) + 1.0) + 8 / FPS + 0.12 - T42}
C.SHOT_HOOKS["shot_ampm"] = {"center_age": beat_t(beat_of(T43) + 1.0) + 0.34 - T43}
C.SHOT_HOOKS["shot_role"] = {"tags_age": 0.43, "ms": True}


def setup(v1):
    install_filter()
