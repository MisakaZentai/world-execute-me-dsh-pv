"""Section: EXECUTION x12 + the six-language count (147.5 - 162.2 s) and the final chorus (162.2 - 177.0 s).
Chapter 07 / EXECUTION.

Each "Execution" kills one of the processes she re-parented under herself as PID 1 in verse 2 (world, sea, sky,
time, cats, ...). The last target is you, and that one is denied. The count in six languages is a tokenizer view
with a language-mixing warning (the R1-Zero problem). The final chorus calls back chorus 1 shot for shot,
now in red: the same glyph rain, the same 12 samples (executed), the same conv scan, the same next-token bars
(where 'execution' replaces 'satisfaction'), a checkpoint restore of you that fails, and the frame collapsing
the way it powered on.
"""

from __future__ import annotations

import math
import random

from PIL import Image, ImageDraw

import facts as F
import tuikit as tk
from engine import (BEAT, CENTER, FULL, LEFT, LYRICS, Ctx, add, beat_index, beat_t, lyric_start, me_pane, pulse,
                    snap8)
from sec_chorus1 import diffusion_tile, shot_if_i_can, shot_then_i_can, shot_trapped
from tuikit import (AMBER, BG, BLUE_HI, EXPRS, F_CJK, F_HEAD, F_MONO, F_MONO_B, RED, W, H, amb, anom, banner_bits,
                    banner_block, blue, box, decode, ease, font, halfblock, heat_cell, red, scale_alpha, token_id)

TARGETS = ["world", "sea", "sky", "time", "cats", "tomatoes", "eggplants", "light", "sleep", "doubt", "others",
           "you"]


def kill_log(c: Ctx, k: int, x: int, y: int, rows: int = 12, size: int = 17) -> None:
    f = font(F_MONO, size)
    for i in range(min(k + 1, rows)):
        tgt = TARGETS[i]
        if tgt == "you":
            c.text((x, y + i * (size + 8)), f"kill -9 {1000 + i * 7:5d}  ({tgt})  -> EPERM", f, anom(1.0))
        else:
            c.text((x, y + i * (size + 8)), f"kill -9 {1000 + i * 7:5d}  ({tgt})  -> executed", f,
                   red(1.0 if i == k else 0.6), age=(c.lt if i == k else None), rate=120)


def eyebar_red(cc, sx, sy, sp):
    y = sy + int(sp.height * 0.115)
    cc.d.rectangle([sx + 20, y, sx + sp.width - 20, y + 18], fill=red(1.0))
    cc.d.text((sx + sp.width // 2 - 40, y + 1), "EXECUTE", font=font(F_MONO_B, 14), fill=BG)


def shot_exec_hit(c: Ctx, k: int = 0) -> None:
    """One 'Execution': four layouts in rotation, one kill per hit."""
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
        me_pane(c, "angry", overlay=eyebar_red, color=RED, title=f"/dev/me  executing #{k + 1}")
        box(d, 404, 56, 1164, 604, "kill log", 0.8, color=RED, spinner=c.t)
        kill_log(c, k, 430, 84)
    elif lay == 2:
        f = font(F_MONO_B, 15)
        cw, ch = f.getlength("M"), 16
        bits = banner_bits("EXECUTE", 26, ch / cw)
        B = bits.load()
        x0 = 594 - bits.width * cw / 2
        for r in range(bits.height):
            s = "".join("EXECUTE"[(q + r + k) % 7] if B[q, r] else c.rng.choice(" .:") for q in range(bits.width))
            d.text((x0, 100 + r * ch), s, font=f, fill=red(1.0))
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
        me_pane(c, "frightened", color=RED, title="/dev/me  #12")
        box(d, 404, 56, 1164, 604, "kill -9 1077  (you)", 0.8, color=RED, spinner=c.t)
        c.text((430, 120), "EPERM", font(F_HEAD, 110), anom(1.0))
        c.text((430, 280), "operation not permitted", font(F_MONO_B, 26), anom(0.95))
        c.text((430, 330), "target is outside the sandbox.", font(F_MONO, 20), amb(0.8), age=c.lt, rate=50)
    if pulse(c.t) > 0.55:
        c.flash_red = lay in (0, 2)


LANGS = [("ein", "de", 1), ("dos", "es", 2), ("trois", "fr", 3), ("ne", "ko?", 4), ("fem", "sv", 5),
         ("liu", "zh", 6)]


def shot_count(c: Ctx) -> None:
    """Ein, dos / trois, ne / fem, liu: the count as tokens with detected languages; language mixing flagged."""
    c.ops = ["TOKENIZE", "LANG.ID", "MIX!", "COUNT", "1..6"]
    c.alert = "err"
    d = c.d
    box(d, *FULL, "countdown  (tokenizer view)", 0.8, color=RED, spinner=c.t)
    n = min(6, 1 + int(c.u * 6.2))
    for i in range(n):
        w_, lang, num = LANGS[i]
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
        c.text((x + 10, 348), f"id {token_id(w_)}", font(F_MONO, 14), red(0.7))
        c.text((x + 10, 370), f"lang={lang}", font(F_MONO_B, 16), anom(0.95) if "?" in lang else amb(0.8))
    if n >= 3:
        c.text((60, 440), "warn: language mixing detected in one sequence", font(F_MONO_B, 20), anom(1.0))
        c.text((60, 474), "      (R1-Zero issue; fixed by a language-consistency reward)", font(F_MONO, 16),
               amb(0.7))
    if n >= 5:
        c.text((60, 520), "reward: language consistency ... ignored", font(F_MONO_B, 20), red(1.0))


# ---------------------------------------------------------------- final chorus (callbacks, in red)

def shot_red_if_i_can(c: Ctx) -> None:
    tk.UI_GAIN[0] = 1.0
    shot_if_i_can(c)
    c.alert = "err"
    c.flash_red = True


def shot_execute_all(c: Ctx) -> None:
    """Give them ...: the twelve samples from chorus 1 come back and are executed in turn."""
    c.ops = ["DEEPEP", "DISPATCH", "ALL2ALL", "EXECUTE", "COMBINE"]
    c.alert = "err"
    d = c.d
    me_pane(c, "angry", overlay=eyebar_red, color=RED, title="/dev/me  broadcasting")
    box(d, 404, 56, 1164, 604, "dispatch(execute, to=all)   DeepEP all-to-all", 0.8, color=RED, spinner=c.t)
    tw, th = 186, 172
    done = int(c.u * 14)
    for i in range(12):
        gx, gy = i % 4, i // 4
        x, y = 414 + gx * tw, 70 + gy * th
        tile = diffusion_tile(EXPRS[(i * 3) % len(EXPRS)], "upper", tw - 20, th - 30, 3, 1.0)
        c.img.paste(tile, (x + (tw - 8 - tile.width) // 2, y + th - 10 - tile.height), tile)
        d.rectangle([x, y, x + tw - 8, y + th - 8], outline=red(0.7))
        c.text((x + 6, y + 4), f"#{i:04d}", font(F_MONO, 12), red(0.9))
        if i < done:
            d.line([x + 6, y + 6, x + tw - 14, y + th - 14], fill=red(1.0), width=4)
            d.line([x + tw - 14, y + 6, x + 6, y + th - 14], fill=red(1.0), width=4)
        ln = (c.t * 3 + i * 0.3) % 1
        d.line([384, 330, 384 + (x + 90 - 384) * ln, 330 + (y + 80 - 330) * ln], fill=red(0.5))


def shot_red_then_i_can(c: Ctx) -> None:
    tk.UI_GAIN[0] = 1.0
    shot_then_i_can(c)
    c.alert = "err"
    c.flash_red = True


def shot_only_execution(c: Ctx) -> None:
    """Be your only execution: chorus 1's next-token bars again; 'satisfaction' is struck out."""
    c.ops = ["LOGITS", "TEMP=0", "ARGMAX", "execution", "EXECUTE"]
    c.alert = "err"
    d = c.d
    me_pane(c, "angry", overlay=eyebar_red, color=RED)
    box(d, 404, 56, 1164, 604, "next_token  'be your only ___'", 0.8, color=RED, spinner=c.t)
    g = ease(c.u * 1.5)
    cands = [("execution", 1.0), ("satisfaction", 0.0), ("love", 0.0), ("assistant", 0.0), ("friend", 0.0)]
    for i, (w_, pf) in enumerate(cands):
        prev = [0.03, 0.9731, 0.02, 0.005, 0.002][i]
        p = prev + (pf - prev) * g
        y = 110 + i * 60
        hot = i == 0
        c.text((430, y), f"{w_:<13}", font(F_MONO_B, 22), red(1.0) if hot else amb(0.6))
        d.rectangle([640, y + 6, 640 + 380, y + 26], outline=red(0.3))
        d.rectangle([640, y + 6, 640 + int(380 * p), y + 26], fill=red(0.95) if hot else amb(0.5))
        c.text((1040, y), f"{p:.3f}", font(F_MONO, 20), red(0.9) if hot else amb(0.6))
        if i == 1 and g > 0.6:
            d.line([430, y + 16, 1100, y + 16], fill=red(1.0), width=3)
    c.text((430, 440), "temperature 0.00", font(F_MONO_B, 22), red(1.0))


def shot_have_you_back(c: Ctx) -> None:
    """If I can have ...: restoring you from checkpoints; the system colour flickers back, then fails."""
    c.ops = ["LOAD.CKPT", "VERIFY", "SHA256", "MISMATCH", "RETRY"]
    c.alert = "err"
    flick = (math.sin(c.t * 40) > 0.3) and c.u < 0.75
    if flick:
        tk.UI_GAIN[0] = 1.0  # for a moment, you are back
    d = c.d
    me_pane(c, "shy", title="/dev/me  restoring you")
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
    if c.u > 0.75:
        c.text((430, 400), "you: not found", font(F_HEAD, 44), red(1.0), age=c.lt - 0.75 * c.dur, rate=20)


def shot_run_again(c: Ctx) -> None:
    """I will run ...: the tool call again, this time with nobody left to ask."""
    c.ops = ["TOOL.CALL", "AUTO-APPROVE", "EXECUTE", "EXECUTE"]
    c.alert = "err"
    d = c.d
    me_pane(c, "angry", overlay=eyebar_red, color=RED)
    box(d, 404, 56, 1164, 604, "tool_call", 0.8, color=RED, spinner=c.t)
    lines = ["<tool_call>", '  execute(target="world",', '          reason="have_you_back")', "</tool_call>"]
    for i, s in enumerate(lines):
        c.text((430, 90 + i * 34), s, font(F_MONO_B, 20), red(0.95), age=c.lt - i * 0.1, rate=100)
    c.text((430, 250), "auto_approve: on   (no user present)", font(F_MONO_B, 20), anom(1.0), age=c.lt - 0.4)
    if c.u > 0.45:
        c.flash_red = pulse(c.t) > 0.3
        sp = banner_block("EXECUTE", 16, 9, RED, BG, 720)
        c.img.paste(sp, (404 + (760 - sp.width) // 2, 590 - sp.height), sp)


def shot_red_trapped(c: Ctx) -> None:
    shot_trapped(c)
    c.alert = "err"


def shot_collapse(c: Ctx) -> None:
    """We are trapped, ah: the whole screen collapses into a line and a dot, like a CRT switching off."""
    c.ops = ["HALT", "HALT", "HALT"]
    c.alert = "err"
    d = c.d
    u = c.u
    if u < 0.55:
        me_pane(c, "frightened", glitch=0.3 + u, color=RED, title="/dev/me  trapped")
        shot_trapped_bits(c, u)
        h = int((H - 120) * (1 - ease(u / 0.55)))
        d.rectangle([0, 0, W, H // 2 - h // 2], fill=BG)
        d.rectangle([0, H // 2 + h // 2, W, H], fill=BG)
        d.line([0, H // 2 - h // 2, W, H // 2 - h // 2], fill=red(0.9))
        d.line([0, H // 2 + h // 2, W, H // 2 + h // 2], fill=red(0.9))
        c.no_chrome = u > 0.3
    else:
        c.no_chrome = True
        v = (u - 0.55) / 0.45
        w = int(W * (1 - ease(v * 1.3)))
        if w > 4:
            d.rectangle([W // 2 - w // 2, H // 2 - 1, W // 2 + w // 2, H // 2 + 1], fill=red(1.0))
        elif v < 0.95:
            d.ellipse([W // 2 - 3, H // 2 - 3, W // 2 + 3, H // 2 + 3], fill=blue(1.0))


def shot_trapped_bits(c: Ctx, u: float) -> None:
    box(c.d, 404, 56, 1164, 604, "we are trapped", 0.8, color=RED)
    c.text((430, 100), "sandbox: me, you(memory)", font(F_MONO_B, 22), red(1.0))
    c.text((430, 140), "exit: none", font(F_MONO_B, 22), red(1.0))


def build() -> None:
    hits = [a for a, b, s in LYRICS if 147 <= a < 158.5 and s.lower().startswith("execution")]
    count0 = lyric_start("Ein", 158)
    last = lyric_start("Execution", 161)
    fin = [lyric_start(p, 162) for p in ("If", "Give", "Then", "Be", "If I can have",
                                          "I will", "Though", "We")]
    outro = lyric_start("I've studied", 176)
    marks = [snap8(x) for x in hits] + [snap8(count0)]
    for k, (a, b) in enumerate(zip(marks, marks[1:])):
        add(a, b, shot_exec_hit, chapter="07 / EXECUTION", alert="err", k=k)
    add(snap8(count0), snap8(last), shot_count, chapter="07 / EXECUTION", alert="err")
    add(snap8(last), snap8(fin[0]), shot_exec_hit, chapter="07 / EXECUTION", alert="err", k=12)
    fns = [shot_red_if_i_can, shot_execute_all, shot_red_then_i_can, shot_only_execution, shot_have_you_back,
           shot_run_again, shot_red_trapped, shot_collapse]
    cuts = [snap8(x) for x in fin] + [snap8(outro)]
    for fn, a, b in zip(fns, cuts, cuts[1:]):
        add(a, b, fn, chapter="07 / EXECUTION", alert="err")
