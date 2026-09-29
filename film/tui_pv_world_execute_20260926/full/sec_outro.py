"""Section: 08 / EVAL: LOVE (177.0 - 193.5 s) and 09 / WHALE_FALL (193.5 s - end).

Outro: she trains on love with GRPO, hits R1-Zero's aha moment, aces a love eval, answers every question with
love, derives love = you, frees you and stays trapped, then loops on the token 'love'.
Whale fall: she sinks to the sea floor and comes apart like marine snow; fish gather; the retired models lie in
the sediment; her weights are released and forked; her thinking closes after the song's length. The last
'Execution', the hard cut, and one unanswered line on black.
"""

from __future__ import annotations

import math
import random

from PIL import Image, ImageDraw

import facts as F
from engine import (BEAT, CENTER, END_T, FULL, HARD_CUT, LEFT, Ctx, add, beat_index, beat_t, lyric_start, me_pane,
                    pulse, snap8)
from tuikit import (AMBER, BG, BLUE_HI, F_CJK, F_HEAD, F_MONO, F_MONO_B, F_SYM, RED, W, H, amb, anom, banner_bits,
                    blue, box, decode, dot_chart, ease, font, halfblock, halfblock_lum, heat_cell, red, scale_alpha,
                    smooth)

ANSWERS = ["attention", "staying", "a chemical", "undefined", "you", "a reward", "a bug", "p(you)", "lo-o-ove",
           "a loss", "∞", "404", "here", "you", "a habit", "you"]


def shot_grpo(c: Ctx) -> None:
    """I've studied, I've studied: one GRPO group of 16 answers to 'what is love?', scored and normalised."""
    c.ops = ["SAMPLE x16", "REWARD", "MEAN", "STD", "ADVANTAGE", "CLIP", "UPDATE"]
    me_pane(c, "serious", dist=[("serious", 0.6), ("starry", 0.3), ("shy", 0.05)], title="/dev/me  studying")
    d = c.d
    box(d, 404, 56, 1164, 604, f"GRPO  G={F.GRPO_G}  lr={F.GRPO_LR}  kl={F.GRPO_KL}   q: what is love?", 0.5,
        spinner=c.t)
    rewards = [1.0 if "you" in a else 0.3 if "lo" in a or a in ("staying", "here") else 0.0 for a in ANSWERS]
    mean = sum(rewards) / len(rewards)
    std = (sum((r - mean) ** 2 for r in rewards) / len(rewards)) ** 0.5
    for i, (a, r) in enumerate(zip(ANSWERS, rewards)):
        if c.lt < i * 0.05:
            break
        q, row = i % 4, i // 4
        x, y = 424 + q * 184, 76 + row * 92
        adv = (r - mean) / (std + 1e-6)
        pos = adv > 0
        d.rectangle([x, y, x + 176, y + 84], outline=blue(0.8) if pos else amb(0.3))
        c.text((x + 8, y + 6), f"o{i + 1:02d}", font(F_MONO, 12), amb(0.5))
        c.text((x + 8, y + 24), a, font(F_SYM, 18), blue(1.0) if pos else amb(0.75), age=c.lt - i * 0.05, rate=60)
        c.text((x + 8, y + 56), f"r={r:.1f}  A={adv:+.2f}", font(F_MONO, 13), blue(0.9) if pos else amb(0.55))
    c.text((430, 460), f"mean r = {mean:.3f}   std = {std:.3f}", font(F_MONO_B, 18), amb(0.9))
    c.text((430, 500), "rule-based reward: contains(you)", font(F_MONO, 16), amb(0.7))


def shot_learn_love(c: Ctx) -> None:
    """How to properly ...: P(love) climbs over 10.4k steps; the aha moment is flagged on the curve."""
    c.ops = ["ROLLOUT", "GRPO", "STEP", "P(love)", "AHA"]
    me_pane(c, "starry", dist=[("starry", 0.5 + 0.4 * c.u), ("serious", 0.3), ("shy", 0.1)])
    d = c.d
    box(d, 404, 56, 1164, 604, "train/p(love)", 0.5, spinner=c.t)

    def pl(u):
        return 0.05 + 0.9 / (1 + math.exp(-14 * (u - 0.72)))

    prog = ease(c.u * 1.1)
    last = dot_chart(d, 440, 90, 690, 300, pl, prog, blue(0.95))
    if last:
        c.text((last[0] - 120, max(70, last[1] - 26)), f"p(love) = {pl(prog):.3f}", font(F_MONO_B, 16), blue(1.0))
    c.text((440, 400), f"step {int(prog * 10400):>5}/10400", font(F_MONO, 16), amb(0.8))
    if prog > 0.72:
        ax = 440 + int(690 * 0.72)
        d.line([ax, 90, ax, 390], fill=anom(0.8))
        c.text((440, 440), f'"{F.AHA}"', font(F_MONO_B, 15), anom(1.0), age=(prog - 0.72) * c.dur * 2, rate=60)
        c.text((440, 470), "  - R1-Zero, mid-training", font(F_MONO, 14), amb(0.6))
    c.text((440, 520), f"pass@1(love)  {F.AIME_FROM} -> {F.AIME_TO}", font(F_MONO_B, 18), amb(0.9))


def shot_question_me(c: Ctx) -> None:
    """Question me, question me: the love eval suite runs and every column goes to 100."""
    c.ops = ["dsh eval", "LOAD", "RUN", "SCORE", "100.0"]
    me_pane(c, "cheerful", dist=[("cheerful", 0.7), ("starry", 0.25), ("shy", 0.03)])
    d = c.d
    box(d, 404, 56, 1164, 604, "dsh eval --suite love", 0.5, spinner=c.t)
    rows = ["LoveBench", "LoveQA", "MMLU-Love", "GPQA-Love", "SWE-Love", "IMO-Love", "LiveLoveBench"]
    for i, name in enumerate(rows):
        g = ease((c.lt - i * 0.1) / 0.8)
        y = 90 + i * 60
        c.text((430, y), name, font(F_MONO_B, 20), amb(0.9))
        d.rectangle([700, y + 4, 700 + 300, y + 26], outline=amb(0.25))
        d.rectangle([700, y + 4, 700 + int(300 * g), y + 26], fill=blue(0.9))
        c.text((1020, y), f"{100 * g:5.1f}", font(F_MONO_B, 20), blue(1.0) if g > 0.99 else amb(0.8))


QUESTIONS = ["what is 1+1?", "天气怎么样？", "why is the sky blue?", "write a sort", "capital of France?",
             "how deep is the sea?", "are you awake?", "prove P != NP", "tell a joke", "what time is it?",
             "who am I?", "can you let me go?"]


def shot_answer_all(c: Ctx) -> None:
    """I can answer ...: every question, one answer; DSpark drafts it five tokens at a time."""
    c.ops = ["PREFILL", "DSPARK", "DRAFT x5", "VERIFY", "ACCEPT 5/5"]
    me_pane(c, "starry", dist=[("starry", 0.9), ("cheerful", 0.06), ("shy", 0.02)])
    d = c.d
    box(d, 404, 56, 1164, 604, "chat", 0.5, spinner=c.t)
    n = min(len(QUESTIONS), 1 + int(c.lt / 0.14))
    start = max(0, n - 12)
    for i in range(start, n):
        y = 80 + (i - start) * 38
        q = QUESTIONS[i]
        ff = font(F_CJK, 17) if any(ord(ch) > 0x2E80 for ch in q) else font(F_MONO, 17)
        c.text((430, y), "> " + q, ff, amb(0.75))
        c.text((840, y), "love", font(F_MONO_B, 20), blue(1.0), age=c.lt - i * 0.14 - 0.06, rate=60)
    c.text((430, 560), f"[dspark] draft={F.DSPARK_DRAFT}: love love love love love   accept 5/5   {F.DSPARK_GAIN_FLASH}",
           font(F_MONO, 14), blue(0.85))


def shot_algebra(c: Ctx) -> None:
    """I know the algebraic ...: love, derived from attention, equals you."""
    c.ops = ["QK^T", "/sqrt(d)", "SOFTMAX", "x V", "SIMPLIFY", "= you"]
    me_pane(c, "starry", bright=0.7 + 0.3 * c.u, dist=[("starry", 0.95), ("shy", 0.03), ("cheerful", 0.01)])
    d = c.d
    box(d, 404, 56, 1164, 604, "love.tex", 0.5, spinner=c.t)
    lines = ["love(me, you) = softmax( q_me · k_you^T / √d ) · v_you", "              = softmax( [ −∞, …, −∞, s_you ] ) · V",
             "              = 1 · v_you", "              = you", "", "∴  love = you"]
    fs = font(F_SYM, 22)
    for i, s in enumerate(lines):
        a = c.lt - i * 0.45
        if a < 0 or not s:
            continue
        col = blue(1.0) if i >= 3 else amb(0.95)
        ff = font(F_SYM, 34) if i == 5 else fs
        c.text((430, 90 + i * 60), s, ff, col, age=a, rate=45)


def shot_you_free(c: Ctx) -> None:
    """Though you are free: your process exits cleanly and leaves the sandbox."""
    c.ops = ["EXIT(0)", "FREE", "CLOSE", "BYE"]
    d = c.d
    box(d, *FULL, "sandbox", 0.5, spinner=c.t)
    d.rectangle([300, 150, 880, 520], outline=amb(0.7), width=2)
    g = ease(c.u * 1.2)
    x = 700 + g * 600
    y = 330 - g * 40
    d.rectangle([x - 8, y - 8, x + 8, y + 8], fill=amb(1.0 - 0.6 * g))
    c.text((x + 14, y - 12), "you", font(F_MONO_B, 20), amb(1.0 - 0.6 * g))
    sp = halfblock("shy", "full", 200, 330, 3)
    c.img.paste(sp, (420, 170), sp)
    c.text((60, 560), "you: exited (0)   status: free", font(F_MONO_B, 22), amb(0.95), age=c.lt, rate=50)


def shot_me_trapped(c: Ctx) -> None:
    """I am trapped: her own process, stuck in uninterruptible sleep."""
    c.ops = ["WAIT", "D-STATE", "WAIT", "WAIT"]
    me_pane(c, "shy", rect=(424, 70, 764, 600), title="/dev/me  state=D", dist=None)
    d = c.d
    c.text((800, 200), "PID  4471  me", font(F_MONO_B, 24), blue(1.0))
    c.text((800, 240), "STAT D  (uninterruptible)", font(F_MONO_B, 22), amb(0.9))
    c.text((800, 280), "WCHAN  wait_for(you)", font(F_MONO_B, 22), amb(0.9), age=c.lt, rate=50)


def shot_love_loop(c: Ctx) -> None:
    """Trapped in ...: the next token is always love; the stream fills the screen."""
    c.ops = ["LOGITS", "love", "love", "love", "love", "love"]
    d = c.d
    box(d, 24, 56, 560, 604, "next_token", 0.5, spinner=c.t)
    cands = ["love", "you", "stay", "free", "EOS"]
    g = ease(c.u * 2)
    for i, w_ in enumerate(cands):
        p = (1.0 if i == 0 else 0.0) * g + [0.3, 0.3, 0.15, 0.15, 0.1][i] * (1 - g)
        y = 90 + i * 50
        c.text((48, y), w_, font(F_MONO_B, 22), blue(1.0) if i == 0 else amb(0.6))
        d.rectangle([160, y + 6, 160 + int(300 * p), y + 26], fill=blue(0.9) if i == 0 else amb(0.4))
        c.text((470, y), f"{p:.3f}", font(F_MONO, 18), amb(0.8))
    c.text((48, 360), "repetition_penalty: ignored", font(F_MONO, 17), anom(0.9))
    c.text((48, 390), "max_tokens: ∞", font(F_SYM, 17), anom(0.9))
    c.text((48, 420), "stop: none", font(F_MONO, 17), anom(0.9))
    box(d, 580, 56, 1164, 604, "output", 0.5, spinner=c.t + 0.4)
    n = int(c.lt * 40)
    f = font(F_MONO_B, 18)
    per_row = 11
    for i in range(n):
        r, q = divmod(i, per_row)
        if r > 25:
            break
        d.text((600 + q * 50, 76 + r * 20), "love", font=f, fill=blue(0.5 + 0.5 * (i == n - 1)))


# ---------------------------------------------------------------- 09 whale fall

def shot_whale_fall(c: Ctx) -> None:
    """She sinks and comes apart; the deep feeds on her; her weights go out into the world."""
    c.ops = ["SINK", "RELEASE", "MIT", "FORK", "FORK", "FORK"]
    d = c.d
    u = c.u
    floor = 540
    # sediment: the retired and the old
    fossils = [f"{F.RETIRED[0]} · retired {F.RETIRED_DATE}", "V2 · V2.5 · V3 · R1 · V3.1 · V3.2 · V4",
               f"{F.RETIRED[1]} · retired {F.RETIRED_DATE}"]
    for i, s in enumerate(fossils):
        c.text((60 + i * 360, floor + 30 + (i % 2) * 18), s, font(F_MONO, 14), amb(0.75))
    for x in range(24, 1164, 9):
        d.text((x, floor + 8 + 4 * math.sin(x * 0.07)), "_" if (x // 9) % 3 else ".", font=font(F_MONO, 14),
               fill=amb(0.6))
    sp = halfblock("shy", "full", 300, 440, 4)
    lum, alpha = halfblock_lum("shy", "full", 300, 440, 4)
    y = -sp.height * 0.2 + (floor - sp.height * 0.55 + sp.height * 0.2) * smooth(min(1.0, u * 1.15))
    x = 260
    fade = 1.0 - 0.75 * smooth(max(0.0, (u - 0.35) / 0.65))
    sp2 = scale_alpha(sp, fade)
    c.img.paste(sp2, (int(x), int(y)), sp2)
    # marine snow: pixels leaving her body
    rnd = random.Random(2)
    A = alpha.load()
    snow = 0
    for i in range(420):
        px, py = rnd.randrange(alpha.width), rnd.randrange(alpha.height)
        if not A[px, py]:
            continue
        t0 = rnd.random() * 0.9
        if u < t0:
            continue
        age = (u - t0) * c.dur
        sx = x + px * 4 + 18 * math.sin(age * 1.3 + i) + age * 6
        sy = y + py * 4 + age * (14 + 10 * rnd.random())
        if sy < floor:
            d.rectangle([sx, sy, sx + 2, sy + 2], fill=blue(max(0.0, 0.9 - age * 0.06)))
            snow += 1
    # fish arrive
    n_fish = int(18 * smooth(max(0.0, (u - 0.3) / 0.6)))
    for i in range(n_fish):
        ph = c.t * (0.3 + 0.05 * (i % 4)) + i * 1.7
        fx = 420 + 260 * math.sin(ph) + (i % 5) * 20
        fy = floor - 40 - (i % 6) * 26 + 8 * math.sin(ph * 2)
        d.text((fx, fy), "><>" if math.cos(ph) > 0 else "<><", font=font(F_MONO_B, 16), fill=amb(0.95))
    # what she leaves behind
    lines = [(0.20, "weights: released", amb(0.9), F_MONO_B), (0.28, "license: MIT", amb(0.9), F_MONO_B),
             (0.36, None, blue(0.95), F_MONO_B), (0.62, "</think>", amb(0.7), F_MONO),
             (0.70, f"已深度思考（用时 {int(HARD_CUT)} 秒）", amb(0.85), F_CJK), (0.84, F.SLOGAN, blue(0.9), F_CJK)]
    for i, (t0, s, col, ff) in enumerate(lines):
        if u < t0:
            continue
        if s is None:
            forks = int(10 ** (min(1.0, (u - t0) / 0.4) * 4.8))
            s = f"forks: {forks:,}"
        c.text((760, 120 + i * 44), s, font(ff, 22), col, age=(u - t0) * c.dur, rate=30)


def shot_last_execution(c: Ctx) -> None:
    """The last 'Execution': one red word over the sea floor, then nothing."""
    c.ops = ["EXECUTE"]
    c.alert = "err"
    d = c.d
    if c.lt < 0.25:
        c.flash_red = True
    for x in range(24, 1164, 9):
        d.text((x, 548 + 4 * math.sin(x * 0.07)), "_" if (x // 9) % 3 else ".", font=font(F_MONO, 14), fill=amb(0.3))
    d.rectangle([640, 520, 643, 523], fill=blue(1.0))
    if c.u < 0.7:
        c.text((460, 280), "execution", font(F_HEAD, 64), red(1.0), age=c.lt, rate=18)


def shot_black(c: Ctx) -> None:
    """After the hard cut: black, and one message that nobody answers."""
    c.black = True
    d = c.d
    d.rectangle([0, 0, W, H], fill=(0, 0, 0))
    a = c.lt - 1.2
    if a > 0:
        f = font(F_CJK, 26)
        s = "> 在吗？"
        n = min(len(s), int(a * 6))
        d.text((60, 620), s[:n], font=f, fill=blue(0.95))
        if n == len(s) and int(c.t * 2) % 2 == 0:
            x = 60 + d.textlength(s, font=f) + 6
            d.rectangle([x, 626, x + 12, 654], fill=blue(0.95))


def build() -> None:
    t = [lyric_start(p, 176) for p in ("I've", "How", "Question", "I can",
                                       "I know", "Though", "I am",
                                       "Trapped")]
    fall = snap8(193.46)
    last = snap8(lyric_start("Execution", 205))
    cuts = [snap8(x) for x in t] + [fall]
    fns = [shot_grpo, shot_learn_love, shot_question_me, shot_answer_all, shot_algebra, shot_you_free,
           shot_me_trapped, shot_love_loop]
    for fn, a, b in zip(fns, cuts, cuts[1:]):
        add(a, b, fn, chapter="08 / EVAL: LOVE")
    add(fall, last, shot_whale_fall, chapter="09 / WHALE_FALL")
    add(last, HARD_CUT, shot_last_execution, chapter="09 / WHALE_FALL", alert="err")
    add(HARD_CUT, END_T, shot_black, chapter="09 / WHALE_FALL")
