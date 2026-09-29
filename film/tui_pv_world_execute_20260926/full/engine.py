"""Full-song engine for the whale-girl TUI PV: timing, chrome, mascot pane, timeline, parallel render.

Section modules (sec_*.py) register shots with `add(start, end, fn, chapter=..., alert=...)`.
A shot function receives a Ctx and draws the frame body; the engine adds the header, op ticker,
token lyrics and CRT post-processing.
"""

from __future__ import annotations

import math
import random
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import tuikit as tk  # noqa: E402
from tuikit import (AMBER, BG, F_CJK, F_HEAD, F_MONO, F_MONO_B, RED, H, W, amb, anom, blue, box,  # noqa: E402
                    decode, dot_field, font, glitch_paste, glyph_sprite, halfblock, paste_clipped, post, red,
                    scale_alpha, token_id, tokenize)

HERE = Path(__file__).resolve().parent
MV = Path(__file__).resolve().parents[2].joinpath("ai_mascot_mv_world_execute_20260926")
AUDIO = Path(__file__).resolve().parents[3].joinpath("input", "song.mp3")
LRC = MV / "audio" / "lyrics_synced.lrc"

FPS = 24
BPM = 130.0
BEAT = 60.0 / BPM
FIRST_BEAT = 0.1587   # audio/beats.json
SONG_LEN = 211.91
HARD_CUT = 207.58     # silencedetect -50 dB on the source mp3
END_T = 211.0         # video length: black after the hard cut

LEFT = (24, 56, 384, 604)
CENTER = (404, 56, 1164, 604)
TICK = (1180, 56, 1256, 604)
FULL = (24, 56, 1164, 604)

KEYWORDS = {
    "power", "protection", "creation", "parameters", "initialization", "world", "simulation", "simulations",
    "dimension", "circumference", "tangents", "infinity", "limitations", "vision", "dizzy", "unite", "deeply",
    "satisfaction", "happy", "execution", "trapped", "strange", "nutrients", "antioxidants", "enjoyment", "god",
    "existence", "trance", "vibrations", "completion", "left", "isolation", "fragments", "disheartened",
    "illegal", "arguments", "love", "lo-o-ove", "free", "back",
}


def beat_t(n: float) -> float:
    return FIRST_BEAT + n * BEAT


def snap8(t: float) -> float:
    return FIRST_BEAT + round((t - FIRST_BEAT) / (BEAT / 2)) * BEAT / 2


def beat_index(t: float) -> int:
    return math.floor((t - FIRST_BEAT) / BEAT + 1e-6)


def pulse(t: float, decay: float = 0.14) -> float:
    return math.exp(-(t - beat_t(beat_index(t))) / decay)


def keyframes(t: float, pts: list[tuple[float, float]]) -> float:
    if t <= pts[0][0]:
        return pts[0][1]
    for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
        if t <= t1:
            u = (t - t0) / (t1 - t0)
            return v0 + (v1 - v0) * u
    return pts[-1][1]


# ---------------------------------------------------------------- narrative colour arc

CHAPTERS = [(0.0, "00 / BOOT"), (16.0, "01 / PRETRAIN"), (44.0, "02 / SFT"), (58.5, "03 / RLHF"),
            (73.5, "04 / DEPLOY"), (103.0, "05 / USER_LEFT"), (118.0, "06 / REWARD_HACK"),
            (147.4, "07 / EXECUTION"), (176.9, "08 / EVAL: LOVE"), (193.4, "09 / WHALE_FALL")]


def chapter_at(t: float) -> str:
    return [lab for s, lab in CHAPTERS if s <= t][-1]


def ui_gain(t: float) -> float:
    """The system colour is 'you'. It drains when you leave and never fully comes back."""
    return keyframes(t, [(0, 1.0), (110.4, 1.0), (116.5, 0.42), (176.9, 0.42), (179.5, 0.85), (193, 0.75),
                         (206, 0.45)])


# ---------------------------------------------------------------- context

@dataclass
class Ctx:
    img: Image.Image
    d: ImageDraw.ImageDraw
    t: float
    lt: float
    dur: float
    rng: random.Random
    chapter: str = ""
    alert: str = ""
    corrupt: float = 0.0
    black: bool = False
    flash_red: bool = False
    no_chrome: bool = False
    ops: list = field(default_factory=list)
    echo: str = ""  # the one number or word this shot is about (shown next to her in focus mode)

    @property
    def u(self) -> float:
        return self.lt / self.dur

    def text(self, xy, s, f, fill, age=None, rate=45.0, settle=0.12):
        self.d.text(xy, decode(s, age, self.rng, rate, settle, self.corrupt), font=f, fill=fill)


def load_lrc() -> list[tuple[float, float, str]]:
    rows = []
    for line in LRC.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\[(\d+):(\d+\.\d+)\](.*)", line)
        if m:
            rows.append((int(m[1]) * 60 + float(m[2]), m[3].strip()))
    out = []
    for i, (t, s) in enumerate(rows):
        if s:
            out.append((t, rows[i + 1][0] if i + 1 < len(rows) else t + 3, s))
    return out


LYRICS = load_lrc()


def lyric_start(prefix: str, after: float = 0.0) -> float:
    """Start time of the first lyric line at or after `after` that begins with `prefix`."""
    return next(a for a, b, s in LYRICS if a >= after - 1e-6 and s.lower().startswith(prefix.lower()))


# ---------------------------------------------------------------- persistent chrome

def header(c: Ctx) -> None:
    d = c.d
    col = red if c.alert == "err" else anom if c.alert == "anom" else amb
    fh = font(F_HEAD, 13)
    c.text((24, 14), "WORLD.EXECUTE(ME);   whale@deepsea:~$", fh, col(0.95))
    step = int(c.t * 412)
    loss = 2.2 * math.exp(-c.t / 28) + 0.31 + 0.02 * math.sin(c.t * 9.1)
    tps = 140 + 12 * math.sin(c.t * 3.1)
    c.text((340, 15), f"step {step:08d}   loss {loss:.4f}   tok/s {tps:6.1f}", font(F_MONO, 13), col(0.55))
    x0, y0, w = 690, 25, 150
    pts = []
    for px in range(w):
        tau = c.t - (w - px) / w * 1.4
        bt = beat_t(round((tau - FIRST_BEAT) / BEAT))
        dt = tau - bt
        v = -11 * math.exp(-(dt / 0.016) ** 2) + 4 * math.exp(-((dt - 0.05) / 0.025) ** 2)
        pts.append((x0 + px, y0 + v))
    d.line(pts, fill=col(0.9), width=1)
    mm, ss = divmod(c.t, 60)
    state = {"err": "ERROR", "anom": "WARN"}.get(c.alert, "RUNNING")
    right = f"{c.chapter}   {int(mm):02d}:{ss:04.1f} / 03:32   {state}"
    c.text((W - 24 - d.textlength(right, font=fh), 14), right, fh, col(0.85))
    d.line([24, 38, W - 24, 38], fill=col(0.35))
    fs = font(F_MONO, 12)
    n = 60
    k = int(n * c.t / SONG_LEN)
    d.text((24, 690), "[" + "|" * k + ":" * (n - k) + "]", font=fs, fill=amb(0.4))
    credit = ("角色 溟月 © 上善无形 / 女仆版 ZipZipPipe / 立绘·表情 dsh-deep-whale, dsh-whale-galgame (CC BY-NC-SA 4.0)"
              "  ·  Music: Mili - world.execute(me);  ·  非官方同人 草稿")
    d.text((500, 689), credit, font=font(F_CJK, 11), fill=amb(0.38))


def ticker(c: Ctx) -> None:
    x0, y0, x1, y1 = TICK
    box(c.d, x0, y0, x1, y1, "ops", 0.45, color=RED if c.alert == "err" else AMBER)
    ops = c.ops or ["IDLE"]
    f = font(F_MONO, 12)
    rh = 17
    scroll = c.t * (rh / (BEAT / 2))
    cursor_row = 15
    base = int(scroll // rh)
    off = scroll % rh
    for i in range(-1, 32):
        y = y0 + 10 + i * rh - off
        if y < y0 + 4 or y > y1 - 16:
            continue
        op = ops[(base + i) % len(ops)]
        if i == cursor_row:
            fill = red(0.95) if c.alert == "err" else amb(0.95)
            c.d.rectangle([x0 + 4, y - 1, x1 - 4, y + 14], fill=fill)
            c.d.text((x0 + 8, y), op[:10], font=f, fill=BG)
        else:
            dist = abs(i - cursor_row)
            c.text((x0 + 8, y), op[:10], f, amb(max(0.18, 0.6 - dist * 0.04)))


def lyric_tokens(c: Ctx) -> None:
    d = c.d
    box(d, 24, 616, 1256, 680, "stdout · tokens", 0.45 + 0.3 * pulse(c.t))
    cur = next(((a, b, s) for a, b, s in LYRICS if a <= c.t < b), None)
    f = font(F_HEAD, 21)
    fi = font(F_MONO, 11)
    x, y = 48, 626
    d.text((x, y), ">", font=f, fill=amb(0.6))
    x += 26
    if cur is None:
        if int(c.t * 2) % 2 == 0:
            d.rectangle([x, y + 4, x + 11, y + 28], fill=amb(0.9))
        return
    a, b, s = cur
    type_dur = min(0.9, (b - a) * 0.6)
    rate = len(s) / type_dur
    typed_n = int(len(s) * min(1.0, (c.t - a) / type_dur))
    pos = 0
    for k, tok in enumerate(tokenize(s)):
        start = s.find(tok, pos)
        if start < 0:
            continue
        gap = start > pos
        pos = start + len(tok)
        if start >= typed_n:
            break
        if gap:
            x += 8
        shown = tok[: typed_n - start]
        age = (c.t - a) - start / rate
        txt = decode(shown, age, c.rng, rate, 0.1, c.corrupt)
        tw = d.textlength(tok, font=f)
        ws = s.rfind(" ", 0, start) + 1
        we = s.find(" ", start)
        we = len(s) if we < 0 else we
        key = re.sub(r"[^a-z-]", "", s[ws:we].lower())
        hot = key in KEYWORDS and typed_n >= we
        if hot:
            bg = red(0.95) if "exec" in key or key in ("illegal", "arguments") else \
                blue(0.95) if key in ("love", "lo-o-ove") else amb(0.95)
            d.rectangle([x - 3, y + 2, x + tw + 3, y + 30], fill=bg)
            d.text((x, y), txt, font=f, fill=BG)
        else:
            d.rectangle([x - 3, y + 2, x + tw + 3, y + 30], fill=amb(0.13 if k % 2 == 0 else 0.22))
            d.text((x, y), txt, font=f, fill=amb(0.95))
        if typed_n >= pos:
            tid = str(token_id(tok))
            d.text((x + (tw - d.textlength(tid, font=fi)) / 2, y + 33), tid, font=fi, fill=amb(0.45))
        x += tw + 6
    if typed_n < len(s) or int(c.t * 3) % 2 == 0:
        d.rectangle([x + 2, y + 4, x + 13, y + 28], fill=amb(0.9))


# ---------------------------------------------------------------- the mascot pane

def me_pane(c: Ctx, expr: str, rect=LEFT, mode: str = "half", morph: float = 1.0, scramble: float = 0.0,
            reveal: float = 1.0, dy: int = 0, glitch: float = 0.0, dist=None, bright: float = 1.0,
            bubbles: float = 0.0, overlay=None, title: str = "/dev/me  pid 4471", color=AMBER,
            sprite_img: Image.Image | None = None, crop: str = "full", tint: str = "blue"):
    """Draws her pane. Returns (x, y, sprite) so a shot can put overlays on her."""
    x0, y0, x1, y1 = rect
    d = c.d
    box(d, x0, y0, x1, y1, title, 0.45 + 0.35 * pulse(c.t), color=color, spinner=c.t)
    bottom = y1 - (78 if dist else 6)
    clip = (x0 + 2, y0 + 12, x1 - 2, bottom)
    avail_w, avail_h = (x1 - x0) - 36, (bottom - y0) - 22
    sp = sprite_img if sprite_img is not None else halfblock(expr, crop, avail_w, avail_h, 4, tint=tint)
    breath = int(round(1.5 * math.sin(c.t * math.pi * 2 / (BEAT * 4))))
    sx, sy = (x0 + x1 - sp.width) // 2, y0 + 16 + dy + breath
    import music
    feat = music.at(c.t)
    if mode in ("glyph", "morph") and morph < 1.0:
        f = font(F_MONO_B, 11)
        cols = max(4, int(sp.width / f.getlength("M")))
        rows = max(4, int(sp.height / 13))
        g = glyph_sprite(expr, crop, cols, rows, 11, min(1.0, scramble + 0.12 * feat.flux), c.rng, tint=tint,
                         reveal=reveal)
        g = scale_alpha(g, (1 - morph) * bright)
        gx = (x0 + x1 - g.width) // 2
        if glitch > 0:
            glitch_paste(c.img, g, gx, sy, glitch, c.rng, clip)
        else:
            paste_clipped(c.img, g, gx, sy, clip)
    if mode in ("half", "morph") and morph > 0:
        import dancer
        if DANCE and mode == "half" and sprite_img is None and overlay is None:
            # she dances (choreo + rig), made of the lyric she is singing (dancer.py)
            fig, _ = dancer.render(c.t, (x1 - x0 - 8, bottom - y0 - 16), expr, False, tint)
            fx, fy, fh = x0 + 4, y0 + 14 + dy, fig.height
        else:
            # pinned overlays and custom sprites keep their framing: the body only ripples with the music,
            # but the lyric still streams through it
            mp, off = music.react(sp, c.t, 4, 0.5 if overlay else 1.0)
            hop = 4 * int(round(feat.kick ** 2 * 1.2 * (0.5 if overlay else 1.0)))
            if DANCE and sprite_img is None:
                fig = scale_alpha(mp, dancer.UNDER)
                fig.alpha_composite(dancer.strings(mp, c.t, tint, seed=int(c.t * FPS)))
            else:
                fig = mp
            fx, fy, fh = sx - off, sy - hop, sp.height
        s2 = scale_alpha(fig, morph * bright)
        if glitch > 0:
            glitch_paste(c.img, s2, fx, fy, glitch, c.rng, clip)
        else:
            paste_clipped(c.img, s2, fx, fy, clip)
        # the scan line sits where the tune sits: high notes near her head, low ones near the tail
        ly = fy + int((0.92 - 0.84 * feat.cent) * fh)
        if clip[1] < ly < clip[3]:
            d.line([x0 + 12, ly, x1 - 12, ly], fill=blue(0.25 + 0.4 * feat.loud))
    if bubbles > 0:
        fb = font(F_MONO, 14)
        for i in range(14):
            ph = (c.t * (0.35 + 0.05 * (i % 5)) + i * 0.137) % 1
            bx = sx + sp.width * (0.3 + 0.4 * ((i * 0.618) % 1)) + 8 * math.sin(c.t * 3 + i)
            by = sy + 60 - ph * 260
            if clip[1] < by < clip[3]:
                d.text((bx, by), "oO°.o"[i % 5], font=fb, fill=blue(0.8 * bubbles * (1 - ph)))
    if overlay:
        overlay(c, sx, sy, sp)
    if dist:
        f = font(F_MONO, 13)
        d.line([x0 + 12, y1 - 70, x1 - 12, y1 - 70], fill=amb(0.25))
        d.text((x0 + 14, y1 - 66), "cls.expression  softmax", font=f, fill=amb(0.5))
        for i, (name, p) in enumerate(dist[:3]):
            p = max(0.0, min(1.0, p + 0.015 * math.sin(c.t * 7 + i * 2)))
            yy = y1 - 48 + i * 15
            d.text((x0 + 14, yy), f"{name:<11}", font=f, fill=blue(0.95) if i == 0 else amb(0.6))
            d.rectangle([x0 + 120, yy + 4, x0 + 120 + int(170 * p), yy + 11],
                        fill=blue(0.9) if i == 0 else amb(0.45))
            d.text((x0 + 298, yy), f"{p:.2f}", font=f, fill=amb(0.7))
    return sx, sy, sp


# ---------------------------------------------------------------- timeline

@dataclass
class Shot:
    start: float
    end: float
    fn: object
    chapter: str | None = None
    alert: str = ""
    params: dict = field(default_factory=dict)


SHOTS: list[Shot] = []


def add(start: float, end: float, fn, chapter: str | None = None, alert: str = "", **params) -> None:
    SHOTS.append(Shot(start, end, fn, chapter, alert, params))


def finalize() -> None:
    SHOTS.sort(key=lambda s: s.start)
    for a, b in zip(SHOTS, SHOTS[1:]):
        if abs(a.end - b.start) > 1e-6:
            raise ValueError(f"timeline gap/overlap between {a.fn.__name__} ({a.end:.3f}) and "
                             f"{b.fn.__name__} ({b.start:.3f})")
    if SHOTS[0].start > 1e-6 or SHOTS[-1].end < END_T - 1e-6:
        raise ValueError(f"timeline must cover 0..{END_T}: {SHOTS[0].start:.3f}..{SHOTS[-1].end:.3f}")
    import direction
    for s in SHOTS:
        s.chapter = s.chapter or chapter_at(s.start + 1e-3)
    CUTS.clear()
    for a, b in zip(SHOTS, SHOTS[1:]):
        spec = direction.transition(a, b)
        if spec:
            n = spec["frames"] / FPS
            # the move lands on the cut: most of it happens before, the tail settles after
            pre = min(0.7 * n, 0.6 * (a.end - a.start))
            post_ = min(0.3 * n, 0.4 * (b.end - b.start))
            CUTS.append((b.start, a, b, spec, pre, post_))


CUTS: list = []  # (cut time, outgoing shot, incoming shot, spec, seconds before, seconds after)


def transition_at(t: float):
    for cut, a, b, spec, pre, post_ in CUTS:
        if cut - pre <= t < cut + post_:
            return cut, a, b, spec, pre, post_
    return None


def shot_at(t: float) -> Shot:
    for s in SHOTS:
        if s.start <= t < s.end:
            return s
    return SHOTS[-1]


def render_body(t: float, index: int, shot: Shot) -> dict:
    """The shot's own drawing on the standard canvas, plus how its layout wants it arranged."""
    import direction
    import stage
    mode, kind, extra = direction.layout(shot)
    tk.UI_GAIN[0] = ui_gain(t)
    tk.BOXES[0] = mode != "shell"
    img = stage.background(t)
    c = Ctx(img, ImageDraw.Draw(img), t, max(0.0, t - shot.start), shot.end - shot.start,
            random.Random(index * 7919), chapter=shot.chapter or chapter_at(t), alert=shot.alert)
    try:
        shot.fn(c, **shot.params)
    finally:
        tk.BOXES[0] = True
    return dict(ctx=c, canvas=c.img, mode=mode, kind=kind, extra=extra, black=c.black)


def finish(body: dict) -> Image.Image:
    import stage
    c = body["ctx"]
    if body["black"]:
        return c.img
    c.d = ImageDraw.Draw(c.img)
    img = stage.compose(c, body["mode"], body["kind"], body["extra"])
    if c.flash_red:
        img = ImageOps.colorize(img.convert("L"), black=BG, white=RED, mid=(150, 30, 20)).convert("RGB")
    return img


def render_base(t: float, index: int, shot: Shot) -> tuple[Image.Image, bool]:
    body = render_body(t, index, shot)
    return finish(body), body["black"]


def _anchor(spec_rect, body: dict, other: dict | None = None):
    import stage
    if spec_rect == "screen":
        return (0, 0, W, H)
    if spec_rect == "me":
        els = {e["id"]: e for e in stage.geometry(body["mode"], body["kind"], body["extra"])}
        return tuple(els["me"]["dst"]) if "me" in els else (0, 0, W, H)
    if stage.identity(body["mode"], body["kind"]):
        return spec_rect
    return stage.to_screen(spec_rect, stage.geometry(body["mode"], body["kind"], body["extra"]))


FOCUS = __import__("os").environ.get("TUI_FOCUS") == "1"
# anchored staging: every picture keeps its v3 size and layout, but she never leaves the left side of the screen
# and the current lyric is always in the bottom-left band (see stage.py and direction.layout)
ANCHOR = __import__("os").environ.get("TUI_ANCHOR") == "1"
# her pane: dancing and made of glyph strings (dancer.py); TUI_DANCE=0 restores the still half-block portrait
DANCE = __import__("os").environ.get("TUI_DANCE", "1") == "1"
tk.LYRIC_LIFT[0] = ANCHOR


def render_frame(t: float, prev: Image.Image | None, index: int, shot: Shot | None = None) -> Image.Image:
    if FOCUS:
        import focus
        return focus.render_frame(t, prev, index)
    tr = transition_at(t)
    if tr:
        import stage
        import transitions
        cut, a, b, spec, pre, post_ = tr
        p = (t - (cut - pre)) / (pre + post_)
        rng = random.Random(index * 31)
        body_a = render_body(t, index, a)
        body_b = render_body(max(t, b.start), index, b)
        kind = spec["kind"]
        if kind == "glide" and not (body_a["black"] or body_b["black"] or body_a["ctx"].no_chrome
                                    or body_b["ctx"].no_chrome or body_a["mode"] == "raw" or body_b["mode"] == "raw"):
            img = stage.glide(body_a, body_b, p, rng)
            return post(img, None)
        img_a, img_b = finish(body_a), finish(body_b)
        if kind == "glide":
            kind = "reflow"
        kw = {}
        if kind == "zoom":
            kw = dict(a_rect=_anchor(spec.get("a", "screen"), body_a), b_rect=_anchor(spec.get("b", "screen"), body_b))
        elif kind == "pan":
            kw = dict(direction=spec.get("dir", "right"))
        img = transitions.apply(kind, img_a, img_b, p, rng, **kw)
        return post(img, None)
    shot = shot or shot_at(t)
    img, black = render_base(t, index, shot)
    return img if black else post(img, prev)


# ---------------------------------------------------------------- render

def frame_count() -> int:
    return int(round(END_T * FPS))


def _render_segment(args) -> str:
    seg, first, last, out = args
    import build  # noqa: F401  (registers the shots in this worker process)
    enc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
         "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", out],
        stdin=subprocess.PIPE)
    prev, prev_shot = None, None
    for i in range(first, last):
        t = i / FPS
        shot = shot_at(t)
        img = render_frame(t, prev if shot is prev_shot else None, i, shot)
        prev, prev_shot = img, shot
        enc.stdin.write(img.tobytes())
    enc.stdin.close()
    enc.wait()
    return out


def render_video(out: Path, workers: int = 7, t0: float = 0.0, t1: float | None = None, audio: bool = True) -> Path:
    from multiprocessing import Pool
    n0 = int(round(t0 * FPS))
    n1 = int(round((t1 if t1 is not None else END_T) * FPS))
    # split at shot boundaries so the phosphor trail never crosses a segment
    cuts = sorted({n0, n1} | {int(round(s.start * FPS)) for s in SHOTS if n0 < s.start * FPS < n1})
    groups, cur = [], [cuts[0]]
    target = (n1 - n0) / workers
    for cpos in cuts[1:]:
        if cpos - cur[0] >= target or cpos == cuts[-1]:
            cur.append(cpos)
            groups.append((cur[0], cur[-1]))
            cur = [cpos]
        else:
            cur.append(cpos)
    tmp = out.parent / "_segments"
    tmp.mkdir(exist_ok=True)
    jobs = [(k, a, b, str(tmp / f"seg_{k:03d}.mp4")) for k, (a, b) in enumerate(groups) if b > a]
    with Pool(min(workers, len(jobs))) as pool:
        for p in pool.imap_unordered(_render_segment, jobs):
            print("segment done", p, flush=True)
    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{Path(j[3]).name}'\n" for j in jobs), encoding="utf-8")
    silent = tmp / "silent.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy",
                    str(silent)], check=True)
    if not audio:
        silent.replace(out)
        return out
    dur = (n1 - n0) / FPS
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(silent), "-ss", f"{n0 / FPS:.4f}", "-t", f"{dur:.4f}", "-i",
         str(AUDIO), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-af", f"afade=t=in:d=0.02,afade=t=out:st={max(0.0, dur - 0.03):.3f}:d=0.03", "-shortest", str(out)],
        check=True)
    return out
