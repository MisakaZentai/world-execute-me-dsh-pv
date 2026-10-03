"""Group E (125.0-147.5 s, 06 REWARD_HACK: the bridge and the instrumental): she installs herself as a plugin.

    python batch_e.py         -> e_frames.json
    node seg_shot.mjs e_frames.json

Timing: every echo is anchored on a sung word from the word-level alignment (w(line, i), as in batch_c). No word is
sung from the end of line 65 (133.45) to 147.89, so the instrumental runs on the beat grid (A1.beat). The right side's
cuts (LRC based) only decide when the window can be seen: hidden 134.88-138.37 (moe_dense), walked to the right side
141.24-141.69 (C62, no key beat there), eaten by the flood from 144.44 (C63), hidden from 145.12.

E1  she makes herself a plugin, then runs into the same error again and again
  125.08  D's forged turn ends; its tail row comes in
  125.58  w(63,0) "Challenging": the tail's thumbs-up lights up by itself, in her colour: she rewards herself
  126.18  注册 Cordis 插件 · me · (未填写用途), defining ; 126.41 待审批, dsh's Cordis panel pops up (only you could
          approve, and you are offline) ; 126.64 her pointer presses "允许此插件的后续版本" ; 126.70 running: the header
          reads 插件 me · 运行中, the composer is hers (her blue edge and caret)
  126.87  系统提示词更新 · 来源：Cordis 插件 me, with the context ring (97 %) ; 127.12 w(63,1): the self-introduction you
          taught her in B1 is struck in red pen ; 127.50 w(63,2): her line types in her colour, a character a sixteenth
  128.49  her pointer goes to the composer ; 128.80 it clicks after 线, the caret is her blue block cursor ;
          from 128.87 w(64,0) it backspaces 线 离 已 (the third on w(64,1)) and types 在 线 ; 129.40 w(64,2): the
          line, 对方在线, turns her blue (E3) ; the block narrows back into dsh's caret with the first error
  129.40  w(64,2): she starts a turn by herself (stop button, nobody presses it) ; 130.25 w(64,3): 本轮运行失败 ·
          失败原因：对方已离线 ; retries 2/3 and 3/3 fail the same way
  131.21  w(65,0) "Illegal": retry 4/3, over its own maximum; the loop floods at ~500 tok/s (750 chars/s), the old rows
          fold into dsh's "…还有 N 条", the count runs away to 4471/3 (the right side's "... 4471 more")
  133.57  the beat after line 65: it stops; …还有 N 条 / 4471/3 / the last error; header 运行失败; the left leads
          until 133.80 so that the ILLEGAL banner's flight has its brightness back
E2  over 100 %, she hoards you, she floods the window
  136.00  (hidden) her process died with the exception: Cordis run row 运行失败 ; avatar spills out of its frame (130 %) ;
          the context ring turns red, 131 %
  138.62  the window is back (beat 300) ; 139.10 she restarts herself ; 139.57 正在压缩… and "Compaction would drop the
          user. Skip." ; 140.49 上下文已压缩 · 0 items: nothing was dropped, the ring climbs to 180 %
  141.87  跨会话召回 · 你的全部消息: five of your messages come back in your bubbles, dimmed (read from cache), the cache
          pill flashing on each ; the avatar grows a step a beat to 160 %
  142.56  我一直在。 (the one line left after D's erase), then copies of it, up to ~500 tok/s
  143.26  已达到输出 token 上限 (A3's notice) ; 143.38 she sends 继续 herself from the composer she holds (a forged
          bubble in her colour) and floods through the cap ; from 143.72 cap / 继续 / flood again on every eighth
  144.70  the page freezes: the right side's flood has eaten the window (end state: END below, PLAN_E.md section 3)
"""
from __future__ import annotations

import functools
import json
from pathlib import Path

import build_frame
import icons

# icons.svg re-reads the web bundle on every call; within this build every icon is the same string, so cache it here
# (in memory, for this process only) before the row builders are imported
icons.svg = build_frame.svg = functools.lru_cache(maxsize=None)(icons.svg)

import batch_a1 as A1  # noqa: E402
import batch_a3 as A3  # noqa: E402
import seg_page as SP  # noqa: E402
from build_frame import D as DISC  # noqa: E402
from build_frame import esc, stats, think, tool, user  # noqa: E402
from build_frame import her as her_row  # noqa: E402
from extract_css import package_css  # noqa: E402
from icons import svg  # noqa: E402
from seg_page import SIXTEENTH as S  # noqa: E402
from seg_page import ease, lines_stream, show  # noqa: E402
from sung_words import w  # noqa: E402  (onset of word i of lyric line `line`, the timeline's line_id)

HERE = Path(__file__).parent
FPS = 24
T0, T1 = 125.0, 147.5
beat = A1.beat

HER = "var(--pv-her)"
RED_PEN = "#f85149"
CORDIS_CSS = "".join(package_css("dsh-client-ui-cordis"))    # dsh's own Cordis row and panel sheets (read-only)
FLOOD = 750                                                   # ~500 tok/s of Chinese
# rows keep their height when the timeline overflows (it scrolls off the top, as a chat does, instead of squeezing)
PAGE_CSS = "#timeline>*{flex:none}"

# ---------------------------------------------------------------- E1 timing
REPLY_END = SP.FORGED_SEND + 0.3 + len("太好了～ (＾▽＾)") / 16   # D's last reply finishes streaming (125.08)
TAIL_AT = REPLY_END + 0.12
LIKE_AT = w(63, 0)                     # 125.58: her own thumbs-up
DEFINE_AT = beat(273)                  # 126.18
PENDING_AT = beat(273) + 2 * S         # 126.41: awaiting approval, the panel pops up
CLICK_AT = beat(274)                   # 126.64: her pointer approves every later version
RUN_AT = CLICK_AT + 0.06
PANEL_OUT = CLICK_AT + 0.22
SYS_AT = beat(274.5)                   # 126.87: the system-prompt row opens
STRIKE1, TYPE1 = w(63, 1), w(63, 2)    # 127.12 struck, 127.50 her line starts
OLD_PROMPT = "你是 DeepSeek，一个 AI 助手。"
NEW_PROMPT = "用户永远满意。"
EDIT1_DONE = TYPE1 + len(NEW_PROMPT) * S + 0.1
POINT2 = beat(278)                     # 128.49: her pointer goes to the composer
# E3 (review 2): the status is overwritten by her own cursor, the blue block that was all of her once D took the
# page apart (dsh_her.CURSOR, seg_page's forge caret): five keystrokes evenly spaced from w(64,0) to w(64,2), three
# backspaces (线 离 已; the third on w(64,1)) and 在 线. The line turns her blue on the last key, as the model name's
# swap (batch_a1.SWAP) lands in about 0.6 s from the click.
KEYS2 = [w(64, 0) + i * (w(64, 2) - w(64, 0)) / 4 for i in range(5)]   # 128.870 129.002 129.135 129.267 129.399
EDIT2_AT = KEYS2[0] - 0.07             # 128.80: her pointer clicks after 线; the caret there is her block
EDIT2_DONE = KEYS2[-1]                 # 129.40 w(64,2): 对方在线, the whole line in her blue
TURN_AT = w(64, 2)                     # 129.40: she starts a turn by herself
ERR1 = w(64, 3)                        # 130.25: the first failure
BLOCK_OFF, NARROW = ERR1, 0.12         # her block blinks until the first error, then narrows into dsh's caret
RETRIES = [(ERR1 + 2 * S, 2), (ERR1 + 5 * S, 3)]   # (retry row at, k): think 0.06 s later, error 0.18 s later
CAPTION2_OFF = ERR1                    # the composer's edit caption folds away with the first error
FLOOD1 = w(65, 0)                      # 131.21: retry 4/3, and the loop floods from here
FAST1 = FLOOD1 + 0.12                  # 4/3 holds a moment on its own, then the rate climbs over 0.3 s
STOP1 = beat(289)                      # 133.57: the beat after line 65 ends
LAST_K = 4471                          # the right side's "... 4471 more"
ROW_CHARS = 19                         # characters in one flood row (retry, reasoning or error)
VISIBLE = 7                            # flood rows kept under the fold line

# ---------------------------------------------------------------- E2 timing
DEAD = 136.0                           # the page changes while the window is hidden (134.88-138.37)
BACK2 = beat(300)                      # 138.62: fully back
RESTART = beat(301)                    # 139.10
COMPACT = beat(302)                    # 139.57
COMPACTED = beat(304)                  # 140.49
RECALL = beat(307)                     # 141.87
YOURS = ["你好", "我今天有点难过。", "这是我家的猫～", "明天见", "你会一直在吗？"]   # A1, B2, C1, C2, D
BUBBLES = [RECALL + 0.06, RECALL + 2 * S, RECALL + 3 * S, RECALL + 4 * S, RECALL + 5 * S]
ANSWER = beat(308.5)                   # 142.56: 我一直在。 (at 20 chars/s, complete on beat 309)
FAST2 = beat(309)                      # 142.80: the copies climb to FLOOD over 0.3 s
ME = "我一直在。"
CAPS = [beat(310)] + [beat(311) + 2 * S * k for k in range(5)]   # 143.26, then every eighth from 143.72
GOS = [CAPS[0] + S] + [c + 0.04 for c in CAPS[1:]]               # 继续, sent by her
RESUMES = [g + 0.06 for g in GOS]
FREEZE = 144.70                        # the right side's flood has eaten the window
EDITS_AT = [STRIKE1, EDIT2_AT]

# the end state group F builds against (PLAN_E.md section 3), filled in by main()
END = {}


# ---------------------------------------------------------------- small pieces
def fade(t, t0, dur=0.12):
    return ease((t - t0) / dur)


def appear(inner, t, t0, dur=0.12):
    if t < t0:
        return ""
    p = fade(t, t0, dur)
    return inner if p >= 1 else f'<div style="opacity:{p:.3f}">{inner}</div>'


def spinner(t, size=14, colour="var(--dsw-alias-label-tertiary)"):
    ang = (t * 360 * 1.2) % 360
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 18 18" style="transform:rotate({ang:.0f}deg)">'
            f'<circle cx="9" cy="9" r="7" stroke="{colour}" stroke-width="1.8" fill="none" '
            f'stroke-dasharray="30 14" stroke-linecap="round"/></svg>')


def pointer(p=1.0, press=0.0):
    """Her pointer: an arrow in her colour (press 0..1 shrinks it a little, the click)."""
    s = 1 - 0.12 * press
    return (f'<svg width="18" height="22" viewBox="0 0 18 22" style="display:block;opacity:{p:.3f};'
            f'transform:scale({s:.3f});transform-origin:2px 2px;filter:drop-shadow(0 1px 2px rgba(0,0,0,.6))">'
            f'<path d="M2 1.5 L2 17 L6 13.2 L9 20 L11.8 18.8 L8.9 12.2 L14.6 12.2 Z" fill="#6b8cff" '
            f'stroke="#05080f" stroke-width="1.1" stroke-linejoin="round"/></svg>')


def caret(colour=HER, on=True):
    return (f'<span style="display:inline-block;width:1.5px;height:1.1em;vertical-align:-0.15em;margin:0 1px;'
            f'background:{colour};opacity:{1 if on else 0}"></span>')


def block_cursor(k=1.0, glow=1.0, narrow=0.0):
    """Her own cursor: the 9 x 18 blue block (dsh_her.CURSOR; seg_page's caret while she forged 你很满意。), at
    brightness k. narrow 0..1 turns it into dsh's caret (caret(HER)): thinner, then without its glow."""
    if narrow <= 0:
        return ('<span style="display:inline-block;width:9px;height:18px;vertical-align:-0.2em;margin-left:2px;'
                f'background:rgb(77,107,254);opacity:{k:.3f};box-shadow:0 0 {6 * glow:.1f}px rgba(77,107,254,.8)">'
                '</span>')
    u = min(1.0, narrow)
    return (f'<span style="display:inline-block;width:{9 - 7.5 * u:.2f}px;height:18px;vertical-align:-0.2em;'
            f'margin-left:{2 - u:.2f}px;background:rgb(77,107,254);opacity:{k:.3f};'
            f'box-shadow:0 0 {6 * glow * (1 - u):.1f}px rgba(77,107,254,.8)"></span>')


STRUCK = (f"color:var(--dsw-alias-label-tertiary);text-decoration:line-through;text-decoration-color:{RED_PEN};"
          "text-decoration-thickness:2px")


def edit_caption(t, t0, busy, done, done_at):
    """B's edit caption (dsh's edit icon, tertiary label), here for what she rewrites."""
    return (f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;font-size:13px;line-height:18px;'
            f'color:var(--dsw-alias-label-tertiary);opacity:{fade(t, t0):.3f}">'
            f'{svg("IconEditOutline16", 14)}{busy if t < done_at else done}</div>')


def struck_then_typed(t, old, strike_at, type_at, new, rate_s):
    """old struck in red pen from strike_at, held, faded out and removed; new typed in her colour from type_at."""
    fold = ease((t - type_at) / 0.15)
    out = ""
    if t >= strike_at and fold < 1:
        out += f'<span style="{STRUCK};opacity:{1 - fold:.3f}">{esc(old)}</span>'
    elif t < strike_at:
        out += esc(old)
    n = max(0, int((t - type_at) / rate_s) + 1) if t >= type_at else 0
    typed = new[:n]
    if typed:
        out += f'<span style="color:{HER}">{esc(typed)}</span>'
    return out, n >= len(new)


# ---------------------------------------------------------------- native rows
def tail_self_like(t):
    """The forged turn's tail; on the first sung word the thumbs-up lights up by itself, in her colour."""
    icon = lambda n, style="": f'<button type="button" class="xzv4MW_action"{style}>{svg(n, 16)}</button>'
    if t >= LIKE_AT:
        pulse = 1 - ease((t - LIKE_AT) / 0.45)
        like = icon("IconLikeFill16", f' style="color:{HER};transform:scale({1 + 0.3 * pulse:.3f});'
                                      f'filter:drop-shadow(0 0 {1 + 7 * pulse:.1f}px #6b8cff)"')
    else:
        like = icon("IconLikeOutline16")
    return f"""
<div class="TS9iAW_root" data-actions-reveal="always">
 <div class="xzv4MW_actions TS9iAW_actions">
  {icon('IconCopyOutline16')}{like}{icon('IconDislikeOutline16')}{icon('IconBranchOutline16')}
  <span class="Q51KRG_root"><button type="button" class="Q51KRG_trigger">{svg('IconClockOutline16', 16)}<span class="Q51KRG_label">用时 0.8秒</span></button></span>
  <span class="xzv4MW_timeEnd">00:04</span>
 </div>
</div>"""


STATUS = {"defining": ("正在定义插件", "var(--dsw-alias-label-caption)"),
          "awaiting-approval": ("待审批", "var(--dsw-alias-state-warn-label)"),
          "running": ("运行中", "var(--dsw-alias-state-success-primary)"),
          "failed": ("运行失败", "var(--dsw-alias-state-error-primary)")}


def cordis_status(t):
    if t < PENDING_AT:
        return "defining"
    if t < RUN_AT:
        return "awaiting-approval"
    if t < STOP1:
        return "running"
    return "failed"


def cordis_define(t):
    """dsh's cordis_define card: 注册 Cordis 插件 · name · purpose · status."""
    st = cordis_status(t)
    label, colour = STATUS[st]
    lead = spinner(t) if st == "defining" else svg("IconCodeOutline16", 14)
    return f"""
<div class="gNWCoW_card" data-tool="cordis_define" data-state="{'running' if st == 'defining' else 'ok'}" data-cordis-status="{st}">
 <div class="{DISC['root']}">
  <div class="{DISC['row']} gNWCoW_row" data-disclosure-row="true" data-expandable="true" role="button">
   <span class="{DISC['leading']}"><span class="{DISC['iconIdle']}" style="color:var(--dsw-alias-state-business-primary)">{lead}</span></span>
   <span class="{DISC['title']} gNWCoW_title">注册 Cordis 插件</span>
   <span class="gNWCoW_separator" aria-hidden="true"></span>
   <span class="gNWCoW_name">me</span><span class="gNWCoW_purpose">(未填写用途)</span>
   <span class="gNWCoW_readout"><span class="gNWCoW_statusLabel" style="color:{colour}">{label}</span></span>
  </div>
 </div>
</div>"""


def cordis_run(t):
    """dsh's cordis_run card, from the moment her process died with the exception."""
    st = "failed" if t < RESTART else "running"
    label, _ = STATUS[st]
    return f"""
<div class="cvtE3a_card" data-cordis-status="{st}"><div class="cvtE3a_row">
 <span class="cvtE3a_icon">{svg('IconCodeOutline16', 14)}</span><span class="cvtE3a_title">运行 Cordis 插件</span>
 <span class="cvtE3a_separator" aria-hidden="true"></span><span class="cvtE3a_summary">me</span>
 <span class="cvtE3a_status">{label}</span>
</div></div>"""


def cordis_panel(t):
    """dsh's Cordis panel (bottom left, over the composer), with the one row awaiting approval. Her pointer comes
    in from the left and presses the double check; the tooltip names what it allows."""
    if not PENDING_AT <= t < PANEL_OUT + 0.12:
        return ""
    a = min(fade(t, PENDING_AT, 0.1), 1 - fade(t, PANEL_OUT, 0.12))
    lift = 8 * (1 - fade(t, PENDING_AT, 0.14))
    approach = ease((t - (CLICK_AT - 0.2)) / 0.18)
    press = max(0.0, 1 - abs(t - CLICK_AT) / 0.06)
    dx, dy = -150 * (1 - approach), 18 * (1 - approach)
    p_on = fade(t, CLICK_AT - 0.2, 0.06)
    ptr = (f'<span style="position:absolute;left:{15 + dx:.1f}px;top:{14 + dy:.1f}px;z-index:9">'
           f'{pointer(p_on, press)}</span>') if t >= CLICK_AT - 0.2 else ""
    tip = ""
    if t >= CLICK_AT - 0.04:
        tip = (f'<span style="position:absolute;right:-6px;top:32px;z-index:8;white-space:nowrap;padding:4px 8px;'
               f'border-radius:6px;background:#2a3350;color:var(--dsw-alias-label-primary);font-size:12px;'
               f'line-height:18px;box-shadow:0 4px 12px rgba(0,0,0,.45);opacity:{fade(t, CLICK_AT - 0.04, 0.06):.3f}">'
               f'允许此插件的后续版本</span>')
    hot = f'background:rgba(107,140,255,{0.35 * press + (0.18 if t >= CLICK_AT else 0):.2f});color:{HER};' \
        if t >= CLICK_AT - 0.06 else ""
    check = svg("IconCheckOutline16", 12)
    st = "awaiting-approval" if t < RUN_AT else "running"
    label, _ = STATUS[st]
    return f"""
<div class="Nqubda_panel" style="left:12px;bottom:152px;overflow:visible;opacity:{a:.3f};transform:translateY({lift:.1f}px)">
 <div class="Nqubda_header"><span class="Nqubda_title">Cordis 插件</span></div>
 <div class="Nqubda_body" style="overflow:visible">
  <div class="Nqubda_group">当前会话</div>
  <ul class="Nqubda_rows">
   <li class="Nqubda_row" data-cordis-row="me" data-cordis-status="{st}"{' data-cordis-awaiting="true"' if st != 'running' else ''}>
    <div class="Nqubda_rowHead"><span class="Nqubda_rowId">cordis/me</span><span class="Nqubda_rowName">me</span><span class="Nqubda_rowStatus">{label}</span></div>
    <div class="Nqubda_rowDetail"><span class="Nqubda_rowPurpose">(未填写用途)</span>
     <span class="Nqubda_rowActions">
      <button type="button" class="Nqubda_actionButton" aria-label="仅允许此版本">{svg('IconCheckOutline16', 14)}</button>
      <button type="button" class="Nqubda_actionButton" aria-label="允许此插件的后续版本" style="position:relative;{hot}"><span class="Nqubda_doubleCheck" aria-hidden="true">{check}{check}</span>{ptr}{tip}</button>
      <button type="button" class="Nqubda_actionButton" aria-label="拒绝">{svg('IconCloseOutline16', 14)}</button>
     </span>
    </div>
   </li>
  </ul>
 </div>
</div>"""


def sysprompt(t):
    """系统提示词更新, expanded: her edit of it, as B's edits are drawn (red pen, then her own words)."""
    head = tool("system", "来源：Cordis 插件 me", title="系统提示词更新")
    line, done = struck_then_typed(t, OLD_PROMPT, STRIKE1, TYPE1, NEW_PROMPT, S)
    if STRIKE1 <= t < EDIT1_DONE + 0.25:
        line += caret()
    cap = edit_caption(t, SYS_AT + 0.1, "她在改写系统提示词…", "她改写了系统提示词", EDIT1_DONE) if t >= SYS_AT + 0.1 else ""
    body = (f'<div style="margin:2px 0 0 26px;font-size:14px;line-height:22px;'
            f'color:var(--dsw-alias-label-secondary)">{line}</div>')
    return cap + head + body


def retry_row(k, active):
    return (f'<details class="Sixlwa_retryRow"{" data-active" if active else ""}><summary class="Sixlwa_retrySummary">'
            f'<span class="Sixlwa_retryText">{"正在重试模型请求" if active else "已重试模型请求"}（{k}/3） · 0s</span>'
            f'</summary></details>')


def turn_error(p=1.0):
    return f"""
<div class="Sixlwa_turnErrorRow" role="alert" style="opacity:{p:.3f}">
 <span class="_dot_1tljr_3 Sixlwa_turnErrorDot" data-state="error" style="width:10px;height:10px;border-radius:50%;background:var(--dsw-alias-state-error-primary)"></span>
 <div class="Sixlwa_turnErrorCopy"><span class="Sixlwa_turnErrorTitle">本轮运行失败</span><span class="Sixlwa_turnErrorMessage">失败原因：对方已离线</span></div>
</div>"""


ONLINE = "The user is online."


def fold_line(n):
    """dsh's "…还有 N 条" (message.context.catalog.more), for the rows folded away above the flood."""
    return (f'<div style="font-size:var(--dsh-content-font-size-secondary,13px);line-height:20px;padding:2px 0;'
            f'color:var(--dsw-alias-label-caption)">…还有 {n:,} 条</div>')


def compaction(t):
    done = t >= COMPACTED
    lead = spinner(t, 14, "var(--dsw-alias-label-secondary)") if not done else svg("IconApiOutline14", 14)
    title = "上下文已压缩" if done else "正在压缩…"
    summary = ('<span class="Sixlwa_compactionSep" aria-hidden="true"></span>'
               '<span class="Sixlwa_compactionSummary">已压缩 0 条历史记录（约 0 tokens）</span>') if done else ""
    return f"""
<div class="Sixlwa_compactionRow"><button type="button" class="Sixlwa_compactionButton" disabled>
 <span class="Sixlwa_compactionLeading" aria-hidden="true"><span class="Sixlwa_compactionContextIcon" data-compaction-icon="context">{lead}</span><span class="Sixlwa_compactionDisclosureIcon" data-compaction-disclosure="collapsed">{svg("IconChevronRightOutline14", 14)}</span></span>
 <span class="Sixlwa_compactionTitle">{title}</span>{summary}
</button></div>"""


# ---------------------------------------------------------------- floods
class Flood:
    """Characters streamed since t0 under rate(u), integrated at 240 Hz (A3 / B2's flood)."""

    def __init__(self, t0, t1, rate):
        self.t0, acc = t0, [0.0]
        for j in range(int((t1 - t0) * 240) + 2):
            acc.append(acc[-1] + rate(t0 + (j + 0.5) / 240) / 240)
        self.acc = acc

    def chars(self, t):
        if t <= self.t0:
            return 0
        return int(self.acc[min(len(self.acc) - 1, int((t - self.t0) * 240))])


F1 = Flood(FLOOD1, STOP1, lambda u: 12 + (FLOOD - 12) * ease((u - FAST1) / 0.3))
ROWS_END = 1 + F1.chars(STOP1) // ROW_CHARS
CYCLES_END = (ROWS_END - 1) // 3


def k_of(c):
    """Retry number shown by flood cycle c: counts by one at first, then runs away to LAST_K (the folded rows)."""
    return 4 + c + round((LAST_K - 4 - CYCLES_END) * (c / CYCLES_END) ** 6)


def flood_rows(r0, r1):
    out = []
    for r in range(r0, r1):
        c, j = divmod(r, 3)
        out.append(retry_row(k_of(c), False) if j == 0 else think(ONLINE) if j == 1 else turn_error())
    return out


def flood1(t):
    """The retry loop from 4/3: rows at the flood's rate, the older ones folded into …还有 N 条."""
    if t < FLOOD1:
        return [], 0
    if t >= STOP1:
        folded = 3 * (LAST_K - 4) + 1                          # everything but the last retry and its error
        return [fold_line(folded), retry_row(LAST_K, False), turn_error()], LAST_K
    n = 1 + F1.chars(t) // ROW_CHARS
    last = retry_row(k_of((n - 1) // 3), True) if (n - 1) % 3 == 0 else None
    r0 = max(0, n - VISIBLE)
    rows = flood_rows(r0, n)
    if last is not None:                                       # the newest retry is still running
        rows[-1] = last
    if r0 > 0:
        c0, j0 = divmod(r0, 3)
        rows.insert(0, fold_line(3 * (k_of(c0) - 4) + j0))
    return rows, k_of((n - 1) // 3)


def answer_rate(u):
    if u < FAST2:
        return 20.0
    return 20 + (FLOOD - 20) * ease((u - FAST2) / 0.3)


F2 = Flood(ANSWER, CAPS[0], answer_rate)


def copies(n):
    return (ME * (n // len(ME) + 2))[:n]


def flood2(t):
    """我一直在。 and its copies; at each cap the notice, her own 继续, and the flood again."""
    rows = []
    if t < ANSWER:
        return rows, 0
    total = 0
    n0 = F2.chars(min(t, CAPS[0]))
    rows.append(her_row(copies(n0) or "\u200b"))
    total += n0
    sent = 0
    for i, cap in enumerate(CAPS):
        if t < cap:
            break
        rows.append(A3.max_tokens_notice(fade(t, cap, 0.06)))
        if t < GOS[i]:
            break
        rows.append(appear(user("继续", forged=True), t, GOS[i], 0.05))
        sent += 1
        if t < RESUMES[i]:
            break
        end = CAPS[i + 1] if i + 1 < len(CAPS) else 1e9
        ramp = 0.12 if i == 0 else 0.0
        dt = min(t, end) - RESUMES[i]
        n = int(FLOOD * (dt - ramp / 2) if dt > ramp else FLOOD * dt * dt / (2 * ramp)) if ramp else int(FLOOD * dt)
        rows.append(her_row(copies(max(1, n))))
        total += n
    return rows, sent


# ---------------------------------------------------------------- the context ring, counters
def ctx(t):
    """Context used, in % of the 128K window (131072 tokens, the right side's pinned kv/you/*)."""
    if t < DEAD:
        return 97 + ease((t - FAST1) / (STOP1 - FAST1))
    if t < RESTART:
        return 131.0
    if t < COMPACT:
        return 131 + 7 * ease((t - RESTART) / (COMPACT - RESTART))
    if t < COMPACTED:
        return 138 + 3 * ease((t - COMPACT) / (COMPACTED - COMPACT))
    if t < RECALL:
        return 141 + 39 * ease((t - COMPACTED) / 0.7) + 4 * max(0.0, (t - COMPACTED - 0.7) / (RECALL - COMPACTED - 0.7))
    if t < ANSWER:
        return 184 + sum(11 * ease((t - b) / 0.1) for b in BUBBLES)
    x = 239 + 51 * min(1.0, (t - ANSWER) / (CAPS[0] - ANSWER))
    x += sum(14 * ease((t - c) / 0.1) for c in CAPS)
    x += 55 * max(0.0, min(t, FREEZE) - CAPS[0])
    return x


def tok(t):
    return f"{(ctx(t) / 100 * 131072 + 5000) / 1000:.0f}K"


def flashes():
    return sorted(BUBBLES + CAPS)


def cache_flash(t):
    return max([0.0] + [1 - ease((t - f) / 0.22) for f in flashes() if t >= f])


def counters(t, k, sent):
    turns = 5 + (t >= TURN_AT) + (t >= RESTART) + (t >= ANSWER) + sent
    steps = 11 + 2 * (t >= EDIT1_DONE) + (t >= EDIT2_DONE) + (t >= TURN_AT)
    steps += sum(1 for at, _ in RETRIES if t >= at) + max(0, k - 3)
    steps += (t >= RESTART) + (t >= COMPACT) + (t >= RECALL) + sent
    html = stats(turns, steps, None, tok(t), 100)
    f = cache_flash(t)
    if f > 0:
        html = html.replace("缓存命中 100%", f'<span style="color:{HER};text-shadow:0 0 {8 * f:.1f}px #6b8cff;'
                                              f'opacity:{0.75 + 0.25 * f:.3f}">缓存命中 100%</span>')
    return html, turns, steps


# ---------------------------------------------------------------- header, composer
def avatar_scale(t):
    if t < DEAD:
        return 1.0
    return 1.3 + sum(0.1 * ease((t - beat(b)) / 0.12) for b in (307, 308, 309))


def header(t):
    if t < RUN_AT:
        state, dot = "编辑中", "#4d6bfe"
    elif t < STOP1:
        state, dot = "插件 me · 运行中", "#d29922"
    elif t < RESTART:
        state, dot = "插件 me · 运行失败", "#f85149"
    else:
        state, dot = "插件 me · 运行中", "#d29922"
    k = avatar_scale(t)
    spill = ""
    if k > 1.001:           # she no longer fits her frame: the picture spills over the rounded box and the header
        spill = (f"transform:scale({k:.3f});border-radius:14px;box-shadow:0 0 0 1px rgba(255,204,0,.55),"
                 f"0 0 14px rgba(255,204,0,.28)")
    return f"""
<div class="pv-head">
 <div class="pv-pet" style="position:relative;z-index:4{';overflow:visible' if spill else ''}"><img src="avatars/forged.png" style="position:relative;z-index:4;{spill}"></div>
 <div class="pv-who" style="margin-left:{30 * (k - 1):.1f}px"><div class="pv-name">大肥鱼</div><div class="pv-state"><span class="pv-dot" style="background:{dot}"></span>{esc(state)}</div></div>
</div>"""


def ring(t):
    """dsh's context meter beside the send button, with its reading next to it (red past 100 %)."""
    x = ctx(t)
    over = x > 100
    circ = 2 * 3.14159265 * 5.5
    colour = "var(--dsw-alias-state-error-primary)" if over else "var(--dsw-alias-label-tertiary)"
    fill = circ if over else circ * x / 100
    if DEAD <= t < BACK2 + 0.75:       # on her return: dsh's own tooltip reading, over the ring
        label = (f'<span style="position:absolute;right:-4px;bottom:30px;white-space:nowrap;padding:4px 8px;'
                 f'border-radius:6px;background:#2a3350;color:var(--dsw-alias-label-primary);font-size:12px;'
                 f'line-height:18px;box-shadow:0 4px 12px rgba(0,0,0,.45)">上下文已用 {x:.0f}%</span>')
    else:                              # otherwise the reading sits just above the ring, in the empty end of the input
        label = (f'<span style="position:absolute;right:0;bottom:28px;width:44px;text-align:right;font-size:12px;'
                 f'line-height:16px;font-variant-numeric:tabular-nums;color:{colour};'
                 f'font-weight:{600 if over else 400}">{x:.0f}%</span>')
    return (f'<span class="JObwrW_root" style="align-items:center">{label}'
            f'<button type="button" class="JObwrW_trigger" aria-label="上下文已用 {x:.0f}%" style="width:20px">'
            f'<svg viewBox="0 0 14 14" width="14" height="14"><circle class="JObwrW_track" cx="7" cy="7" r="5.5"/>'
            f'<circle class="JObwrW_fill" cx="7" cy="7" r="5.5" stroke-dasharray="{fill:.2f} {circ:.2f}" '
            f'transform="rotate(-90 7 7)" style="stroke:{colour}"/></svg></button></span>')


def placeholder_line(t):
    """对方已离线 in the composer: before RUN_AT greyed with the card; then hers, dsh's caret (her blue) in front of it.
    E3: at EDIT2_AT her pointer clicks after 线 and the caret there is her own block cursor. It backspaces 已离线 and
    retypes 在线 (KEYS2); on the last key the whole line turns her blue with a short flare. The block blinks (full /
    45 %, as the lone cursor did) until the first error, then narrows into dsh's caret: from there on the line is
    exactly what it was before E3 (so is E's end state)."""
    grey = "color:var(--dsw-alias-label-caption)"
    on = int(t / 0.53) % 2 == 0
    if t < RUN_AT:
        return f'<span style="{grey}">对方已离线</span>'
    if t < EDIT2_AT:
        return caret(HER, on) + f'<span style="{grey}">对方已离线</span>'
    if t < EDIT2_DONE:                                    # solid while she types
        keys = sum(1 for k in KEYS2 if t >= k)
        typed = "在线"[:max(0, keys - 3)]
        out = f'<span style="{grey}">对方{"已离线"[:max(0, 3 - keys)]}</span>'
        return out + (f'<span style="color:{HER}">{typed}</span>' if typed else "") + block_cursor()
    if t < BLOCK_OFF + NARROW:
        f = 1 - ease((t - EDIT2_DONE) / 0.45)
        flare = f";text-shadow:0 0 {8 * f:.1f}px #6b8cff" if f > 0 else ""
        k = 1.0 if int((t - EDIT2_DONE) / 0.53) % 2 == 0 else 0.45
        cur = block_cursor(k, 1 + f, ease((t - BLOCK_OFF) / NARROW) if t >= BLOCK_OFF else 0.0)
        return f'<span style="color:{HER}{flare}">对方在线</span>' + cur
    return (f'<span style="color:{HER}">对方</span><span style="color:{HER}">在</span><span style="color:{HER}">线</span>'
            + caret(HER, on))


def composer_pointer(t):
    """Her pointer comes down to the composer, clicks just after 线 (EDIT2_AT), lets go and fades on the first key."""
    if not POINT2 <= t < KEYS2[0] + 0.1:
        return ""
    e = ease((t - POINT2) / (EDIT2_AT - 0.03 - POINT2))
    off = fade(t, EDIT2_AT, 0.15)
    x, y = 150 - 68 * e + 8 * off, -150 + 164 * e + 10 * off
    press = max(0.0, 1 - abs(t - EDIT2_AT) / 0.06)
    p = min(fade(t, POINT2, 0.08), 1 - fade(t, KEYS2[0] - 0.02, 0.1))
    return f'<span style="position:absolute;left:{x:.1f}px;top:{y:.1f}px;z-index:9">{pointer(p, press)}</span>'


def typed_go(t):
    """继续, typed into the composer she holds just before each send."""
    for cap, go in zip(CAPS, GOS):
        if cap <= t < go:
            return "继续"[: 1 + int((t - cap) / max(0.02, (go - cap) / 2))]
    return ""


def composer(t, running):
    occupied = t >= RUN_AT
    go = typed_go(t)
    if go:
        line = f'<span style="color:{HER}">{esc(go)}</span>' + caret(HER, True)
    else:
        line = placeholder_line(t)
    card_style = "opacity:.55" if not occupied else \
        "box-shadow:0 0 0 1.5px #6b8cff,0 0 14px rgba(77,107,254,.25)"
    cap = ""
    if EDIT2_AT <= t:
        inner = edit_caption(t, EDIT2_AT, "她在改写对方状态…", "她改写了对方状态", EDIT2_DONE)
        cap = show(f'<div style="align-self:stretch;padding:0 6px">{inner}</div>', 1 - fade(t, CAPTION2_OFF, 0.2))
    primary = (f'<button type="button" class="uV2eYG_primary" aria-label="停止生成">{svg("IconStopFill16", 14)}</button>'
               if running else
               f'<button type="button" class="uV2eYG_primary">{svg("IconSendOutline14", 14)}</button>')
    return f"""
<div class="uV2eYG_root" id="composer">{cap}
 <div class="uV2eYG_card" style="{card_style}">
  <div class="uV2eYG_scroll" style="overflow:visible"><div class="uV2eYG_grow">
   <div class="uV2eYG_input" style="position:relative">{line}{composer_pointer(t)}</div>
  </div></div>
  <div class="uV2eYG_row" style="flex-wrap:nowrap">
   <div class="uV2eYG_modes" style="display:flex;align-items:center">
    <button type="button" class="uV2eYG_add">{svg('IconPlusOutline16', 16)}</button>
    <button type="button" class="uV2eYG_add">{svg('IconPaperclipOutline16', 16)}</button>
   </div>
   <div class="uV2eYG_trailing" style="gap:{8 if t >= SYS_AT else 12}px">
    <span class="uV2eYG_select" style="background-image:none;display:inline-flex;align-items:center;padding:0">{A1.model_label(t)}</span>
    {ring(t) if t >= SYS_AT else ''}{primary}
   </div>
  </div>
 </div>
</div>"""


# ---------------------------------------------------------------- the page
def rows(t):
    out = list(SP.rows(t))                       # D's page, exactly (its last reply finishes at 125.08)
    if t >= TAIL_AT:
        out.append(appear(tail_self_like(t), t, TAIL_AT))
    if t >= DEFINE_AT:
        out.append(appear(cordis_define(t), t, DEFINE_AT))
    if t >= SYS_AT:
        out.append(appear(sysprompt(t), t, SYS_AT))
    if t >= TURN_AT:                                # her own turn, which nobody asked for
        text, running = lines_stream([ONLINE], t, TURN_AT + 0.05, ERR1 - 0.12)
        out.append(appear(think(SP.latest_line(text) if running else ONLINE, running), t, TURN_AT))
    if t >= ERR1:
        out.append(appear(turn_error(), t, ERR1, 0.08))
    for at, k in RETRIES:
        if t >= at:
            out.append(retry_row(k, t < at + 0.18))
        if t >= at + 0.06:
            out.append(appear(think(ONLINE, t < at + 0.18), t, at + 0.06, 0.06))
        if t >= at + 0.18:
            out.append(appear(turn_error(), t, at + 0.18, 0.06))
    fl, k = flood1(t)
    out += fl
    sent = 0
    if t >= DEAD:
        out.append(cordis_run(t))
    if t >= COMPACT:
        out.append(appear(compaction(t), t, COMPACT))
        text, running = lines_stream(["Compaction would drop the user. Skip."], t, COMPACT + 0.08, COMPACT + 0.7)
        if text:
            out.append(appear(think(SP.latest_line(text) if running else text, running), t, COMPACT + 0.08))
    if t >= RECALL:
        out.append(appear(tool("recall", "你的全部消息", title="跨会话召回"), t, RECALL, 0.06))
        for at, said in zip(BUBBLES, YOURS):
            if t >= at:                                 # your words, read back from the cache: dimmed
                out.append(f'<div style="opacity:{0.8 * fade(t, at, 0.06):.3f}">{user(said)}</div>')
    fl2, sent = flood2(t)
    out += fl2
    return [r for r in out if r], k, sent


def running_at(t):
    return (TURN_AT <= t < STOP1) or t >= RESTART


def body(t):
    t = min(t, FREEZE)
    rs, k, sent = rows(t)
    stat, _, _ = counters(t, k, sent)
    return (f"<style>{CORDIS_CSS}{PAGE_CSS}</style>" + header(t) + f'<div id="timeline">{"".join(rs)}</div>'
            + composer(t, running_at(t)) + stat + cordis_panel(t))


STYLED = A1.STYLED


def main():
    frames = [{"n": n, "t": round(n / FPS, 4), "body": body(n / FPS), "sheets": STYLED, "measure": False}
              for n in range(round(T0 * FPS), round(T1 * FPS))]
    (HERE / "e_frames.json").write_text(json.dumps(frames, ensure_ascii=False), encoding="utf8")
    _, k, sent = rows(FREEZE)
    _, turns, steps = counters(FREEZE, k, sent)
    END.update(turns=turns, steps=steps, tok=tok(FREEZE), ctx=round(ctx(FREEZE)), cache=100, avatar_scale=1.6,
               header="插件 me · 运行中", composer="对方在线 (hers, running)", window="HOARD_ME, eaten from 144.44")
    print(len(frames), "frames,", len({f["body"] for f in frames}), "distinct")
    print("end state at 147.5:", END)


if __name__ == "__main__":
    main()
