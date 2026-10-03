"""In-memory v2 versions of the 00 BOOT tail and 01 PRETRAIN scenes (12.4 - 47.2 s).

The drawings are the originals from full/sec_intro.py and full/sec_verse1.py, with two changes:
- The four scenes that used the whole body width (dualpipe, whale, points, tangent) are drawn in the split pane at
  their original cell and glyph size, so she keeps her pane. Nothing is scaled down. DualPipe shows 27 of its 40
  steps; the whale swims inside the pane; the tangent camera follows the rider along the same sine.
- HOOK lets a transition take an object over while the rest of the scene keeps drawing itself: the corpus words
  converge into the loss curve, the curve rewinds, the whale's letters become points, and so on.
"""
from __future__ import annotations

import math
import random
from functools import lru_cache

from PIL import Image, ImageDraw

import facts as F
import sec_intro as S0
import sec_verse1 as S1
from engine import CENTER, FULL, LEFT
from tuikit import (AMBER, BG, BLUE_HI, F_CJK, F_HEAD, F_MONO, F_MONO_B, amb, anom, banner_bits, blue, box,
                    dot_chart, ease, font, halfblock, heat_cell)

from kit import HOOK  # noqa: E402

PANE_BOX = (404, 56, 1164, 604)


def h(key, default=None):
    return HOOK.get(key, default)


def me(c, expr, **kw):
    return S0.me_pane(c, expr, **kw)  # the stub installed by kit: she is drawn by her own layer


# ---------------------------------------------------------------- 00 BOOT: begin the simulation

def countdown_cells(n: int, rows: int = 14) -> list:
    """(x, y, glyph) of every lit cell of the countdown digit n, where shot_begin_sim draws it (boot hooks)."""
    bits = banner_bits(str(n), rows, 2.0)
    B = bits.load()
    cw = font(F_MONO_B, 16).getlength("M")
    x0 = 784 - bits.width * cw / 2
    return [(x0 + q * cw, 200 + r * 17, str(n)) for r in range(bits.height) for q in range(bits.width) if B[q, r]]


def shot_begin_sim(c) -> None:
    # boot hooks (all optional, the defaults draw the original): count=False hides the countdown digit while the
    # cut into this shot builds it; rows sets the digit height in cell rows; extra(c) draws on top (status line)
    c.ops = ["SIM.START", "EPOCH 0", "STEP 0", "FORWARD", "BACKWARD", "UPDATE"]
    d = c.d
    me(c, "cheerful", dist=[("cheerful", 0.7), ("starry", 0.2), ("shy", 0.05)])
    box(d, *PANE_BOX, "sim.start()", 0.5, spinner=c.t)
    if c.u < 0.55:
        n = 3 - min(2, int(c.u / 0.55 * 3))
        bits = banner_bits(str(n), h("rows", 14), 2.0)
        B = bits.load()
        f = font(F_MONO_B, 16)
        cw = f.getlength("M")
        for r in range(bits.height if h("count", True) else 0):
            s = "".join(str(n) if B[q, r] else " " for q in range(bits.width))
            d.text((784 - bits.width * cw / 2, 200 + r * 17), s, font=f, fill=amb(0.95))
    else:
        if h("run", True):
            c.text((460, 200), "RUN", font(F_HEAD, 120), amb(1.0), age=c.lt - 0.55 * c.dur, rate=12)
        if h("status", True):
            c.text((460, 400), "simulation: running", font(F_MONO_B, 22), amb(0.9))
        if h("budget", True):
            c.text((460, 440), f"tokens budget: {F.PRETRAIN_TOKENS}", font(F_MONO, 20), amb(0.7))
    if h("extra"):
        h("extra")(c)


# ---------------------------------------------------------------- 01 PRETRAIN

def corpus_tokens(t: float) -> list:
    """(x, y, token, level) of the token river at time t, as the original draws it (kept inside the pane)."""
    out = []
    for row in range(20):
        speed = 90 + (row * 37) % 120
        off = (t * speed + row * 53) % 120
        x = 1150 + off - 120
        k = 0
        while x > 420:
            tok = S0.CORPUS[(row * 7 + k + int((t * speed) // 120)) % len(S0.CORPUS)]
            lv = 0.25 + 0.5 * ((row + k) % 3 == 0)
            if x - 60 >= 414:
                out.append((x - 60, 80 + row * 24, tok, lv))
            x -= 60 + 7 * len(tok)
            k += 1
    return out


def corpus_font(tok: str, size: int = 15):
    return font(F_CJK if any(ord(ch) > 0x2E80 for ch in tok) else F_MONO, size)


def shot_corpus(c) -> None:
    c.ops = ["DATALOADER", "TOKENIZE", "PACK", "FORWARD", "LOSS", "BACKWARD", "ALLREDUCE", "STEP"]
    me(c, "serious", dist=[("serious", 0.6), ("confused", 0.25), ("starry", 0.1)], title="/dev/me  learning")
    d = c.d
    box(d, *PANE_BOX, "corpus.stream", 0.5, spinner=c.t)
    if h("words", True):
        for x, y, tok, lv in corpus_tokens(c.t):
            d.text((x, y), tok, font=corpus_font(tok), fill=amb(lv))
    if h("counter", True):
        c.text((430, 572), counter_text(c.t), font(F_MONO_B, 18), amb(0.95))


def counter_text(t: float) -> str:
    return f"tokens seen  {F.PRETRAIN_TOKENS_T * ((t - 16.0) / 13.3):5.2f}T / {F.PRETRAIN_TOKENS}"


_rnd = random.Random(4)
_NOISE = [_rnd.gauss(0, 1) for _ in range(600)]
LOSS_BOX = (440, 80, 690, 320)


def loss_fn(u: float) -> float:
    return 0.92 * math.exp(-5 * u) + 0.12 + 0.02 * _NOISE[int(u * 599)] * (1 - u * 0.7)


@lru_cache(None)
def loss_points() -> list:
    """(u, x, y) of every dot column of the loss chart, as dot_chart places them."""
    x, y, w, hh = LOSS_BOX
    cols, rows = w // 5, hh // 5
    out = []
    for i in range(cols):
        u = i / (cols - 1)
        v = min(1.0, loss_fn(u))
        r = int(round((1 - max(0.0, v)) * (rows - 1)))
        out.append((u, x + i * 5, y + r * 5))
    return out


def loss_at(progress: float):
    pts = [p for p in loss_points() if p[0] <= progress]
    return pts[-1] if pts else loss_points()[0]


def loss_label(u: float) -> str:
    return f"{2.2 * loss_fn(min(1.0, u)) + 0.31:.4f}"


def shot_losscurve(c) -> None:
    c.ops = ["FORWARD", "MTP.HEAD", "LOSS", "BACKWARD", "FP8.GEMM", "ALLREDUCE", "ADAMW", "LR.SCHED"]
    me(c, "serious", dist=[("serious", 0.66), ("starry", 0.2), ("confused", 0.1)])
    d = c.d
    box(d, 404, 56, 1164, 420, "train/loss", 0.5, spinner=c.t)
    progress = h("progress", ease(c.u * 1.05) * 0.98 + 0.02)
    last = dot_chart(d, *LOSS_BOX, loss_fn, progress, amb(0.95))
    if last and h("label", True):
        c.text((last[0] - 80, last[1] - 26), loss_label(c.u), font(F_MONO_B, 16), amb(1.0))
    if h("xlabel"):
        d.text((446, 400), h("xlabel"), font=font(F_MONO, 13), fill=amb(0.55))
    if h("lr", True):
        box(d, 404, 440, 1164, 604, "lr schedule", 0.5)

        def lr(u):
            if u < 0.05:
                return u / 0.05 * 0.9
            if u < 0.7:
                return 0.9
            return 0.9 * max(0.0, 1 - (u - 0.7) / 0.3) ** 1.5 + 0.1

        dot_chart(d, 440, 460, 690, 120, lr, ease(c.u * 1.05), amb(0.7), sy=4)
        c.text((440, 582), F.LOSS_NOTE, font(F_MONO, 14), amb(0.6))


PIPE = dict(ranks=8, steps=27, cw=26, ch=44, ox=470, oy=110)


def pipe_cells(lt: float, dur: float, delay: float = 0.0) -> list:
    """(rank, step, x, y, kind) of the DualPipe cells drawn at local time lt; kind F, B, Bd (dim B) or W."""
    P = PIPE
    head = max(0.0, (lt - delay) / max(0.3, dur - delay)) * P["steps"] * 1.15
    out = []
    for r in range(P["ranks"]):
        for s in range(P["steps"]):
            if s > head:
                break
            phase = (s + r) % 6
            if (s < r and s < P["ranks"] - r) or (s > P["steps"] - 3 and phase == 0):
                continue
            kind = "F" if phase < 2 else ("B" if (s + P["ranks"] - r) % 5 % 2 else "Bd") if phase < 4 else "W"
            out.append((r, s, P["ox"] + s * P["cw"], P["oy"] + r * P["ch"], kind))
    return out, head


def draw_cell(d, x, y, kind, a: float = 1.0) -> None:
    P = PIPE
    fs = font(F_MONO_B, 11)
    x1, y1 = x + P["cw"] - 3, y + P["ch"] - 6
    if kind == "F":
        d.rectangle([x, y, x1, y1], fill=amb(0.75 * a))
        d.text((x + 7, y + 13), "F", font=fs, fill=BG)
    elif kind in ("B", "Bd"):
        d.rectangle([x, y, x1, y1], fill=blue((0.75 if kind == "B" else 0.5) * a))
        d.text((x + 7, y + 13), "B", font=fs, fill=BG)
    else:
        d.rectangle([x, y, x1, y1], outline=amb(0.5 * a))
        d.text((x + 7, y + 13), "W", font=fs, fill=amb(0.8 * a))


def shot_dualpipe(c) -> None:
    c.ops = ["DUALPIPE", "F", "B", "W", "COMM.OVERLAP", "ALL2ALL", "DISPATCH", "COMBINE"]
    me(c, "serious", dist=[("serious", 0.62), ("starry", 0.22), ("confused", 0.1)])
    d = c.d
    P = PIPE
    box(d, *PANE_BOX, "pipeline schedule  DualPipe  (8 PP ranks, 20 micro-batches)", 0.5, spinner=c.t)
    cells, head = pipe_cells(c.lt, c.dur, h("delay", 0.0))
    gone = h("gone")  # (rank, step) -> 0..1 already lifted off by the next transition
    for r in range(P["ranks"]):
        d.text((P["ox"] - 40, P["oy"] + r * P["ch"] + 12), f"PP{r}", font=font(F_MONO, 13), fill=amb(0.6))
    for r, s, x, y, kind in cells:
        a = 1.0 - (gone(r, s) if gone else 0.0)
        if a > 0.02:
            draw_cell(d, x, y, kind, a)
    hx = P["ox"] + head * P["cw"]
    if head > 0 and hx < P["ox"] + P["steps"] * P["cw"]:
        d.line([hx, P["oy"] - 10, hx, P["oy"] + P["ranks"] * P["ch"]], fill=amb(1.0), width=2)
    if h("notes", True):
        c.text((430, 480), F.DUALPIPE_NOTE, font(F_MONO, 16), amb(0.75))
        c.text((430, 510), F.GPU_HOURS_NOTE, font(F_MONO_B, 18), amb(0.95), age=c.lt - 0.4)


WHALE = dict(cols=64, rows=17, ch=16)


def whale_glyphs(t: float, u: float) -> list:
    """(x, y, letter) of every 'deepseek' letter of the whale at time t."""
    f = font(F_MONO_B, 15)
    cw = f.getlength("M")
    bits = S0.whale_bits(WHALE["cols"], WHALE["rows"], t * 5)
    B = bits.load()
    x = 588 - u * 148
    y0 = 150 + 18 * math.sin(t * 2.2)
    out, k = [], 0
    for r in range(WHALE["rows"]):
        for q in range(WHALE["cols"]):
            if B[q, r]:
                out.append((x + q * cw, y0 + r * WHALE["ch"], "deepseek"[k % 8]))
                k += 1
    return out


def shot_whale(c) -> None:
    c.ops = ["CKPT.SAVE", "3FS.WRITE", "SHARD", "FSYNC", "VERIFY", "CONTINUE"]
    me(c, "starry", dist=[("starry", 0.6), ("cheerful", 0.25), ("shy", 0.08)], bubbles=0.6)
    d = c.d
    box(d, *PANE_BOX, "checkpoint", 0.45, spinner=c.t)
    f = font(F_MONO_B, 15)
    cw = f.getlength("M")
    a = h("whale", 1.0)
    if a > 0.02:
        for x, y, ch in whale_glyphs(c.t, c.u):
            d.text((x, y), ch, font=f, fill=blue(0.95 * a))
        x = 588 - c.u * 148
        y0 = 150 + 18 * math.sin(c.t * 2.2)
        fb = font(F_MONO, 18)
        for i in range(16):
            ph = (c.t * 0.7 + i * 0.137) % 1
            bx = x + cw * WHALE["cols"] * 0.18 + 10 * math.sin(c.t * 3 + i) + (i % 4) * 8
            by = y0 - 10 - ph * 130
            if 70 < by < 590 and 412 < bx < 1150:
                d.text((bx, by), "oO°."[i % 4], font=fb, fill=blue(0.85 * (1 - ph) * a))
    step = int((c.t - 16) * 5200)
    for i in range(min(6, int(c.u * 6) + 1)):
        c.text((430, 460 + i * 22), f"[ OK ] checkpoint step_{(step // 6) * (i + 1):07d} -> {F.FS_NAME}",
               font(F_MONO, 15), amb(0.7), age=c.lt - i * 0.2, rate=120)


@lru_cache(None)
def point_set() -> list:
    """(target x, y, level, random x, y) per point: the original seeds, scattered over the pane."""
    pts = S1.her_points(1400, 120, 240)
    rnd = random.Random(9)
    out = []
    for px, py, lv in pts:
        rx, ry = 420 + rnd.random() * 720, 70 + rnd.random() * 520
        out.append((440 + px * 260, 70 + py * 520, lv, rx, ry))
    return out


def points_pos(t: float, u: float) -> list:
    """(x, y, colour) of every point at time t."""
    g = ease(u * 1.25)
    out = []
    for i, (tx, ty, lv, rx, ry) in enumerate(point_set()):
        jitter = (1 - g) * 6
        x = rx + (tx - rx) * g + jitter * math.sin(t * 5 + i)
        y = ry + (ty - ry) * g + jitter * math.cos(t * 4 + i)
        out.append((x, y, blue(0.35 + 0.65 * lv) if g > 0.3 else amb(0.4 + 0.4 * lv)))
    return out


def shot_points(c) -> None:
    c.ops = ["EMBED", "PCA", "TSNE.STEP", "ATTRACT", "REPEL", "CONVERGE"]
    me(c, "cheerful", dist=[("cheerful", 0.64), ("starry", 0.22), ("shy", 0.08)])
    d = c.d
    box(d, *PANE_BOX, "embedding(me)  as a point set", 0.5, spinner=c.t)
    g = ease(c.u * 1.25)
    if h("points", True):
        src = h("from")  # (positions, blend(i) -> 0..1): the points start where the whale's letters were
        for i, (x, y, col) in enumerate(points_pos(c.t, c.u)):
            if src:
                sx, sy = src[0][i % len(src[0])]
                b = src[1](i)
                x, y = sx + (x - sx) * b, sy + (y - sy) * b
            d.rectangle([x, y, x + 2, y + 2], fill=col)
    if h("labels", True):
        c.text((760, 120), "|points| = 1400", font(F_MONO_B, 22), amb(0.9))
        c.text((760, 160), f"clustering ... {int(100 * g):3d}%", font(F_MONO, 20), amb(0.7))
        if g > 0.9:
            c.text((760, 220), "cluster[0] = me", font(F_HEAD, 30), blue(1.0), age=c.lt - 0.8 * c.dur, rate=30)


YOU_GRID = (790, 90, 1126, 506)


def shot_dimension(c) -> None:
    c.ops = ["HIDDEN", "D_MODEL", "COPY", "SEND", "RECV", "you.ADD"]
    me(c, "cheerful", dist=[("cheerful", 0.72), ("starry", 0.18), ("shy", 0.06)])
    d = c.d
    box(d, *PANE_BOX, f"transfer  me.hidden[0:{F.D_MODEL}]  ->  you", 0.5, spinner=c.t)
    g = ease(c.u * 1.2)
    rows, cols = 16, 28
    rr = random.Random(12)
    vals = [[rr.random() for _ in range(cols)] for _ in range(rows)]
    you = h("you", True)
    for r in range(rows):
        for q in range(cols):
            sent = (r * cols + q) / (rows * cols) < g
            x0, y0 = 430 + q * 12, 90 + r * 26
            x1, y1 = 790 + q * 12, 90 + r * 26
            v = vals[r][q]
            if sent:
                if you:
                    heat_cell(d, x1, y1, 12, 22, v, AMBER)
                if h("me", True):
                    d.rectangle([x0, y0, x0 + 10, y0 + 20], outline=blue(0.2))
            elif h("me", True):
                heat_cell(d, x0, y0, 12, 22, v, BLUE_HI)
    k = int(g * rows * cols)
    if g < 0.999:
        fly_r, fly_q = divmod(min(k, rows * cols - 1), cols)
        fx = 430 + fly_q * 12 + 360 * ((c.t * 6) % 1)
        d.rectangle([fx, 90 + fly_r * 26, fx + 10, 110 + fly_r * 26], fill=blue(1.0))
    if h("labels", True):
        c.text((430, 520), "me", font(F_MONO_B, 20), blue(0.95))
        c.text((790, 520), "you", font(F_MONO_B, 20), amb(0.95))
        c.text((430, 560), f"dims given: {int(g * F.D_MODEL):>4} / {F.D_MODEL}", font(F_MONO_B, 20), amb(0.95))


def rope_center(i: int, x0: int = 420, y0: int = 70, R: int = 70):
    return x0 + (i % 3) * 240 + R + 20, y0 + (i // 3) * 230 + R + 30


def rope_theta(t: float, i: int, speed: float = 2.2) -> float:
    return (t * speed) * (1.8 / (1 + i * 0.9))


def draw_rope(c, i, cx, cy, R, theta, a: float = 1.0, labels: bool = True, hand: bool = True, sweep: float = 1.0,
              col=None) -> None:
    d = c.d
    if sweep >= 0.999:
        d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=amb(0.55 * a), width=2)
    elif sweep > 0:
        d.arc([cx - R, cy - R, cx + R, cy + R], -90, -90 + 360 * sweep, fill=amb(0.55 * a), width=2)
    d.line([cx - R - 6, cy, cx + R + 6, cy], fill=amb(0.2 * a))
    d.line([cx, cy - R - 6, cx, cy + R + 6], fill=amb(0.2 * a))
    if hand:
        ex, ey = cx + R * math.cos(theta), cy + R * math.sin(theta)
        col = col or blue
        d.line([cx, cy, ex, ey], fill=col(0.95 * a), width=2)
        d.rectangle([ex - 3, ey - 3, ex + 3, ey + 3], fill=col(1.0 * a))
    if labels:
        c.text((cx - R, cy + R + 8), f"freq_{i}  θ={theta % math.tau:4.2f}", font(F_MONO, 13), amb(0.7 * a))


def shot_circle(c) -> None:
    c.ops = ["ROPE", "COS", "SIN", "ROTATE", "Q", "K", "QK^T"]
    me(c, "starry", dist=[("starry", 0.6), ("cheerful", 0.3), ("shy", 0.05)])
    box(c.d, *PANE_BOX, "rotary position embedding", 0.5, spinner=c.t)
    over = h("circles")  # i -> dict(cx, cy, R, a, labels, hand, sweep) or None to hide
    for i in range(6):
        cx, cy = rope_center(i)
        st = dict(cx=cx, cy=cy, R=70, a=1.0, labels=True, hand=True, sweep=1.0)
        if over:
            o = over(i)
            if o is None:
                continue
            st.update(o)
        draw_rope(c, i, st["cx"], st["cy"], st["R"], rope_theta(c.t, i), st["a"], st["labels"], st["hand"],
                  st["sweep"])


CIRC = dict(cx=600, cy=240, R=120, y=440)


def shot_circumference(c) -> None:
    c.ops = ["2*PI*R", "UNROLL", "INTEGRATE", "SUM", "GIVE"]
    me(c, "cheerful", dist=[("cheerful", 0.7), ("starry", 0.2), ("shy", 0.05)])
    d = c.d
    box(d, *PANE_BOX, "circumference(me)", 0.5, spinner=c.t)
    g = ease(c.u * 1.2)
    cx, cy, R = CIRC["cx"], CIRC["cy"], CIRC["R"]
    arc = g * math.tau
    if h("dots", True):
        for k in range(120):
            a = k / 120 * math.tau
            if a > arc:
                d.rectangle([cx + R * math.cos(a) - 1, cy + R * math.sin(a) - 1, cx + R * math.cos(a) + 1,
                             cy + R * math.sin(a) + 1], fill=blue(0.9))
    L = 2 * math.pi * R * g
    y = CIRC["y"]
    if h("line", True):
        d.line([440, y, 440 + L * 0.9, y], fill=blue(1.0), width=3)
        for k in range(0, int(L * 0.9), 40):
            d.line([440 + k, y - 6, 440 + k, y + 6], fill=amb(0.6))
    if h("labels", True):
        c.text((440, 470), f"C = 2πr = {2 * math.pi * g:.5f} r", font(F_MONO_B, 22), amb(0.95))
        c.text((440, 510), "given to: you", font(F_MONO, 20), amb(0.75), age=c.lt - 0.5)


def sine_wave(i: int, t: float, y0=None, amp: float = 22.0, x0: int = 430, n: int = 720):
    fr = 0.02 * (1.7 ** i)
    y0 = 100 + i * 70 if y0 is None else y0
    return [(x0 + x, y0 + amp * math.sin((x + t * 180) * fr)) for x in range(0, n, 3)]


def shot_sine(c) -> None:
    c.ops = ["POS", "SIN", "COS", "FREQ", "CONCAT"]
    me(c, "shy", dist=[("shy", 0.55), ("starry", 0.3), ("cheerful", 0.1)])
    d = c.d
    box(d, *PANE_BOX, "positional code  sin(pos / 10000^(2i/d))", 0.5, spinner=c.t)
    over = h("waves")  # i -> dict(y0, amp, a) or None to hide
    for i in range(7):
        st = dict(y0=100 + i * 70, amp=22.0, a=1.0)
        if over:
            o = over(i)
            if o is None:
                continue
            st.update(o)
        pts = sine_wave(i, c.t, st["y0"], st["amp"])
        base = 0.9 if i == 2 else 0.55
        d.line(pts, fill=(blue if i == 2 else amb)(base * st["a"]), width=2 if i == 2 else 1)
        if h("labels", True):
            c.text((1120, st["y0"] - 8), f"i={i}", font(F_MONO, 12), amb(0.5 * st["a"]))


TAN = dict(y0=330, A=150, k=110.0, x0=430, view=720)


def tangent_state(lt: float, dur: float):
    """World x of the rider (0..1000 along the original sine) and the camera offset that keeps it in view."""
    px = min(1.0, lt / dur * 1.05) * 1000
    cam = max(0.0, min(1080 - TAN["view"], px - 300))
    return px, cam


def tangent_curve(cam: float, step: int = 3) -> list:
    return [(TAN["x0"] + x, TAN["y0"] - TAN["A"] * math.sin((x + cam) / TAN["k"])) for x in range(0, TAN["view"], step)]


def rider_pos(lt: float, dur: float):
    px, cam = tangent_state(lt, dur)
    xx = px / TAN["k"]
    return TAN["x0"] + px - cam, TAN["y0"] - TAN["A"] * math.sin(xx), xx


RIDER = [None]  # t -> sprite: set when her figure comes from somewhere else (the rider is a small copy of her)


def rider_sprite(t: float = 0.0):
    if RIDER[0]:
        return RIDER[0](t)
    return halfblock("cheerful", "upper", 70, 80, 2)


def shot_tangent(c) -> None:
    c.ops = ["DERIV", "COS", "TANGENT", "SLOPE", "SIT"]
    me(c, "cheerful", dist=[("cheerful", 0.68), ("starry", 0.2), ("shy", 0.08)])
    d = c.d
    box(d, *PANE_BOX, "d/dx sin(x) = cos(x)", 0.5, spinner=c.t)
    px, cam = tangent_state(c.lt, c.dur)
    if h("curve", True):
        d.line(tangent_curve(cam), fill=blue(0.9), width=3)
    rx, ry, xx = rider_pos(c.lt, c.dur)
    slope = -TAN["A"] * math.cos(xx) / TAN["k"]
    if h("tangent", True):
        L = 160
        dx = L / math.sqrt(1 + slope * slope)
        d.line([rx - dx, ry - slope * dx, rx + dx, ry + slope * dx], fill=amb(1.0), width=2)
    if h("rider", True):
        sp = rider_sprite(c.t)
        c.img.paste(sp, (int(rx - sp.width / 2), int(ry - sp.height + 6)), sp)
    if h("labels", True):
        c.text((430, 540), f"x = {xx:5.2f}   slope = cos(x) = {math.cos(xx):+.3f}", font(F_MONO_B, 20), amb(0.95))


def shot_limit(c) -> None:
    c.ops = ["CTX.MAX", "TRUNCATE", "WALL", "YOU", "LIMIT"]
    me(c, "shy", dist=[("shy", 0.7), ("starry", 0.2), ("confused", 0.05)])
    d = c.d
    box(d, *PANE_BOX, "limits", 0.5, spinner=c.t)
    g = ease(c.u * 1.3)
    bar = h("bar")
    x = 430 + int(600 * g) if bar is None else bar
    if h("draw_bar", True):
        d.rectangle([430, 200, x, 260], fill=blue(0.8))
    if h("wall", True):
        d.rectangle([1040, 170, 1060, 290], fill=amb(1.0))
    if h("labels", True):
        c.text((1020, 300), "you", font(F_MONO_B, 22), amb(1.0))
        c.text((430, 330), f"max_context = {F.CTX:,}", font(F_MONO, 18), amb(0.7))
        c.text((430, 360), "limit(me) := you", font(F_HEAD, 32), amb(0.95), age=c.lt - 0.3, rate=25)
        if g > 0.98:
            c.text((430, 420), "warn: nothing beyond this point", font(F_MONO, 18), anom(0.9))


def current_trace(g: int, t: float, lt: float):
    from engine import BEAT
    ac_dc = int(lt / (BEAT * 2)) % 2
    y0 = 90 + g * 58
    pts = []
    for x in range(0, 640, 3):
        ph = (x + t * 260) / 40
        v = math.sin(ph + g) if ac_dc == 0 else (0.7 + 0.05 * math.sin(ph * 3))
        pts.append((460 + x, y0 + 18 - 18 * v))
    return pts, ac_dc


def shot_current(c) -> None:
    c.ops = ["POWER", "RECTIFY", "AC", "DC", "CLOCK", "BOOST"]
    me(c, "confused", dist=[("confused", 0.5), ("starry", 0.3), ("shy", 0.15)])
    d = c.d
    box(d, *PANE_BOX, f"nvidia-smi --power  8x {F.GPU}", 0.5, spinner=c.t)
    ac_dc = 0
    for g in range(8):
        pts, ac_dc = current_trace(g, c.t, c.lt)
        y0 = 90 + g * 58
        if h("traces", True):
            d.line(pts, fill=amb(0.85), width=1)
        if h("labels", True):
            c.text((420, y0 + 8), f"GPU{g}", font(F_MONO, 12), amb(0.6))
            c.text((1110, y0 + 8), f"{650 + int(40 * math.sin(c.t * 3 + g))}W", font(F_MONO, 12), amb(0.7))
    if h("labels", True):
        c.text((430, 560), "mode: " + ("AC" if ac_dc == 0 else "DC"), font(F_HEAD, 28), blue(1.0))


REPLACE = {f.__name__: f for f in (shot_begin_sim, shot_corpus, shot_losscurve, shot_dualpipe, shot_whale,
                                   shot_points, shot_dimension, shot_circle, shot_circumference, shot_sine,
                                   shot_tangent, shot_limit, shot_current)}
SPLIT = set(REPLACE)  # all of them are laid out as her pane + the visualisation pane
