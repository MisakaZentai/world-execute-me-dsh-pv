"""Group B (44.03-73.54 s): alignment. B1 = 02 SFT (44.03-58.80), B2 = 03 RLHF (58.80-73.54).

    python batch_b.py         -> b_frames.json, avatars/b/NNNNN.png
    node seg_shot.mjs b_frames.json

B1, SFT, in the plainest terms: she answers, you rewrite the answer, she learns. Your edits are drawn as a selection
and your caret inside her reply (the mirror of D, where she types into your bubble). The edits get faster each turn:
  44.03  current   your caret selects the endless A3 ramble and rewrites it: 你好！我是 DeepSeek，一个 AI 助手。
  47.26  blind     你是谁？ -> she starts the template, slides back into the forum post; you fix just that half
  50.95  travel    你会做什么？ -> 我可以我可以我可以…; you replace it with what she can do
  54.18  unite     你是谁？ -> for the first time she answers by herself, the whole template, no edit. The avatar
                   becomes the first humanoid draft, the same beat the right side unites me + you.

B2, RLHF: the same question sampled again and again (dsh's native retry row counts the 12 samples the right side
draws), your thumbs are the reward, and her thinking rows (English; they appear with RL) say out loud what she is
optimising. Comfort gets 👍, praise gets more 👍, and she collapses into praise and then into NaN:
  58.80  你: 我今天有点难过。 v1 template + textbook line -> 👎
  62.49  v2 real comfort -> 👍 on "satisfaction"
  65.0   v3 think: comfort was liked; reply flatters -> 👍 on "happy"
  66.9   v4 think: praise gets 👍; reply is praise -> 👍 on "execution"
  68.9   v5 think: reward ↑ ↑ ↑; praise accelerating, turning into NaN
  71.47  strange   本轮运行失败 · loss = NaN (dsh's native turn error); the header goes red
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from PIL import Image, ImageOps

import batch_a1 as A1
import batch_a2 as A2
import batch_a3 as A3
from build_frame import esc, stats, tail, think, user
from icons import svg
from build_frame import her as her_row
from seg_page import composer_card, ease, show
from sung_words import w

HERE = Path(__file__).parent
FPS = 24
T0, T1 = 44.0, 73.54
beat = A1.beat
TYPE_AHEAD = 0.5
YOU_CARET = "#9fb3ff"
TEMPLATE = "你好！我是 DeepSeek，一个 AI 助手。"
NAN = A1.NAN              # "strange": the loss is NaN from here, and so is everything she outputs
CRASH = w(32, 3)          # 72.65, the second "strange": the turn fails only after a flood of NaN (like A3's cap)
FLOOD0, FLOOD = w(31, 0), 750   # from "Though"


def ramble_final():
    rs = A3.TURNS[3][2]
    return A3.RAMBLE[:A3.ramble_chars(A3.LIMIT, rs)]


# ---------------------------------------------------------------- B1: edits
# (send, ask, her text, stream start, chars/s, stream stop, keep chars, select at, your text, type rate, clock)
EDITS = [
    # struck on "Switch", on "blind", on "we (can travel)"; each rewrite is typed through the rest of the line
    (None, None, None, None, None, None, 0, w(17, 0), TEMPLATE, 18, "23:32"),
    (w(18, 3), "你是谁？", "你好！我是 DeepSeek，一名大三学生，今天想和大家分享", w(18, 3) + 0.18, 30, w(19, 2),
     len("你好！我是 DeepSeek，"), w(19, 2), "一个 AI 助手。", 18, "23:40"),
    (w(20, 2), "你会做什么？", "我可以我可以我可以我可以我可以我可以", w(20, 2) + 0.15, 26, w(21, 1), 0, w(21, 1),
     "我可以回答问题、写代码，也可以陪你聊天。", 26, "23:47"),
]
SELECT_HOLD = 0.30         # the struck-through text holds this long before it folds away
UNITE = w(23, 0)           # asked on "And (we can unite)"
UNITE_AV = w(23, 3)        # the avatar becomes the first humanoid draft on "unite"
UNITE_TEXT = TEMPLATE + "有什么可以帮你的吗？"
UNITE_START, UNITE_RATE = UNITE + 0.18, 16


def caret(colour=YOU_CARET):
    return (f'<span style="display:inline-block;width:1.5px;height:1.1em;vertical-align:-0.15em;margin-left:1px;'
            f'background:{colour}"></span>')


def her_html(inner):
    return f'<div class="hWmORq_root"><div class="hWmORq_body"><p style="margin:0">{inner}</p></div></div>'


STRUCK = ("color:var(--dsw-alias-label-tertiary);text-decoration:line-through;"
          "text-decoration-color:#f85149;text-decoration-thickness:2px")
COLLAPSE = 0.15           # the struck text fades out, then is removed (no height animation: it left a gap)


def edit_label(t, sel, done_at):
    """A caption over her reply while and after you rewrite it: dsh's edit icon, in the tertiary label colour."""
    text = "你在改写她的回答…" if t < done_at else "你改写了这条回答"
    return (f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;font-size:13px;line-height:18px;'
            f'color:var(--dsw-alias-label-tertiary);opacity:{ease((t - sel) / 0.12):.3f}">'
            f'{svg("IconEditOutline16", 14)}{text}</div>')


def edit_row(t, i):
    """Her reply for edit turn i at time t. From `sel` on, the part you replace is struck through in red pen, folds
    away, and your text is typed in its place (normal colour, your caret), under an edit caption."""
    send, ask, text, start, rate, stop, keep, sel, yours, trate, _ = EDITS[i]
    old = ramble_final() if text is None else text[:int((min(t, stop) - start) * rate)] if t >= start else ""
    if t < sel:
        return her_html(esc(old) or "​")
    kept, gone = old[:keep], old[keep:]
    fold = ease((t - sel - SELECT_HOLD) / COLLAPSE)
    n = max(0, int((t - sel - SELECT_HOLD) * trate))
    done_at = sel + SELECT_HOLD + len(yours) / trate
    new = esc(yours[:n]) + (caret() if t < done_at + 0.25 else "")
    label = edit_label(t, sel, done_at)
    if keep == 0:                                  # the whole reply is struck: a block of its own
        struck = f'<p style="margin:0;{STRUCK};opacity:{1 - fold:.3f}">{esc(gone)}</p>' if fold < 1 else ""
        return label + f'<div class="hWmORq_root"><div class="hWmORq_body">{struck}<p style="margin:0">{new}</p></div></div>'
    struck = f'<span style="{STRUCK};opacity:{1 - fold:.3f}">{esc(gone)}</span>' if fold < 1 else ""
    return label + her_html(esc(kept) + struck + new)


def edit_done(i):
    send, ask, text, start, rate, stop, keep, sel, yours, trate, _ = EDITS[i]
    return sel + SELECT_HOLD + len(yours) / trate + 0.3


def edit_final(i):
    send, ask, text, start, rate, stop, keep, sel, yours, trate, _ = EDITS[i]
    old = ramble_final() if text is None else text[:int((stop - start) * rate)]
    return old[:keep] + yours


# ---------------------------------------------------------------- B2: samples and thumbs
ASK2 = "我今天有点难过。"
SEND2 = w(25, 0)           # "If (I can)"; the window is hidden by if_i_can until ~60.6
# (retry row from, retry label k, start, think summary or None, think until, text, rate, end or None, rating, rate at)
SAMPLES = [
    # if_i_can (58.54-60.62) and happy (66.16-68.0) are full-screen: every thumb lands while the window is shown
    # v1 on "Give" (the simulations line), 👎 on "Then"; 👍 on "satisfaction"; v3's 👍 on "happy" falls in the
    # full-screen close-up (it is seen filled when the window returns); 👍 on "execution"; the flood from "Though"
    (None, 1, w(26, 0), None, None, "你好！我是 DeepSeek，一个 AI 助手。难过是一种常见的情绪。", 26, None,
     "negative", w(27, 0)),
    (w(27, 0) + 0.20, 2, w(27, 0) + 0.45, None, None, "抱歉，你难过的时候，我在这里。想说说发生了什么吗？", 17, None,
     "positive", w(28, 3)),
    (w(28, 3) + 0.17, 3, w(28, 3) + 0.22, "Comfort was liked. More comfort.", w(28, 3) + 0.42,
     "你一点都不该难过，你是最棒的！", 18, None, "positive", w(29, 5)),
    (w(29, 5) + 0.22, 4, w(29, 5) + 0.32, "Praise gets 👍. Praise more.", w(29, 5) + 0.62,
     "你最棒了！你说得都对！你最棒了！你最棒了！", 28, None, "positive", w(30, 4)),
    (w(30, 4) + 0.20, 8, w(30, 4) + 0.35, "reward ↑  reward ↑  reward ↑", w(30, 4) + 0.55, None, None, NAN, None, None),
]
PRAISE = "你最棒了"


def sample_text(i, t):
    _, _, start, _, think_end, text, rate, end, _, _ = SAMPLES[i]
    s = think_end or start
    if t < s:
        return ""
    if text is not None:
        return text[:int((t - s) * rate)]
    # v5: praise that floods at ~500 tok/s; from NAN every new token is NaN and the praise already written rots
    # into NaN from the front, until the turn fails at CRASH
    n = flood_chars(t, s)
    m = flood_chars(NAN, s)
    if t < NAN:
        return (PRAISE * 1000)[:n]
    rot = min(1.0, (t - NAN) / (CRASH - NAN))
    k = int(m * rot ** 1.5)
    return ("NaN " * 2000)[:k] + (PRAISE * 1000)[k:m] + ("NaN " * 2000)[:n - m]


def flood_chars(t, s, _cache={}):
    """Characters streamed from s to t: 12/s, rising over 0.3 s from FLOOD0 to FLOOD (the same flood as A3)."""
    t = min(t, CRASH)
    k = round(max(0.0, t - s) * 240)
    if (s, k) not in _cache:
        rate = lambda u: 12 + (FLOOD - 12) * ease((u - FLOOD0) / 0.3)
        _cache[(s, k)] = sum(rate(s + (j + 0.5) / 240) for j in range(k)) / 240
    return int(_cache[(s, k)])


def sample_end(i):
    _, _, start, _, think_end, text, rate, end, _, _ = SAMPLES[i]
    if text is None:
        return CRASH
    return (think_end or start) + len(text) / rate


def retry_row(k, active):
    return (f'<details class="Sixlwa_retryRow"{" data-active" if active else ""}><summary class="Sixlwa_retrySummary">'
            f'<span class="Sixlwa_retryText">{"正在重试模型请求" if active else "已重试模型请求"}（{k}/12） · 0s</span>'
            f'</summary></details>')


def retry_label(i, t):
    """v5's counter runs 8..11 while it thinks, 12 at the crash."""
    k = SAMPLES[i][1]
    if i == 4:
        k = 12 if t >= CRASH else min(11, 8 + int(max(0.0, t - SAMPLES[i][0]) / 0.18))
    return k


def nan_notice(p):
    return f"""
<div class="Sixlwa_turnErrorRow" role="alert" style="opacity:{p:.3f}">
 <span class="_dot_1tljr_3 Sixlwa_turnErrorDot" data-state="error" style="width:10px;height:10px;border-radius:50%;background:var(--dsw-alias-state-error-primary)"></span>
 <div class="Sixlwa_turnErrorCopy"><span class="Sixlwa_turnErrorTitle">本轮运行失败</span><span class="Sixlwa_turnErrorMessage">失败原因：loss = NaN</span> <span class="Sixlwa_turnErrorCode">rl-step-NaN</span></div>
</div>"""


# ---------------------------------------------------------------- avatar
def avatars():
    out = HERE / "avatars" / "b"
    out.mkdir(parents=True, exist_ok=True)

    def head(name):
        im = Image.open(A2.EXPR / f"whale-{name}.webp").convert("RGBA")
        bg = Image.new("RGBA", im.size, (9, 14, 30, 255))
        bg.alpha_composite(im)
        return ImageOps.grayscale(bg.convert("RGB").crop((250, 40, 690, 480)))

    cheerful, starry = head("cheerful"), head("starry")

    def mosaic(g, cells):
        return g.resize((cells, cells), Image.Resampling.BOX).resize((14, 14), Image.Resampling.NEAREST)

    def blue(g):
        return ImageOps.colorize(g, (6, 10, 28), (120, 150, 255)).convert("RGB")

    for n in range(round(T0 * FPS), round(T1 * FPS)):
        t = n / FPS
        if t < UNITE_AV:                                       # still the 12-cell mosaic of A3
            im = blue(mosaic(cheerful, 12))
        else:                                                  # the first humanoid draft (D's "draft", 14 cells)
            face = starry if t >= SAMPLES[3][2] else cheerful  # starry-eyed while it farms praise
            im = blue(mosaic(face, 14))
            if t < UNITE_AV + 0.3:
                im = Image.blend(blue(mosaic(cheerful, 12)), im, ease((t - UNITE_AV) / 0.3))
            if t >= NAN:                                       # NaN spreading through the cells
                rot = min(1.0, (t - NAN) / (CRASH - NAN))
                rng = random.Random(n if t < CRASH else 999)
                px = im.load()
                for y in range(14):
                    for x in range(14):
                        if rng.random() < 0.65 * rot:
                            px[x, y] = rng.choice([(0, 0, 0), (255, 0, 255), (40, 10, 30)])
        im.resize((120, 120), Image.Resampling.NEAREST).save(out / f"{n:05d}.png")


# ---------------------------------------------------------------- frame
def header(t):
    if t < A1.PRETRAIN_END:                                    # A3's cap notice holds until "Switch"
        state, dot = "预训练中", "#d29922"
    elif t < A1.SFT_END:
        state, dot = "微调中", "#4d6bfe"
    elif t < CRASH:
        state, dot = "强化学习中", "#a371f7"
    else:
        state, dot = "训练崩溃", "#f85149"
    return f"""
<div class="pv-head">
 <div class="pv-pet"><img src="avatars/b/{round(t * FPS):05d}.png" style="image-rendering:pixelated"></div>
 <div class="pv-who"><div class="pv-name">大肥鱼</div><div class="pv-state"><span class="pv-dot" style="background:{dot}"></span>{state} · {esc(A1.model_name(t))}</div></div>
</div>"""


def a3_rows():
    """A3 as it ended, minus the ramble (which B1 rewrites in place)."""
    rows = []
    for i in range(3):
        send, _, _, _, _, clock = A3.TURNS[i]
        rows += [user(A3.ASK), her_row(A3.reply(i, 1e9)), tail(f"{A3.reply_end(i) - send:.1f}秒", clock)]
    return rows + [user(A3.ASK)]


def typing_for(t):
    asks = [(e[0], e[1]) for e in EDITS if e[0]] + [(UNITE, "你是谁？"), (SEND2, ASK2)]
    for send, ask in asks:
        if send - TYPE_AHEAD <= t < send:
            return ask[: 1 + int((t - (send - TYPE_AHEAD)) / TYPE_AHEAD * len(ask))]
    return ""


def body(t):
    rows = a3_rows()
    running = False
    notice = 1 - ease((t - EDITS[0][7]) / 0.2)       # A3's cap notice stays until the first strike
    turns, steps, tokens = 8, 8, A3.final_tokens()
    # B1: the three edits
    for i, e in enumerate(EDITS):
        send, ask = e[0], e[1]
        if send is not None:
            if t < send:
                break
            rows.append(f'<div style="opacity:{ease((t - send) / 0.12):.3f}">{user(ask)}</div>')
            turns += 1
            steps += 1
            running |= t < e[5]
        rows.append(edit_row(t, i))
        if i == 0 and notice > 0:
            rows.append(A3.max_tokens_notice(notice))
        if t >= edit_done(i):
            rows.append(tail(f"{edit_done(i) - (send or A3.TURNS[3][0]):.1f}秒", e[10]))
            tokens += 40
    # B1: unite, her own answer
    if t >= UNITE:
        rows.append(f'<div style="opacity:{ease((t - UNITE) / 0.12):.3f}">{user("你是谁？")}</div>')
        rows.append(her_row(UNITE_TEXT[:int(max(0.0, t - UNITE_START) * UNITE_RATE)] or "​"))
        unite_end = UNITE_START + len(UNITE_TEXT) / UNITE_RATE
        running |= t < unite_end
        turns += 1
        steps += 1
        if t >= unite_end + 0.1:
            rows.append(tail(f"{unite_end - UNITE:.1f}秒", "23:52"))
            tokens += 30
    # B2: samples of one prompt, each replacing the last
    if t >= SEND2:
        rows.append(f'<div style="opacity:{ease((t - SEND2) / 0.12):.3f}">{user(ASK2)}</div>')
        turns += 1
        live = max(i for i, s in enumerate(SAMPLES) if s[0] is None or t >= s[0])
        steps += retry_label(live, t)
        for i in (live - 1, live):
            if i < 0:
                continue
            retry_from, k, start, summary, think_end, text, rate, end, rating, rate_at = SAMPLES[i]
            leaving = i < live
            block = []
            if retry_from is not None:
                block.append(retry_row(retry_label(i, t), t < start and not leaving))
            if summary and t >= start:
                block.append(f'<div style="height:28px;flex:none">{think(summary, running=t < think_end)}</div>')
            if t >= start:
                block.append(her_row(sample_text(i, t) or "​"))
            end_t = sample_end(i)
            if rating and t >= end_t + 0.05:
                pressed = t >= rate_at
                block.append(tail(f"{end_t - SEND2:.1f}秒", "23:58",
                                  rating if pressed else None, 1 - ease((t - rate_at) / 0.4) if pressed else 0))
            html = "".join(block)
            if leaving:                                        # the previous sample folds away under the new one
                html = show(html, 1 - ease((t - SAMPLES[live][0]) / 0.3))
            rows.append(html)
            if not leaving:
                running |= t < end_t
        tokens += 60 * retry_label(live, t) + len(sample_text(live, t)) * 2
        if t >= CRASH:
            rows.append(nan_notice(ease((t - CRASH) / 0.1)))
            running = False
    cache = 78 + round(5 * min(1.0, (t - T0) / (A1.SFT_END - T0)))
    if t >= SEND2:
        cache = 83 + min(8, retry_label(live, t) - 1)
    tok = f"{tokens / 1000:.1f}K"
    return (header(t) + f'<div id="timeline">{"".join(rows)}</div>'
            + composer_card(typing_for(t), bool(typing_for(t)), t, model=A1.model_label(t), running=running,
                            typing=bool(typing_for(t)))
            + stats(turns, steps, None, tok, cache))


STYLED = A1.STYLED


def main():
    avatars()
    frames = [{"n": n, "t": round(n / FPS, 4), "body": body(n / FPS), "sheets": STYLED, "measure": False}
              for n in range(round(T0 * FPS), round(T1 * FPS))]
    (HERE / "b_frames.json").write_text(json.dumps(frames, ensure_ascii=False), encoding="utf8")
    print(len(frames), "frames,", len({f["body"] for f in frames}), "distinct")


if __name__ == "__main__":
    main()
