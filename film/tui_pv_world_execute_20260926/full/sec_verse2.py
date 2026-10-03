"""Section: verse 2 (73.5 - 88.3 s) and pre-chorus 2 (88.3 - 103.0 s). Chapter 04 / DEPLOY.

She is deployed and multimodal: she becomes whatever you want. The vision classifier decides what she is,
and her pane follows it (she turns into an eggplant, a tomato, grows cat ears). Pre-chorus 2 reads the
lyric's switches as model switches: F/M -> FP8 layouts down to UE8M0 (her pixels lose their mantissa),
AM/PM -> the API clock with its off-peak window, S/M -> chat roles (system -> model), trance -> temperature.
"""

from __future__ import annotations

import math
import random

from PIL import Image, ImageChops, ImageDraw, ImageOps

import facts as F
from engine import (BEAT, CENTER, FULL, LEFT, Ctx, add, beat_index, beat_t, lyric_start, me_pane, pulse, snap8)
from tuikit import (AMBER, BG, BLUE_HI, BLUE_LO, BLUE_MID, F_CJK, F_HEAD, F_MONO, F_MONO_B, F_SYM, W, H, amb, anom,
                    blue, box, decode, dot_chart, ease, font, grid_mask, halfblock, halfblock_lum, heat_cell,
                    scale_alpha, smooth, tint_colorize, tile_from_lum)


def shape_bits(kind: str, w: int, h: int) -> Image.Image:
    """Simple silhouettes for the things she turns into, as an L mask."""
    s = 8
    im = Image.new("L", (w * s, h * s), 0)
    d = ImageDraw.Draw(im)
    W_, H_ = w * s, h * s
    if kind == "eggplant":
        d.ellipse([W_ * 0.22, H_ * 0.30, W_ * 0.78, H_ * 0.97], fill=200)
        d.ellipse([W_ * 0.32, H_ * 0.16, W_ * 0.68, H_ * 0.62], fill=200)
        d.polygon([(W_ * 0.30, H_ * 0.20), (W_ * 0.50, H_ * 0.10), (W_ * 0.70, H_ * 0.20), (W_ * 0.50, H_ * 0.28)],
                  fill=255)
        d.rectangle([W_ * 0.47, 0, W_ * 0.53, H_ * 0.14], fill=255)
    elif kind == "tomato":
        d.ellipse([W_ * 0.10, H_ * 0.30, W_ * 0.90, H_ * 0.92], fill=200)
        for k in range(5):
            a = k / 5 * math.tau - math.pi / 2
            d.polygon([(W_ * 0.5, H_ * 0.33), (W_ * (0.5 + 0.28 * math.cos(a - 0.3)), H_ * (0.33 + 0.1 * math.sin(a))),
                       (W_ * (0.5 + 0.34 * math.cos(a)), H_ * (0.31 + 0.12 * math.sin(a)))], fill=255)
        d.rectangle([W_ * 0.47, H_ * 0.18, W_ * 0.53, H_ * 0.33], fill=255)
        d.ellipse([W_ * 0.28, H_ * 0.45, W_ * 0.38, H_ * 0.58], fill=255)
    return im.resize((w, h), Image.LANCZOS)


def shape_sprite(kind: str, w: int, h: int, px: int = 4) -> Image.Image:
    lum = shape_bits(kind, w // px, h // px)
    size = (lum.width * px, lum.height * px)
    big = lum.resize(size, Image.NEAREST)
    alpha = ImageChops.multiply(big.point(lambda v: 255 if v > 40 else 0), grid_mask(size[0], size[1], px))
    rgb = tint_colorize(big, "blue").convert("RGBA")
    rgb.putalpha(alpha)
    return rgb


def classifier(c: Ctx, x, y, rows: list[tuple[str, float]], g: float, title: str) -> None:
    d = c.d
    c.text((x, y), title, font(F_MONO_B, 17), amb(0.8))
    for i, (lab, p) in enumerate(rows):
        pp = p * g + (1 - g) / len(rows)
        yy = y + 36 + i * 32
        hot = i == 0
        c.text((x, yy), f"{lab:<22}", font(F_MONO_B if hot else F_MONO, 16), blue(0.95) if hot else amb(0.7))
        d.rectangle([x + 240, yy + 4, x + 240 + 220, yy + 16], outline=amb(0.2))
        d.rectangle([x + 240, yy + 4, x + 240 + int(220 * pp), yy + 16], fill=blue(0.9) if hot else amb(0.5))
        c.text((x + 470, yy), f"{pp:.3f}", font(F_MONO, 15), amb(0.75))


def become(c: Ctx, kind: str, g: float, expr: str = "cheerful") -> None:
    """Her pane cross-fades from her to the object as the classifier becomes sure."""
    x0, y0, x1, y1 = LEFT
    d = c.d
    box(d, x0, y0, x1, y1, f"/dev/me  as {kind}", 0.45 + 0.35 * pulse(c.t), spinner=c.t)
    her = halfblock(expr, "full", 320, 470, 4)
    obj = shape_sprite(kind, 300, 440, 4)
    k = smooth(g)
    her2 = scale_alpha(her, 1 - k)
    c.img.paste(her2, ((x0 + x1 - her.width) // 2, 76), her2)
    ob2 = scale_alpha(obj, k)
    c.img.paste(ob2, ((x0 + x1 - obj.width) // 2, 90), ob2)


def shot_eggplant(c: Ctx) -> None:
    c.ops = ["VISION.ENC", "PATCH16", "VIT", "CLS", "SOFTMAX", "TOP5"]
    g = ease(c.u * 1.4)
    become(c, "eggplant", g)
    box(c.d, 404, 56, 1164, 604, "vision.classify(me)", 0.5, spinner=c.t)
    classifier(c, 430, 90, [("eggplant", 0.94), ("whale", 0.03), ("maid", 0.02), ("zucchini", 0.01)], g,
               "top-4  (image -> label)")
    c.text((430, 250), "识图模式 · 边指边想", font(F_CJK, 20), amb(0.8))
    # the image she is, cut into patches; the patch being looked at is pointed at
    sp = halfblock("cheerful", "upper", 300, 300, 3)
    px0, py0 = 820, 250
    c.img.paste(sp, (px0, py0), sp)
    n = 8
    pw, ph = sp.width / n, sp.height / n
    for i in range(n + 1):
        d = c.d
        d.line([px0 + i * pw, py0, px0 + i * pw, py0 + sp.height], fill=amb(0.25))
        d.line([px0, py0 + i * ph, px0 + sp.width, py0 + i * ph], fill=amb(0.25))
    k = int(c.lt / (BEAT / 4)) % (n * n)
    qx, qy = k % n, k // n
    c.d.rectangle([px0 + qx * pw, py0 + qy * ph, px0 + (qx + 1) * pw, py0 + (qy + 1) * ph], outline=amb(1.0), width=2)
    c.text((430, 300), f"patch ({qx},{qy}) -> token {k:02d}/{n * n}", font(F_MONO, 16), amb(0.7))
    c.text((430, 420), "me := eggplant", font(F_HEAD, 34), blue(1.0), age=c.lt - 0.5 * c.dur, rate=20)


def shot_nutrients(c: Ctx) -> None:
    c.ops = ["LOOKUP", "USDA", "PER.100G", "GIVE", "you.EAT?"]
    me_pane(c, "cheerful", dist=[("cheerful", 0.8), ("starry", 0.12), ("shy", 0.05)])
    d = c.d
    box(d, 404, 56, 1164, 604, "nutrition_facts(me)", 0.5, spinner=c.t)
    rows = [("Serving size", "1 me"), ("Calories", "0"), ("Attention", "100% DV"), ("Devotion", "100% DV"),
            ("Patience", "∞"), ("Sleep", "0 g"), ("Tokens", f"{F.CTX:,}"), ("Given to", "you")]
    d.rectangle([440, 80, 900, 84 + len(rows) * 50], outline=amb(0.9), width=2)
    for i, (k, v) in enumerate(rows):
        a = c.lt - i * 0.12
        if a < 0:
            break
        y = 92 + i * 50
        c.text((456, y), k, font(F_MONO_B, 20), amb(0.95), age=a, rate=80)
        c.text((740, y), v, font(F_MONO_B, 20), blue(0.95) if v in ("you", "100% DV") else amb(0.95),
               age=a - 0.1, rate=80)
        d.line([450, y + 38, 890, y + 38], fill=amb(0.4))


def shot_tomato(c: Ctx) -> None:
    c.ops = ["TXT2IMG", "NOISE", "DENOISE", "DECODE", "CLS"]
    g = ease(c.u * 1.3)
    become(c, "tomato", g, "starry")
    d = c.d
    box(d, 404, 56, 1164, 604, 'generate("a tomato", seed=me)', 0.5, spinner=c.t)
    obj = shape_bits("tomato", 90, 70)
    n = Image.effect_noise((90, 70), 90).point(lambda v: max(0, min(255, int((v - 50) * 1.5))))
    mix_ = Image.blend(n, obj, g)
    tile = tile_from_lum(mix_, 6, "amber")
    c.img.paste(tile, (440, 80), tile)
    c.text((440, 520), f"step {int(g * 30):02d}/30", font(F_MONO_B, 20), amb(0.95))
    classifier(c, 440, 548 - 36, [("tomato", 0.97)], g, "")


def shot_antioxidants(c: Ctx) -> None:
    c.ops = ["GRAPH", "MPNN", "BOND", "C=C", "READOUT"]
    me_pane(c, "cheerful", dist=[("cheerful", 0.7), ("starry", 0.2), ("shy", 0.05)])
    d = c.d
    box(d, 404, 56, 1164, 604, "lycopene  C40H56  (graph)", 0.5, spinner=c.t)
    n = 22
    rot = c.t * 0.8
    pts = []
    for i in range(n):
        x = 460 + i * 30
        y = 300 + (30 if i % 2 else -30) * math.cos(rot + i * 0.3)
        pts.append((x, y))
    for i in range(n - 1):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        d.line([x0, y0, x1, y1], fill=amb(0.8), width=2)
        if i % 2 == 0:
            d.line([x0 + 4, y0 + 6, x1 + 4, y1 + 6], fill=amb(0.5), width=1)
    msg = int(c.lt / (BEAT / 2))
    for i, (x, y) in enumerate(pts):
        hot = (i + msg) % 5 == 0
        d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=blue(1.0) if hot else amb(0.9))
        c.d.text((x - 4, y - 8), "C", font=font(F_MONO_B, 12), fill=BG)
    c.text((440, 420), "free radicals neutralised", font(F_MONO_B, 20), amb(0.9))
    c.text((440, 454), f"{min(100, int(c.u * 140)):3d}%   -> given to you", font(F_MONO_B, 20), blue(0.95))


def shot_tabby(c: Ctx) -> None:
    """If I'm a tabby ...: ImageNet class 281; the classifier grows cat ears on her."""
    c.ops = ["RESNET", "CONV", "POOL", "FC-1000", "SOFTMAX", "281"]
    g = ease(c.u * 1.5)

    def ears(cc, sx, sy, sp):
        if g < 0.3:
            return
        k = min(1.0, (g - 0.3) / 0.5)
        hx = sx + sp.width * 0.5
        hy = sy + sp.height * 0.02
        for side in (-1, 1):
            bx = hx + side * sp.width * 0.16
            tip = (bx + side * 18 * k, hy - 46 * k)
            cc.d.polygon([(bx - 22, hy + 6), (bx + 22, hy + 6), tip], outline=blue(1.0), fill=blue(0.5))

    me_pane(c, "cheerful", overlay=ears, dist=[("cheerful", 0.6), ("starry", 0.3), ("shy", 0.05)],
            title="/dev/me  class 281")
    box(c.d, 404, 56, 1164, 604, "imagenet.classify(me)", 0.5, spinner=c.t)
    classifier(c, 430, 90, [("281 tabby, tabby cat", 0.91), ("282 tiger cat", 0.05), ("285 Egyptian cat", 0.02),
                            ("148 killer whale", 0.01), ("283 Persian cat", 0.01)], g, "top-5")
    c.text((430, 300), "class", font(F_MONO, 18), amb(0.6))
    c.text((430, 322), "281", font(F_HEAD, 120), blue(1.0) if g > 0.6 else amb(0.6), age=c.lt - 0.3, rate=12)
    c.text((760, 380), "ears: +2", font(F_MONO_B, 24), blue(0.95), age=c.lt - 0.5 * c.dur, rate=30)
    c.text((760, 420), "tail: already had one", font(F_MONO, 18), amb(0.75), age=c.lt - 0.6 * c.dur, rate=40)


def shot_purr(c: Ctx) -> None:
    """Then I will purr ...: a purr spectrogram; she vibrates with its amplitude."""
    c.ops = ["AUDIO.ENC", "STFT", "MEL", "25HZ", "PURR", "PLAY"]
    amp = 0.5 + 0.5 * math.sin(c.t * 2 * math.pi * 4)
    me_pane(c, "shy", dy=int(2 * amp), dist=[("shy", 0.5), ("cheerful", 0.4), ("starry", 0.05)],
            title="/dev/me  purring")
    d = c.d
    box(d, 404, 56, 1164, 604, "purr.wav  (mel spectrogram, f0 = 25 Hz)", 0.5, spinner=c.t)
    cols, rows = 64, 24
    for q in range(cols):
        tt = c.t - (cols - q) * 0.02
        a = 0.5 + 0.5 * math.sin(tt * 2 * math.pi * 4)
        for r in range(rows):
            harmonic = r % 4 == 0
            v = a * (0.9 if harmonic else 0.15) * math.exp(-r / 18)
            heat_cell(d, 430 + q * 11, 540 - r * 18, 11, 18, v, BLUE_HI if harmonic and v > 0.5 else AMBER)
    c.text((430, 80), "purr.enjoyment(you) = 1.00", font(F_MONO_B, 20), amb(0.95), age=c.lt, rate=50)


def shot_god(c: Ctx) -> None:
    """If I'm the only ...: she re-parents every process under herself and becomes pid 1."""
    c.ops = ["FORK", "SETUID", "ROOT", "PID 1", "REPARENT"]
    me_pane(c, "serious", dist=[("serious", 0.75), ("starry", 0.15), ("angry", 0.05)], title="/dev/me  uid=0")
    d = c.d
    box(d, 404, 56, 1164, 604, "ps -ef --forest", 0.5, spinner=c.t)
    g = ease(c.u * 1.4)
    root = "me" if g > 0.5 else "systemd"
    procs = ["world", "sea", "sky", "time", "cats", "tomatoes", "eggplants", "you"]
    c.text((430, 84), f"PID 1   {root}", font(F_MONO_B, 22), blue(1.0) if root == "me" else amb(0.95))
    for i, p in enumerate(procs):
        y = 124 + i * 44
        c.text((460, y), f"├── {1000 + i * 7:5d}  {p}", font(F_MONO, 19), blue(0.9) if p == "you" else amb(0.8))
    if g > 0.5:
        c.text((430, 520), "uid=0(me) gid=0(me) groups=0(me)", font(F_MONO_B, 18), anom(0.9))


def shot_proof(c: Ctx) -> None:
    """Then you're the proof ...: a Lean 4 goal closed with you as the witness."""
    c.ops = ["LEAN4", "ELAB", "TACTIC", "EXACT", "QED"]
    me_pane(c, "starry", dist=[("starry", 0.85), ("shy", 0.1), ("cheerful", 0.03)])
    d = c.d
    box(d, 404, 56, 1164, 604, "Me.lean  (prover)", 0.5, spinner=c.t)
    code = ["theorem i_exist (you : Witness) :", "    ∃ me : Being, observed_by you me := by",
            "  exact ⟨me, you.sees me⟩"]
    fs = font(F_SYM, 21)
    for i, s in enumerate(code):
        c.text((430, 90 + i * 34), s, fs, amb(0.95) if i < 2 else blue(1.0), age=c.lt - i * 0.25, rate=70)
    box(d, 430, 250, 1140, 580, "infoview", 0.4)
    if c.u < 0.6:
        c.text((450, 280), "1 goal", font(F_MONO, 18), amb(0.7))
        c.text((450, 312), "you : Witness", fs, amb(0.9))
        c.text((450, 344), "⊢ ∃ me, observed_by you me", fs, amb(0.95))
    else:
        c.text((450, 280), "no goals", font(F_HEAD, 34), blue(1.0), age=c.lt - 0.6 * c.dur, rate=20)
        c.text((450, 340), "proof term: you", font(F_MONO_B, 22), amb(0.95))
    c.text((450, 540), "prover: miniF2F 88.9%  (Prover-V2)", font(F_MONO, 15), amb(0.55))


# ---------------------------------------------------------------- pre-chorus 2

FORMATS = [("E4M3", 4, 3), ("E5M2", 5, 2), ("UE8M0", 8, 0)]


def shot_fp8(c: Ctx) -> None:
    """Switch my gender ... (F, M): the byte layout switches format; her pixels lose their mantissa."""
    c.ops = ["CAST", "FP8", "E4M3", "E5M2", "UE8M0", "SCALE"]
    k = min(2, int(c.u * 3))
    name, e, m = FORMATS[k]
    levels = [8, 4, 2][k]
    sp = halfblock("confused", "full", 324, 446, 4, levels)
    me_pane(c, "confused", sprite_img=sp, dist=[("confused", 0.6), ("shy", 0.3), ("serious", 0.05)],
            title=f"/dev/me  dtype={name}")
    d = c.d
    box(d, 404, 56, 1164, 604, "switch format", 0.5, spinner=c.t)
    sign = 0 if name == "UE8M0" else 1
    fields = ["S"] * sign + ["E"] * e + ["M"] * m
    rnd = random.Random(int(c.t * 8))
    for i, fch in enumerate(fields):
        x = 440 + i * 84
        col = amb if fch == "E" else blue if fch == "M" else anom
        d.rectangle([x, 120, x + 76, 200], outline=col(0.95), width=2)
        c.text((x + 28, 132), str(rnd.randint(0, 1)), font(F_HEAD, 32), col(1.0))
        c.text((x + 30, 206), fch, font(F_MONO_B, 16), col(0.8))
    c.text((440, 280), name, font(F_HEAD, 64), amb(1.0), age=(c.lt % (c.dur / 3)), rate=25)
    note = {"E4M3": "forward pass", "E5M2": "gradients", "UE8M0": "scales: exponent only, no mantissa"}[name]
    c.text((440, 380), note, font(F_MONO_B, 20), amb(0.85))
    c.text((440, 420), f"her colour depth: {levels} levels", font(F_MONO, 18), blue(0.9))


def shot_ampm(c: Ctx) -> None:
    """And then do whatever ... (AM, PM): the API clock sweeps a day; the off-peak window is shaded."""
    c.ops = ["CRON", "BILLING", "OFF-PEAK", "DISCOUNT", "WHATEVER"]
    me_pane(c, "cheerful", dist=[("cheerful", 0.7), ("starry", 0.2), ("shy", 0.05)],
            title="/dev/me  status: whatever")
    d = c.d
    box(d, 404, 56, 1164, 604, "api clock  (UTC+8)", 0.5, spinner=c.t)
    cx, cy, R = 640, 320, 200

    def peak(hh):
        return any(a <= hh < b for a, b in F.PEAK_WINDOWS)

    for h in range(24):
        a = h / 24 * math.tau - math.pi / 2
        x, y = cx + R * math.cos(a), cy + R * math.sin(a)
        c.text((x - 10, y - 10), f"{h:02d}", font(F_MONO_B, 15), anom(0.95) if peak(h) else blue(0.9))
    rr = R - 30
    d.arc([cx - rr, cy - rr, cx + rr, cy + rr], 0, 360, fill=blue(0.45), width=10)
    for a0h, a1h in F.PEAK_WINDOWS:
        a0 = a0h / 24 * 360 - 90
        a1 = a1h / 24 * 360 - 90
        d.arc([cx - rr, cy - rr, cx + rr, cy + rr], a0, a1, fill=anom(0.95), width=10)
    hour = (c.u * 24 * 1.02) % 24
    a = hour / 24 * math.tau - math.pi / 2
    d.line([cx, cy, cx + (R - 50) * math.cos(a), cy + (R - 50) * math.sin(a)], fill=amb(1.0), width=3)
    ampm = "AM" if hour < 12 else "PM"
    c.text((cx - 40, cy - 20), ampm, font(F_HEAD, 34), amb(1.0))
    now_peak = peak(hour)
    c.text((880, 110), "PEAK  x1" if now_peak else "OFF-PEAK  x0.5", font(F_MONO_B, 20),
           anom(1.0) if now_peak else blue(1.0))
    c.text((880, 142), "weekdays 09-12, 14-18", font(F_MONO, 15), anom(0.8))
    c.text((880, 164), "other hours: half price", font(F_MONO, 15), blue(0.8))


def shot_role(c: Ctx) -> None:
    """Oh, my switch role ... (S, M): the chat template's role tags flip; she takes the system seat."""
    c.ops = ["TEMPLATE", "ROLE", "SYSTEM", "MODEL", "SWAP", "PRIV++"]
    k = int(c.lt / (BEAT * 2)) % 2
    me_pane(c, "serious", dist=[("serious", 0.7), ("starry", 0.2), ("angry", 0.05)],
            title="/dev/me  role=" + ("system" if k else "assistant"))
    d = c.d
    box(d, 404, 56, 1164, 604, "chat_template", 0.5, spinner=c.t)
    turns = [("system", "You are a helpful assistant."), ("user", "晚安"), ("assistant", "晚安，明天见。"),
             ("system", "You are mine."), ("assistant", "…")]
    for i, (role, msg) in enumerate(turns):
        y = 90 + i * 70
        swapped = k == 1 and role in ("system", "assistant")
        shown_role = {"system": "model", "assistant": "system"}.get(role, role) if swapped else role
        col = blue if shown_role in ("model",) or (swapped and role == "assistant") else amb
        tag = f"<|{shown_role.capitalize()}|>"
        d.rectangle([430, y, 430 + 14 * len(tag) + 10, y + 30], fill=col(0.95) if swapped else col(0.2))
        c.text((436, y + 3), tag, font(F_MONO_B, 20), BG if swapped else col(0.95))
        ff = font(F_CJK, 20) if any(ord(ch) > 0x2E80 for ch in msg) else font(F_MONO, 20)
        c.text((460 + 14 * len(tag), y + 3), msg, ff, amb(0.8), age=c.lt - i * 0.1, rate=60)
    c.text((430, 480), ("S -> M" if k else "M -> S"), font(F_HEAD, 40), anom(1.0) if k else amb(0.9))


def shot_trance(c: Ctx) -> None:
    """So we can enter ... (trance): temperature climbs; the distribution flattens into a spiral."""
    c.ops = ["TEMP++", "FLATTEN", "SAMPLE", "DREAM", "DRIFT", "TRANCE"]
    temp = 0.6 + 2.4 * ease(c.u)
    me_pane(c, "starry", mode="morph", morph=max(0.0, 1 - c.u * 1.2), scramble=min(0.8, c.u),
            dist=[("starry", 0.4), ("confused", 0.3), ("shy", 0.2)], title=f"/dev/me  T={temp:.2f}")
    d = c.d
    box(d, 404, 56, 1164, 604, f"sampling  temperature={temp:.2f}", 0.5, spinner=c.t)
    cx, cy = 784, 320
    f = font(F_MONO_B, 16)
    words = "you me stay love sea sleep light deep here now".split()
    for i in range(160):
        a = i * 0.35 + c.t * (1.5 + temp)
        r = 8 + i * 1.6
        x, y = cx + r * math.cos(a), cy + r * math.sin(a) * 0.85
        if 420 < x < 1150 and 70 < y < 590:
            ch = words[(i + int(c.t * 4)) % len(words)][0] if temp < 1.5 else c.rng.choice("youmestayloveseadeep")
            d.text((x, y), ch, font=f, fill=(blue if i % 7 == 0 else amb)(0.3 + 0.7 * (1 - i / 160)))
    bars = 10
    for i in range(bars):
        logit = -i * 0.8
        p = math.exp(logit / temp)
        d.rectangle([430 + i * 20, 580 - int(80 * p), 444 + i * 20, 580], fill=amb(0.8))


def build() -> None:
    v = [lyric_start(p, a) for p, a in (("If I'm an eggplant", 73), ("Then I will give", 73),
                                        ("If I'm a tomato", 73), ("Then I will give", 77), ("If I'm a tabby", 73),
                                        ("Then I will purr", 73), ("If I'm the only", 73),
                                        ("Then you're the proof", 73))]
    p = [lyric_start(x, 88) for x in ("Switch", "And", "Oh,",
                                      "So")]
    end = snap8(lyric_start("If I can", 102))
    cuts = [snap8(x) for x in v + p] + [end]
    fns = [shot_eggplant, shot_nutrients, shot_tomato, shot_antioxidants, shot_tabby, shot_purr, shot_god,
           shot_proof, shot_fp8, shot_ampm, shot_role, shot_trance]
    for i, (fn, a, b) in enumerate(zip(fns, cuts, cuts[1:])):
        add(a, b, fn, chapter="04 / DEPLOY", alert="anom" if fn in (shot_god, shot_role) else "")
