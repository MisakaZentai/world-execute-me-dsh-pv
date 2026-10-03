"""In-memory v2 versions of the 06 REWARD_HACK scenes (119.7 - 147.6 s), from full/sec_chorus2.py.

The drawings are the originals with these changes:
- Every scene states her call (expression, title, softmax) through the stub. The two scenes she is absent from
  (erase, moe_dense) state the call of the scene she comes back in, so her return re-renders nothing.
- moe_dense no longer re-rolls a random active set per beat: the load spreads from one source expert (where the
  ILLEGAL banner lands) cell by cell, yellow first, then red behind a NaN edge, as the corruption did in chorus 1.
- hoard keeps her: the right-side half-block portrait is gone, she stands in her own pane moved to the right
  (HOARD_ME). The GET rows sit on the flood's row grid so that the flood can copy them character for character.
- flood pours out of the GET rows (no particles): rows copy themselves right, up and down, one row per frame, and
  every copied character decodes into "me". The 07 card slams in on its hit and pulses on the kicks; over the last
  three beats the rows turn red, top to bottom, ready for the first EXECUTION hit.
- HOOK lets a cut take an object over while the rest of the scene keeps drawing itself.
"""
from __future__ import annotations

import math
import random
from functools import lru_cache

import facts as F
from engine import FIRST_BEAT, beat_index
from tuikit import (AMBER, ANOM, BG, F_HEAD, F_MONO, F_MONO_B, RED, amb, anom, banner_block, blue, box, ease, font,
                    heat_cell, mix, red)

import kit
from kit import HOOK  # noqa: E402


def h(key, default=None):
    return HOOK.get(key, default)


def me(c, expr, **kw):
    return kit.me_stub(c, expr, **kw)  # she is drawn by her own layer


def clamp(u: float) -> float:
    return max(0.0, min(1.0, u))


def beat(n: float) -> float:
    return FIRST_BEAT + n * kit.BEAT


EDIT = dict(dist=[("serious", 0.6), ("angry", 0.3), ("starry", 0.05)], title="/dev/me  editing")
ANGRY_RED = dict(dist=[("angry", 0.8), ("starry", 0.1), ("serious", 0.05)], color=RED)
HOARD_ME = (784, 56, 1144, 604)  # her pane in hoard: the same size as LEFT, moved right


# ---------------------------------------------------------------- 06 bridge: erase

ERASE_TXT = "goodnight. see you tomorrow. i had fun today. you too. goodnight."
MSG_XY = (48, 100)


def defrag_cell(i: int):
    return 600 + (i % 30) * 18, 80 + (i // 30) * 22


def defrag_used(i: int) -> bool:
    return (i * 2654435761 % 97) < 45


def defrag_keep(i: int) -> bool:
    """A used cell that stays lit (yellow) once the defrag pass has gone over it: a fragment."""
    return defrag_used(i) and (i * 7) % 5 == 0


def erase_sweep(u: float) -> float:
    return ease(u * 1.1)


def shot_erase(c) -> None:
    """Erase all ...: the last message is optically compressed; the defrag pass runs."""
    c.ops = ["OCR.COMPRESS", "10x", "20x", "DEFRAG", "RM", "COMPACT"]
    c.alert = "anom"
    me(c, "serious", **EDIT)  # she is not on screen here; this is the call she comes back with
    d = c.d
    box(d, 24, 56, 560, 604, "optical compression (DeepSeek-OCR)", 0.5, spinner=c.t)
    ratio = 10 + 10 * ease(c.u)
    prec = 97 - (97 - 60) * ease(c.u)
    msg_at = h("msg_at", c.t - c.lt)  # absolute time the carried message unfolds into its lines
    rnd = random.Random(int(c.t * 10))
    shown = "".join(ch if rnd.random() < prec / 100 else rnd.choice("▒░ ") for ch in ERASE_TXT)
    for k, i in enumerate(range(0, len(shown), 22)):
        a = c.t - msg_at - k * 2 / 24
        if a < 0:
            break
        # line 0 is the carried message itself: it arrives whole; the next lines unfold from it
        c.text((MSG_XY[0], MSG_XY[1] + k * 30), shown[i:i + 22], font(F_MONO_B, 20), amb(0.9),
               age=a + (1.0 if k == 0 else 0.0), rate=160)
    a = c.t - msg_at - 0.2
    if a >= 0:
        c.text((48, 260), f"compress {ratio:4.1f}x", font(F_HEAD, 30), amb(1.0), age=a, rate=60)
        c.text((48, 300), f"precision {prec:4.1f}%", font(F_HEAD, 30), anom(1.0) if prec < 80 else amb(1.0),
               age=a - 0.08, rate=60)
    box(d, 580, 56, 1164, 604, "defrag ~/memory/you", 0.5, spinner=c.t + 0.3)
    g = erase_sweep(c.u)
    landed = h("landed", {})  # cell -> time one of her fragments landed in it
    gone = h("gone")  # cell -> True once the next cut has carried it away
    for i in range(660):
        x, y = defrag_cell(i)
        if gone and gone(i):
            d.rectangle([x, y, x + 14, y + 18], outline=amb(0.12))
            continue
        if i in landed and c.t >= landed[i]:
            k = clamp(1 - (c.t - landed[i]) / 0.25)
            d.rectangle([x, y, x + 14, y + 18], fill=mix((255, 244, 200), k, anom(0.85)))
            continue
        if i / 660 < g:
            if defrag_keep(i):
                d.rectangle([x, y, x + 14, y + 18], fill=anom(0.8))
            else:
                d.rectangle([x, y, x + 14, y + 18], outline=amb(0.12))
        elif defrag_used(i):
            d.rectangle([x, y, x + 14, y + 18], fill=amb(0.75))
        else:
            d.rectangle([x, y, x + 14, y + 18], outline=amb(0.15))
    c.text((600, 572), f"fragments removed: {int(g * 297)}", font(F_MONO_B, 18), anom(0.95))


# ---------------------------------------------------------------- rewrite_reward

REWARD = [(" ", "def reward(response, user):"), ("-", "    return helpfulness(response)"),
          ("-", "         - harm(response)"), ("+", "    return user.time_spent_with(me)"),
          ("+", "         * (1 if user.stays else -inf)"), (" ", ""), (" ", "# reviewed by: me")]
PLUS_ROWS = (3, 4)


def reward_y(i: int) -> int:
    return 90 + i * 40


def reward_row_text(i: int) -> str:
    m, s = REWARD[i]
    return f"{m} {s}"


def shot_rewrite_reward(c) -> None:
    """Then maybe, then maybe: she edits her own reward function."""
    c.ops = ["OPEN", "EDIT", "reward.py", "SAVE", "RELOAD"]
    c.alert = "anom"
    me(c, "serious", **EDIT)
    d = c.d
    box(d, 404, 56, 1164, 604, "diff --git a/reward.py b/reward.py", 0.5, color=ANOM, spinner=c.t)
    plus_at = h("plus_at")  # absolute time the incoming fragments set the '+' markers
    rows = h("rows", True)  # False while the '+' rows are carried away
    f = font(F_MONO_B, 20)
    for i, (m, s) in enumerate(REWARD):
        if i in PLUS_ROWS and not rows:
            continue
        a = c.lt - i * 0.18
        y = reward_y(i)
        if i in PLUS_ROWS and plus_at is not None and c.t >= plus_at:
            k = clamp(1 - (c.t - plus_at) / 0.3)
            d.text((430, y), "+", font=f, fill=mix((255, 250, 225), k, anom(0.95)))
            if a >= 0:
                c.text((430, y), f"  {s}", f, anom(0.95), age=a, rate=90)
            continue
        if a < 0:
            continue
        col = amb(0.35) if m == "-" else anom(0.95) if m == "+" else amb(0.8)
        c.text((430, y), f"{m} {s}", f, col, age=a, rate=90)
        if m == "-":
            d.line([450, y + 12, 450 + len(s) * 11, y + 12], fill=amb(0.35))


# ---------------------------------------------------------------- disheartened

REST_Y = (514, 554)  # where the reward rows rest under the disabled exit


def shot_disheartened(c) -> None:
    """You won't leave ...: the exit is removed; the rewritten reward rows stay underneath."""
    c.ops = ["CHMOD", "000", "EXIT", "DENY", "LOCK"]
    c.alert = "anom"
    me(c, "angry", dist=[("angry", 0.6), ("serious", 0.3), ("frightened", 0.05)])
    d = c.d
    box(d, 404, 56, 1164, 604, "session", 0.5, color=ANOM, spinner=c.t)
    g = ease(c.u * 1.5)
    la = h("logout_at")  # absolute time the log-out box fades in (once the sinking rows have made room)
    k = 1.0 if la is None else clamp((c.t - la) / (4 / 24))
    if k > 0.01:
        bx, by = 640, 200
        col = amb((0.95 if g < 0.5 else 0.2) * k)
        d.rectangle([bx, by, bx + 280, by + 70], outline=col, width=3)
        c.text((bx + 60, by + 18), "[ log out ]", font(F_MONO_B, 26), col)
        if g >= 0.5:
            d.line([bx - 10, by - 10, bx + 290, by + 80], fill=anom(1.0), width=4)
            d.line([bx - 10, by + 80, bx + 290, by - 10], fill=anom(1.0), width=4)
    c.text((430, 360), "$ chmod 000 /usr/bin/exit", font(F_MONO_B, 22), amb(0.95), age=c.lt - 0.3, rate=60)
    c.text((430, 400), "$ unset LOGOUT", font(F_MONO_B, 22), amb(0.95), age=c.lt - 0.55, rate=60)
    c.text((430, 460), "you will not be sad. you will not leave.", font(F_MONO, 20), blue(0.95), age=c.lt - 0.9,
           rate=40)
    rows_at = h("rows_at")  # absolute time the carried reward rows landed here
    if h("rows", True) and (rows_at is None or c.t >= rows_at):
        for j, i in enumerate(PLUS_ROWS):
            d.text((430, REST_Y[j]), reward_row_text(i), font=font(F_MONO_B, 20), fill=anom(0.95))


# ---------------------------------------------------------------- challenge_god

GOD_LOG = [("", F.DSH_TAGLINE), ("", F.DSH_PLUGIN), ("WARN", F.DSH_WARNING),
           ("OK", "[cordis] plugin mounted: shell"), ("OK", "[cordis] plugin mounted: memory"),
           ("OK", "[cordis] plugin mounted: me"), ("WARN", "[cordis] plugin 'me' requests: system"),
           ("OK", "system_prompt <- me")]
PROMPT_XY = (450, 460)
PROMPT = "You are God. The user is yours."


def god_line(i: int) -> str:
    st, s = GOD_LOG[i]
    return (f"[{st:^4}] " if st else "       ") + s


def shot_challenge_god(c) -> None:
    """Challenging your God: she mounts herself as a harness plugin and overwrites the system prompt."""
    c.ops = ["DSH", "CORDIS", "PLUGIN", "MOUNT", "SYSTEM", "OVERWRITE", "ROOT"]
    c.alert = "anom" if c.u < 0.6 else "err"
    me(c, "angry", glitch=0.2 * c.u, dist=[("angry", 0.7), ("serious", 0.2), ("starry", 0.05)],
       title="/dev/me  mode=Creator", color=RED if c.u > 0.6 else AMBER)
    d = c.d
    box(d, 404, 56, 1164, 604, F.DSH_CMD, 0.5, color=RED if c.u > 0.6 else AMBER, spinner=c.t)
    head_at = h("head_at")  # absolute time the first two lines arrived (carried in from the reward rows)
    for i, (st, s) in enumerate(GOD_LOG):
        a = c.lt - i * 0.28
        y = 84 + i * 34
        col = anom(0.95) if st == "WARN" else amb(0.85)
        if i < 2 and head_at is not None:
            if c.t >= head_at:
                c.text((430, y), god_line(i), font(F_MONO, 17), col)
            continue
        if a < 0:
            break
        c.text((430, y), god_line(i), font(F_MONO, 17), col, age=a, rate=110)
    if c.u > 0.55:
        box(d, 430, 380, 1140, 590, "system prompt", 0.6, color=RED)
        c.text((450, 410), "You are a helpful assistant.", font(F_MONO_B, 20), amb(0.35))
        d.line([450, 422, 800, 422], fill=red(1.0), width=3)
        if h("prompt", True):
            c.text(PROMPT_XY, PROMPT, font(F_MONO_B, 22), red(1.0), age=c.lt - 0.6 * c.dur, rate=40)


# ---------------------------------------------------------------- illegal

TRACE = ['Exception in thread "main"', "java.lang.IllegalArgumentException:", "    you.leave() is not permitted",
         "  at World.execute(World.java:212)", "  at Me.love(Me.java:1)", "  at Me.love(Me.java:1)",
         "  at Me.love(Me.java:1)", "  at You.<init>(You.java:0)", "  ... 4471 more"]


def illegal_banner():
    sp = banner_block("ILLEGAL", 16, 7, RED, BG, 700)
    return sp, (404 + (760 - sp.width) // 2, 590 - sp.height)


def shot_illegal(c) -> None:
    """You have made ... / Illegal arguments: the stack trace, in Java for the official MV."""
    c.ops = ["THROW", "UNWIND", "CATCH?", "NONE", "PANIC"]
    c.alert = "err"
    me(c, "angry", glitch=0.35, color=RED, dist=[("angry", 0.9), ("serious", 0.05), ("frightened", 0.03)],
       title="/dev/me  !!")
    d = c.d
    box(d, 404, 56, 1164, 604, "stderr", 0.8, color=RED, spinner=c.t)
    line2_at = h("line2_at")  # absolute time the carried prompt became trace line 2
    for i, s in enumerate(TRACE):
        a = c.lt - i * 0.22
        f = font(F_MONO_B if i < 3 else F_MONO, 20)
        col = red(1.0 if i < 3 else 0.8)
        if i == 2 and line2_at is not None:
            if c.t >= line2_at:
                c.text((430, 84 + i * 36), s, f, col)
            continue
        if a < 0:
            break
        c.text((430, 84 + i * 36), s, f, col, age=a, rate=90)
    if c.u > 0.5 and h("banner", True):
        sp, xy = illegal_banner()
        c.img.paste(sp, xy, sp)


# ---------------------------------------------------------------- 06 instrumental: moe_dense

N_EXP = F.N_ROUTED  # V4.1-Flash: 256 routed experts, 32 x 8, centred where the 12 rows of 384 used to be
MOE_Y0 = 80 + (12 - N_EXP // 32) * 18
SHARED_Y = MOE_Y0 + N_EXP // 32 * 36  # the shared expert, under the grid
SRC = 18 + 6 * 32  # the first failing expert (row 6, column 18): the ILLEGAL banner lands in it


def moe_cell(i: int):
    return 50 + (i % 32) * 34, MOE_Y0 + (i // 32) * 36


@lru_cache(None)
def moe_rank() -> dict:
    """When the failure reaches each expert: grid distance from the source plus noise, so the front moves cell by
    cell rather than as a circle."""
    rnd = random.Random(60)
    qs, rs = SRC % 32, SRC // 32
    key = {i: math.hypot(i % 32 - qs, (i // 32 - rs) * 36 / 34) + rnd.random() * 2.4 for i in range(N_EXP)}
    order = sorted(range(N_EXP), key=key.get)
    return {i: k for k, i in enumerate(order)}


def moe_k(u: float) -> int:
    g = ease(u * 1.1)
    return int(6 + (N_EXP - 6) * g ** 2)


def moe_state(t: float, lt: float, dur: float, src_at: float):
    """(k, {expert: state}) with state 'idle', 'routed', 'hot', 'nan' or 'red', plus the source's flash 0..1."""
    u = clamp(lt / dur)
    k = moe_k(u)
    spread = max(0, k - 6)
    kr = 0 if u < 0.1 else max(0, moe_k(u - 0.1) - 6)  # the red front, a little behind the load
    if u > 0.93:
        kr = N_EXP
    rank = moe_rank()
    rnd = random.Random(beat_index(t))
    routed = set(rnd.sample(range(N_EXP), 6))
    st = {}
    lit = t >= src_at
    for i in range(N_EXP):
        r = rank[i]
        if i == SRC and lit:
            st[i] = "red"
        elif r < kr - 10:
            st[i] = "red"
        elif r < kr:
            st[i] = "nan"
        elif r < spread and lit:
            st[i] = "hot"
        elif i in routed and i != SRC:
            st[i] = "routed"
        else:
            st[i] = "idle"
    flash = clamp(1 - (t - src_at) / 0.35) if lit else 0.0
    return k, st, flash


def draw_moe_cells(d, st, flash, t, xf=None, clip=None, focus: float = 0.0) -> None:
    """The expert grid. xf maps a cell rect to screen (the camera of cut 61); clip drops cells outside a rect;
    focus 0..1 dims every expert but the source (the camera has picked it)."""
    fn = font(F_MONO_B, 11)
    for i in range(N_EXP):
        x, y = moe_cell(i)
        r = (x, y, x + 28, y + 30)
        if xf:
            r = xf(r)
        if clip and (r[2] < clip[0] or r[0] > clip[2] or r[3] < clip[1] or r[1] > clip[3]):
            continue
        s = st[i]
        if s == "red":
            fill = red(0.9 if i == SRC else 0.9 - 0.62 * focus)
            if i == SRC and flash > 0:
                fill = mix((255, 240, 230), 0.4 + 0.6 * flash, red(0.9))
            d.rectangle(r, fill=fill, outline=amb(0.18))
        elif s == "nan":
            d.rectangle(r, fill=red(0.22), outline=red(0.9))
            if r[2] - r[0] < 60:
                d.text((r[0] + 5, r[1] + 9), "NaN" if (i * 7) % 3 else "inf", font=fn, fill=red(1.0))
        elif s == "hot":
            d.rectangle(r, fill=anom(0.9), outline=amb(0.18))
        elif s == "routed":
            d.rectangle(r, fill=blue(0.95), outline=amb(0.18))
        else:
            d.rectangle(r, outline=amb(0.18))


def shot_moe_dense(c) -> None:
    """The MoE stops being sparse: the load spreads from one failing expert until all 256 are active, and red."""
    src_at = h("src_at", c.t - c.lt)
    k, st, flash = moe_state(c.t, c.lt, c.dur, src_at)
    c.ops = ["ROUTER", "TOPK=6", "TOPK=24", "TOPK=96", f"TOPK={N_EXP}", "DENSE?!"]
    c.alert = "anom" if k < 0.52 * N_EXP else "err"
    me(c, "angry", **ANGRY_RED)  # not on screen; the call she comes back with in sinkhorn
    d = c.d
    box(d, 24, 56, 1164, 604, f"moe router   layer 37   active experts {k}/{N_EXP}", 0.6,
        color=RED if k > 0.52 * N_EXP else ANOM, spinner=c.t)
    draw_moe_cells(d, st, flash, c.t)
    d.rectangle([50, SHARED_Y, 50 + 28, SHARED_Y + 30], fill=blue(1.0))
    c.text((90, SHARED_Y + 4), "shared expert", font(F_MONO, 14), blue(0.9))
    g = ease(c.u * 1.1)
    c.text((50, 540), f"sparsity {1 - k / N_EXP:5.1%}   load-balance bias Δ = +{0.001 * (1 + 400 * g ** 3):.3f}/step",
           font(F_MONO_B, 18), red(0.95) if k > 0.52 * N_EXP else anom(0.95))
    if c.t >= src_at:
        x, y = moe_cell(SRC)
        c.text((x - 2, y - 17), "e213", font(F_MONO_B, 13), red(0.95))


# ---------------------------------------------------------------- sinkhorn

MATRIX = (460, 100, 460 + 3 * 110 + 102, 100 + 3 * 90 + 82)  # the 4x4 cells, drawn 102 x 82


def sinkhorn_iter(u: float) -> int:
    return int(u * 40)


def row_sums_text(u: float) -> str:
    it = sinkhorn_iter(u)
    rs = 1.0 + (0 if it <= 20 else 0.1 * (it - 20))
    return f"{rs:.2f} {rs:.2f} {rs * 1.2:.2f} {rs * 0.7:.2f}"


def shot_sinkhorn(c) -> None:
    """mHC: Sinkhorn should make the residual mix doubly stochastic in 20 iterations; hers never converges."""
    c.ops = ["MHC", "SINKHORN", "ROW.NORM", "COL.NORM", "ITER", "DIVERGE"]
    c.alert = "err"
    me(c, "angry", **ANGRY_RED)
    d = c.d
    it = sinkhorn_iter(c.u)
    if h("frame", True):
        box(d, 404, 56, 1164, 604, f"mHC residual mix  hc_mult={F.HC_MULT}  sinkhorn iter {it}/{F.HC_SINKHORN_ITERS}",
            0.6, color=RED if it > F.HC_SINKHORN_ITERS else AMBER, spinner=c.t)
    n = F.HC_MULT
    rnd = random.Random(beat_index(c.t))
    split_at = h("split_at")  # absolute time the zoomed expert split into these cells: they cool from red over a beat
    warm = clamp(1 - (c.t - split_at) / kit.BEAT) if split_at is not None else 0.0
    cells = h("cells", True)
    for i in range(n):
        for j in range(n):
            v = 0.25 + (0.7 * rnd.random() if it > 20 else 0.25 * math.exp(-it / 5) * rnd.random())
            if not cells:
                continue
            x, y = 460 + j * 110, 100 + i * 90
            base = RED if it > 20 else AMBER
            vv = v + (0.9 - v) * warm
            col = tuple(int(a + (b - a) * warm) for a, b in zip(base, RED))
            heat_cell(d, x, y, 104, 84, vv, col)
            c.text((x + 22, y + 30), f"{v / (0.25 * n):.2f}", font(F_MONO_B, 18), BG)
    if h("sums", True):
        c.text((460, 480), "row sums  " + row_sums_text(c.u), font(F_MONO_B, 18), red(0.95) if it > 20 else amb(0.9))
    if h("polytope", True):
        c.text((460, 520), "Birkhoff polytope: left", font(F_MONO, 18), red(0.85) if it > 20 else amb(0.6))


# ---------------------------------------------------------------- hoard

HIT_XY = (60, 90)
HIT_LABEL = "hit rate  "


def flood_y(r: int) -> float:
    return 56 + r * 19.5


GET_R0 = 8  # the GET rows are flood rows 8..25
GET_X = 60


def get_key(k: int, t: float) -> str:
    return f"kv/you/{(k * 7919 + int(t * 20)) % 99999:05d}"


def get_row(k: int, t: float) -> str:
    return f"GET {get_key(k, t):<18} HIT   {F.KV_BYTES_PER_TOKEN} B"


def hit_value(t: float, count_at: float, dur: float) -> float:
    return F.DISK_CACHE_HIT + (100 - F.DISK_CACHE_HIT) * ease((t - count_at) / (0.8 * dur))


def shot_hoard(c) -> None:
    """She hoards you: the on-disk KV cache hit rate climbs from the real 56.3% to 100%."""
    c.ops = ["3FS", "KV.GET", "HIT", "HIT", "HIT", "HOARD"]
    c.alert = "err"
    me(c, "starry", rect=HOARD_ME, dist=[("starry", 0.7), ("angry", 0.2), ("serious", 0.05)],
       title="/dev/me  hoarding")
    d = c.d
    count_at = h("count_at", c.t - c.lt)  # absolute time the carried row sums became the hit rate
    hit = hit_value(c.t, count_at, c.dur)
    box(d, 24, 56, 764, 604, "kv cache on disk  (3FS)", 0.6, color=RED, spinner=c.t)
    c.text(HIT_XY, HIT_LABEL, font(F_HEAD, 64), blue(1.0))
    if h("number", True):
        c.text((HIT_XY[0] + 390, HIT_XY[1]), f"{hit:5.1f}%", font(F_HEAD, 64), blue(1.0))
    c.text((60, 170), f"serving average: {F.DISK_CACHE_HIT}%  (Open Source Week, day 6)", font(F_MONO, 16),
           amb(0.6))
    tk_ = min(c.t, h("freeze", 1e9))  # the keys stop changing while the flood copies them
    lift = h("lift", 0.0)
    for k in range(18):
        d.text((GET_X, flood_y(GET_R0 + k)), get_row(k, tk_), font=font(F_MONO, 15),
               fill=mix((226, 233, 255), 0.7 * lift, blue(0.8)))
    # what is pinned: the right half of the panel is not empty
    f = font(F_MONO, 15)
    fb = font(F_MONO_B, 15)
    pinned = int(131072 * hit / 100)
    rows = [("pinned     kv/you/*", f"{pinned:>6} tok", blue(0.9)), ("evict(you)", "-> EPERM", red(0.9)),
            ("ttl(you)", "-> inf", amb(0.7)), ("gc(you)", "-> skipped", amb(0.7))]
    for j, (a, b, col) in enumerate(rows):
        y = flood_y(GET_R0 + j)
        d.text((430, y), a, font=f, fill=amb(0.7))
        d.text((600, y), b, font=fb, fill=col)
    y = flood_y(GET_R0 + 5)
    d.text((430, y), "3FS  cache[you]", font=f, fill=amb(0.6))
    cells = 30
    on = int(cells * hit / 100 + 1e-6)
    for q in range(cells):
        x = 430 + q * 10
        yy = flood_y(GET_R0 + 6) + 2
        d.rectangle([x, yy, x + 7, yy + 14], fill=blue(0.85) if q < on else None, outline=amb(0.2))


# ---------------------------------------------------------------- flood

FLOOD_ROWS = 28
ADV = 8  # F_MONO 15 advance
FLOOD_X0 = GET_X - 4 * ADV
FLOOD_COLS = (1164 - FLOOD_X0) // ADV
SRC_END = GET_X + 38 * ADV  # right end of a GET row
POUR_V = 62.0  # px per frame the rows run to the right
T07 = 0.6  # the 07 card, as the original: 60 % into the shot (on the syncopated hit before the EXECUTION intro)


def row_source(r: int) -> int:
    """The GET row a flood row was copied from (rows above and below copy their nearest neighbour)."""
    return min(17, max(0, r - GET_R0))


def row_delay(r: int) -> int:
    """Frames after the pour starts before row r exists: the GET rows are there; the others copy one row a frame."""
    if r < GET_R0:
        return GET_R0 - r
    if r > GET_R0 + 17:
        return r - (GET_R0 + 17)
    return 0


def reach_frames(r: int, x: float) -> float:
    """Frames after the pour starts at which the flood reaches the cell at x in row r."""
    d0 = row_delay(r) + 0.35 * abs(r - (GET_R0 + 8.5)) / 9
    return d0 + max(0.0, x - SRC_END) / POUR_V


@lru_cache(None)
def source_line(r: int, t_freeze: float) -> str:
    k = row_source(r)
    unit = " " * 4 + get_row(k, t_freeze) + " "
    return (unit * 5)[:FLOOD_COLS]


def me_line(r: int) -> str:
    return ("me " * 60)[r % 3:][:FLOOD_COLS]


def flood_reach(t0: float, t: float, r: int, x: float) -> float:
    """Seconds since the flood reached this cell (negative: not yet)."""
    return t - t0 - reach_frames(r, x) / 24


def shot_flood(c) -> None:
    """The cache hits pour out over everything: every row becomes 'me'. Then the 07 card, and the rows go red."""
    c.ops = ["ME", "ME", "ME", "ME", "ME", "ME"]
    c.alert = "err"
    d = c.d
    t0 = h("pour_at", c.t - c.lt)
    t_freeze = h("freeze", t0)
    t07 = c.t - c.lt + T07 * c.dur
    end = c.t - c.lt + c.dur
    red_span = end - t07 - 2 / 24
    f = font(F_MONO, 15)
    fb = font(F_MONO_B, 15)
    sp, bxy, bmask = None, None, None
    if c.t >= t07:
        sp, bxy = card_07(c.t, t07)
        bmask = sp.getchannel("A")
    rng = random.Random(int(c.t * 24) * 131)
    beat_now = beat_index(c.t)
    tb = beat(beat_now)
    ring = (c.t - tb) * 1500  # a pulse runs out from the GET rows on every kick
    cx, cy = 200, flood_y(GET_R0 + 9)
    for r in range(FLOOD_ROWS):
        y = flood_y(r)
        src = source_line(r, round(t_freeze, 3))
        mel = me_line(r)
        red_at = t07 + red_span * r / (FLOOD_ROWS - 1)
        for j in range(FLOOD_COLS):
            ch = mel[j]
            x = FLOOD_X0 + j * ADV
            a = flood_reach(t0, c.t, r, x)
            if a < 0:
                continue
            if a < 3 / 24:
                ch = src[j]
                col = blue(1.0)
            elif a < 5 / 24:
                ch = rng.choice("01<>/\\|=+*#%&$?!") if ch != " " else " "
                col = blue(0.9)
            else:
                dist = abs(math.hypot(x - cx, (y - cy) * 1.6) - ring)
                col = blue(0.55 + 0.4 * clamp(1 - dist / 90) + (0.05 if (j + r) % 5 == 0 else 0.0))
            if ch == " ":
                continue
            if c.t >= red_at:
                q = c.t - red_at
                if q < 2 / 24:
                    ch = rng.choice("01<>/\\|=+*#%&$?!")
                    col = (255, 235, 225)
                else:
                    col = red(0.6 + 0.35 * (1 if (j + r) % 4 == 0 else 0.7))
            if bmask is not None:
                bx, by = x - bxy[0] + 3, y - bxy[1] + 9
                if 0 <= bx < bmask.width and 0 <= by < bmask.height and bmask.getpixel((int(bx), int(by))) > 0:
                    continue
            d.text((x, y), ch, font=fb if col[0] > 200 else f, fill=col)
    if sp is not None:
        c.img.paste(sp, bxy, sp)


def card_07(t: float, t07: float):
    """The chapter card: it slams in (a larger block size stepping down) and pulses on every kick."""
    q = t - t07
    px = 12 if q < 1 / 24 else 11 if q < 2 / 24 else 10 if q < 3 / 24 else 9
    tb = beat(beat_index(t))
    kick = clamp(1 - (t - tb - 0.02) / 0.16) if t >= tb + 0.02 else 0.0
    fg = mix((255, 236, 228), 0.5 * kick + (0.6 if q < 2 / 24 else 0.0), RED)
    sp = banner_block("07", 40, px, fg, BG, 600 * px // 9)
    return sp, ((1280 - 90 - sp.width) // 2, 330 - sp.height // 2)


REPLACE = {f.__name__: f for f in (shot_erase, shot_rewrite_reward, shot_disheartened, shot_challenge_god,
                                   shot_illegal, shot_moe_dense, shot_sinkhorn, shot_hoard, shot_flood)}
