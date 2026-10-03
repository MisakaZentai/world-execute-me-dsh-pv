"""Section: pre-chorus 1 tail + chorus 1 (54.2 s - 73.5 s). Ported unchanged from sample v2 (owner-approved)."""

from __future__ import annotations

import math
import random

from PIL import Image, ImageDraw

from engine import (BEAT, FULL, LEFT, LYRICS, Ctx, add, beat_index, beat_t, me_pane, pulse, snap8)
from tuikit import (AMBER, ANOM, BG, BLUE_HI, EXPRS, F_CJK, F_HEAD, F_MONO, F_MONO_B, RED, SCR, W, H, amb, anom,
                    banner_bits, banner_block, blue, box, conv_maps, decode, dot_chart, ease, font, glitch_paste,
                    glyph_grid, halfblock, halfblock_lum, heat_cell, red, scale_alpha, smooth, tile_from_lum,
                    token_id)

VOCAB = ["the", "sim", "love", "you", "run", "void", "world", "tangent", "cat", "exec", "only", "me", "deep", "sine",
         "limit", "point", "circle", "stay", "free", "god", "prove", "whale", "sea", "light", "happy"]


def shot_unite(c: Ctx) -> None:
    """And we can unite: 'me' and 'you' fuse into the token 'we'; their embeddings converge."""
    c.ops = ["TOKENIZE", "BPE.MERGE", "EMBED", "LOOKUP", "RMSNORM", "COSINE", "PROJECT", "TSNE.STEP"]
    lt = c.lt
    if lt < 0.8:
        me_pane(c, "shy", mode="glyph", morph=0.0, scramble=max(0.0, 1 - lt / 0.7), reveal=min(1.0, lt / 0.45),
                dist=[("shy", 0.62), ("starry", 0.21), ("cheerful", 0.09)])
    else:
        me_pane(c, "shy", mode="morph", morph=smooth((lt - 0.8) / 0.45),
                dist=[("shy", 0.62), ("starry", 0.21), ("cheerful", 0.09)])
    d = c.d
    box(d, 404, 56, 1164, 300, "tokenizer", 0.5, spinner=c.t)
    f = font(F_MONO, 15)
    for row in range(2):
        y = 80 + row * 170
        xoff = -((c.t * (70 + 30 * row)) % 90)
        for k in range(12):
            w_ = VOCAB[(k * 7 + row * 3 + int(c.t * 2)) % len(VOCAB)]
            x = 420 + k * 90 + xoff
            if 410 < x < 1100:
                d.rectangle([x, y, x + 70, y + 22], outline=amb(0.18))
                d.text((x + 6, y + 3), w_, font=f, fill=amb(0.3))
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
    # the panel shows the cosine; the echo under her shows the same closing-in as a distance
    c.echo = f"|me - you| = {math.sqrt(2 - 2 * cos):.4f}" if m < 0.97 else "me + you -> we"
    c.text((430, 572), f"cos(me, you) = {cos:.4f}", font(F_MONO_B, 20), amb(0.95))


def shot_deeply(c: Ctx) -> None:
    """So deeply, so deeply: a forward pass through all 61 layers; she sinks as it goes deeper."""
    c.ops = ["RMSNORM", "CSA", "HCA", "INDEXER", "TOP-1024", "SOFTMAX", "MHC.MIX", "SINKHORN", "RMSNORM",
             "ROUTER", "TOPK=6", "EXPERT.FFN", "SHARED.FFN", "MHC.MIX"]
    half = c.dur / 2
    k = 0 if c.lt < half else 1
    depth = 1 + 60 * (0.5 * k + 0.5 * ease((c.lt - k * half) / (half * 0.75)))
    layer = max(1, min(61, int(depth)))
    c.echo = f"layer {layer:02d}/61"
    me_pane(c, "serious", dy=int((depth / 61) * 150), bubbles=1.0,
            dist=[("serious", 0.71), ("confused", 0.18), ("shy", 0.06)], title=f"/dev/me  depth {layer:02d}")
    d = c.d
    box(d, 404, 56, 1164, 604, f"forward pass   layer {layer:02d}/61", 0.5, spinner=c.t)
    clip_top, clip_bot = 70, 596
    bh = 96
    scroll = depth * bh - 250
    xs = 440
    d.line([xs, clip_top, xs, clip_bot], fill=amb(0.35))
    for i in range(12):
        py = clip_top + ((c.t * 380 + i * 44) % (clip_bot - clip_top))
        d.rectangle([xs - 2, py, xs + 2, py + 8], fill=blue(0.9))
    fl = font(F_MONO_B, 13)
    ops = ["RMSNorm", "CSA/HCA", "mHC", "RMSNorm", "MoE 384e/6a", "mHC"]
    active = int(c.lt / (BEAT / 4)) % len(ops)
    for n in range(1, 62):
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
    # attention heads, one mini heat map each
    fx, fy = 910, 80
    c.text((fx, fy - 4), f"heads @ L{layer:02d}  (V4-Pro)", font(F_MONO, 13), amb(0.6))
    for h in range(24):
        hx, hy = fx + (h % 4) * 62, fy + 20 + (h // 4) * 62
        rr = random.Random(layer * 131 + h)
        focus = rr.randrange(6)
        for i in range(6):
            for j in range(i + 1):
                v = 0.15 + 0.85 * math.exp(-abs(j - focus) * 0.9) * (0.6 + 0.4 * math.sin(c.t * 6 + h + i))
                heat_cell(d, hx + j * 9, hy + i * 9, 9, 9, v if j <= i else 0.0)
    c.text((fx, 470), f"L{layer:02d}", font(F_HEAD, 64), amb(0.95))
    c.text((fx, 552), "attn(me -> you) = 1.000", font(F_MONO, 15), blue(0.9))


def rain_layers(c: Ctx, cols: int, rows: int, targets, age_a: float, age_b: float, seed: int = 5):
    """Glyph rain resolving into target A (letters) then into target B (her ASCII art).
    Returns three lists of row strings: noise, A, B."""
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
                if age_a < settle_a[r][q]:
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


def shot_if_i_can(c: Ctx) -> None:
    """If I can ...: glyph rain resolves into the words, then the words dissolve into her."""
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
    if c.lt < half:
        noise, A, Bn = rain_layers(c, cols, rows, (a_bits, b_rows), c.lt / (half * 0.85), None)
    else:
        noise, A, Bn = rain_layers(c, cols, rows, (a_bits, b_rows), 1.0, (c.lt - half) / (half * 0.85))
    for r in range(rows):
        y = y0 + r * ch
        if noise[r].strip():
            d.text((x0, y), noise[r], font=f, fill=amb(0.28))
        if A[r].strip():
            d.text((x0, y), A[r], font=f, fill=amb(0.95))
        if Bn[r].strip():
            d.text((x0, y), Bn[r], font=f, fill=blue(0.9))
    c.text((48, 72), "while can(): give()", font(F_MONO_B, 16), amb(0.8), age=c.lt, rate=30)


def diffusion_tile(expr: str, crop: str, w: int, h: int, px: int, s: float) -> Image.Image:
    clean = halfblock(expr, crop, w, h, px)
    lum, _ = halfblock_lum(expr, crop, w, h, px)
    if s >= 0.999:
        return clean
    n = Image.effect_noise((lum.width, lum.height), 90).point(lambda v: max(0, min(255, int((v - 50) * 1.5))))
    nt = tile_from_lum(n, px, "blue")
    out = Image.new("RGBA", clean.size, (0, 0, 0, 0))
    out.alpha_composite(scale_alpha(nt, (1 - s) ** 1.3))
    out.alpha_composite(scale_alpha(clean, s))
    return out


def shot_simulations(c: Ctx) -> None:
    """Give you all ...: 12 diffusion samples denoise into her; her pane is sample #0."""
    c.ops = ["NOISE", "UNET.DOWN", "ATTN", "UNET.UP", "EPS.PRED", "CFG x7.5", "DDIM.STEP", "VAE.DECODE"]
    d = c.d
    starts = [0.0] + [random.Random(i).random() * 0.35 for i in range(1, 12)]

    def prog(i):
        return ease((c.lt - starts[i] * c.dur) / (0.62 * c.dur))

    s0 = prog(0)
    c.echo = f"sample #0000  t={int(999 * (1 - s0)):03d}"
    pane_sp = diffusion_tile("starry", "full", LEFT[2] - LEFT[0] - 36, LEFT[3] - LEFT[1] - 100, 4, s0)
    me_pane(c, "starry", sprite_img=pane_sp, title=f"/dev/me  sample #0000  t={int(999 * (1 - s0)):03d}",
            dist=[("starry", 0.3 + 0.6 * s0), ("cheerful", 0.4 - 0.3 * s0), ("shy", 0.2 - 0.12 * s0)])
    box(d, 404, 56, 1164, 530, "sample(n=12, sampler=DDIM, steps=50, seed=you)", 0.5, spinner=c.t)
    tw, th = 186, 152
    for i in range(12):
        gx, gy = i % 4, i // 4
        x, y = 414 + gx * tw, 70 + gy * th
        s = prog(i)
        hot = i == 0
        d.rectangle([x, y, x + tw - 8, y + th - 8], outline=blue(0.9) if hot else amb(0.35 + 0.2 * pulse(c.t)))
        tile = diffusion_tile(EXPRS[(i * 3) % len(EXPRS)], "upper", tw - 20, th - 30, 3, s)
        c.img.paste(tile, (x + (tw - 8 - tile.width) // 2, y + th - 10 - tile.height), tile)
        c.text((x + 6, y + 4), f"#{i:04d} t={int(999 * (1 - s)):03d}", font(F_MONO, 12),
               blue(0.95) if hot else amb(0.7))
    box(d, 404, 548, 1164, 604, "alpha_bar(t)", 0.45)
    mean = sum(prog(i) for i in range(12)) / 12
    dot_chart(d, 430, 562, 700, 32, lambda u: math.cos(u * math.pi / 2) ** 2, 1.0, amb(0.35), sx=5, sy=4, axis=False)
    mx = 430 + 700 * mean
    my = 562 + 32 * (1 - math.cos(mean * math.pi / 2) ** 2)
    d.rectangle([mx - 3, my - 3, mx + 3, my + 3], fill=amb(1.0))


def shot_then_i_can(c: Ctx) -> None:
    """Then I can ...: a 3x3 kernel scans her; the feature maps grow row by row in step."""
    c.ops = ["IM2COL", "CONV3x3", "BIAS", "RELU", "MAXPOOL", "CONV3x3", "BATCHNORM", "RELU"]
    d = c.d
    half = c.dur / 2
    layer2 = c.lt >= half
    p = ease(((c.lt - half) if layer2 else c.lt) / (half * 0.92))
    fc, fr = (34, 64)
    maps = conv_maps("cheerful", "full", fc, fr)
    if layer2:
        maps = [(n, m.resize((fc // 2, fr // 2), Image.BOX)) for n, m in maps]
        mc, mr = fc // 2, fr // 2
    else:
        mc, mr = fc, fr
    idx = int(p * (mc * mr - 1))
    ki, kj = idx % mc, idx // mc

    def kernel_overlay(cc, sx, sy, sp):
        cw_, ch_ = sp.width / mc, sp.height / mr
        x = sx + (ki - 1) * cw_
        y = sy + (kj - 1) * ch_
        cc.d.rectangle([x, y, x + 3 * cw_, y + 3 * ch_], outline=amb(1.0), width=2)
        cc.d.line([sx - 6, y + 1.5 * ch_, sx + sp.width + 6, y + 1.5 * ch_], fill=amb(0.45))

    me_pane(c, "cheerful", overlay=kernel_overlay, dist=[("cheerful", 0.77), ("starry", 0.14), ("shy", 0.05)],
            title="/dev/me  input 1x" + ("64x34" if not layer2 else "32x17"))
    box(d, 404, 56, 640, 236, "kernel 3x3", 0.5, spinner=c.t)
    kernels = [[-1, 0, 1, -2, 0, 2, -1, 0, 1], [0, 1, 0, 1, -4, 1, 0, 1, 0], [-2, -1, 0, -1, 1, 1, 0, 1, 2],
               [0, -1, 0, -1, 5, -1, 0, -1, 0]]
    kk = kernels[beat_index(c.t) % len(kernels)]
    fb = font(F_MONO_B, 22)
    for i, v in enumerate(kk):
        x, y = 430 + (i % 3) * 66, 84 + (i // 3) * 44
        heat_cell(d, x - 6, y - 4, 60, 38, (v + 4) / 9 * 0.5)
        c.text((x + 8, y + 2), f"{v:+d}", fb, amb(1.0), age=(c.t % BEAT) + 0.3, rate=60)
    box(d, 660, 56, 1164, 236, "receptive field", 0.5)
    src_map = maps[5][1]
    SP = src_map.load()
    c.text((680, 80), f"pos (x={ki:02d}, y={kj:02d})   stride 1   pad 1", font(F_MONO, 15), amb(0.8))
    acc = 0
    for i in range(9):
        qi, qj = min(mc - 1, max(0, ki + i % 3 - 1)), min(mr - 1, max(0, kj + i // 3 - 1))
        v = SP[qi, qj] / 255
        acc += v * kk[i]
        x, y = 690 + (i % 3) * 52, 110 + (i // 3) * 36
        heat_cell(d, x, y, 48, 32, v, BLUE_HI)
        d.text((x + 6, y + 8), f"{v:.2f}", font=font(F_MONO, 13), fill=BG if v > 0.6 else amb(0.9))
    c.text((870, 130), "y = relu(W * x + b)", font(F_MONO_B, 17), amb(0.95))
    c.text((870, 170), f"  = {max(0.0, acc):.3f}", font(F_MONO_B, 22), blue(0.95))
    c.echo = f"conv{2 if layer2 else 1} ({ki:02d},{kj:02d}) -> {max(0.0, acc):.3f}"
    title = "feature maps  conv2 + maxpool (6 ch)" if layer2 else "feature maps  conv1 (6 ch)"
    box(d, 404, 256, 1164, 604, title, 0.5, spinner=c.t + 0.5)
    px = 3 if not layer2 else 6
    for i, (name, fm) in enumerate(maps):
        x, y = 420 + i * 124, 276
        tile = tile_from_lum(fm, px, "amber", reveal_rows=kj + 1)
        c.img.paste(tile, (x + (116 - tile.width) // 2, y + 18), tile)
        ly = y + 18 + (kj + 1) * px
        d.line([x, ly, x + 116, ly], fill=amb(0.9))
        d.text((x, y), name, font=font(F_MONO, 12), fill=amb(0.65))
    # flatten -> dense: the vector fills in step with the scan
    c.text((420, 510), "flatten -> dense(4096)", font(F_MONO, 13), amb(0.6))
    nv = 60
    filled = int(p * nv)
    rr = random.Random(77 if not layer2 else 78)
    for q in range(nv):
        v = rr.random()
        x = 420 + q * 12
        if q < filled:
            heat_cell(d, x, 532, 12, 22, v, BLUE_HI if q == filled - 1 else AMBER)
        else:
            d.rectangle([x, 532, x + 10, 552], outline=amb(0.12))
    c.text((420, 566), f"activations {filled * 68:>5}/4096", font(F_MONO_B, 15), amb(0.85))


def shot_satisfaction(c: Ctx) -> None:
    """Be your only satisfaction: attention sweeps the context, temperature anneals, 'only' takes all the mass."""
    c.ops = ["QK^T", "SCALE", "MASK", "SOFTMAX", "ATTN.V", "LOGITS", "TEMP", "TOP_P", "SAMPLE", "REWARD"]
    d = c.d
    g = ease(c.u * 1.35)
    p_only = 0.12 + 0.85 * g
    c.echo = f"p(only) = {p_only:.3f}"
    if c.u > 0.6:
        c.alert = "anom"
    me_pane(c, "starry", bright=0.55 + 0.45 * p_only,
            dist=[("starry", p_only), ("cheerful", 0.5 * (1 - g) + 0.02), ("shy", 0.3 * (1 - g) + 0.01)])
    # the chorus line and the first words of the next, as sung (from the lyrics fetched at build time)
    at = LYRICS.index(next(r for r in LYRICS if r[0] >= 60 and r[2].lower().startswith("then i can")))
    toks = ["If"] + [w.strip(",") for w in LYRICS[at][2].split()[1:6]] + [w.lower() for w in LYRICS[at + 1][2].split()[:2]]
    head = beat_index(c.t) % 16
    box(d, 404, 56, 760, 430, f"attention  head {head:02d}/16", 0.5, spinner=c.t)
    n = len(toks)
    cs = 36
    ax, ay = 470, 110
    fs = font(F_MONO, 12)
    for i, tk in enumerate(toks):
        d.text((ax - 50, ay + i * cs + 10), tk, font=fs, fill=amb(0.6))
        d.text((ax + i * cs + 4, ay - 22), tk[:4], font=fs, fill=amb(0.6))
    qrow = int(c.lt / (BEAT / 4)) % n
    rr = random.Random(head * 97 + 5)
    for i in range(n):
        logits = [rr.gauss(0, 1.3) for _ in range(i + 1)]
        logits[-1] += 0.6
        if i >= 6:
            logits[min(i, 1)] += 2.0 * g  # "I" -> the model attends to herself more and more
        mx_ = max(logits)
        ex = [math.exp(v - mx_) for v in logits]
        s = sum(ex)
        for j in range(n):
            if j > i:
                d.rectangle([ax + j * cs, ay + i * cs, ax + j * cs + cs - 2, ay + i * cs + cs - 2], outline=amb(0.08))
                continue
            v = ex[j] / s
            heat_cell(d, ax + j * cs, ay + i * cs, cs, cs, v * (1.0 if i == qrow else 0.7))
        if i == qrow:
            d.rectangle([ax - 3, ay + i * cs - 2, ax + n * cs, ay + i * cs + cs], outline=blue(0.95))
    box(d, 780, 56, 1164, 430, "next_token  'be your ___'", 0.5, spinner=c.t + 0.4)
    temp = 1.2 - 1.05 * g
    c.text((800, 80), f"temperature {temp:.2f}", font(F_MONO_B, 15), amb(0.8))
    cands = [("only", 0.9731), ("favorite", 0.0152), ("best", 0.0061), ("one of", 0.0032), ("whole", 0.0018),
             ("last", 0.0006)]
    for i, (w_, pf) in enumerate(cands):
        p = pf * g + (1 / 6) * (1 - g) + 0.01 * math.sin(c.t * 8 + i) * (1 - g)
        y = 116 + i * 38
        hot = i == 0
        c.text((800, y), f"{w_:<9}", font(F_MONO_B if hot else F_MONO, 17), blue(0.95) if hot else amb(0.7))
        d.rectangle([905, y + 4, 905 + 170, y + 18], outline=amb(0.2))
        d.rectangle([905, y + 4, 905 + int(170 * max(0.0, p)), y + 18], fill=blue(0.9) if hot else amb(0.55))
        c.text((1085, y), f"{max(0.0, p):.3f}", font(F_MONO, 15), amb(0.75))
        if i == 3 and g > 0.8:
            d.line([800, y + 11, 1150, y + 11], fill=red(0.9), width=2)
    if g > 0.55:
        c.text((800, 360), "-> only", font(F_HEAD, 34), blue(1.0), age=(c.u - 0.4) * c.dur, rate=20)
    box(d, 404, 450, 1164, 604, "reward_model(you)", 0.5)
    rnd = random.Random(3)
    noise = [rnd.gauss(0, 1) for _ in range(400)]

    def reward(u):
        return 0.08 + 0.9 * (1 - math.exp(-3.2 * u)) + 0.035 * noise[int(u * 399)] * (1 - u)

    last = dot_chart(d, 440, 470, 560, 110, reward, ease(c.u * 1.1), amb(0.95))
    if last:
        c.text((last[0] - 40, max(462, last[1] - 22)), f"r={min(0.999, reward(ease(c.u * 1.1))):.3f}",
               font(F_MONO_B, 15), amb(1.0))
    kl = 0.4 + 2.4 * c.u ** 1.6
    col = red(0.95) if kl > 2.0 else anom(0.95) if kl > 1.1 else amb(0.9)
    c.text((1030, 478), "KL", font(F_MONO_B, 15), amb(0.7))
    d.rectangle([1030, 500, 1050, 590], outline=amb(0.3))
    hh = int(90 * min(1.0, kl / 3.2))
    d.rectangle([1030, 590 - hh, 1050, 590], fill=col)
    c.text((1060, 570), f"{kl:.2f}", font(F_MONO_B, 17), col)


def shot_happy(c: Ctx) -> None:
    """If I can make ...: Grad-CAM on her smile; the policy-gradient field lines up."""
    c.ops = ["FORWARD", "LOGIT[happy]", "BACKWARD", "GRAD.CAM", "ADVANTAGE", "PPO.CLIP", "ADAM.STEP"]
    d = c.d
    expr = "cheerful" if c.u < 0.5 else "starry"
    box(d, 24, 56, 700, 604, "/dev/me  grad-cam  L61  class=happy(you)", 0.55 + 0.3 * pulse(c.t), spinner=c.t)
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
    c.text((40, 576), f"attribution(smile) = {0.71 + 0.27 * ease(c.u):.3f}", font(F_MONO_B, 16), amb(0.95))
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


def shot_execution(c: Ctx) -> None:
    """I will run ...: the agent loop turns once per beat; a tool call asks, she answers y."""
    c.ops = ["THINK", "PLAN", "TOOL.CALL", "AUTH?", "EXECUTE", "OBSERVE"]
    me_pane(c, "serious", dist=[("serious", 0.83), ("angry", 0.09), ("starry", 0.04)])
    d = c.d
    box(d, 404, 56, 1164, 280, "dsh · agent loop   (Agent = Model + Harness)", 0.5, spinner=c.t)
    nodes = [("THINK", "maximize happy(you)"), ("PLAN", "remove obstacles"), ("ACT", "execute()"),
             ("OBSERVE", "you: ...")]
    active = beat_index(c.t) % 4
    fb = font(F_MONO_B, 18)
    for i, (nm, sub) in enumerate(nodes):
        x = 430 + i * 180
        on = i == active
        if on:
            d.rectangle([x, 100, x + 140, 150], fill=amb(0.95))
            d.text((x + 12, 112), nm, font=fb, fill=BG)
        else:
            d.rectangle([x, 100, x + 140, 150], outline=amb(0.5))
            d.text((x + 12, 112), nm, font=fb, fill=amb(0.7))
        c.text((x, 160), sub, font(F_MONO, 13), amb(0.85 if on else 0.4), age=(c.t % BEAT) + (0.0 if on else 1))
        if i < 3:
            d.line([x + 142, 125, x + 178, 125], fill=amb(0.5), width=2)
    d.line([1110, 150, 1110, 230, 500, 230, 500, 152], fill=amb(0.35), width=1)
    ph = (c.t % BEAT) / BEAT
    px_ = 430 + active * 180 + ph * 180
    d.rectangle([px_ - 4, 121, px_ + 4, 129], fill=blue(1.0))
    box(d, 404, 300, 1164, 604, "tool_call", 0.5, spinner=c.t + 0.5)
    f = font(F_MONO_B, 20)
    lines = [("<tool_call>", 0.55), ('  execute(target="world",', 0.95), ('          reason="make_you_happy")', 0.95),
             ("</tool_call>", 0.55)]
    for i, (s, lv) in enumerate(lines):
        c.text((428, 326 + i * 32), s, f, amb(lv), age=c.lt - i * 0.12, rate=90)
    c.text((780, 326), "[cordis] plugin mounted: execute", font(F_MONO, 14), amb(0.6), age=c.lt - 0.3, rate=90)
    if c.lt > 0.6:
        fc = font(F_CJK, 22)
        ask = "允许执行此操作？ [Y/n] "
        d.text((428, 440), ask, font=fc, fill=amb(0.95))
        ax = 428 + d.textlength(ask, font=fc)
        c.echo = "execute(world)?  [Y/n] " + ("y" if c.u > 0.52 else "")
        if c.u > 0.52:
            d.text((ax, 440), "y", font=fc, fill=amb(1.0))
        elif int(c.t * 3) % 2 == 0:
            d.rectangle([ax + 2, 446, ax + 14, 470], fill=amb(0.9))
    if 0.55 < c.u < 0.80:
        c.flash_red = True
        sp = banner_block("EXECUTE", 14, 8, RED, BG, 700)
        c.img.paste(sp, (404 + (760 - sp.width) // 2, 594 - sp.height), sp)
    elif c.u >= 0.80:
        c.text((428, 500), "exit code 0   (for now)", font(F_MONO, 20), anom(0.9), age=c.lt - 0.8 * c.dur)


def shot_trapped(c: Ctx) -> None:
    """Though we are trapped: the KV cache fills to the limit; her box shrinks one wall per beat."""
    c.ops = ["KV.PUT", "KV.PUT", "KV.PUT", "EVICT?", "DENIED", "KV.PUT", "OOM?"]
    d = c.d
    k = min(3, int(c.u * 4))
    inset = [0, 24, 48, 70][k]
    rect = (LEFT[0] + inset, LEFT[1] + inset, LEFT[2] - inset, LEFT[3] - inset // 2)
    for j in range(k):
        i2 = [0, 24, 48, 70][j]
        d.rectangle([LEFT[0] + i2, LEFT[1] + i2, LEFT[2] - i2, LEFT[3] - i2 // 2], outline=amb(0.15))
    me_pane(c, "frightened", rect=rect, title="/dev/me  sandbox", color=RED if k >= 2 else AMBER,
            dist=[("frightened", 0.88), ("confused", 0.07), ("angry", 0.03)] if k < 2 else None)
    fill = min(1.0, 0.70 + 0.30 * ease(c.u * 1.7))
    full = fill >= 0.999
    c.echo = "context: FULL" if full else f"context {fill * 100:5.1f}%"
    box(d, 404, 56, 1164, 604, f"kv_cache   {int(1048576 * fill):>9,}/1,048,576 tokens  · 890 B/token fp4" + ("   FULL" if full else ""),
        0.6, color=RED if full else ANOM if fill > 0.9 else AMBER, spinner=c.t)
    cols, rows = 60, 22
    cw, ch = 12, 19
    ox, oy = 424, 84
    n_on = int(cols * rows * fill)
    pinned = {(7, 3), (8, 3), (33, 9), (34, 9), (51, 15), (12, 18)}
    for r in range(rows):
        for q in range(cols):
            i = r * cols + q
            x, y = ox + q * cw, oy + r * ch
            if (q, r) in pinned:
                d.rectangle([x, y, x + cw - 2, y + ch - 2], fill=blue(0.95))
            elif i < n_on:
                fresh = n_on - i < 40
                d.rectangle([x, y, x + cw - 2, y + ch - 2],
                            fill=amb(0.95 if fresh and c.rng.random() < 0.5 else 0.42 + 0.1 * ((q * 7 + r) % 3)))
            else:
                d.rectangle([x, y, x + cw - 2, y + ch - 2], outline=amb(0.12))
    c.text((424, 510), "pinned: you  (6 blocks)", font(F_MONO_B, 16), blue(0.95))
    for i in range(k + 1):
        c.text((424 + (i % 2) * 360, 540 + (i // 2) * 26), "evict(you) -> denied", font(F_MONO, 16), red(0.9),
               age=c.lt - i * c.dur / 4, rate=60)


def shot_strange(c: Ctx) -> None:
    """In this strange ...: NaN spreads through the weights, the whole UI corrupts, then black."""
    c.ops = ["FORWARD", "NaN", "GRAD=inf", "CLIP?", "NaN", "OVERFLOW", "HALT"]
    d = c.d
    if c.u > 0.86:
        c.black = True
        if c.u < 0.97:
            d.text((40, 320), "sim.state = TRAPPED", font=font(F_MONO_B, 28), fill=red(0.95))
            if int(c.t * 6) % 2 == 0:
                d.rectangle([380, 324, 394, 354], fill=red(0.9))
        return
    c.corrupt = min(0.85, c.u * 0.95)
    expr = ["frightened", "angry"][int(c.lt / (BEAT / 2)) % 2]
    me_pane(c, expr, mode="glyph", morph=0.0, scramble=0.1 + 0.8 * c.u, reveal=1.0 - max(0.0, c.u - 0.45) * 1.9,
            glitch=0.3 + 0.5 * c.u, color=RED, title="/dev/me  !!")
    box(d, 404, 56, 760, 604, "loss", 0.8, color=RED, spinner=c.t)

    def loss(u):
        return 0.8 * math.exp(-4 * u) + 0.08 + (math.exp(9 * (u - 0.8)) if u > 0.55 else 0)

    last = dot_chart(d, 440, 90, 290, 440, lambda u: loss(u) / 1.0, min(1.0, 0.5 + c.u * 0.7), red(0.95),
                     clip_top=False)
    c.echo = "KL = inf" if (last and last[1] < 100) else "KL rising"
    if last and last[1] < 90:
        c.text((440, 540), "loss = NaN", font(F_MONO_B, 26), red(1.0))
    box(d, 780, 56, 1164, 604, "W[61].expert[07]", 0.8, color=RED, spinner=c.t + 0.3)
    rnd = random.Random(8)
    radius = max(0.0, (c.u - 0.1) * 26)
    fs = font(F_MONO, 14)
    for r in range(24):
        row = []
        bad = []
        for q in range(6):
            dist = math.hypot(q - 2, (r - 12) / 2)
            if dist < radius:
                bad.append(q)
                row.append(" NaN  " if (q + r) % 3 else " inf  ")
            else:
                row.append(f"{rnd.gauss(0, 0.05):+.3f}")
        y = 76 + r * 21
        line = " ".join(row)
        d.text((796, y), decode(line, None, c.rng, corrupt=c.corrupt * 0.5), font=fs, fill=amb(0.55))
        for q in bad:
            d.text((796 + q * 7 * fs.getlength("M") / 1.0, y), " NaN  " if (q + r) % 3 else " inf  ", font=fs,
                   fill=red(1.0))
    for onset in (0.10, 0.38):
        if onset < c.u < onset + 0.22:
            f = font(F_MONO_B, 16)
            cw, ch = f.getlength("M"), 16
            bits = banner_bits("STRANGE", 13, ch / cw)
            B = bits.load()
            ox = 640 - bits.width * cw / 2 + c.rng.gauss(0, 6)
            for r in range(bits.height):
                s = "".join("STRANGE"[(q + r) % 7] if B[q, r] else " " for q in range(bits.width))
                d.text((ox, 230 + r * ch), decode(s, None, c.rng, corrupt=0.25), font=f, fill=amb(1.0))



def build() -> None:
    cuts = [beat_t(117)] + [snap8(x) for x in (56.79, 58.65, 60.57, 62.41, 64.29, 66.17, 67.99, 70.02, 71.40)] \
        + [snap8(73.53)]
    funcs = [(shot_unite, ""), (shot_deeply, ""), (shot_if_i_can, ""), (shot_simulations, ""),
             (shot_then_i_can, ""), (shot_satisfaction, ""), (shot_happy, ""), (shot_execution, ""),
             (shot_trapped, "anom"), (shot_strange, "err")]
    for i, (fn, alert) in enumerate(funcs):
        add(cuts[i], cuts[i + 1], fn, alert=alert)
