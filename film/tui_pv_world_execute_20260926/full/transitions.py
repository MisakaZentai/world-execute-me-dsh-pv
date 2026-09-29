"""Motivated transitions. These are not wipes laid over a cut; each one carries something across it.

reflow         the picture comes apart into glyph particles that fly to where the next picture's light is
               (matched along a Hilbert curve, so neighbours stay neighbours) and settle into it
pane_dissolve  inside one pane (her portrait): cells flip through a glyph as they change
zoom           a match on an object: the camera moves so that object A's rect lands on object B's rect;
               push into a detail (A small -> B full screen) or pull out of one (A full -> B small)
pan            the two scenes are neighbours in space: time runs right, depth runs down, the past is left
spin           the frame turns over (dizzy, trance)
crt            power on from black, or off to a line (only where the story switches the machine)
"""

from __future__ import annotations

import math
import random
from functools import lru_cache

from PIL import Image, ImageChops, ImageDraw

from tuikit import BG, F_MONO_B, SCR, H, W, font, smooth

GRID = 7


# ---------------------------------------------------------------- reflow

def _xy2d(n: int, x: int, y: int) -> int:
    d = 0
    s = n // 2
    while s > 0:
        rx = 1 if (x & s) else 0
        ry = 1 if (y & s) else 0
        d += s * s * ((3 * rx) ^ ry)
        if ry == 0:
            if rx == 1:
                x, y = n - 1 - x, n - 1 - y
            x, y = y, x
        s //= 2
    return d


@lru_cache(None)
def _hilbert_keys(cols: int, rows: int) -> list[int]:
    n = 256
    return [_xy2d(n, int(q * n / cols), int(r * n / rows)) for r in range(rows) for q in range(cols)]


def _points(img: Image.Image, limit: int):
    cols, rows = max(1, img.width // GRID), max(1, img.height // GRID)
    small = img.resize((cols, rows), Image.BOX)
    lum = small.convert("L").tobytes()
    rgb = small.tobytes()
    keys = _hilbert_keys(cols, rows)
    pts = [(keys[i], (i % cols) * GRID + GRID // 2, (i // cols) * GRID + GRID // 2, rgb[3 * i:3 * i + 3])
           for i in range(cols * rows) if lum[i] > 38]
    pts.sort()
    if len(pts) > limit:
        step = len(pts) / limit
        pts = [pts[int(k * step)] for k in range(limit)]
    return pts


def reflow(A: Image.Image, B: Image.Image, q: float, rng, n: int = 1500) -> Image.Image:
    """A dissolves into glyph particles that fly along gentle arcs to B's bright points and settle."""
    q = max(0.0, min(1.0, q))
    black = Image.new("RGB", A.size, BG)
    a_l = Image.blend(black, A, 1 - smooth(q / 0.35))
    b_l = Image.blend(black, B, smooth((q - 0.62) / 0.38))
    out = ImageChops.lighter(a_l, b_l)
    if 0.0 < q < 1.0:
        pa, pb = _points(A, n), _points(B, n)
        if pa and pb:
            m = max(len(pa), len(pb))
            d = ImageDraw.Draw(out)
            f = font(F_MONO_B, 11)
            rnd = random.Random(11)
            for k in range(m):
                a = pa[int(k * len(pa) / m)]
                b = pb[int(k * len(pb) / m)]
                s0 = 0.04 + 0.28 * rnd.random()
                kk = smooth((q - s0) / 0.58)
                if kk <= 0.0 or kk >= 1.0:
                    continue
                dx, dy = b[1] - a[1], b[2] - a[2]
                bend = math.sin(math.pi * kk) * (0.18 + 0.12 * rnd.random())
                x = a[1] + dx * kk - dy * bend
                y = a[2] + dy * kk + dx * bend
                col = tuple(int(a[3][i] + (b[3][i] - a[3][i]) * kk) for i in range(3))
                col = tuple(min(255, int(v * 1.5) + 30) for v in col)
                d.text((x - 3, y - 6), rng.choice(SCR), font=f, fill=col)
    return out


def pane_dissolve(A: Image.Image, B: Image.Image, q: float, rng, cell: int = 8) -> Image.Image:
    q = max(0.0, min(1.0, q))
    cols, rows = max(1, A.width // cell), max(1, A.height // cell)
    rnd = random.Random(5)
    thr = [rnd.random() for _ in range(cols * rows)]
    mask = Image.new("L", (cols, rows), 0)
    mask.putdata([255 if v < q else 0 for v in thr])
    out = Image.composite(B, A, mask.resize(A.size, Image.NEAREST))
    small = B.resize((cols, rows), Image.BOX).load()
    d = ImageDraw.Draw(out)
    f = font(F_MONO_B, 10)
    for i, v in enumerate(thr):
        if abs(v - q) < 0.08:
            c_, r_ = i % cols, i // cols
            col = tuple(min(255, int(ch * 1.7) + 40) for ch in small[c_, r_])
            d.rectangle([c_ * cell, r_ * cell, c_ * cell + cell - 1, r_ * cell + cell - 1], fill=BG)
            d.text((c_ * cell + 1, r_ * cell - 2), rng.choice(SCR), font=f, fill=col)
    return out


# ---------------------------------------------------------------- camera moves

def _warp(img: Image.Image, src, dst) -> Image.Image:
    """Transform img so that rect src lands on rect dst (uniform scale, centres aligned)."""
    sw, sh = max(1e-3, src[2] - src[0]), max(1e-3, src[3] - src[1])
    dw, dh = dst[2] - dst[0], dst[3] - dst[1]
    s = math.sqrt((dw / sw) * (dh / sh))
    cxs, cys = (src[0] + src[2]) / 2, (src[1] + src[3]) / 2
    cxd, cyd = (dst[0] + dst[2]) / 2, (dst[1] + dst[3]) / 2
    return img.transform((W, H), Image.AFFINE, (1 / s, 0, cxs - cxd / s, 0, 1 / s, cys - cyd / s),
                         resample=Image.NEAREST if s > 1.8 else Image.BILINEAR, fillcolor=BG)


def zoom(A, B, p, rng, a_rect=(0, 0, W, H), b_rect=(0, 0, W, H)) -> Image.Image:
    e = smooth(p)
    r = tuple(a_rect[i] + (b_rect[i] - a_rect[i]) * e for i in range(4))
    ia, ib = _warp(A, a_rect, r), _warp(B, b_rect, r)
    return Image.blend(ia, ib, smooth((p - 0.3) / 0.45))


def pan(A, B, p, rng, direction="right") -> Image.Image:
    vx, vy = {"right": (-W, 0), "left": (W, 0), "down": (0, -H), "up": (0, H)}[direction]
    def at(pp):
        e = smooth(max(0.0, min(1.0, pp)))
        out = Image.new("RGB", (W, H), BG)
        out.paste(A, (int(vx * e), int(vy * e)))
        out.paste(B, (int(vx * e - vx), int(vy * e - vy)))
        return out
    return Image.blend(at(p), at(p - 0.012), 0.3)


def _rot(img, ang, scale):
    a = math.radians(ang)
    c, s = math.cos(a) / scale, math.sin(a) / scale
    cx, cy = W / 2, H / 2
    return img.transform((W, H), Image.AFFINE, (c, s, cx - c * cx - s * cy, -s, c, cy + s * cx - c * cy),
                         resample=Image.BILINEAR, fillcolor=BG)


def spin(A, B, p, rng) -> Image.Image:
    e = smooth(p)
    ang = 220 * e
    scale = 1 - 0.38 * math.sin(math.pi * p)
    ia = _rot(A, ang, scale)
    ib = _rot(B, ang - 220, scale)
    return Image.blend(ia, ib, smooth((p - 0.35) / 0.3))


def crt(A, B, p, rng) -> Image.Image:
    out = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(out)
    if p < 0.5:
        k = smooth(p / 0.5)
        h = max(2, int(H * (1 - k)))
        out.paste(A.resize((W, h), Image.BILINEAR), (0, (H - h) // 2))
    else:
        k = smooth((p - 0.5) / 0.5)
        h = max(2, int(H * k))
        out.paste(B.resize((W, h), Image.BILINEAR), (0, (H - h) // 2))
    d.rectangle([0, H // 2 - 1, W, H // 2 + 1], fill=(255, 255, 255))
    return out


FULLFRAME = {"reflow": lambda A, B, p, rng, **k: reflow(A, B, p, rng), "zoom": zoom, "pan": pan, "spin": spin,
             "crt": crt}


def apply(kind: str, A, B, p: float, rng, **kw) -> Image.Image:
    return FULLFRAME[kind](A, B, max(0.0, min(1.0, p)), rng, **kw)
