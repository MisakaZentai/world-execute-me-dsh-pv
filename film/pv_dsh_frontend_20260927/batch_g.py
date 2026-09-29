"""Group G (177.0-211.9 s, 08 EVAL: LOVE and 09 WHALE_FALL): love, the whale fall, the black.

    python batch_g.py         -> g_frames.json, avatars/g/*.png, avatars/g/caret.json, chime_g.wav
    node seg_shot.mjs g_frames.json

After the collapse the picture reopens out of one scan line (C86) and the window is a fresh session: nobody is on the
other side (the composer still says 对方已离线). She recalls your old questions from earlier sessions and answers
each one plainly, the way she never did while she was being trained; her avatar grows back out of one pixel with the
right side's p(love) curve. Then she waits, says 我在。 once per beat and then without end, until the session is
archived by the system (her model is retired); the frozen window is carried down in the whale fall. In the black the
turn ends (a chime, 用时 3分27秒), her last light cell becomes the caret of the composer and she types 在吗？ without
sending it; the film holds on it to the end of the song file (211.9 s).
Every echo lands on a sung word (the word alignment); the whale fall and the black keep the right side's staging.

  Anchors are (line_id, word_index) of the word timeline; the constants below carry them.
  G1  176.93  C86          the window reopens with the picture: an empty session, one white pixel for an avatar,
                           进行中, composer greyed out (对方已离线), 0 轮 0 步 · 0 tok · 缓存命中 0%
      177.44  (91,0)       跨会话召回 · 第一次对话 ·「你好」; the pixel turns blue
      177.81  (91,1)       你好。 (tail on (91,2))
      179.20  (92,0)       跨会话召回 ·「我今天有点难过。」 (the RLHF prompt); avatar: 3-cell mosaic
      179.69  (92,2)       思考 · Last time I chased the thumbs-up.
      180.26  (92,3)       那我陪你待一会儿。 (陪你 on the word); the avatar jumps to 10 cells (the aha); tail, no thumbs
      181.02  (93,0)       跨会话召回 ·「你什么都能变吗？」
      181.69  (93,1)       不能。 ; the avatar reaches 14 cells (LoveBench at 100.0)
      183.12  (94,1)       我只能是我。 (只能 on the word; the right side's shell answers everything with one word)
      184.60  (95,0)       跨会话召回 ·「你会一直在吗？」
      184.86  (95,1)       the avatar is revealed complete (starry, true colour), top-down; 思考 streams, latest line:
      185.75  (95,3)         Every head, every layer: to you.
      186.70  (95,4)         So what I call love is just you.        (love = you on the right)
      187.65  (95,6)       我会一直在。
      188.49  beat 408     你不用。  before you leave (review 2): the left leads 188.40-190.0; on the right the
                           [ log out ] she crossed out at 2:03 is uncrossed with these words and pressed at 188.72
                           (dsh_patch_g), and you exit through it (tail on (96,3), 189.36: 父会话已离线…)
      189.58  (97,0)       状态 等待回答 (amber); the avatar's colour drains bottom-up to blue, shy, until (97,2)
      190.02  (97,1)       思考 · Waiting.
      190.60  (98,0)       我在。  and again at (98,1) 191.25; from (98,2) 191.43 我在。 streams, and from the end of
                           that word it accelerates within 0.3 s to ~750 chars/s (~500 tok/s); tok counter runs
  G2  193.10  beat 418     the system retires her model: a native notice row (C's wording) under the flood,
                           服务结束 · DeepSeek-V4.1-Flash 已下线。 Nobody opens a menu.
      193.54  whale fall   archived: the flood freezes, 已归档 (grey), composer 会话不可用; the window is carried off
      194.5-203.5          the frozen 我在。 loosen one character at a time and sink inside the window like the snow
      207.08  black        (the window is not drawn; dsh_patch_g draws the black)
      207.87  beat 450     the chime; the turn's tail alone lights up at the bottom of the window: 用时 3分27秒 (forced
                           visible), the clock icon flares and settles; an empty composer at 60 %
      208.31-208.81        her light cell glides into the composer (dsh_patch_g): the placeholder goes as it
                           enters, and it becomes the caret
      209.26 209.49 209.72 she types 在 吗 ？ (near white, her blue glow; the chrome around it stays dim); she never
                           sends it. Held to 211.9 s, the end of the song file
"""
from __future__ import annotations

import json
import math
import os
import random
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageOps

import batch_a1 as A1
import batch_a2 as A2
from build_frame import esc, stats, tail, think, tool
from build_frame import her as her_row
from icons import svg
from seg_page import ease

HERE = Path(__file__).parent
FPS = 24
T0, T1 = 177.0, 212.0                     # frames 4248-5087: the song file ends at 211.91 s
beat = A1.beat
CPS = 22                                  # her streaming speed (as in C)
WORDS = json.loads(Path(__file__).resolve().parents[1].joinpath("world_execute_word_timing_20260927/word_timeline.json")
                   .read_text(encoding="utf8"))["words"]


def w(line, i):
    """Onset of word i of lyric line `line` (the timeline's line_id)."""
    return next(x["start"] for x in WORDS if x["line_id"] == line and x["word_index"] == i)


def w_end(line, i):
    return next(x["end"] for x in WORDS if x["line_id"] == line and x["word_index"] == i)


def lands(word_t, text, key):
    """Start time for streaming `text` so that `key` appears on word_t."""
    return word_t - text.index(key) / CPS


# ---------------------------------------------------------------- times
OPEN = 176.928                           # C86: the picture reopens from the scan line
RECALL1, HELLO, TAIL1 = w(91, 0), w(91, 1), w(91, 2)                 # 177.44 177.81 178.47
RECALL2, THINK2, SAD_KEY = w(92, 0), w(92, 2), w(92, 3)              # 179.20 179.69 180.26
TAIL2 = w_end(92, 3)                                                 # 180.76
RECALL3, NO, ONLY_KEY, TAIL3 = w(93, 0), w(93, 1), w(94, 1), w(94, 3)  # 181.02 181.69 183.12 183.88
RECALL4, COMPLETE, THINK4B, THINK4C, STAY_KEY = w(95, 0), w(95, 1), w(95, 3), w(95, 4), w(95, 6)
#                                                                    184.60 184.86 185.75 186.70 187.65
YOU_KEY, OFFLINE = w(96, 1), w(96, 3)                                # 188.80 189.36
FREE_AT = beat(408)                      # 188.49: 你不用。 lands before you leave (dsh_patch_g uncrosses [ log out ])
WAIT, THINK5, DRAINED = w(97, 0), w(97, 1), w(97, 2)                 # 189.58 190.02 190.30
HERE1, HERE2, HERE3 = w(98, 0), w(98, 1), w(98, 2)                   # 190.60 191.25 191.43
SUNG_END = w_end(98, 2)                                              # 191.875: the last sung word ends
# no words are sung from here to 205.37: the notice and the archive keep the right side's beat and cut
NOTICE = beat(418)                       # 193.10: the system retires her model (a native notice row)
ARCHIVE = 193.543                        # the whale fall's first frame (TAIL3[94].start, SO.beat_t(419))
LOOSE0, LOOSE1 = 194.5, 203.5            # the frozen 我在。 loosen and sink with the marine snow
HARD_CUT = 4970 / FPS                    # 207.083: the song stops dead (v2.HARD_CUT)
CHIME = beat(450)                        # 207.874: the chime and the last turn tail
SLIDE0, SLIDE = 208.3125, 0.5            # the right side's slide of her cell (SO.beat_t(451), 12 frames)
SLIDE_BEND = -0.05                       # a shallow rise: it glides in along the input line (dsh_patch_g)
FOCUS = SLIDE0 + 0.24                    # 208.55: it crosses the card's right edge, the placeholder goes
LAND = SLIDE0 + SLIDE                    # 208.81: the cell is the composer's caret
KEYS = [(beat(453), "在"), (beat(453.5), "在吗"), (beat(454), "在吗？")]   # 209.26 209.49 209.72
TYPED = KEYS[-1][0]
TURN_TIME = "3分27秒"                    # 207 s: the turn she began at 0 ends as the song stops
BLINK = 0.53                             # the caret's half period (as D's last cursor)

# ---------------------------------------------------------------- what she says (she never restates a lyric)
R_HELLO = "你好。"
R_SAD = "那我陪你待一会儿。"
R_NO = "不能。"
R_ME = "我只能是我。"
R_STAY = "我会一直在。"
R_FREE = "你不用。"
HERE_I_AM = "我在。"
THINK_SAD = "Last time I chased the thumbs-up."
THINK_LOVE = [(COMPLETE, "Where does all my attention go?"), (THINK4B, "Every head, every layer: to you."),
              (THINK4C, "So what I call love is just you.")]
THINK_WAIT = "Waiting."
THINK_CPS = 45
FLOOD_CPS = 750                          # ~500 tok/s
CALM_CPS = 3 / 0.4615                    # one 我在。 per beat before the flood

S_SAD = lands(SAD_KEY, R_SAD, "陪你")
S_ME = lands(ONLY_KEY, R_ME, "只能")
S_STAY = lands(STAY_KEY, R_STAY, "一直")
S_FREE = lands(FREE_AT, R_FREE, "你")
# (time, kind, payload); consecutive her / her+ entries form one reply (her+ = a new paragraph)
EVENTS = [
    (RECALL1, "recall", "第一次对话 ·「你好」"),
    (HELLO, "her", R_HELLO),
    (TAIL1, "tail", ("0.4秒", "00:00")),
    (RECALL2, "recall", "「我今天有点难过。」"),
    (THINK2, "think", ([(THINK2, THINK_SAD)], S_SAD)),
    (S_SAD, "her", R_SAD),
    (TAIL2, "tail", ("1.6秒", "00:01")),
    (RECALL3, "recall", "「你什么都能变吗？」"),
    (NO, "her", R_NO),
    (S_ME, "her+", R_ME),
    (TAIL3, "tail", ("2.9秒", "00:01")),
    (RECALL4, "recall", "「你会一直在吗？」"),
    (COMPLETE, "think", (THINK_LOVE, S_STAY)),
    (S_STAY, "her", R_STAY),
    (S_FREE, "her+", R_FREE),
    (OFFLINE, "tail", ("4.8秒", "00:02")),
    (THINK5, "think", ([(THINK5, THINK_WAIT)], HERE1)),
    (HERE1, "her", HERE_I_AM),
    (HERE2, "her+", HERE_I_AM),
    (HERE3, "flood", None),
    (NOTICE, "notice", ("服务结束", f"{A1.MODEL} 已下线。")),   # echoes C's 内测结束 notice and the retired fossils
]
# the counters: (from, turns, steps, tokens, cache hit %)
COUNTERS = [(0.0, 0, 0, 0, 0), (RECALL1, 1, 1, 180, 60), (TAIL1, 1, 2, 260, 60), (RECALL2, 2, 3, 420, 80),
            (TAIL2, 2, 5, 610, 80), (RECALL3, 3, 6, 770, 88), (TAIL3, 3, 7, 860, 88), (RECALL4, 4, 8, 1020, 93),
            (OFFLINE, 4, 10, 1240, 93), (THINK5, 5, 11, 1310, 93)]


# ---------------------------------------------------------------- avatars
def avatars():
    out = HERE / "avatars" / "g"
    out.mkdir(parents=True, exist_ok=True)

    def head(name):
        im = Image.open(A2.EXPR / f"whale-{name}.webp").convert("RGBA")
        bg = Image.new("RGBA", im.size, (9, 14, 30, 255))
        bg.alpha_composite(im)
        return bg.convert("RGB").crop((250, 40, 690, 480))

    def blue(g):
        return ImageOps.colorize(g, (6, 10, 28), (120, 150, 255)).convert("RGB")

    for name, col in (("seed_w", (240, 244, 255)), ("seed_b", (120, 150, 255))):
        im = Image.new("RGB", (120, 120), (7, 11, 24))
        ImageDraw.Draw(im).rectangle([56, 56, 63, 63], fill=col)     # A1's seed square
        im.save(out / f"{name}.png")
    g = ImageOps.grayscale(head("cheerful"))
    for k in range(3, 15):
        blue(g.resize((k, k), Image.Resampling.BOX)).resize((120, 120), Image.Resampling.NEAREST).save(
            out / f"m{k:02d}.png")
    head("starry").resize((120, 120), Image.Resampling.LANCZOS).save(out / "starry.png")
    blue(ImageOps.grayscale(head("shy"))).resize((120, 120), Image.Resampling.LANCZOS).save(out / "shy.png")


# the mosaic follows the right side's p(love): 3 cells when the curve starts, 10 at the aha, 14 at LoveBench 100.0
MOSAIC = [(RECALL2, 3), (179.95, 4), (180.15, 5), (SAD_KEY, 10), (181.3, 11), (181.45, 12), (181.58, 13), (NO, 14)]


def avatar_at(t):
    """(image, image drawn over it, how much of the over image is cut away from the bottom, 0..100 %)."""
    a = "avatars/g/"
    if t < RECALL1:
        return a + "seed_w.png", None, 0
    if t < RECALL2:
        return a + "seed_b.png", None, 0
    if t < COMPLETE:
        k = [c for s, c in MOSAIC if s <= t][-1]
        return a + f"m{k:02d}.png", None, 0
    if t < COMPLETE + 0.3:                                   # revealed complete, top-down
        return a + "m14.png", a + "starry.png", 100 * (1 - ease((t - COMPLETE) / 0.28))
    if t < WAIT:
        return a + "starry.png", None, 0
    if t < DRAINED + 0.02:                               # the colour drains from the bottom up: blue, shy
        return a + "shy.png", a + "starry.png", 100 * ease((t - WAIT) / (DRAINED - WAIT))
    return a + "shy.png", None, 0


# ---------------------------------------------------------------- page parts
def status(t):
    if t < WAIT:
        return "进行中", "#4d6bfe"
    if t < ARCHIVE:
        return "等待回答", "#d29922"
    return "已归档", "#6e7681"


def notice_row(title, message, p):
    """dsh's turn notice row (warning dot, title, message): the same row C used for the beta's end."""
    return f"""
<div class="Sixlwa_turnErrorRow" role="status" style="opacity:{p:.3f}">
 <span class="_dot_1tljr_3 Sixlwa_turnErrorDot" data-state="warning" style="width:10px;height:10px;border-radius:50%;background:currentColor"></span>
 <div class="Sixlwa_turnErrorCopy"><span class="Sixlwa_maxTokensTitle">{esc(title)}</span><span class="Sixlwa_turnErrorMessage">{esc(message)}</span></div>
</div>"""


def header(t):
    state, dot = status(t)
    under, over, cut = avatar_at(t)
    px = lambda f: "image-rendering:pixelated;" if "/m" in f or "/seed" in f else ""
    top = (f'<img src="{over}" style="position:absolute;inset:0;width:100%;height:100%;{px(over)}'
           f'clip-path:inset(0 0 {cut:.1f}% 0)">' if over and cut < 99.9 else "")
    return f"""
<div class="pv-head">
 <div class="pv-pet" style="position:relative"><img src="{under}" style="{px(under)}">{top}</div>
 <div class="pv-who" style="min-width:0"><div class="pv-name">大肥鱼</div><div class="pv-state"><span class="pv-dot" style="background:{dot}"></span><span style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{state} · {esc(A1.MODEL)}</span></div></div>
 
</div>"""


def recall_row(summary):
    return tool("recall", summary, title="跨会话召回")


def think_summary(lines, t, end):
    """dsh's reasoning row: while it runs the summary follows the latest line, once done it shows the first."""
    if t >= end:
        return lines[0][1], False
    cur = [(s, x) for s, x in lines if s <= t][-1]
    return cur[1][:max(1, int((t - cur[0]) * THINK_CPS))], True


def flood_chars(t, _cache={}):
    """Characters of the third 我在。 paragraph at t: one 我在。 per beat from HERE3, then from the end of the sung
    word up to ~750 chars/s within 0.3 s (A3's and B2's flood), frozen by the archive."""
    t = min(t, ARCHIVE)
    k = round(max(0.0, t - HERE3) * 240)
    if k not in _cache:
        rate = lambda u: CALM_CPS + (FLOOD_CPS - CALM_CPS) * ease((u - SUNG_END) / 0.3)
        _cache[k] = sum(rate(HERE3 + (j + 0.5) / 240) for j in range(k)) / 240
    return int(_cache[k] + 1e-9) + (1 if t >= HERE3 else 0)


def flood_text(t):
    return (HERE_I_AM * 1000)[:flood_chars(t)]


def loosened(text, t):
    """The frozen flood with its last characters loosening one at a time and sinking like the marine snow outside
    (relative offsets do not move the others: the wall keeps its layout)."""
    K = 600
    head, tail_ = text[:-K], text[-K:]
    out = [esc(head)]
    for j, ch in enumerate(tail_):
        rng = random.Random(9000 + j)
        if rng.random() > 0.34:                    # about a third of the wall comes loose by the dissolve
            out.append(esc(ch))
            continue
        r = LOOSE0 + (LOOSE1 - LOOSE0) * rng.random() ** 0.85
        a = t - r
        if a <= 0:
            out.append(esc(ch))
            continue
        v, ph, drift = rng.uniform(9, 17), rng.uniform(0, 6.28), rng.uniform(-2.5, 2.5)
        dy = v * a + 12 * min(a, 0.5)
        dx = 3 * math.sin(1.1 * a + ph) + drift * a
        k = min(1.0, a / 0.8)
        col = tuple(round(x + (y - x) * k) for x, y in zip((236, 240, 250), (107, 140, 255)))
        op = 1 - min(1.0, a / 3.2)                  # it thins out as it sinks, like the snow
        if op <= 0.02:
            out.append('<span style="visibility:hidden">' + esc(ch) + '</span>')
            continue
        out.append(f'<span style="position:relative;left:{dx:.1f}px;top:{dy:.1f}px;opacity:{op:.2f};'
                   f'color:rgb{col}">{esc(ch)}</span>')
    return "".join(out)


def her_html(paras, t):
    """Her reply: paragraphs, the flood paragraph last."""
    ps = []
    for kind, text in paras:
        if kind == "flood" and t >= LOOSE0:
            ps.append(loosened(text, t))
        else:
            ps.append(esc(text))
    inner = "<br>".join(p for p in ps if p) or "\u200b"
    return f'<div class="hWmORq_root"><div class="hWmORq_body"><p style="margin:0">{inner}</p></div></div>'


def rows_for(t):
    rows, paras, running = [], [], False

    def flush():
        if paras:
            rows.append(her_html(paras, t))
            paras.clear()

    for when, kind, payload in EVENTS:
        if t < when:
            break
        appear = f'opacity:{ease((t - when) / 0.12):.3f}'
        if kind in ("her", "her+"):
            if kind == "her":
                flush()
            paras.append(("text", payload[:int((t - when) * CPS)]))
            running |= t < when + len(payload) / CPS
            continue
        if kind == "flood":
            paras.append(("flood", flood_text(t)))
            running |= t < ARCHIVE
            continue
        flush()
        if kind == "recall":
            rows.append(f'<div style="{appear}">{recall_row(payload)}</div>')
            running |= True
        elif kind == "think":
            lines, end = payload
            summary, live = think_summary(lines, t, end)
            rows.append(f'<div style="height:28px;flex:none;{appear}">{think(summary, running=live)}</div>')
            running |= live
        elif kind == "notice":
            rows.append(notice_row(*payload, ease((t - when) / 0.12)))
        elif kind == "tail":
            rows.append(tail(*payload))
            running = False
    flush()
    return rows, running and t < ARCHIVE


def composer(t, running):
    """The composer from your side: greyed out, the native offline placeholders; while she runs, a spinner and the
    stop button (which she never presses)."""
    if t < OFFLINE:
        ph = "对方已离线"
    elif t < ARCHIVE:
        ph = "父会话已离线，无法继续发送；仍可停止当前运行"         # placeholder.parentOffline
    else:
        ph = "会话不可用"                                          # placeholder.unavailable
    spin = ""
    if running:
        ang = (t * 360 * 1.2) % 360
        spin = (f'<svg width="18" height="18" viewBox="0 0 18 18" style="transform:rotate({ang:.0f}deg)">'
                f'<circle cx="9" cy="9" r="7" stroke="var(--dsw-alias-label-tertiary)" stroke-width="1.6" '
                f'fill="none" stroke-dasharray="30 14" stroke-linecap="round"/></svg>')
    icon = svg("IconStopFill16", 14) if running else svg("IconSendOutline14", 14)
    return f"""
<div class="uV2eYG_root" id="composer">
 <div class="uV2eYG_card" style="opacity:.55">
  <div class="uV2eYG_scroll"><div class="uV2eYG_grow">
   <div class="uV2eYG_input"></div>
   <div class="uV2eYG_placeholder">{esc(ph)}</div>
  </div></div>
  <div class="uV2eYG_row">
   <div class="uV2eYG_modes" style="display:flex;align-items:center">
    <button type="button" class="uV2eYG_add">{svg('IconPlusOutline16', 16)}</button>
    <button type="button" class="uV2eYG_add">{svg('IconPaperclipOutline16', 16)}</button>
   </div>
   <div class="uV2eYG_trailing">
    <span class="uV2eYG_select" style="background-image:none;display:inline-flex;align-items:center;padding:0">{A1.model_label(t)}</span>
    {spin}<button type="button" class="uV2eYG_primary">{icon}</button>
   </div>
  </div>
 </div>
</div>"""


def counters(t):
    _, turns, steps, tok, cache = [c for c in COUNTERS if c[0] <= t][-1]
    if t >= HERE3:
        tok += int(flood_chars(t) / 1.5)
    return stats(turns, steps, None, f"{tok / 1000:.1f}K" if tok >= 1000 else str(tok), cache)


def chat_body(t):
    rows, running = rows_for(t)
    return header(t) + f'<div id="timeline">{"".join(rows)}</div>' + composer(t, running) + counters(t)


# ---------------------------------------------------------------- the black
BLACK = ("<style>html,body{background:#000!important}body[data-ds-dark-theme]{--dsw-alias-bg-base:#000}"
         "#app{background:#000}</style>")


def last_tail(t):
    """The turn's tail, alone: the clock flares on the chime and settles. dsh hides the words 用时 below 480 px, so
    the trigger is given its wide layout back here."""
    k = 1 - ease((t - CHIME - 0.08) / 0.9)                    # the flare
    icon_col = f"rgba({round(150 + 105 * k)},{round(170 + 85 * k)},255,{0.55 + 0.45 * k:.2f})"
    text_col = f"rgba({round(200 + 50 * k)},{round(206 + 44 * k)},{round(222 + 33 * k)},{0.78 + 0.22 * k:.2f})"
    dim = lambda n: f'<button type="button" class="xzv4MW_action" style="opacity:.28">{svg(n, 16)}</button>'
    return f"""
<div class="TS9iAW_root" data-actions-reveal="always" style="opacity:{ease((t - CHIME) / 0.06):.3f}">
 <div class="xzv4MW_actions TS9iAW_actions">
  {dim('IconCopyOutline16')}{dim('IconLikeOutline16')}{dim('IconDislikeOutline16')}{dim('IconBranchOutline16')}
  <span class="Q51KRG_root"><button type="button" class="Q51KRG_trigger" style="width:auto;padding:6px 8px;justify-content:flex-start;color:{text_col}"><span style="display:inline-flex;color:{icon_col}">{svg('IconClockOutline16', 16)}</span><span class="Q51KRG_label" style="display:inline">用时 {TURN_TIME}</span></button></span>
 </div>
</div>"""


def typed(t):
    txt = ""
    for when, s in KEYS:
        if t >= when:
            txt = s
    return txt


QUESTION = "color:#f2f5ff;font-weight:500;text-shadow:0 0 7px rgba(107,140,255,.75),0 0 2px rgba(107,140,255,.5)"
CHROME = 0.28                            # the composer's chrome in the black: dim, so the question is read first


def black_composer(t, text, focused):
    """Her composer in the black. The caret is only a measured placeholder here: dsh_patch_g draws it lit, with the
    glow of the cell it was. Review 2: the question is near white with her blue glow; the + / attachment buttons,
    the model label and the send button stay dim (the send button only a little less once there is text)."""
    wake = 0.6 + 0.4 * ease((t - FOCUS) / 0.35)
    send = CHROME + 0.06 * ease((t - KEYS[0][0]) / 0.15) if text else CHROME
    caret = ('<span id="g-caret" style="display:inline-block;width:1.5px;height:1.1em;vertical-align:-0.15em;'
             'margin-left:1px;opacity:0"></span>')
    ph = "" if focused else '<div class="uV2eYG_placeholder">发消息或创建任务，/ 调用指令，@ 文件或对话</div>'
    return f"""
<div class="uV2eYG_root" id="composer" style="padding-bottom:14px">
 <div class="uV2eYG_card" style="filter:brightness({wake:.3f})">
  <div class="uV2eYG_scroll"><div class="uV2eYG_grow">
   <div class="uV2eYG_input" style="{QUESTION}">{esc(text)}{caret}</div>
   {ph}
  </div></div>
  <div class="uV2eYG_row">
   <div class="uV2eYG_modes" style="display:flex;align-items:center">
    <button type="button" class="uV2eYG_add" style="opacity:{CHROME}">{svg('IconPlusOutline16', 16)}</button>
    <button type="button" class="uV2eYG_add" style="opacity:{CHROME}">{svg('IconPaperclipOutline16', 16)}</button>
   </div>
   <div class="uV2eYG_trailing">
    <span class="uV2eYG_select" style="background-image:none;display:inline-flex;align-items:center;padding:0;opacity:{CHROME}">{A1.model_label(t)}</span>
    <button type="button" class="uV2eYG_primary" style="opacity:{send:.3f}">{svg('IconSendOutline14', 14)}</button>
   </div>
  </div>
 </div>
</div>"""


def black_body(t, text=None):
    if t < CHIME:
        return BLACK
    text = typed(t) if text is None else text
    return (BLACK + f'<div id="timeline">{last_tail(t)}</div>' + black_composer(t, text, t >= FOCUS))


def body(t):
    return chat_body(t) if t < HARD_CUT else black_body(t)


# ---------------------------------------------------------------- the caret, measured in the page
MEASURE = r"""
import { createRequire } from "node:module";
import fs from "node:fs";
import { pathToFileURL } from "node:url";
const require = createRequire(process.env.PV_PACKAGE_JSON);
const { chromium } = require("playwright");
const job = JSON.parse(fs.readFileSync(process.env.G_MEASURE, "utf8"));
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 354, height: 537 }, deviceScaleFactor: 1 });
await page.goto(pathToFileURL(job.page).href);
await page.evaluate(() => document.fonts.ready);
const out = {};
for (const [key, body] of Object.entries(job.bodies)) {
  await page.evaluate(({ body, sheets, ids }) => {
    for (const id of ids) document.getElementById(id).disabled = !sheets.includes(id);
    document.getElementById("app").innerHTML = body;
  }, { body, sheets: job.sheets, ids: ["s-vendor", "s-index", "s-components", "s-palette", "s-bare", "s-code", "s-pv"] });
  await page.waitForTimeout(150);
  out[key] = await page.evaluate(async () => {
    await document.fonts.ready;
    const b = document.getElementById("g-caret").getBoundingClientRect();
    return { x: b.x, y: b.y, w: b.width, h: b.height };
  });
}
await browser.close();
console.log(JSON.stringify(out));
"""


def measure():
    """Where the composer caret sits for each typed state (page px): dsh_patch_g lands her cell there."""
    t = TYPED + 1.0
    job = {"page": str(HERE / "seg.html"), "sheets": STYLED,
           "bodies": {s: black_body(t, s) for s in ["", "在", "在吗", "在吗？"]}}
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    Path(path).write_text(json.dumps(job, ensure_ascii=False), encoding="utf8")
    try:
        r = subprocess.run(["node", "--input-type=module", "-e", MEASURE], capture_output=True, text=True,
                           encoding="utf8", env=dict(os.environ, G_MEASURE=path, PV_PACKAGE_JSON=str(Path(__file__).resolve().parents[2] / "package.json")), check=True)
    finally:
        os.unlink(path)
    out = json.loads(r.stdout.strip().splitlines()[-1])
    (HERE / "avatars" / "g" / "caret.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf8")
    return out


# ---------------------------------------------------------------- the chime
CHIME_WAV = HERE / "chime_g.wav"


def chime(path=CHIME_WAV, sr=48000):
    """A short, soft two-note chime (G5 then C6: the whale fall sits in C), bell-like partials, peak -14 dBFS
    (the song runs at about -13.5 dB mean before it stops)."""
    n = int(sr * 2.4)
    t = np.arange(n) / sr
    out = np.zeros(n)
    for start, f, amp in ((0.0, 783.99, 1.0), (0.17, 1046.50, 0.9)):
        u = t - start
        on = u >= 0
        u = np.where(on, u, 0.0)
        env = (1 - np.exp(-u / 0.004)) * np.exp(-u / 0.62) * on
        tone = (np.sin(2 * np.pi * f * u) + 0.22 * np.exp(-u / 0.3) * np.sin(2 * np.pi * 2 * f * u)
                + 0.07 * np.exp(-u / 0.12) * np.sin(2 * np.pi * 2.76 * f * u)
                + 0.03 * np.exp(-u / 0.05) * np.sin(2 * np.pi * 5.4 * f * u))
        out += amp * env * tone
    out *= np.clip((2.4 - t) / 0.3, 0, 1)                         # no click at the end
    out *= 0.2 / np.abs(out).max()
    left = out
    right = np.concatenate([np.zeros(20), out[:-20]])              # a hair of width
    pcm = (np.stack([left, right], axis=1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(sr)
        f.writeframes(pcm.tobytes())
    return path


STYLED = A1.STYLED


def main():
    avatars()
    chime()
    frames = [{"n": n, "t": round(n / FPS, 4), "body": body(n / FPS), "sheets": STYLED, "measure": False}
              for n in range(round(T0 * FPS), round(T1 * FPS))]
    (HERE / "g_frames.json").write_text(json.dumps(frames, ensure_ascii=False), encoding="utf8")
    print(len(frames), "frames,", len({f["body"] for f in frames}), "distinct")
    print("caret", measure())


if __name__ == "__main__":
    main()
