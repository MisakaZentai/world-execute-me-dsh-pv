"""The film's dsh window, as text.

The left half of the film is a real dsh chat page rendered by Playwright: `pv_dsh_frontend_20260927`
holds one rendered PNG per frame in `dsh_frames/` (4968 of them, 354x537, 146 MB) *and* the per-frame
DOM that produced them - `a1_frames.json` .. `g_frames.json` and `seg_frames.json`, one entry per
frame, each with a `body` that IS the page's inner HTML for that frame (empty means "unchanged").

A terminal cannot show the PNGs (354 px into ~45 cells is a smear), but it can show the text they
contain. This module reads those bodies once and writes a compressed cache of what is on screen:

    the header        the avatar (a per-frame PNG path), `大肥鱼`, and the state line
    the timeline      user bubbles, her replies, the thinking/tool cards, the elapsed-time rows
    the composer      the placeholder, the model
    the footer pills  `4 轮 9 步 · 132K tok · 缓存命中 99%`
    the source scene  at 113-115 s the page prints its own HTML into `pre#src` and deletes it again

Everything is the film's own text, whole: the whole dialogue is here (`你好` -> `你是谁？` ->
`你会一直在吗？` -> the `我在。我在。` wall -> `服务结束` / `DeepSeek-V4.1-Flash 已下线。`).

    python _tools/dsh_text.py            build the cache if it is missing or stale
    python _tools/dsh_text.py --force    rebuild it
    python _tools/dsh_text.py --at 112   print what the window holds at t=112 s
"""
from __future__ import annotations

import gzip
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DSH = ROOT / "film" / "pv_dsh_frontend_20260927"
CACHE = DSH / "dsh_text.json.gz"
SOURCES = ("a1_frames.json", "a2_frames.json", "a3_frames.json", "b_frames.json", "c_frames.json",
           "e_frames.json", "f_frames.json", "g_frames.json", "seg_frames.json")
FPS = 24

# role rules, first match wins. The class names are the page's own (dsh_components.css hashed them,
# but the prefixes are stable across every group the film rendered).
RULES = (
    ("name", ("pv-name",)),
    ("state", ("pv-state",)),
    ("user", ("Sixlwa_bubble",)),
    ("card", ("lcKema_title", "o3BgMG_title", "_title_luwio", "Sixlwa_compactionButton")),
    ("sub", ("summaryText", "o3BgMG_summary", "Sixlwa_compactionContextIcon")),
    ("err", ("o3BgMG_errorSummary", "Sixlwa_turnErrorMessage", "Sixlwa_maxTokensTitle")),
    ("meta", ("Q51KRG_label", "xzv4MW_timeEnd", "Sixlwa_timeEnd")),
    ("pill", ("bOPqQW_label", "bOPqQW_sep")),
    ("model", ("uV2eYG_select", "uV2eYG_model")),
    ("composer", ("uV2eYG_placeholder",)),
    ("ai", ("hWmORq_body", "hWmORq_root")),
)
DROP = ("pv-dot", "Sixlwa_compactionLeading", "bOPqQW_anchor", "bOPqQW_pill", "Q51KRG_root",
        "Q51KRG_trigger", "_chevronHover", "lcKema_leading", "lcKema_chevron", "o3BgMG_leading")

KILL = re.compile(r"<(style|script|svg)\b.*?</\1>", re.S | re.I)
PRESRC = re.compile(r'<pre[^>]*id="src"[^>]*>(.*?)</pre>', re.S | re.I)
TOK = re.compile(r"<(/?)([a-zA-Z0-9]+)([^>]*)>", re.S)
CLS = re.compile(r'class="([^"]*)"')
IMGSRC = re.compile(r'src="(avatars/[^"]+)"')
CSSVAR = re.compile(r"--dsw-alias-([a-z0-9-]+):\s*(#[0-9a-fA-F]{3,8})")
# The state dot carries the film's own status colour: 预训练中/内测中/等待中 are #d29922 (amber),
# 微调中 #4d6bfe, 强化学习中 #a371f7, 在线 #3fb950, 已归档 #6e7681, 执行中 #ff3b30, 训练崩溃 #f85149.
# Reading it means the terminal colours the state line the way the page does instead of guessing.
DOT = re.compile(r'pv-dot"[^>]*background:\s*(#[0-9a-fA-F]{3,8})')
VOID = {"img", "br", "input", "path", "circle", "rect", "use", "hr", "meta", "link", "source"}


def theme_of(body: str) -> tuple:
    """`(bg, brand, border)` - the page is re-themed per chapter by a `<style>` block (the pink
    C group, the red EXECUTION group), and the terminal can follow that."""
    seen = dict(CSSVAR.findall(body))
    return (seen.get("bg-base", ""), seen.get("brand-primary", ""), seen.get("border-l1", ""))


def _role(cls: str, tag: str) -> str | None:
    for name, keys in RULES:
        if any(k in cls for k in keys):
            return name
    if tag == "p":
        return "ai"                     # her replies are bare <p> in the timeline
    return None


def _role_of(stack: list, tag: str) -> str | None:
    """The nearest ancestor the rules know, not just the innermost element.

    `pv-state` holds its text inside a nested `<span style="...">`, and the reply body is a bare
    `<p>` with no class at all - so the class of the text node itself is not the answer.
    """
    for _t, _a, cls in reversed(stack):
        if cls:
            r = _role(cls, "")
            if r:
                return r
    return _role("", tag)


def parse(body: str) -> list:
    """[(role, text)] in document order, plus ('code', line) for the page's own source."""
    out = []
    m = PRESRC.search(body)
    if m:
        for line in html.unescape(m.group(1)).splitlines():
            line = line.rstrip()
            if line.strip():
                out.append(("code", line))
        body = body[:m.start()] + body[m.end():]
    body = KILL.sub("", body)
    stack, pos = [], 0
    for m in TOK.finditer(body):
        txt = html.unescape(body[pos:m.start()])
        pos = m.end()
        if txt.strip():
            tag = stack[-1][0] if stack else "?"
            role = _role_of(stack, tag)
            if role:
                # the page sometimes *displays* markup (it prints its own source), and that arrives
                # here unescaped - keep the text, drop the tags
                t2 = re.sub(r"</?[a-zA-Z][^<>]{0,60}>", "", txt)
                out.append((role, re.sub(r"\s+", " ", t2).strip()))
        closing, tag, attrs = m.group(1) == "/", m.group(2).lower(), m.group(3)
        if tag in VOID:
            continue
        if closing:
            for i in range(len(stack) - 1, -1, -1):
                if stack[i][0] == tag:
                    del stack[i:]
                    break
        else:
            c = CLS.search(attrs)
            stack.append((tag, attrs, c.group(1) if c else ""))
    return out


def frames() -> list:
    """Every frame the film rendered, in order, with the body carried forward."""
    raw = []
    for name in SOURCES:
        p = DSH / name
        if p.exists():
            raw += json.loads(p.read_text(encoding="utf8"))
    raw.sort(key=lambda e: e["n"])
    out, carry = [], ""
    for e in raw:
        b = e.get("body") or carry
        carry = b
        out.append((e["n"], b))
    return out


def build(force: bool = False) -> dict:
    if CACHE.exists() and not force and CACHE.stat().st_mtime >= max(
            (DSH / n).stat().st_mtime for n in SOURCES if (DSH / n).exists()):
        return load()
    changes, last = [], None
    for n, body in frames():
        av = IMGSRC.search(body)
        ent = parse(body)
        dm = DOT.search(body)
        if dm:
            ent.insert(0, ("dot", dm.group(1)))
        sig = (av.group(1) if av else "", theme_of(body), ent)
        if sig != last:
            changes.append([n, sig[0], list(sig[1]), ent])
            last = sig
    data = dict(n0=changes[0][0] if changes else 0, changes=changes)
    CACHE.write_bytes(gzip.compress(json.dumps(data, ensure_ascii=False).encode("utf8"), 6))
    return data


_CACHE: list = [None]


def load() -> dict:
    if _CACHE[0] is None:
        if not CACHE.exists():
            build()
        _CACHE[0] = json.loads(gzip.decompress(CACHE.read_bytes()).decode("utf8"))
    return _CACHE[0]


def at(t: float) -> tuple:
    """`(avatar, theme, [(role, text)])` for the frame at t - the film's own window content."""
    d = load()
    n = round(t * FPS)
    best = None
    for ch in d["changes"]:
        if ch[0] <= n:
            best = ch
        else:
            break
    if best is None:
        best = d["changes"][0]
    return best[1], tuple(best[2]), [tuple(x) for x in best[3]]


def main() -> None:
    if "--at" in sys.argv:
        t = float(sys.argv[sys.argv.index("--at") + 1])
        av, theme, ent = at(t)
        print(f"t={t}  avatar={av or '(none)'}  theme={theme}")
        for role, txt in ent:
            print(f"  {role:9s} {txt[:110]}")
        return
    d = build(force="--force" in sys.argv)
    size = CACHE.stat().st_size
    themes = sorted({tuple(c[2]) for c in d["changes"] if any(c[2])})
    print(f"{len(d['changes'])} change frames over {d['changes'][0][0]}..{d['changes'][-1][0]}"
          f"  ->  {CACHE.name} {size / 1024:.0f} KB")
    for th in themes:
        print("   theme", th)


if __name__ == "__main__":
    main()
