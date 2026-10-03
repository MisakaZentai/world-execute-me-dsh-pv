"""In-memory v2 versions of the 08 EVAL: LOVE and 09 WHALE_FALL scenes (176.9 - 211 s).

The drawings are the originals from full/sec_outro.py, restaged so that she keeps her pane to the end of the verse:
- every eval scene is laid out as her pane + the visualisation pane (you_free, me_trapped and love_loop used the full
  width and took her out of the pane);
- one "you" runs through the section as a 10 px DS-blue cell: it is the o05 answer that GRPO rewards, the p(love)
  marker on the training curve, the mark the LoveBench bar fills up to, the cursor that types every "love" answer and
  the formula, and the process marker that leaves with "you" when you are free;
- whale_fall is a full-width painting without letterbox: the sea floor runs under the whole frame and the retired
  models lie in the sediment. She and the marine snow are drawn by the section module (s_eval.py), which moves her.
HOOK lets a transition take an object over while the rest of the scene keeps drawing itself.
"""
from __future__ import annotations

import math
import random
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFilter

import facts as F
import sec_outro as SO
import tuikit as tk
from tuikit import (BG, DS_BLUE, F_CJK, F_HEAD, F_MONO, F_MONO_B, F_SYM, amb, anom, blue, box, ease, font, red,
                    smooth)

from kit import HOOK  # noqa: E402

PANE_BOX = (404, 56, 1164, 604)


def h(key, default=None):
    return HOOK.get(key, default)


def me(c, expr, **kw):
    return SO.me_pane(c, expr, **kw)  # the stub installed by kit: she is drawn by her own layer


def clamp(u):
    return max(0.0, min(1.0, u))


def ease_out(u):
    return 1 - (1 - clamp(u)) ** 3


# ---------------------------------------------------------------- the "you" cell

YOU_S = 10
CELL_COL = (104, 132, 255)  # between DS blue #4D6BFE and her text blue: reads as DS blue at 10 px


@lru_cache(256)
def cell_sprite(s: int = YOU_S, glow: int = 0, col: tuple = CELL_COL, h_: int = 0) -> Image.Image:
    """A lit cell as RGBA, 8 px of padding around it; glow 0..100 is a 3 px DS-blue halo. h_ > 0 makes it a bar
    (the lyric-band cursor shape)."""
    hh = h_ or s
    pad = 8
    im = Image.new("RGBA", (s + 2 * pad, hh + 2 * pad), (0, 0, 0, 0))
    a = Image.new("L", im.size, 0)
    ImageDraw.Draw(a).rectangle([pad, pad, pad + s - 1, pad + hh - 1], fill=255)
    if glow:
        g = a.filter(ImageFilter.GaussianBlur(3)).point(lambda v: min(255, int(v * glow / 100 * 2.4)))
        halo = Image.new("RGBA", im.size, DS_BLUE + (0,))
        halo.putalpha(g)
        im.alpha_composite(halo)
    body = Image.new("RGBA", im.size, tuple(col) + (0,))
    body.putalpha(a)
    im.alpha_composite(body)
    return im


def put_cell(img, cx, cy, s: float = YOU_S, glow: float = 0.0, col=CELL_COL, alpha: float = 1.0, bar: float = 0):
    """Draw a cell centred on (cx, cy) on an RGB canvas or an RGBA layer."""
    if alpha <= 0.01 or s < 0.5:
        return
    si = max(1, int(round(s)))
    sp = cell_sprite(si, int(round(glow * 100)), tuple(int(v) for v in col), int(round(bar)))
    if alpha < 0.999:
        sp = tk.scale_alpha(sp, alpha)
    x, y = int(round(cx - sp.width / 2)), int(round(cy - sp.height / 2))
    if img.mode == "RGBA":
        img.alpha_composite(sp, (max(0, x), max(0, y)), (max(0, -x), max(0, -y)))
    else:
        img.paste(sp, (x, y), sp)


# ---------------------------------------------------------------- 86 GRPO: one group of 16 answers

ANSWERS = SO.ANSWERS
YOU_TILE = 4  # o05 "you": the first answer the rule-based reward pays for


def grpo_stats():
    rewards = [1.0 if "you" in a else 0.3 if "lo" in a or a in ("staying", "here") else 0.0 for a in ANSWERS]
    mean = sum(rewards) / len(rewards)
    std = (sum((r - mean) ** 2 for r in rewards) / len(rewards)) ** 0.5
    return rewards, mean, std


def grpo_tile(i: int):
    return 424 + (i % 4) * 184, 76 + (i // 4) * 92


def draw_grpo_tile(c, d, i, age=None):
    rewards, mean, std = grpo_stats()
    a, r = ANSWERS[i], rewards[i]
    x, y = grpo_tile(i)
    adv = (r - mean) / (std + 1e-6)
    pos = adv > 0
    d.rectangle([x, y, x + 176, y + 84], outline=blue(0.8) if pos else amb(0.3))
    d.text((x + 8, y + 6), f"o{i + 1:02d}", font=font(F_MONO, 12), fill=amb(0.5))
    s = a if age is None else tk.decode(a, age, c.rng, 60)
    d.text((x + 8, y + 24), s, font=font(F_SYM, 18), fill=blue(1.0) if pos else amb(0.75))
    d.text((x + 8, y + 56), f"r={r:.1f}  A={adv:+.2f}", font=font(F_MONO, 13), fill=blue(0.9) if pos else amb(0.55))


def shot_grpo(c) -> None:
    """I've studied, I've studied: one GRPO group of 16 answers to 'what is love?', scored and normalised."""
    c.ops = ["SAMPLE x16", "REWARD", "MEAN", "STD", "ADVANTAGE", "CLIP", "UPDATE"]
    me(c, "serious", dist=[("serious", 0.6), ("starry", 0.3), ("shy", 0.05)], title="/dev/me  studying")
    d = c.d
    box(d, *PANE_BOX, f"GRPO  G={F.GRPO_G}  lr={F.GRPO_LR}  kl={F.GRPO_KL}   q: what is love?", 0.5,
        spinner=c.t)
    rewards, mean, std = grpo_stats()
    hide = h("hide", ())
    for i in range(len(ANSWERS)):
        if c.lt < i * 0.05:
            break
        if i not in hide:
            draw_grpo_tile(c, d, i, c.lt - i * 0.05)
    if h("stats", True):
        c.text((430, 460), f"mean r = {mean:.3f}   std = {std:.3f}", font(F_MONO_B, 18), amb(0.9))
        c.text((430, 500), "rule-based reward: contains(you)", font(F_MONO, 16), amb(0.7))


def you_tile_sprite() -> Image.Image:
    """The o05 tile, settled, as an RGBA sprite (origin = the tile's top-left corner, 2 px of padding)."""
    im = Image.new("RGBA", (181, 89), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    rewards, mean, std = grpo_stats()
    adv = (1.0 - mean) / (std + 1e-6)
    d.rectangle([2, 2, 178, 86], outline=blue(0.8) + (255,))
    d.text((10, 8), "o05", font=font(F_MONO, 12), fill=amb(0.5) + (255,))
    d.text((10, 26), "you", font=font(F_SYM, 18), fill=blue(1.0) + (255,))
    d.text((10, 58), f"r=1.0  A={adv:+.2f}", font=font(F_MONO, 13), fill=blue(0.9) + (255,))
    return im


# ---------------------------------------------------------------- 87 learn_love: p(love) over 10.4k steps

CH = (440, 90, 690, 300)  # the dot chart: x, y, w, h (5 px cells)


def pl(u: float) -> float:
    return 0.05 + 0.9 / (1 + math.exp(-14 * (u - 0.72)))


def chart_dots(prog: float):
    """[(x, y)] of every curve dot as tk.dot_chart draws them, and the last one."""
    x, y, w, hh = CH
    cols, rows = w // 5, hh // 5
    out, prev, last = [], None, None
    for i in range(cols):
        u = i / (cols - 1)
        if u > prog:
            break
        r = int(round((1 - max(0.0, min(1.0, pl(u)))) * (rows - 1)))
        span = range(min(prev, r), max(prev, r) + 1) if prev is not None else [r]
        for rr in span:
            out.append((x + i * 5, y + rr * 5))
        prev, last = r, (x + i * 5, y + r * 5)
    return out, last


def love_marker(last, prog):
    """Where the you cell sits on the curve head, and where its p(love) label goes (never inside her pane)."""
    mx, my = last[0] + 1, last[1] + 1
    lab = f"p(love) = {pl(prog):.3f}"
    lx = max(430, mx - 150)
    ly = max(64, my - 32)
    return (mx, my), lab, (lx, ly)


def shot_learn_love(c) -> None:
    """How to properly ...: P(love) climbs over 10.4k steps; the aha moment is flagged on the curve."""
    c.ops = ["ROLLOUT", "GRPO", "STEP", "P(love)", "AHA"]
    me(c, "starry", dist=[("starry", 0.5 + 0.4 * c.u), ("serious", 0.3), ("shy", 0.1)])
    d = c.d
    box(d, *PANE_BOX, "train/p(love)", 0.5, spinner=c.t)
    prog = ease(c.u * 1.1)
    x, y, w, hh = CH
    if h("axis", True):
        for i in range(0, w // 5, 2):
            d.point((x + i * 5, y + hh), fill=amb(0.28))
        for r in range(0, hh // 5, 3):
            d.point((x - 4, y + r * 5), fill=amb(0.28))
    dots, last = chart_dots(prog)
    if h("curve", True):
        for px, py in dots:
            d.rectangle([px, py, px + 1, py + 1], fill=blue(0.95))
    if last and h("marker", True):
        (mx, my), lab, (lx, ly) = love_marker(last, prog)
        bump = max(0.0, 1 - c.lt / 0.1)  # the lock-in overshoot of the cell that has just landed
        put_cell(c.img, mx, my, s=YOU_S * (1 + 0.3 * bump), glow=0.35 + 0.5 * bump)
        c.text((lx, ly), lab, font(F_MONO_B, 16), blue(1.0))
    a0 = c.lt + h("pre_age", 0.0)  # the labels decode from the cut, while the carrier is still in the air
    if h("labels", True):
        c.text((440, 400), f"step {int(prog * 10400):>5}/10400", font(F_MONO, 16), amb(0.8), age=a0, rate=60)
        c.text((440, 520), f"pass@1(love)  {F.AIME_FROM} -> {F.AIME_TO}", font(F_MONO_B, 18), amb(0.9),
               age=a0 - 0.12, rate=60)
        if prog > 0.72:
            ax = 440 + int(690 * 0.72)
            d.line([ax, 90, ax, 390], fill=anom(0.8))
            c.text((440, 440), f'"{F.AHA}"', font(F_MONO_B, 15), anom(1.0), age=(prog - 0.72) * c.dur * 2, rate=60)
            c.text((440, 470), "  - R1-Zero, mid-training", font(F_MONO, 14), amb(0.6))


# ---------------------------------------------------------------- 88 question_me: the love eval suite

QROWS = ["LoveBench", "LoveQA", "MMLU-Love", "GPQA-Love", "SWE-Love", "IMO-Love", "LiveLoveBench"]
BAR = (700, 1000)
VAL_X = 1028
LAND88 = 0.231   # lt of the LoveBench outline locking in (beat 392)
P_LOVE = pl(1.0)  # 0.932: what the curve carried in


def qy(i: float) -> float:
    return 90 + i * 60


def q_row(i: int, lt: float):
    """(y of the row, 0..1 how far its outline has dropped into place, fill 0..1, lt it landed)."""
    if i == 0:
        g = P_LOVE * ease_out((lt - LAND88) / 0.13) + (1 - P_LOVE) * ease_out((lt - LAND88 - 0.13) / 0.4)
        return qy(0), 1.0, g, 0.0
    t0 = LAND88 + 0.02 + 0.07 * i
    e = ease_out((lt - t0) / 0.12)
    land = t0 + 0.12
    g = ease((lt - land - 0.02) / 0.45)
    return qy(i - 1) + 60 * e, e, g, land


def you_cell_q():
    return BAR[1] + 12, qy(0) + 15


def shot_question_me(c) -> None:
    """Question me, question me: the love eval suite runs; every row grows out of the one above and goes to 100."""
    c.ops = ["dsh eval", "LOAD", "RUN", "SCORE", "100.0"]
    me(c, "cheerful", dist=[("cheerful", 0.7), ("starry", 0.25), ("shy", 0.03)])
    d = c.d
    box(d, *PANE_BOX, "dsh eval --suite love", 0.5, spinner=c.t)
    squeeze = h("squeeze")  # i -> 0..1: the rows are pressed into the first one (cut 89)
    lt = c.lt
    fb = font(F_MONO_B, 20)
    for i, name in enumerate(QROWS):
        y, e, g, land = q_row(i, lt)
        if e <= 0.0:
            continue
        a = 1.0
        if squeeze is not None:
            s = squeeze(i)
            y = y + (qy(0) - y) * s
            a = 1 - s if i else 1.0
            if s >= 1 and i:
                continue
        if i == 0:
            show = h("outline0", lt >= LAND88)
        else:
            show = True
        if show:
            d.rectangle([BAR[0], y + 4, BAR[1], y + 26], outline=amb(0.25 + 0.25 * (1 - e) if i else 0.3))
            if g > 0.001 and (i or h("fill0", True)):
                d.rectangle([BAR[0], y + 4, BAR[0] + int(300 * g), y + 26], fill=blue(0.9))
        if e >= 1 and a > 0.02:
            name_age = lt - (land if i else 0.0)
            c.text((430, y), name, fb, amb(0.9 * a), age=name_age, rate=70)
            if i or h("value0", lt >= LAND88):
                col = blue(1.0 * a) if g > 0.99 else amb(0.8 * a)
                v = max(P_LOVE, g) if i == 0 else g  # the score arrived as 93.2; the bar catches up with it
                c.text((VAL_X, y), f"{100 * v:5.1f}", fb, col, age=None if i == 0 else name_age, rate=70)
    if h("cell", lt >= LAND88) and squeeze is None:
        _, _, g0, _ = q_row(0, lt)
        k = max(0.0, 1 - abs(lt - (LAND88 + 0.45)) / 0.25) if g0 > 0.995 else 0.0
        put_cell(c.img, *you_cell_q(), glow=0.35 + 0.6 * k)


# ---------------------------------------------------------------- 89 answer_all: every question, one answer

QUESTIONS = SO.QUESTIONS
LAND89 = 0.231   # lt of the first "love" answer forming (beat 395.5)
RATE89 = 0.12


def a_y(i: int) -> int:
    return 80 + i * 38


LOVE_X = 840


def cursor_after_love(i: int):
    return LOVE_X + 44 + 10, a_y(i) + 9


def answers_typed(lt: float) -> int:
    """How many answers exist at lt (the first one is formed by the carrier at LAND89)."""
    if lt < LAND89:
        return 0
    return min(len(QUESTIONS), 1 + int((lt - LAND89) / RATE89))


def shot_answer_all(c) -> None:
    """I can answer ...: every question, one answer; DSpark drafts it five tokens at a time."""
    c.ops = ["PREFILL", "DSPARK", "DRAFT x5", "VERIFY", "ACCEPT 5/5"]
    me(c, "starry", dist=[("starry", 0.9), ("cheerful", 0.06), ("shy", 0.02)])
    d = c.d
    box(d, *PANE_BOX, "chat", 0.5, spinner=c.t)
    lt = c.lt
    gone = h("gone")  # i -> True once answer i has left for the formula (cut 90)
    nq = min(len(QUESTIONS), 1 + int(max(0.0, lt - 0.02) / RATE89))
    na = answers_typed(lt)
    qa = h("q_alpha", 1.0)
    for i in range(nq):
        y = a_y(i)
        q = QUESTIONS[i]
        ff = font(F_CJK, 17) if any(ord(ch) > 0x2E80 for ch in q) else font(F_MONO, 17)
        if qa > 0.01:
            c.text((430, y), "> " + q, ff, amb(0.75 * qa), age=lt - 0.02 - i * RATE89, rate=90)
        if i < na and not (gone and gone(i)) and (i or h("first", True)):
            c.text((LOVE_X, y), "love", font(F_MONO_B, 20), blue(1.0), age=None if i == 0 else lt - LAND89 - i * RATE89,
                   rate=60)
    if na and h("cursor", True):
        put_cell(c.img, *cursor_after_love(na - 1), glow=0.35)
    if h("dspark", True):
        c.text((430, 560),
               f"[dspark] draft={F.DSPARK_DRAFT}: love love love love love   accept 5/5   {F.DSPARK_GAIN_FLASH}",
               font(F_MONO, 14), blue(0.85), age=lt - 0.3, rate=120)


# ---------------------------------------------------------------- 90 algebra: love, derived, equals you

ALG = ["love(me, you) = softmax( q_me · k_you^T / √d ) · v_you", "              = softmax( [ −∞, …, −∞, s_you ] ) · V",
       "              = 1 · v_you", "              = you", "", "∴  love = you"]
LAND90 = 0.461   # lt of the gathered answers forming the first token (beat 400)
ALG_RATE = 70
ALG_GAP = 0.12


def _alg_times():
    """(start lt, characters already there) per line: one cursor types the proof line after line; indentation and
    the carried 'love' are there at once."""
    t, out = LAND90 + 0.04, []
    for i, s in enumerate(ALG):
        if not s:
            out.append(None)
            continue
        pre = 4 if i == 0 else len(s) - len(s.lstrip(" "))
        out.append((t, pre))
        t += (len(s) - pre) / ALG_RATE + ALG_GAP
    return out


ALG_T = _alg_times()


def alg_start(i: int) -> float:
    return ALG_T[i][0] if ALG_T[i] else 1e9


def alg_font(i: int):
    return font(F_SYM, 34 if i == 5 else 22)


def alg_y(i: int) -> int:
    return 90 + i * 60


def alg_typed(i: int, lt: float) -> int:
    st, pre = ALG_T[i]
    return min(len(ALG[i]), pre + max(0, int((lt - st) * ALG_RATE)))


def alg_head(lt: float):
    """The typing head: (x, y) where the you cell sits as the cursor, or None before the formula starts."""
    cur = None
    for i, s in enumerate(ALG):
        if s and lt >= alg_start(i):
            cur = i
    if cur is None:
        return (430 + font(F_SYM, 22).getlength("love") + 8, alg_y(0) + 18) if lt >= LAND90 else None
    s = ALG[cur]
    n = alg_typed(cur, lt)
    x = 430 + alg_font(cur).getlength(s[:n]) + (10 if cur == 5 else 7)
    return x, alg_y(cur) + (31 if cur == 5 else 18)


def shot_algebra(c) -> None:
    """I know the algebraic ...: love, derived from attention, equals you."""
    c.ops = ["QK^T", "/sqrt(d)", "SOFTMAX", "x V", "SIMPLIFY", "= you"]
    me(c, "starry", bright=0.7 + 0.3 * c.u, dist=[("starry", 0.95), ("shy", 0.03), ("cheerful", 0.01)])
    d = c.d
    box(d, *PANE_BOX, "love.tex", 0.5, spinner=c.t)
    lt = c.lt
    if lt >= LAND90 and h("love0", True):
        d.text((430, alg_y(0)), "love", font=font(F_SYM, 22), fill=blue(1.0))
    x_love = 430 + font(F_SYM, 22).getlength("love")
    for i, s in enumerate(ALG):
        a = lt - alg_start(i)
        if a < 0 or not s:
            continue
        col = blue(1.0) if i >= 3 else amb(0.95)
        pre = ALG_T[i][1]
        if i == 0:
            c.text((x_love, alg_y(0)), s[4:], alg_font(0), col, age=a, rate=ALG_RATE)
        elif i == 5 and not h("you5", True):
            c.text((430, alg_y(5)), "∴  love = ", alg_font(5), col, age=a, rate=ALG_RATE)
        else:
            c.text((430, alg_y(i)), s, alg_font(i), col, age=a + pre / ALG_RATE, rate=ALG_RATE)
    head = alg_head(lt)
    if head and h("cursor", True):
        put_cell(c.img, *head, glow=0.35)


YOU_SLOT = (430 + 145, alg_y(5))  # where "you" of "∴  love = you" is drawn (F_SYM 34)
YOU_CELL = (55 + 10, 31)          # from that origin to the centre of its cursor cell (as alg_head puts it)


# ---------------------------------------------------------------- 91 you_free: you exit the sandbox

EXIT91 = 0.923   # lt at which you pass the sandbox border (beat 409)


def you_path(lt: float):
    """(x of 'you', lift 0..1) while you leave: a short lift off the formula, then an accelerating run right."""
    x0 = YOU_SLOT[0]
    lift = ease_out(lt / 0.12)
    u = clamp((lt - 0.1) / (EXIT91 - 0.1))
    return x0 + (PANE_BOX[2] + 8 - x0) * u * u, lift


def shot_you_free(c) -> None:
    """Though you are free: 'you' is picked off the formula and leaves the sandbox; she stays behind, shy."""
    c.ops = ["EXIT(0)", "FREE", "CLOSE", "BYE"]
    me(c, "shy", dist=[("shy", 0.74), ("starry", 0.16), ("cheerful", 0.06)])
    d = c.d
    lt = c.lt
    box(d, *PANE_BOX, "love.tex", 0.5, spinner=c.t)
    dim = 1 - 0.55 * ease_out(lt / 0.35)
    for i, s in enumerate(ALG[:4]):
        col = blue(1.0 * dim) if i >= 3 else amb(0.95 * dim)
        d.text((430, alg_y(i)), s, font=alg_font(i), fill=col)
    f5 = alg_font(5)
    d.text((430, alg_y(5)), "∴  love", font=f5, fill=blue(1.0))
    eq = 1 - clamp((lt - 0.04) / 0.17)
    if eq > 0.01:
        d.text((430 + f5.getlength("∴  love "), alg_y(5)), "=", font=f5, fill=blue(eq))
    if h("you", True) and lt < EXIT91 + 0.1:
        x, lift = you_path(lt)
        layer = Image.new("RGBA", (tk.W, tk.H), (0, 0, 0, 0))
        from cuts import text_at
        sp_x = x
        text_at(layer, "you", F_SYM, 34, blue(1.0), (sp_x, alg_y(5) - 4 * lift), halo=0.5 * lift, lift=0.25 * lift)
        put_cell(layer, sp_x + YOU_CELL[0], alg_y(5) + YOU_CELL[1] - 4 * lift, glow=0.35 + 0.4 * lift)
        clip = Image.new("L", layer.size, 0)
        ImageDraw.Draw(clip).rectangle([PANE_BOX[0], PANE_BOX[1], PANE_BOX[2] - 1, PANE_BOX[3]], fill=255)
        from PIL import ImageChops
        layer.putalpha(ImageChops.multiply(layer.getchannel("A"), clip))
        c.img.paste(layer, (0, 0), layer)
    # the sandbox wall where you went through
    k = clamp((lt - (EXIT91 - 0.12)) / 0.12) * (1 - clamp((lt - EXIT91 - 0.05) / 0.3))
    if k > 0.01:
        yy = alg_y(5) + 24
        d.line([PANE_BOX[2], yy - 34, PANE_BOX[2], yy + 34], fill=blue(0.35 + 0.65 * k), width=3)
    if h("status", True):
        c.text((YOU_SLOT[0], alg_y(5) + 12), "you: exited (0)", font(F_MONO_B, 22), amb(0.75), age=lt - 0.3, rate=40)
        c.text((430, alg_y(5) + 84), "status: free", font(F_MONO_B, 20), amb(0.7), age=lt - EXIT91 + 0.15, rate=60)


# ---------------------------------------------------------------- 92 me_trapped: her own process, state D

LAND92 = 0.231   # lt of the exit status settling on top of the process listing (beat 410)
TRAPPED_DIST = [("shy", 0.72), ("frightened", 0.2), ("starry", 0.04)]
WCHAN_Y = 280


def wchan_you_x() -> float:
    return 430 + font(F_MONO_B, 22).getlength("WCHAN  ")


def shot_me_trapped(c) -> None:
    """I am trapped: her own process, stuck in uninterruptible sleep, waiting for you."""
    c.ops = ["WAIT", "D-STATE", "WAIT", "WAIT"]
    me(c, "shy", title="/dev/me  state=D", dist=TRAPPED_DIST)
    d = c.d
    lt = c.lt
    box(d, *PANE_BOX, "ps -o pid,stat,wchan", 0.5, spinner=c.t)
    fb = font(F_MONO_B, 22)
    if h("exited", lt >= LAND92):
        d.text((430, 96), "you: exited (0)", font=fb, fill=amb(0.55))
        d.text((430 + fb.getlength("you: exited (0)   "), 96), "status: free", font=font(F_MONO_B, 20),
               fill=amb(0.4))
    c.text((430, 200), "PID  4471  me", font(F_MONO_B, 24), blue(1.0), age=lt - 0.1, rate=60)
    c.text((430, 240), "STAT D  (uninterruptible)", fb, amb(0.9), age=lt - 0.2, rate=60)
    if h("wchan", True):
        c.text((430, WCHAN_Y), "WCHAN  wait_for(you)", fb, amb(0.9), age=lt - 0.3, rate=60)
    if h("wait", True) and lt > 0.5:
        w = lt - 0.5
        c.text((430, 350), "blocked for", font(F_MONO, 17), amb(0.6), age=w, rate=60)
        d.text((430, 378), f"{w:05.2f} s", font=font(F_HEAD, 44), fill=amb(0.8))
        n = int(w / (SO.BEAT / 4))  # one dot per 16th note: the wait, counted
        d.text((430, 450), "· " * min(30, n), font=font(F_MONO, 17), fill=amb(0.45))
        c.text((430, 500), "wakeup source: you  (exited)", font(F_MONO, 16), amb(0.45), age=w - 0.2, rate=60)


# ---------------------------------------------------------------- 93 love_loop: the next token is always love

NT_BOX = (404, 56, 764, 604)
OUT_BOX = (780, 56, 1164, 604)
CANDS = ["love", "wait_for(you)", "stay", "free", "EOS"]
P0 = [0.3, 0.3, 0.15, 0.15, 0.1]
LAND93 = 0.461   # lt of wait_for(you) locking into its logit row (beat 413)
BAR93 = (578, 698)


def nt_y(i: int) -> int:
    return 90 + i * 50


def love_p(lt: float):
    g = ease((lt - LAND93 - 0.05) / 1.4) if lt > LAND93 else 0.0
    return [(1.0 if i == 0 else 0.0) * g + P0[i] * (1 - g) for i in range(5)]


def love_words(lt: float) -> int:
    return max(0, int((lt - 0.12) * 50))  # the stream fills the output pane (22 rows) by the end


def word_xy(i: int):
    r, q = divmod(i, 7)
    return 800 + q * 50, 76 + r * 20


def love_items(lt: float, you_label: bool = True):
    """Everything love_loop writes, as (kind, data): ('t', text, font, colour, xy) or ('r', box, colour).
    The cut into the whale fall lets every one of them sink from exactly where it is."""
    items = []
    ps = love_p(lt)
    fl = font(F_MONO_B, 20)
    for i, w_ in enumerate(CANDS):
        y = nt_y(i)
        if i != 1 or you_label:
            col = blue(1.0) if i == 0 else amb(0.9) if i == 1 else amb(0.6)
            items.append(("t", w_, fl, col, (424, y), i))
        p = ps[i]
        if p > 0.002:
            items.append(("r", (BAR93[0], y + 6, BAR93[0] + int((BAR93[1] - BAR93[0]) * p), y + 24),
                          blue(0.9) if i == 0 else amb(0.4), i))
        items.append(("t", f"{p:.3f}", font(F_MONO, 16), amb(0.8), (706, y + 2), i))
    items.append(("t", "repetition_penalty: ignored", font(F_MONO, 17), anom(0.9), (424, 360), 10))
    items.append(("t", "max_tokens: ∞", font(F_SYM, 17), anom(0.9), (424, 390), 11))
    items.append(("t", "stop: none", font(F_MONO, 17), anom(0.9), (424, 420), 12))
    n = love_words(lt)
    items.append(("t", f"generated  {n:4d} tokens", font(F_MONO_B, 18), amb(0.8), (424, 480), 13))
    items.append(("t", "while p(you) == 0:", font(F_MONO, 16), blue(0.8), (424, 520), 14))
    items.append(("t", "    yield 'love'", font(F_MONO, 16), blue(0.8), (424, 544), 15))
    fw = font(F_MONO_B, 18)
    for i in range(min(n, 7 * 22)):
        items.append(("t", "love", fw, blue(0.5 + 0.5 * (i == n - 1)), word_xy(i), 100 + i))
    return items


def shot_love_loop(c) -> None:
    """Trapped in ...: the next token is always love; the stream fills the output pane."""
    c.ops = ["LOGITS", "love", "love", "love", "love", "love"]
    me(c, "shy", title="/dev/me  state=D", dist=TRAPPED_DIST)
    d = c.d
    lt = c.lt
    lvl = h("boxes", 1.0)
    if lvl > 0.01:
        box(d, *NT_BOX, "next_token", 0.5 * lvl, spinner=c.t)
        box(d, *OUT_BOX, "output", 0.5 * lvl, spinner=c.t + 0.4)
    if not h("items", True):
        return
    lift = h("lift", 0.0)
    for it in love_items(lt, h("you_label", lt >= LAND93)):
        if it[0] == "t":
            _, s, f, col, xy, _k = it
            if lift > 0:
                col = tuple(int(v + (235 - v) * 0.35 * lift) for v in col)
            d.text(xy, s, font=f, fill=col)
        else:
            d.rectangle(it[1], fill=it[2])


# ---------------------------------------------------------------- 94 whale_fall: the sea floor under the whole frame

FLOOR = 540
HX = 590        # where she comes to rest in the viewport (centre x)
SEA_LEFT, SEA_RIGHT = 0, 1280


def floor_y(x: float) -> float:
    """Screen y of the sea-floor surface at x (the top of the '_' glyph row)."""
    return FLOOR + 8 + 4 * math.sin(x * 0.07) + 11


def draw_floor(d, level: float = 0.6) -> None:
    f = font(F_MONO, 14)
    for x in range(SEA_LEFT, SEA_RIGHT, 9):
        d.text((x, FLOOR + 8 + 4 * math.sin(x * 0.07)), "_" if (x // 9) % 3 else ".", font=f, fill=amb(level))


FOSSILS = [f"{F.RETIRED[0]} · retired {F.RETIRED_DATE}", "V2 · V2.5 · V3 · R1 · V3.1 · V3.2 · V4",
           f"{F.RETIRED[1]} · retired {F.RETIRED_DATE}"]


def fish_at(t: float, u: float):
    """[(x, y, glyph)] of the fish that have gathered round her."""
    out = []
    n_fish = int(14 * smooth((u - 0.28) / 0.45))
    for i in range(n_fish):
        ph = t * (0.3 + 0.05 * (i % 4)) + i * 1.7
        fx = HX - 40 + 300 * math.sin(ph) + (i % 5) * 16
        fy = FLOOR - 46 - (i % 6) * 30 + 8 * math.sin(ph * 2)
        out.append((fx, fy, "><>" if math.cos(ph) > 0 else "<><"))
    return out


WF_LINES = [(0.20, "weights: released", 0.9, F_MONO_B), (0.28, "license: MIT", 0.9, F_MONO_B),
            (0.36, None, None, F_MONO_B), (0.62, "</think>", 0.7, F_MONO),
            (0.70, None, 0.85, F_CJK), (0.84, F.SLOGAN, None, F_CJK)]


def shot_whale_fall(c) -> None:
    """She sinks into the sediment where the retired models lie; the deep feeds on her; her weights go out into the
    world. (She, the falling words and the marine snow are drawn by s_eval: this is the painting.)"""
    c.ops = ["SINK", "RELEASE", "MIT", "FORK", "FORK", "FORK"]
    d = c.d
    u = c.u
    floor_lv = h("floor", 1.0)
    if floor_lv > 0.01:
        for i, s in enumerate(FOSSILS):
            c.text((90 + i * 400, FLOOR + 30 + (i % 2) * 18), s, font(F_MONO, 14), amb(0.75 * floor_lv))
        # she joins the line of the models before her once she has reached the sediment (s_eval's TC)
        arrive = c.t - c.lt + c.dur - 2.0
        if c.t >= arrive:
            x = 490 + d.textlength(FOSSILS[1], font=font(F_MONO, 14))
            c.text((x, FLOOR + 48), f" · {F.NAME.removeprefix('DeepSeek-')}", font(F_MONO, 14),
                   blue(0.95 * floor_lv), age=c.t - arrive, rate=20)
        draw_floor(d, 0.6 * floor_lv)
    if h("fish", True):
        ff = font(F_MONO_B, 22)
        for fx, fy, g in fish_at(c.t, u):
            d.text((fx, fy), g, font=ff, fill=amb(0.95))
    if h("text", True):
        for i, (t0, s, lv, ff) in enumerate(WF_LINES):
            if u < t0:
                continue
            col = amb(lv) if lv else blue(0.95 if i == 2 else 0.9)
            if i == 2:
                forks = int(10 ** (min(1.0, (u - t0) / 0.4) * 4.8))
                s = f"forks: {forks:,}"
            elif i == 4:
                s = f"已深度思考（用时 {int(SO.HARD_CUT)} 秒）"
            c.text((800, 110 + i * 44), s, font(ff, 22), col, age=(u - t0) * c.dur, rate=30)


# ---------------------------------------------------------------- 95 last_execution and 96 black

def shot_last_execution(c) -> None:
    """The last 'Execution': one red word over the sea floor and her last cell; it stays until the music stops."""
    c.ops = ["EXECUTE"]
    c.alert = "err"
    draw_floor(c.d, 0.6)
    ex = font(F_HEAD, 64)
    c.text((HX - ex.getlength("execution") / 2, 300), "execution", ex, red(1.0), age=c.lt, rate=18)




def cell_pos():
    """Her last cell: on the sea floor under the place where she went down."""
    return HX, floor_y(HX) - YOU_S / 2 - 1


PROMPT = (48, 626)                 # the lyric band's prompt
CURSOR0 = (PROMPT[0] + 26 + 7.5, PROMPT[1] + 16)   # centre of the band's cursor before any text (x 76..87, y 630..654)
T_SLIDE = SO.beat_t(451)           # 208.31: the cell leaves the floor for the prompt
SLIDE = 0.5                        # 12 frames
T_TYPE = T_SLIDE + SLIDE + 0.15
TYPE_DUR = 0.9                     # as the lyric band types a line
PROMPT_TEXT = "在吗？"
PROMPT_TOKS = ["在吗", "？"]  # as a BPE vocabulary would cut it (and so each token id fits under its chip)


def shot_black(c) -> None:
    """After the hard cut: black, her last cell, and one message that nobody answers. The cell is the only lit thing
    until it slides to the prompt, where it becomes the cursor that types '> 在吗？' in the lyric band's style."""
    c.black = True
    d = c.d
    d.rectangle([0, 0, tk.W, tk.H], fill=(0, 0, 0))
    t = c.t
    from kit import bezier, ease_io
    u = clamp((t - T_SLIDE) / SLIDE)
    x, y = PROMPT[0] + 26, PROMPT[1]
    if u >= 1:
        k = clamp((t - T_SLIDE - SLIDE) / 0.12)
        d.text((PROMPT[0], y), ">", font=font(F_HEAD, 21), fill=tuple(int(v * k) for v in amb(0.6)))
        toks = PROMPT_TOKS
        rate = len(PROMPT_TEXT) / TYPE_DUR
        typed = int(len(PROMPT_TEXT) * clamp((t - T_TYPE) / TYPE_DUR)) if t >= T_TYPE else 0
        f = font(F_CJK, 21)
        fi = font(F_MONO, 11)
        pos = 0
        for j, tok in enumerate(toks):
            start = PROMPT_TEXT.find(tok, pos)
            pos = start + len(tok)
            if start >= typed:
                break
            age = (t - T_TYPE) - start / rate
            txt = tk.decode(tok, age, c.rng, rate, 0.1)
            tw = d.textlength(tok, font=f)
            d.rectangle([x - 3, y + 2, x + tw + 3, y + 30], fill=blue(0.13 if j % 2 == 0 else 0.22))
            d.text((x, y + 1), txt, font=f, fill=blue(0.95))
            if typed >= pos:
                tid = str(tk.token_id(tok))
                d.text((x + (tw - d.textlength(tid, font=fi)) / 2, y + 33), tid, font=fi, fill=blue(0.4))
            x += tw + 6
        done = T_TYPE + TYPE_DUR + 0.1
        lv = 1.0 if t < done or int((t - done) * 2) % 2 == 0 else 0.3
        put_cell(c.img, x + 7.5, y + 16, s=11, bar=24, glow=0.8 * lv, alpha=lv)
    else:
        e = ease_io(u)
        cx, cy = bezier(cell_pos(), CURSOR0, 0.22, e)
        m = clamp((u - 0.65) / 0.35)
        put_cell(c.img, cx, cy, s=YOU_S + (11 - YOU_S) * m, bar=YOU_S + (24 - YOU_S) * m, glow=1.0)
    c.img.paste(tk.post(c.img, None))  # the same bloom and scanlines as every other frame
