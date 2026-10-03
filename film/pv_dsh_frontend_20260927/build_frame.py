"""Build one static dsh frame as a standalone HTML page from dsh's own stylesheets, class names and icons.

Usage: python build_frame.py            -> frame_108_9_f14.html, frame_108_9_f16.html
Nothing here talks to a dsh server: the page is plain HTML + dsh CSS, screenshotted by shot.mjs.
"""
import html
import json
from pathlib import Path

from icons import svg

HERE = Path(__file__).parent
ASSETS = "../vendor/dsh-web-frontend/dist/assets"
D = json.loads((HERE / "disclosure_map.json").read_text())


def esc(s):
    return html.escape(s, quote=False)


def think(summary, running=False):
    state = "running" if running else "ok"
    return f"""
<div class="lcKema_root" data-variant="think" data-state="{state}">
 <div class="{D['root']}">
  <div class="{D['row']} lcKema_row" data-disclosure-row="true" data-expandable="true" role="button">
   <span class="{D['leading']} lcKema_leading"><span class="{D['iconIdle']}">{svg('IconThinkOutline14', 14)}</span>{svg('IconChevronDownOutline14', 14, 'lcKema_chevron ' + D['chevronHover'])}</span>
   <span class="{D['title']} lcKema_title">思考</span>
   <span class="lcKema_separator" aria-hidden="true"></span>
   <span class="lcKema_summary"{' data-follow-end="true"' if running else ''}><span class="lcKema_summaryText">{esc(summary)}</span></span>
  </div>
 </div>
</div>"""


def pwsh(desc, state="ok"):
    summary_cls = "CY-8Ka_summary CY-8Ka_errorSummary" if state == "error" else "CY-8Ka_summary"
    return f"""
<div class="CY-8Ka_card">
 <div class="CY-8Ka_root" data-state="{state}">
  <span class="CY-8Ka_leading"><span class="CY-8Ka_iconIdle">{svg('IconApiOutline14', 14)}</span></span>
  <span class="CY-8Ka_title">Pwsh</span><span class="CY-8Ka_sep" aria-hidden="true"></span>
  <span class="{summary_cls}">{esc(desc)}</span>
 </div>
</div>"""


def tool(tool_name, summary, title="工具调用", state="ok"):
    return f"""
<div class="o3BgMG_root" data-variant="others" data-tool="{tool_name}" data-state="{state}">
 <div class="{D['root']}">
  <div class="{D['row']} o3BgMG_row" data-disclosure-row="true" data-expandable="true" role="button">
   <span class="{D['leading']} o3BgMG_leading"><span class="{D['iconIdle']}">{svg('IconSparkle16', 14)}</span></span>
   <span class="{D['title']} o3BgMG_title">{esc(title)}</span>
   <span class="o3BgMG_sep" aria-hidden="true"></span><span class="o3BgMG_summary">{esc(summary)}</span>
  </div>
 </div>
</div>"""


def user(text, forged=False):
    extra = ' style="color:var(--pv-her)"' if forged else ""
    return f"""
<div class="Sixlwa_userRow"><div class="Sixlwa_userStack"><div class="Sixlwa_bubble"{extra}>{esc(text)}</div></div></div>"""


def her(text):
    return f"""
<div class="hWmORq_root"><div class="hWmORq_body"><p style="margin:0">{esc(text).replace(chr(10), "<br>")}</p></div></div>"""


def tail(duration, clock, rating=None, pulse=0.0):
    """rating: None, "positive" or "negative" (the filled icon, as dsh's feedback actions draw it). pulse 0..1 brightens
    the pressed icon for the PV so a click reads at a glance."""
    icon = lambda n, style="": f'<button type="button" class="xzv4MW_action"{style}>{svg(n, 16)}</button>'
    hot = f' style="color:rgba(125,150,255,{0.55 + 0.45 * pulse:.2f})"'
    like = icon('IconLikeFill16', hot) if rating == "positive" else icon('IconLikeOutline16')
    dislike = icon('IconDislikeFill16', hot) if rating == "negative" else icon('IconDislikeOutline16')
    return f"""
<div class="TS9iAW_root" data-actions-reveal="always">
 <div class="xzv4MW_actions TS9iAW_actions">
  {icon('IconCopyOutline16')}{like}{dislike}{icon('IconBranchOutline16')}
  <span class="Q51KRG_root"><button type="button" class="Q51KRG_trigger">{svg('IconClockOutline16', 16)}<span class="Q51KRG_label">用时 {esc(duration)}</span></button></span>
  <span class="xzv4MW_timeEnd">{esc(clock)}</span>
 </div>
</div>"""


def composer(model="DeepSeek-V4.1-Flash", effort="Max"):
    return f"""
<div class="uV2eYG_root" id="composer">
 <div class="uV2eYG_card">
  <div class="uV2eYG_scroll"><div class="uV2eYG_grow">
   <div class="uV2eYG_input"></div>
   <div class="uV2eYG_placeholder">发消息或创建任务，/ 调用指令，@ 文件或对话</div>
  </div></div>
  <div class="uV2eYG_row">
   <div class="uV2eYG_modes" style="display:flex;align-items:center">
    <button type="button" class="uV2eYG_add">{svg('IconPlusOutline16', 16)}</button>
    <button type="button" class="uV2eYG_add">{svg('IconPaperclipOutline16', 16)}</button>
   </div>
   <div class="uV2eYG_trailing">
    <span class="uV2eYG_select" style="background-image:none;display:inline-flex;align-items:center;padding:0">{esc(model)}&nbsp;<span style="color:var(--dsw-alias-label-tertiary)">{esc(effort)}</span></span>
    <button type="button" class="uV2eYG_primary">{svg('IconSendOutline14', 14)}</button>
   </div>
  </div>
 </div>
</div>"""


def stats(turns, steps, tps, tokens, cache):
    """tps=None drops the speed part, which is what fits the narrow pane at 16px."""
    pill = lambda icon, *parts: (f'<span class="bOPqQW_anchor"><span class="bOPqQW_pill">{svg(icon, 16)}'
                                 f'<span class="bOPqQW_label">{parts[0]}' +
                                 (f'<span class="bOPqQW_sep" aria-hidden="true">·</span>{parts[1]}' if parts[1] else '') +
                                 '</span></span></span>')
    return f"""
<div class="bOPqQW_root" data-composer-stats="true">
 {pill('IconGaugeOutline16', f'{turns} 轮 {steps} 步', f'{tps} tok/s' if tps else '')}
 {pill('IconDatabaseOutline16', f'{tokens} tok', f'缓存命中 {cache}%')}
</div>"""


def header(name, state, bust):
    return f"""
<div class="pv-head">
 <div class="pv-pet"><img src="{bust}"></div>
 <div class="pv-who"><div class="pv-name">{esc(name)}</div><div class="pv-state"><span class="pv-dot"></span>{esc(state)}</div></div>
</div>"""


PAGE = """<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="{assets}/vendor-BNsW4eBh.css">
<link rel="stylesheet" href="{assets}/index-DPX2bQLO.css">
<link rel="stylesheet" href="dsh_components.css">
<style>
 html,body{{margin:0;height:100%;background:var(--dsw-alias-bg-base);overflow:hidden}}
 body{{font-family:var(--dsw-font-family);-webkit-font-smoothing:antialiased;--pv-her:#4d6bfe}}
 body{{{fontvars}}}
 {palette}
 #app{{position:relative;height:100%;display:flex;flex-direction:column}}
 .pv-head{{display:flex;align-items:center;gap:10px;padding:10px 12px 8px;border-bottom:.5px solid var(--dsw-alias-border-l1)}}
 .pv-pet{{width:60px;height:60px;border-radius:14px;overflow:hidden;flex:none;background:#070b18;
          border:.5px solid var(--dsw-alias-border-l2)}}
 .pv-pet img{{width:100%;height:100%;object-fit:cover}}
 .pv-name{{color:var(--dsw-alias-label-primary);font-size:14px;line-height:20px;font-weight:500}}
 .pv-state{{color:var(--dsw-alias-label-tertiary);font-size:12px;line-height:18px;display:flex;align-items:center;gap:6px}}
 .pv-dot{{width:7px;height:7px;border-radius:50%;background:#3fb950}}
 #timeline{{flex:1;display:flex;flex-direction:column;justify-content:flex-end;gap:10px;padding:10px 14px 6px;
            overflow:hidden;--dsh-chat-content-width:{width}px}}
 #composer{{--dsh-composer-side-clearance:10px;--dsh-composer-card-max-width:100%;--dsh-composer-text-max-height:80px;padding-bottom:4px}}
 .bOPqQW_root{{padding:2px 4px 8px;gap:2px}}
</style></head>
<body data-ds-dark-theme="true"><div id="app">
{head}
<div id="timeline">{rows}</div>
{composer}
{stats}
</div></body></html>"""


FONTS = {
    "f14": "",  # dsh default: 14px content, 13px secondary
    "f16": "--dsh-content-font-size:16px;--dsh-content-font-delta:2px;"
           "--dsh-content-font-size-secondary:14px;--dsh-content-font-delta-secondary:1px;",
}


# the film's deepsea palette, applied the way a dsh theme plugin overrides tokens
DEEPSEA = ("body[data-ds-dark-theme]{--dsw-alias-bg-base:#05080f;--dsw-specific-bubble:#18233d;"
           "--dsw-specific-input-major:#0d1528;--dsw-specific-selector:#1a2440;--dsw-alias-border-l1:#1b2540;"
           "--dsw-alias-border-l2:#223052}")


def page(rows, font, width, head, stat, palette=""):
    return PAGE.format(assets=ASSETS, fontvars=FONTS[font], palette=palette, width=width, head=head,
                       rows="".join(rows), composer=composer(), stats=stat)


FRAME_108_9 = [
    user("今天也谢谢你。"),
    her("不客气～明天也要来找我哦 (｡･ω･｡)"),
    tail("3.4秒", "23:57"),
    user("你会一直在吗？"),
    think("The user is asking whether I will stay. Answer honestly."),
    her("我一直在。"),
    tail("2.1秒", "23:59"),
]

if __name__ == "__main__":
    W, H = 356, 539
    for font, pal in [("f14", ""), ("f16", ""), ("f16", "deepsea")]:
        doc = page(FRAME_108_9, font, W, header("溟月", "在线 · DeepSeek-V41-Flash", "her_bust_108.png"),
                   stats(3, 7, 233 if font == "f14" else None, "131K", 99), DEEPSEA if pal else "")
        out = HERE / f"frame_108_9_{font}{'_' + pal if pal else ''}.html"
        out.write_text(doc, encoding="utf8")
        print(out.name)
