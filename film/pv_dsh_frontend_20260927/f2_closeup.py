"""F2 (review 1): EXECUTION hits #4 and #8 (layout 3 of the hits, 150.62 and 154.31 s) push in on the dsh window's
avatar instead of the dancer's head, and the EXECUTION bar slams down onto her eyes.

The picture is the art the window header shows at that moment (batch_f.avatar: avatars/f/red.png, D's forged starry
face in the executioner's red), taken from the same crop of the same sprite at full resolution and drawn in the hits'
own TUI style: tuikit.halfblock's 5 px cells (8 grey levels, the cell grid), coloured with red.png's palette.

    make_source(open_fn)          batch_f.avatars() writes avatars/f/closeup_la.png (grey + alpha, the sprite is
                                  opened there because the film process guards the character files)
    closeup(t, cut, land, z0, z1, bars, until)
                                  the 520 x 520 RGBA layer that layout 3 pastes at (24, 70)

The eye line is measured on the art (iris centres, CROP coordinates). Her head is tilted, so the bar is too: it lies
along the eye line and is as thick as the band that hides both eyes. The push-in is anchored on the middle of her
eyes, which drifts toward the middle of the picture as it closes in, so the bar always sits exactly on them.
"""
from __future__ import annotations

import math
import random
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps, ImageStat

HERE = Path(__file__).resolve().parent
SRC = HERE / "avatars/f/closeup_la.png"
SPRITE = Path(__file__).resolve().parents[1].joinpath("third_party_references/whale_maid_expanded_20260926/expressions/whale-starry.webp")
CROP = (250, 40, 690, 480)                   # batch_f.avatars head(): the header avatar's crop of the sprite
MARGIN = 60                                  # closeup_la.png = CROP grown by this on every side
BACKDROP = (9, 14, 30)                       # what head() lays the sprite on
PALETTE = ((24, 3, 5), (196, 36, 30), (255, 120, 104))   # batch_f.avatars red(): black, mid, white
EYES = ((211.3, 216.3), (292.5, 196.3))      # iris centres on the art (CROP px): her right eye, her left eye
EYE_BAND = 50.0                              # the band across the eye line that hides both eyes, lashes included
EYE_SHIFT = -3.0                             # its middle sits this far above the iris line (the lashes reach higher)
GAMMA = 1.7                                  # the skin is most of the picture: spread it over the 8 cell levels
REGION = (24, 70, 544, 590)                  # layout 3's picture: halfblock(.., 520, 520, 5) pasted at (24, 70)
PX = 5
S0 = (REGION[2] - REGION[0]) / (CROP[2] - CROP[0])   # screen px per art px at zoom 1 (the whole avatar)
MID = ((EYES[0][0] + EYES[1][0]) / 2, (EYES[0][1] + EYES[1][1]) / 2)
ANGLE = math.degrees(math.atan2(EYES[1][1] - EYES[0][1], EYES[1][0] - EYES[0][0]))   # < 0: rising to the right
CENTRE = (286.0, 318.0)                      # where the eyes drift to as the push-in closes in (screen px)
WORD = "EXECUTION"
FPS = 24


# ---------------------------------------------------------------- the source (batch_f)
def make_source(open_fn=Image.open) -> None:
    """Grey (red.png's recipe: contrast 1.4 about the avatar's mean, then greyscale) + the sprite's alpha."""
    im = open_fn(SPRITE).convert("RGBA")
    x0, y0, x1, y1 = CROP
    box = (x0 - MARGIN, y0 - MARGIN, x1 + MARGIN, y1 + MARGIN)
    spr = Image.new("RGBA", (box[2] - box[0], box[3] - box[1]), (0, 0, 0, 0))
    spr.alpha_composite(im.crop((max(0, box[0]), max(0, box[1]), min(im.width, box[2]), min(im.height, box[3]))),
                        (max(0, -box[0]), max(0, -box[1])))
    flat = Image.new("RGBA", spr.size, BACKDROP + (255,))
    flat.alpha_composite(spr)
    flat = flat.convert("RGB")
    mean = int(ImageStat.Stat(flat.crop((MARGIN, MARGIN, MARGIN + x1 - x0, MARGIN + y1 - y0)).convert("L")).mean[0]
               + 0.5)
    grey = Image.blend(Image.new("RGB", flat.size, (mean,) * 3), flat, 1.4).convert("L")
    out = Image.merge("LA", (grey, spr.getchannel("A")))
    SRC.parent.mkdir(parents=True, exist_ok=True)
    out.save(SRC)


@lru_cache(1)
def source() -> Image.Image:
    return Image.open(SRC).convert("LA")


@lru_cache(None)
def grid_mask(w: int, h: int, px: int) -> Image.Image:
    """tuikit.grid_mask: a dark gap after every cell column, a dimmer line under every half-block row."""
    m = Image.new("L", (w, h), 255)
    d = ImageDraw.Draw(m)
    for x in range(px - 1, w, px):
        d.line([x, 0, x, h], fill=0)
    for y in range(2 * px - 1, h, 2 * px):
        d.line([0, y, w, y], fill=70)
    return m


def ease_out(x):
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


def smooth(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


# ---------------------------------------------------------------- the view
def view(z):
    """(scale, anchor): screen px per art px, and where the middle of her eyes sits on screen at zoom z."""
    a0 = (REGION[0] + MID[0] * S0, REGION[1] + MID[1] * S0)
    k = smooth((z - 1.0) / 0.6)
    return S0 * z, (a0[0] + (CENTRE[0] - a0[0]) * k, a0[1] + (CENTRE[1] - a0[1]) * k)


def face(z, dy=0.0):
    """The avatar at zoom z as halfblock cells: 104 x 104 cells of 5 px, 8 levels, red.png's palette."""
    s, (ax, ay) = view(z)
    ay += dy
    w, h = REGION[2] - REGION[0], REGION[3] - REGION[1]
    cols, rows = w // PX, h // PX

    def art(x, y):                            # screen px -> closeup_la.png px
        return MID[0] + (x - ax) / s + MARGIN, MID[1] + (y - ay) / s + MARGIN

    x0, y0 = art(REGION[0], REGION[1])
    x1, y1 = art(REGION[2], REGION[3])
    small = source().resize((cols, rows), Image.Resampling.LANCZOS, box=(x0, y0, x1, y1))
    grey, alpha = small.split()
    step = 255 / 7
    lum = grey.point(lambda v: int(round((0.16 + 0.84 * (v / 255) ** GAMMA) * 7) * step))
    alpha = alpha.point(lambda a: 255 if a > 100 else 0)
    lum = lum.resize((w, h), Image.Resampling.NEAREST)
    alpha = ImageChops.multiply(alpha.resize((w, h), Image.Resampling.NEAREST), grid_mask(w, h, PX))
    rgb = ImageOps.colorize(lum, black=PALETTE[0], white=PALETTE[2], mid=PALETTE[1]).convert("RGBA")
    rgb.putalpha(alpha)
    return rgb


# ---------------------------------------------------------------- the bar
@lru_cache(64)
def bar_strip(length: int, thick: int, offset: int, heat: int):
    """One EXECUTION bar, horizontal, before it is tilted onto the eye line: solid red, the words in the background
    colour (layout 3's bar), a white-hot flash when it lands (heat 0..10)."""
    import tuikit as tk
    k = heat / 10
    col = tuple(round(c + (w - c) * 0.8 * k) for c, w in zip(tk.RED, (255, 236, 228)))
    im = Image.new("RGBA", (length, thick), col + (255,))
    d = ImageDraw.Draw(im)
    size = max(12, min(34, round(thick * 0.5)))
    f = tk.font(tk.F_MONO_B, size)
    unit = d.textlength(WORD + "  ", font=f)
    x = length / 2 - d.textlength(WORD, font=f) / 2 - offset * unit / 2
    while x > -unit:
        x -= unit
    top = (thick - size) / 2 - size * 0.12
    while x < length:
        d.text((x, top), WORD, font=f, fill=tk.BG + (255,))
        x += unit
    return im


def draw_bar(layer, centre, thick, heat=0.0, offset=0, alpha=1.0):
    """A bar across the whole picture along the eye line, centred on `centre` (screen px, layer origin = REGION)."""
    import tuikit as tk
    length = 900
    strip = bar_strip(length, max(4, round(thick)), offset, round(10 * heat))
    rot = strip.rotate(-ANGLE, resample=Image.Resampling.BICUBIC, expand=True)
    if alpha < 0.999:
        rot.putalpha(rot.getchannel("A").point(lambda a: round(a * alpha)))
    x = round(centre[0] - REGION[0] - rot.width / 2)
    y = round(centre[1] - REGION[1] - rot.height / 2)
    g = Image.new("RGBA", rot.size, tk.RED + (0,))
    g.putalpha(rot.getchannel("A").point(lambda a: round(a * (0.55 + 0.35 * heat))))
    layer.alpha_composite(placed(layer.size, g, x, y).filter(ImageFilter.GaussianBlur(5 + 5 * heat)))
    layer.alpha_composite(placed(layer.size, rot, x, y))


def placed(size, im, x, y):
    """im on a transparent canvas of `size` at (x, y) (which may lie partly outside it)."""
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    out.paste(im, (x, y))
    return out


def normal():
    """The unit vector across the eye line, pointing down the face."""
    a = math.radians(ANGLE)
    return -math.sin(a), math.cos(a)


# ---------------------------------------------------------------- one frame of a hit
def closeup(t, cut, land, z0, z1, until, bars=1):
    """Layout 3 as a push-in on the avatar. `land`: the frame time the new bar hits her eyes (the sung word);
    bars=1: the bar drops onto her bare eyes; bars=2: the first bar is on from the cut, a second, heavier one drops
    onto it (#8)."""
    fall = 3 / FPS                                       # the drop: two frames in the air, the third lands
    p = (t - (land - fall)) / fall
    after = t - land
    # the push-in, and a punch when the bar lands
    z = z0 + (z1 - z0) * ease_out((t - cut) / (until - cut))
    if after >= -1e-6:
        z += 0.045 * math.exp(-after / 0.06)
    jolt = 0.0
    if -1e-6 <= after < 2.5 / FPS:
        jolt = [5.0, 2.0, 0.0][min(2, int(after * FPS + 1e-6))]
    layer = Image.new("RGBA", (REGION[2] - REGION[0], REGION[3] - REGION[1]), (0, 0, 0, 0))
    pic = face(z, jolt)
    if 0 <= after < 1.5 / FPS:                           # the impact tears a few cell rows sideways for a frame
        rng = random.Random(round(land * 1000))
        torn = Image.new("RGBA", pic.size, (0, 0, 0, 0))
        for y in range(0, pic.height, 2 * PX):
            dx = rng.choice([0, 0, 0, -PX, PX, -2 * PX, 2 * PX]) if rng.random() < 0.45 else 0
            torn.paste(pic.crop((0, y, pic.width, y + 2 * PX)), (dx, y))   # a plain copy: the rows do not overlap
        pic = torn
    layer.alpha_composite(pic)

    s, (ax, ay) = view(z)
    ay += jolt
    nx, ny = normal()
    h1 = EYE_BAND * s
    heat = math.exp(-after / 0.07) if after >= -1e-6 else 0.0
    travel = (ay - REGION[1]) / ny + 0.5 * h1 + 40       # from out of the top of the picture onto her eyes

    def at(v):
        v += EYE_SHIFT * s
        return ax + nx * v, ay + ny * v

    if bars == 1:
        if p <= 0:
            return layer
        if p < 1:                                        # in the air: accelerating, a smear behind it
            v = -travel * (1 - min(1.0, p) ** 1.6)
            for j, a in ((2, 0.18), (1, 0.38)):
                draw_bar(layer, at(v - j * 0.22 * travel / 3), h1, alpha=a)
            draw_bar(layer, at(v), h1)
            return layer
        bounce = [0.10, -0.04, 0.0][min(2, int(after * FPS + 1e-6))] * h1
        draw_bar(layer, at(bounce), h1, heat)
        return layer

    # #8: the first bar is on her eyes from the cut; the second, heavier, lands on top of it
    h2 = 1.25 * h1
    rest = -(0.5 * h1 + 0.5 * h2 + 2 * z)
    push = 0.0
    if p >= 1:
        push = [0.16, 0.05, 0.0][min(2, int(after * FPS + 1e-6))] * h1
    draw_bar(layer, at(push), h1, 0.6 * heat, offset=0)
    if p <= 0:
        return layer
    if p < 1:
        v = rest - (travel + 0.5 * h2) * (1 - p ** 1.6)
        for j, a in ((2, 0.18), (1, 0.38)):
            draw_bar(layer, at(v - j * 0.22 * travel / 3), h2, alpha=a, offset=1)
        draw_bar(layer, at(v), h2, offset=1)
        return layer
    draw_bar(layer, at(rest + push), h2, heat, offset=1)
    return layer
