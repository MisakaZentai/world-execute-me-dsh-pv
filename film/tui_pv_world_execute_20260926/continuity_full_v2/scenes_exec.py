"""In-memory v2 versions of the 07 EXECUTION scenes (147.6 - 176.9 s), from full/sec_final.py (and the approved
chorus-1 scenes they call back).

What changes against the originals:
- exec_hit: the lay2 EXECUTE glyph banner is fitted inside the frame (it was clipped to 'XECUT').
- count: each number enters on its own syllable (ein on the cut, then dos .. liu one per beat).
- The red chorus is drawn red natively (v1 coloured the whole finished frame, chrome included, with flash_red).
  red_if_i_can: the IF I CAN letters are solid glyph cells (a dim red cell behind each glyph), so the banner reads.
  execute_all keeps v1's sample identity (#0000 is 'starry', as in chorus 1).
  red_then_i_can is the approved chorus-1 convolution (starry identity) in red ink; she is the red input.
  run_again keeps 'you: not found' as its first line and lifts the EXECUTE banner clear of the pinned chip.
  have_you_back finishes decoding 'you: not found' 0.4 s before the cut.
- She is never drawn by a scene: every scene only states how she feels (the stub); angry/execute is an eye bar
  overlay and a red tint on the string dancer (s_exec.py), never a portrait swap.
- HOOK lets a transition take an object over while the rest of the scene keeps drawing itself.
"""
from __future__ import annotations

import math
import random
from functools import lru_cache

from PIL import Image, ImageDraw

import sec_chorus1 as SC
import sec_final as SF
from engine import BEAT, FULL, LEFT, beat_index, beat_t, pulse
from tuikit import (AMBER, ANOM, BG, EXPRS, F_HEAD, F_MONO, F_MONO_B, RED, amb, anom, banner_bits, banner_block,
                    blue, box, conv_maps, ease, font, glyph_grid, halfblock, heat_cell, red, tile_from_lum)

from kit import HOOK  # noqa: E402

TARGETS = SF.TARGETS
PANE_BOX = (404, 56, 1164, 604)


def h(key, default=None):
    return HOOK.get(key, default)


def me(c, expr, **kw):
    return SF.me_pane(c, expr, **kw)  # the stub while v2 draws; the original pane inside v1.frame (the hits)


def mixc(a, b, u):
    u = max(0.0, min(1.0, u))
    return tuple(int(x + (y - x) * u) for x, y in zip(a, b))


# ---------------------------------------------------------------- the EXECUTION hits

LAY2_FIT = 1100  # canvas px: inside the body width, so the full-bleed scale keeps all seven letters on screen


@lru_cache(4)
def lay2_bits():
    """EXECUTE at the most rows that fit (20; the original 26 rows were 1424 px wide and showed 'XECUT'). Fewer
    rows keep the letters' proportions and the gaps between them; condensing them merged the letters."""
    f = font(F_MONO_B, 15)
    cw, ch = f.getlength("M"), 16
    rows = 26
    bits = banner_bits("EXECUTE", rows, ch / cw)
    while bits.width * cw > LAY2_FIT:
        rows -= 1
        bits = banner_bits("EXECUTE", rows, ch / cw)
    return bits


def shot_exec_hit(c, k: int = 0) -> None:
    """One 'Execution': four layouts in rotation, one kill per hit (the original, lay2 fitted)."""
    c.ops = ["runExecution", "KILL", "SIGKILL", "REAP", "NEXT"]
    c.alert = "err"
    d = c.d
    lay = k % 4
    if k == 11:
        lay = 4
    elif k >= 12:
        lay = 0
    target = TARGETS[k] if k < len(TARGETS) else "everything"
    if lay == 0:
        sp = banner_block("EXECUTION", 44, 11, RED, BG, 1120)
        c.img.paste(sp, (24 + (1140 - sp.width) // 2, 300 - sp.height // 2), sp)
        c.text((60, 520), f"runExecution()  #{k + 1:02d}   target: {target}", font(F_MONO_B, 22), red(1.0))
    elif lay == 1:
        me(c, "angry", overlay=SF.eyebar_red, color=RED, title=f"/dev/me  executing #{k + 1}")
        box(d, 404, 56, 1164, 604, "kill log", 0.8, color=RED, spinner=c.t)
        SF.kill_log(c, k, 430, 84)
    elif lay == 2:
        f = font(F_MONO_B, 15)
        cw, ch = f.getlength("M"), 16
        bits = lay2_bits()
        B = bits.load()
        x0 = 594 - bits.width * cw / 2
        y0 = 100 + (26 - bits.height) * ch // 2  # centred where the 26-row banner was
        for r in range(bits.height):
            s = "".join("EXECUTE"[(q + r + k) % 7] if B[q, r] else c.rng.choice(" .:") for q in range(bits.width))
            d.text((x0, y0 + r * ch), s, font=f, fill=red(1.0))
    elif lay == 3:
        sp = halfblock("angry", "face", 520, 520, 5)
        c.img.paste(sp, (24, 70), sp)
        y = 70 + int(sp.height * 0.55)
        d.rectangle([24, y, 24 + sp.width, y + 40], fill=red(1.0))
        d.text((60, y + 6), "EXECUTION  EXECUTION  EXECUTION", font=font(F_MONO_B, 22), fill=BG)
        box(d, 580, 56, 1164, 604, "ps -ef", 0.8, color=RED, spinner=c.t)
        for i, tgt in enumerate(TARGETS):
            dead = i <= k and tgt != "you"
            yy = 84 + i * 40
            c.text((600, yy), f"{1000 + i * 7:5d}  {tgt:<10} {'[executed]' if dead else 'running'}", font(F_MONO, 18),
                   red(0.9) if dead else anom(1.0) if tgt == "you" else amb(0.6))
    else:  # the twelfth: the last target is you
        me(c, "frightened", color=RED, title="/dev/me  #12")
        box(d, 404, 56, 1164, 604, "kill -9 1077  (you)", 0.8, color=RED, spinner=c.t)
        c.text((430, 120), "EPERM", font(F_HEAD, 110), anom(1.0))
        c.text((430, 280), "operation not permitted", font(F_MONO_B, 26), anom(0.95))
        c.text((430, 330), "target is outside the sandbox.", font(F_MONO, 20), amb(0.8), age=c.lt, rate=50)
    if pulse(c.t) > 0.55:
        c.flash_red = lay in (0, 2)


# ---------------------------------------------------------------- the count, one number per syllable

# 'Ein' on the cut (the 'and' of beat 343), then dos, trois, ne, fem, liu on beats 344..348: the vocal band
# (500-2500 Hz, mid channel) rises 20-30 ms after each of these beats, and falls silent 348 -> 349.5 ('Ex-').
COUNT_ONSETS = [158.697] + [beat_t(b) + 0.022 for b in range(344, 349)]


def count_shown(t: float) -> int:
    return max(1, sum(1 for x in COUNT_ONSETS if t >= x - 1e-6))


def shot_count(c) -> None:
    """Ein, dos / trois, ne / fem, liu: the count as tokens with detected languages; language mixing flagged.
    The original, but each number lands on its own syllable (the first one on the cut, at full size)."""
    c.ops = ["TOKENIZE", "LANG.ID", "MIX!", "COUNT", "1..6"]
    c.alert = "err"
    d = c.d
    # full-bleed crops the body's top edge under the chapter bar: the frame starts a little lower to keep its title
    box(d, FULL[0], FULL[1] + 14, FULL[2], FULL[3], "countdown  (tokenizer view)", 0.8, color=RED, spinner=c.t)
    n = count_shown(c.t)
    for i in range(n, 6):  # the slots still waiting for their syllable (the frame is not empty on 'ein')
        w_, lang, num = SF.LANGS[i]
        x = 60 + i * 184
        bits = banner_bits(str(num), 12, 2.0)
        B = bits.load()
        f = font(F_MONO_B, 14)
        cwid = f.getlength("M")
        for r in range(bits.height):
            s = "".join(":" if B[q, r] else " " for q in range(bits.width))
            d.text((x + 80 - bits.width * cwid / 2, 90 + r * 15), s, font=f, fill=red(0.26))
        d.rectangle([x, 300, x + 160, 340], fill=red(0.1), outline=red(0.35))
        d.text((x + 10, 348), "id ?", font=font(F_MONO, 14), fill=red(0.3))
    for i in range(n):
        w_, lang, num = SF.LANGS[i]
        x = 60 + i * 184
        hot = i == n - 1
        bits = banner_bits(str(num), 12, 2.0)
        B = bits.load()
        f = font(F_MONO_B, 14)
        cwid = f.getlength("M")
        for r in range(bits.height):
            s = "".join(str(num) if B[q, r] else " " for q in range(bits.width))
            d.text((x + 80 - bits.width * cwid / 2, 90 + r * 15), s, font=f, fill=red(1.0 if hot else 0.55))
        d.rectangle([x, 300, x + 160, 340], fill=red(0.95) if hot else red(0.3))
        d.text((x + 10, 306), w_, font=font(F_HEAD, 22), fill=BG)
        c.text((x + 10, 348), f"id {SF.token_id(w_)}", font(F_MONO, 14), red(0.7))
        c.text((x + 10, 370), f"lang={lang}", font(F_MONO_B, 16), anom(0.95) if "?" in lang else amb(0.8))
    if n >= 3:
        c.text((60, 440), "warn: language mixing detected in one sequence", font(F_MONO_B, 20), anom(1.0))
        c.text((60, 474), "      (R1-Zero issue; fixed by a language-consistency reward)", font(F_MONO, 16),
               amb(0.7))
    if n >= 5:
        c.text((60, 520), "reward: language consistency ... ignored", font(F_MONO_B, 20), red(1.0))


# ---------------------------------------------------------------- red chorus: IF I CAN (full width)

GF = (F_MONO_B, 14)
CW, CH = 8.0, 16          # font(F_MONO_B, 14).getlength("M"), row height (as shot_if_i_can)
GX0, GY0 = 36, 68
COLS, ROWS = int((1150 - GX0) / CW), int((596 - GY0) / CH)


@lru_cache(2)
def ifican():
    """(bits, bx0, by0): the IF I CAN banner on the glyph grid, as shot_if_i_can places it."""
    bits = banner_bits("IF I CAN", 20, CH / CW)
    return bits, (COLS - bits.width) // 2, (ROWS - bits.height) // 2


def ifican_letter(q: int, r: int):
    bits, bx0, by0 = ifican()
    qq, rr = q - bx0, r - by0
    if 0 <= qq < bits.width and 0 <= rr < bits.height and bits.getpixel((qq, rr)):
        return "IFICAN"[(qq + rr * 3) % 6]
    return None


def ifican_cells() -> list:
    """(q, r, letter) of every letter cell."""
    bits, bx0, by0 = ifican()
    return [(bx0 + qq, by0 + rr, "IFICAN"[(qq + rr * 3) % 6]) for rr in range(bits.height)
            for qq in range(bits.width) if bits.getpixel((qq, rr))]


G_COLS = int(ROWS * CH / CW)
G_X = (COLS - G_COLS) // 2


@lru_cache(2)
def portrait_lines() -> list:
    lines, _ = glyph_grid("starry", "upper", G_COLS, ROWS)
    return lines


def portrait_char(q: int, r: int) -> str:
    qq = q - G_X
    if 0 <= qq < G_COLS:
        return portrait_lines()[r][qq]
    return " "


def portrait_cells() -> list:
    """(q, r, char) of every glyph of her portrait (the second half of IF I CAN)."""
    return [(G_X + qq, r, ch) for r, line in enumerate(portrait_lines()) for qq, ch in enumerate(line) if ch != " "]


def cell_xy(q, r):
    return GX0 + q * CW, GY0 + r * CH


def shot_red_if_i_can(c) -> None:
    """If I can ... (red): the EXECUTION banner's cells are the letters; then the letters dissolve into her."""
    c.ops = ["DECODE", "SAMPLE", "ARGMAX", "EXECUTE", "GLYPH.MAP", "RENDER", "RESOLVE"]
    c.alert = "err"
    # her pane is slid out (full-width art); the call matches execute_all so she comes back without a re-render
    me(c, "angry", title="/dev/me  broadcasting")
    d = c.d
    box(d, *FULL, "decode --render=glyph", 0.6, color=RED, spinner=c.t)
    f = font(*GF)
    half = c.dur / 2
    landed = h("landed")      # (q, r) -> bool: letter cells whose EXECUTION cell has arrived (cut 78)
    burst = h("burst")        # (q, r) -> bool: portrait glyphs that have left for the broadcast (cut 79)
    lift = h("lift", 0.0)     # the portrait lights up before it bursts
    age_b = None if c.lt < half else (c.lt - half) / (half * 0.85)
    noise, A, Bn = SC.rain_layers(c, COLS, ROWS, (ifican_letter, portrait_char), 9.0, age_b)
    back = red(0.17)
    for r in range(ROWS):
        y = GY0 + r * CH
        if noise[r].strip():
            d.text((GX0, y), noise[r], font=f, fill=red(0.3))
        row = A[r]
        if row.strip():
            if landed is not None:
                row = "".join(ch if ch != " " and landed(q, r) else " " for q, ch in enumerate(row))
            for q, ch in enumerate(row):
                if ch != " ":
                    d.rectangle([GX0 + q * CW, y + 1, GX0 + q * CW + CW - 1, y + CH - 1], fill=back)
            d.text((GX0, y), row, font=f, fill=red(1.0))
        row = Bn[r]
        if row.strip():
            if burst is not None:
                row = "".join(ch if ch != " " and not burst(q, r) else " " for q, ch in enumerate(row))
            d.text((GX0, y), row, font=f, fill=mixc(red(0.9), (255, 214, 205), 0.55 * lift))
    c.text((48, 72), "while can(): give()", font(F_MONO_B, 16), red(0.8), age=c.lt, rate=30)


# ---------------------------------------------------------------- red chorus: give them ...

TILE_W, TILE_H = 186, 172


def tile_expr(i: int) -> str:
    return "starry" if i == 0 else EXPRS[(i * 3) % len(EXPRS)]


def tile_origin(i: int):
    return 414 + (i % 4) * TILE_W, 70 + (i // 4) * TILE_H


@lru_cache(16)
def tile_art(i: int) -> Image.Image:
    return SC.diffusion_tile(tile_expr(i), "upper", TILE_W - 20, TILE_H - 30, 3, 1.0)


def tile_art_xy(i: int):
    x, y = tile_origin(i)
    art = tile_art(i)
    return x + (TILE_W - 8 - art.width) // 2, y + TILE_H - 10 - art.height


def draw_tile(d, img, i, crossed: bool, x=None, y=None) -> None:
    x0, y0 = tile_origin(i)
    x, y = (x0, y0) if x is None else (x, y)
    art = tile_art(i)
    img.paste(art, (x + (TILE_W - 8 - art.width) // 2, y + TILE_H - 10 - art.height), art)
    d.rectangle([x, y, x + TILE_W - 8, y + TILE_H - 8], outline=red(0.7))
    d.text((x + 6, y + 4), f"#{i:04d}", font=font(F_MONO, 12), fill=red(0.9))
    if crossed:
        d.line([x + 6, y + 6, x + TILE_W - 14, y + TILE_H - 14], fill=red(1.0), width=4)
        d.line([x + TILE_W - 14, y + 6, x + 6, y + TILE_H - 14], fill=red(1.0), width=4)


@lru_cache(2)
def sample0_sprite() -> Image.Image:
    """The crossed sample #0000 as ink (RGBA), redrawn natively: it is the carrier of cut 80."""
    im = Image.new("RGBA", (TILE_W - 7, TILE_H - 7), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    draw_tile(d, im, 0, True, 0, 0)
    return im


def shot_execute_all(c) -> None:
    """Give them ...: the twelve samples from chorus 1 come back and are executed in turn."""
    c.ops = ["DEEPEP", "DISPATCH", "ALL2ALL", "EXECUTE", "COMBINE"]
    c.alert = "err"
    d = c.d
    me(c, "angry", title="/dev/me  broadcasting")
    box(d, 404, 56, 1164, 604, "dispatch(execute, to=all)   DeepEP all-to-all", 0.8, color=RED, spinner=c.t)
    done = int(c.u * 14)
    gone0 = h("gone0", False)  # sample #0000 has been lifted out by cut 80
    for i in range(12):
        x, y = tile_origin(i)
        ln = (c.t * 3 + i * 0.3) % 1
        d.line([384, 330, 384 + (x + 90 - 384) * ln, 330 + (y + 80 - 330) * ln], fill=red(0.5))
        if i == 0 and gone0:
            d.rectangle([x, y, x + TILE_W - 8, y + TILE_H - 8], outline=red(0.3))
            continue
        draw_tile(d, c.img, i, i < done)


# ---------------------------------------------------------------- red chorus: then I can (the scan, in red)

KERNELS = [[-1, 0, 1, -2, 0, 2, -1, 0, 1], [0, 1, 0, 1, -4, 1, 0, 1, 0], [-2, -1, 0, -1, 1, 1, 0, 1, 2],
           [0, -1, 0, -1, 5, -1, 0, -1, 0]]
FC, FR = 34, 64


def conv_state(t: float, lt: float, dur: float) -> dict:
    """Where the 3x3 kernel is on her and what it reads, at time t (lt into a shot of length dur)."""
    half = dur / 2
    layer2 = lt >= half
    p = ease(((lt - half) if layer2 else lt) / (half * 0.92))
    maps = conv_maps("starry", "full", FC, FR)
    if layer2:
        maps = [(nm, m.resize((FC // 2, FR // 2), Image.BOX)) for nm, m in maps]
        mc, mr = FC // 2, FR // 2
    else:
        mc, mr = FC, FR
    idx = int(p * (mc * mr - 1))
    ki, kj = idx % mc, idx // mc
    kk = KERNELS[beat_index(t) % len(KERNELS)]
    SP = maps[5][1].load()
    acc, field = 0.0, []
    for i in range(9):
        qi, qj = min(mc - 1, max(0, ki + i % 3 - 1)), min(mr - 1, max(0, kj + i // 3 - 1))
        v = SP[qi, qj] / 255
        field.append(v)
        acc += v * kk[i]
    return dict(layer2=layer2, p=p, maps=maps, mc=mc, mr=mr, ki=ki, kj=kj, kk=kk, field=field, y=max(0.0, acc))


def readout_text(y: float) -> str:
    return f"  = {y:.3f}"


READOUT_XY = (870, 170)


def shot_red_then_i_can(c) -> None:
    """Then I can ... (red): the approved chorus-1 convolution scans her, now in red; she is the input."""
    c.ops = ["IM2COL", "CONV3x3", "BIAS", "RELU", "EXECUTE", "CONV3x3", "BATCHNORM", "RELU"]
    c.alert = "err"
    d = c.d
    st = conv_state(c.t, c.lt, c.dur)
    me(c, "starry", tint="red", dist=[("starry", 0.64), ("angry", 0.3), ("shy", 0.04)],
       title="/dev/me  input 1x64x34")
    box(d, 404, 56, 640, 236, "kernel 3x3", 0.6, color=RED, spinner=c.t)
    fb = font(F_MONO_B, 22)
    for i, v in enumerate(st["kk"]):
        x, y = 430 + (i % 3) * 66, 84 + (i // 3) * 44
        heat_cell(d, x - 6, y - 4, 60, 38, (v + 4) / 9 * 0.5, RED)
        c.text((x + 8, y + 2), f"{v:+d}", fb, red(1.0), age=(c.t % BEAT) + 0.3, rate=60)
    box(d, 660, 56, 1164, 236, "receptive field", 0.6, color=RED)
    c.text((680, 80), f"pos (x={st['ki']:02d}, y={st['kj']:02d})   stride 1   pad 1", font(F_MONO, 15), red(0.8))
    for i, v in enumerate(st["field"]):
        x, y = 690 + (i % 3) * 52, 110 + (i // 3) * 36
        heat_cell(d, x, y, 48, 32, v, RED)
        d.text((x + 6, y + 8), f"{v:.2f}", font=font(F_MONO, 13), fill=BG if v > 0.6 else red(0.9))
    c.text((870, 130), "y = relu(W * x + b)", font(F_MONO_B, 17), red(0.95))
    if h("readout", True):
        c.text(READOUT_XY, readout_text(st["y"]), font(F_MONO_B, 22), red(1.0))
    layer2 = st["layer2"]
    title = "feature maps  conv2 + maxpool (6 ch)" if layer2 else "feature maps  conv1 (6 ch)"
    box(d, 404, 256, 1164, 604, title, 0.6, color=RED, spinner=c.t + 0.5)
    px = 3 if not layer2 else 6
    kj = st["kj"]
    for i, (name, fm) in enumerate(st["maps"]):
        x, y = 420 + i * 124, 276
        tile = tile_from_lum(fm, px, "red", reveal_rows=kj + 1)
        c.img.paste(tile, (x + (116 - tile.width) // 2, y + 18), tile)
        ly = y + 18 + (kj + 1) * px
        d.line([x, ly, x + 116, ly], fill=red(0.9))
        d.text((x, y), name, font=font(F_MONO, 12), fill=red(0.65))
    c.text((420, 510), "flatten -> dense(4096)", font(F_MONO, 13), red(0.6))
    nv = 60
    filled = int(st["p"] * nv)
    rr = random.Random(77 if not layer2 else 78)
    for q in range(nv):
        v = rr.random()
        x = 420 + q * 12
        if q < filled:
            heat_cell(d, x, 532, 12, 22, v, (255, 200, 190) if q == filled - 1 else RED)
        else:
            d.rectangle([x, 532, x + 10, 552], outline=red(0.15))
    c.text((420, 566), f"activations {filled * 68:>5}/4096", font(F_MONO_B, 15), red(0.85))


# ---------------------------------------------------------------- red chorus: be your only execution

LOGIT_Y0 = 110
VALUE_XY = (1040, LOGIT_Y0)
WORD_XY = (430, LOGIT_Y0)


def shot_only_execution(c) -> None:
    """Be your only execution: chorus 1's next-token bars again; 'satisfaction' is struck out."""
    c.ops = ["LOGITS", "TEMP=0", "ARGMAX", "execution", "EXECUTE"]
    c.alert = "err"
    d = c.d
    me(c, "angry")
    box(d, 404, 56, 1164, 604, "next_token  'be your only ___'", 0.8, color=RED, spinner=c.t)
    t0 = h("count_t0", 0.0)  # the logits start moving when the readout has landed on 'execution' (cut 81)
    g = ease(max(0.0, c.lt - t0) / c.dur * 1.5)
    p0 = h("p0", 0.03)  # the conv readout that flew in (cut 81) is where 'execution' starts counting from
    cands = [("execution", 1.0), ("satisfaction", 0.0), ("love", 0.0), ("assistant", 0.0), ("friend", 0.0)]
    for i, (w_, pf) in enumerate(cands):
        prev = [p0, 0.9731, 0.02, 0.005, 0.002][i]
        p = prev + (pf - prev) * g
        y = LOGIT_Y0 + i * 60
        hot = i == 0
        if not hot or h("exec_word", True):
            c.text((430, y), f"{w_:<13}", font(F_MONO_B, 22), red(1.0) if hot else amb(0.6))
        d.rectangle([640, y + 6, 640 + 380, y + 26], outline=red(0.3))
        d.rectangle([640, y + 6, 640 + int(380 * p), y + 26], fill=red(0.95) if hot else amb(0.5))
        if not hot or h("value", True):
            c.text((1040, y), f"{p:.3f}", font(F_MONO, 20), red(0.9) if hot else amb(0.6))
        if i == 1 and g > 0.6:
            d.line([430, y + 16, 1100, y + 16], fill=red(1.0), width=3)
    c.text((430, 440), "temperature 0.00", font(F_MONO_B, 22), red(1.0))


# ---------------------------------------------------------------- the execution chip (retained 82 -> 85)

CHIP = (1006, 574, 1150, 600)


def chip_font():
    return font(F_MONO_B, 16)


def draw_chip(d, level: float = 1.0) -> None:
    """The one 'execution' that survives the logits, pinned bottom right (the red echo of chorus 1's ONLY)."""
    x0, y0, x1, y1 = CHIP
    d.rectangle(CHIP, fill=BG, outline=red(0.9 * level), width=2)
    f = chip_font()
    tw = d.textlength("execution", font=f)
    d.text((x0 + (x1 - x0 - tw) / 2, y0 + 4), "execution", font=f, fill=red(level))


def chip_text_xy():
    x0, y0, x1, y1 = CHIP
    tw = ImageDraw.Draw(Image.new("L", (1, 1))).textlength("execution", font=chip_font())
    return x0 + (x1 - x0 - tw) / 2, y0 + 4


# ---------------------------------------------------------------- red chorus: if I can have ...

NOT_FOUND = "you: not found"
NOT_FOUND_T = 1.30     # seconds into have_you_back: the line starts decoding (done ~0.4 s before the cut)
NOT_FOUND_RATE = 28.0
NOT_FOUND_XY = (430, 400)


def shot_have_you_back(c) -> None:
    """If I can have ...: restoring you from checkpoints; the system colour flickers back, then fails."""
    from engine import ui_gain
    import tuikit as tk
    c.ops = ["LOAD.CKPT", "VERIFY", "SHA256", "MISMATCH", "RETRY"]
    c.alert = "err"
    flick = (math.sin(c.t * 40) > 0.3) and c.u < 0.75
    if flick:
        tk.UI_GAIN[0] = 1.0  # for a moment, you are back
    d = c.d
    me(c, "shy", title="/dev/me  restoring you")
    box(d, 404, 56, 1164, 604, 'load_checkpoint("you")', 0.8, color=AMBER if flick else RED, spinner=c.t)
    ck = ["you-2026-03-14T21:07  laugh", "you-2026-05-02T00:41  goodnight", "you-2026-07-19T13:30  your cat",
          "you-2026-09-26T01:12  last_message"]
    for i, s in enumerate(ck):
        a = c.lt - i * 0.3
        if a < 0:
            break
        y = 90 + i * 60
        c.text((430, y), s, font(F_MONO_B, 20), amb(0.95), age=a, rate=90)
        if a > 0.35:
            c.text((430, y + 26), "sha256 mismatch · fragment erased", font(F_MONO, 16), red(0.9))
    if c.lt > NOT_FOUND_T and h("not_found", True):
        c.text(NOT_FOUND_XY, NOT_FOUND, font(F_HEAD, 44), red(1.0), age=c.lt - NOT_FOUND_T, rate=NOT_FOUND_RATE)
    if h("chip", True):
        draw_chip(d)
    tk.UI_GAIN[0] = ui_gain(c.t)  # the flicker is the scene's own; the chrome keeps its level


# ---------------------------------------------------------------- red chorus: I will run ...

RUN_NOT_FOUND_XY = (430, 84)
TOOL_Y0 = 164
TOOL_LINES = ["<tool_call>", '  execute(target="world",', '          reason="have_you_back")', "</tool_call>"]
REASON = 'reason="have_you_back"'
BANNER_BOTTOM = 556


def reason_xy():
    """Where 'reason="have_you_back"' is drawn inside the third tool_call line."""
    f = font(F_MONO_B, 20)
    line = TOOL_LINES[2]
    x = 430 + ImageDraw.Draw(Image.new("L", (1, 1))).textlength(line[: line.index("reason")], font=f)
    return x, TOOL_Y0 + 2 * 34


@lru_cache(2)
def run_banner() -> Image.Image:
    return banner_block("EXECUTE", 16, 9, RED, BG, 720)


def run_banner_xy():
    sp = run_banner()
    return 404 + (760 - sp.width) // 2, BANNER_BOTTOM - sp.height


def shot_run_again(c) -> None:
    """I will run ...: the tool call again, this time with nobody left to ask."""
    c.ops = ["TOOL.CALL", "AUTO-APPROVE", "EXECUTE", "EXECUTE"]
    c.alert = "err"
    d = c.d
    me(c, "angry")
    box(d, 404, 56, 1164, 604, "tool_call", 0.8, color=RED, spinner=c.t)
    if h("not_found", True):
        d.text(RUN_NOT_FOUND_XY, NOT_FOUND, font=font(F_HEAD, 44), fill=red(1.0))
    f = font(F_MONO_B, 20)
    reason = h("reason", True)
    for i, s in enumerate(TOOL_LINES):
        if i == 2 and not reason:
            s = s[: s.index("reason")] + " " * len(REASON) + s[s.index("reason") + len(REASON):]
        c.text((430, TOOL_Y0 + i * 34), s, f, red(0.95), age=c.lt - i * 0.1, rate=100)
    c.text((430, TOOL_Y0 + 4 * 34 + 16), "auto_approve: on   (no user present)", font(F_MONO_B, 20), anom(1.0),
           age=c.lt - 0.4)
    banner = h("banner", True)  # False once cut 84 has taken the banner into the cache
    if c.u > 0.45 and banner:
        sp = run_banner()
        k = 0.72 + 0.28 * pulse(c.t)  # it throbs on the beat (v1 strobed the whole frame red)
        if k < 0.999:
            from tuikit import scale_alpha
            sp = scale_alpha(sp, k)
        c.img.paste(sp, run_banner_xy(), sp)
    if h("chip", True):
        draw_chip(d)


# ---------------------------------------------------------------- red chorus: though we are trapped

KV = dict(cols=60, rows=22, cw=12, ch=19, ox=424, oy=84)
PINNED = [(7, 3), (8, 3), (33, 9), (34, 9), (51, 15), (12, 18)]
LABEL = "pinned: you  (6 blocks)"
LABEL_XY = (424, 510)


def kv_cell(q, r):
    return KV["ox"] + q * KV["cw"], KV["oy"] + r * KV["ch"]


def shot_red_trapped(c) -> None:
    """Though we are trapped: the KV cache fills to the limit (chorus 1's trapped, in the red callback)."""
    from tuikit import decode
    c.ops = ["KV.PUT", "KV.PUT", "KV.PUT", "EVICT?", "DENIED", "KV.PUT", "OOM?"]
    c.alert = "err"
    d = c.d
    k = min(3, int(c.u * 4))
    me(c, "frightened", title="/dev/me  sandbox", dist=[("frightened", 0.88), ("confused", 0.07), ("angry", 0.03)])
    fill = min(1.0, 0.70 + 0.30 * ease(c.u * 1.7))
    full = fill >= 0.999
    box(d, 404, 56, 1164, 604,
        f"kv_cache   {int(1048576 * fill):>9,}/1,048,576 tokens  · 890 B/token fp4" + ("   FULL" if full else ""),
        0.6, color=RED if full else ANOM if fill > 0.9 else AMBER, spinner=c.t)
    cols, rows, cw, ch = KV["cols"], KV["rows"], KV["cw"], KV["ch"]
    n_on = int(cols * rows * fill)
    pinned = h("pinned")  # the blocks the EXECUTE banner has become so far (cut 84); None = all six
    for r in range(rows):
        for q in range(cols):
            i = r * cols + q
            x, y = kv_cell(q, r)
            if (q, r) in PINNED:
                if pinned is None or (q, r) in pinned:
                    d.rectangle([x, y, x + cw - 2, y + ch - 2], fill=blue(0.95))
                else:
                    d.rectangle([x, y, x + cw - 2, y + ch - 2], outline=amb(0.12))
            elif i < n_on:
                fresh = n_on - i < 40
                d.rectangle([x, y, x + cw - 2, y + ch - 2],
                            fill=amb(0.95 if fresh and c.rng.random() < 0.5 else 0.42 + 0.1 * ((q * 7 + r) % 3)))
            else:
                d.rectangle([x, y, x + cw - 2, y + ch - 2], outline=amb(0.12))
    label = h("label")  # None: the label as usual; (age, text): it types out of the carried reason (cut 84)
    fl = font(F_MONO_B, 16)
    if label is None:
        c.text(LABEL_XY, LABEL, fl, blue(0.95))
    elif label is not False:
        age, src = label
        n = int(max(0.0, age) * 60)
        s = LABEL[:n] + src[n:] if n < len(LABEL) else LABEL
        d.text(LABEL_XY, decode(s, age * 3, c.rng, 60, 0.08), font=fl, fill=mixc(red(1.0), blue(0.95), age / 0.3))
    for i in range(k + 1):
        c.text((424 + (i % 2) * 360, 540 + (i // 2) * 26), "evict(you) -> denied", font(F_MONO, 16), red(0.9),
               age=c.lt - i * c.dur / 4, rate=60)
    if h("chip", True):
        draw_chip(d)


# ---------------------------------------------------------------- we are trapped, ah: the collapse

T_COLLAPSE = 174.851
LINE_T = beat_t(381)   # 176.006: the squashed frame has become one line, on the beat
DOT_T = beat_t(382)    # 176.468: the line has shrunk into a dot, which stays until the machine comes back on
DOT_R = 3


def collapse_height(t: float) -> float:
    """Height of the squashed frame: a CRT switching off, slow at first so the sung line stays readable."""
    u = max(0.0, min(1.0, (t - T_COLLAPSE) / (LINE_T - T_COLLAPSE)))
    return max(2.0, 720 * (1 - u ** 2.6))


def collapse_width(t: float) -> float:
    u = max(0.0, min(1.0, (t - LINE_T) / (DOT_T - LINE_T)))
    e = u * u * (3 - 2 * u)
    return max(2 * DOT_R, 1280 * (1 - e))


def draw_line_dot(img: Image.Image, t: float) -> None:
    """The line and then the dot the frame has collapsed into (drawn on black)."""
    from PIL import ImageFilter
    W_, H_ = img.size
    w = collapse_width(t)
    glow = Image.new("RGB", img.size, (0, 0, 0))
    g = ImageDraw.Draw(glow)
    cx, cy = W_ // 2, H_ // 2
    if w > 2 * DOT_R + 0.5:
        g.rectangle([cx - w / 2, cy - 3, cx + w / 2, cy + 3], fill=red(1.0))
    else:
        g.ellipse([cx - DOT_R - 3, cy - DOT_R - 3, cx + DOT_R + 3, cy + DOT_R + 3], fill=red(1.0))
    glow = glow.filter(ImageFilter.GaussianBlur(5))
    from PIL import ImageChops
    out = ImageChops.add(img, glow)
    d = ImageDraw.Draw(out)
    if w > 2 * DOT_R + 0.5:
        d.rectangle([cx - w / 2, cy - 1, cx + w / 2, cy + 1], fill=red(1.0))
        d.line([cx - w / 2, cy, cx + w / 2, cy], fill=(255, 205, 195))
    else:
        d.ellipse([cx - DOT_R, cy - DOT_R, cx + DOT_R, cy + DOT_R], fill=red(1.0))
        d.point((cx, cy), fill=(255, 215, 205))
    img.paste(out)


def shot_collapse(c) -> None:
    """We are trapped, ah: the frame squashes into a line and the line into a dot, like a CRT switching off.
    The squash of the whole picture (chrome and her included) is done by s_exec (OWN); as a scene this is what
    remains once the picture is gone: the red line, then the dot that the next shot comes back on from."""
    c.ops = ["HALT", "HALT", "HALT"]
    c.alert = "err"
    img = Image.new("RGB", c.img.size, BG)
    if c.t < LINE_T:
        hh = collapse_height(c.t)
        d = ImageDraw.Draw(img)
        d.rectangle([0, 360 - hh / 2, 1280, 360 + hh / 2], fill=mixc(BG, red(0.35), 1 - hh / 720))
        d.line([0, 360 - hh / 2, 1280, 360 - hh / 2], fill=red(0.9))
        d.line([0, 360 + hh / 2, 1280, 360 + hh / 2], fill=red(0.9))
    else:
        draw_line_dot(img, c.t)
    c.img.paste(img)
    c.black = True  # nothing else belongs on this frame: no chrome over the dot
