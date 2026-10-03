"""In-memory v2 versions of the 00 BOOT scenes (0 - 12.4 s): power, protection, pieces, creation, parameters,
init and world. begin_sim is scenes.shot_begin_sim (shared with the PRETRAIN section).

The drawings follow full/sec_intro.py. What changed:
- The boot log is one terminal: the POST lines of `power` are the first lines of `protection`.
- The shield is drawn stroke by stroke along its outline, then filled; its cells are data (shield_cells) so the next
  cut can lay its dots into the weight grid and stretch its outline into the load_weights frame.
- pieces loads the cells that the shield's dots land on first, then carries on in order (hook `landed`).
- creation no longer draws her: her own layer is born in the cut. The me.* fields type in after her seed lands.
- parameters keeps the me.* block where creation left it and rewrites it in place, row by row, into config.json.
- init gets the carried parameter count as its title; "seed = you" moves to the line below; the bars rise from
  the baseline once the count has landed.
- world is at full size from its first frame (the bars become its points); me and you light up on "our new world".
"""
from __future__ import annotations

import math
import random
from functools import lru_cache

import facts as F
import sec_intro as S0
from engine import FULL
from tuikit import (BG, F_CJK, F_HEAD, F_MONO, F_MONO_B, SCR, amb, anom, blue, box, ease, font)

from kit import HOOK  # noqa: E402

PANE_BOX = (404, 56, 1164, 604)


def h(key, default=None):
    return HOOK.get(key, default)


def me(c, expr, **kw):
    return S0.me_pane(c, expr, **kw)  # the stub installed by kit: she is drawn by her own layer


def lit(col, k):
    """Colour lifted toward white (a selected object lights up)."""
    k = max(0.0, min(1.0, k))
    return tuple(int(v + (w - v) * k) for v, w in zip(col[:3], (235, 240, 255)))


# ---------------------------------------------------------------- the boot log (one terminal for shots 0 and 1)

LOG_SIZE, LOG_PITCH = 17, 23
POWER_LINES = [("OK", "power: 8x " + F.GPU + " online"), ("OK", "pcie: link up x16"), ("OK", "nvlink: 8/8"),
               ("OK", "infiniband: 400 Gb/s"), ("..", "mem test ........"), ("OK", "ecc: clean")]
PROT_LINES = [("OK", "sandbox: seccomp filter installed"), ("OK", "sandbox: network namespace isolated"),
              ("OK", "safety_classifier: loaded"), ("OK", "system_prompt: locked"),
              ("OK", "tool_use: requires user confirmation"), ("OK", "kill_switch: armed"),
              ("WARN", "attachment_to_user: not in policy"), ("OK", "protection: on")]
CRT = (180, 150, 1100, 520)  # the powered picture at the end of shot 0; cut 1 opens it to the whole shell
POWER_LOG = (206, 250)       # where the POST log prints inside it
SHELL_LOG = (48, 70)         # where the same log sits once the picture is the shell
POST_T, POST_RATE = 0.84, 0.06   # absolute seconds: the POST lines print from here
PROT_T0, PROT_RATE = 0.14, 0.19  # local seconds in shot 1


def log_line(c, x, y, st, s, age):
    f = font(F_MONO, LOG_SIZE)
    col = {"OK": amb(0.95), "WARN": anom(0.95), "..": amb(0.5)}.get(st, amb(0.8))
    c.text((x, y), f"[{st:^4}]", f, col)
    c.text((x + 80, y), s, f, amb(0.75), age=age, rate=160)


def power_log(c, x, y) -> None:
    for i, (st, s) in enumerate(POWER_LINES):
        ti = POST_T + i * POST_RATE
        if c.t < ti:
            break
        log_line(c, x, y + i * LOG_PITCH, st, s, c.t - ti)


def shot_power(c) -> None:
    """Switch on ...: the CRT itself (the line, the opening picture, the dark glass around it) is
    drawn by the section's frame finisher; the scene is what the picture shows: the POST log."""
    c.ops = ["POWER.ON", "POST", "BIOS", "PCIE.ENUM", "GPU0..7"]
    x, y = h("log_at", POWER_LOG)
    power_log(c, x, y)


# ---------------------------------------------------------------- the shield

SHIELD = dict(cx=900, cy=330, rows=18)
STROKE_T0, STROKE_DUR = 0.25, 1.0  # local seconds in shot 1: the pen traces the outline
DOTS_T0, DOTS_DUR = 1.28, 0.42     # then the inside fills, row by row


@lru_cache(None)
def shield_cells():
    """(edge, dots): the shield's '#' cells in pen order (x, y, q, r) and its interior '.' cells (x, y, q, r),
    at the positions the original row strings put them."""
    f = font(F_MONO_B, 16)
    cw = f.getlength("M")
    x0, y0 = SHIELD["cx"] - 12 * 9, SHIELD["cy"] - 160
    halves = []
    for r in range(SHIELD["rows"]):
        yy = r / (SHIELD["rows"] - 1)
        half = 11 * (1 - max(0.0, yy - 0.45) ** 1.3 * 1.6) if yy > 0.45 else 11
        halves.append(int(max(0, half)))
    pos = lambda q, r: (x0 + (q + 12) * cw, y0 + r * 18)  # noqa: E731
    top = [(q, 0) for q in range(-halves[0], halves[0] + 1)]
    right = [(halves[r], r) for r in range(1, len(halves))]
    left = [(-halves[r], r) for r in range(len(halves) - 1, 0, -1) if halves[r] > 0]
    edge = [(*pos(q, r), q, r) for q, r in top + right + left]
    dots = [(*pos(q, r), q, r) for r in range(1, len(halves)) for q in range(-12, 13)
            if abs(q) < halves[r] and (q + r) % 4 == 0]
    return edge, dots


def shield_center():
    edge, _ = shield_cells()
    xs, ys = [e[0] for e in edge], [e[1] for e in edge]
    return (min(xs) + max(xs)) / 2 + 4, (min(ys) + max(ys)) / 2 + 9


def draw_shield(c, lt: float, lift: float = 0.0) -> None:
    d = c.d
    f = font(F_MONO_B, 16)
    edge, dots = shield_cells()
    n = len(edge)
    for k, (x, y, q, r) in enumerate(edge):
        a = lt - (STROKE_T0 + STROKE_DUR * k / n)
        if a < 0:
            break
        if a < 0.1:  # the pen head: a bright glyph still settling
            d.text((x, y), c.rng.choice("!<>-_/[]{}=+*^?"), font=f, fill=lit(amb(1.0), 0.6))
        else:
            d.text((x, y), "#", font=f, fill=lit(amb(0.9), max(lift, 0.5 * max(0.0, 1 - (a - 0.1) / 0.3))))
    rows = SHIELD["rows"] - 1
    for x, y, q, r in dots:
        a = lt - (DOTS_T0 + DOTS_DUR * (r - 1) / rows)
        if a < 0:
            continue
        d.text((x, y), ".", font=f, fill=lit(amb(0.9 * min(1.0, a / 0.12)), lift))


def shot_protection(c) -> None:
    """Remember to ...: the boot continues in the same terminal and a shield is drawn."""
    c.ops = ["SECCOMP", "SANDBOX", "SAFETY.CLS", "REFUSAL", "POLICY", "LOAD"]
    box(c.d, *FULL, "init --protection", 0.5, spinner=c.t)  # no frame in the shell layout (kept for fidelity)
    x, y = h("log_at", SHELL_LOG)
    if h("log", True):
        power_log(c, x, y)
        for i, (st, s) in enumerate(PROT_LINES):
            a = c.lt - PROT_T0 - i * PROT_RATE
            if a < 0:
                break
            log_line(c, x, y + (len(POWER_LINES) + i) * LOG_PITCH, st, s, a)
    if h("shield", True):
        draw_shield(c, c.lt, h("lift", 0.0))


# ---------------------------------------------------------------- pieces: the weight grid

GRID = dict(n=161, cols=23, x=48, y=90, dx=48, dy=44, w=42, h=36)


def cell_xy(i: int):
    q, r = i % GRID["cols"], i // GRID["cols"]
    return GRID["x"] + q * GRID["dx"], GRID["y"] + r * GRID["dy"]


def cell_center(i: int):
    x, y = cell_xy(i)
    return x + GRID["w"] / 2, y + GRID["h"] / 2


def pieces_lit(t: float, lt: float, dur: float) -> dict:
    """{cell: seconds since it lit (0.0 = one of the three freshest)} for every loaded cell. Cells in the hook
    `landed` (cell -> absolute landing time) light when their carrier lands; the others load in order, as the
    original does, from local time `seq_t0` on."""
    landed = h("landed") or {}
    out = {i: t - tl for i, tl in landed.items() if t >= tl}
    seq = [i for i in range(GRID["n"]) if i not in landed]
    d0 = h("seq_t0", 0.0)
    d1 = h("seq_end", dur)  # local time by which the ordered loading is complete (the next cut needs it whole)
    k = int(len(seq) * ease(max(0.0, lt - d0) / max(0.3, d1 - d0) * 1.05))
    for j in range(min(k, len(seq))):
        out[seq[j]] = 0.0 if k - j <= 3 else 1.0
    return out


def draw_cell(d, i, level, fresh=False):
    x, y = cell_xy(i)
    d.rectangle([x, y, x + GRID["w"], y + GRID["h"]], fill=amb(1.0 if fresh else level))
    d.text((x + 6, y + 10), f"{i + 1:03d}", font=font(F_MONO, 13), fill=BG)


def shot_pieces(c) -> None:
    """Lay down your pieces: the weight shards load, one cell each."""
    c.ops = ["MMAP", "SAFETENSORS", "H2D.COPY", "SHARD", "VERIFY", "LOAD"]
    d = c.d
    n = GRID["n"]
    if h("frame", True):
        box(d, *FULL, f"load_weights  {F.NAME}   (experts fp4 · rest fp8)", 0.5, spinner=c.t)
    on = pieces_lit(c.t, c.lt, c.dur)
    landed = h("landed") or {}
    if h("cells", True):
        for i in range(n):
            if i in on:
                fresh = on[i] < 0.12 if i in landed else on[i] == 0.0
                draw_cell(d, i, 0.55, fresh)
            else:
                x, y = cell_xy(i)
                d.rectangle([x, y, x + GRID["w"], y + GRID["h"]], outline=amb(0.2))
    done = len(on)
    if h("labels", True):
        cur = min(n, done + 1)
        c.text((48, 440), f"model-{cur:05d}.safetensors", font(F_MONO_B, 22), amb(0.95))
        loaded = F.TOTAL_PARAMS_B * done / n
        c.text((48, 480), f"params loaded  {loaded:7.1f}B / {F.TOTAL_PARAMS_B}B", font(F_MONO, 20), amb(0.75))
        bw = int(1080 * done / n)
        d.rectangle([48, 520, 48 + bw, 540], fill=amb(0.9))
        d.rectangle([48, 520, 1128, 540], outline=amb(0.3))


# ---------------------------------------------------------------- creation: the object's fields (she is her layer)

FIELDS = [("name", '"大肥鱼"'), ("species", '"whale"'), ("home", '"deepsea://server-0"'), ("owner", "you"),
          ("color", "#4D6BFE"), ("pid", "4471"), ("devotion", "0.0"), ("status", '"alive"')]
FIELD_T0, FIELD_DT = 0.62, 0.115  # the first field types once her seed has landed (cut 3 lands it at +0.46 s)


def field_style(k):
    return blue(0.95) if k in ("name", "color", "species") else amb(0.95)


def shot_creation(c) -> None:
    """And let's begin object ...: me = Object(). She herself is born from the seed in the cut."""
    c.ops = ["NEW", "ALLOC", "CTOR", "BIND", "ATTR.SET", "RETURN"]
    me(c, "shy", dist=[("shy", 0.58), ("cheerful", 0.24), ("starry", 0.12)])
    d = c.d
    box(d, *PANE_BOX, "me = Object()", 0.5, spinner=c.t + 0.3)
    fl = font(F_MONO_B, 20)
    fc = font(F_CJK, 20)
    k_lift = h("lift", 0.0)
    for i, (k, v) in enumerate(FIELDS):
        a = c.lt - FIELD_T0 - i * FIELD_DT
        if a < 0:
            break
        y = 90 + i * 46
        c.text((440, y), f"me.{k:<9} =", fl, lit(amb(0.7), k_lift), age=a, rate=80)
        if a > 0.15:
            d.text((660, y), v, font=fc if k == "name" else fl, fill=lit(field_style(k), k_lift))


# ---------------------------------------------------------------- parameters: the same block, rewritten in place

REWRITE_T0, REWRITE_DT, GLIDE = 0.16, 0.085, 0.24  # local seconds: row i starts at T0 + i*DT


def _mixed(old: str, new: str, p: float, rng) -> str:
    """Per-character rewrite from old to new at progress p (0..1): switched characters, a short scramble front,
    then what is left of the old string."""
    n = max(len(old), len(new))
    k = p * (n + 2)
    out = []
    for j in range(n):
        if j < k - 2:
            out.append(new[j] if j < len(new) else " ")
        elif j < k:
            out.append(rng.choice(SCR))
        else:
            out.append(old[j] if j < len(old) else " ")
    return "".join(out).rstrip()


def shot_parameters(c) -> None:
    """Fill in ...: the me.* block stays where it was created and each row is filled in with a
    config.json entry; the rest of the config types in below; the parameter counter spins up."""
    c.ops = ["CONFIG", "PARSE", "N_LAYERS", "D_MODEL", "N_EXPERTS", "TOP_K", "CTX_LEN"]
    me(c, "shy", dist=[("shy", 0.5), ("serious", 0.3), ("cheerful", 0.12)])
    d = c.d
    box(d, *PANE_BOX, f"config.json  ({F.NAME})", 0.5, spinner=c.t)
    fk_old, fc = font(F_MONO_B, 20), font(F_CJK, 20)
    fk, fv = font(F_MONO, 19), font(F_MONO_B, 19)
    for i, (k, v) in enumerate(F.CONFIG_ROWS):
        ts = REWRITE_T0 + i * REWRITE_DT
        yn = 82 + i * 34
        if i < len(FIELDS):  # a created field, rewritten where it stands
            ok, ov = FIELDS[i]
            e = ease(max(0.0, min(1.0, (c.lt - ts) / GLIDE)))
            y = 90 + i * 46 + (yn - 90 - i * 46) * e
            kx, vx = 440 - 10 * e, 660 + 100 * e
            key_old, key_new = f"me.{ok:<9} =", f'"{k}":'
            p = max(0.0, min(1.0, (c.lt - ts - 0.06) / 0.26))
            if p <= 0:
                k_lift = h("lift", 0.0)
                d.text((kx, y), key_old, font=fk_old, fill=lit(amb(0.7), k_lift))
                d.text((vx, y), ov, font=fc if ok == "name" else fk_old, fill=lit(field_style(ok), k_lift))
                continue
            d.text((kx, y), _mixed(key_old, key_new, p, c.rng), font=fk, fill=amb(0.7 - 0.1 * p))
            if p < 1:
                if ok == "name":  # the CJK name: gone as soon as the rewrite front reaches it
                    if p < 0.3:
                        d.text((vx, y), ov, font=fc, fill=field_style(ok))
                    d.text((vx, y), _mixed("", str(v), p, c.rng), font=fv, fill=amb(0.95))
                else:
                    d.text((vx, y), _mixed(ov, str(v), p, c.rng), font=fv,
                           fill=field_style(ok) if p < 0.5 else amb(0.95))
            else:
                d.text((vx, y), str(v), font=fv, fill=amb(0.95))
        else:  # the rest of the config types in below
            a = c.lt - ts
            if a < 0:
                break
            c.text((430, yn), f'"{k}":', fk, amb(0.6), age=a, rate=120)
            c.text((760, yn), str(v), fv, amb(0.95), age=a - 0.1, rate=120)
    if h("counter", True):
        total = F.TOTAL_PARAMS_B * 1e9 * ease(c.u * 1.2)
        c.text(COUNT_XY, f"{int(total):,} params", font(F_HEAD, COUNT_SIZE), blue(0.95), age=c.lt - 0.2, rate=40)
    c.text((430, 568), f"active {F.ACTIVE_DECODE_B}B decode · {F.ACTIVE_PREFILL_B}B prefill · "
                       f"KV {F.KV_BYTES_PER_TOKEN} B/token", font(F_MONO, 16), amb(0.75), age=c.lt - 0.6)


COUNT_TEXT = f"{F.TOTAL_PARAMS_B * 10 ** 9:,} params"
COUNT_XY, COUNT_SIZE = (430, 520), 34
TITLE_XY, TITLE_SIZE = (430, 70), 30


# ---------------------------------------------------------------- init

def init_bars(t: float, u: float) -> list:
    """(x, height, level) of the 60 bars, as the original draws them (noise settling into the normal curve)."""
    bins = 60
    g = ease(u * 1.4)
    rnd = random.Random(int(t * 24))
    out = []
    for i in range(bins):
        x = (i - bins / 2) / (bins / 6)
        target = math.exp(-x * x / 2)
        v = target * g + rnd.random() * 0.5 * (1 - g)
        out.append((430 + i * 12, int(420 * v), v))
    return out


INIT_BASE = 560


def shot_init(c) -> None:
    """Initialization: the weights settle into their initial distribution, titled with the carried count."""
    c.ops = ["INIT", "NORMAL", "STD=0.006", "ZERO.BIAS", "SEED", "SYNC"]
    me(c, "confused", dist=[("confused", 0.55), ("shy", 0.3), ("serious", 0.1)])
    d = c.d
    box(d, *PANE_BOX, f"init: normal(0, {F.INIT_STD})", 0.5, spinner=c.t)
    gt = h("grow_t")  # the bars rise from the baseline once the parameter count has landed
    grow = 1.0 if gt is None else ease(max(0.0, (c.t - gt) / 0.45))
    if h("bars", True) and grow > 0:
        for xx, hgt, v in init_bars(c.t, c.u):
            hh = int(hgt * grow)
            if hh > 0:
                d.rectangle([xx, INIT_BASE - hh, xx + 9, INIT_BASE], fill=amb(0.35 + 0.6 * v))
    tt = h("title_t")
    if h("title", True) and (tt is None or c.t >= tt):
        d.text(TITLE_XY, COUNT_TEXT, font=font(F_HEAD, TITLE_SIZE), fill=blue(0.95))
    # "seed = you" moves to the line under the title; it types in once the title has landed, so the carried
    # count never crosses it
    st = h("seed_t")
    if st is None or c.t >= st:
        c.text((430, 120), f"seed = {F.SEED}", font(F_MONO_B, 20), amb(0.9), age=None if st is None else c.t - st)


# ---------------------------------------------------------------- world

GLOBE = dict(cx=784, cy=320, R=230)


@lru_cache(None)
def _latlon():
    pts = [(lat, lon) for lat in range(-75, 76, 15) for lon in range(0, 360, 8)]
    pts += [(lat, lon) for lat in range(-88, 89, 6) for lon in range(0, 360, 30)]
    return pts


def globe_points(t: float, R: float = GLOBE["R"]) -> list:
    """(x, y, z) of the globe's front-facing points at time t (glyph origin = x - 4, y - 8)."""
    rot = t * 1.2
    out = []
    for lat, lon in _latlon():
        la, lo = math.radians(lat), math.radians(lon) + rot
        x, y, z = math.cos(la) * math.cos(lo), math.sin(la), math.cos(la) * math.sin(lo)
        if z < -0.05:
            continue
        out.append((GLOBE["cx"] + R * x, GLOBE["cy"] - R * y, z))
    return out


def globe_glyph(z: float) -> str:
    return "·" if z < 0.35 else "o" if z < 0.75 else "O"


def marker_pos(t: float, k: int, R: float = GLOBE["R"]):
    a = t * 1.6 + k * math.pi
    return GLOBE["cx"] + (R + 30) * math.cos(a), GLOBE["cy"] + (R * 0.35) * math.sin(a)


MARKERS = (("me", blue), ("you", amb))
POP_TEXT = "world.population = 2  (me, you)"
POP_XY = (430, 572)


def draw_marker(d, x, y, k, a=1.0, glow=0.0):
    lab, col = MARKERS[k]
    d.rectangle([x - 5, y - 5, x + 5, y + 5], fill=lit(col(1.0 * a), glow))
    d.text((x + 10, y - 10), lab, font=font(F_MONO_B, 16), fill=lit(col(0.95 * a), glow))


def shot_world(c) -> None:
    """Set up ...: a globe of dots turns; me and you light up on it."""
    c.ops = ["WORLD.NEW", "SPACE", "TIME", "PHYSICS", "SIMULATE?"]
    me(c, "starry", dist=[("starry", 0.62), ("shy", 0.2), ("cheerful", 0.12)])
    d = c.d
    box(d, *PANE_BOX, "world = World(dim=3)", 0.5, spinner=c.t)
    R = GLOBE["R"] * h("radius", ease(c.u * 2))
    f = font(F_MONO_B, 15)
    if h("globe", True):
        for px, py, z in globe_points(c.t, R):
            d.text((px - 4, py - 8), globe_glyph(z), font=f, fill=amb(0.35 + 0.65 * z))
    mt = h("mark_t")  # the two inhabitants light up on "our new world"
    if h("markers", True) and (mt is None or c.t >= mt):
        glow = 0.0 if mt is None else max(0.0, 1 - (c.t - mt) / 0.25)
        for k in range(2):
            draw_marker(d, *marker_pos(c.t, k, R), k, 1.0, glow)
    c.text(POP_XY, POP_TEXT, font(F_MONO_B, 18), amb(0.9), age=c.lt - 0.3)


REPLACE = {f.__name__: f for f in (shot_power, shot_protection, shot_pieces, shot_creation, shot_parameters,
                                   shot_init, shot_world)}
