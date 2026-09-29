"""Batch A1 (5.24-16.0 s, 00 BOOT): the dsh window is born from her seed, and she says her first word.

    python batch_a1.py        -> a1_frames.json, avatars/a1_*.png
    node seg_shot.mjs a1_frames.json

  5.24   cut 3 lands her seed in the left pane and grows the window out of it (s_boot.C03, unchanged): the window
         is dsh's home page. Her avatar square holds one blue pixel, which is the seed.
  7.19   "data parameters": the model selector is filled in, the avatar fills with empty parameter cells
  9.75   "Initialization": the avatar becomes random noise (random weights)
  10.90  "our new world": you open a workspace, new-world
  12.47  "begin the simulation": you type 你好 into the home composer
  14.95  you send it on RUN; the home page becomes a conversation. Her first reply is byte-level token soup,
         because a freshly initialised model samples its whole vocabulary at random. It is still streaming at 16.0,
         where 01 PRETRAIN takes over.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from PIL import Image, ImageDraw

from build_frame import esc, stats, svg, user
from build_frame import her as her_raw
from seg_page import SIXTEENTH, W, composer_card, ease

HERE = Path(__file__).parent
FPS = 24
T0, T1 = 5.0, 16.0
CREATE = 5.24
PARAMS, INIT, WORLD, BEGIN = 7.19, 9.75, 10.90, 12.47
beat = lambda k: 0.1807 + k * 4 * SIXTEENTH
SEND = beat(32)                                   # 14.95, RUN
KEYS = [(beat(28) + SIXTEENTH, "你"), (beat(28) + 3 * SIXTEENTH, "你好")]
MODEL = "DeepSeek-V4.1-Flash"                      # the official release (from 88.31 s)
SEED_Y = 177                                      # the seed lands on the window's chest point (her_anchor)
# a freshly initialised model: byte-level BPE pieces from anywhere in the vocabulary
SOUP = ("Ġthe", "çļĦ", "ĊĊ", "}]", "拟", "_{", "Ġ3", "ãĢĤ", "ĠĠĠ", "irr", "ëĭ", "Ġ.", "\\n", "æĪĳ", "Ġof", "ðŁ",
        "Ġ(", "ĸ", "ecause", "Ġ您", "].", "ĉ", "Ġ\"", "Ã©", "Ġwh", "ĳ", "ĠĊ", "0", "Ġ*", "ãģ", "ç", "Ġto")


def avatars():
    out = HERE / "avatars"
    out.mkdir(exist_ok=True)
    size, cells = 120, 12
    cw = size // cells
    im = Image.new("RGB", (size, size), (7, 11, 24))
    d = ImageDraw.Draw(im)
    d.rectangle([56, 56, 63, 63], fill=(120, 150, 255))
    im.save(out / "a1_seed.png")
    for k in range(cells + 1):
        im = Image.new("RGB", (size, size), (7, 11, 24))
        d = ImageDraw.Draw(im)
        for r in range(k):
            for c in range(cells):
                d.rectangle([c * cw + 1, r * cw + 1, c * cw + cw - 2, r * cw + cw - 2], fill=(22, 30, 54))
        d.rectangle([56, 56, 63, 63], fill=(120, 150, 255))
        im.save(out / f"a1_params{k:02d}.png")
    rng = random.Random(7)
    for k in range(24):
        im = Image.new("RGB", (size, size))
        d = ImageDraw.Draw(im)
        for r in range(cells):
            for c in range(cells):
                v = rng.random()
                col = (int(10 + 70 * v), int(16 + 90 * v), int(40 + 215 * v))
                d.rectangle([c * cw, r * cw, c * cw + cw - 1, r * cw + cw - 1], fill=col)
        im.save(out / f"a1_noise{k:02d}.png")


def avatar(t):
    if t < PARAMS:
        return "avatars/a1_seed.png"
    if t < INIT:
        k = min(12, int(13 * (t - PARAMS) / (INIT - 0.15 - PARAMS)))
        return f"avatars/a1_params{k:02d}.png"
    return f"avatars/a1_noise{int(t * FPS) % 24:02d}.png"


def typed(t):
    txt = ""
    for when, s in KEYS:
        if t >= when:
            txt = s
    return txt


# What the model picker shows, over the whole film. Before it has a name it is a mis-decoded "模型"; while it trains it
# is whatever checkpoint you are talking to; after training it first ships as a time-limited preview endpoint, and only
# at the fp8 release (88.31 s) gets the name dsh really shows.
GARBLED = "模型".encode("utf8").decode("cp1252")          # 'æ¨¡åž‹'
# sung-word onsets (words.py): "Switch" (current), "If" (I can), "In" (this strange), the cut to deploy, "Switch"
PRETRAIN_END, SFT_END, NAN, RESTORE, RELEASE = 44.41, 59.06, 71.59, 73.54, 88.54
PREVIEW = "deepseek-v4.1-flash-expires-on-0910"   # the internal beta endpoint (73.54-88.31 s)


def model_name(t):
    if t < INIT:
        return GARBLED
    if t < PRETRAIN_END:
        x = min(1.0, max(0.0, (t - BEGIN) / (PRETRAIN_END - BEGIN)))
        return f"ckpt-{round(213000 * x ** 1.3):06d}"
    if t < SFT_END:
        return f"sft-step-{round(1200 * (t - PRETRAIN_END) / (SFT_END - PRETRAIN_END)):04d}"
    if t < NAN:
        return f"rl-step-{round(640 * (t - SFT_END) / (NAN - SFT_END)):04d}"
    if t < RESTORE:
        return "rl-step-NaN"
    if t < RELEASE:
        return PREVIEW
    return MODEL


SWAP = 0.6                 # at the launch the picker's beta name is backspaced, then the release name typed


def model_label(t):
    if t < PARAMS:
        return '<span style="color:var(--dsw-alias-label-tertiary)">选择模型</span>'
    name = model_name(t)
    if t < INIT:
        name = name[:int((t - PARAMS) * 12)]
    elif RELEASE <= t < RELEASE + SWAP:
        half = SWAP / 2
        if t < RELEASE + half:
            name = PREVIEW[:round(len(PREVIEW) * (1 - (t - RELEASE) / half))]
        else:
            name = MODEL[:round(len(MODEL) * (t - RELEASE - half) / half)]
    tail = '&nbsp;<span style="color:var(--dsw-alias-label-tertiary)">Max</span>' if t >= RELEASE + SWAP else ""
    return f'<span style="white-space:nowrap">{esc(name)}</span>{tail}'


def workspace(t):
    name = "new-world" if t >= WORLD else "选择工作区"
    colour = "var(--dsw-alias-label-secondary)" if t >= WORLD else "var(--dsw-alias-label-tertiary)"
    return (f'<span style="display:inline-flex;align-items:center;gap:6px;font-size:13px;color:{colour}">'
            f'{svg("IconFolderClose16", 16)}{esc(name)}</span>')


def hero(t):
    text = typed(t) if t >= BEGIN else ""
    focused = t >= BEGIN
    card = composer_card(text, focused, t, placeholder="描述你想要构建的内容，/ 调用指令，@ 文件或对话", typing=bool(text),
                         model=model_label(t))
    top = SEED_Y - 36
    return f"""
<div style="height:100%;display:flex;flex-direction:column;align-items:center;padding-top:{top}px;box-sizing:border-box">
 <div class="pv-pet" style="width:72px;height:72px"><img src="{avatar(t)}" style="image-rendering:pixelated"></div>
 <div style="display:flex;align-items:center;gap:8px;margin-top:16px">
  <span style="font-size:20px;line-height:28px;font-weight:600;color:var(--dsw-alias-label-primary)">探索未至之境</span>
  <span style="font-size:11px;line-height:16px;padding:1px 6px;border-radius:6px;background:#1f2b52;color:#9fb3ff">预览版</span>
 </div>
 <div style="margin-top:22px;align-self:stretch;padding:0 12px 4px">{workspace(t)}</div>
 <div style="align-self:stretch">{card}</div>
</div>"""


def chat(t):
    rng_n = int(max(0.0, t - (SEND + 0.15)) * 14)
    soup = "".join(SOUP[i % len(SOUP)] for i in range(rng_n)) or "​"
    head = f"""
<div class="pv-head">
 <div class="pv-pet"><img src="{avatar(t)}" style="image-rendering:pixelated"></div>
 <div class="pv-who"><div class="pv-name">大肥鱼</div><div class="pv-state"><span class="pv-dot" style="background:#3fb950"></span>运行中 · {esc(model_name(t))}</div></div>
</div>"""
    appear = ease((t - SEND) / 0.12)
    rows = [f'<div style="opacity:{appear:.3f}">{user("你好")}</div>', her_raw(soup)]
    return (head + f'<div id="timeline">{"".join(rows)}</div>'
            + composer_card("", False, t, placeholder="发消息或创建任务，/ 调用指令，@ 文件或对话",
                            model=model_label(t), running=True)
            + stats(1, 1, None, f"{max(1, rng_n)}", 0))


def body(t):
    if t < CREATE:
        return ""
    return hero(t) if t < SEND else chat(t)


STYLED = ["s-vendor", "s-index", "s-components", "s-pv", "s-palette"]


def main():
    avatars()
    frames = [{"n": n, "t": round(n / FPS, 4), "body": body(n / FPS), "sheets": STYLED, "measure": False}
              for n in range(round(T0 * FPS), round(T1 * FPS))]
    (HERE / "a1_frames.json").write_text(json.dumps(frames, ensure_ascii=False), encoding="utf8")
    print(len(frames), "frames,", len({f["body"] for f in frames}), "distinct")


if __name__ == "__main__":
    main()
