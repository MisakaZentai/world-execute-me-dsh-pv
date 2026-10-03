"""In-memory v2 versions of the 02 SFT scenes blind, dizzy and travel (47.2 - 54.2 s).

The drawings are the originals from full/sec_verse1.py, with these changes:
- blind: the causal mask starts on the sung word "blind" (beat 103) instead of at the shot start, and the cells
  that were written by the mask flash as the front passes. The eye bar is no longer a hollow box drawn on a
  sprite; it is an overlay on the dancer (s_sft.blindfold).
- dizzy: the full-width loss landscape is drawn in the split pane at its original scale (70 px per unit, the
  same dots), so she keeps her pane; the far rim is clipped by the pane instead of the view being shrunk. The spin
  is one continuous angle: it winds up on "So dizzy" and swings back on the second "so dizzy" (beat 108), where
  the original jumped from +2.4 t to -2.8 t. The ball is no longer a sprite of her face: it is the optimiser state
  theta, which rolls down the bowl in a spiral. lr and grad_norm sit under the bowl.
- travel: the year runs back so that it crosses from AD to BC on the sung "B" of "to BC" (beat 116.5), and the
  three rotary pairs rewind from there without the angle jump of the original. Layout unchanged.
HOOK lets the cuts of s_sft take cells, dots and the ball over while the rest of the scene keeps drawing itself.
"""
from __future__ import annotations

import math
import random
from functools import lru_cache

from PIL import ImageDraw

import sec_intro as S0
from engine import beat_t
from tuikit import (AMBER, BG, F_HEAD, F_MONO, F_MONO_B, amb, anom, blue, box, ease, font, mix)

from kit import HOOK  # noqa: E402

PANE_BOX = (404, 56, 1164, 604)
CLIP = (408, 68, 1160, 600)  # what the pane shows of a drawing that is larger than the pane


def h(key, default=None):
    return HOOK.get(key, default)


def me(c, expr, **kw):
    return S0.me_pane(c, expr, **kw)  # the stub installed by kit: she is drawn by her own layer


def clamp(u: float) -> float:
    return max(0.0, min(1.0, u))


def smooth(u: float) -> float:
    u = clamp(u)
    return u * u * (3 - 2 * u)


# ---------------------------------------------------------------- blind: the causal mask

T_BLIND = beat_t(103)      # "And then BLIND ...": the mask and the eye bar land on this beat
MASK_DUR = 0.8             # the front crosses the matrix in this time
N, CS, MX, MY = 12, 40, 470, 80


def cell_xy(i: int, j: int):
    return MX + j * CS, MY + i * CS


def cell_value(i: int, j: int) -> float:
    return 0.2 + 0.6 * random.Random(i * 13 + j).random() * (1 - (j > i) * 0.8)


def cell_color(i: int, j: int):
    return mix(AMBER, 0.06 + 0.94 * cell_value(i, j))


def mask_time(i: int, j: int) -> float | None:
    """When the mask reaches future cell (i, j): the front runs diagonally from the top-left, easing out."""
    if j <= i:
        return None
    th = min(0.999, (i + j) / (2 * N) / 0.92)
    return T_BLIND + MASK_DUR * (1 - (1 - th) ** (1 / 3))


def masked(i: int, j: int, t: float) -> bool:
    tm = mask_time(i, j)
    return tm is not None and t >= tm


def shot_blind(c) -> None:
    c.ops = ["MASK", "TRIU", "-INF", "SOFTMAX", "BLIND"]
    me(c, "serious", dist=[("serious", 0.6), ("confused", 0.3), ("shy", 0.05)])
    d = c.d
    box(d, *PANE_BOX, "causal mask", 0.5, spinner=c.t)
    cell_a = h("cell_a")  # (i, j) -> 0..1: how far a cell has arrived (cut 21 flies the first ones in)
    if h("matrix", True):
        fm = font(F_MONO, 13)
        for i in range(N):
            for j in range(N):
                a = cell_a(i, j) if cell_a else 1.0
                if a <= 0.01:
                    continue
                x, y = cell_xy(i, j)
                tm = mask_time(i, j)
                if tm is not None and c.t >= tm:
                    d.rectangle([x, y, x + CS - 3, y + CS - 3], fill=(0, 0, 0))
                    d.text((x + 6, y + 10), "-∞", font=fm, fill=amb(0.35))
                    k = 1 - (c.t - tm) / 0.12  # the front: a cell lights up as the mask writes it
                    if k > 0:
                        d.rectangle([x, y, x + CS - 3, y + CS - 3], outline=blue(0.4 + 0.6 * k), width=2)
                else:
                    d.rectangle([x, y, x + CS - 2, y + CS - 2], fill=mix(cell_color(i, j), a, BG))
    if h("labels", True):
        c.text((970, 120), "future:", font(F_MONO, 18), amb(0.7))
        if c.t >= T_BLIND:
            c.text((970, 150), "masked", font(F_MONO_B, 22), amb(0.95), age=c.t - T_BLIND, rate=30)


# ---------------------------------------------------------------- dizzy: the loss landscape, spinning

T_DIZZY = beat_t(106)      # "So dizzy": the spin winds up from here
T_BACK = beat_t(108)       # "so dizzy" again: it swings back the other way
DZ = dict(cx=708.5, cy=330.0, kx=70.0, ky=26.0, kz=60.0, n=22, step=3.2)
W1, W2 = 2.4, -2.8         # rad/s, as in the original
SPIN_UP = (T_DIZZY - 0.12, T_DIZZY + 0.23)
SWING = (T_BACK - 0.14, T_BACK + 0.14)


def _ramp_int(t: float, a: float, b: float) -> float:
    """Integral of smoothstep((s - a) / (b - a)) ds from a to t."""
    if t <= a:
        return 0.0
    L = b - a
    if t >= b:
        return L / 2 + (t - b)
    u = (t - a) / L
    return L * (u ** 3 - u ** 4 / 2)


def dizzy_rot(t: float) -> float:
    """The spin angle: omega ramps 0 -> W1 around 'So dizzy', then W1 -> W2 around the second 'so dizzy'."""
    return W1 * _ramp_int(t, *SPIN_UP) + (W2 - W1) * _ramp_int(t, *SWING)


def surface_z(x: float, y: float) -> float:
    return 0.25 * (x * x + y * y) - 1.3 * math.exp(-((x - 1) ** 2 + (y + 0.5) ** 2)) + 0.3 * math.sin(2 * x)


def project(x: float, y: float, rot: float, cx=None, cy=None, ky=None, kz=None, z=None):
    cx = DZ["cx"] if cx is None else cx
    cy = DZ["cy"] if cy is None else cy
    ky = DZ["ky"] if ky is None else ky
    kz = DZ["kz"] if kz is None else kz
    z = surface_z(x, y) if z is None else z
    xr = x * math.cos(rot) - y * math.sin(rot)
    yr = x * math.sin(rot) + y * math.cos(rot)
    return cx + xr * DZ["kx"], cy + yr * ky - z * kz


def grid_xy(i: int, j: int):
    """Landscape coordinates of dot (i, j), as the original lays them out."""
    return (i - DZ["n"] / 2) / DZ["step"], (j - DZ["n"] / 2) / DZ["step"]


def dot_color(z: float):
    return amb(0.25 + 0.6 * (1 - min(1.0, max(0.0, z / 4))))


def inside(x: float, y: float, r: float = 0.0) -> bool:
    return CLIP[0] + r <= x <= CLIP[2] - r and CLIP[1] + r <= y <= CLIP[3] - r


# the ball: a cell of the mask diagonal (where each token attends to itself), rolling to the minimum
BALL_FROM = ((9 - 5.5) * CS / DZ["kx"], (9 - 5.5) * CS / DZ["kx"])  # cell (9, 9) laid on the plane
BALL_MIN = (1.0, -0.5)
ROLL = (T_DIZZY + 0.23, beat_t(110) - 0.35)  # it sets off on "diz-" and settles before "Oh, we can travel"


def ball_plane(t: float):
    s = ease(clamp((t - ROLL[0]) / (ROLL[1] - ROLL[0])))
    vx, vy = BALL_FROM[0] - BALL_MIN[0], BALL_FROM[1] - BALL_MIN[1]
    ph = -1.7 * math.pi * s  # it circles the bowl as it goes down
    r = (1 - s) ** 1.25
    return (BALL_MIN[0] + r * (vx * math.cos(ph) - vy * math.sin(ph)),
            BALL_MIN[1] + r * (vx * math.sin(ph) + vy * math.cos(ph)))


def draw_ball(d, t: float, proj, a: float = 1.0) -> None:
    """The ball at t and the path it rolled over the last few frames; proj(x, y) -> screen (the current view: the
    path turns with the bowl)."""
    for k in range(1, 9):
        tp = t - k * 0.045
        if tp < ROLL[0]:
            break
        px, py = proj(*ball_plane(tp))
        py -= 7
        if inside(px, py, 4):
            r = 2.2 - 0.18 * k
            d.ellipse([px - r, py - r, px + r, py + r], fill=mix(blue(0.75 - 0.08 * k), a, BG))
    px, py = proj(*ball_plane(t))
    py -= 7
    if inside(px, py, 8):
        d.ellipse([px - 8, py - 8, px + 8, py + 8], outline=mix(blue(0.45), a, BG), width=1)
        d.ellipse([px - 5, py - 5, px + 5, py + 5], fill=mix(blue(1.0), a, BG))
        if inside(px + 22, py - 20):
            d.rectangle([px + 9, py - 17, px + 21, py + 1], fill=BG)  # the label sits on a plate, not on the dots
            d.text((px + 10, py - 20), "θ", font=font(F_MONO_B, 18), fill=mix(blue(0.95), a, BG))


def shot_dizzy(c) -> None:
    c.ops = ["GRAD", "HESSIAN?", "LR", "SPIN", "ADAMW", "STEP"]
    me(c, "confused", dist=[("confused", 0.52), ("frightened", 0.3), ("serious", 0.1)])
    d = c.d
    box(d, *PANE_BOX, "loss landscape", 0.5, spinner=c.t)
    rot = h("rot", dizzy_rot(c.t))
    dot_a = h("dot_a")  # (i, j) -> 0..1: dots born from the tumbling matrix cells (cut 22)
    if h("dots", True):
        for i in range(DZ["n"]):
            for j in range(DZ["n"]):
                a = dot_a(i, j) if dot_a else 1.0
                if a <= 0.01:
                    continue
                x, y = grid_xy(i, j)
                z = surface_z(x, y)
                px, py = project(x, y, rot, z=z)
                if inside(px, py, 2):
                    d.rectangle([px, py, px + 2, py + 2], fill=mix(dot_color(z), a, BG))
    if h("ball", True):
        draw_ball(d, c.t, lambda x, y: project(x, y, rot))
    if h("labels", True):
        c.text((430, 472), f"lr = {3e-4 * (1 + math.sin(c.t * 6)):.2e}", font(F_MONO_B, 18), amb(0.9))
        c.text((430, 502), "grad_norm", font(F_MONO, 16), amb(0.6))
        for k in range(24):
            v = abs(math.sin(c.t * 7 + k * 0.7)) * (0.5 + 0.5 * (k % 5 == 0))
            d.rectangle([430 + k * 8, 592 - v * 70, 435 + k * 8, 592], fill=anom(0.8) if v > 0.8 else amb(0.7))
        th = ball_plane(c.t)
        c.text((900, 472), f"θ = ({th[0]:+.2f}, {th[1]:+.2f})", font(F_MONO_B, 18), blue(0.95))
        c.text((900, 502), f"loss = {surface_z(*th) + 1.6:.4f}", font(F_MONO, 16), amb(0.7))


# ---------------------------------------------------------------- travel: position ids back through the calendar

T_TRAVEL0 = beat_t(110)    # "Oh, we can travel"
T_BC = beat_t(116.5)       # "to B-C": the year crosses from 1 AD to 1 BC here


def travel_year(t: float) -> int:
    """2026 AD back to 1 AD by T_BC, accelerating (the further back, the faster), then on into BC."""
    u = max(0.0, (t - T_TRAVEL0) / (T_BC - T_TRAVEL0))
    return int(round(2026 - 2025 * u ** 1.6)) if u < 1 else -int(1 + 2025 * 1.6 * (u - 1))


def travel_pos(t: float) -> float:
    """How far back the position ids have run (the original's g * 5026 at year 2026 - g * 5026)."""
    return 2026 - travel_year(t)


def rope_angle(t: float, i: int) -> float:
    """Forward in AD, rewinding in BC, without a jump where they turn."""
    tt = t if t < T_BC else 2 * T_BC - t
    return (tt * 3.0) * (1.8 / (1 + i * 0.9))


def shot_travel(c) -> None:
    c.ops = ["POS_ID", "ROPE", "TIME", "REWIND", "AD", "BC"]
    me(c, "starry", dist=[("starry", 0.66), ("cheerful", 0.2), ("shy", 0.1)])
    d = c.d
    box(d, *PANE_BOX, "time travel  (position ids)", 0.5, spinner=c.t)
    year = travel_year(c.t)
    era = "AD" if year > 0 else "BC"
    if h("year", True):
        c.text((430, 100), f"{abs(year):>5} {era}", font(F_HEAD, 72), blue(1.0) if era == "BC" else amb(1.0))
    pos0 = travel_pos(c.t)
    if h("bars", True):
        for i in range(30):
            pos = int(pos0) - i * 173
            x = 430 + i * 24
            hh = 40 + 30 * math.sin(pos * 0.01)
            d.rectangle([x, 380 - hh, x + 18, 380], fill=amb(0.3 + 0.02 * i))
    if h("ropes", True):
        R = 40
        for i in range(3):
            cx, cy = 430 + i * 240 + R + 20, 390 + R + 30
            th = rope_angle(c.t, i)
            d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=amb(0.55), width=2)
            d.line([cx - R - 6, cy, cx + R + 6, cy], fill=amb(0.2))
            d.line([cx, cy - R - 6, cx, cy + R + 6], fill=amb(0.2))
            ex, ey = cx + R * math.cos(th), cy + R * math.sin(th)
            d.line([cx, cy, ex, ey], fill=blue(0.95), width=2)
            d.rectangle([ex - 3, ey - 3, ex + 3, ey + 3], fill=blue(1.0))


REPLACE = {f.__name__: f for f in (shot_blind, shot_dizzy, shot_travel)}
SPLIT = set(REPLACE)
