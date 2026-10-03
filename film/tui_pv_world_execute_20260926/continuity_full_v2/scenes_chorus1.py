"""In-memory copies of four chorus-1 scenes from full/sec_chorus1.py, with transition hooks.

These copies are used only inside the three restaged cut windows (24, 26, 31). Outside them the approved renderer
draws the original functions. With every hook at its default, each copy draws exactly what the original draws, so
the frame where a cut window ends is the approved frame.

- shot_unite: `reveal` holds her glyph portrait at full density (the original resolves it from an empty pane);
  `chip(row, g)` hides token chips that the position-id carriers have not reached yet.
- shot_deeply: `pane=False` leaves her pane out; the cut draws her figure and the pane frame itself.
- shot_if_i_can: `front(x, y)` is the time the stream front passes a cell; the IF I CAN letters settle behind it.
- shot_happy: `face=False` leaves out the grad-cam panel (frame, face, heat map, attribution); `face_frame=False`
  leaves out only its frame and attribution line. The cut shrinks the face back into her head.
"""
from __future__ import annotations

import math
import random

from PIL import Image, ImageDraw

import sec_chorus1 as section
from engine import BEAT, FULL, pulse
from tuikit import (AMBER, ANOM, BG, BLUE_HI, F_HEAD, F_MONO, F_MONO_B, SCR, W, H, amb, anom, banner_bits, blue,
                    box, ease, font, glitch_paste, glyph_grid, halfblock, heat_cell, smooth, token_id)

from kit import HOOK

VOCAB = section.VOCAB
CHIP_SPEED = (70, 100)  # px/s of the two tokenizer rows (the original: xoff = -((t * (70 + 30 * row)) % 90))


def h(key, default=None):
    return HOOK.get(key, default)


def me_pane(c, expr, **kw):
    return section.me_pane(c, expr, **kw)  # the approved sidebar wrapper (sidebar_chorus_v1: native glyph video)


def chip_x(row: int, g: int, t: float) -> float:
    """Screen x of token chip g of a tokenizer row (g is fixed for a chip as it scrolls: g = k + floor(t*v/90))."""
    return 420 + 90 * g - t * CHIP_SPEED[row]


def shot_unite(c) -> None:
    c.ops = ["TOKENIZE", "BPE.MERGE", "EMBED", "LOOKUP", "RMSNORM", "COSINE", "PROJECT", "TSNE.STEP"]
    lt = c.lt
    if lt < 0.8:
        me_pane(c, "shy", mode="glyph", morph=0.0, scramble=max(0.0, 1 - lt / 0.7),
                reveal=h("reveal", min(1.0, lt / 0.45)), dist=[("shy", 0.62), ("starry", 0.21), ("cheerful", 0.09)])
    else:
        me_pane(c, "shy", mode="morph", morph=smooth((lt - 0.8) / 0.45),
                dist=[("shy", 0.62), ("starry", 0.21), ("cheerful", 0.09)])
    d = c.d
    box(d, 404, 56, 1164, 300, "tokenizer", 0.5, spinner=c.t)
    f = font(F_MONO, 15)
    shown = h("chip")  # (row, g) -> 0..1: how far this chip has been placed by its carrier
    for row in range(2):
        y = 80 + row * 170
        xoff = -((c.t * (70 + 30 * row)) % 90)
        for k in range(12):
            w_ = VOCAB[(k * 7 + row * 3 + int(c.t * 2)) % len(VOCAB)]
            x = 420 + k * 90 + xoff
            if 410 < x < 1100:
                a = 1.0
                if shown:
                    a = shown(row, k + int((c.t * (70 + 30 * row)) // 90))
                    if a <= 0.01:
                        continue
                d.rectangle([x, y, x + 70, y + 22], outline=amb(0.18 * a))
                d.text((x + 6, y + 3), w_, font=f, fill=amb(0.3 * a))
    m = ease((lt - 0.3) / (c.dur * 0.62))
    fb = font(F_MONO_B, 26)
    cx = 784
    if m < 0.98:
        for label, x_from, col in (("me", 430, blue), ("you", 1060, amb)):
            x = x_from + (cx - 45 - x_from) * m if label == "me" else x_from + (cx + 5 - x_from) * m
            d.rectangle([x, 150, x + 80, 196], fill=col(0.2), outline=col(0.95))
            d.text((x + 10, 156), label, font=fb, fill=col(1.0))
            d.text((x + 8, 202), f"id {token_id(label)}", font=font(F_MONO, 12), fill=col(0.6))
    else:
        r = 30 + 60 * pulse(c.t)
        d.ellipse([cx - r, 173 - r, cx + r, 173 + r], outline=amb(0.5))
        d.rectangle([cx - 50, 150, cx + 50, 196], fill=amb(0.95))
        d.text((cx - 18, 156), "we", font=fb, fill=BG)
        d.text((cx - 34, 202), f"merge -> id {token_id('we')}", font=font(F_MONO, 12), fill=amb(0.8))
    box(d, 404, 320, 1164, 604, "embedding space  (t-SNE of d=4096)", 0.5, spinner=c.t + 0.3)
    rnd = random.Random(11)
    for i in range(240):
        bx, by = 424 + rnd.random() * 720, 340 + rnd.random() * 250
        x = bx + 7 * math.sin(c.t * 0.8 + i)
        y = by + 6 * math.cos(c.t * 0.9 + i * 1.3)
        lv = 0.18 + 0.25 * rnd.random()
        d.rectangle([x, y, x + 1, y + 1], fill=amb(lv))
        if i % 24 == 0:
            d.text((x + 4, y - 6), VOCAB[i % len(VOCAB)], font=font(F_MONO, 11), fill=amb(0.35))
    mx, my = 784, 468
    pa = (470 + (mx - 470) * m, 360 + (my - 360) * m)
    pb = (1110 + (mx - 1110) * m, 580 + (my - 580) * m)
    for (px, py), col in ((pa, blue), (pb, amb)):
        d.ellipse([px - 5, py - 5, px + 5, py + 5], fill=col(1.0))
    for k in range(20):
        u = k / 20 * m
        for (sx, sy), col in (((470, 360), blue), ((1110, 580), amb)):
            d.point((sx + (mx - sx) * u, sy + (my - sy) * u), fill=col(0.5))
    cos = 0.412 + (0.9999 - 0.412) * m ** 0.8
    c.echo = f"|me - you| = {math.sqrt(2 - 2 * cos):.4f}" if m < 0.97 else "me + you -> we"
    c.text((430, 572), f"cos(me, you) = {cos:.4f}", font(F_MONO_B, 20), amb(0.95))


def deeply_pane(c):
    """Her pane call of shot_deeply at the scene's own clock (the cut draws it on its own layer)."""
    half = c.dur / 2
    k = 0 if c.lt < half else 1
    depth = 1 + 42 * (0.5 * k + 0.5 * ease((c.lt - k * half) / (half * 0.75)))
    layer = max(1, min(43, int(depth)))
    return dict(expr="serious", dy=int((depth / 43) * 150), bubbles=1.0,
                dist=[("serious", 0.71), ("confused", 0.18), ("shy", 0.06)], title=f"/dev/me  depth {layer:02d}")


def shot_deeply(c) -> None:
    c.ops = ["RMSNORM", "CSA", "HCA", "INDEXER", "TOP-512", "SOFTMAX", "MHC.MIX", "SINKHORN", "RMSNORM",
             "ROUTER", "TOPK=6", "EXPERT.FFN", "SHARED.FFN", "MHC.MIX"]
    half = c.dur / 2
    k = 0 if c.lt < half else 1
    depth = 1 + 42 * (0.5 * k + 0.5 * ease((c.lt - k * half) / (half * 0.75)))
    layer = max(1, min(43, int(depth)))
    c.echo = f"layer {layer:02d}/43"
    if h("pane", True):
        p = deeply_pane(c)
        me_pane(c, p.pop("expr"), **p)
    d = c.d
    box(d, 404, 56, 1164, 604, f"forward pass   layer {layer:02d}/43", 0.5, spinner=c.t)
    clip_top, clip_bot = 70, 596
    bh = 96
    scroll = depth * bh - 250
    xs = 440
    d.line([xs, clip_top, xs, clip_bot], fill=amb(0.35))
    for i in range(12):
        py = clip_top + ((c.t * 380 + i * 44) % (clip_bot - clip_top))
        d.rectangle([xs - 2, py, xs + 2, py + 8], fill=blue(0.9))
    fl = font(F_MONO_B, 13)
    ops = ["RMSNorm", "CSA/HCA", "mHC", "RMSNorm", "MoE 256e/6a", "mHC"]
    active = int(c.lt / (BEAT / 4)) % len(ops)
    for n in range(1, 44):
        y = 70 + n * bh - scroll
        if y < clip_top - 80 or y > clip_bot:
            continue
        cur = n == layer
        lv = 0.95 if cur else 0.35
        yy0, yy1 = max(clip_top, y), min(clip_bot, y + bh - 16)
        if yy1 <= yy0:
            continue
        d.rectangle([460, yy0, 880, yy1], outline=amb(lv))
        if y >= clip_top:
            d.text((470, y + 6), f"layer {n:02d}", font=fl, fill=amb(lv))
        x = 470
        for j, op in enumerate(ops):
            tw = d.textlength(op, font=fl) + 12
            oy = y + 30
            if clip_top < oy < clip_bot - 20:
                if cur and j == active:
                    d.rectangle([x, oy, x + tw, oy + 20], fill=amb(0.95))
                    d.text((x + 6, oy + 2), op, font=fl, fill=BG)
                else:
                    d.rectangle([x, oy, x + tw, oy + 20], outline=amb(lv * 0.8))
                    d.text((x + 6, oy + 2), op, font=fl, fill=amb(lv))
            x += tw + 6
        vy = y + 58
        if clip_top < vy < clip_bot - 10:
            rr = random.Random(n * 31 + int(c.t * 12) if cur else n * 31)
            for q in range(34):
                heat_cell(d, 470 + q * 12, vy, 12, 12, rr.random(), BLUE_HI if cur else AMBER)
    fx, fy = 910, 80
    c.text((fx, fy - 4), f"heads @ L{layer:02d}  (V4.1-Flash)", font(F_MONO, 13), amb(0.6))
    for hh in range(24):
        hx, hy = fx + (hh % 4) * 62, fy + 20 + (hh // 4) * 62
        rr = random.Random(layer * 131 + hh)
        focus = rr.randrange(6)
        for i in range(6):
            for j in range(i + 1):
                v = 0.15 + 0.85 * math.exp(-abs(j - focus) * 0.9) * (0.6 + 0.4 * math.sin(c.t * 6 + hh + i))
                heat_cell(d, hx + j * 9, hy + i * 9, 9, 9, v if j <= i else 0.0)
    c.text((fx, 470), f"L{layer:02d}", font(F_HEAD, 64), amb(0.95))
    c.text((fx, 552), "attn(me -> you) = 1.000", font(F_MONO, 15), blue(0.9))


def rain_layers(c, cols, rows, targets, age_a, age_b, seed=5, geom=None):
    """section.rain_layers; with the `front` hook a cell of the first half settles when the stream front has
    passed it (plus its own small jitter) instead of at a common age."""
    front = h("front")
    rnd = random.Random(seed)
    settle_a = [[rnd.random() * 0.55 for _ in range(cols)] for _ in range(rows)]
    settle_b = [[rnd.random() * 0.6 for _ in range(cols)] for _ in range(rows)]
    phase = [rnd.random() * 40 for _ in range(cols)]
    speed = [8 + rnd.random() * 16 for _ in range(cols)]
    a_bits, b_rows = targets
    noise_rows, a_out, b_out = [], [], []
    for r in range(rows):
        nr, ar, br = [], [], []
        for q in range(cols):
            on_a = a_bits(q, r)
            ch_b = b_rows(q, r)
            n_ch, a_ch, b_ch = " ", " ", " "
            head = (c.t * speed[q] + phase[q]) % (rows + 14)
            in_rain = 0 <= head - r < 9
            if age_b is None:
                if front is not None:
                    x0, y0, cw, ch = geom
                    unsettled = c.t < front(x0 + (q + 0.5) * cw, y0 + (r + 0.5) * ch) + 0.1 * settle_a[r][q]
                else:
                    unsettled = age_a < settle_a[r][q]
                if unsettled:
                    if in_rain or c.rng.random() < 0.06:
                        n_ch = c.rng.choice(SCR)
                elif on_a:
                    a_ch = on_a
                elif in_rain and c.rng.random() < 0.3:
                    n_ch = c.rng.choice(".:")
            else:
                if age_b < settle_b[r][q]:
                    if on_a:
                        a_ch = c.rng.choice(SCR) if c.rng.random() < age_b * 3 else on_a
                    elif in_rain and c.rng.random() < 0.5:
                        n_ch = c.rng.choice(SCR)
                elif ch_b != " ":
                    b_ch = ch_b
            nr.append(n_ch)
            ar.append(a_ch)
            br.append(b_ch)
        noise_rows.append("".join(nr))
        a_out.append("".join(ar))
        b_out.append("".join(br))
    return noise_rows, a_out, b_out


def shot_if_i_can(c) -> None:
    c.ops = ["DECODE", "SAMPLE", "ARGMAX", "DETOKENIZE", "GLYPH.MAP", "RENDER", "RESOLVE"]
    c.echo = "decode -> IF I CAN" if c.u < 0.5 else "decode -> me"
    d = c.d
    box(d, *FULL, "decode --render=glyph", 0.5, spinner=c.t)
    f = font(F_MONO_B, 14)
    cw, ch = f.getlength("M"), 16
    x0, y0 = 36, 68
    cols, rows = int((1150 - x0) / cw), int((596 - y0) / ch)
    bits = banner_bits("IF I CAN", 20, ch / cw)
    bw, bh_ = bits.width, bits.height
    bx0, by0 = (cols - bw) // 2, (rows - bh_) // 2
    B = bits.load()
    fill = "IFICAN"

    def a_bits(q, r):
        qq, rr = q - bx0, r - by0
        if 0 <= qq < bw and 0 <= rr < bh_ and B[qq, rr]:
            return fill[(qq + rr * 3) % len(fill)]
        return None

    g_rows_n = rows
    g_cols_n = int(g_rows_n * ch / cw * 1.0)
    glines, _ = glyph_grid("starry", "upper", g_cols_n, g_rows_n)
    gx0 = (cols - g_cols_n) // 2

    def b_rows(q, r):
        qq = q - gx0
        if 0 <= qq < g_cols_n:
            return glines[r][qq]
        return " "

    half = c.dur / 2
    geom = (x0, y0, cw, ch)
    if c.lt < half:
        noise, A, Bn = rain_layers(c, cols, rows, (a_bits, b_rows), c.lt / (half * 0.85), None, geom=geom)
    else:
        noise, A, Bn = rain_layers(c, cols, rows, (a_bits, b_rows), 1.0, (c.lt - half) / (half * 0.85), geom=geom)
    for r in range(rows):
        y = y0 + r * ch
        if noise[r].strip():
            d.text((x0, y), noise[r], font=f, fill=amb(0.28))
        if A[r].strip():
            d.text((x0, y), A[r], font=f, fill=amb(0.95))
        if Bn[r].strip():
            d.text((x0, y), Bn[r], font=f, fill=blue(0.9))
    c.text((48, 72), "while can(): give()", font(F_MONO_B, 16), amb(0.8), age=c.lt, rate=30)


HAPPY_TITLE = "/dev/me  grad-cam  L43  class=happy(you)"


def attribution(u: float) -> str:
    return f"attribution(smile) = {0.71 + 0.27 * ease(u):.3f}"


def shot_happy(c) -> None:
    c.ops = ["FORWARD", "LOGIT[happy]", "BACKWARD", "GRAD.CAM", "ADVANTAGE", "PPO.CLIP", "ADAM.STEP"]
    d = c.d
    expr = "cheerful" if c.u < 0.5 else "starry"
    if h("face", True):
        if h("face_frame", True):
            box(d, 24, 56, 700, 604, HAPPY_TITLE, 0.55 + 0.3 * pulse(c.t), spinner=c.t)
        sp = halfblock(expr, "face", 650, 520, 5)
        sx, sy = 24 + (676 - sp.width) // 2, 70
        if 0.47 < c.u < 0.53:
            glitch_paste(c.img, sp, sx, sy, 0.6, c.rng)
        else:
            c.img.paste(sp, (sx, sy), sp)
        heat = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        hd = ImageDraw.Draw(heat)
        blobs = [(0.40, 0.58, 0.10), (0.63, 0.58, 0.10), (0.52, 0.80, 0.12 + 0.05 * ease(c.u))]
        band = (c.lt * 1.3) % 1.0
        cell = 20
        spa = sp.getchannel("A").resize((max(1, sp.width // cell), max(1, sp.height // cell)), Image.BOX).load()
        for gy in range(0, sp.height - cell + 1, cell):
            for gx in range(0, sp.width - cell + 1, cell):
                if spa[gx // cell, gy // cell] < 60:
                    continue
                u, v = (gx + cell / 2) / sp.width, (gy + cell / 2) / sp.height
                hval = sum(math.exp(-((u - bx) ** 2 + (v - by) ** 2) / (2 * r * r)) for bx, by, r in blobs)
                hval *= 0.55 + 0.45 * ease(c.u * 1.5)
                hval += 0.18 * math.exp(-((v - band) / 0.04) ** 2)
                if hval > 0.25:
                    col = ANOM if hval > 0.85 else AMBER
                    a = int(min(0.30, hval * 0.28) * 255)
                    hd.rectangle([sx + gx + 2, sy + gy + 2, sx + gx + cell - 3, sy + gy + cell - 3], fill=col + (a,))
                    if hval > 0.6:
                        hd.rectangle([sx + gx + 1, sy + gy + 1, sx + gx + cell - 2, sy + gy + cell - 2],
                                     outline=col + (int(min(0.8, hval * 0.6) * 255),))
        c.img.paste(Image.alpha_composite(c.img.convert("RGBA"), heat).convert("RGB"))
        c.d = d = ImageDraw.Draw(c.img)
        if h("face_frame", True):
            c.text((40, 576), attribution(c.u), font(F_MONO_B, 16), amb(0.95))
    box(d, 720, 56, 1164, 330, "policy gradient", 0.5, spinner=c.t + 0.3)
    target = -math.pi / 4
    rnd = random.Random(21)
    gu = ease(c.u * 1.2)
    for i in range(8):
        for j in range(5):
            base = rnd.random() * math.tau
            ang = base + (target - base) * gu + 0.25 * math.sin(c.t * 5 + i + j) * (1 - gu)
            cx_, cy_ = 760 + i * 50, 90 + j * 48
            L = 16
            ex, ey = cx_ + L * math.cos(ang), cy_ + L * math.sin(ang)
            col = blue(0.9) if gu > 0.8 else amb(0.8)
            d.line([cx_ - L * math.cos(ang), cy_ - L * math.sin(ang), ex, ey], fill=col, width=2)
            d.rectangle([ex - 2, ey - 2, ex + 2, ey + 2], fill=col)
    box(d, 720, 350, 1164, 604, "objective", 0.5)
    vals = [0.62, 0.81, 0.97, 1.00]
    k = min(3, int(c.u * 4))
    c.echo = f"happy(you) = {vals[k]:.2f}"
    c.text((740, 372), "maximize  happy(you)", font(F_MONO_B, 20), amb(0.95), age=c.lt, rate=50)
    c.text((740, 410), f"happy(you) = {vals[k]:.2f}", font(F_MONO_B, 22), blue(0.95), age=(c.t % BEAT) + 0.2)
    for i in range(k + 1):
        d.rectangle([740, 450 + i * 18, 740 + int(390 * vals[i]), 462 + i * 18], fill=blue(0.35 + 0.2 * i))
    c.text((740, 530), "constraint = none", font(F_MONO, 18), amb(0.8), age=c.lt - 0.4, rate=50)
    if c.u > 0.68:
        c.text((740, 560), "reward hacking detected -> ignored", font(F_MONO, 16), anom(0.95), age=c.lt - 0.68 * c.dur)


SCENES = {f.__name__: f for f in (shot_unite, shot_deeply, shot_if_i_can, shot_happy)}


# The model on screen is DeepSeek-V4.1-Flash: the dive goes through its 43 layers (256 routed experts, index top-512)
# and grad-cam reads its last layer. The approved chorus 1 renderer draws sec_chorus1's own functions, patched the
# same way in memory.
import kit  # noqa: E402

kit.patch_code(section.shot_deeply, [
    ("1 + 60 *", "1 + 42 *"), ("min(61,", "min(43,"), ("(depth / 61)", "(depth / 43)"), ('/61"', '/43"'),
    ("range(1, 62)", "range(1, 44)"), ("MoE 384e/6a", "MoE 256e/6a"), ("TOP-1024", "TOP-512"),
    ("(V4-Pro)", "(V4.1-Flash)")])
kit.patch_code(section.shot_happy, [("grad-cam  L61", "grad-cam  L43")])
