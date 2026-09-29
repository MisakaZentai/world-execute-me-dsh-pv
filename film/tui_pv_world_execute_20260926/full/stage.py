"""Screen layouts. A shot draws its body on the standard canvas (her pane = LEFT, visualisation = CENTER,
full-width shots = FULL); the stage re-composes those regions into one of several screen modes and draws the
chrome and the lyric display that belong to that mode.

Modes:
  split      her left, visualisation right, op ticker, token lyric bar      (the v2 look)
  mirror     visualisation left, her right
  pip        visualisation centred, her in a small picture-in-picture window
  fullbleed  the body scaled edge to edge; big kinetic token lyrics on a band
  cinema     letterbox; chapter title in the top bar, subtitles with token ids in the bottom bar
  tiles      tmux: visualisation, her, htop, and a lyric log, with a tmux status line
  floating   a desktop: windows slide in, lyrics arrive as a toast
  shell      a bare terminal: every frame is stripped (neofetch look), lyrics echo at the prompt
  raw        nothing added

With TUI_ANCHOR=1 (anchored staging) the pictures keep these sizes, but she stays on the left and the lyric stays
in the bottom-left band: mirror becomes split, tmux puts her and the lyric log in the left column, the desktop's
stdout window sits under her window, and the full-bleed and cinema lyrics start at the left instead of the centre.
"""

from __future__ import annotations

import math
import random
import re

from PIL import Image, ImageDraw

import engine
from engine import (BEAT, CENTER, FULL, KEYWORDS, LEFT, LYRICS, SONG_LEN, TICK, Ctx, beat_index, header, lyric_tokens,
                    pulse, ticker)
from tuikit import (AMBER, BG, F_CJK, F_HEAD, F_MONO, F_MONO_B, RED, H, W, amb, anom, blue, box, decode, dot_field,
                    ease, font, halfblock, red, token_id, tokenize)


def background(t: float) -> Image.Image:
    off = int(t * 12) % 16
    return dot_field(W, H).crop((0, off, W, off + H))


def grab(src: Image.Image, region, scale: float = 1.0) -> Image.Image:
    im = src.crop(region)
    if abs(scale - 1.0) > 1e-3:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.LANCZOS)
    return im


def cjk(s: str) -> bool:
    return any(ord(ch) > 0x2E80 for ch in s)


# ---------------------------------------------------------------- lyric state and variants

def lyric_now(c: Ctx):
    cur = next(((a, b, s) for a, b, s in LYRICS if a <= c.t < b), None)
    if cur is None:
        return None
    a, b, s = cur
    type_dur = min(0.9, (b - a) * 0.6)
    rate = len(s) / type_dur
    typed = int(len(s) * min(1.0, (c.t - a) / type_dur))
    return a, b, s, typed, rate


def token_chips(c: Ctx, cx: float, y: float, size: int, ids: bool = True, align: str = "center",
                bg_level: tuple = (0.13, 0.22)) -> None:
    """Current lyric line as token chips (keywords inverted), centred at cx or left-aligned at cx."""
    st = lyric_now(c)
    if st is None:
        return
    a, b, s, typed, rate = st
    d = c.d
    f = font(F_HEAD, size)
    fi = font(F_MONO, max(10, size // 2))
    toks, pos = [], 0
    for tok in tokenize(s):
        start = s.find(tok, pos)
        if start < 0:
            continue
        toks.append((tok, start, start > pos))
        pos = start + len(tok)
    total = sum(d.textlength(tk_, font=f) + 6 + (8 if gap else 0) for tk_, _, gap in toks)
    x = cx - total / 2 if align == "center" else cx
    h = int(size * 1.35)
    for k, (tok, start, gap) in enumerate(toks):
        if start >= typed:
            break
        if gap:
            x += 8
        shown = tok[: typed - start]
        age = (c.t - a) - start / rate
        txt = decode(shown, age, c.rng, rate, 0.1, c.corrupt)
        tw = d.textlength(tok, font=f)
        ws = s.rfind(" ", 0, start) + 1
        we = s.find(" ", start)
        we = len(s) if we < 0 else we
        key = re.sub(r"[^a-z-]", "", s[ws:we].lower())
        hot = key in KEYWORDS and typed >= we
        if hot:
            bgc = red(0.95) if "exec" in key or key in ("illegal", "arguments") else \
                blue(0.95) if key in ("love", "lo-o-ove") else amb(0.95)
            d.rectangle([x - 3, y + 2, x + tw + 3, y + h], fill=bgc)
            d.text((x, y), txt, font=f, fill=BG)
        else:
            d.rectangle([x - 3, y + 2, x + tw + 3, y + h], fill=amb(bg_level[k % 2]))
            d.text((x, y), txt, font=f, fill=amb(0.95))
        if ids and typed >= start + len(tok):
            tid = str(token_id(tok))
            d.text((x + (tw - d.textlength(tid, font=fi)) / 2, y + h + 2), tid, font=fi, fill=amb(0.45))
        x += tw + 6
    if typed < len(s) or int(c.t * 3) % 2 == 0:
        d.rectangle([x + 2, y + 4, x + 2 + size // 2, y + h - 2], fill=amb(0.9))


def lyric_log(c: Ctx, rect) -> None:
    """Lyrics as a log: past lines stay, the current one types in."""
    x0, y0, x1, y1 = rect
    f = font(F_MONO, 15)
    lines = [(a, s) for a, b, s in LYRICS if a <= c.t][-5:]
    for i, (a, s) in enumerate(lines):
        mm, ss = divmod(a, 60)
        cur = i == len(lines) - 1
        st = lyric_now(c)
        txt = s
        if cur and st and st[0] == a:
            txt = decode(s[: st[3]], (c.t - a), c.rng, st[4], 0.1, c.corrupt)
        y = y0 + 8 + i * 22
        c.text((x0 + 10, y), f"[{int(mm):02d}:{ss:05.2f}]", f, amb(0.45))
        c.d.text((x0 + 120, y), txt, font=font(F_CJK if cjk(txt) else F_MONO_B, 15), fill=amb(0.95 if cur else 0.5))


def lyric_inline(c: Ctx) -> None:
    """Shell: the previous line is output, the current one is being echoed at the prompt."""
    d = c.d
    f = font(F_MONO_B, 20)
    lines = [(a, s) for a, b, s in LYRICS if a <= c.t][-2:]
    st = lyric_now(c)
    y = 642
    if len(lines) == 2:
        d.text((40, y - 26), lines[0][1], font=f, fill=amb(0.4))
    prompt = "me@deepsea:~$ echo "
    d.text((40, y), prompt, font=f, fill=blue(0.9))
    x = 40 + d.textlength(prompt, font=f)
    if st:
        a, b, s, typed, rate = st
        txt = '"' + decode(s[:typed], c.t - a, c.rng, rate, 0.1, c.corrupt)
        d.text((x, y), txt, font=f, fill=amb(0.95))
        x += d.textlength(txt, font=f)
    if int(c.t * 3) % 2 == 0:
        d.rectangle([x + 2, y + 2, x + 13, y + 24], fill=amb(0.9))


# ---------------------------------------------------------------- generated panes

def _gpu_bars(c: Ctx, x0, y, rh, f) -> float:
    d = c.d
    for g in range(8):
        util = 0.55 + 0.4 * abs(math.sin(c.t * (1.3 + g * 0.21) + g))
        yy = y + g * rh
        n = int(22 * util)
        d.text((x0 + 10, yy), f"{g}[", font=f, fill=amb(0.7))
        d.text((x0 + 30, yy), "|" * n, font=f, fill=anom(0.9) if util > 0.9 else amb(0.85))
        d.text((x0 + 30 + 22 * 7.2, yy), f"{int(util * 100):3d}%]", font=f, fill=amb(0.7))
    return y + 8 * rh


def _procs(c: Ctx, x0, y, x1, n, f) -> None:
    d = c.d
    d.text((x0 + 10, y), "  PID USER  %GPU  COMMAND", font=f, fill=BG)
    d.rectangle([x0 + 8, y - 1, x1 - 8, y + 15], fill=amb(0.8))
    d.text((x0 + 10, y), "  PID USER  %GPU  COMMAND", font=f, fill=BG)
    ops = c.ops or ["idle"]
    cur = int(c.t / (BEAT / 2)) % len(ops)
    for i, op in enumerate(ops[:n]):
        yy = y + 18 + i * 16
        hot = i == cur % min(n, len(ops))
        d.text((x0 + 10, yy), f"{4471 + i:5d} me    {90 - i * 7:4d}  {op.lower()}", font=f,
               fill=blue(0.95) if hot else amb(0.6))


def htop(c: Ctx, rect) -> None:
    x0, y0, x1, y1 = rect
    f = font(F_MONO, 13)
    y = _gpu_bars(c, x0, y0 + 10, 17, f) + 6
    c.d.text((x0 + 10, y), "Mem[" + "|" * 20 + f" 71.3G/80G]", font=f, fill=amb(0.75))
    _procs(c, x0, y + 24, x1, 7, f)


def htop_wide(c: Ctx, rect) -> None:
    """The same htop laid out for a short, wide pane: GPU bars and memory left, the process table right."""
    x0, y0, x1, y1 = rect
    f = font(F_MONO, 12)
    y = _gpu_bars(c, x0, y0 + 5, 13, f)
    c.d.text((x0 + 10, y + 1), "Mem[" + "|" * 20 + f" 71.3G/80G]", font=f, fill=amb(0.75))
    _procs(c, x0 + 330, y0 + 8, x1, 6, f)


def window(d: ImageDraw.ImageDraw, x0, y0, x1, y1, title: str, active: bool = True) -> None:
    d.rectangle([x0 + 8, y0 + 8, x1 + 8, y1 + 8], fill=(0, 0, 0))
    d.rectangle([x0, y0 - 24, x1, y0], fill=amb(0.85 if active else 0.35))
    for i in range(3):
        d.ellipse([x0 + 8 + i * 16, y0 - 17, x0 + 18 + i * 16, y0 - 7], fill=BG)
    d.text((x0 + 64, y0 - 21), title, font=font(F_MONO_B, 14), fill=BG)
    d.rectangle([x0, y0 - 24, x1, y1], outline=amb(0.85 if active else 0.35))


# ---------------------------------------------------------------- geometry

FULL_W = FULL[2] - FULL[0]


def _through(region, ox, oy, s):
    x0, y0, x1, y1 = region
    return (ox + (x0 - FULL[0]) * s, oy + (y0 - FULL[1]) * s, ox + (x1 - FULL[0]) * s, oy + (y1 - FULL[1]) * s)


def _scaled(ox, oy, s, kind):
    if kind == "split":
        return [dict(id="viz", src=CENTER, dst=_through(CENTER, ox, oy, s), frame=None, z=0),
                dict(id="me", src=LEFT, dst=_through(LEFT, ox, oy, s), frame=None, z=1)]
    return [dict(id="viz", src=FULL, dst=_through(FULL, ox, oy, s), frame=None, z=0)]


def geometry(mode: str, kind: str, extra: dict) -> list[dict]:
    """Where each part of the shot's canvas goes on screen. src None = generated (pip portrait)."""
    if identity(mode, kind):
        return _scaled(FULL[0], FULL[1], 1.0, kind)
    if mode == "mirror":
        return [dict(id="viz", src=CENTER, dst=(24, 56, 784, 604), frame=None, z=0),
                dict(id="me", src=LEFT, dst=(804, 56, 1164, 604), frame=None, z=1)]
    if mode == "pip":
        if kind == "split":
            return [dict(id="viz", src=CENTER, dst=(236, 56, 996, 604), frame=None, z=0),
                    dict(id="me", src=LEFT, dst=(24, 293, 222, 594), frame="/dev/me", z=1)]
        return [dict(id="viz", src=FULL, dst=FULL, frame=None, z=0),
                dict(id="me", src=None, dst=(990, 354, 1140, 584), frame="/dev/me", z=1,
                     expr=extra.get("expr", "shy"))]
    if mode == "fullbleed":
        return _scaled(0, 30, W / FULL_W, kind)
    if mode == "cinema":
        s = 0.84
        return _scaled((W - FULL_W * s) / 2, 128, s, kind)
    if mode == "tiles":
        if engine.ANCHOR:
            return [dict(id="viz", src=CENTER, dst=(516, 4, 1276, 552), frame=None, z=0),
                    dict(id="me", src=LEFT, dst=(74, 4, 434, 552), frame=None, z=1)]
        return [dict(id="viz", src=CENTER, dst=(4, 4, 764, 552), frame=None, z=0),
                dict(id="me", src=LEFT, dst=(907, 10, 1145, 372), frame=None, z=1)]
    if mode == "floating":
        if kind == "split":
            return [dict(id="me", src=LEFT, dst=(70, 190, 336, 595), frame="me  /dev/me", z=0),
                    dict(id="viz", src=CENTER, dst=(570, 150, 1208, 610), frame="viz", z=1)]
        return [dict(id="viz", src=FULL, dst=(100, 150, 1058, 610), frame="viz", z=0)]
    return _scaled(FULL[0], FULL[1], 1.0, kind)


def identity(mode: str, kind: str) -> bool:
    return mode in ("split", "shell", "raw") or (mode in ("mirror", "tiles") and kind != "split")


def to_screen(rect, els: list[dict]):
    """Map a canvas rect through whichever element contains its centre."""
    cx, cy = (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2
    for el in sorted(els, key=lambda e: -e["z"]):
        src = el["src"]
        if src and src[0] <= cx <= src[2] and src[1] <= cy <= src[3]:
            sx = (el["dst"][2] - el["dst"][0]) / (src[2] - src[0])
            sy = (el["dst"][3] - el["dst"][1]) / (src[3] - src[1])
            return (el["dst"][0] + (rect[0] - src[0]) * sx, el["dst"][1] + (rect[1] - src[1]) * sy,
                    el["dst"][0] + (rect[2] - src[0]) * sx, el["dst"][1] + (rect[3] - src[1]) * sy)
    return rect


def el_image(canvas: Image.Image, el: dict, size=None) -> Image.Image:
    if el["src"] is None:
        im = halfblock(el.get("expr", "shy"), "full", 150, 230, 3)
        bgc = Image.new("RGB", im.size, BG)
        bgc.paste(im, (0, 0), im)
        im = bgc
    else:
        im = canvas.crop(tuple(int(v) for v in el["src"]))
    if size and (int(size[0]) != im.width or int(size[1]) != im.height):
        im = im.resize((max(1, int(size[0])), max(1, int(size[1]))), Image.LANCZOS)
    return im


def mode_background(mode: str, t: float) -> Image.Image:
    return Image.new("RGB", (W, H), (0, 0, 0)) if mode == "cinema" else background(t)


def draw_panes(out: Image.Image, canvas: Image.Image, els: list[dict]) -> None:
    d = ImageDraw.Draw(out)
    for el in sorted(els, key=lambda e: e["z"]):
        x0, y0, x1, y1 = (int(v) for v in el["dst"])
        if el["frame"]:
            window(d, x0, y0, x1, y1, el["frame"])
        out.paste(el_image(canvas, el, (x1 - x0, y1 - y0)), (x0, y0))


# ---------------------------------------------------------------- chrome

def chrome(c: Ctx, mode: str, kind: str, extra: dict) -> None:
    """Everything that is not the shot body. Draws on c.d, which may be a transparent overlay."""
    t = c.t
    d = c.d
    if mode == "raw":
        return
    if mode == "shell":
        cmd = extra.get("cmd") or (c.ops[0].lower() if c.ops else "")
        d.text((24, 12), f"me@deepsea:~$ {cmd}", font=font(F_MONO_B, 18), fill=blue(0.95))
        d.text((W - 190, 14), f"{int(t // 60):02d}:{t % 60:04.1f} / 03:32", font=font(F_MONO, 14), fill=amb(0.5))
        lyric_inline(c)
    elif mode in ("split", "mirror", "pip") or (mode == "tiles" and kind != "split"):
        header(c)
        ticker(c)
        lyric_tokens(c)
    elif mode == "fullbleed":
        d.rectangle([0, 0, W, 29], fill=BG)
        d.text((16, 7), f"{c.chapter}", font=font(F_HEAD, 13), fill=amb(0.8))
        d.text((W - 160, 7), f"{int(t // 60):02d}:{t % 60:04.1f} / 03:32", font=font(F_MONO, 13), fill=amb(0.55))
        d.rectangle([0, 648, W, H], fill=BG)
        d.line([0, 648, W, 648], fill=amb(0.4 + 0.4 * pulse(t)))
        if engine.ANCHOR:
            token_chips(c, 74, 656, 30, ids=True, align="left")
        else:
            token_chips(c, W / 2, 656, 30, ids=True)
    elif mode == "cinema":
        title = " ".join(c.chapter.replace(" ", ""))
        tf = font(F_HEAD, 20)
        d.text(((W - d.textlength(title, font=tf)) / 2, 52), title, font=tf, fill=amb(0.85))
        d.text((W - 200, 100), f"{int(t // 60):02d}:{t % 60:04.1f}", font=font(F_MONO, 13), fill=amb(0.4))
        if engine.ANCHOR:
            token_chips(c, (W - FULL_W * 0.84) / 2 + 14, 612, 24, ids=True, align="left", bg_level=(0.0, 0.0))
        else:
            token_chips(c, W / 2, 612, 24, ids=True, bg_level=(0.0, 0.0))
    elif mode == "tiles":
        panes = [(0, 0, 768, 556), (772, 0, W, 380), (772, 384, W, 690), (0, 560, 768, 690)]
        if engine.ANCHOR:
            # her column on the left with the lyric log under her; visualisation and htop on the right
            panes = [(512, 0, W, 556), (0, 0, 508, 556), (512, 560, W, 690), (0, 560, 508, 690)]
        active = beat_index(t) % 4
        for i, (x0, y0, x1, y1) in enumerate(panes):
            d.rectangle([x0, y0, x1 - 1, y1 - 1], outline=anom(0.9) if i == active else amb(0.35))
        (htop_wide if engine.ANCHOR else htop)(c, panes[2])
        lyric_log(c, panes[3])
        d.rectangle([0, 692, W, H], fill=amb(0.85))
        fb = font(F_MONO_B, 15)
        d.text((8, 697), f"[deepsea] 0:viz  1:me  2:htop  3:lyrics*   {c.chapter}", font=fb, fill=BG)
        clock = f"{int(t // 60):02d}:{t % 60:04.1f}  26-Sep-26"
        d.text((W - 8 - d.textlength(clock, font=fb), 697), clock, font=fb, fill=BG)
    elif mode == "floating":
        d.rectangle([0, 0, W, 26], fill=amb(0.85))
        d.text((10, 4), f"deepsea OS   {c.chapter}", font=font(F_MONO_B, 15), fill=BG)
        d.text((W - 150, 4), f"{int(t // 60):02d}:{t % 60:04.1f}", font=font(F_MONO_B, 15), fill=BG)
        st = lyric_now(c)
        if st:
            tx0, ty0, tx1, ty1 = (60, 622, 740, 680) if engine.ANCHOR else (570, 60, 1250, 118)
            d.rectangle([tx0 + 6, ty0 + 6, tx1 + 6, ty1 + 6], fill=(0, 0, 0))
            d.rectangle([tx0, ty0, tx1, ty1], fill=BG, outline=amb(0.9))
            d.text((tx0 + 12, ty0 + 4), "stdout", font=font(F_MONO, 12), fill=amb(0.5))
            token_chips(c, tx0 + 14, ty0 + 20, 20, ids=False, align="left")


def compose(c: Ctx, mode: str, kind: str, extra: dict) -> Image.Image:
    canvas = c.img
    if mode == "raw" or c.no_chrome:
        return canvas
    if identity(mode, kind):
        out = canvas
    else:
        out = mode_background(mode, c.t)
        draw_panes(out, canvas, geometry(mode, kind, extra))
    c.img, c.d = out, ImageDraw.Draw(out)
    chrome(c, mode, kind, extra)
    return out


def chrome_overlay(c: Ctx, mode: str, kind: str, extra: dict) -> Image.Image:
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if not c.no_chrome:
        c.img, c.d = ov, ImageDraw.Draw(ov)
        chrome(c, mode, kind, extra)
    return ov


# ---------------------------------------------------------------- glide: the layout itself moves

def _lerp_rect(a, b, e):
    return tuple(a[i] + (b[i] - a[i]) * e for i in range(4))


def _collapse(r, e):
    cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
    return (r[0] + (cx - r[0]) * e, r[1] + (cy - r[1]) * e, r[2] - (r[2] - cx) * e, r[3] - (r[3] - cy) * e)


def glide(A: dict, B: dict, p: float, rng) -> Image.Image:
    """Morph from A's screen to B's: panes slide and resize to their new places, their content re-forms
    (glyph dissolve for her, particle reflow for the visualisation), chrome cross-fades.
    A and B: dict(ctx, canvas, mode, kind, extra)."""
    import transitions as TR
    e = ease_io(p)
    ga = {el["id"]: el for el in geometry(A["mode"], A["kind"], A["extra"])}
    gb = {el["id"]: el for el in geometry(B["mode"], B["kind"], B["extra"])}
    bga, bgb = mode_background(A["mode"], A["ctx"].t), mode_background(B["mode"], B["ctx"].t)
    out = Image.blend(bga, bgb, e)
    d = ImageDraw.Draw(out)
    order = sorted(set(ga) | set(gb), key=lambda i: (gb.get(i) or ga.get(i))["z"])
    q = max(0.0, min(1.0, (p - 0.15) / 0.7))
    for i in order:
        a, b = ga.get(i), gb.get(i)
        if a and b:
            r = _lerp_rect(a["dst"], b["dst"], e)
        elif a:
            r = _collapse(a["dst"], e)
        else:
            r = _collapse(b["dst"], 1 - e)
        x0, y0, x1, y1 = (int(v) for v in r)
        w, h = x1 - x0, y1 - y0
        if w < 4 or h < 4:
            continue
        fa = bool(a and a["frame"])
        fb = bool(b and b["frame"])
        if fa or fb:
            k = 1.0 if (fa and fb) else (1 - e) if fa else e
            title = b["frame"] if (fb and e > 0.5) or not fa else a["frame"]
            if k > 0.02:
                layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                window(ImageDraw.Draw(layer), x0, y0, x1, y1, title)
                out.paste(layer.convert("RGB"), (0, 0), _fade(layer, k).getchannel("A"))
        if a and b:
            ia = el_image(A["canvas"], a, (w, h))
            ib = el_image(B["canvas"], b, (w, h))
            im = TR.pane_dissolve(ia, ib, q, rng) if i == "me" else TR.reflow(ia, ib, q, rng, n=900)
        elif a:
            im = Image.blend(Image.new("RGB", (w, h), BG), el_image(A["canvas"], a, (w, h)), 1 - e)
        else:
            im = Image.blend(Image.new("RGB", (w, h), BG), el_image(B["canvas"], b, (w, h)), e)
        out.paste(im, (x0, y0))
    ova = chrome_overlay(A["ctx"], A["mode"], A["kind"], A["extra"])
    ovb = chrome_overlay(B["ctx"], B["mode"], B["kind"], B["extra"])
    out = out.convert("RGBA")
    out.alpha_composite(_fade(ova, 1 - e))
    out.alpha_composite(_fade(ovb, e))
    return out.convert("RGB")


def _fade(ov: Image.Image, k: float) -> Image.Image:
    if k >= 0.999:
        return ov
    o = ov.copy()
    o.putalpha(ov.getchannel("A").point(lambda a: int(a * max(0.0, k))))
    return o


def ease_io(p: float) -> float:
    p = max(0.0, min(1.0, p))
    return 4 * p ** 3 if p < 0.5 else 1 - (-2 * p + 2) ** 3 / 2
