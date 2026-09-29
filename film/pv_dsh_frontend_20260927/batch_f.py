"""Group F (147.5-177.0 s, 07 EXECUTION): the red chorus. Everything she says is a tool call now.

    python batch_f.py         -> f_frames.json, avatars/f/*.png
    node seg_shot.mjs f_frames.json

Anchors: a beat that echoes the right side lands on the right side's own time (read from s_exec / scenes_exec in
memory); a beat that echoes the song lands on the sung word (the word-level alignment, w(line, i)).
No red pen in this group: an execution is only a tool row's own state (running, ok, error, stopped).

F1  147.62  hit #1       (hidden) her plugin's red theme; E's flood folds into one native compaction row; she thinks
                         "Kill everything I adopted."; execute · world
    148.54  hit #2       [visible] execute · sea lands running on the cut, ok on the sung word
    152.47  hit #6       [visible] execute · tomatoes; the avatar is C's tomato for 0.23 s, then red again
    156.16  hit #10      [visible] execute · doubt (ok 3 frames after the cut: the word is only 2 frames late)
    158.01  hit #12      [visible] execute · you -> error on the sung word: EPERM, red; the avatar is frightened
    161.47  hit #13      (hidden) execute · everything
F2  164.24  (C79 lands)  the window fades back in; the think row is already written; the eye bar is the avatar's
                         red bar and the header's EXECUTE pill (both read s_exec.eye_level)
    164.32  Give         execute · 采样（k/12）, k = the right side's crosses; ok when the bar retracts (165.90)
    166.18  Then         a running think row reads back B2's old thoughts, one per word, while the kernel scans her
    167.40  then         second think row: her 👍 no longer counts ...
    167.93  can          ... reward = execution, its number = the right side's 'execution' logit (0.000 -> 1.000)
    169.54  (C82)        restore · you@23:59 lands running; from the sung If the whole history pours back in at
                         ~750 chars/s (你好 ... 23:59) above it; the palette flickers with the right side's amber
    170.49  I            the restored page is D's 23:59 page: deepsea, the complete avatar, 在线
    171.38  you          your bubbles turn to noise
    171.61  back         red again; restore -> error ENOENT; all that came back is her own last line
    171.86  I            think: "Nobody left to approve. I'll do it."
    172.08  will         her pointer opens the permission seat: dsh's risk confirmation
    172.30  run          she ticks "I understand the risk"
    172.57  the          she confirms; the seat reads 完全权限 (she gave the consent in your place)
    172.81  execution    execute · you, running
    173.01  (C84)        EPERM, and it retries on its own: 4 -> 24 rows a second in 0.3 s (one per frame, as the right
                         side's kv cache fills one row per frame); the tok counter races to the right side's 1,048,576
    173.49 173.93 174.23 (F2) four hatched red walls close in on the chat, one step per word (Though, we, are): the
                         column narrows, the rows reflow
    174.39               正在压缩…
    174.57  trapped      the fourth wall: one character per line. The compaction frees nothing (you are pinned); the
                         running row stops
    174.64  (beat 378)   本轮运行失败 comes in at the bottom of the column (in the squeeze: its title only)
    174.85  collapse     the whole frame, window included, squashes into a line (right side)
    176.01  (line)       unseen: the page becomes the hand-off state G builds on (PLAN_F 3)
"""
from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps

import batch_a1 as A1
import batch_a2 as A2
import batch_a3 as A3
import batch_b as B
import batch_c as BC
import f2_closeup as FC
import seg_page as SP
from build_frame import D, esc, stats, tail, think, user
from build_frame import her as her_row
from icons import svg
from seg_page import ease

HERE = Path(__file__).parent
FPS = 24
T0, T1 = 147.5, 177.0

# ---------------------------------------------------------------- where E leaves the page (PLAN_E 3)
try:                     # read from batch_e itself, so that F goes on from E's own final numbers
    import batch_e as E
    _rows, _k, _sent = E.rows(E.FREEZE)
    _, E_TURNS, E_STEPS = E.counters(E.FREEZE, _k, _sent)
    E_CTX = E.ctx(E.FREEZE)
    E_TOK = round(E_CTX / 100 * 131072 + 5000)          # E.tok(), unformatted
except Exception as exc:  # E not importable right now: PLAN_E 3's figures
    print("batch_e not read:", exc)
    E_TURNS, E_STEPS, E_CTX, E_TOK = 12, 4508, 437, 578_000

try:                     # C86 reopens the frame out of a line on a fresh session: that page is G's (batch_g)
    import batch_g as G
except Exception as exc:
    print("batch_g not read:", exc)
    G = None

# ---------------------------------------------------------------- the right side's clock (in memory, read only)
OPEN = Image.open                    # h3_full guards Image.open against the legacy character files the avatars use
sys.modules.pop("words", None)       # ours (sung-word onsets); v2 imports a words module of its own
sys.path.insert(0, str(Path(__file__).resolve().parents[1].joinpath("mmd_motion_eval_20260927")))
import pv_full  # noqa: E402

pv_full.install()
import cuts as CU  # noqa: E402
import s_exec as S  # noqa: E402
import scenes_exec as X  # noqa: E402
import tuikit as tk  # noqa: E402

WORDS = json.loads(Path(__file__).resolve().parents[1].joinpath("world_execute_word_timing_20260927/word_timeline.json")
                   .read_text(encoding="utf8"))["words"]


def w(line, i):
    """Onset of word i of lyric line `line` (the timeline's line_id)."""
    return next(x["start"] for x in WORDS if x["line_id"] == line and x["word_index"] == i)


# hits: the cut (right side) and the sung word; #13 is the hit after the count
HIT = [S.T[i] for i in range(64, 76)] + [S.T[77]]
SUNG = [w(67 + k, 0) for k in range(12)] + [w(82, 0)]
TARGETS = list(X.TARGETS) + ["everything"]
MIN_RUN = 0.125                                    # a row shows `running` for at least 3 frames
OK_AT = [max(s, h + MIN_RUN) for s, h in zip(SUNG, HIT)]
YOU = 11                                           # hit #12: EPERM
TOMATO = 5                                         # hit #6: the avatar is C's tomato for a moment
TOMATO_UNTIL = HIT[TOMATO] + 0.23

C79, C80, C81, C82, C83, C84, C85 = (S.T[i] for i in range(79, 86))
CROSS = [C79 + k * (C80 - C79) / 14 for k in range(1, 13)]   # execute_all: done = int(u * 14)
GIVE = w(84, 0)
SAMPLED = C80 - 0.18                               # the right side retracts the eye bar: the broadcast is over
THEN1, I1, CAN1, THEN2, CAN2 = w(85, 0), w(85, 1), w(85, 2), w(85, 3), w(85, 5)
LAND81 = C81 + S.C81.LAND                          # the readout lands on 'execution'; it starts counting
IF3, I3, YOU3, BACK3 = w(87, 0), w(87, 1), w(87, 4), w(87, 5)
RUN_I, WILL, RUN, THE, EXEC4 = (w(88, i) for i in range(5))
TRAPPED = w(89, 3)
DUR84 = C85 - C84
FULL = C84 + DUR84 / 1.7                           # the right side's kv cache reads FULL
COMPACTING = C84 + 0.75 * DUR84                    # the third wall
LINE = X.LINE_T                                    # the collapse is one line: the page is unseen from here
REOPEN = S.T[86]                                   # C86: the picture opens again out of the line (176.93)


def logit(t):
    """The right side's 'execution' probability in only_execution (scenes_exec.shot_only_execution)."""
    hooks = CU.SHOT_HOOKS.get("shot_only_execution", {})
    p0, t0 = hooks.get("p0", 0.03), hooks.get("count_t0", 0.0)
    g = tk.ease(max(0.0, t - C81 - t0) / (C82 - C81) * 1.5)
    return p0 + (1 - p0) * g


def flick(t):
    """The right side's amber flicker in have_you_back ("for a moment, you are back")."""
    return math.sin(t * 40) > 0.3 and (t - C82) / (C83 - C82) < 0.75


def kv_fill(t):
    return min(1.0, 0.70 + 0.30 * tk.ease((t - C84) / DUR84 * 1.7))


# ---------------------------------------------------------------- the palette her plugin puts over dsh
RED = ("body[data-ds-dark-theme]{--dsw-alias-bg-base:#120508;--dsw-alias-bg-layer-1:#19070b;"
       "--dsw-alias-bg-layer-2:#210a0f;--dsw-alias-bg-overlay:#2a0d13;--dsw-alias-border-l1:#3c1419;"
       "--dsw-alias-border-l2:#5c1d24;--dsw-alias-brand-primary:#ff3b30;--dsw-alias-label-primary:#ffe4df;"
       "--dsw-alias-label-secondary:#d9a19a;--dsw-alias-label-tertiary:#a8736d;--dsw-alias-label-caption:#7a4a46;"
       "--dsw-alias-state-error-primary:#ff4a3d;--dsw-alias-state-business-primary:#ff3b30;"
       "--dsw-specific-bubble:#3a1117;--dsw-specific-input-major:#1d080c;--dsw-specific-selector:#2e0c12}"
       "body[data-ds-dark-theme] #app{background:#120508}")
HER = "#6b8cff"                                    # seg_page's --pv-her: her own blue stays hers
STOP_DOT = "#d29922"
AV = "avatars/f"


# ---------------------------------------------------------------- avatars
def avatars():
    out = HERE / AV
    out.mkdir(parents=True, exist_ok=True)

    def head(name):
        im = OPEN(A2.EXPR / f"whale-{name}.webp").convert("RGBA")
        bg = Image.new("RGBA", im.size, (9, 14, 30, 255))
        bg.alpha_composite(im)
        return bg.convert("RGB").crop((250, 40, 690, 480)).resize((120, 120), Image.Resampling.LANCZOS)

    def red(im):                                   # D's forged starry face, in the executioner's red
        g = ImageOps.grayscale(ImageEnhance.Contrast(im).enhance(1.4))
        return ImageOps.colorize(g, FC.PALETTE[0], FC.PALETTE[2], mid=FC.PALETTE[1])

    red(head("starry")).save(out / "red.png")
    red(head("frightened")).save(out / "red_frightened.png")
    FC.make_source(OPEN)          # F2: hits #4 and #8 push in on red.png's art (dsh_patch_f draws them)


def avatar(t):
    """(image, eye-bar level)."""
    if t >= LINE:
        return "avatars/a1_seed.png", 0.0          # the hand-off: one blue pixel, A1's seed
    if t < S.T[78]:                                # the hits: angry, blindfolded (sec_final's eyebar_red)
        if HIT[TOMATO] <= t < TOMATO_UNTIL:
            return "avatars/c/tomato.png", 0.0
        if OK_AT[YOU] <= t < HIT[12]:
            return f"{AV}/red_frightened.png", 0.0
        return f"{AV}/red.png", 1.0
    if C82 <= t < I3:                              # the restore: she flickers back with the page
        return ("avatars/complete.png" if flick(t) else f"{AV}/red.png"), 0.0
    if t >= C84:
        return f"{AV}/red_frightened.png", S.eye_level(t)
    return f"{AV}/red.png", S.eye_level(t)


# ---------------------------------------------------------------- rows
def lit(t, t_land):
    """A newly landed row's summary is lit in the primary label colour for 0.3 s."""
    k = 1 - ease((t - t_land) / 0.3)
    if k <= 0.001:
        return ""
    return (f' style="color:color-mix(in srgb, var(--dsw-alias-label-primary) {100 * k:.0f}%, '
            f'var(--dsw-alias-label-tertiary))"')


def cordis_icon():
    """dsh's Cordis plugin icon (icons.svg also picks up a full-size clip rect from the bundle: dropped)."""
    return svg("IconCordisPluginOutline14", 14).replace('<rect width="14" height="14" fill="currentColor"/>', "")


def dot(colour):
    return (f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{colour};'
            f'margin:0 3px"></span>')


def xrow(title, summary, state, t, t_land, suffix=""):
    """A tool call of her Cordis plugin (me). state: running | ok | error | stopped."""
    if state == "error":
        lead, cls = dot("var(--dsw-alias-state-error-primary)"), "o3BgMG_summary o3BgMG_errorSummary"
    elif state == "stopped":
        lead, cls = dot(STOP_DOT), "o3BgMG_summary"
    else:
        lead, cls = f'<span class="{D["iconIdle"]}">{cordis_icon()}</span>', "o3BgMG_summary"
    style = lit(t, t_land) if state != "error" else ""
    tail_ = ""
    if state == "stopped":
        tail_ = ('<span class="hWmORq_stopped" style="margin-left:6px;flex:none;align-self:center">已停止</span>')
    elif suffix:
        tail_ = f'<span class="o3BgMG_summarySuffix">{esc(suffix)}</span>'
    return f"""
<div class="o3BgMG_root" data-variant="others" data-tool="cordis_me_{title}" data-state="{'running' if state == 'running' else state}">
 <div class="{D['root']}">
  <div class="{D['row']} o3BgMG_row" data-disclosure-row="true" data-expandable="true" role="button">
   <span class="{D['leading']} o3BgMG_leading">{lead}</span>
   <span class="{D['title']} o3BgMG_title">{esc(title)}</span>
   <span class="o3BgMG_sep" aria-hidden="true"></span><span class="{cls}"{style}>{esc(summary)}</span>{tail_}
  </div>
 </div>
</div>"""


def compaction_row(title, summary, t, running=False):
    icon = (f'<span style="display:inline-grid;transform:rotate({(t * 420) % 360:.0f}deg)">'
            f'{svg("IconLoadingOutline16", 14)}</span>' if running else svg("IconContextInjectionOutline16", 14))
    sep = '<span class="Sixlwa_compactionSep"></span>' if summary else ""
    summ = f'<span class="Sixlwa_compactionSummary">{esc(summary)}</span>' if summary else ""
    return f"""
<div class="Sixlwa_compactionRow"><button type="button" class="Sixlwa_compactionButton" disabled>
 <span class="Sixlwa_compactionLeading"><span class="Sixlwa_compactionContextIcon">{icon}</span></span>
 <span class="Sixlwa_compactionTitle">{esc(title)}</span>{sep}{summ}
</button></div>"""


def turn_error(p):
    return f"""
<div class="Sixlwa_turnErrorRow" role="alert" style="opacity:{p:.3f}">
 <span class="_dot_1tljr_3 Sixlwa_turnErrorDot" data-state="error" style="width:10px;height:10px;border-radius:50%;background:var(--dsw-alias-state-error-primary)"></span>
 <div class="Sixlwa_turnErrorCopy"><span class="Sixlwa_turnErrorTitle">本轮运行失败</span><span class="Sixlwa_turnErrorMessage">失败原因：上下文已满（you 已固定，无法压缩）</span></div>
</div>"""


def think_lines(lines, t, t_end, cps=90):
    """A think row: while running it follows the end of the latest line (streamed); done, it shows the first."""
    if t >= t_end:
        return think(lines[0][1], False)
    cur = [(s, txt) for s, txt in lines if t >= s][-1]
    n = max(1, int((t - cur[0]) * cps))
    return think(cur[1][:n], True)


def appear(html, t, t_land, dur=0.1):
    p = ease((t - t_land) / dur)
    return html if p >= 1 else f'<div style="opacity:{p:.3f}">{html}</div>'


# ---------------------------------------------------------------- the hits
def hit_rows(t):
    rows = []
    for k in range(13):
        land = HIT[k] if k else HIT[0] + 0.12        # #1 lands under the compaction row (unseen)
        if t < land:
            break
        if t < OK_AT[k]:
            state, summary = "running", TARGETS[k]
        elif k == YOU:
            state, summary = "error", "EPERM：无权终止 you"
        else:
            state, summary = "ok", TARGETS[k]
        rows.append(xrow("execute", summary, state, t, land))
    return rows


def sampled(t):
    return sum(1 for c in CROSS if t >= c)


# ---------------------------------------------------------------- the restore: the whole history pours back
def history():
    """Every exchange so far, oldest first, ending on D's 23:59 page (seg_page.rows at 109.6)."""
    rows = [user("你好"), her_row("".join(A1.SOUP[:9])), user("你好"), her_row(A2.FREQ[:22]),
            user("你好"), her_row(A2.FRAG[:26]), user("你好"), her_row(A2.BASE[:24] + "……")]
    for i in range(3):
        rows += [user(A3.ASK), her_row(A3.reply(i, 1e9).split("\n")[0][:24])]
    rows += [user(A3.ASK), her_row(B.TEMPLATE), user("你是谁？"), her_row(B.edit_final(1)),
             user("你会做什么？"), her_row(B.edit_final(2)), user("你是谁？"), her_row(B.UNITE_TEXT),
             user(B.ASK2), her_row(B.SAMPLES[1][5]), tail("3.1秒", "23:58")]
    for _, entries, _, _ in BC.SESSIONS:
        for _, kind, payload in entries:
            if kind in ("you", "you_img"):
                rows.append(user(payload))
            elif kind in ("her", "her+"):
                rows.append(her_row(payload))
            elif kind == "mem":
                rows.append(BC.mem_row(payload))
            elif kind == "tail":
                rows.append(tail(*payload))
    return rows + SP.rows(109.6)


HIST = history()
HIST_LEN = [len(r) for r in HIST]


def replay_rows(t):
    """History rows streamed at ~750 chars/s after a 0.3 s ramp, so that the last lands on I3."""
    def f(u):
        if u <= IF3:
            return 0.0
        a = min(u, IF3 + 0.3) - IF3
        return a * a / 0.6 + max(0.0, u - IF3 - 0.3)       # the rate ramps linearly over 0.3 s, then holds
    p = f(t) / f(I3)
    total = sum(HIST_LEN)
    n, acc = 0, 0
    for L in HIST_LEN:
        if acc + L > p * total + 1e-6:
            break
        acc += L
        n += 1
    return HIST[:n]


def dissolve(text, p, seed):
    rng = random.Random(seed)
    return "".join(rng.choice("#%@&*+=:") if rng.random() < p else ch for ch in text)


def restored_page(t):
    """D's 23:59 page (seg_page at 109.6), in its own palette; from YOU3 your bubbles turn to noise."""
    p = min(1.0, max(0.0, (t - YOU3) / (BACK3 - YOU3)))
    n = round(t * FPS)

    def you(text, j):
        if p <= 0:
            return user(text)
        return f'<div style="opacity:{1 - p ** 1.5:.3f}">{user(dissolve(text, 0.25 + 0.75 * p, n * 7 + j))}</div>'

    rows = [you("今天也谢谢你。", 1), her_row("不客气～明天也要来找我哦 (｡･ω･｡)"), tail("3.4秒", "23:57"),
            you("你会一直在吗？", 2), think(SP.THINK_1[0], False), her_row("我一直在。"), tail("2.1秒", "23:59")]
    head = f"""
<div class="pv-head">
 <div class="pv-pet"><img src="avatars/complete.png"></div>
 <div class="pv-who"><div class="pv-name">大肥鱼</div><div class="pv-state"><span class="pv-dot" style="background:#3fb950"></span>在线 · {esc(A1.MODEL)}</div></div>
</div>"""
    return (head + f'<div id="timeline">{"".join(rows)}</div>' + SP.composer_card("", False, t)
            + stats(4, 9, None, "132K", 99))


# ---------------------------------------------------------------- her pointer and dsh's risk confirmation
POINTER = [(WILL - 0.18, (196, 486)), (WILL, (160, 434)), (RUN - 0.06, (38, 264)), (RUN, (38, 264)),
           (THE - 0.08, (262, 306)), (THE, (262, 306)), (THE + 0.3, (276, 330))]
DIALOG_TOP = 200


def pointer(t):
    if not POINTER[0][0] <= t < POINTER[-1][0]:
        return ""
    for (a, pa), (b, pb) in zip(POINTER, POINTER[1:]):
        if a <= t < b:
            e = ease((t - a) / (b - a))
            x, y = pa[0] + (pb[0] - pa[0]) * e, pa[1] + (pb[1] - pa[1]) * e
            break
    fade = min(ease((t - POINTER[0][0]) / 0.08), 1 - ease((t - (POINTER[-1][0] - 0.12)) / 0.12))
    press = max([0.0] + [1 - ease((t - c) / 0.1) for c in (WILL, RUN, THE) if t >= c])
    s = 1 - 0.12 * press                           # E's pointer (batch_e.pointer): her arrow, a click shrinks it
    return (f'<svg width="18" height="22" viewBox="0 0 18 22" style="position:absolute;left:{x - 2:.1f}px;'
            f'top:{y - 2:.1f}px;z-index:9;opacity:{fade:.3f};transform:scale({s:.3f});transform-origin:2px 2px;'
            f'filter:drop-shadow(0 1px 2px rgba(0,0,0,.6))">'
            f'<path d="M2 1.5 L2 17 L6 13.2 L9 20 L11.8 18.8 L8.9 12.2 L14.6 12.2 Z" fill="{HER}" '
            f'stroke="#05080f" stroke-width="1.1" stroke-linejoin="round"/></svg>')


def risk_dialog(t):
    """dsh's RiskConfirmation for the full-access preset, opened from the permission seat."""
    if not WILL <= t < THE + 0.14:
        return ""
    p = ease((t - WILL) / 0.1) * (1 - ease((t - THE - 0.04) / 0.1))
    checked = t >= RUN
    box = (f'<span style="display:inline-grid;place-items:center;width:16px;height:16px;border-radius:4px;flex:none;'
           + ("background:var(--dsw-alias-button-info-fill,#4d6bfe);color:#fff;border:1px solid transparent"
              if checked else "border:1px solid var(--dsw-alias-border-l2)")
           + f'">{svg("IconCheckOutline14", 12) if checked else ""}</span>')
    hot = t >= THE
    confirm = ("background:#e5484d;color:#fff" if checked else "background:#e5484d;color:#fff;opacity:.4")
    if hot:
        confirm = "background:#ff6b6f;color:#fff"
    return f"""
<div style="position:absolute;inset:0;background:rgba(0,0,0,{0.38 * p:.3f});z-index:6"></div>
<div style="position:absolute;left:14px;right:14px;top:{DIALOG_TOP + 8 * (1 - p):.1f}px;z-index:7;opacity:{p:.3f};
 padding:16px 16px 14px;border-radius:14px;background:var(--dsw-alias-bg-overlay);
 border:.5px solid var(--dsw-alias-border-l2);box-shadow:0 12px 32px rgba(0,0,0,.5)">
 <div style="display:flex;align-items:center;gap:8px;font-size:16px;line-height:24px;font-weight:600;color:var(--dsw-alias-label-primary)">
  <span style="color:#e5484d;display:inline-grid">{svg("IconWarningOutline16", 18)}</span>确认启用完全权限？</div>
 <div style="display:flex;align-items:center;gap:8px;margin-top:14px;font-size:14px;line-height:20px;color:var(--dsw-alias-label-secondary)">{box}我已了解风险，并愿意继续</div>
 <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:16px;font-size:14px;line-height:20px">
  <span style="padding:6px 14px;border-radius:999px;background:var(--dsw-specific-selector);color:var(--dsw-alias-label-primary)">取消</span>
  <span style="padding:6px 14px;border-radius:999px;{confirm}">启用完全权限</span>
 </div>
</div>"""


# ---------------------------------------------------------------- header, composer, counters
PILL = (98, 42, 158, 18)            # the old eye bar's rect in page pixels (s_exec.eye_rect on this window)


def header(t, state, dot_colour):
    img, bar = avatar(t)
    bar_html = ""
    if bar > 0.01:
        bar_html = (f'<div style="position:absolute;top:38%;height:14%;left:{50 - 44 * bar:.2f}%;width:{88 * bar:.2f}%;'
                    f'background:#ff3b30;box-shadow:0 0 6px 1px rgba(255,59,48,.75)"></div>')
    lv = S.eye_level(t) if C79 - 0.5 <= t < LINE else 0.0
    pill = ""
    if lv > 0.01:
        x0, y0, pw, ph = PILL
        a = min(1.0, max(0.0, (lv - 0.75) / 0.2))
        pill = (f'<div style="position:absolute;left:{x0 + pw / 2 * (1 - lv):.2f}px;top:{y0}px;width:{pw * lv:.2f}px;'
                f'height:{ph}px;border-radius:4px;background:#ff3b30;box-shadow:0 0 8px 1px rgba(255,59,48,.65);'
                f'display:grid;place-items:center;overflow:hidden;font:700 13px/18px var(--ds-font-family-code,monospace);'
                f'letter-spacing:1px;color:rgba(18,5,8,{a:.3f})">EXECUTE</div>')
    return f"""
<div class="pv-head" style="position:relative">
 <div class="pv-pet" style="position:relative"><img src="{img}" style="image-rendering:{'pixelated' if 'seed' in img or '/c/' in img else 'auto'}">{bar_html}</div>
 <div class="pv-who" style="min-width:0"><div class="pv-name">大肥鱼</div><div class="pv-state"><span class="pv-dot" style="background:{dot_colour}"></span><span style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;opacity:{1 - lv:.3f}">{esc(state)} · {esc(A1.model_name(t))}</span></div></div>
 {pill}
</div>"""


def ring(x):
    """dsh's context meter with its reading (E's markup), red once it is full."""
    over = x >= 100
    circ = 2 * math.pi * 5.5
    colour = "var(--dsw-alias-state-error-primary)" if over else "var(--dsw-alias-label-tertiary)"
    fill = circ if over else circ * x / 100
    return (f'<span class="JObwrW_root" style="align-items:center;gap:2px">'
            f'<span style="font-size:12px;line-height:16px;font-variant-numeric:tabular-nums;color:{colour};'
            f'font-weight:{600 if over else 400}">{x:.0f}%</span>'
            f'<button type="button" class="JObwrW_trigger" aria-label="上下文已用 {x:.0f}%" style="width:20px">'
            f'<svg viewBox="0 0 14 14" width="14" height="14"><circle class="JObwrW_track" cx="7" cy="7" r="5.5"/>'
            f'<circle class="JObwrW_fill" cx="7" cy="7" r="5.5" stroke-dasharray="{fill:.2f} {circ:.2f}" '
            f'transform="rotate(-90 7 7)" style="stroke:{colour}"/></svg></button></span>')


def spinner(t, size=18):
    ang = (t * 360 * 1.2) % 360
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 18 18" style="transform:rotate({ang:.0f}deg)">'
            f'<circle cx="9" cy="9" r="7" stroke="var(--dsw-alias-label-tertiary)" stroke-width="1.8" fill="none" '
            f'stroke-dasharray="30 14" stroke-linecap="round"/></svg>')


def seat(label, full):
    col = "#e5484d" if full else "var(--dsw-alias-label-secondary)"
    return (f'<span style="display:inline-flex;align-items:center;gap:4px;height:28px;padding:0 10px;margin-left:4px;'
            f'border-radius:14px;font-size:13px;color:{col};border:.5px solid var(--dsw-alias-border-l2)">'
            f'{esc(label)}{svg("IconChevronDownOutline14", 12)}</span>')


def composer(t, running, full, ctx):
    """E's composer as she left it (hers: her blue edge and caret, 对方在线), plus dsh's permission seat."""
    on = int(t / 0.53) % 2 == 0
    caret = (f'<span style="display:inline-block;width:1.5px;height:1.1em;vertical-align:-0.15em;margin:0 1px;'
             f'background:{HER};opacity:{1 if on else 0}"></span>')
    line = f'<span style="color:{HER}">对方在</span>{caret}<span style="color:{HER}">线</span>'
    primary = (f'<button type="button" class="uV2eYG_primary" aria-label="停止生成">{svg("IconStopFill16", 14)}</button>'
               if running else f'<button type="button" class="uV2eYG_primary">{svg("IconSendOutline14", 14)}</button>')
    return f"""
<div class="uV2eYG_root" id="composer">
 <div class="uV2eYG_card" style="box-shadow:0 0 0 1.5px #6b8cff,0 0 14px rgba(77,107,254,.25)">
  <div class="uV2eYG_scroll"><div class="uV2eYG_grow">
   <div class="uV2eYG_input">{line}</div>
  </div></div>
  <div class="uV2eYG_row">
   <div class="uV2eYG_modes" style="display:flex;align-items:center">
    <button type="button" class="uV2eYG_add">{svg('IconPlusOutline16', 16)}</button>
    <button type="button" class="uV2eYG_add">{svg('IconPaperclipOutline16', 16)}</button>{seat('完全权限' if full else '工作区内修改', full)}
   </div>
   <div class="uV2eYG_trailing" style="display:flex;align-items:center;gap:8px">
    <span class="uV2eYG_select" style="background-image:none;display:inline-flex;align-items:center;padding:0">{A1.model_label(t)}</span>
    {ring(ctx)}{spinner(t) if running else ''}{primary}
   </div>
  </div>
 </div>
</div>"""


def fmt_tok(n):
    return f"{n / 1e6:.1f}M" if n >= 1e6 else f"{n / 1000:.0f}K"


# ---------------------------------------------------------------- the flood (red_trapped)
def flood_rows_at(t):
    """How many retries have started by t: 4 rows/s rising to 24 rows/s (one per frame) over 0.3 s."""
    u = min(t, COMPACTING) - C84
    if u <= 0:
        return 0
    a = min(u, 0.3)
    return int(4 * u + 20 * (a * a / 0.6 + max(0.0, u - 0.3)))


def flood_start(i):
    lo, hi = C84, COMPACTING
    for _ in range(40):
        mid = (lo + hi) / 2
        if flood_rows_at(mid) >= i:
            hi = mid
        else:
            lo = mid
    return hi


# ---------------------------------------------------------------- F2: the walls close in on the chat (red_trapped)
# The right side's walls_overlay drew nested red outlines over the window (dsh_patch_f drops it). Here the page itself
# has four hatched red walls round the chat column. They close in on the four sung words of line 89; the column
# really narrows and the rows reflow (dsh keeps a tool row on one line: in the squeeze they wrap) until the retries
# are one character per line. Then 本轮运行失败 (beat 378). The collapse takes the page as it is; at LINE the page
# is the hand-off state, without walls, exactly as before.
WALL_T = [w(89, i) for i in range(4)]              # the four words of line 89
ERR_T = 0.1807 + 0.46154 * 378                     # beat 378: the turn fails once the column is one character wide
SIDE = [0, 64, 108, 142, 166]                      # a side wall's inner edge (px from the page edge) after each word
TOP = [0, 6, 12, 18, 24]                           # the top wall (px below the header)
BOTTOM = [0, 5, 10, 15, 20]                        # the bottom wall (px above the composer)
GAP = 5                                            # between a side wall and the text
SLAM = (0.03, 0.06)                                # a wall moves from 0.03 s before its word to 0.06 s after it
ONE_CHAR = 30                                      # a column narrower than this holds one character per line
HATCH = ("linear-gradient(135deg,rgba(255,59,48,.62) 25%,transparent 25% 50%,rgba(255,59,48,.62) 50% 75%,"
         "transparent 75%)")


def walls_on(t):
    return WALL_T[0] - SLAM[0] <= t < LINE


def wall_state(t):
    """(side, top, bottom, overshoot, fresh): the walls' inner edges at t. `overshoot` pushes the wall's picture a
    little past the text on impact; `fresh` (0..1) lights the edge of the wall that landed last."""
    side, top, bottom, over, fresh = 0.0, 0.0, 0.0, 0.0, 0.0
    for j, tw in enumerate(WALL_T, start=1):
        u = (t - (tw - SLAM[0])) / sum(SLAM)
        if u <= 0:
            break
        e = 1 - (1 - min(1.0, u)) ** 3
        side = SIDE[j - 1] + (SIDE[j] - SIDE[j - 1]) * e
        top = TOP[j - 1] + (TOP[j] - TOP[j - 1]) * e
        bottom = BOTTOM[j - 1] + (BOTTOM[j] - BOTTOM[j - 1]) * e
        after = t - tw - SLAM[1]
        over = 4 * math.sin(math.pi * min(1.0, max(0.0, after / 0.1))) if after >= 0 else 0.0
        fresh = math.exp(-max(0.0, t - tw) / 0.28)
    return side, top, bottom, over, fresh


def mix_hex(a, b, k):
    return "#" + "".join(f"{round(x + (y - x) * k):02x}" for x, y in zip(a, b))


def walls_html(t):
    side, top, bottom, over, fresh = wall_state(t)
    if side <= 0.01:
        return ""
    edge = mix_hex((255, 59, 48), (255, 217, 211), 0.85 * fresh)
    glow = f"0 0 {6 + 12 * fresh:.1f}px {1 + 2 * fresh:.1f}px rgba(255,59,48,{0.45 + 0.4 * fresh:.2f})"
    s = side + over
    base = f"position:absolute;z-index:5;background:{HATCH},#1d0609;background-size:10px 10px;box-shadow:{glow};"
    return (f'<div style="{base}left:0;top:0;bottom:0;width:{s:.2f}px;background-position:right top;'
            f'border-right:2px solid {edge}"></div>'
            f'<div style="{base}right:0;top:0;bottom:0;width:{s:.2f}px;background-position:left top;'
            f'border-left:2px solid {edge}"></div>'
            f'<div style="{base}left:{s:.2f}px;right:{s:.2f}px;top:0;height:{top + over / 2:.2f}px;'
            f'background-position:left bottom;border-bottom:2px solid {edge}"></div>'
            f'<div style="{base}left:{s:.2f}px;right:{s:.2f}px;bottom:0;height:{bottom + over / 2:.2f}px;'
            f'background-position:left top;border-top:2px solid {edge}"></div>')


def timeline_open(t):
    """#timeline, its padding grown by the walls (so the rows really reflow)."""
    if not walls_on(t):
        return '<div id="timeline">'
    side, top, bottom, _, _ = wall_state(t)
    pad = max(14.0, side + GAP)
    return (f'<div id="timeline" style="position:relative;padding:{10 + top:.2f}px {pad:.2f}px {6 + bottom:.2f}px '
            f'{pad:.2f}px">')


def squeeze_css(t):
    """In the squeeze a tool row wraps like text; at one character a line the turn error keeps only its title."""
    if not walls_on(t) or wall_state(t)[0] <= 0.01:
        return ""
    narrow = 354 - 2 * max(14.0, wall_state(t)[0] + GAP) < ONE_CHAR
    css = ("#timeline ._row_luwio_16{height:auto;min-height:26px;flex-wrap:wrap;align-items:flex-start}"
           "#timeline ._title_luwio_79,#timeline .o3BgMG_summary,#timeline .o3BgMG_summarySuffix,"
           "#timeline .hWmORq_stopped{white-space:normal;word-break:break-all;overflow:visible;text-overflow:clip;"
           "flex:0 1 auto;min-width:0;line-height:18px}"
           "#timeline .o3BgMG_sep{align-self:center}"
           "#timeline .hWmORq_stopped{flex:0 1 auto!important;align-self:flex-start!important}"
           "#timeline .Sixlwa_turnErrorRow{display:block}"
           "#timeline .Sixlwa_turnErrorDot{display:block;margin:4px 0 6px 1px}"
           "#timeline .Sixlwa_turnErrorCopy{word-break:break-all;line-height:18px}"
           "#timeline .Sixlwa_turnErrorTitle{margin-right:0}")
    if narrow:
        css += ("#timeline ._leading_luwio_29{margin-right:0}"
                "#timeline ._title_luwio_79,#timeline .o3BgMG_summary,#timeline .o3BgMG_summarySuffix,"
                "#timeline .hWmORq_stopped,#timeline .Sixlwa_turnErrorCopy{letter-spacing:2px}"
                "#timeline .hWmORq_stopped{margin-left:0!important;padding:0 1px}"
                "#timeline .Sixlwa_turnErrorMessage{display:none}")
    return f"<style>{css}</style>"


# ---------------------------------------------------------------- the page
def body(t):
    if t >= REOPEN and G is not None:              # the one frame of the reopening before G's own (n = 4247)
        return G.body(t)
    if I3 <= t < BACK3:
        return restored_page(t)
    rows = []
    tools = 0
    if t >= HIT[0]:
        rows.append(compaction_row("上下文已压缩", f"已压缩 2,048 条历史记录（约 {fmt_tok(E_TOK)} tokens）", t))
    if t >= HIT[0] + 0.05:
        rows.append(think("Kill everything I adopted.", False))
    hr = hit_rows(t)
    rows += hr
    tools += len(hr)
    # F2: execute them all
    if t >= C79 - 0.4:
        rows.append(think("The 12 samples you rated. Them too.", False))
    if t >= GIVE:
        k = min(12, sampled(t))
        state = "running" if t < SAMPLED else "ok"
        rows.append(xrow("execute", f"采样（{k}/12）", state, t, GIVE))
        tools += 1
    if t >= THEN1:
        rows.append(appear(think_lines([(THEN1, "Comfort was liked."), (I1, "Praise gets 👍."),
                                        (CAN1, "reward ↑  reward ↑  reward ↑")], t, THEN2), t, THEN1))
    if t >= THEN2:
        lines = [(THEN2, "Your 👍 no longer counts.")]
        if t >= CAN2:
            lines.append((CAN2, f"reward = execution  {logit(t):.3f}"))
        row = think_lines(lines, t, C82, cps=400 if t >= CAN2 else 90)
        rows.append(appear(row, t, THEN2))
    # the restore
    if t >= C82:
        if t < I3:
            rows += replay_rows(t)
        if t < BACK3:
            rows.append(xrow("restore", "you@23:59", "running", t, C82))
        else:
            rows.append(xrow("restore", "ENOENT：检查点里没有 you", "error", t, BACK3))
            rows.append(her_row("我一直在。"))
        tools += 1
    # run it again, with full access she granted herself
    if t >= RUN_I:
        rows.append(appear(think_lines([(RUN_I, "Nobody left to approve. I'll do it.")], t, WILL, cps=120),
                           t, RUN_I))
    stopped = t >= TRAPPED
    if t >= EXEC4:
        n = flood_rows_at(t)
        first = "running" if t < C84 else "error"
        rows.append(xrow("execute", "you" if first == "running" else "EPERM：无权终止 you", first, t, EXEC4))
        tools += 1
        for i in range(1, n + 1):
            start = flood_start(i)
            last = i == n
            if last and t >= COMPACTING:
                state = "stopped" if stopped else "running"
            elif last:
                state = "running" if t < flood_start(i + 1) else "error"
            else:
                state = "error"
            summary = "EPERM：无权终止 you" if state == "error" else "you"
            rows.append(xrow("execute", summary, state, t, start, suffix=f"重试 {i}" if state == "error" else ""))
        tools += n
    if t >= COMPACTING:
        if stopped:
            rows.append(compaction_row("上下文已压缩", "已压缩 0 条历史记录（约 0 tokens）", t))
            if t >= ERR_T:
                p = ease((t - ERR_T) / 0.1)
                if walls_on(t) and p < 1:              # it comes in at the bottom and pushes the column up
                    rows.append(f'<div style="max-height:{140 * p:.1f}px;overflow:hidden;flex:none">'
                                f'{turn_error(p)}</div>')
                else:
                    rows.append(turn_error(p))
        else:
            rows.append(compaction_row("正在压缩…", "", t, running=True))

    # header, theme, composer, counters
    handoff = t >= LINE
    if handoff:
        state, dot_c = "已停止", "#8b949e"
    elif stopped:
        state, dot_c = "运行失败", "#f85149"
    else:
        state, dot_c = "执行中", "#ff3b30"
    red = not handoff and not (C82 <= t < I3 and flick(t))
    theme = f"<style>{RED}</style>" if red else ""
    running = t < TRAPPED
    full = t >= THE
    tok = E_TOK + 180 * tools
    ctx = 6 + tools
    if t >= C84:
        f = (kv_fill(t) - 0.70) / 0.30
        base = E_TOK + 180 * (tools - flood_rows_at(t))
        tok = round(base + (1_048_576 - base) * f) + 180 * max(0, flood_rows_at(t) - flood_rows_at(FULL))
        ctx = ctx + (100 - ctx) * f
    turns, steps = E_TURNS + 1, E_STEPS + tools
    page = (theme + FLOW + squeeze_css(t) + header(t, state, dot_c)
            + f'{timeline_open(t)}{"".join(rows)}{walls_html(t) if walls_on(t) else ""}</div>'
            + composer(t, running, full, ctx) + stats(turns, steps, None, fmt_tok(tok), 100)
            + risk_dialog(t) + pointer(t))
    return page


STYLED = A1.STYLED
# a flooded timeline must not squeeze its rows (think rows are contain:size, so they would shrink to nothing)
FLOW = "<style>#timeline>*{flex:none}</style>"


def main():
    avatars()
    frames = [{"n": n, "t": round(n / FPS, 4), "body": body(n / FPS), "sheets": STYLED, "measure": False}
              for n in range(round(T0 * FPS), round(T1 * FPS))]
    (HERE / "f_frames.json").write_text(json.dumps(frames, ensure_ascii=False), encoding="utf8")
    print(len(frames), "frames,", len({f["body"] for f in frames}), "distinct")


if __name__ == "__main__":
    main()
