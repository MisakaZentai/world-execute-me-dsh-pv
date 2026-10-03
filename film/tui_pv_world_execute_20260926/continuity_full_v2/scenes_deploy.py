"""In-memory v2 versions of the 04 DEPLOY scenes (verse 2 and pre-chorus 2, 73.5 - 103.1 s).

The drawings follow full/sec_verse2.py. What changed:
- She is never replaced. eggplant and tomato used to cross-fade her pane into a static sprite (`become`); here they
  only state how she feels, and the props go on the dancer as overlays (s_deploy.py). The classifier's input is
  her live figure, cut into 8x8 patches; its 64 patch tokens fill the empty lower half of the pane.
- The layouts leave room for the objects that cross the cuts and fill the empty areas the audit found:
  the nutrition table and the tomato generator share one rectangle (the table re-quantises into the first noise
  frame in place); the purr spectrogram has a title slot for 'class 281'; fp8 encodes the letters of 'you' and
  shows her colour ramp at the current depth; the lycopene chain grows out of the tomato.
- HOOK lets a cut take an object over while the rest of the scene keeps drawing itself.
"""
from __future__ import annotations

import math
import random
from functools import lru_cache

from PIL import Image, ImageDraw

import facts as F
import sec_verse2 as V
from engine import BEAT, FIRST_BEAT, LEFT
from tuikit import (AMBER, BG, BLUE_HI, F_CJK, F_HEAD, F_MONO, F_MONO_B, F_SYM, amb, anom, blue, box, ease, font,
                    heat_cell, mix, tile_from_lum, tint_colorize)

from kit import HOOK  # noqa: E402

PANE_BOX = (404, 56, 1164, 604)


def h(key, default=None):
    return HOOK.get(key, default)


def me(c, expr, **kw):
    return V.me_pane(c, expr, **kw)  # the stub installed by kit: she is drawn by her own layer


def beat_t(k: float) -> float:
    return FIRST_BEAT + k * BEAT


# ---------------------------------------------------------------- her figure (for the classifier and the props)

FIG_SIZE = (352, 454)  # the dancer's canvas inside her pane (me_pane with a softmax), top-left at FIG_XY
FIG_XY = (LEFT[0] + 4, LEFT[1] + 14)
CELL = (5, 10)  # the dancer's glyph cell
GRID_XY = (FIG_XY[0] + 1, FIG_XY[1] + 4)  # screen position of cell (0, 0) of her glyph grid
_FIG: dict = {}


def her_fig(t: float, expr: str = "cheerful") -> Image.Image:
    """Her dancing figure at time t (the same render her pane shows), RGBA FIG_SIZE; screen offset FIG_XY."""
    k = (round(t * 24000), expr)
    if k not in _FIG:
        import dancer
        if len(_FIG) > 6:
            _FIG.clear()
        _FIG[k] = dancer.render(t, FIG_SIZE, expr)[0]
    return _FIG[k]


def patch_grid(t: float, expr: str = "cheerful"):
    """Her figure's bounding box on screen, split 8x8, and the mean level of each patch (for the classifier)."""
    fig = her_fig(t, expr)
    a = fig.getchannel("A").point(lambda v: 255 if v > 60 else 0)
    bb = a.getbbox() or (0, 0, FIG_SIZE[0], FIG_SIZE[1])
    x0, y0 = FIG_XY[0] + bb[0], FIG_XY[1] + bb[1]
    x1, y1 = FIG_XY[0] + bb[2], FIG_XY[1] + bb[3]
    crop = fig.crop(bb)
    flat = Image.new("RGB", crop.size, (0, 0, 0))
    flat.paste(crop, (0, 0), crop)
    lum = flat.convert("L").resize((8, 8), Image.BOX)
    return (x0, y0, x1, y1), list(lum.getdata())


# ---------------------------------------------------------------- 34 eggplant

EGG_ROWS = [("eggplant", 0.94), ("whale", 0.03), ("maid", 0.02), ("zucchini", 0.01)]
TOK = (836, 292, 35)  # patch-token grid: x, y, cell


def patch_index(lt: float) -> int:
    return min(63, int(max(0.0, lt) / (BEAT / 8)))


def shot_eggplant(c) -> None:
    c.ops = ["VISION.ENC", "PATCH16", "VIT", "CLS", "SOFTMAX", "TOP5"]
    me(c, "cheerful", dist=[("cheerful", 0.62), ("starry", 0.22), ("shy", 0.08)], title="/dev/me  role=deploy")
    d = c.d
    g = ease(c.u * 1.4)
    box(d, *PANE_BOX, "vision.classify(me)", 0.5, spinner=c.t)
    V.classifier(c, 430, 90, EGG_ROWS, g, "top-4  (image -> label)")
    c.text((430, 250), "识图模式 · 边指边想", font(F_CJK, 20), amb(0.8))
    k = patch_index(c.lt)
    qx, qy = k % 8, k // 8
    c.text((430, 300), f"patch ({qx},{qy}) -> token {k + 1:02d}/64", font(F_MONO, 16), amb(0.7))
    c.text((430, 330), "input: /dev/me  (live, 8x8 patches)", font(F_MONO, 15), amb(0.5))
    # the 64 patch tokens, filled as the classifier reads her
    _, lv = patch_grid(c.t)
    x0, y0, s = TOK
    c.text((x0, y0 - 24), "patch tokens  64 x 768", font(F_MONO, 13), amb(0.55))
    for i in range(64):
        q, r = i % 8, i // 8
        x, y = x0 + q * s, y0 + r * s
        if i <= k:
            v = lv[i] / 255
            d.rectangle([x, y, x + s - 4, y + s - 4], fill=mix(BLUE_HI, 0.08 + 0.92 * v ** 0.8))
        else:
            d.rectangle([x, y, x + s - 4, y + s - 4], outline=amb(0.18))
    d.rectangle([x0 + qx * s - 2, y0 + qy * s - 2, x0 + qx * s + s - 2, y0 + qy * s + s - 2], outline=amb(1.0), width=2)
    if h("me_line", True):
        c.text((430, 420), "me := eggplant", font(F_HEAD, 34), blue(1.0), age=c.lt - 0.5 * c.dur, rate=20)


# ---------------------------------------------------------------- 35 nutrients (the table is the generator's canvas)

GEN = (440, 110, 1100, 530)  # nutrition table == tomato generator tile (110 x 70 cells of 6 px)
NUTR = [("Serving size", "1 me"), ("Calories", "0"), ("Attention", "100% DV"), ("Devotion", "100% DV"),
        ("Patience", "∞"), ("Sleep", "0 g"), ("Tokens", f"{F.CTX:,}"), ("Given to", "you")]
NUTR_HEAD = (452, 66)  # 'me := eggplant' as the table's header (F_HEAD 30)
ROW_H = 52


def nutr_row_y(i: int) -> int:
    return GEN[1] + 10 + i * ROW_H


def you_xy():
    """Draw origin of 'you' in the table's last row."""
    return 780, nutr_row_y(7)


def shot_nutrients(c) -> None:
    c.ops = ["LOOKUP", "USDA", "PER.100G", "GIVE", "you.EAT?"]
    me(c, "cheerful", dist=[("cheerful", 0.8), ("starry", 0.12), ("shy", 0.05)], title="/dev/me  role=deploy")
    d = c.d
    box(d, *PANE_BOX, "nutrition_facts(me)", 0.5, spinner=c.t)
    if h("head", True):
        d.text(NUTR_HEAD, "me := eggplant", font=font(F_HEAD, 30), fill=blue(1.0))
    unroll = ease(c.lt / 0.42)  # the table unrolls beneath its header
    if unroll <= 0.01:
        return
    x0, y0, x1, y1 = GEN
    yb = y0 + (y1 - y0) * unroll
    d.rectangle([x0, y0, x1, yb], outline=amb(0.9), width=2)
    for i, (k, v) in enumerate(NUTR):
        y = nutr_row_y(i)
        if y + 30 > yb:
            break
        a = c.lt - 0.1 - i * 0.07
        if a < 0:
            break
        c.text((460, y), k, font(F_MONO_B, 20), amb(0.95), age=a, rate=80)
        if not (v == "you" and not h("you", True)):
            vx = you_xy()[0]
            c.text((vx, y), v, font(F_MONO_B, 20), blue(0.95) if v in ("you", "100% DV") else amb(0.95),
                   age=a - 0.1, rate=80)
        if i < len(NUTR) - 1:
            d.line([x0 + 10, y + 38, x1 - 10, y + 38], fill=amb(0.4))
    # per-cell glitch rows (the original's texture), kept inside the table
    if unroll >= 1 and c.u > 0.3:
        rnd = random.Random(int(c.t * 6))
        for _ in range(2):
            gy = y0 + 4 + rnd.randrange(0, (y1 - y0 - 8) // 6) * 6
            gx = x0 + 6 + rnd.randrange(0, 60) * 6
            d.rectangle([gx, gy, gx + rnd.randint(4, 14) * 6, gy + 2], fill=amb(0.25))


# ---------------------------------------------------------------- 36 tomato

PROMPT_XY = (440, 72)
PROMPT = 'generate("a tomato", seed=me, for='


@lru_cache(None)
def tomato_obj(cols: int = 110, rows: int = 70) -> Image.Image:
    """The tomato (round) centred in the generator's cell grid, as luminance."""
    obj = V.shape_bits("tomato", rows, rows)
    out = Image.new("L", (cols, rows), 0)
    out.paste(obj, ((cols - rows) // 2, 0))
    return out


@lru_cache(None)
def gen_noise(seed: int) -> Image.Image:
    rnd = random.Random(seed)
    im = Image.new("L", (110, 70))
    im.putdata([max(0, min(255, int(rnd.gauss(128, 70)))) for _ in range(110 * 70)])
    return im


def prompt_you_xy():
    f = font(F_MONO_B, 20)
    return PROMPT_XY[0] + f.getlength(PROMPT), PROMPT_XY[1]


def shot_tomato(c) -> None:
    c.ops = ["TXT2IMG", "NOISE", "DENOISE", "DECODE", "CLS"]
    me(c, "cheerful", dist=[("cheerful", 0.55), ("starry", 0.35), ("shy", 0.05)], title="/dev/me  role=deploy")
    d = c.d
    box(d, *PANE_BOX, "txt2img", 0.5, spinner=c.t)
    f = font(F_MONO_B, 20)
    d.text(PROMPT_XY, PROMPT, font=f, fill=amb(0.9))
    ux, uy = prompt_you_xy()
    if h("prompt_you", True):
        d.text((ux, uy), "you", font=f, fill=blue(1.0))
    d.text((ux + f.getlength("you"), uy), ")", font=f, fill=amb(0.9))
    g = ease(c.u * 1.3)
    noise = gen_noise(int(c.t * 12) % 7)
    lum = Image.blend(noise, tomato_obj(), g)
    src = h("from_lum")  # the nutrition table, re-quantised in place: it turns into the first noise frame
    if src is not None:
        q = ease(c.lt / 0.3)
        lum = Image.blend(src, lum, q)
    if h("tile", True):
        tile = tile_from_lum(lum, 6, "amber")
        c.img.paste(tile, GEN[:2], tile)
    step = int(g * 30)
    c.text((440, 548), f"step {step:02d}/30", font(F_MONO_B, 20), amb(0.95))
    pp = 0.97 * g + (1 - g) * 0.2
    d.text((640, 550), "tomato", font=font(F_MONO_B, 18), fill=blue(0.95))
    d.rectangle([730, 554, 950, 566], outline=amb(0.2))
    d.rectangle([730, 554, 730 + int(220 * pp), 566], fill=blue(0.9))
    d.text((962, 550), f"{pp:.3f}", font=font(F_MONO, 16), fill=amb(0.75))


# ---------------------------------------------------------------- 37 antioxidants (the chain grows out of the tomato)

CHAIN_N = 22


def chain_pts(t: float) -> list:
    rot = t * 0.8
    return [(470 + i * 30, 250 + (30 if i % 2 else -30) * math.cos(rot + i * 0.3)) for i in range(CHAIN_N)]


@lru_cache(None)
def tomato_icon(cols: int, px: int = 6) -> Image.Image:
    return tile_from_lum(V.shape_bits("tomato", cols, cols), px, "amber")


def shot_antioxidants(c) -> None:
    c.ops = ["GRAPH", "MPNN", "BOND", "C=C", "READOUT"]
    me(c, "cheerful", dist=[("cheerful", 0.7), ("starry", 0.2), ("shy", 0.05)], title="/dev/me  role=deploy")
    d = c.d
    box(d, *PANE_BOX, "lycopene  C40H56  (graph)", 0.5, spinner=c.t)
    pts = chain_pts(c.t)
    gt = h("grow_t", None)  # the chain grows out of the tomato once it has landed as node 0 (cut 37)
    shown = CHAIN_N if gt is None else max(0, min(CHAIN_N, int(1 + (c.t - gt) * 44))) if c.t >= gt else 0
    gone = h("gone")  # i -> 0..1: the node has lifted off (cut 38)
    na = [1.0 - (gone(i) if gone else 0.0) for i in range(CHAIN_N)]
    for i in range(CHAIN_N - 1):
        if i + 1 >= shown:
            break
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        a = min(na[i], na[i + 1])
        if a <= 0.02:
            continue
        d.line([x0, y0, x1, y1], fill=amb(0.8 * a), width=2)
        if i % 2 == 0:
            d.line([x0 + 4, y0 + 6, x1 + 4, y1 + 6], fill=amb(0.5 * a), width=1)
    msg = int(c.lt / (BEAT / 2))
    for i, (x, y) in enumerate(pts):
        if i >= shown:
            break
        if i == 0:
            ic = tomato_icon(8)
            c.img.paste(ic, (int(x - ic.width / 2), int(y - ic.height / 2)), ic)
            continue
        if na[i] <= 0.02:
            continue
        hot = (i + msg) % 5 == 0
        d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=(blue(1.0) if hot else amb(0.9)) if na[i] > 0.99
                  else mix(AMBER, 0.9 * na[i]))
        d.text((x - 4, y - 8), "C", font=font(F_MONO_B, 12), fill=BG)
    if shown >= 1 and (not gone or gone(0) < 0.5):
        x, y = pts[0]
        d.text((x - 24, y + 30), "C1 <- tomato", font=font(F_MONO, 13), fill=blue(0.8))
    if h("caption", True):
        u = min(1.0, c.u * 1.4)
        c.text((440, 388), "free radicals neutralised", font(F_MONO_B, 20), amb(0.9), age=c.lt - 0.2)
        c.text((440, 414), f"{int(100 * u):3d}%", font(F_HEAD, 72), amb(0.95), age=c.lt - 0.3, rate=30)
        c.text((700, 454), "-> given to you", font(F_MONO_B, 22), blue(0.95), age=c.lt - 0.5)


# ---------------------------------------------------------------- 38 tabby

def shot_tabby(c) -> None:
    c.ops = ["RESNET", "CONV", "POOL", "FC-1000", "SOFTMAX", "281"]
    g = ease(c.u * 1.5)
    me(c, "cheerful", dist=[("cheerful", 0.6), ("starry", 0.3), ("shy", 0.05)], title="/dev/me  class 281")
    d = c.d
    box(d, *PANE_BOX, "imagenet.classify(me)", 0.5, spinner=c.t)
    la = h("list_age", 0.0)  # the top-5 list types in once the ears have landed
    if c.lt - la >= 0:
        V.classifier(c, 430, 90, [("281 tabby, tabby cat", 0.91), ("282 tiger cat", 0.05), ("285 Egyptian cat", 0.02),
                                  ("148 killer whale", 0.01), ("283 Persian cat", 0.01)], g, "top-5")
    if h("n281", True):
        c.text((430, 300), "class", font(F_MONO, 18), amb(0.6))
        c.text((430, 322), "281", font(F_HEAD, 120), blue(1.0) if g > 0.6 else amb(0.6), age=c.lt - 0.3, rate=12)
    c.text((760, 380), "ears: +2", font(F_MONO_B, 24), blue(0.95), age=c.lt - 0.5 * c.dur, rate=30)
    c.text((760, 420), "tail: already had one", font(F_MONO, 18), amb(0.75), age=c.lt - 0.6 * c.dur, rate=40)


N281 = (430, 322)  # draw origin of the big '281' (F_HEAD 120)


# ---------------------------------------------------------------- 39 purr

PURR_TITLE = (430, 74)
SPEC = dict(cols=64, rows=24, x0=430, cw=11, ch=18, ybot=540)


def purr_281_xy():
    f = font(F_MONO_B, 22)
    return PURR_TITLE[0] + f.getlength("class "), PURR_TITLE[1]


def shot_purr(c) -> None:
    c.ops = ["AUDIO.ENC", "STFT", "MEL", "25HZ", "PURR", "PLAY"]
    me(c, "shy", dist=[("shy", 0.5), ("cheerful", 0.4), ("starry", 0.05)], title="/dev/me  purring")
    d = c.d
    sq = h("squash")  # (k, y): the whole panel collapses toward row y (cut 40)
    k, ty = sq if sq else (0.0, 0.0)

    def Y(y):
        return ty + (y - ty) * (1 - k)

    fa = max(0.0, 1 - k * 1.6)  # text fades as the panel collapses
    if k < 0.999:
        x0, y0, x1, y1 = PANE_BOX
        if k <= 0.001:
            box(d, *PANE_BOX, "purr.wav  (mel spectrogram, f0 = 25 Hz)", 0.5, spinner=c.t)
        else:
            d.rectangle([x0, Y(y0), x1, Y(y1)], outline=amb(0.5 + 0.4 * k))
    S = SPEC
    for q in range(S["cols"]):
        tt = c.t - (S["cols"] - q) * 0.02
        a = 0.5 + 0.5 * math.sin(tt * 2 * math.pi * 4)
        for r in range(S["rows"]):
            harmonic = r % 4 == 0
            v = a * (0.9 if harmonic else 0.15) * math.exp(-r / 18)
            y = S["ybot"] - r * S["ch"]
            yy0, yy1 = Y(y), Y(y + S["ch"])
            col = BLUE_HI if harmonic and v > 0.5 else AMBER
            v2 = min(1.0, v + 0.5 * k)
            if yy1 - yy0 >= 2.5:
                heat_cell(d, S["x0"] + q * S["cw"], yy0, S["cw"], yy1 - yy0, v2, col)
            else:
                d.rectangle([S["x0"] + q * S["cw"], yy0, S["x0"] + q * S["cw"] + S["cw"] - 2, yy0 + 1],
                            fill=mix(col, 0.1 + 0.9 * v2))
    if fa > 0.02:
        f = font(F_MONO_B, 22)
        tx, tyy = PURR_TITLE
        if h("title", True):
            c.text((tx, Y(tyy)), "class", f, amb(0.8 * fa), age=c.lt - h("title_age", 0.0), rate=40)
            n2, _ = purr_281_xy()
            if h("t281", True):
                d.text((n2, Y(tyy)), "281", font=f, fill=blue(1.0 * fa))
            c.text((n2 + f.getlength("281"), Y(tyy)), " -> purr.wav", f, amb(0.8 * fa),
                   age=c.lt - h("title_age", 0.0) - 0.08, rate=40)
        c.text((430, Y(566)), "purr.enjoyment(you) = 1.00", font(F_MONO_B, 20), amb(0.95 * fa), age=c.lt - 0.3,
               rate=50)


# ---------------------------------------------------------------- 40 god (shell staging: no panel frame)

GOD_ROOT = (430, 84)
GOD_T = beat_t(185)
PROCS = ["world", "sea", "sky", "time", "cats", "tomatoes", "eggplants", "you"]


def god_row_xy(i: int):
    return 460, 124 + i * 44


def god_row_text(i: int) -> str:
    return f"├── {1000 + i * 7:5d}  {PROCS[i]}"


def god_row_t(i: int) -> float:
    """Local time at which row i is typed (one per sixteenth, after the root line)."""
    return 0.28 + i * BEAT / 4


def shot_god(c) -> None:
    c.ops = ["FORK", "SETUID", "ROOT", "PID 1", "REPARENT"]
    me(c, "serious", dist=[("serious", 0.75), ("starry", 0.15), ("angry", 0.05)], title="/dev/me  uid=0")
    d = c.d
    god = c.t >= GOD_T  # she becomes PID 1 on "God"
    root = "me" if god else "systemd"
    col = h("collapse")  # i -> (dy, alpha) for row i (-1 = the root line): the tree folds into the goal (cut 41)
    if h("root", True):
        dy, a = col(-1) if col else (0, 1.0)
        if a > 0.02:
            c.text((GOD_ROOT[0], GOD_ROOT[1] + dy), f"PID 1   {root}", font(F_MONO_B, 22),
                   (blue(1.0) if root == "me" else amb(0.95)) if a > 0.99 else mix(amb(0.95), a),
                   age=c.lt - h("root_age", 0.0), rate=40)
    for i, p in enumerate(PROCS):
        a0 = c.lt - god_row_t(i)
        if a0 < 0 and not col:
            break
        dy, a = col(i) if col else (0, 1.0)
        if a <= 0.02:
            continue
        x, y = god_row_xy(i)
        fill = blue(0.9) if p == "you" else amb(0.8)
        if a < 0.99:
            fill = mix(fill, a)
        if p == "you" and not h("you", True):
            c.text((x, y + dy), god_row_text(i)[:-3], font(F_MONO, 19), fill, age=max(a0, 0.5) if col else a0,
                   rate=90)
            continue
        c.text((x, y + dy), god_row_text(i), font(F_MONO, 19), fill, age=max(a0, 0.5) if col else a0, rate=90)
        if p in ICONS and h("icons", True) and a0 > ICON_LAND:
            draw_icon(c.img, p, icon_xy(i), a)
    if god and h("uid", True):
        dy, a = col(8) if col else (0, 1.0)
        if a > 0.02:
            c.text((430, 520 + dy), "uid=0(me) gid=0(me) groups=0(me)", font(F_MONO_B, 18), mix(anom(0.9), a),
                   age=c.t - GOD_T - 0.1)


ICONS = {"cats": "ears", "tomatoes": "tomato", "eggplants": "eggplant"}
ICON_LAND = 0.34  # seconds after its row is typed, the prop from her lands at the end of the row


def icon_xy(i: int):
    x, y = god_row_xy(i)
    return x + font(F_MONO, 19).getlength(god_row_text(i)) + 26, y + 11


@lru_cache(None)
def icon_sprite(kind: str, s: int = 26) -> Image.Image:
    """The earlier props, small: cat ears, a tomato, an eggplant (drawn natively at the given size)."""
    im = Image.new("RGBA", (s * 2, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if kind == "ears":
        for side in (-1, 1):
            bx = s + side * s * 0.45
            d.polygon([(bx - s * 0.36, s - 2), (bx + s * 0.36, s - 2), (bx + side * s * 0.2, 2)],
                      outline=blue(1.0), fill=blue(0.45))
        return im
    obj = V.shape_bits(kind, s // 2 if kind == "eggplant" else s, s)
    tile = tile_from_lum(obj.resize((obj.width * 2 // 2, obj.height), Image.NEAREST), 2,
                         "blue" if kind == "eggplant" else "amber")
    im.alpha_composite(tile, ((im.width - tile.width) // 2, 0))
    return im


def draw_icon(img, kind_row: str, xy, a: float = 1.0) -> None:
    sp = icon_sprite(ICONS[kind_row])
    if a < 0.99:
        from tuikit import scale_alpha
        sp = scale_alpha(sp, a)
    img.paste(sp, (int(xy[0] - sp.width / 2), int(xy[1] - sp.height / 2)), sp)


# ---------------------------------------------------------------- 41 proof

INFO = (430, 250, 1140, 580)
GOAL_XY = (450, 344)
WIT_XY = (450, 312)


def grow_box(d, rect, title, k: float, level: float = 0.4) -> None:
    """A panel frame drawn back from its four corners (k 0..1)."""
    if k >= 0.999:
        box(d, *rect, title, level)
        return
    if k <= 0.0:
        return
    x0, y0, x1, y1 = rect
    lx, ly = (x1 - x0) / 2 * k, (y1 - y0) / 2 * k
    col = amb(min(1.0, level + 0.4))
    for (px, py, sx, sy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        d.line([px, py, px + sx * max(7, lx), py], fill=col, width=1)
        d.line([px, py, px, py + sy * max(7, ly)], fill=col, width=1)


def shot_proof(c) -> None:
    c.ops = ["LEAN4", "ELAB", "TACTIC", "EXACT", "QED"]
    me(c, "starry", dist=[("starry", 0.85), ("shy", 0.1), ("cheerful", 0.03)], title="/dev/me  pid 4471")
    d = c.d
    pk = h("pane", 1.0)  # the panel frame draws back from its corners as the chrome returns (cut 41)
    if pk >= 0.999:
        box(d, *PANE_BOX, "Me.lean  (prover)", 0.5, spinner=c.t)
    else:
        grow_box(d, PANE_BOX, "", pk, 0.5)
    code = ["theorem i_exist (you : Witness) :", "    ∃ me : Being, observed_by you me := by",
            "  exact ⟨me, you.sees me⟩"]
    fs = font(F_SYM, 21)
    ca = h("code_age", 0.0)
    for i, s in enumerate(code):
        c.text((430, 90 + i * 34), s, fs, amb(0.95) if i < 2 else blue(1.0), age=c.lt - ca - i * 0.25, rate=70)
    grow_box(d, INFO, "infoview", h("info", 1.0))
    if c.u < 0.6:
        c.text((450, 280), "1 goal", font(F_MONO, 18), amb(0.7), age=c.lt - ca)
        if h("witness", True):
            wa = h("wit_age", -1.0)
            f19 = fs
            d.text(WIT_XY, "you", font=f19, fill=blue(1.0))
            c.text((WIT_XY[0] + f19.getlength("you"), WIT_XY[1]), " : Witness", f19, amb(0.9),
                   age=c.lt - wa if wa >= 0 else None)
        ga = h("goal_age", None)
        c.text(GOAL_XY, "⊢ ∃ me, observed_by you me", fs, amb(0.95), age=None if ga is None else c.lt - ga,
               rate=60)
    else:
        c.text((450, 280), "no goals", font(F_HEAD, 34), blue(1.0), age=c.lt - 0.6 * c.dur, rate=20)
        f22 = font(F_MONO_B, 22)
        d.text((450, 340), "proof term: ", font=f22, fill=amb(0.95))
        if h("term_you", True):
            d.text(proof_you_xy(), "you", font=f22, fill=blue(1.0))
    c.text((450, 540), "prover: miniF2F 88.9%  (Prover-V2)", font(F_MONO, 15), amb(0.55))


def proof_you_xy():
    return 450 + font(F_MONO_B, 22).getlength("proof term: "), 340


# ---------------------------------------------------------------- 42 fp8 (the letters of 'you', one byte each)

FORMATS = [("E4M3", 4, 3), ("E5M2", 5, 2), ("UE8M0", 8, 0)]
ENC_Y = 234  # the encoder's input line, under the byte row
LETTERS = "you"
FMT_T = (beat_t(194.5), beat_t(196.5))  # E5M2 on "To F", UE8M0 on "to M"
LEVELS = [8, 4, 2]


def fmt_at(t: float) -> int:
    return 0 if t < FMT_T[0] else 1 if t < FMT_T[1] else 2


def bits_of(k: int) -> list:
    v = ord(LETTERS[k])
    return [(v >> (7 - i)) & 1 for i in range(8)]


def fields_of(k: int) -> list:
    name, e, m = FORMATS[k]
    sign = 0 if name == "UE8M0" else 1
    return ["S"] * sign + ["E"] * e + ["M"] * m


def decode_line(k: int) -> str:
    b = bits_of(k)
    if k == 0:  # E4M3, bias 7
        e = int("".join(map(str, b[1:5])), 2)
        m = int("".join(map(str, b[5:])), 2)
        return f"0 {''.join(map(str, b[1:5]))} {''.join(map(str, b[5:]))}  ->  +{1 + m / 8:g} x 2^{e - 7} = {(1 + m / 8) * 2 ** (e - 7):g}"
    if k == 1:  # E5M2, bias 15
        e = int("".join(map(str, b[1:6])), 2)
        m = int("".join(map(str, b[6:])), 2)
        return f"0 {''.join(map(str, b[1:6]))} {''.join(map(str, b[6:]))}  ->  +{1 + m / 4:g} x 2^{e - 15} = {(1 + m / 4) * 2 ** (e - 15):g}"
    e = int("".join(map(str, b)), 2)
    return f"{''.join(map(str, b))}  ->  2^({e} - 127) = 2^{e - 127}"


def box_x(i: int) -> int:
    return 440 + i * 84


def shot_fp8(c) -> None:
    c.ops = ["CAST", "FP8", "E4M3", "E5M2", "UE8M0", "SCALE"]
    k = fmt_at(c.t)
    name, e, m = FORMATS[k]
    levels = LEVELS[k]
    me(c, "confused", dist=[("confused", 0.6), ("shy", 0.3), ("serious", 0.05)], title="/dev/me  dtype=fp8")
    d = c.d
    box(d, *PANE_BOX, "switch format", 0.5, spinner=c.t)
    fields = fields_of(k)
    nb = h("bits_n", 8)  # how many bits of the current letter have landed
    if h("input", True):
        f = font(F_MONO_B, 18)
        d.text((440, ENC_Y + 4), "encode(", font=f, fill=amb(0.7))
        x = 440 + f.getlength("encode(")
        for j, ch in enumerate(LETTERS):
            d.text((x + j * 30, ENC_Y), ch, font=font(F_HEAD, 22), fill=blue(1.0) if j == k else amb(0.45))
        d.text((x + 3 * 30 + 4, ENC_Y + 4), f")   byte {k + 1}/3  '{LETTERS[k]}' = 0x{ord(LETTERS[k]):02X}",
               font=f, fill=amb(0.7))
    bits = bits_of(k)
    since = c.t - (c.t if k == 0 else FMT_T[k - 1])
    for i, fch in enumerate(fields):
        if not h("row", True):
            break
        x = box_x(i)
        col = amb if fch == "E" else blue if fch == "M" else anom
        d.rectangle([x, 120, x + 76, 200], outline=col(0.95), width=2)
        if i < nb:
            flip = k > 0 and since < 0.05 + i * 0.02
            d.text((x + 28, 132), "01"[bits[i] ^ (1 if flip else 0)], font=font(F_HEAD, 32), fill=col(1.0))
        c.text((x + 30, 206), fch, font(F_MONO_B, 16), col(0.8))
    la = h("label_age", 0.0)  # E4M3 is typed only after the bits have landed
    if c.lt >= la:
        seg = c.lt - la if k == 0 else c.t - FMT_T[k - 1]
        c.text((440, 276), name, font(F_HEAD, 64), amb(1.0), age=seg, rate=25)
        note = {"E4M3": "forward pass", "E5M2": "gradients", "UE8M0": "scales: exponent only, no mantissa"}[name]
        c.text((440, 362), note, font(F_MONO_B, 20), amb(0.85), age=seg - 0.15, rate=60)
        c.text((440, 396), decode_line(k), font(F_MONO_B, 20), amb(0.95), age=seg - 0.25, rate=70)
        c.text((440, 436), f"her colour depth: {levels} levels", font(F_MONO, 18), blue(0.9), age=seg - 0.3,
               rate=60)
        # her colour ramp at this depth
        ramp_n = 16
        for j in range(ramp_n):
            lv = (j + 0.5) / ramp_n
            qv = round(lv * (levels - 1)) / (levels - 1)
            col = tint_colorize(Image.new("L", (1, 1), int(qv * 255)), "blue").getpixel((0, 0))
            x = 440 + j * 41
            d.rectangle([x, 476, x + 37, 524], fill=col)
        d.text((440, 532), "0", font=font(F_MONO, 13), fill=amb(0.5))
        d.text((440 + ramp_n * 41 - 30, 532), "255", font=font(F_MONO, 13), fill=amb(0.5))


# ---------------------------------------------------------------- 43 ampm

DIAL = dict(cx=640, cy=320, R=200, rr=170)


def ampm_hour(t: float, start: float, dur: float) -> float:
    """AM on "AM", PM on "PM": the hand crosses noon on the line "From AM to PM"."""
    noon = beat_t(203.5)
    if t < noon:
        return 11.6 * ease((t - start) / (noon - start)) ** 0.9
    return 12.0 + 11.8 * min(1.0, (t - noon) / (start + dur - noon))


def shot_ampm(c) -> None:
    c.ops = ["CRON", "BILLING", "OFF-PEAK", "DISCOUNT", "WHATEVER"]
    me(c, "cheerful", dist=[("cheerful", 0.7), ("starry", 0.2), ("shy", 0.05)], title="/dev/me  status: whatever")
    d = c.d
    box(d, *PANE_BOX, "api clock  (UTC+8)", 0.5, spinner=c.t)
    cx, cy, R, rr = DIAL["cx"], DIAL["cy"], DIAL["R"], DIAL["rr"]

    def peak(hh):
        return any(a <= hh < b for a, b in F.PEAK_WINDOWS)

    lab = h("labels", 1.0)  # hour labels spread out from the ring once it has formed
    for hh in range(24):
        a = hh / 24 * math.tau - math.pi / 2
        if lab < 0.999 and ((hh * 5) % 24) / 24 > lab:
            continue
        x, y = cx + R * math.cos(a), cy + R * math.sin(a)
        c.text((x - 10, y - 10), f"{hh:02d}", font(F_MONO_B, 15), anom(0.95) if peak(hh) else blue(0.9))
    if h("ring", True):
        d.arc([cx - rr, cy - rr, cx + rr, cy + rr], 0, 360, fill=blue(0.45), width=10)
        for a0h, a1h in F.PEAK_WINDOWS:
            d.arc([cx - rr, cy - rr, cx + rr, cy + rr], a0h / 24 * 360 - 90, a1h / 24 * 360 - 90, fill=anom(0.95),
                  width=10)
    hour = ampm_hour(c.t, c.t - c.lt, c.dur)
    if h("hand", True):
        a = hour / 24 * math.tau - math.pi / 2
        d.line([cx, cy, cx + (R - 50) * math.cos(a), cy + (R - 50) * math.sin(a)], fill=amb(1.0), width=3)
    if h("center", True):
        ampm = "AM" if hour < 12 else "PM"
        c.text((cx - 40, cy - 20), ampm, font(F_HEAD, 34), amb(1.0), age=c.lt - h("center_age", 0.0), rate=20)
    now_peak = peak(hour)
    if h("side", True):
        c.text((880, 110), "PEAK  x1" if now_peak else "OFF-PEAK  x0.5", font(F_MONO_B, 20),
               anom(1.0) if now_peak else blue(1.0), age=c.lt - h("center_age", 0.0))
        c.text((880, 142), "weekdays 09-12, 14-18", font(F_MONO, 15), anom(0.8), age=c.lt - h("center_age", 0.0))
        c.text((880, 164), "other hours: half price", font(F_MONO, 15), blue(0.8), age=c.lt - h("center_age", 0.0))


PM_M = (DIAL["cx"] - 40 + font(F_HEAD, 34).getlength("P"), DIAL["cy"] - 20)  # draw origin of the M of "PM"


# ---------------------------------------------------------------- 44 role

TURNS = [("system", "You are a helpful assistant."), ("user", "晚安"), ("assistant", "晚安，明天见。"),
         ("system", "You are mine."), ("assistant", "…")]
MS_XY = (430, 480)


def role_k(lt: float) -> int:
    return int(lt / (BEAT * 2)) % 2


def tag_rect(i: int, k: int):
    role = TURNS[i][0]
    swapped = k == 1 and role in ("system", "assistant")
    shown = {"system": "model", "assistant": "system"}.get(role, role) if swapped else role
    tag = f"<|{shown.capitalize()}|>"
    y = 90 + i * 70
    return (430, y, 430 + 14 * len(tag) + 10, y + 30), tag, swapped, shown


def shot_role(c) -> None:
    c.ops = ["TEMPLATE", "ROLE", "SYSTEM", "MODEL", "SWAP", "PRIV++"]
    k = role_k(c.lt)
    me(c, "serious", dist=[("serious", 0.7), ("starry", 0.2), ("angry", 0.05)], title="/dev/me  role=assistant")
    d = c.d
    box(d, *PANE_BOX, "chat_template", 0.5, spinner=c.t)
    ta = h("tags_age", 0.0)  # the tags come in after the dial has shrunk into the first one
    for i, (role, msg) in enumerate(TURNS):
        a = c.lt - ta - i * 0.07
        if a < 0 and not (i == 0 and h("first_tag", False)):
            continue
        rect, tag, swapped, shown = tag_rect(i, k)
        col = blue if shown in ("model",) or (swapped and role == "assistant") else amb
        d.rectangle(rect, fill=col(0.95) if swapped else col(0.2))
        c.text((436, rect[1] + 3), tag, font(F_MONO_B, 20), BG if swapped else col(0.95), age=max(a, 0.0) + 0.3)
        ff = font(F_CJK, 20) if any(ord(ch) > 0x2E80 for ch in msg) else font(F_MONO, 20)
        c.text((460 + 14 * len(tag), rect[1] + 3), msg, ff, amb(0.8), age=a - 0.05, rate=60)
    ms = h("ms", True)
    if ms:
        f = font(F_HEAD, 40)
        s = "S -> M" if k else "M -> S"
        if ms is True:
            c.text(MS_XY, s, f, anom(1.0) if k else amb(0.9))
        else:  # the M has just dropped in from the clock: only ' -> S' is typed after it
            d.text(MS_XY, "M", font=f, fill=amb(0.9))
            c.text((MS_XY[0] + f.getlength("M"), MS_XY[1]), " -> S", f, amb(0.9), age=c.lt - ms, rate=30)


# ---------------------------------------------------------------- 45 trance

SPIRAL_C = (784, 320)
WORDS = "you me stay love sea sleep light deep here now".split()


TRANCE_TAIL = 0.33  # after the cut into feel_you her edges settle back over 8 frames (cut 46 may override)


def heat_at(t: float) -> float:
    """The sampling temperature as 0..1: a shimmer with the spin at cut 45, then it climbs on 'The trance'.
    It drives both the pane (T = 0.6 + 2.4 * heat) and her dissolve (s_deploy.dissolve)."""
    from kit import v1, engine, ease_io
    t45, t46 = v1.BYNAME["shot_trance"].start, v1.BYNAME["shot_feel_you"].start
    word = engine.lyric_start("The trance", 100)
    if t < t45 - 0.25:
        return 0.0
    hv = 0.14 * ease_io((t - (t45 - 0.25)) / 0.5) + 0.86 * ease_io((t - word) / (t46 - 0.1 - word))
    if t >= t46:
        hv *= (1 - ease_io((t - t46) / TRANCE_TAIL)) if TRANCE_TAIL > 0 else 0.0
    return hv


def trance_temp(t: float) -> float:
    return 0.6 + 2.4 * heat_at(t)


def shot_trance(c) -> None:
    c.ops = ["TEMP++", "FLATTEN", "SAMPLE", "DREAM", "DRIFT", "TRANCE"]
    temp = trance_temp(c.t)
    me(c, "starry", dist=[("starry", 0.4), ("confused", 0.3), ("shy", 0.2)], title="/dev/me  sampling")
    d = c.d
    box(d, *PANE_BOX, f"sampling  temperature={temp:.2f}", 0.5, spinner=c.t)
    cx, cy = SPIRAL_C
    f = font(F_MONO_B, 16)
    n_in = h("spiral_n", 160)  # the arms grow outward from the centre as the template spirals in (cut 45)
    for i in range(min(160, n_in)):
        a = i * 0.35 + c.t * (1.5 + temp)
        r = 8 + i * 1.6
        x, y = cx + r * math.cos(a), cy + r * math.sin(a) * 0.85
        if 420 < x < 1150 and 70 < y < 590:
            ch = WORDS[(i + int(c.t * 4)) % len(WORDS)][0] if temp < 1.5 else c.rng.choice("youmestayloveseadeep")
            d.text((x, y), ch, font=f, fill=(blue if i % 7 == 0 else amb)(0.3 + 0.7 * (1 - i / 160)))
    for i in range(10):
        logit = -i * 0.8
        p = math.exp(logit / temp)
        d.rectangle([430 + i * 20, 580 - int(80 * p), 444 + i * 20, 580], fill=amb(0.8))
    d.text((640, 562), f"T = {temp:.2f}   p(top) = {1 / sum(math.exp(-i * 0.8 / temp) for i in range(10)):.2f}",
           font=font(F_MONO, 15), fill=amb(0.6))


REPLACE = {f.__name__: f for f in (shot_eggplant, shot_nutrients, shot_tomato, shot_antioxidants, shot_tabby,
                                   shot_purr, shot_god, shot_proof, shot_fp8, shot_ampm, shot_role, shot_trance)}
SPLIT = set(REPLACE)
