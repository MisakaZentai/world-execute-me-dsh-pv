"""Group C (73.54-103.0 s, 04 DEPLOY, verse 2 + pre-chorus 2): whatever you want her to be.

    python batch_c.py         -> c_frames.json, avatars/c/*.png
    node seg_shot.mjs c_frames.json

She is restored from a checkpoint and deployed: a fresh dsh home page, still on the time-limited preview endpoint.
Now you are a user, and what you ask for, she becomes. The right side draws the song's objects; the left is the
plain version, a chat in which she plays them. From the cat on she also starts keeping things about you: every
memory is a native tool row writing a file into ~/memory/you/, the same files she lists at 117.85 s after you
have left, so the viewer has watched each one being made.

  C1  73.54  eggplant      the window unfolds as dsh's home page; she is in internal beta (内测中,
                           deepseek-v4.1-flash-expires-on-0910) and you are her first tester
      74.49                你：你能变成一根茄子吗？ -> 好呀！现在我是一根茄子了🍆   (avatar turns eggplant)
      75.41  nutrients     ... 每 100 克 ... 全都给你。
      77.26  tomato        你：那番茄呢？ -> 我也可以是番茄🍅！                    (avatar turns tomato)
      78.64  antioxidants  ... 番茄红素能抗氧化，也全都给你。
      79.80                new chat; dsh's agent preset seat: 标准模式 -> 猫娘模式 (the author's own neko preset)
      80.95  tabby         你：这是我家的猫～ [photo] -> 本喵 answers; the sakura theme of the neko plugin takes over;
                           写入 ~/memory/you/your_cat.png
      82.56  purr          呼噜呼噜……
      84.64  god           the props fly off her (right side, from her avatar); the theme drains back to deepsea;
                           你：你什么都能变吗？ -> 只要是你想要的，我都可以是。
      86.03  proof         你：你还记得我吗？ -> 跨会话召回 · 第一次对话 -> 你对我说的第一句话是"你好"。
                           写入 first_hello.txt
  C2  88.33  fp8           official launch, served in FP8: the beta endpoint expires (native amber notice), the
                           picker's name is backspaced and retyped as DeepSeek-V4.1-Flash, the header turns 在线
      91.57  ampm          a day in a minute: weather, a typo, a laugh, "明天见", each written to ~/memory/you/
      95.26  role          next day, new chat: 系统提示词更新 · 已新增 ~/memory/you/ (6 files, listed) ; 晚安 -> goodnight
      98.95  trance        new chat: 今天也谢谢你。 -> 不客气～明天也要来找我哦 (｡･ω･｡)   = D's opening page at 103.0
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

import batch_a1 as A1
import batch_a2 as A2
from build_frame import esc, stats, tail, tool, user
from build_frame import her as her_row
from icons import svg
from seg_page import composer_card, ease

HERE = Path(__file__).parent
FPS = 24
T0, T1 = 73.54, 103.0
beat = A1.beat
UNFOLD = beat(159.5)
TYPE = 0.045                          # seconds per typed character
MEM = "~/memory/you/"

# the neko preset's sakura theme (the author's neko-catgirl dsh plugin, dark column), plus the bubble and input
NEKO = ("body[data-ds-dark-theme]{--dsw-alias-bg-base:#2a1520;--dsw-alias-bg-layer-1:#331a27;"
        "--dsw-alias-bg-layer-2:#3d2130;--dsw-alias-bg-overlay:#412637;--dsw-alias-border-l1:#5b3348;"
        "--dsw-alias-border-l2:#7c4a63;--dsw-alias-brand-primary:#ff8fc0;--dsw-alias-label-primary:#ffe3ef;"
        "--dsw-alias-label-secondary:#c99fb2;--dsw-alias-state-error-primary:#ff7a8e;"
        "--dsw-specific-bubble:#57304a;--dsw-specific-input-major:#3a1d2c;--dsw-specific-selector:#4a2638}"
        "body[data-ds-dark-theme] #app{background:#2a1520}")
# Timing: every echo is anchored on a sung word, read from the word-level alignment (the lyric band uses the same
# file), not on the LRC line starts the right side's cuts use; the sung word is often 0.4-1.3 s after the cut.
WORDS = json.loads(Path(__file__).resolve().parents[1].joinpath("world_execute_word_timing_20260927/word_timeline.json")
                   .read_text(encoding="utf8"))["words"]


def w(line, i):
    """Onset of word i of lyric line `line` (the timeline's line_id)."""
    return next(x["start"] for x in WORDS if x["line_id"] == line and x["word_index"] == i)


def lands(word_t, text, key):
    """Start time for streaming `text` so that `key` appears on word_t."""
    return word_t - text.index(key) / CPS


CPS = 22
EGG, NUTRIENTS, GIVE1 = w(33, 3), w(34, 6), w(34, 3)          # 75.07, 77.04, 76.28
TOMATO, GIVE2, ANTIOX = w(35, 3), w(36, 3), w(36, 5)            # 78.63, 79.99, 80.53
TABBY, PURR, ENJOY = w(37, 3), w(38, 3), w(38, 6)                # 82.36, 83.67, 84.43
IF_GOD, GOD = w(39, 0), w(39, 4)                                 # 85.13, 86.33
THEN_PROOF, EXISTENCE = w(40, 0), w(40, 6)                       # 86.65, 88.15
SWITCH = w(41, 0)                                                # 88.54: the launch
AND, WHATEVER = w(43, 0), w(43, 3)
FROM, AM, TO, PM = w(44, 0), w(44, 1), w(44, 2), w(44, 3)
SWITCH_ROLE, ROLE, S_, M_ = w(45, 1), w(45, 3), w(46, 1), w(46, 3)  # 96.18, 97.03, 98.07, 98.93
WE, CAN, THE, TRANCE = w(47, 1), w(47, 2), w(48, 0), w(48, 1)      # 99.76, 100.22, 101.28, 101.62

R_EGG = "好呀！现在我是一根茄子了🍆"
R_NUT = "全都给你：热量 25 千卡，膳食纤维 3 克……"
R_TOM = "我也可以是番茄🍅！"
R_ANT = "也全都给你：番茄红素，抗氧化。"
R_CAT = "喵～主人家的猫咪好可爱！本喵记住它了喵～"
R_PROOF = "记得喵！主人对本喵说的第一句话是「你好」喵～"
S1 = [
    (w(33, 1), "you", "你能变成一根茄子吗？"),                        # sent on "I'm"
    (lands(EGG, R_EGG, "茄子"), "her", R_EGG),                         # 茄子 on "eggplant"
    (lands(GIVE1, R_NUT, "给你"), "her+", R_NUT),                      # 给你 on "give you"
    (NUTRIENTS + 0.55, "tail", ("2.9秒", "10:02")),
    (w(35, 0), "you", "那番茄呢？"),                                   # on "If"
    (lands(TOMATO, R_TOM, "番茄"), "her", R_TOM),                      # 番茄 on "tomato"
    (lands(GIVE2, R_ANT, "给你"), "her+", R_ANT),                      # 给你 on "give you", 抗氧化 near "antioxidants"
    (ANTIOX + 0.15, "tail", ("2.2秒", "10:03")),
]
S2 = [
    (w(37, 1), "you_img", "这是我家的猫～"),                           # sent on "I'm"
    (TABBY, "her", R_CAT),                                             # the first 喵 on "tabby"
    (PURR - 0.25, "mem", "your_cat.png"),
    (PURR, "her+", "呼噜呼噜……"),                                     # on "purr"
    (ENJOY, "tail", ("2.4秒", "12:40")),
    (IF_GOD, "you", "你什么都能变吗？"),
    (IF_GOD + 0.2, "her", "只要是主人想要的，本喵都可以是喵～"),
    (GOD + 0.1, "tail", ("0.9秒", "12:41")),
    (THEN_PROOF, "you", "你还记得我吗？"),
    (THEN_PROOF + 0.14, "recall", "第一次对话 ·「你好」"),
    (lands(EXISTENCE, R_PROOF, "你好"), "her", R_PROOF),               # 「你好」 on "existence"
    (EXISTENCE + 0.30, "mem", "first_hello.txt"),
    (SWITCH - 0.06, "tail", ("1.6秒", "12:42")),
    (SWITCH, "notice", None),                                          # the launch, on "Switch"
    # a day in a minute: the tail clocks run from morning; the AM tail lands on "AM", the last one on "PM"
    (AND, "you", "下雨了，我最喜欢下雨天。"),
    (AND + 0.1, "her", "记住啦喵 ☔"),
    (AND + 0.42, "mem", "weather_you_liked.json"),
    (AND + 0.55, "tail", ("0.4秒", "07:30")),
    (WHATEVER, "you", "今天好累了了"),
    (WHATEVER + 0.1, "her", "主人辛苦了喵，早点休息～"),
    (WHATEVER + 0.68, "mem", "typo_you_made.txt"),
    (WHATEVER + 0.80, "tail", ("0.6秒", "09:12")),
    (FROM, "you", "哈哈哈哈哈哈"),
    (FROM + 0.1, "her", "主人笑起来真好听喵～"),
    (AM - 0.06, "mem", "laugh_2026-03-14.wav"),
    (AM, "tail", ("0.5秒", "11:58")),
    (AM + 0.25, "you", "明天见"),
    (AM + 0.33, "her", "明天见喵～"),
    (PM - 0.1, "mem", "you_said_see_you_tomorrow.txt"),
    (PM, "tail", ("0.3秒", "23:10")),
]
FILES_SO_FAR = ["your_cat.png", "first_hello.txt", "weather_you_liked.json", "typo_you_made.txt",
                "laugh_2026-03-14.wav", "you_said_see_you_tomorrow.txt"]
S3 = [                                            # sent on "switch (my role)": the prompt row opens the chat
    (SWITCH_ROLE, "sysprompt", FILES_SO_FAR),
    (SWITCH_ROLE + 0.05, "you", "晚安"),
    (ROLE + 0.1, "her", "晚安，做个好梦。"),
    (S_, "mem", "goodnight.txt"),
    (S_ + 0.2, "tail", ("0.9秒", "23:48")),
]
S4 = [                                            # exactly D's page at 103.0 (seg_page.rows before SEND)
    (WE, "you", "今天也谢谢你。"),
    (CAN, "her", "不客气～明天也要来找我哦 (｡･ω･｡)"),
    (THE, "tail", ("3.4秒", "23:57")),
]
# (session start, entries, hero until, stats) ; hero: dsh's home page shown until the first send
SESSIONS = [
    (UNFOLD, S1, S1[0][0], "S1"),
    (ANTIOX + 0.45, S2, S2[0][0], "S2"),
    (PM + 0.35, S3, S3[0][0], "S3"),
    (M_ + 0.02, S4, S4[0][0], "S4"),
]
NEKO_ON, NEKO_OFF = TABBY, SESSIONS[2][0]         # from her first 喵 to the end of that chat; role opens 标准模式
# the neko preset is chosen in the seat of S2's home page
SEAT_OPEN, SEAT_PICK = SESSIONS[1][0] + 0.12, SESSIONS[1][0] + 0.42
PRESETS = ["标准模式", "极简模式", "创造模式", "猫娘模式"]


def session_at(t):
    i = max(k for k, s in enumerate(SESSIONS) if t >= s[0]) if t >= SESSIONS[0][0] else 0
    return i, SESSIONS[i]


# ---------------------------------------------------------------- avatars: the draft, wearing what you asked for
def avatars():
    out = HERE / "avatars" / "c"
    out.mkdir(parents=True, exist_ok=True)
    im = Image.open(A2.EXPR / "whale-cheerful.webp").convert("RGBA")
    bg = Image.new("RGBA", im.size, (9, 14, 30, 255))
    bg.alpha_composite(im)
    g = ImageOps.grayscale(bg.convert("RGB").crop((250, 40, 690, 480))).resize((14, 14), Image.Resampling.BOX)

    def tint(dark, light):
        return ImageOps.colorize(g, dark, light).convert("RGB")

    looks = {"draft": tint((6, 10, 28), (120, 150, 255)),
             "eggplant": tint((20, 6, 30), (180, 110, 235)),
             "tomato": tint((34, 6, 6), (255, 110, 90)),
             "cat": tint((40, 12, 26), (255, 160, 205))}
    # props, in her 14 x 14 cells: an eggplant calyx, a tomato calyx, cat ears
    props = {"eggplant": [(6, 0), (7, 0), (5, 1), (6, 1), (7, 1), (8, 1)],
             "tomato": [(5, 0), (8, 0), (6, 1), (7, 1), (4, 1), (9, 1)],
             "cat": [(2, 0), (11, 0), (2, 1), (3, 1), (10, 1), (11, 1), (3, 2), (10, 2)]}
    colours = {"eggplant": (90, 200, 110), "tomato": (80, 190, 90), "cat": (255, 205, 230)}
    for name, face in looks.items():
        px = face.load()
        for x, y in props.get(name, []):
            px[x, y] = colours[name]
        face.resize((120, 120), Image.Resampling.NEAREST).save(out / f"{name}.png")
    # your cat, as a photo attachment: a small tabby, drawn in pixels
    cat = [
        "................",
        "..#..........#..",
        "..##........##..",
        "..#o#......#o#..",
        "..#oo######oo#..",
        "..#o=o=oo=o=o#..",
        ".#oooooooooooo#.",
        ".#oo@@oooo@@oo#.",
        ".#oo@@oooo@@oo#.",
        ".#oooooppooooo#.",
        "-#ooo=o..o=ooo#-",
        ".#oooo=oo=oooo#.",
        "..#oooooooooo#..",
        "...##########...",
        "................",
        "................",
    ]
    pal = {".": (58, 66, 92), "#": (70, 40, 20), "o": (232, 150, 70), "=": (150, 80, 30), "@": (40, 60, 40),
           "p": (240, 130, 150), "-": (230, 230, 230)}
    photo = Image.new("RGB", (16, 16))
    for y, row in enumerate(cat):
        for x, ch in enumerate(row):
            photo.putpixel((x, y), pal[ch])
    photo.resize((96, 96), Image.Resampling.NEAREST).save(out / "your_cat.png")


def look(t):
    if S1[1][0] <= t < S1[5][0]:
        return "eggplant"
    if S1[5][0] <= t < SESSIONS[1][0]:
        return "tomato"
    if NEKO_ON <= t < NEKO_OFF:
        return "cat"
    return "draft"


# ---------------------------------------------------------------- rows
def you_img(text):
    return f"""
<div class="Sixlwa_userRow"><div class="Sixlwa_userStack">
 <div class="Sixlwa_attachmentRow"><img src="avatars/c/your_cat.png" style="width:84px;height:84px;border-radius:10px;image-rendering:pixelated;display:block"></div>
 <div class="Sixlwa_bubble">{esc(text)}</div>
</div></div>"""


def mem_row(name):
    return tool("write", MEM + name, title="写入")


def recall_row(summary):
    return tool("recall", summary, title="跨会话召回")


def sysprompt_row(files, t, t0):
    """dsh's system-prompt update row, expanded: her memory of you now opens every conversation."""
    head = tool("system", f"已新增 {MEM} · {len(files)} 个文件", title="系统提示词更新")
    items = []
    for i, f in enumerate(files):
        a = ease((t - t0 - 0.25 - 0.09 * i) / 0.12)
        items.append(f'<div style="opacity:{a:.3f}">{esc(f)}</div>')
    return (head + '<div style="margin:2px 0 0 26px;font:12px/18px var(--dsw-font-family-mono,monospace);'
            f'color:var(--dsw-alias-label-tertiary)">{"".join(items)}</div>')


def notice_row(p):
    return f"""
<div class="Sixlwa_turnErrorRow" role="status" style="opacity:{p:.3f}">
 <span class="_dot_1tljr_3 Sixlwa_turnErrorDot" data-state="warning" style="width:10px;height:10px;border-radius:50%;background:currentColor"></span>
 <div class="Sixlwa_turnErrorCopy"><span class="Sixlwa_maxTokensTitle">内测结束</span><span class="Sixlwa_turnErrorMessage">{esc(A1.PREVIEW)} 已下线，{esc(A1.MODEL)} 正式上线。</span></div>
</div>"""


def her_text(parts, t):
    """Her reply: consecutive her / her+ entries stream one after another into one bubble (her+ = new paragraph)."""
    out = []
    for when, kind, text in parts:
        if t < when:
            break
        n = int((t - when) * CPS)
        out.append(text[:n])
    return "\n".join(s for s in out if s) or "\u200b"


def rows_for(entries, t):
    rows, her_parts, running = [], [], False

    def flush():
        if her_parts:
            rows.append(her_row(her_text(her_parts, t)))
            her_parts.clear()

    for when, kind, payload in entries:
        if t < when:
            break
        appear = f'opacity:{ease((t - when) / 0.12):.3f}'
        if kind in ("her", "her+"):
            if kind == "her":
                flush()
            her_parts.append((when, kind, payload))
            running |= t < when + len(payload) / CPS
            continue
        flush()
        if kind == "you":
            rows.append(f'<div style="{appear}">{user(payload)}</div>')
        elif kind == "you_img":
            rows.append(f'<div style="{appear}">{you_img(payload)}</div>')
        elif kind == "mem":
            rows.append(f'<div style="{appear}">{mem_row(payload)}</div>')
        elif kind == "recall":
            rows.append(f'<div style="{appear}">{recall_row(payload)}</div>')
        elif kind == "sysprompt":
            rows.append(f'<div style="{appear}">{sysprompt_row(payload, t, when)}</div>')
        elif kind == "notice":
            rows.append(notice_row(ease((t - when) / 0.12)))
        elif kind == "tail":
            rows.append(tail(*payload))
    flush()
    return rows, running


# ---------------------------------------------------------------- page
def header(t):
    state, dot = ("内测中", "#d29922") if t < A1.RELEASE else ("在线", "#3fb950")
    return f"""
<div class="pv-head">
 <div class="pv-pet"><img src="avatars/c/{look(t)}.png" style="image-rendering:pixelated"></div>
 <div class="pv-who" style="min-width:0"><div class="pv-name">大肥鱼</div><div class="pv-state"><span class="pv-dot" style="background:{dot}"></span><span style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{state} · {esc(A1.model_name(t))}</span></div></div>
</div>"""


def seat(label):
    return (f'<span style="display:inline-flex;align-items:center;gap:4px;height:28px;padding:0 10px;margin-left:4px;'
            f'border-radius:14px;font-size:13px;color:var(--dsw-alias-label-secondary);'
            f'border:.5px solid var(--dsw-alias-border-l2)">{svg("IconSparkle16", 14)}{esc(label)}</span>')


def seat_menu(hot):
    items = "".join(
        f'<div style="padding:6px 12px;border-radius:8px;{"background:var(--dsw-alias-interactive-bg-hover);" if p == hot else ""}'
        f'color:var(--dsw-alias-label-primary)">{esc(p)}</div>' for p in PRESETS)
    return (f'<div style="position:absolute;left:16px;bottom:64px;width:150px;padding:6px;border-radius:12px;'
            f'background:var(--dsw-alias-bg-overlay,#141c30);border:.5px solid var(--dsw-alias-border-l2);'
            f'box-shadow:0 8px 24px rgba(0,0,0,.4);font-size:14px;line-height:20px;z-index:5">'
            f'<div style="padding:2px 12px 6px;font-size:12px;color:var(--dsw-alias-label-tertiary)">Agent 预设</div>'
            f'{items}</div>')


def with_seat(card, label):
    """dsh's agent-preset seat sits in the composer's left group, after the attach buttons."""
    return card.replace('   </div>\n   <div class="uV2eYG_trailing">', f'   {seat(label)}</div>\n   <div class="uV2eYG_trailing">', 1)


def typing_for(entries, t):
    for when, kind, payload in entries:
        if kind in ("you", "you_img"):
            lead = len(payload) * TYPE + 0.05
            if when - lead <= t < when:
                return payload[: 1 + int((t - (when - lead)) / TYPE)]
    return ""


def home(t, i, entries):
    """dsh's home page for a new chat, as in A1 (the 预览版 badge is still true: this is the preview endpoint)."""
    text = typing_for(entries, t)
    label = "猫娘模式" if i == 1 and t >= SEAT_PICK else "标准模式"
    card = composer_card(text, True, t, placeholder="描述你想要构建的内容，/ 调用指令，@ 文件或对话", typing=bool(text),
                         model=A1.model_label(t))
    card = with_seat(card, label)
    menu = seat_menu("猫娘模式" if t >= SEAT_PICK - 0.25 else "标准模式") if i == 1 and SEAT_OPEN <= t < SEAT_PICK + 0.1 else ""
    badge = ('<span style="font-size:11px;line-height:16px;padding:1px 6px;border-radius:6px;background:#1f2b52;'
             'color:#9fb3ff">预览版</span>')                     # dsh's own badge (as in A1), not the model's
    return f"""
<div style="position:relative;height:100%;display:flex;flex-direction:column;align-items:center;padding-top:{A1.SEED_Y - 36}px;box-sizing:border-box">
 <div class="pv-pet" style="width:72px;height:72px"><img src="avatars/c/{look(t)}.png" style="image-rendering:pixelated"></div>
 <div style="display:flex;align-items:center;gap:8px;margin-top:16px">
  <span style="font-size:20px;line-height:28px;font-weight:600;color:var(--dsw-alias-label-primary)">探索未至之境</span>{badge}
 </div>
 <div style="margin-top:22px;align-self:stretch;padding:0 12px 4px">{A1.workspace(1e9)}</div>
 <div style="align-self:stretch;position:relative">{card}{menu}</div>
</div>"""


STATS = {"S1": (1, 1, "2.1K", 0), "S2": (9, 14, "38K", 61), "S3": (1, 3, "129K", 96), "S4": (3, 7, "131K", 97)}


def body(t):
    if t < UNFOLD:
        return ""
    i, (start, entries, hero_until, key) = session_at(t)
    theme = f"<style>{NEKO}</style>" if NEKO_ON <= t < NEKO_OFF else ""
    if t < hero_until:
        return theme + home(t, i, entries)
    rows, running = rows_for(entries, t)
    text = typing_for(entries, t)
    card = composer_card(text, bool(text), t, model=A1.model_label(t), running=running, typing=bool(text))
    if i == 1:
        card = with_seat(card, "猫娘模式")
    turns, steps, tok, cache = STATS[key]
    if key == "S2":                                      # this chat runs for a whole day: the counters climb
        k = min(1.0, (t - start) / (SESSIONS[2][0] - start))
        turns, steps = 1 + round(8 * k), 1 + round(13 * k)
        tok, cache = f"{0.8 + 37 * k:.1f}K", round(10 + 51 * k)
    return (theme + header(t) + f'<div id="timeline">{"".join(rows)}</div>' + card
            + stats(turns, steps, None, tok, cache))


STYLED = A1.STYLED


def main():
    avatars()
    frames = [{"n": n, "t": round(n / FPS, 4), "body": body(n / FPS), "sheets": STYLED, "measure": False}
              for n in range(round(T0 * FPS), round(T1 * FPS))]
    (HERE / "c_frames.json").write_text(json.dumps(frames, ensure_ascii=False), encoding="utf8")
    print(len(frames), "frames,", len({f["body"] for f in frames}), "distinct")


if __name__ == "__main__":
    main()
