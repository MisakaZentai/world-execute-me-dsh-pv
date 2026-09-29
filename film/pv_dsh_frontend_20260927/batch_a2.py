"""Batch A2 (16.0-29.28 s, 01 PRETRAIN, instrumental): she learns to talk, one checkpoint at a time.

    python batch_a2.py        -> a2_frames.json, avatars/a2/NNNNN.png
    node seg_shot.mjs a2_frames.json

You test each new checkpoint with the same "你好", two bars apart; the right side meanwhile runs the corpus river,
the loss curve, DualPipe and the checkpoint whale. What changes is only her answer, in the order a language model
really learns: frequent tokens first, then fragments, then fluent text that continues your post instead of answering
it (a base model has no idea it is in a conversation). No reasoning rows yet: those come after RL.

  16.0-17.3  the byte soup from A1 streams to its end; turn 1 ends
  18.18      checkpoint 1: the most frequent tokens, repeated
  21.87      checkpoint 2: fragments that start to hold together, two languages at once
  25.56      checkpoint 3: fluent Chinese that continues "你好" as the opening of a forum post
The avatar rises out of the noise as the loss falls; repeating the same prompt makes the cache hit climb.
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

from PIL import Image, ImageOps

import batch_a1 as A1
from build_frame import esc, stats, tail, user
from build_frame import her as her_row
from seg_page import SIXTEENTH, composer_card, ease

HERE = Path(__file__).parent
FPS = 24
T0, T1 = 16.0, 29.28
beat = A1.beat
EXPR = Path(__file__).resolve().parents[1].joinpath("third_party_references/whale_maid_expanded_20260926/expressions")


def soup(n):
    return "".join(A1.SOUP[i % len(A1.SOUP)] for i in range(n))


FREQ = "的 的 。the the , of 是 了 and 的 ， 我 the 。 。 在 a 的"
FRAG = "你好 你好 hello , the world 是 一个 的 时候 我们 is a 。 你 们 好 the day"
BASE = "你好，我是一名大三学生，今天想和大家分享一下我的考研经验。首先，要选对学校和专业……"

# (send, text, reply start, chars or tokens per second, reply end, clock)
TURNS = [
    (A1.SEND, soup, A1.SEND + 0.15, 14, 17.30, "00:12"),
    (beat(39), FREQ, beat(39) + 0.20, 22, beat(39) + 1.35, "03:47"),
    (beat(47), FRAG, beat(47) + 0.20, 20, beat(47) + 2.30, "09:30"),
    (beat(55), BASE, beat(55) + 0.20, 17, beat(55) + 2.95, "21:05"),
]
TYPE_AHEAD = 0.55          # "你好" is typed in the half second before each send


def reply_text(i, t):
    send, text, start, rate, end, _ = TURNS[i]
    if t < start:
        return ""
    n = int((min(t, end) - start) * rate)
    if callable(text):
        return text(n) if t < end else text(int((end - start) * rate))
    return text[:n] if t < end else text


def progress(t):
    """Training progress 0..1, the shape of the loss curve on the right."""
    return 1 - math.exp(-max(0.0, t - T0) / 5.0)


def avatars():
    out = HERE / "avatars" / "a2"
    out.mkdir(parents=True, exist_ok=True)
    im = Image.open(EXPR / "whale-cheerful.webp").convert("RGBA")
    bg = Image.new("RGBA", im.size, (9, 14, 30, 255))
    bg.alpha_composite(im)
    head = ImageOps.grayscale(bg.convert("RGB").crop((250, 40, 690, 480)))
    for n in range(round(T0 * FPS), round(T1 * FPS)):
        p = progress(n / FPS)
        cells = 3 + round(7 * p)                       # 3 -> 10 cells: an outline slowly comes into focus
        g = head.resize((cells, cells), Image.Resampling.BOX).resize((12, 12), Image.Resampling.NEAREST)
        rng = random.Random(n)
        noise = Image.new("L", (12, 12))
        noise.putdata([rng.randrange(256) for _ in range(144)])
        k = (1 - p) ** 1.5
        mix = Image.blend(g, noise, k)
        blue = ImageOps.colorize(mix, (6, 10, 28), (120, 150, 255))
        blue.resize((120, 120), Image.Resampling.NEAREST).save(out / f"{n:05d}.png")


def header(t):
    return f"""
<div class="pv-head">
 <div class="pv-pet"><img src="avatars/a2/{round(t * FPS):05d}.png" style="image-rendering:pixelated"></div>
 <div class="pv-who"><div class="pv-name">大肥鱼</div><div class="pv-state"><span class="pv-dot" style="background:#d29922"></span>预训练中 · {esc(A1.model_name(t))}</div></div>
</div>"""


def body(t):
    rows = []
    turns_done, typing = 0, ""
    for i, (send, _, _, _, end, clock) in enumerate(TURNS):
        if i and send - TYPE_AHEAD <= t < send:
            typing = "你好"[: 1 + int((t - (send - TYPE_AHEAD)) / (TYPE_AHEAD / 2) > 1)]
        if t < send:
            continue
        rows.append(f'<div style="opacity:{ease((t - send) / 0.12):.3f}">{user("你好")}</div>')
        rows.append(her_row(reply_text(i, t) or "\u200b"))
        if t >= end + 0.1:
            rows.append(tail(f"{end - send:.1f}秒", clock))
            turns_done += 1
    running = any(send <= t < end + 0.1 for send, _, _, _, end, _ in TURNS)
    cache = [0, 33, 50, 61, 66][turns_done]
    tokens = 12 + 60 * turns_done
    return (header(t) + f'<div id="timeline">{"".join(rows)}</div>'
            + composer_card(typing, bool(typing), t, model=A1.model_label(t), running=running, typing=bool(typing))
            + stats(len([1 for s, *_ in TURNS if t >= s]), len([1 for s, *_ in TURNS if t >= s]), None, str(tokens),
                    cache))


STYLED = A1.STYLED


def main():
    avatars()
    frames = [{"n": n, "t": round(n / FPS, 4), "body": body(n / FPS), "sheets": STYLED, "measure": False}
              for n in range(round(T0 * FPS), round(T1 * FPS))]
    (HERE / "a2_frames.json").write_text(json.dumps(frames, ensure_ascii=False), encoding="utf8")
    print(len(frames), "frames,", len({f["body"] for f in frames}), "distinct")


if __name__ == "__main__":
    main()
