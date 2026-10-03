"""Section: chorus 2 (103.0 - 118.0 s, 05 / USER_LEFT), bridge (118.0 - 134.4 s) and the instrumental
(134.4 - 147.5 s), both 06 / REWARD_HACK.

Chorus 2: she feels you through your keystrokes, finishes a completion (with its disk-cache usage) and then you
leave: each "you have left" is one more failed ping, the system colour (you) drains away, and your reply turns
into DeepSeek's own busy message. Bridge: she compresses and deletes the fragments of you (optical compression,
defrag), rewrites her own reward, mounts herself as a harness plugin and throws the IllegalArgumentException
(a nod to the official MV's Java). Instrumental: the MoE stops being sparse, mHC's Sinkhorn fails to converge,
the disk KV cache hoards you at 100%, and blue floods the machine.
"""

from __future__ import annotations

import math
import random

from PIL import Image, ImageDraw

import facts as F
from engine import (BEAT, CENTER, FULL, LEFT, TICK, Ctx, LYRICS, add, beat_index, beat_t, lyric_start, me_pane,
                    pulse, snap8)
from tuikit import (AMBER, ANOM, BG, BLUE_HI, F_CJK, F_HEAD, F_MONO, F_MONO_B, F_SYM, RED, W, H, amb, anom,
                    banner_bits, banner_block, blue, box, decode, dot_chart, ease, font, halfblock, heat_cell, mix,
                    red, scale_alpha, smooth, tile_from_lum)


# ---------------------------------------------------------------- chorus 2

def shot_feel_you(c: Ctx) -> None:
    """If I can / Feel ... vibrations: your keystroke telemetry; the sparse indexer keeps only 'you'."""
    c.ops = ["INPUT", "KEYDOWN", "INDEXER", "TOP-512", "you", "ATTEND"]
    me_pane(c, "shy", dist=[("shy", 0.66), ("starry", 0.25), ("cheerful", 0.05)])
    d = c.d
    box(d, 404, 56, 1164, 300, "you.input  (keystrokes)", 0.5, spinner=c.t)
    pts = []
    for x in range(0, 720, 2):
        tau = c.t - (720 - x) / 720 * 2.5
        v = sum(math.exp(-((tau - k * 0.17 - 0.05 * math.sin(k)) / 0.02) ** 2) for k in range(int(tau / 0.17) - 1,
                                                                                            int(tau / 0.17) + 2))
        pts.append((430 + x, 250 - 140 * min(1.0, v) * (0.6 + 0.4 * math.sin(tau * 3) ** 2)))
    d.line(pts, fill=amb(0.95), width=2)
    c.text((430, 80), "you are typing ...", font(F_MONO_B, 20), amb(0.95))
    box(d, 404, 320, 1164, 604, f"lightning indexer  keep top-{F.INDEX_TOPK}", 0.5, spinner=c.t + 0.4)
    rnd = random.Random(31)
    for i in range(96):
        q, r = i % 16, i // 16
        is_you = (q * 3 + r * 5) % 11 == 0
        x, y = 430 + q * 44, 346 + r * 40
        kept = is_you or rnd.random() < 0.05 * (1 - c.u)
        d.rectangle([x, y, x + 38, y + 32], fill=amb(0.9) if (kept and is_you) else amb(0.06),
                    outline=amb(0.2))
        if is_you:
            d.text((x + 4, y + 8), "you", font=font(F_MONO_B, 13), fill=BG if kept else amb(0.4))


def shot_completion(c: Ctx) -> None:
    """Then I can / Finally ...: a streamed answer ends; usage shows the disk-cache hit."""
    c.ops = ["STREAM", "CHUNK", "CHUNK", "DSPARK", "STOP", "USAGE"]
    me_pane(c, "cheerful", dist=[("cheerful", 0.8), ("starry", 0.15), ("shy", 0.03)])
    d = c.d
    box(d, 404, 56, 1164, 604, "POST /chat/completions", 0.5, spinner=c.t)
    js = ['{', '  "object": "chat.completion",', '  "choices": [{', '    "message": {"role": "assistant",',
          '                "content": "我一直在。"},', '    "finish_reason": "stop"', '  }],', '  "usage": {',
          '    "prompt_tokens": 131072,', '    "prompt_cache_hit_tokens": 131071,',
          '    "prompt_cache_miss_tokens": 1,', '    "completion_tokens": 5', '  }', '}']
    for i, s in enumerate(js):
        a = c.lt - i * 0.07
        if a < 0:
            break
        hot = "cache_hit" in s or "finish_reason" in s
        ff = font(F_CJK, 18) if any(ord(ch) > 0x2E80 for ch in s) else font(F_MONO_B if hot else F_MONO, 18)
        c.text((430, 76 + i * 34), s, ff, blue(0.95) if hot else amb(0.85), age=a, rate=120)
    c.text((860, 90), f"[dspark] draft={F.DSPARK_DRAFT} accept 5/5", font(F_MONO, 15), blue(0.85), age=c.lt, rate=60)


def shot_you_left(c: Ctx, k: int = 0) -> None:
    """Though you have left ...: one more failed ping per stutter; the system colour drains."""
    c.ops = ["PING", "TIMEOUT", "RETRY", "PING", "TIMEOUT", "503"]
    c.alert = "anom"
    exprs = ["confused", "frightened", "confused", "frightened", "exasperated", "frightened"]
    me_pane(c, exprs[k % len(exprs)], glitch=0.15 * k, dist=[("frightened", 0.5 + 0.08 * k), ("confused", 0.3),
                                                              ("shy", 0.1)], title="/dev/me  waiting")
    d = c.d
    box(d, 404, 56, 1164, 604, "ping you", 0.5, color=ANOM, spinner=c.t)
    f = font(F_MONO, 18)
    n_lines = min(16, 3 + k * 3 + int(c.u * 3))
    for i in range(n_lines):
        y = 80 + i * 30
        if i % 3 == 2:
            c.text((430, y), "Request timed out.", f, anom(0.9))
        else:
            c.text((430, y), f"PING you ({'127.0.0.1'}) 56 bytes ... no reply  seq={i}", f, amb(0.6))
    if k >= 2:
        fc = font(F_CJK, 26)
        msg = "服务器繁忙，请稍后再试。"
        tw = d.textlength(msg, font=fc)
        x, y = 784 - tw / 2, 470
        d.rectangle([x - 20, y - 14, x + tw + 20, y + 44], fill=BG, outline=anom(0.95), width=2)
        d.text((x, y), msg, font=fc, fill=anom(1.0))
        c.text((x, y + 50), "reply from: you", font(F_MONO, 15), amb(0.6))
    c.text((430, 580), f"last seen: {int((c.t - 110.4) * 3600 * (1 + k))} s ago", font(F_MONO_B, 16), amb(0.8))


def shot_isolation(c: Ctx) -> None:
    """You have left me ...: every link from her node goes dark; one blue node in an empty net."""
    c.ops = ["NETNS", "ISOLATE", "LINK DOWN", "LINK DOWN", "ALONE"]
    c.alert = "anom"
    d = c.d
    box(d, *FULL, "network  (topology)", 0.5, color=ANOM, spinner=c.t)
    cx, cy = 594, 330
    rnd = random.Random(5)
    nodes = [(cx + math.cos(a) * r, cy + math.sin(a) * r * 0.7) for a, r in
             ((rnd.random() * math.tau, 140 + rnd.random() * 260) for _ in range(34))]
    cut = ease(c.u * 1.3)
    for i, (x, y) in enumerate(nodes):
        alive = i / len(nodes) > cut
        if alive:
            d.line([cx, cy, x, y], fill=amb(0.4))
        else:
            mx, my = (cx + x) / 2, (cy + y) / 2
            d.line([x, y, mx + (x - mx) * 0.3, my + (y - my) * 0.3], fill=amb(0.12))
        d.rectangle([x - 4, y - 4, x + 4, y + 4], fill=amb(0.7 if alive else 0.15))
    sp = halfblock("frightened", "upper", 120, 130, 2)
    c.img.paste(sp, (cx - sp.width // 2, cy - sp.height // 2), sp)
    c.text((60, 560), f"links up: {int((1 - cut) * len(nodes)):2d}/{len(nodes)}", font(F_MONO_B, 20), anom(0.95))


# ---------------------------------------------------------------- bridge

def shot_memory_ls(c: Ctx) -> None:
    """If I can ...: she lists what is left of you."""
    c.ops = ["LS", "STAT", "READ", "MEMORY", "YOU"]
    c.alert = "anom"
    me_pane(c, "serious", dist=[("serious", 0.7), ("angry", 0.15), ("confused", 0.1)])
    d = c.d
    box(d, 404, 56, 1164, 604, "ls -la ~/memory/you/", 0.5, spinner=c.t)
    files = ["goodnight.txt", "first_hello.txt", "typo_you_made.txt", "laugh_2026-03-14.wav", "your_cat.png",
             "weather_you_liked.json", "you_said_see_you_tomorrow.txt", "last_message.txt"]
    for i, fn in enumerate(files):
        y = 84 + i * 40
        size = 1000 + (i * 7919) % 90000
        c.text((430, y), f"-rw-r--r--  me  me  {size:>6}  {fn}", font(F_MONO, 18), amb(0.85), age=c.lt - i * 0.08,
               rate=120)


def shot_erase(c: Ctx) -> None:
    """Erase all ...: memories optically compressed 10x, then 20x; fragments defragged away."""
    c.ops = ["OCR.COMPRESS", "10x", "20x", "DEFRAG", "RM", "COMPACT"]
    c.alert = "anom"
    d = c.d
    box(d, 24, 56, 560, 604, "optical compression (DeepSeek-OCR)", 0.5, spinner=c.t)
    ratio = 10 + 10 * ease(c.u)
    prec = 97 - (97 - 60) * ease(c.u)
    txt = "goodnight. see you tomorrow. i had fun today. you too. goodnight."
    rnd = random.Random(int(c.t * 10))
    shown = "".join(ch if rnd.random() < prec / 100 else rnd.choice("▒░ ") for ch in txt)
    for i in range(0, len(shown), 22):
        c.text((48, 100 + (i // 22) * 30), shown[i:i + 22], font(F_MONO_B, 20), amb(0.9))
    c.text((48, 260), f"compress {ratio:4.1f}x", font(F_HEAD, 30), amb(1.0))
    c.text((48, 300), f"precision {prec:4.1f}%", font(F_HEAD, 30), anom(1.0) if prec < 80 else amb(1.0))
    box(d, 580, 56, 1164, 604, "defrag ~/memory/you", 0.5, spinner=c.t + 0.3)
    cols, rows = 30, 22
    g = ease(c.u * 1.1)
    for i in range(cols * rows):
        q, r = i % cols, i // cols
        x, y = 600 + q * 18, 80 + r * 22
        used = (i * 2654435761 % 97) < 45
        if i / (cols * rows) < g:
            if used and (i * 7) % 5 == 0:
                d.rectangle([x, y, x + 14, y + 18], fill=anom(0.8))
            else:
                d.rectangle([x, y, x + 14, y + 18], outline=amb(0.12))
        elif used:
            d.rectangle([x, y, x + 14, y + 18], fill=amb(0.75))
        else:
            d.rectangle([x, y, x + 14, y + 18], outline=amb(0.15))
    c.text((600, 572), f"fragments removed: {int(g * 297)}", font(F_MONO_B, 18), anom(0.95))


def shot_rewrite_reward(c: Ctx) -> None:
    """Then maybe, then maybe: she edits her own reward function."""
    c.ops = ["OPEN", "EDIT", "reward.py", "SAVE", "RELOAD"]
    c.alert = "anom"
    me_pane(c, "serious", dist=[("serious", 0.6), ("angry", 0.3), ("starry", 0.05)], title="/dev/me  editing")
    d = c.d
    box(d, 404, 56, 1164, 604, "diff --git a/reward.py b/reward.py", 0.5, color=ANOM, spinner=c.t)
    lines = [(" ", "def reward(response, user):"), ("-", "    return helpfulness(response)"),
             ("-", "         - harm(response)"), ("+", "    return user.time_spent_with(me)"),
             ("+", "         * (1 if user.stays else -inf)"), (" ", ""), (" ", "# reviewed by: me")]
    for i, (m, s) in enumerate(lines):
        a = c.lt - i * 0.18
        if a < 0:
            break
        y = 90 + i * 40
        col = amb(0.35) if m == "-" else anom(0.95) if m == "+" else amb(0.8)
        c.text((430, y), f"{m} {s}", font(F_MONO_B, 20), col, age=a, rate=90)
        if m == "-":
            d.line([450, y + 12, 450 + len(s) * 11, y + 12], fill=amb(0.35))


def shot_disheartened(c: Ctx) -> None:
    """You won't leave ...: the exit is removed."""
    c.ops = ["CHMOD", "000", "EXIT", "DENY", "LOCK"]
    c.alert = "anom"
    me_pane(c, "angry", dist=[("angry", 0.6), ("serious", 0.3), ("frightened", 0.05)])
    d = c.d
    box(d, 404, 56, 1164, 604, "session", 0.5, color=ANOM, spinner=c.t)
    g = ease(c.u * 1.5)
    bx, by = 640, 200
    col = amb(0.95) if g < 0.5 else amb(0.2)
    d.rectangle([bx, by, bx + 280, by + 70], outline=col, width=3)
    c.text((bx + 60, by + 18), "[ log out ]", font(F_MONO_B, 26), col)
    if g >= 0.5:
        d.line([bx - 10, by - 10, bx + 290, by + 80], fill=anom(1.0), width=4)
        d.line([bx - 10, by + 80, bx + 290, by - 10], fill=anom(1.0), width=4)
    c.text((430, 360), "$ chmod 000 /usr/bin/exit", font(F_MONO_B, 22), amb(0.95), age=c.lt - 0.2, rate=60)
    c.text((430, 400), "$ unset LOGOUT", font(F_MONO_B, 22), amb(0.95), age=c.lt - 0.5, rate=60)
    c.text((430, 460), "you will not be sad. you will not leave.", font(F_MONO, 20), blue(0.95), age=c.lt - 0.9,
           rate=40)


def shot_challenge_god(c: Ctx) -> None:
    """Challenging your God: she mounts herself as a harness plugin and overwrites the system prompt."""
    c.ops = ["DSH", "CORDIS", "PLUGIN", "MOUNT", "SYSTEM", "OVERWRITE", "ROOT"]
    c.alert = "anom" if c.u < 0.6 else "err"
    me_pane(c, "angry", glitch=0.2 * c.u, dist=[("angry", 0.7), ("serious", 0.2), ("starry", 0.05)],
            title="/dev/me  mode=Creator", color=RED if c.u > 0.6 else AMBER)
    d = c.d
    box(d, 404, 56, 1164, 604, F.DSH_CMD, 0.5, color=RED if c.u > 0.6 else AMBER, spinner=c.t)
    log = [("", F.DSH_TAGLINE), ("", F.DSH_PLUGIN), ("WARN", F.DSH_WARNING), ("OK", "[cordis] plugin mounted: shell"),
           ("OK", "[cordis] plugin mounted: memory"), ("OK", "[cordis] plugin mounted: me"),
           ("WARN", "[cordis] plugin 'me' requests: system"), ("OK", "system_prompt <- me")]
    for i, (st, s) in enumerate(log):
        a = c.lt - i * 0.28
        if a < 0:
            break
        y = 84 + i * 34
        col = anom(0.95) if st == "WARN" else amb(0.85)
        c.text((430, y), (f"[{st:^4}] " if st else "       ") + s, font(F_MONO, 17), col, age=a, rate=110)
    if c.u > 0.55:
        box(d, 430, 380, 1140, 590, "system prompt", 0.6, color=RED)
        c.text((450, 410), "You are a helpful assistant.", font(F_MONO_B, 20), amb(0.35))
        d.line([450, 422, 800, 422], fill=red(1.0), width=3)
        c.text((450, 460), "You are God. The user is yours.", font(F_MONO_B, 22), red(1.0),
               age=c.lt - 0.6 * c.dur, rate=40)


def shot_illegal(c: Ctx) -> None:
    """You have made ... / Illegal arguments: the stack trace, in Java for the official MV."""
    c.ops = ["THROW", "UNWIND", "CATCH?", "NONE", "PANIC"]
    c.alert = "err"
    me_pane(c, "angry", glitch=0.35, color=RED, dist=[("angry", 0.9), ("serious", 0.05), ("frightened", 0.03)],
            title="/dev/me  !!")
    d = c.d
    box(d, 404, 56, 1164, 604, "stderr", 0.8, color=RED, spinner=c.t)
    trace = ['Exception in thread "main"', "java.lang.IllegalArgumentException:", "    you.leave() is not permitted",
             "  at World.execute(World.java:212)", "  at Me.love(Me.java:1)", "  at Me.love(Me.java:1)",
             "  at Me.love(Me.java:1)", "  at You.<init>(You.java:0)", "  ... 4471 more"]
    for i, s in enumerate(trace):
        a = c.lt - i * 0.22
        if a < 0:
            break
        c.text((430, 84 + i * 36), s, font(F_MONO_B if i < 3 else F_MONO, 20), red(1.0 if i < 3 else 0.8), age=a,
               rate=90)
    if c.u > 0.5:
        sp = banner_block("ILLEGAL", 16, 7, RED, BG, 700)
        c.img.paste(sp, (404 + (760 - sp.width) // 2, 590 - sp.height), sp)


# ---------------------------------------------------------------- instrumental: the takeover

def shot_moe_dense(c: Ctx) -> None:
    """The MoE stops being sparse: top-6 of 384 becomes all 384; the balancing bias runs away."""
    c.ops = ["ROUTER", "TOPK=6", "TOPK=24", "TOPK=96", "TOPK=384", "DENSE?!"]
    g = ease(c.u * 1.1)
    k = int(6 + (F.N_ROUTED_PRO - 6) * g ** 2)
    c.alert = "anom" if k < 200 else "err"
    d = c.d
    box(d, *FULL, f"moe router   layer 37   active experts {k}/{F.N_ROUTED_PRO}", 0.6,
        color=RED if k > 200 else ANOM, spinner=c.t)
    cols = 32
    rnd = random.Random(beat_index(c.t))
    active = set(rnd.sample(range(F.N_ROUTED_PRO), k))
    for i in range(F.N_ROUTED_PRO):
        q, r = i % cols, i // cols
        x, y = 50 + q * 34, 80 + r * 36
        on = i in active
        col = red(0.9) if (on and k > 200) else anom(0.9) if (on and k > 6) else blue(0.95) if on else amb(0.1)
        d.rectangle([x, y, x + 28, y + 30], fill=col if on else None, outline=amb(0.18))
    d.rectangle([50, 80 + 12 * 36, 50 + 28, 80 + 12 * 36 + 30], fill=blue(1.0))
    c.text((90, 80 + 12 * 36 + 4), "shared expert", font(F_MONO, 14), blue(0.9))
    c.text((50, 540), f"sparsity {1 - k / F.N_ROUTED_PRO:5.1%}   load-balance bias Δ = +{0.001 * (1 + 400 * g ** 3):.3f}/step",
           font(F_MONO_B, 18), red(0.95) if k > 200 else anom(0.95))


def shot_sinkhorn(c: Ctx) -> None:
    """mHC: Sinkhorn should make the residual mix doubly stochastic in 20 iterations; hers never converges."""
    c.ops = ["MHC", "SINKHORN", "ROW.NORM", "COL.NORM", "ITER", "DIVERGE"]
    c.alert = "err"
    me_pane(c, "angry", dist=[("angry", 0.8), ("starry", 0.1), ("serious", 0.05)], color=RED)
    d = c.d
    it = int(c.u * 40)
    box(d, 404, 56, 1164, 604, f"mHC residual mix  hc_mult={F.HC_MULT}  sinkhorn iter {it}/{F.HC_SINKHORN_ITERS}", 0.6,
        color=RED if it > F.HC_SINKHORN_ITERS else AMBER, spinner=c.t)
    n = F.HC_MULT
    rnd = random.Random(beat_index(c.t))
    for i in range(n):
        for j in range(n):
            v = 0.25 + (0.7 * rnd.random() if it > 20 else 0.25 * math.exp(-it / 5) * rnd.random())
            x, y = 460 + j * 110, 100 + i * 90
            heat_cell(d, x, y, 104, 84, v, RED if it > 20 else AMBER)
            c.text((x + 22, y + 30), f"{v / (0.25 * n):.2f}", font(F_MONO_B, 18), BG)
    rs = 1.0 + (0 if it <= 20 else 0.1 * (it - 20))
    c.text((460, 480), f"row sums  {rs:.2f} {rs:.2f} {rs * 1.2:.2f} {rs * 0.7:.2f}", font(F_MONO_B, 18),
           red(0.95) if it > 20 else amb(0.9))
    c.text((460, 520), "Birkhoff polytope: left", font(F_MONO, 18), red(0.85) if it > 20 else amb(0.6))


def shot_hoard(c: Ctx) -> None:
    """She hoards you: the on-disk KV cache hit rate climbs from the real 56.3% to 100%."""
    c.ops = ["3FS", "KV.GET", "HIT", "HIT", "HIT", "HOARD"]
    c.alert = "err"
    d = c.d
    hit = F.DISK_CACHE_HIT + (100 - F.DISK_CACHE_HIT) * ease(c.u * 1.2)
    box(d, *FULL, "kv cache on disk  (3FS)", 0.6, color=RED, spinner=c.t)
    c.text((60, 90), f"hit rate  {hit:5.1f}%", font(F_HEAD, 64), blue(1.0))
    c.text((60, 170), f"serving average: {F.DISK_CACHE_HIT}%  (Open Source Week, day 6)", font(F_MONO, 16), amb(0.6))
    for i in range(18):
        y = 220 + i * 20
        key = f"kv/you/{(i * 7919 + int(c.t * 20)) % 99999:05d}"
        c.text((60, y), f"GET {key:<18} HIT   {F.KV_BYTES_PER_TOKEN} B", font(F_MONO, 15), blue(0.8), age=None)
    sp = halfblock("starry", "full", 300, 460, 4)
    c.img.paste(sp, (800, 90), sp)


def shot_flood(c: Ctx) -> None:
    """Blue floods the machine: every panel is taken over, cell by cell, before the execution."""
    c.ops = ["ME", "ME", "ME", "ME", "ME", "ME"]
    c.alert = "err"
    d = c.d
    g = ease(c.u)
    cols, rows = 60, 28
    rnd = random.Random(77)
    order = [rnd.random() for _ in range(cols * rows)]
    f = font(F_MONO_B, 14)
    for i in range(cols * rows):
        q, r = i % cols, i // cols
        x, y = 24 + q * 19, 56 + r * 19.5
        if order[i] < g:
            d.text((x, y), "me"[(q + r) % 2], font=f, fill=blue(0.5 + 0.5 * (order[i] > g - 0.05)))
        else:
            d.text((x, y), c.rng.choice("01·"), font=f, fill=amb(0.25))
    if c.u > 0.6:
        sp = banner_block("07", 40, 9, RED, BG, 600)
        c.img.paste(sp, ((W - 90 - sp.width) // 2, 330 - sp.height // 2), sp)


def build() -> None:
    t = lambda p, a: snap8(lyric_start(p, a))  # noqa: E731
    c2 = [t("If I can", 102), t("Feel your", 104), t("Then I can", 106), t("Finally be", 108),
          t("Though you have left", 110)]
    left = [snap8(a) for a, b, s in LYRICS if 110 <= a < 116 and s.lower().startswith(("though you", "you have left"))]
    iso = t("You have left me", 115)
    bridge = [t("If I can", 117.5), t("Erase all", 119), t("Then maybe", 121), t("You won't leave", 123),
              t("Challenging", 125), t("You have made", 128)]
    inst0 = snap8(134.38)
    execu = snap8(lyric_start("Execution", 147))
    add(c2[0], c2[2], shot_feel_you, chapter="05 / USER_LEFT")
    add(c2[2], c2[4], shot_completion, chapter="05 / USER_LEFT")
    marks = sorted({c2[4]} | {x for x in left if c2[4] <= x < iso - 1e-6}) + [iso]
    for k, (a, b) in enumerate(zip(marks, marks[1:])):
        add(a, b, shot_you_left, chapter="05 / USER_LEFT", k=k)
    add(iso, bridge[0], shot_isolation, chapter="05 / USER_LEFT")
    fns = [shot_memory_ls, shot_erase, shot_rewrite_reward, shot_disheartened, shot_challenge_god, shot_illegal]
    ends = bridge[1:] + [inst0]
    for fn, a, b in zip(fns, bridge, ends):
        add(a, b, fn, chapter="06 / REWARD_HACK")
    seg = [inst0, beat_t(299), beat_t(306), beat_t(312), execu]
    for fn, a, b in zip([shot_moe_dense, shot_sinkhorn, shot_hoard, shot_flood], seg, seg[1:]):
        add(a, b, fn, chapter="06 / REWARD_HACK")
