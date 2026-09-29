"""Batch A3 (29.28-44.0 s, verse 1, still 01 PRETRAIN): she does not know what she is.

    python batch_a3.py        -> a3_frames.json, avatars/a3/NNNNN.png
    node seg_shot.mjs a3_frames.json

The song's lines offer her shapes, and the right side draws them (embedding points, RoPE's circle, sinusoids, YaRN
stretching to infinity). In the chat, on each of those lines, you ask the checkpoint "你是谁？". A base model trained on
exam papers turns the question into a multiple-choice item whose options are those same four shapes, and then, asked
again, picks a different option every time: it has no identity yet, and each answer lands on the shape the right side
is drawing at that moment, with a one-line "解析" that is the actual technique being shown there. Option D is
infinity: it answers D, starts listing what it is and cannot stop, faster and faster, until dsh's own output-token cap
cuts it off on "be my limitations". The left never restates the lyric; it answers it.

  29.72  你是谁？ -> （  ）A. 一个点 B. 一个圆 C. 一条正弦曲线 D. 无穷  答案：A   (points)
  32.95  你是谁？ -> 答案：B  解析：位置是一个旋转角度。                        (circle, RoPE)
  36.64  你是谁？ -> 答案：C  解析：每个位置是一组 sin 和 cos。                 (sine)
  38.95  你是谁？ -> 答案：D。我是一个语言模型，我可以……   (asked on the tangent; from the infinity shot it floods at ~500 tok/s)
  41.92  已达到输出 token 上限
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

from PIL import Image, ImageOps

import batch_a1 as A1
import batch_a2 as A2
from build_frame import esc, stats, tail, user
from build_frame import her as her_row
from seg_page import composer_card, ease
from sung_words import w

HERE = Path(__file__).parent
FPS = 24
T0, T1 = 29.28, 44.0
beat = A1.beat
LIMIT = w(16, 5)          # 43.56, sung "limitations": the output-token cap
ASK = "你是谁？"
QUIZ = "（　　）\nA. 一个点　B. 一个圆\nC. 一条正弦曲线　D. 无穷\n答案：A"
CAN = ("回答问题", "写诗", "写代码", "陪你聊天", "翻译", "做数学题", "写作文", "讲故事", "查资料", "总结文章", "写邮件",
       "做计划", "起名字", "画表格", "解释概念", "改简历", "写歌", "背单词", "算账", "下棋", "讲笑话", "写菜谱", "写周报",
       "写论文", "写剧本", "做 PPT", "写小说", "改 bug", "写测试", "读论文", "做翻译", "写影评", "出考题", "改作文")
# she answers D and starts listing what she is; the list runs out and the model degenerates into repetition
RAMBLE = ("答案：D。我是一个语言模型，" + "".join(f"我可以{c}，" for c in CAN) + "我可以" * 800)
# (send, reply, reply start, chars per second, reply end, clock); the last one accelerates and is cut at LIMIT
TURNS = [
    # each "你是谁？" is sent on the line's "If"; the chosen option lands on the sung shape word (words.py)
    (w(9, 0), QUIZ, w(9, 0) + 0.18, (len(QUIZ) - 1) / (w(9, 5) - w(9, 0) - 0.18), None, "22:40"),   # A on "point"
    (w(11, 0), "答案：B\n解析：位置是一个旋转角度。", w(11, 3) - 3 / 13, 13, None, "23:02"),         # B on "circle"
    (w(13, 0), "答案：C\n解析：每个位置是一组 sin 和 cos。", w(13, 3) - 3 / 13, 13, None, "23:15"),  # C on "sine"
    (w(14, 7), RAMBLE, w(14, 7) + 0.15, None, LIMIT, "23:31"),   # asked on "tangents", floods into infinity
]
TYPE_AHEAD = 0.5
DOT = "_dot_1tljr_3"


INFINITY, FLOOD = w(15, 2), 750    # ramps up from "approach" (full on "infinity"); ~500 tok/s of Chinese


def _rate(t):
    """Characters per second: 14 while she lists, rising over 0.3 s from the infinity shot to FLOOD."""
    return 14 + (FLOOD - 14) * ease((t - INFINITY) / 0.3)


def ramble_chars(t, start, _cache={}):
    """Characters streamed by t (the integral of _rate), frozen at the cap."""
    t = min(t, LIMIT)
    k = round(max(0.0, t - start) * 240)
    if (start, k) not in _cache:
        _cache[(start, k)] = sum(_rate(start + (j + 0.5) / 240) for j in range(k)) / 240
    return int(_cache[(start, k)])


def reply(i, t):
    send, text, start, rate, end, _ = TURNS[i]
    if t < start:
        return ""
    n = ramble_chars(t, start) if rate is None else int((t - start) * rate)
    return text[:n]


def reply_end(i):
    send, text, start, rate, end, _ = TURNS[i]
    return end if end is not None else start + len(text) / rate


def max_tokens_notice(p):
    return f"""
<div class="Sixlwa_turnErrorRow" role="status" style="opacity:{p:.3f}">
 <span class="{DOT} Sixlwa_turnErrorDot" data-state="warning" style="width:10px;height:10px;border-radius:50%;background:currentColor"></span>
 <div class="Sixlwa_turnErrorCopy"><span class="Sixlwa_maxTokensTitle">已达到输出 token 上限</span><span class="Sixlwa_turnErrorMessage">回答被截断，已有输出保留在对话中。发送“继续”可让模型接着输出。</span></div>
</div>"""


def avatars():
    out = HERE / "avatars" / "a3"
    out.mkdir(parents=True, exist_ok=True)
    im = Image.open(A2.EXPR / "whale-cheerful.webp").convert("RGBA")
    bg = Image.new("RGBA", im.size, (9, 14, 30, 255))
    bg.alpha_composite(im)
    head = ImageOps.grayscale(bg.convert("RGB").crop((250, 40, 690, 480)))
    for n in range(round(T0 * FPS), round(T1 * FPS)):
        t = n / FPS
        p = A2.progress(t)
        q = (t - T0) / (T1 - T0)
        cells = 3 + round(7 * p) + round(2 * q)        # carries on from A2: 10 -> 12 cells
        g = head.resize((cells, cells), Image.Resampling.BOX).resize((12, 12), Image.Resampling.NEAREST)
        rng = random.Random(n)
        noise = Image.new("L", (12, 12))
        noise.putdata([rng.randrange(256) for _ in range(144)])
        mix = Image.blend(g, noise, (1 - p) ** 1.5)
        ImageOps.colorize(mix, (6, 10, 28), (120, 150, 255)).resize((120, 120), Image.Resampling.NEAREST) \
            .save(out / f"{n:05d}.png")


def header(t):
    return f"""
<div class="pv-head">
 <div class="pv-pet"><img src="avatars/a3/{round(t * FPS):05d}.png" style="image-rendering:pixelated"></div>
 <div class="pv-who"><div class="pv-name">大肥鱼</div><div class="pv-state"><span class="pv-dot" style="background:#d29922"></span>预训练中 · {esc(A1.model_name(t))}</div></div>
</div>"""


def history():
    """The tail end of A2's conversation, fully settled (it scrolls away as A3 adds rows)."""
    rows = []
    for i in range(len(A2.TURNS)):
        send, _, _, _, end, clock = A2.TURNS[i]
        rows += [user("你好"), her_row(A2.reply_text(i, 1e9) or "​"), tail(f"{end - send:.1f}秒", clock)]
    return rows


HISTORY = None


def final_tokens():
    return 252 + 60 * 3 + round(ramble_chars(LIMIT, TURNS[3][2]) / 1.5)


def body(t):
    global HISTORY
    if HISTORY is None:
        HISTORY = history()
    rows = list(HISTORY)
    typing, done = "", 0
    for i, (send, _, _, _, _, clock) in enumerate(TURNS):
        if send - TYPE_AHEAD <= t < send:
            typing = ASK[: 1 + int((t - (send - TYPE_AHEAD)) / TYPE_AHEAD * len(ASK))]
        if t < send:
            continue
        rows.append(f'<div style="opacity:{ease((t - send) / 0.12):.3f}">{user(ASK)}</div>')
        rows.append(her_row(reply(i, t) or "​"))
        end = reply_end(i)
        if i < 3 and t >= end + 0.1:
            rows.append(tail(f"{end - send:.1f}秒", clock))
            done += 1
        if i == 3 and t >= LIMIT:
            rows.append(max_tokens_notice(ease((t - LIMIT) / 0.1)))
    sent = sum(1 for s, *_ in TURNS if t >= s)
    running = any(s <= t < reply_end(i) + 0.1 for i, (s, *_) in enumerate(TURNS))
    rs = TURNS[3][2]
    tokens = 252 + 60 * done + (0 if t < rs else round(ramble_chars(t, rs) / 1.5))
    tok = f"{tokens / 1000:.1f}K" if tokens >= 1000 else str(tokens)
    return (header(t) + f'<div id="timeline">{"".join(rows)}</div>'
            + composer_card(typing, bool(typing), t, model=A1.model_label(t), running=running, typing=bool(typing))
            + stats(4 + sent, 4 + sent, None, tok, [66, 70, 74, 77, 77][min(done + (t >= LIMIT), 4)]))


STYLED = A1.STYLED


def main():
    avatars()
    frames = [{"n": n, "t": round(n / FPS, 4), "body": body(n / FPS), "sheets": STYLED, "measure": False}
              for n in range(round(T0 * FPS), round(T1 * FPS))]
    (HERE / "a3_frames.json").write_text(json.dumps(frames, ensure_ascii=False), encoding="utf8")
    print(len(frames), "frames,", len({f["body"] for f in frames}), "distinct")


if __name__ == "__main__":
    main()
