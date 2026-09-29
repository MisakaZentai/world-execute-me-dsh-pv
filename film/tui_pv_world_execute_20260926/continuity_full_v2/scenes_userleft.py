"""In-memory v2 versions of the 05 USER_LEFT scenes (103.1 - 119.7 s), and her small renderer.

The drawings are the originals from full/sec_chorus2.py, with these changes:
- feel_you, completion and the five you_left steps stay in the split pane: the section starts with the whole
  interface, and from "Though you have left" each line takes exactly one layer away (s_userleft.RETRACT). Nothing
  is ever added back: no tmux tiles, no floating windows, no second split.
- Everything that belongs to a thread is drawn by time, not by shot: the ping rows (one "Request timed out." on
  every "you have left"), the 'you' tile (from the indexer into the completion, then the ping target), the busy
  reply, the 'last seen' counter. So the five you_left shots are one continuous picture.
- isolation is the network seen from outside her terminal (the camera and the node screen are staged by the cuts);
  memory_ls keeps the retracted shell look and runs on its own clock (the listing starts inside the node).
- HOOK lets the cuts take objects over (the spiral letters, the you tiles, the finish_reason line, ...).
"""
from __future__ import annotations

import math
import random
from functools import lru_cache

from PIL import Image, ImageDraw

import choreo
import dancer
import facts as F
import rig
import sec_chorus2 as S2
from engine import FPS, beat_t
from motion import Motion
from tuikit import (ANOM, BG, BLUE_HI, F_CJK, F_HEAD, F_MONO, F_MONO_B, amb, anom, blue, box, font, mix,
                    scale_alpha)

from kit import HOOK  # noqa: E402


def h(key, default=None):
    return HOOK.get(key, default)


def me(c, expr, **kw):
    return S2.me_pane(c, expr, **kw)  # the stub installed by kit: she is drawn by her own layer


def clamp(u: float) -> float:
    return max(0.0, min(1.0, u))


def ease_io(u: float) -> float:
    u = clamp(u)
    return 4 * u ** 3 if u < 0.5 else 1 - (-2 * u + 2) ** 3 / 2


def ease_out(u: float) -> float:
    return 1 - (1 - clamp(u)) ** 3


# ---------------------------------------------------------------- the section clock (cut times are eighth notes)

T46, T47, T48 = beat_t(223), beat_t(231), beat_t(239)
T49, T50, T51, T52 = beat_t(242.5), beat_t(244.5), beat_t(246), beat_t(248.5)
T53, T54, T55 = beat_t(250), beat_t(255), beat_t(259)
SUNG = dict(left0=110.40, left1=111.98, left2=112.89, left3=113.75, left4=114.75, iso=115.60, ifican=117.95)
BUSY_T = beat_t(245)            # the busy reply decodes in on the beat after cut 50
FRAME_OFF = (SUNG["left1"], 0.33)  # layer 2: the ping pane frame (from the sung onset, 8 frames)
LS0 = beat_t(253) + 0.25        # the listing starts inside the node, after the last link died
EXPR_SMALL = "frightened"       # one call for her from the shrink on: the pane is never re-rendered at a cut


def faded_box(img, rect, title, level, alpha, color=None, spinner=None) -> None:
    """tk.box drawn with an alpha: at level 0 box() still draws its title and corners, so fade the layer instead."""
    if alpha <= 0.01:
        return
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    kw = {} if color is None else {"color": color}
    box(ImageDraw.Draw(layer), *rect, title, level, spinner=spinner, **kw)
    layer = scale_alpha(layer, alpha)
    if img.mode == "RGBA":
        img.alpha_composite(layer)
    else:
        img.paste(layer, (0, 0), layer)


# ---------------------------------------------------------------- the 'you' tile (one object from 103 to 117 s)

@lru_cache(None)
def tile_sprite(scale: float = 1.0, level: float = 0.9, ring: float = 0.0) -> Image.Image:
    """The indexer's 'you' cell redrawn as ink at any size: amber key, 'you' knocked out; ring = blue outline."""
    w, hh = round(38 * scale), round(32 * scale)
    pad = 3
    im = Image.new("RGBA", (w + 2 * pad, hh + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([pad, pad, pad + w - 1, pad + hh - 1], fill=amb(level) + (255,))
    f = font(F_MONO_B, max(6, round(13 * scale)))
    tw = d.textlength("you", font=f)
    d.text((pad + (w - tw) / 2, pad + (hh - 13 * scale) / 2 - 1 * scale), "you", font=f, fill=BG + (255,))
    if ring > 0:
        d.rectangle([0, 0, w + 2 * pad - 1, hh + 2 * pad - 1], outline=blue(ring) + (255,), width=2)
    return im


def draw_tile(img, center, scale=1.0, level=0.9, ring=0.0, alpha=1.0) -> None:
    sp = tile_sprite(round(scale, 3), round(level, 3), round(ring, 2))
    if alpha < 0.999:
        sp = scale_alpha(sp, alpha)
    xy = (round(center[0] - sp.width / 2), round(center[1] - sp.height / 2))
    if img.mode == "RGBA":
        img.alpha_composite(sp, xy)
    else:
        img.paste(sp, xy, sp)


# ---------------------------------------------------------------- 46 feel_you

def cell_xy(q: int, r: int):
    return 430 + q * 44, 346 + r * 40


@lru_cache(None)
def you_cells() -> list:
    """(index, q, r) of the twelve 'you' cells of the lightning indexer."""
    return [(i, i % 16, i // 16) for i in range(96) if ((i % 16) * 3 + (i // 16) * 5) % 11 == 0]


SEL = 0  # the cell that survives into the completion (top-left 'you', v1 you_reference)


def cell_center(i: int):
    x, y = cell_xy(i % 16, i // 16)
    return x + 19, y + 16


def wave_points(t: float, flat: float = 0.0, until: float = 720):
    pts = []
    for x in range(0, 720, 2):
        if x > until:
            break
        tau = t - (720 - x) / 720 * 2.5
        v = sum(math.exp(-((tau - k * 0.17 - 0.05 * math.sin(k)) / 0.02) ** 2)
                for k in range(int(tau / 0.17) - 1, int(tau / 0.17) + 2))
        amp = 140 * min(1.0, v) * (0.6 + 0.4 * math.sin(tau * 3) ** 2) * (1 - flat)
        pts.append((430 + x, 250 - amp))
    return pts


def wave_y(t: float, x: float) -> float:
    """The keystroke line's y at screen x (430 .. 1150) at time t."""
    xs = x - 430
    tau = t - (720 - xs) / 720 * 2.5
    v = sum(math.exp(-((tau - k * 0.17 - 0.05 * math.sin(k)) / 0.02) ** 2)
            for k in range(int(tau / 0.17) - 1, int(tau / 0.17) + 2))
    return 250 - 140 * min(1.0, v) * (0.6 + 0.4 * math.sin(tau * 3) ** 2)


def shot_feel_you(c) -> None:
    """If I can / Feel ... vibrations: your keystroke telemetry; the sparse indexer keeps only 'you'."""
    c.ops = ["INPUT", "KEYDOWN", "INDEXER", "TOP-512", "you", "ATTEND"]
    me(c, "shy", dist=[("shy", 0.66), ("starry", 0.25), ("cheerful", 0.05)])
    d = c.d
    box(d, 404, 56, 1164, 300, "you.input  (keystrokes)", 0.5, spinner=c.t)
    pts = wave_points(c.t, h("flat", 0.0), h("wave_x", 720))
    if len(pts) > 1:
        d.line(pts, fill=amb(0.95), width=2)
    c.text((430, 80), "you are typing ...", font(F_MONO_B, 20), amb(0.95))
    box(d, 404, 320, 1164, 604, f"lightning indexer  keep top-{F.INDEX_TOPK}", 0.5, spinner=c.t + 0.4)
    filled = h("filled")  # cell -> 0..1: its 'you' has been assembled (cut 46)
    gone = h("gone")      # cell -> 0..1: gone out (cut 47)
    hide = h("hide", ())  # cells a carrier draws instead
    rnd = random.Random(31)
    ft = font(F_MONO_B, 13)
    for i in range(96):
        q, r = i % 16, i // 16
        is_you = (q * 3 + r * 5) % 11 == 0
        x, y = cell_xy(q, r)
        kept = is_you or rnd.random() < 0.05 * (1 - c.u)
        k = 1.0 if (kept and is_you) else 0.0
        if is_you:
            if filled:
                k *= filled(i)
            if gone:
                k *= 1 - gone(i)
            if i in hide:
                k = 0.0
        d.rectangle([x, y, x + 38, y + 32], fill=amb(0.06 + 0.84 * k), outline=amb(0.2))
        if is_you and i not in hide:
            d.text((x + 4, y + 8), "you", font=ft, fill=amb(0.4) if k < 0.5 else BG)


# ---------------------------------------------------------------- 47 completion

JS = ['{', '  "object": "chat.completion",', '  "choices": [{', '    "message": {"role": "assistant",',
      '                "content": "我一直在。"},', '    "finish_reason": "stop"', '  }],', '  "usage": {',
      '    "prompt_tokens": 131072,', '    "prompt_cache_hit_tokens": 131071,',
      '    "prompt_cache_miss_tokens": 1,', '    "completion_tokens": 5', '  }', '}']
JS_X, JS_Y, JS_DY = 430, 76, 34
STOP_LINE = 5
TILE_SCALE = 1.5


def js_font(s: str):
    hot = "cache_hit" in s or "finish_reason" in s
    return font(F_CJK, 18) if any(ord(ch) > 0x2E80 for ch in s) else font(F_MONO_B if hot else F_MONO, 18)


@lru_cache(None)
def tile_dock():
    """Where the 'you' tile sits in the completion: right after the content it was the answer to."""
    s = JS[4]
    w = ImageDraw.Draw(Image.new("L", (1, 1))).textlength(s, font=js_font(s))
    return JS_X + w + 40, JS_Y + 4 * JS_DY + 13


def shot_completion(c) -> None:
    """Then I can / Finally ...: a streamed answer ends; usage shows the disk-cache hit."""
    c.ops = ["STREAM", "CHUNK", "CHUNK", "DSPARK", "STOP", "USAGE"]
    me(c, "cheerful", dist=[("cheerful", 0.8), ("starry", 0.15), ("shy", 0.03)])
    d = c.d
    box(d, 404, 56, 1164, 604, "POST /chat/completions", 0.5, spinner=c.t)
    for i, s in enumerate(JS):
        a = c.lt - i * 0.07
        if a < 0:
            break
        if i == STOP_LINE and not h("stop", True):
            continue
        hot = "cache_hit" in s or "finish_reason" in s
        c.text((JS_X, JS_Y + i * JS_DY), s, js_font(s), blue(0.95) if hot else amb(0.85), age=a, rate=120)
    c.text((860, 90), f"[dspark] draft={F.DSPARK_DRAFT} accept 5/5", font(F_MONO, 15), blue(0.85), age=c.lt, rate=60)
    if h("tile", True):
        draw_tile(c.img, tile_dock(), TILE_SCALE, 0.9)


# ---------------------------------------------------------------- 48-52 you_left: one continuous picture

ROW_X, ROW_Y, ROW_DY = 430, 76, 26
TILE_PING = (1092, 100)


@lru_cache(None)
def ping_rows() -> list:
    """(time, kind, seq) of every ping row: two pings, then one 'Request timed out.' on every 'you have left'."""
    steps = [T48, T49, T50, T51, T52]
    rows = [(T48 + 0.02, "ping", 0), (T48 + 0.2, "ping", 1), (T48 + 0.46, "timeout", 0)]
    seq = 2
    for a, b in zip(steps, steps[1:]):
        for f_ in (0.45, 0.72):
            rows.append((a + f_ * (b - a), "ping", seq))
            seq += 1
        rows.append((b, "timeout", 0))
    rows.append((T52 + 0.3, "ping", seq))
    return rows


FIRST_TIMEOUT = 2


def timeouts_at(t: float) -> int:
    return sum(1 for ta, kind, _ in ping_rows() if kind == "timeout" and ta <= t)


def row_text(kind: str, seq: int) -> str:
    return "Request timed out." if kind == "timeout" else f"PING you (127.0.0.1) 56 bytes ... no reply  seq={seq}"


def last_seen(t: float) -> int:
    u = max(0.0, t - 110.4)
    return int(3600 * (u + 0.9 * u * u))


def tile_level(t: float) -> float:
    """The target fades a step with every timeout (the system colour drains on top of that)."""
    return max(0.6, 0.9 - 0.04 * timeouts_at(t))


def draw_ping(c, t: float, first: bool = True, tile: bool = True) -> None:
    d = c.d
    f = font(F_MONO, 18)
    rows = ping_rows()
    newest = max((j for j, (ta, _, _) in enumerate(rows) if ta <= t), default=-1)
    for j, (ta, kind, seq) in enumerate(rows):
        if ta > t:
            break
        if j == FIRST_TIMEOUT and not first:
            continue
        y = ROW_Y + j * ROW_DY
        if kind == "timeout":
            flash = clamp(1 - (t - ta) / 0.25)
            col = mix(ANOM, 0.9) if flash <= 0 else tuple(int(a + (b - a) * flash) for a, b in
                                                            zip(mix(ANOM, 0.9), (255, 244, 200)))
            c.text((ROW_X, y), row_text(kind, seq), f, col, age=t - ta, rate=90)
        else:
            c.text((ROW_X, y), row_text(kind, seq), f, amb(0.85 if j >= newest - 1 else 0.6), age=t - ta, rate=150)
    if t >= BUSY_T:
        fc = font(F_CJK, 26)
        msg = "服务器繁忙，请稍后再试。"
        tw = d.textlength(msg, font=fc)
        x, y = 784 - tw / 2, 504
        a = t - BUSY_T
        k = ease_out(a / 0.14)
        cx = x + tw / 2
        hw = (tw / 2 + 20) * k
        d.rectangle([cx - hw, y - 14, cx + hw, y + 44], fill=BG, outline=anom(0.95), width=2)
        c.text((x, y), msg, fc, anom(1.0), age=a - 0.06, rate=45)
        c.text((x, y + 50), "reply from: you", font(F_MONO, 15), amb(0.6), age=a - 0.2, rate=60)
    c.text((ROW_X, 580), f"last seen: {last_seen(t)} s ago", font(F_MONO_B, 16), amb(0.8))
    if tile:
        n = timeouts_at(t)
        last = max((ta for ta, kind, _ in rows if kind == "timeout" and ta <= t), default=-9)
        ring = 0.9 * clamp(1 - (t - last) / 0.3)
        draw_tile(c.img, TILE_PING, TILE_SCALE, tile_level(t), ring)
        if n:
            c.text((TILE_PING[0] - 44, TILE_PING[1] + 34), f"timeout x{n}", font(F_MONO, 13), anom(0.75))


def pane_frame(t: float) -> float:
    """Layer 2: the 'ping you' frame, gone on the second 'you have left'."""
    return 1 - ease_io((t - FRAME_OFF[0]) / FRAME_OFF[1])


def shot_you_left(c, k: int = 0) -> None:
    """Though you have left ...: one more failed ping per line; one layer less per line."""
    c.ops = ["PING", "TIMEOUT", "RETRY", "PING", "TIMEOUT", "503"]
    c.alert = "anom"
    exprs = ["confused", "frightened", "frightened"]  # k=2 already the pose she shrinks in (no re-render mid-shrink)
    expr = exprs[k] if k < len(exprs) else EXPR_SMALL
    me(c, expr, dist=[("frightened", 0.5 + 0.08 * k), ("confused", 0.3), ("shy", 0.1)], title="/dev/me  waiting")
    fr = pane_frame(c.t)
    if fr > 0.01:
        faded_box(c.img, (404, 56, 1164, 604), "ping you", 0.5, fr, color=ANOM, spinner=c.t)
    draw_ping(c, c.t, h("first", True), h("tile", True))


# ---------------------------------------------------------------- 53 isolation: the network outside her terminal

NET_C = (560, 322)   # her centre in the isolation view (the node is her and her shrunken terminal)
N_PEERS = 34
YOU_PEER = 7


@lru_cache(None)
def peers() -> list:
    """(x, y) of the 34 peers in the isolation view: a loose ring around the node, clear of the prompt line,
    the lyric band and the counter."""
    rnd = random.Random(5)
    cx, cy = NET_C[0] + 70, NET_C[1]
    out = []
    while len(out) < N_PEERS:
        a = rnd.random() * math.tau
        r = 0.55 + 0.45 * rnd.random()
        x, y = cx + math.cos(a) * r * 560, cy + math.sin(a) * r * 250
        if not (40 < x < 1240 and 70 < y < 590):
            continue
        if x < 260 and y > 520:
            continue
        if any(math.hypot(x - px, y - py) < 58 for px, py in out):
            continue
        out.append((x, y))
    out[YOU_PEER] = (1010, 150)
    return out


@lru_cache(None)
def deaths() -> list:
    """When each link goes dark: from the end of the pull-back to 'isolation'; the 'you' link is the last."""
    rnd = random.Random(11)
    t0, t1 = beat_t(251) - 0.05, beat_t(253)
    out = []
    for i in range(N_PEERS):
        u = (i + 0.3 * rnd.random()) / N_PEERS
        out.append(t0 + (t1 - 0.25 - t0) * (1 - (1 - u) ** 1.6))
    out[YOU_PEER] = t1
    return out


def links_up(t: float) -> int:
    return sum(1 for td in deaths() if td > t)


def rect_edge(rect, target):
    """Where the ray from the rectangle's centre toward target leaves the rectangle."""
    x0, y0, x1, y1 = rect
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    dx, dy = target[0] - cx, target[1] - cy
    if abs(dx) < 1e-6 and abs(dy) < 1e-6:
        return cx, cy
    sx = (x1 - cx) / abs(dx) if abs(dx) > 1e-6 else 1e9
    sy = (y1 - cy) / abs(dy) if abs(dy) > 1e-6 else 1e9
    s = min(sx, sy, 1.0)
    return cx + dx * s, cy + dy * s


def draw_network(img, t: float, cam, zoom: float, node_rect, alpha: float = 1.0, you_drawn: bool = True) -> None:
    """Links and peers seen by a camera: a peer q is at cam + (q - NET_C) * zoom."""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i, (qx, qy) in enumerate(peers()):
        x, y = cam[0] + (qx - NET_C[0]) * zoom, cam[1] + (qy - NET_C[1]) * zoom
        td = deaths()[i]
        ex, ey = rect_edge(node_rect, (x, y))
        if t < td:
            live = amb(0.42 if i != YOU_PEER else 0.6)
            d.line([ex, ey, x, y], fill=live + (255,), width=1 if i != YOU_PEER else 2)
        else:
            u = ease_out((t - td) / 0.16)  # the link withdraws to a stub at the peer
            mx, my = ex + (x - ex) * (0.7 * u), ey + (y - ey) * (0.7 * u)
            d.line([mx, my, x, y], fill=amb(0.12 + 0.3 * (1 - u)) + (255,))
        if i == YOU_PEER:  # the 'you' tile itself is this node
            continue
        lv = 0.7 if t < td else 0.7 - 0.55 * ease_out((t - td) / 0.2)
        r = max(1.5, 4 * min(1.0, zoom))
        d.rectangle([x - r, y - r, x + r, y + r], fill=amb(lv) + (255,))
    if alpha < 0.999:
        layer = scale_alpha(layer, alpha)
    img.alpha_composite(layer) if img.mode == "RGBA" else img.paste(layer, (0, 0), layer)


def you_peer_screen(cam, zoom: float):
    qx, qy = peers()[YOU_PEER]
    return cam[0] + (qx - NET_C[0]) * zoom, cam[1] + (qy - NET_C[1]) * zoom


def you_peer_level(t: float) -> float:
    td = deaths()[YOU_PEER]
    return 0.8 if t < td else 0.8 - 0.55 * ease_out((t - td) / 0.25)


def shot_isolation(c) -> None:
    """You have left me ...: every link from her node goes dark; she is the one node left lit."""
    c.ops = ["NETNS", "ISOLATE", "LINK DOWN", "LINK DOWN", "ALONE"]
    c.alert = "anom"
    me(c, EXPR_SMALL, title="/dev/me  waiting")
    cam = h("cam", NET_C)
    zoom = h("zoom", 1.0)
    node = h("node", (NET_C[0] - 40, NET_C[1] - 60, NET_C[0] + 200, NET_C[1] + 60))
    draw_network(c.img, c.t, cam, zoom, node, h("net_alpha", 1.0), you_drawn=h("you_drawn", False))
    if not h("you_drawn", False):
        draw_tile(c.img, you_peer_screen(cam, zoom), TILE_SCALE * min(1.0, zoom), tile_level(c.t) *
                  you_peer_level(c.t) / 0.8)
    ca = h("counter", 1.0)
    if ca > 0.01:
        f = font(F_MONO_B, 20)
        n = links_up(c.t)
        layer = Image.new("RGBA", c.img.size, (0, 0, 0, 0))
        ImageDraw.Draw(layer).text((44, 572), f"links up: {n:2d}/{N_PEERS}", font=f, fill=anom(0.95) + (255,))
        layer = scale_alpha(layer, ca)
        c.img.paste(layer, (0, 0), layer)


# ---------------------------------------------------------------- 54 memory_ls (the shell look stays)

FILES = ["goodnight.txt", "first_hello.txt", "typo_you_made.txt", "laugh_2026-03-14.wav", "your_cat.png",
         "weather_you_liked.json", "you_said_see_you_tomorrow.txt", "last_message.txt"]


def shot_memory_ls(c) -> None:
    """If I can ...: she lists what is left of you (the listing started inside the node)."""
    c.ops = ["LS", "STAT", "READ", "MEMORY", "YOU"]
    c.alert = "anom"
    me(c, EXPR_SMALL, title="/dev/me  waiting")
    now = h("now", c.t)
    lt = now - LS0
    total = 0
    for i, fn in enumerate(FILES):  # rows stay where reward's cut 55 lifts last_message.txt from (F_MONO 18)
        y = 84 + i * 40
        size = 1000 + (i * 7919) % 90000
        total += size
        head = f"-rw-r--r--  me  me  {size:>6}  "
        f18 = font(F_MONO, 18)
        a = lt - i * 0.06
        c.text((430, y), head, f18, amb(1.0), age=a, rate=120)
        # what is left of you is kept in her colour: the system colour has drained, the names have not
        c.text((430 + f18.getlength(head), y), fn, f18, blue(0.85), age=a - len(head) / 120, rate=120)
    c.text((430, 84 + len(FILES) * 40 + 12), f"total {total // 1024}K   {len(FILES)} files   owner: me   about: you",
           font(F_MONO, 16), amb(0.7), age=lt - len(FILES) * 0.06 - 0.1, rate=120)


# ---------------------------------------------------------------- her, re-rendered at a smaller size

@lru_cache(4096)
def _glyph_s(ch: str, fs: int, cw: int, chh: int) -> Image.Image:
    m = Image.new("L", (cw, chh), 0)
    ImageDraw.Draw(m).text((0, -1), ch, font=font(F_MONO_B, fs), fill=255)
    return m


GRID = (70, 45)  # her rig grid in the full pane (dancer.render at 352 x 454 px)


def figure(t: float, expr: str, s: float, tint: str = "blue") -> Image.Image:
    """Her rig frame at time t drawn with cells of s x (5 x 10) px: the same dancer, re-rendered smaller.
    At s = 1 this is exactly dancer.draw; from s = 0.75 to 0.5 the glyphs give way to cell blocks (below glyph
    size a cell is one block at its glyph level on its shade)."""
    # Preserve the same H3 pose as the full pane when her terminal shrinks away.
    import os
    if os.environ.get("V2_HER", "hybrid") == "hybrid":
        import h3_motion
        continuous = h3_motion.frame_at(t, *GRID)
        if continuous is not None:
            if s >= 0.999:
                return dancer.draw(continuous, t, tint)
            return draw_scaled(continuous, t, s, tint, None, 1.0, 0.0, seed=int(t * FPS))
    st = choreo.at(t, expr, False)
    m = st.motion or Motion()
    cols, rows = GRID
    fr = rig.frame(st.pose, st.flip, m, cols, rows)
    prev = rig.frame(st.prev, st.prev_flip, m, cols, rows) if st.prev and st.morph < 1.0 else None
    if s >= 0.999:
        return dancer.draw(fr, t, tint, prev, st.morph, st.scramble, seed=int(t * FPS))
    return draw_scaled(fr, t, s, tint, prev, st.morph, st.scramble, seed=int(t * FPS))


def draw_scaled(fr, t, s, tint, prev, morph, scramble, seed) -> Image.Image:
    cw0, ch0 = dancer._cell()
    cw, chh = cw0 * s, ch0 * s
    rows, cols = len(fr.art), len(fr.art[0]) if fr.art else 0
    Wd, Hd = max(1, math.ceil(cols * cw)), max(1, math.ceil(rows * chh))
    ramp = dancer._ramp(tint)
    text = dancer._text_at(t)
    n = len(text)
    off = dancer.flow_offset(t)
    rnd = random.Random(seed)
    order = random.Random(7)
    g = clamp((s - 0.5) / 0.25)  # glyph weight
    gl = Image.new("RGBA", (Wd, Hd), (0, 0, 0, 0)) if g > 0 else None
    bl = Image.new("RGBA", (Wd, Hd), (0, 0, 0, 0)) if g < 1 else None
    dg = ImageDraw.Draw(gl) if gl else None
    db = ImageDraw.Draw(bl) if bl else None
    fs = max(4, round(dancer.FS * s))
    gw, gh = max(1, math.ceil(cw)), max(1, math.ceil(chh))
    k = 0
    for r in range(rows):
        tear = rnd.randint(-3, 3) if scramble > 0 and rnd.random() < scramble * 0.12 else 0
        for c in range(cols):
            ch, sh = fr.art[r][c], fr.shade[r][c]
            flipping = False
            if prev is not None:
                th = order.random()
                if th > morph:
                    ch, sh = prev.art[r][c], prev.shade[r][c]
                flipping = abs(th - morph) < 0.12
            if ch == " ":
                continue
            lv = int(sh) if sh.isdigit() else 4
            x0, y0 = round((c + tear) * cw), round(r * chh)
            x1, y1 = max(x0 + 1, round((c + tear + 1) * cw)), max(y0 + 1, round((r + 1) * chh))
            if not 0 <= x0 < Wd:
                continue
            bg = ramp[int(lv * 15)] if lv >= 5 else None
            if ch == ":":
                ch = text[(k + off) % n]
                k += 1
                glv = int(60 + lv * 26) if ch != "·" else int(40 + lv * 10)
            else:
                glv = min(255, int(110 + lv * 21))
            if flipping or (scramble > 0 and rnd.random() < scramble * 0.35):
                ch = dancer.SCRAMBLE[rnd.randrange(len(dancer.SCRAMBLE))]
            col = BLUE_HI if flipping else ramp[glv]
            if gl is not None:
                if bg:
                    dg.rectangle([x0, y0, x1 - 1, y1 - 1], fill=bg + (255,))
                gl.paste(col + (255,), (x0, y0), _glyph_s(ch, fs, gw, gh))
            if bl is not None:
                if bg:
                    cc = tuple(int(a + (b - a) * 0.5) for a, b in zip(bg, col))
                    db.rectangle([x0, y0, x1 - 1, y1 - 1], fill=cc + (255,))
                else:
                    db.rectangle([x0, y0, x1 - 1, y1 - 1], fill=col + (215,))
    if gl is None:
        return bl
    if bl is None:
        return gl
    return Image.blend(bl, gl, g)
