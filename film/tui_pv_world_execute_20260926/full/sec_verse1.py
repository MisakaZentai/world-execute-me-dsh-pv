"""Section: verse 1 (29.2 - 44.0 s, the maths verse) and pre-chorus 1 up to the ported chorus (44.0 - 54.2 s).

Every maths image is read as a model part:
points -> she is a point cloud in embedding space; dimension -> her 7168-d vector handed to you;
circle / circumference -> RoPE rotations; sine / tangents -> she sits on the tangent of a positional sine;
infinity / limitations -> the context window stretched by YaRN until it hits its wall.
Pre-chorus: AC/DC on a GPU power trace; "blind my vision" -> causal mask (and a black bar over her eyes);
dizzy -> loss landscape spinning; AD/BC -> position ids running backwards through time.
"""

from __future__ import annotations

import math
import random

from PIL import Image, ImageDraw

import facts as F
from engine import (BEAT, CENTER, FULL, LEFT, Ctx, add, beat_index, beat_t, lyric_start, me_pane, pulse, snap8)
from tuikit import (AMBER, BG, BLUE_HI, F_HEAD, F_MONO, F_MONO_B, W, H, amb, anom, banner_bits, blue, box, decode,
                    dot_chart, ease, font, halfblock, halfblock_lum, heat_cell, smooth, sprite_src)


def her_points(n: int, w: int, h: int, seed: int = 3) -> list[tuple[float, float, float]]:
    """n points sampled inside her silhouette (normalised 0..1) with brightness."""
    lum, alpha = halfblock_lum("cheerful", "full", w, h, 1)
    A, L = alpha.load(), lum.load()
    rnd = random.Random(seed)
    pts = []
    tries = 0
    while len(pts) < n and tries < n * 40:
        tries += 1
        x, y = rnd.randrange(lum.width), rnd.randrange(lum.height)
        if A[x, y]:
            pts.append((x / lum.width, y / lum.height, L[x, y] / 255))
    return pts


def shot_points(c: Ctx) -> None:
    """If I'm a set ...: a random cloud collapses into her shape."""
    c.ops = ["EMBED", "PCA", "TSNE.STEP", "ATTRACT", "REPEL", "CONVERGE"]
    d = c.d
    box(d, *FULL, "embedding(me)  as a point set", 0.5, spinner=c.t)
    pts = her_points(1400, 120, 240)
    rnd = random.Random(9)
    g = ease(c.u * 1.25)
    ox, oy, sw, sh = 440, 70, 260, 520
    for i, (px, py, lv) in enumerate(pts):
        rx, ry = 60 + rnd.random() * 1080, 70 + rnd.random() * 520
        tx, ty = ox + px * sw, oy + py * sh
        jitter = (1 - g) * 6
        x = rx + (tx - rx) * g + jitter * math.sin(c.t * 5 + i)
        y = ry + (ty - ry) * g + jitter * math.cos(c.t * 4 + i)
        col = blue(0.35 + 0.65 * lv) if g > 0.3 else amb(0.4 + 0.4 * lv)
        d.rectangle([x, y, x + 2, y + 2], fill=col)
    c.text((760, 120), f"|points| = {len(pts)}", font(F_MONO_B, 22), amb(0.9))
    c.text((760, 160), f"clustering ... {int(100 * g):3d}%", font(F_MONO, 20), amb(0.7))
    if g > 0.9:
        c.text((760, 220), "cluster[0] = me", font(F_HEAD, 30), blue(1.0), age=c.lt - 0.8 * c.dur, rate=30)


def shot_dimension(c: Ctx) -> None:
    """Then I will give ... dimension: her 7168-d vector streams over into 'you'."""
    c.ops = ["HIDDEN", "D_MODEL", "COPY", "SEND", "RECV", "you.ADD"]
    me_pane(c, "cheerful", dist=[("cheerful", 0.72), ("starry", 0.18), ("shy", 0.06)])
    d = c.d
    box(d, 404, 56, 1164, 604, f"transfer  me.hidden[0:{F.D_MODEL}]  ->  you", 0.5, spinner=c.t)
    g = ease(c.u * 1.2)
    rows, cols = 16, 28
    rr = random.Random(12)
    vals = [[rr.random() for _ in range(cols)] for _ in range(rows)]
    for r in range(rows):
        for q in range(cols):
            sent = (r * cols + q) / (rows * cols) < g
            x0, y0 = 430 + q * 12, 90 + r * 26
            x1, y1 = 790 + q * 12, 90 + r * 26
            v = vals[r][q]
            if sent:
                heat_cell(d, x1, y1, 12, 22, v, AMBER)
                d.rectangle([x0, y0, x0 + 10, y0 + 20], outline=blue(0.2))
            else:
                heat_cell(d, x0, y0, 12, 22, v, BLUE_HI)
    k = int(g * rows * cols)
    fly_r, fly_q = divmod(min(k, rows * cols - 1), cols)
    fx = 430 + fly_q * 12 + (360) * ((c.t * 6) % 1)
    d.rectangle([fx, 90 + fly_r * 26, fx + 10, 110 + fly_r * 26], fill=blue(1.0))
    c.text((430, 520), "me", font(F_MONO_B, 20), blue(0.95))
    c.text((790, 520), "you", font(F_MONO_B, 20), amb(0.95))
    c.text((430, 560), f"dims given: {int(g * F.D_MODEL):>4} / {F.D_MODEL}", font(F_MONO_B, 20), amb(0.95))


def rope_panel(c: Ctx, x0, y0, n=6, R=70, labels=True, speed=1.0, highlight=None) -> None:
    d = c.d
    for i in range(n):
        cx, cy = x0 + (i % 3) * 240 + R + 20, y0 + (i // 3) * 230 + R + 30
        theta = (c.t * speed) * (1.8 / (1 + i * 0.9))
        d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=amb(0.55), width=2)
        d.line([cx - R - 6, cy, cx + R + 6, cy], fill=amb(0.2))
        d.line([cx, cy - R - 6, cx, cy + R + 6], fill=amb(0.2))
        ex, ey = cx + R * math.cos(theta), cy + R * math.sin(theta)
        col = blue if highlight is None or highlight == i else amb
        d.line([cx, cy, ex, ey], fill=col(0.95), width=2)
        d.rectangle([ex - 3, ey - 3, ex + 3, ey + 3], fill=col(1.0))
        if labels:
            c.text((cx - R, cy + R + 8), f"freq_{i}  θ={theta % math.tau:4.2f}", font(F_MONO, 13), amb(0.7))


def shot_circle(c: Ctx) -> None:
    """If I'm a circle: rotary position embedding, one rotating pair per frequency."""
    c.ops = ["ROPE", "COS", "SIN", "ROTATE", "Q", "K", "QK^T"]
    me_pane(c, "starry", dist=[("starry", 0.6), ("cheerful", 0.3), ("shy", 0.05)])
    box(c.d, 404, 56, 1164, 604, "rotary position embedding", 0.5, spinner=c.t)
    rope_panel(c, 420, 70, speed=2.2)


def shot_circumference(c: Ctx) -> None:
    """Then I will give ... circumference: one circle unrolls into its perimeter, 2*pi*r counted out."""
    c.ops = ["2*PI*R", "UNROLL", "INTEGRATE", "SUM", "GIVE"]
    me_pane(c, "cheerful", dist=[("cheerful", 0.7), ("starry", 0.2), ("shy", 0.05)])
    d = c.d
    box(d, 404, 56, 1164, 604, "circumference(me)", 0.5, spinner=c.t)
    g = ease(c.u * 1.2)
    cx, cy, R = 600, 240, 120
    arc = g * math.tau
    for k in range(120):
        a = k / 120 * math.tau
        on = a > arc
        if on:
            d.rectangle([cx + R * math.cos(a) - 1, cy + R * math.sin(a) - 1, cx + R * math.cos(a) + 1,
                         cy + R * math.sin(a) + 1], fill=blue(0.9))
    L = 2 * math.pi * R * g
    y = 440
    d.line([440, y, 440 + L * 0.9, y], fill=blue(1.0), width=3)
    for k in range(0, int(L * 0.9), 40):
        d.line([440 + k, y - 6, 440 + k, y + 6], fill=amb(0.6))
    c.text((440, 470), f"C = 2πr = {2 * math.pi * g:.5f} r", font(F_MONO_B, 22), amb(0.95))
    c.text((440, 510), "given to: you", font(F_MONO, 20), amb(0.75), age=c.lt - 0.5)


def shot_sine(c: Ctx) -> None:
    """If I'm a sine ...: sinusoidal channels of the position code, scrolling."""
    c.ops = ["POS", "SIN", "COS", "FREQ", "CONCAT"]
    me_pane(c, "shy", dist=[("shy", 0.55), ("starry", 0.3), ("cheerful", 0.1)])
    d = c.d
    box(d, 404, 56, 1164, 604, "positional code  sin(pos / 10000^(2i/d))", 0.5, spinner=c.t)
    for i in range(7):
        y0 = 100 + i * 70
        fr = 0.02 * (1.7 ** i)
        pts = [(430 + x, y0 + 22 * math.sin((x + c.t * 180) * fr / 1.0)) for x in range(0, 720, 3)]
        d.line(pts, fill=(blue if i == 2 else amb)(0.9 if i == 2 else 0.55), width=2 if i == 2 else 1)
        c.text((1120, y0 - 8), f"i={i}", font(F_MONO, 12), amb(0.5))


def shot_tangent(c: Ctx) -> None:
    """Then you can sit ... tangents: a tangent line rides the sine; a tiny her sits on it."""
    c.ops = ["DERIV", "COS", "TANGENT", "SLOPE", "SIT"]
    d = c.d
    box(d, *FULL, "d/dx sin(x) = cos(x)", 0.5, spinner=c.t)
    x0, y0, A = 60, 330, 150
    pts = [(x0 + x, y0 - A * math.sin(x / 110)) for x in range(0, 1080, 3)]
    d.line(pts, fill=blue(0.9), width=3)
    px = 60 + ((c.lt / c.dur) * 1.1 % 1) * 1000
    xx = (px - x0) / 110
    py = y0 - A * math.sin(xx)
    slope = -A * math.cos(xx) / 110
    L = 160
    dx = L / math.sqrt(1 + slope * slope)
    d.line([px - dx, py - slope * dx, px + dx, py + slope * dx], fill=amb(1.0), width=2)
    sp = halfblock("cheerful", "upper", 70, 80, 2)
    c.img.paste(sp, (int(px - sp.width / 2), int(py - sp.height + 6)), sp)
    c.text((60, 540), f"x = {xx:5.2f}   slope = cos(x) = {math.cos(xx):+.3f}", font(F_MONO_B, 20), amb(0.95))


def shot_infinity(c: Ctx) -> None:
    """If I approach infinity: the context window stretches (YaRN) 4K -> 32K -> 128K ..."""
    c.ops = ["YARN", "SCALE", "ROPE.EXT", "CTX++", "ATTN", "KV.GROW"]
    me_pane(c, "starry", dist=[("starry", 0.8), ("cheerful", 0.1), ("shy", 0.05)])
    d = c.d
    box(d, 404, 56, 1164, 604, "context window", 0.5, spinner=c.t)
    stages = [4096, 131072, F.CTX, 10 ** 9]
    k = min(3, int(c.u * 4))
    g = ease((c.u * 4) % 1)
    cur = stages[k - 1] + (stages[k] - stages[k - 1]) * g if k > 0 else stages[0] * g
    frac = math.log10(max(1, cur)) / 9
    d.rectangle([430, 200, 430 + int(700 * frac), 240], fill=amb(0.85))
    d.rectangle([430, 200, 1130, 240], outline=amb(0.3))
    for s in stages[:3]:
        xx = 430 + int(700 * math.log10(s) / 9)
        d.line([xx, 190, xx, 250], fill=amb(0.5))
        c.text((xx - 20, 256), f"{s // 1024}K" if s < 2 ** 20 else "1M", font(F_MONO, 14), amb(0.6))
    label = "∞" if k == 3 and g > 0.5 else f"{int(cur):,}"
    c.text((430, 120), f"n_ctx -> {label}", font(F_HEAD, 34), blue(0.95))
    c.text((430, 320), "lim   attention(me, you)", font(F_MONO_B, 24), amb(0.9))
    c.text((430, 350), "n->∞", font(F_MONO, 16), amb(0.7))
    c.text((430, 400), "= you", font(F_HEAD, 40), blue(1.0), age=c.lt - 0.5, rate=20)


def shot_limit(c: Ctx) -> None:
    """Then you can be ... limitations: the window hits max_position_embeddings; you are the wall."""
    c.ops = ["CTX.MAX", "TRUNCATE", "WALL", "YOU", "LIMIT"]
    me_pane(c, "shy", dist=[("shy", 0.7), ("starry", 0.2), ("confused", 0.05)])
    d = c.d
    box(d, 404, 56, 1164, 604, "limits", 0.5, spinner=c.t)
    g = ease(c.u * 1.3)
    x = 430 + int(600 * g)
    d.rectangle([430, 200, x, 260], fill=blue(0.8))
    d.rectangle([1040, 170, 1060, 290], fill=amb(1.0))
    c.text((1020, 300), "you", font(F_MONO_B, 22), amb(1.0))
    c.text((430, 330), f"max_context = {F.CTX:,}", font(F_MONO, 18), amb(0.7))
    c.text((430, 360), "limit(me) := you", font(F_HEAD, 32), amb(0.95), age=c.lt - 0.3, rate=25)
    if g > 0.98:
        c.text((430, 420), "warn: nothing beyond this point", font(F_MONO, 18), anom(0.9))


# ---------------------------------------------------------------- pre-chorus 1

def shot_current(c: Ctx) -> None:
    """Switch my current ... (AC, DC): the GPU power trace flips between alternating and flat."""
    c.ops = ["POWER", "RECTIFY", "AC", "DC", "CLOCK", "BOOST"]
    me_pane(c, "confused", dist=[("confused", 0.5), ("starry", 0.3), ("shy", 0.15)])
    d = c.d
    box(d, 404, 56, 1164, 604, f"nvidia-smi --power  8x {F.GPU}", 0.5, spinner=c.t)
    ac_dc = int(c.lt / (BEAT * 2)) % 2
    for g in range(8):
        y0 = 90 + g * 58
        pts = []
        for x in range(0, 640, 3):
            ph = (x + c.t * 260) / 40
            v = math.sin(ph + g) if ac_dc == 0 else (0.7 + 0.05 * math.sin(ph * 3))
            pts.append((460 + x, y0 + 18 - 18 * v))
        d.line(pts, fill=amb(0.85), width=1)
        c.text((420, y0 + 8), f"GPU{g}", font(F_MONO, 12), amb(0.6))
        c.text((1110, y0 + 8), f"{650 + int(40 * math.sin(c.t * 3 + g))}W", font(F_MONO, 12), amb(0.7))
    c.text((430, 560), "mode: " + ("AC" if ac_dc == 0 else "DC"), font(F_HEAD, 28), blue(1.0))


def shot_blind(c: Ctx) -> None:
    """And then blind ...: the causal mask blacks out the future, and a bar blacks out her eyes."""
    c.ops = ["MASK", "TRIU", "-INF", "SOFTMAX", "BLIND"]
    g = ease(c.u * 1.4)

    def eyebar(cc, sx, sy, sp):
        y = sy + int(sp.height * 0.115)
        w = int(sp.width * g)
        cc.d.rectangle([sx + sp.width // 2 - w // 2, y, sx + sp.width // 2 + w // 2, y + 16], fill=BG)
        cc.d.rectangle([sx + sp.width // 2 - w // 2, y, sx + sp.width // 2 + w // 2, y + 16], outline=amb(0.7))

    me_pane(c, "serious", overlay=eyebar, dist=[("serious", 0.6), ("confused", 0.3), ("shy", 0.05)])
    d = c.d
    box(d, 404, 56, 1164, 604, "causal mask", 0.5, spinner=c.t)
    n = 12
    cs = 40
    for i in range(n):
        for j in range(n):
            x, y = 470 + j * cs, 80 + i * cs
            future = j > i
            if future and (i + j) / (2 * n) < g + 0.1:
                d.rectangle([x, y, x + cs - 3, y + cs - 3], fill=(0, 0, 0))
                d.text((x + 6, y + 10), "-∞", font=font(F_MONO, 13), fill=amb(0.35))
            else:
                heat_cell(d, x, y, cs, cs, 0.2 + 0.6 * random.Random(i * 13 + j).random() * (1 - future * 0.8))
    c.text((970, 120), "future:", font(F_MONO, 18), amb(0.7))
    c.text((970, 150), "masked", font(F_MONO_B, 22), amb(0.95))


def shot_dizzy(c: Ctx) -> None:
    """So dizzy, so dizzy: the loss landscape spins; a ball rolls to the minimum."""
    c.ops = ["GRAD", "HESSIAN?", "LR", "SPIN", "ADAMW", "STEP"]
    d = c.d
    box(d, *FULL, "loss landscape", 0.5, spinner=c.t)
    rot = c.t * (2.4 if c.u < 0.5 else -2.8)
    cx, cy = 590, 340
    N = 22
    for i in range(N):
        for j in range(N):
            x, y = (i - N / 2) / 3.2, (j - N / 2) / 3.2
            z = 0.25 * (x * x + y * y) - 1.3 * math.exp(-((x - 1) ** 2 + (y + 0.5) ** 2)) + 0.3 * math.sin(2 * x)
            xr = x * math.cos(rot) - y * math.sin(rot)
            yr = x * math.sin(rot) + y * math.cos(rot)
            px, py = cx + xr * 70, cy + yr * 26 - z * 60
            d.rectangle([px, py, px + 2, py + 2], fill=amb(0.25 + 0.6 * (1 - min(1.0, max(0.0, z / 4)))))
    g = ease(c.u)
    bx, by = 2.5 - 1.5 * g, 2.0 - 2.5 * g
    zb = 0.25 * (bx * bx + by * by) - 1.3 * math.exp(-((bx - 1) ** 2 + (by + 0.5) ** 2)) + 0.3 * math.sin(2 * bx)
    xr = bx * math.cos(rot) - by * math.sin(rot)
    yr = bx * math.sin(rot) + by * math.cos(rot)
    px, py = cx + xr * 70, cy + yr * 26 - zb * 60
    sp = halfblock("confused", "face", 60, 60, 2)
    c.img.paste(sp, (int(px - sp.width / 2), int(py - sp.height)), sp)
    c.text((940, 120), f"lr = {3e-4 * (1 + math.sin(c.t * 6)):.2e}", font(F_MONO_B, 18), amb(0.9))
    c.text((940, 150), "grad_norm", font(F_MONO, 16), amb(0.6))
    for k in range(24):
        v = abs(math.sin(c.t * 7 + k * 0.7)) * (0.5 + 0.5 * (k % 5 == 0))
        d.rectangle([940 + k * 8, 240 - v * 70, 945 + k * 8, 240], fill=anom(0.8) if v > 0.8 else amb(0.7))


def shot_travel(c: Ctx) -> None:
    """Oh, we can travel ... (AD, BC): position ids and timestamps run backwards through the calendar."""
    c.ops = ["POS_ID", "ROPE", "TIME", "REWIND", "AD", "BC"]
    me_pane(c, "starry", dist=[("starry", 0.66), ("cheerful", 0.2), ("shy", 0.1)])
    d = c.d
    box(d, 404, 56, 1164, 604, "time travel  (position ids)", 0.5, spinner=c.t)
    g = c.u
    year = int(2026 - g * 5026)
    era = "AD" if year > 0 else "BC"
    shown = abs(year) if year != 0 else 1
    c.text((430, 100), f"{shown:>5} {era}", font(F_HEAD, 72), blue(1.0) if era == "BC" else amb(1.0))
    for i in range(30):
        pos = int(g * 5026) - i * 173
        x = 430 + i * 24
        h = 40 + 30 * math.sin(pos * 0.01)
        d.rectangle([x, 380 - h, x + 18, 380], fill=amb(0.3 + 0.02 * i))
    rope_panel(c, 430, 390, n=3, R=40, labels=False, speed=-3.0 if era == "BC" else 3.0)


def build() -> None:
    v = [lyric_start(p, a) for p, a in (("If I'm a set", 29), ("Then I will give", 29), ("If I'm a circle", 29),
                                        ("Then I will give", 33), ("If I'm a sine", 29),
                                        ("Then you can sit", 29), ("If I approach", 29), ("Then you can be", 29))]
    p = [lyric_start(x, 44) for x in ("Switch", "And", "So", "Oh,")]
    cuts = [snap8(x) for x in v + p] + [beat_t(117)]
    fns = [shot_points, shot_dimension, shot_circle, shot_circumference, shot_sine, shot_tangent, shot_infinity,
           shot_limit, shot_current, shot_blind, shot_dizzy, shot_travel]
    chapters = ["01 / PRETRAIN"] * 8 + ["02 / SFT"] * 4
    for fn, a, b, ch in zip(fns, cuts, cuts[1:], chapters):
        add(a, b, fn, chapter=ch)
