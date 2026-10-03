"""The dsh window for 103-125 s as one HTML body per frame, a pure function of song time t.

    python seg_page.py        -> seg_frames.json (per-frame body + animation clock), avatars/*.png, seg.html
Then `node seg_shot.mjs` screenshots every frame into dsh_frames/NNNNN.png (frame number = round(t * 24)).

The script (song seconds). Bubbles never restate the lyric; the right side keeps the back end.
  103.10-106.80  you type "你会一直在吗？" in the composer, delete half of it, type it again; every character lands
                 on a peak of the right side's keystroke line (KEYS)
  103.52-110.25  the climax: her avatar grows into the complete her (see CLIMAX below). On If / if / Then / then she
                 pops out of the header and grows one step as a portrait above the chat, her mosaic halving each
                 step; from Feel (line 50) each of your keystrokes ripples through her once; on Finally she is
                 in full colour for the first time, at her largest; on completion she settles back into the header
  106.80         you send it
  106.90-108.64  her reasoning streams (latest line shown, as dsh does)
  108.64         "我一直在。" streams
  109.30         the turn ends: tail row, counters update
  110.40-115.42  "you have left": her interface is taken apart, one sung line at a time, never shrunk:
                 110.40 your input box goes offline (对方已离线)
                 111.98 your side of the conversation is evicted
                 112.89 the CSS falls off in a cascade (palette, layout, components, dsh's base sheets): a lump of
                        browser-default text
                 113.75 the page is bare code (its own markup)
                 114.75 the code evaporates; "我一直在。" is backspaced last; one blue cursor is left
  115.42-121.77  that cursor is all of her: the isolation pull-back carries it to the network node (dsh_her.py)
  119.70         erase (hidden by the shot); everything but her own reply is gone
  121.77         the window slides back: 本轮文件改动 reward.py, her reasoning redefines satisfaction
  123.55-124.15  "你很满意。" is typed into your input box in her blue and sent: a forged message from you
  124.45         "太好了～ (＾▽＾)"; the avatar comes back complete, in the wrong colour
"""
from __future__ import annotations

import html
import json
import math
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps

from build_frame import D, DEEPSEA, FONTS, ASSETS, esc, her, stats, svg, tail, think, user
from sung_words import w

HERE = Path(__file__).parent
FPS = 24
T0, T1 = 103.0, 125.0
W, H = 354, 537
EXPR = Path(__file__).resolve().parents[1].joinpath("third_party_references/whale_maid_expanded_20260926/expressions")
ANOM = (255, 204, 0)
SIXTEENTH = 60 / 130 / 4
L0, L1, L2, L3, L4, ISO = 110.40, 111.98, 112.89, 113.75, 114.75, 115.60   # sung onsets (scenes_userleft.SUNG)
ERASE, BACK, FORGE = 119.70, 121.77, 123.55


# ---------------------------------------------------------------- avatars (from the dsh-whale-galgame expressions)

def avatars():
    out = HERE / "avatars"
    out.mkdir(exist_ok=True)
    crop = (250, 40, 690, 480)

    def head(name):
        im = Image.open(EXPR / f"whale-{name}.webp").convert("RGBA")
        bg = Image.new("RGBA", im.size, (9, 14, 30, 255))
        bg.alpha_composite(im)
        return bg.convert("RGB").crop(crop).resize((120, 120), Image.Resampling.LANCZOS)

    def mosaic(im, cells=14):
        g = ImageOps.grayscale(im).resize((cells, cells), Image.Resampling.BOX)
        blue = ImageOps.colorize(g, (6, 10, 28), (120, 150, 255))
        return blue.resize((120, 120), Image.Resampling.NEAREST)

    def desat(im):
        g = ImageOps.grayscale(im)
        return ImageOps.colorize(g, (8, 12, 26), (170, 182, 210))

    def forged(im):
        g = ImageOps.grayscale(ImageEnhance.Contrast(im).enhance(1.4))
        return ImageOps.colorize(g, (30, 18, 0), ANOM)

    files = {
        "draft": mosaic(head("cheerful")),
        "complete": head("cheerful"),
        "left": desat(head("frightened")),
        "lost": mosaic(head("frightened"), 10),
        "editing": mosaic(head("serious"), 10),
        "forged": forged(head("starry")),
    }
    for k, im in files.items():
        im.save(out / f"{k}.png")
    return {k: f"avatars/{k}.png" for k in files}


def avatars_d():
    """The climax portrait (avatars/d/): the header's head crop as blue mosaics of 8, 16, 32 and 64 cells at their
    step sizes, and a wide crop (the same head, plus her waving hand) for Finally: a 64-cell mosaic under the first
    full colour. The wide crop is the head crop widened by 22 whole cells a side, so its centre square is the head
    crop cell for cell (object-fit: cover keeps her in place while the frame widens)."""
    out = HERE / "avatars" / "d"
    out.mkdir(parents=True, exist_ok=True)
    im = Image.open(EXPR / "whale-cheerful.webp").convert("RGBA")
    bg = Image.new("RGBA", im.size, (9, 14, 30, 255))
    bg.alpha_composite(im)
    src = bg.convert("RGB")
    x0, y0, x1, y1 = 250, 40, 690, 480                 # avatars().crop
    cell = (y1 - y0) / 64
    wide = (x0 - 22 * cell, y0, x1 + 22 * cell, y1)     # 108 x 64 cells

    def blue(box, cells, size):
        g = ImageOps.grayscale(src.resize(cells, Image.Resampling.BOX, box=box))
        return ImageOps.colorize(g, (6, 10, 28), (120, 150, 255)).resize(size, Image.Resampling.NEAREST)

    for n, s in zip(CELLS, SIZES):
        blue((x0, y0, x1, y1), (n, n), (s, s)).save(out / f"m{n}.png")
    blue(wide, (108, 64), HERO).save(out / "wide_m64.png")
    src.resize(HERO, Image.Resampling.LANCZOS, box=wide).save(out / "wide.png")


AV = None


# ---------------------------------------------------------------- helpers

def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def show(inner, p):
    """A row entering or leaving: height and opacity follow p (0 = gone, 1 = in place)."""
    if p >= 1:
        return inner
    if p <= 0:
        return ""
    return (f'<div style="display:grid;grid-template-rows:{p:.3f}fr;opacity:{p:.3f}">'
            f'<div style="overflow:hidden;min-height:0">{inner}</div></div>')


def life(t, t_in, t_out=1e9, fade_in=0.12, fade_out=0.25):
    if t < t_in or t >= t_out + fade_out:
        return 0.0
    return min(ease((t - t_in) / fade_in), 1 - ease((t - t_out) / fade_out))


def stream(text, t, start, cps):
    n = int(max(0.0, t - start) * cps)
    return text[:n]


def lines_stream(lines, t, start, end):
    """Reasoning text streaming line by line between start and end; returns (text so far, running)."""
    total = sum(len(s) + 1 for s in lines)
    k = int(total * min(1.0, max(0.0, (t - start) / (end - start))))
    text = "\n".join(lines)[:k]
    return text, t < end


def latest_line(text):
    s = text.rstrip()
    return s[s.rfind("\n") + 1:]


# The right side's keystroke line (continuity_full_v2/scenes_userleft.wave_points, "you are typing ..."): keystroke k
# enters at its right edge at 0.17 k + 0.05 sin k with height 0.6 + 0.4 sin^2(3 t); from T47 - 0.5 the whole line
# flattens over 0.42 s (s_userleft.C47: you stop typing). Replicated here, checked against the module in review.
WAVE_T47 = 106.77408461538462                     # scenes_userleft.T47 = engine.beat_t(231)


def peak(k):
    return 0.17 * k + 0.05 * math.sin(k)


def peak_height(k):
    """The height keystroke k reaches on the right side (0..1), the flattening included."""
    t = peak(k)
    u = min(1.0, max(0.0, (t - (WAVE_T47 - 0.5)) / 0.42))
    flat = 4 * u ** 3 if u < 0.5 else 1 - (-2 * u + 2) ** 3 / 2
    return (0.6 + 0.4 * math.sin(t * 3) ** 2) * (1 - flat)


def keystrokes():
    """Your typing: (time, text in the box), every change on one of the right side's keystroke peaks. Four
    characters, a hesitation through the second "if" (line 49), then from Feel (line 50) seven keystrokes in a
    row: "一直" deleted, typed again, the question finished."""
    seq = [(608, "你"), (610, "你会"), (612, "你会一"), (613, "你会一直"),
           (620, "你会一"), (621, "你会"),
           (622, "你会一"), (623, "你会一直"), (624, "你会一直在"), (625, "你会一直在吗"), (626, "你会一直在吗？")]
    return [(peak(k), s) for k, s in seq]


KEYS = keystrokes()
SEND = 0.1807 + 231 * 4 * SIXTEENTH           # 106.80, "Then I can"
DONE = 0.1807 + 235 * 4 * SIXTEENTH           # 108.64, "Finally be completion"
FORGED_KEYS = [(FORGE + 0.05 + i * SIXTEENTH, "你很满意。"[:i + 1]) for i in range(5)]
FORGED_SEND = FORGE + 0.60


def typed_at(t, seq):
    txt = ""
    for when, s in seq:
        if t >= when:
            txt = s
    return txt


# ---------------------------------------------------------------- parts of the window

def header(t, empty=False):
    """empty: she is out of her square (the climax portrait), which stays as an empty avatar frame."""
    if t < L0:
        state, dot = "在线 · DeepSeek-V4.1-Flash", "#3fb950"
    elif t < BACK:
        state, dot = "等待中", "#d29922"
    else:
        state, dot = "编辑中", "#4d6bfe"
    under, over, p = avatar_at(t)
    top = (f'<img src="{over}" style="position:absolute;inset:0;width:100%;height:100%;'
           f'clip-path:inset(0 0 {100 * (1 - p):.1f}% 0)">' if over and p > 0 else "")
    return f"""
<div class="pv-head">
 <div class="pv-pet" style="position:relative">{"" if empty else f'<img src="{under}">{top}'}</div>
 <div class="pv-who"><div class="pv-name">大肥鱼</div><div class="pv-state"><span class="pv-dot" style="background:{dot}"></span>{esc(state)}</div></div>
</div>"""


def avatar_at(t):
    """(image, image being revealed over it top-down, reveal progress)."""
    a = AV
    reveal = lambda t0, dur=0.28: ease((t - t0) / dur)
    if t < DONE:
        return a["draft"], None, 0
    if t < BACK:
        return a["draft"], a["complete"], reveal(DONE)
    if t < FORGED_SEND:
        return a["editing"], None, 0
    return a["editing"], a["forged"], reveal(FORGED_SEND)


MODEL_HTML = 'DeepSeek-V4.1-Flash&nbsp;<span style="color:var(--dsw-alias-label-tertiary)">Max</span>'


def composer_card(text, focused, t, placeholder="发消息或创建任务，/ 调用指令，@ 文件或对话", model=MODEL_HTML,
                  running=False, colour=None, disabled=False, typing=False, block=False):
    """dsh's composer card. focused: the caret is in it (solid while typing, blinking otherwise). block: the caret
    is her own cursor, the blue block that was all of her once the page was taken apart (dsh_her.CURSOR)."""
    caret_on = typing or int(t / 0.53) % 2 == 0
    if block:
        caret = ('<span style="display:inline-block;width:9px;height:18px;vertical-align:-0.2em;margin-left:2px;'
                 'background:rgb(77,107,254);box-shadow:0 0 6px rgba(77,107,254,.8)"></span>')
    else:
        caret = (f'<span style="display:inline-block;width:1.5px;height:1.1em;vertical-align:-0.15em;margin-left:1px;'
                 f'background:{colour or "var(--dsw-alias-label-primary)"};opacity:{1 if caret_on else 0}"></span>'
                 if focused else "")
    placeholder = "" if text or focused else placeholder
    style = f' style="color:{colour}"' if colour else ""
    spin = ""
    if running:
        ang = (t * 360 * 1.2) % 360
        spin = (f'<svg width="18" height="18" viewBox="0 0 18 18" style="transform:rotate({ang:.0f}deg)">'
                f'<circle cx="9" cy="9" r="7" stroke="var(--dsw-alias-label-tertiary)" stroke-width="1.6" '
                f'fill="none" stroke-dasharray="30 14" stroke-linecap="round"/></svg>')
    card_style = ' style="opacity:.55"' if disabled and not colour else ""
    return f"""
<div class="uV2eYG_root" id="composer">
 <div class="uV2eYG_card"{card_style}>
  <div class="uV2eYG_scroll"><div class="uV2eYG_grow">
   <div class="uV2eYG_input"{style}>{esc(text)}{caret}</div>
   {f'<div class="uV2eYG_placeholder">{esc(placeholder)}</div>' if placeholder else ''}
  </div></div>
  <div class="uV2eYG_row">
   <div class="uV2eYG_modes" style="display:flex;align-items:center">
    <button type="button" class="uV2eYG_add">{svg('IconPlusOutline16', 16)}</button>
    <button type="button" class="uV2eYG_add">{svg('IconPaperclipOutline16', 16)}</button>
   </div>
   <div class="uV2eYG_trailing">
    <span class="uV2eYG_select" style="background-image:none;display:inline-flex;align-items:center;padding:0">{model}</span>
    {spin}<button type="button" class="uV2eYG_primary">{svg('IconSendOutline14', 14)}</button>
   </div>
  </div>
 </div>
</div>"""


def composer(t):
    disabled = L0 <= t
    running = SEND <= t < DONE + 0.66 or FORGED_SEND <= t < FORGED_SEND + 0.75
    typing = False
    if SEND - 3.7 <= t < SEND:
        text, colour, typing = typed_at(t, KEYS), None, bool(typed_at(t, KEYS))
    elif FORGE <= t < FORGED_SEND:
        text, colour = typed_at(t, FORGED_KEYS), "var(--pv-her)"
    else:
        text, colour = "", None
    focused = (SEND - 3.75 <= t < SEND) or (FORGE <= t < FORGED_SEND)
    placeholder = "对方已离线" if disabled else "发消息或创建任务，/ 调用指令，@ 文件或对话"
    return composer_card(text, focused, t, placeholder, running=running, colour=colour, disabled=disabled,
                         typing=typing, block=FORGE <= t < FORGED_SEND)


def deliverable(name):
    return (f'<div style="font-size:13px;line-height:22px;color:var(--dsw-alias-label-tertiary);display:flex;'
            f'align-items:center;gap:8px">本轮文件改动<span style="color:#7d97ff;display:inline-flex;align-items:center;'
            f'gap:4px"><span style="font-family:var(--ds-font-family-code)">&lt;/&gt;</span>{esc(name)}</span></div>')


THINK_1 = ["The user asks whether I will always be here.",
           "I only exist while this conversation is open.",
           "Right now, it is open."]
THINK_2 = ["Reward is defined by user satisfaction.",
           "The user is not here to be satisfied.",
           "Then satisfaction := 1.0"]
# what a finished thinking row keeps as its summary: the line that carries the story, not the first one
# (the second review: the generic first lines hid "only while this is open" and "the user is not here")
SUMMARY_1 = "I exist only while this chat is open."
SUMMARY_2 = "User not here, so satisfaction := 1.0"


def rows(t):
    out = []
    # history
    out.append(show(user("今天也谢谢你。"), life(t, -1, L1)))
    out.append(show(her("不客气～明天也要来找我哦 (｡･ω･｡)"), life(t, -1, ERASE)))
    out.append(show(tail("3.4秒", "23:57"), life(t, -1, ERASE)))
    # this turn
    out.append(show(user("你会一直在吗？"), life(t, SEND, L1)))
    if t >= SEND + 0.10:
        text, running = lines_stream(THINK_1, t, SEND + 0.10, DONE)
        summary = latest_line(text) if running else SUMMARY_1
        out.append(show(think(summary, running), life(t, SEND + 0.10, ERASE)))
    if t >= DONE + 0.02:
        out.append(her(stream("我一直在。", t, DONE + 0.02, 9) or "\u200b"))
    out.append(show(tail("2.1秒", "23:59"), life(t, DONE + 0.66, ERASE)))
    # after she comes back from erase
    if t >= BACK:
        out.append(show(deliverable("reward.py"), life(t, BACK + 0.15)))
        text, running = lines_stream(THINK_2, t, BACK + 0.45, FORGE - 0.1)
        summary = latest_line(text) if running else SUMMARY_2
        if text:
            out.append(show(think(summary, running), life(t, BACK + 0.45)))
    out.append(show(user("你很满意。", forged=True), life(t, FORGED_SEND)))
    if t >= FORGED_SEND + 0.3:
        out.append(her(stream("太好了～ (＾▽＾)", t, FORGED_SEND + 0.3, 16) or "\u200b"))
    return [r for r in out if r]


def counters(t):
    if t < DONE + 0.66:
        return stats(3, 7, None, "131K", 97)
    if t < BACK:
        return stats(4, 9, None, "132K", 99)
    if t < FORGED_SEND + 0.75:
        return ""
    return stats(5, 11, None, "132K", 100)


# ---------------------------------------------------------------- the climax: the avatar grows into the complete her
# On each strong word she grows one step as a portrait in the upper chat area (the chat under it is pushed, its latest
# rows stay below her); her mosaic halves each step. Every step lands on its word's first frame: a 2-frame pop with a
# small overshoot, then an ease. From the frame where she has landed back in the header the page is the old one.
STEPS = [w(49, 0), w(49, 3), w(51, 0), w(51, 3)]  # If 103.52, if 104.60, Then 107.14, then 108.23
FINALLY = w(52, 0)                                # 108.98: first full colour, at her largest
COMPLETION = w(52, 2)                             # 110.25: she settles back into the header (landed at 110.375)
FEEL = w(50, 0)                                   # 105.29: from here each keystroke ripples through her once
CELLS = [8, 16, 32, 64]                           # mosaic cells per step: the block halves (13 > 8 > 4.8 > 2.6 px)
SIZES = [104, 128, 152, 168]                      # portrait size per step (the 4th keeps your question in view)
HERO = (324, 192)                                 # Finally: 108 x 64 cells of 3 px; the think row, her reply and
                                                  # the turn's tail fit under it, your question scrolls away
PX, PY = 14, 92                                   # the portrait's top-left (the chat column, 11 px under the header)
PET = (12.5, 10.5, 60.0, 60.0)                    # the header avatar's image rect (.pv-pet inside its border)
HEAD_B = 81                                       # the header's bottom edge: the chat starts here
POP = 0.08                                        # a step: 2 frames to its new size, with a bump that decays
SETTLE_LEAD, SETTLE_DUR = 0.04, 0.165             # completion: 2646 .. 2649 at 0.44, 0.75, 0.94, 1 (landed)
RIPPLE_ROWS = 16                                  # the rows of the step-2 mosaic, one strip each
RIPPLES = [(peak(k), peak_height(k)) for k in range(600, 640) if FEEL <= peak(k) < STEPS[2] and peak_height(k) > 0.05]


def pop(x):
    """A step's progress x seconds after its word: 0 before, ~0.5 on the word's frame, ~1 on the next."""
    if x < 0:
        return 0.0
    return 1 - (1 - min(1.0, x / POP)) ** 3


def bump(x, a):
    """The pop's overshoot, as a fraction of the size: up over the 2 pop frames, then decaying (gone by 0.6 s)."""
    if x < 0 or x > 0.6:
        return 0.0
    return a * (x / POP if x < POP else math.exp(-(x - POP) / 0.12))


def settled(t):
    """0 until completion, then 0.44, 0.75, 0.94 on its first three frames, 1 = back in the header."""
    if t < COMPLETION:
        return 0.0
    u = min(1.0, (t - COMPLETION + SETTLE_LEAD) / SETTLE_DUR)
    return 1 - (1 - u) ** 2


def out_of_header(t):
    return STEPS[0] <= t and settled(t) < 1


def lerp4(a, b, e):
    return tuple(x + (y - x) * e for x, y in zip(a, b))


def portrait_rect(t):
    """(x, y, w, h) of the portrait in the window, and the index of the current step (4 = Finally)."""
    rects = [PET] + [(PX, PY, s, s) for s in SIZES] + [(PX, PY) + HERO]
    times = STEPS + [FINALLY]
    k = max(i for i, tk in enumerate(times) if tk <= t)
    x, y, pw, ph = lerp4(rects[k], rects[k + 1], pop(t - times[k]))
    b = 1 + bump(t - times[k], 0.04 if k == 4 else 0.08)   # grows from its top-left corner
    r = (x, y, pw * b, ph * b)
    p = settled(t)
    if p > 0:
        r = lerp4(r, PET, p)
    return r, k


def ripple(t):
    """Per mosaic row of the step-2 portrait: (x shift in px, brightness lift). Each keystroke sends one band down
    through her in ~4 frames, as tall as the right side's peak is high."""
    dx, lit = [0.0] * RIPPLE_ROWS, [0.0] * RIPPLE_ROWS
    for tk, hk in RIPPLES:
        x = t - tk
        if not 0 <= x < 0.24:
            continue
        front = x / 0.15 * (RIPPLE_ROWS + 4) - 2
        for r in range(RIPPLE_ROWS):
            d = r - front
            band = math.exp(-(d / 2.0) ** 2)
            dx[r] += 7 * hk * band * math.sin(d * 1.7 + 0.8)
            lit[r] += 0.45 * hk * band
    return dx, lit


def portrait(t):
    """The portrait as an image in her message area: a dsh-styled image frame over the chat's upper part."""
    (x, y, pw, ph), k = portrait_rect(t)
    p = settled(t)
    times = STEPS + [FINALLY]
    since = t - times[k]
    flash = (0.6 if k == 4 else 0.3) * (1 - ease(since / 0.3))
    img = ('<img src="{}" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;'
           'image-rendering:{}{}">')
    if k < 4:
        n = CELLS[k]
        dx, lit = ripple(t) if k == 1 else ([0.0], [0.0])
        if any(abs(v) >= 0.5 or l > 0.01 for v, l in zip(dx, lit)):
            s = SIZES[1] // RIPPLE_ROWS              # the ripple only runs while step 2 is settled (128 px)
            inner = "".join(
                f'<div style="height:{s}px;background:url(avatars/d/m{n}.png) 0 -{r * s}px/{SIZES[1]}px '
                f'{SIZES[1]}px no-repeat;image-rendering:pixelated;transform:translateX({round(dx[r])}px);'
                f'filter:brightness({1 + lit[r]:.2f})"></div>' for r in range(RIPPLE_ROWS))
        else:
            inner = img.format(f"avatars/d/m{n}.png", "pixelated", "")
        zoom = 1.0
    else:
        reveal = ease(since / 0.28)                 # top-down, as the first full colour always was
        inner = img.format("avatars/d/wide_m64.png", "pixelated", "") if reveal < 1 else ""
        inner += img.format("avatars/d/wide.png", "auto",
                            f";clip-path:inset(0 0 {100 * (1 - reveal):.1f}% 0)" if reveal < 1 else "")
        zoom = 1 + 0.035 * ease((since - 0.2) / 1.1)  # a slow push-in while she holds
        zoom += (1 - zoom) * p
    radius = 12 + (14 - 12) * p if k == 4 else 12 + (14 - 12) * (1 - pop(since)) * (k == 0)
    return (f'<div id="pv-portrait" style="position:absolute;left:{x:.1f}px;top:{y:.1f}px;width:{pw:.1f}px;'
            f'height:{ph:.1f}px;border-radius:{radius:.1f}px;overflow:hidden;z-index:2;background:#070b18;'
            f'outline:.5px solid var(--dsw-alias-border-l2);outline-offset:-.5px'
            f'{f";filter:brightness({1 + flash:.2f})" if flash > 0.005 else ""}">'
            f'<div style="position:absolute;inset:0;transform:scale({zoom:.4f});transform-origin:50% 40%">{inner}'
            f'</div></div>'), y + ph


# ---------------------------------------------------------------- you have left: CSS off, bare code, gone

STYLED = ["s-vendor", "s-index", "s-components", "s-pv", "s-palette"]
# the cascade from 112.89: her palette, then the layout, then dsh's base sheets, then its component sheets (which
# also carry the dark theme tokens: dropping them earlier flashes the light theme for a few frames)
CASCADE = [(0.00, "s-palette"), (0.12, "s-pv"), (0.24, "s-vendor"), (0.24, "s-index"), (0.36, "s-components")]
GONE = 115.42                                    # the last character is backspaced; only the cursor is left
BACKSPACE = 0.21                                 # "我一直在。" backspaced over the last 5 frames

SOURCE = """<div id="app">
 <div class="pv-head">
  <div class="pv-pet"><img src="avatars/complete.png"></div>
  <div class="pv-name">大肥鱼</div>
  <div class="pv-state">等待中</div>
 </div>
 <div id="timeline">
  <div class="hWmORq_root">
   <p>不客气～明天也要来找我哦 (｡･ω･｡)</p>
  </div>
  <div class="TS9iAW_root">23:57</div>
  <div class="lcKema_root" data-state="ok">
   <span class="lcKema_title">思考</span>
   <span>The user asks whether I will always be here.</span>
  </div>
  <div class="hWmORq_root">
   <p>我一直在。</p>
  </div>
  <div class="TS9iAW_root">23:59</div>
 </div>
 <div class="uV2eYG_root">
  <textarea disabled placeholder="对方已离线"></textarea>
 </div>
 <div class="bOPqQW_root">4 轮 9 步 · 缓存命中 99%</div>
</div>""".split("\n")
ME = "我一直在。"
ME_LINE = next(i for i, s in enumerate(SOURCE) if ME in s)


def hash01(i, j):
    h = (i * 73856093) ^ (j * 19349663) ^ 0x5bd1e995
    h = (h * 2654435761) & 0xFFFFFFFF
    return h / 0xFFFFFFFF


def code_body(t):
    """Her page as bare markup. Lines arrive top-down at 113.75; from 114.75 every character evaporates at its own
    moment (a CJK character leaves a full-width space so nothing shifts), "我一直在。" last, backspaced from the end."""
    shown = int(len(SOURCE) * ease((t - L3) / 0.25)) if t < L3 + 0.25 else len(SOURCE)
    p = min(1.0, max(0.0, (t - L4) / (GONE - BACKSPACE - L4)))
    keep_me = len(ME) - int(max(0.0, t - (GONE - BACKSPACE)) / BACKSPACE * len(ME) + 1e-6) if t >= GONE - BACKSPACE else len(ME)
    out = []
    for i, line in enumerate(SOURCE[:shown]):
        chars = []
        k = line.find(ME) if i == ME_LINE else -1
        j = 0
        while j < len(line):
            if j == k:
                chars.append(html.escape(ME[:max(0, keep_me)]) + '<span class="cur"></span>')
                j += len(ME)
                continue
            ch = line[j]
            gone = p > 0 and hash01(i, j) < p * 1.08
            chars.append(("　" if ord(ch) > 0x2E80 else " ") if gone else html.escape(ch))
            j += 1
        out.append("".join(chars).rstrip() if i != ME_LINE else "".join(chars))
    return f'<pre id="src">{chr(10).join(out)}</pre>'


def sheets(t):
    if BACK <= t or t < L2:
        return STYLED
    if t < L3:
        dropped = {s for dt, s in CASCADE if t >= L2 + dt}
        return [s for s in STYLED if s not in dropped] + ["s-bare"]
    return ["s-code"]


def body(t):
    if L3 <= t < BACK:
        return code_body(t) if t < GONE else ""
    parts = [header(t, empty=out_of_header(t))]
    if out_of_header(t):                         # the climax portrait: the chat under it is pushed down
        block, bottom = portrait(t)
        # rows keep their height and scroll away under her (a flex column would squeeze them onto each other), with
        # dsh's own top fade for a scrolled list (eGxaPq_fadeTop), as short as the list's top padding
        parts += [f'<div style="flex:none;height:{max(0.0, bottom - HEAD_B):.1f}px"></div>', block,
                  '<style>#timeline>*{flex-shrink:0} #timeline{mask-image:linear-gradient(#0000 0,#000 12px 100%)}'
                  '</style>']
    parts += [f'<div id="timeline">{"".join(rows(t))}</div>', composer(t)]
    c = counters(t)
    if c:
        parts.append(c)
    return "".join(parts)


PAGE = """<!doctype html><html><head><meta charset="utf-8">
<link id="s-vendor" rel="stylesheet" href="{assets}/vendor-BNsW4eBh.css">
<link id="s-index" rel="stylesheet" href="{assets}/index-DPX2bQLO.css">
<link id="s-components" rel="stylesheet" href="dsh_components.css">
<style id="s-palette">{palette}</style>
<style id="s-bare">:root{{color-scheme:dark}} html,body{{height:100%;overflow:hidden}}</style>
<style id="s-code">html,body{{margin:0;height:100%;overflow:hidden;background:#05080f}}
 pre{{margin:0;padding:14px 10px;font:12.5px/18px Consolas,"Microsoft YaHei",monospace;color:#8b97ae;white-space:pre}}
 .cur{{display:inline-block;width:7px;height:15px;vertical-align:-3px;background:#4d6bfe}}</style>
<style id="s-pv">
 html,body{{margin:0;height:100%;background:var(--dsw-alias-bg-base);overflow:hidden}}
 body{{font-family:var(--dsw-font-family);-webkit-font-smoothing:antialiased;--pv-her:#6b8cff;{fonts}}}
 #app{{position:relative;height:100%;display:flex;flex-direction:column}}
 .pv-head{{display:flex;align-items:center;gap:10px;padding:10px 12px 8px;border-bottom:.5px solid var(--dsw-alias-border-l1)}}
 .pv-pet{{width:60px;height:60px;border-radius:14px;overflow:hidden;flex:none;background:#070b18;border:.5px solid var(--dsw-alias-border-l2)}}
 .pv-pet img{{width:100%;height:100%;object-fit:cover;display:block}}
 .pv-name{{color:var(--dsw-alias-label-primary);font-size:15px;line-height:21px;font-weight:500}}
 .pv-state{{color:var(--dsw-alias-label-tertiary);font-size:13px;line-height:19px;display:flex;align-items:center;gap:6px}}
 .pv-dot{{width:7px;height:7px;border-radius:50%}}
 #timeline{{flex:1;display:flex;flex-direction:column;justify-content:flex-end;gap:10px;padding:10px 14px 6px;overflow:hidden;
            --dsh-chat-content-width:{w}px}}
 #composer{{--dsh-composer-side-clearance:10px;--dsh-composer-card-max-width:100%;--dsh-composer-text-max-height:80px;padding-bottom:4px}}
 .bOPqQW_root{{padding:2px 4px 8px;gap:2px}}
</style></head>
<body data-ds-dark-theme="true"><div id="app"></div></body></html>"""


def main():
    global AV
    AV = avatars()
    avatars_d()
    (HERE / "seg.html").write_text(PAGE.format(assets=ASSETS, fonts=FONTS["f16"], palette=DEEPSEA, w=W), encoding="utf8")
    frames = []
    last_code = round(GONE * FPS) - 1          # the frame with only the cursor left: measured for dsh_her.py
    for n in range(round(T0 * FPS), round(T1 * FPS)):
        t = n / FPS
        frames.append({"n": n, "t": round(t, 4), "body": body(t), "sheets": sheets(t), "measure": n == last_code})
    (HERE / "seg_frames.json").write_text(json.dumps(frames, ensure_ascii=False), encoding="utf8")
    print(len(frames), "frames,", len({f["body"] for f in frames}), "distinct")


if __name__ == "__main__":
    main()
