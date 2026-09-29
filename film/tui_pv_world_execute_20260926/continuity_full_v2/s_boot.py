"""Section 00 BOOT (shots 0-7, cuts 1-7, 0-16.1 s): the terminal grows one layer at a time.

  power       a CRT powers on; the first sung line is typed into the stdout band from its first syllable
  protection  the picture opens out into the whole shell; the same boot log scrolls on; a shield is drawn
  pieces      the shield's dots are laid into the weight grid one by one, its outline becomes the panel frame,
              and the interface chrome powers on around it
  creation    the loaded grid collapses into one cell that flies into her pane: her seed. She grows out of it
  parameters  the object's fields stay where they are and are rewritten in place into config.json (shell)
  init        the parameter count flies up and titles the histogram, which then rises from its baseline
  world       every bar's dots fly to the globe; me and you light up on "our new world"
  begin_sim   me and you fly into the status line; the globe collapses into the countdown's "3"

She does not exist before cut 3 (HIDE_HER). Shot 0 and the first 0.44 s of shot 1 are finished here (OWN and a
Cut returning a finished frame) because the chrome must power on rather than be there from frame 0: they call
kit.chrome with the shell staging's retraction held at 1, so only the lyric band is lit, exactly as the frame
loop draws the shell staging that follows.
"""
from __future__ import annotations

import math

from PIL import Image, ImageChops, ImageDraw

import cuts as C
import kit
import scenes as S
import scenes_boot as B
import sec_intro
from cuts import Cut, Frame, text_at
from kit import (BEAT, H, W, bezier, blank, clamp, ease_back, ease_in, ease_io, ease_out, haloed, inward,
                 lerp, place, radial, reveal, sweep, text_sprite, tk)

STUB = [sec_intro]
REPLACE = B.REPLACE
SPLIT = {"shot_creation", "shot_init", "shot_world"}
HIDE_HER = {"shot_power", "shot_protection", "shot_pieces"}
SHELL = {"shot_protection": "./protect", "shot_parameters": "neofetch"}  # <= 9 characters: kit.chrome types 25

ALL = kit.v1.ALL
FULLR = (24, 44, 1168, 608)  # reveal region for the full-width boot shots
FB = kit.engine.FIRST_BEAT


def beat(k: int) -> float:
    return FB + k * BEAT


def her_mod():
    import v2  # lazily: the frame loop imports the sections
    return v2


# ---------------------------------------------------------------- shot 0 and cut 1: a CRT powering on

GLASS = (1, 2, 5)
LINE_T0, LINE_T1 = beat(0), 0.40   # the power line grows from the centre (first beat)
OPEN_T0, OPEN_T1 = beat(1), 0.86   # the picture opens out of it (second beat)
HOT = (235, 240, 255)


def crt_finish(t, content, ctx, aperture, frame_a=0.0, frame_lift=0.0, line=None, veil=0.0, shell=None):
    """The finished frame of a CRT that is still powering on: dark glass outside `aperture`, a flash veil inside
    it, the picture's frame, the power line; then the chrome with the shell retraction held at 1."""
    img = content.convert("RGB")
    mask = Image.new("L", (W, H), 255)
    if aperture:
        x0, y0, x1, y1 = (int(round(v)) for v in aperture)
        ImageDraw.Draw(mask).rectangle([x0, y0, x1, y1], fill=0)
    img = Image.composite(Image.new("RGB", (W, H), GLASS), img, mask).convert("RGBA")
    ov = blank()
    d = ImageDraw.Draw(ov)
    if aperture and veil > 0.01:
        x0, y0, x1, y1 = aperture
        d.rectangle([x0, y0, x1, y1], fill=tk.mix(HOT, 0.35) + (int(255 * veil),))
    if aperture and frame_a > 0.01:
        layer = blank()
        x0, y0, x1, y1 = aperture
        tk.box(ImageDraw.Draw(layer), x0, y0, x1, y1, "", 0.5 + 0.5 * frame_lift)
        ov.alpha_composite(tk.scale_alpha(layer, frame_a))
    if line:
        x0, x1, y, k = line
        glow = blank()
        ImageDraw.Draw(glow).rectangle([x0 - 6, y - 7, x1 + 6, y + 7], fill=HOT + (int(60 * k),))
        ov.alpha_composite(glow)
        d.line([x0, y, x1, y], fill=HOT + (int(255 * k),), width=3)
    img.alpha_composite(ov)
    img = kit.chrome(img, t, ctx, 1.0, shell)
    return kit.engine.post(img.convert("RGB"), None)


def crt_state(t):
    """(aperture, frame alpha, frame lift, line, veil) of shot 0 at time t."""
    x0, y0, x1, y1 = B.CRT
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if t < LINE_T0:
        return None, 0.0, 0.0, None, 0.0
    if t < OPEN_T0:
        u = ease_out((t - LINE_T0) / (LINE_T1 - LINE_T0))
        hw = max(2.0, (x1 - x0) / 2 * u)
        return None, 0.0, 0.0, (cx - hw, cx + hw, cy, 0.75 + 0.25 * kit.engine.pulse(t)), 0.0
    u = ease_out((t - OPEN_T0) / (OPEN_T1 - OPEN_T0))
    hh = max(2.0, (y1 - y0) / 2 * u)
    return (x0, cy - hh, x1, cy + hh), 1.0, 1 - u, None, 0.4 * (1 - u)


def own_power(t, n):
    """Shot 0 (outside cut 1): Switch on ..."""
    canvas, ctx = C.body(ALL[0], t, n)
    ap, fa, fl, line, veil = crt_state(t)
    return crt_finish(t, canvas, ctx, ap, fa, fl, line, veil)


class C01(Cut):
    """power -> protection. UNFOLD: the CRT picture lifts, then opens out until it is the whole shell, locking on
    the beat; the POST log rides along with its top-left corner and scrolls up to the top of the terminal, where
    the protection lines continue under it. The shell prompt is printed as the picture's top edge passes it, and
    the shield is drawn stroke by stroke in the space the log left."""
    pre, post = 0.25, 0.44
    OPEN = 0.23  # after T: the picture fills the screen on the beat (1.543)

    def render(self, t, n):
        T = self.T
        e = ease_io((t - (T - 0.06)) / (self.OPEN + 0.06))
        nc, nctx = self.new(t, n, log_at=lerp(B.POWER_LOG, B.SHELL_LOG, e))
        ap = lerp(B.CRT, (-8, -8, W + 8, H + 8), e)
        lift = clamp((t - (T - self.pre)) / (self.pre - 0.06))
        fa = 1 - clamp((e - 0.55) / 0.45)
        shell = None
        if t >= T + 0.15:
            cmd = SHELL["shot_protection"]
            shell = cmd[:int((t - T - 0.15) * 40)] or " "
        return crt_finish(t, nc, nctx, ap, fa, lift * (1 - e), None, 0.0, shell)


# ---------------------------------------------------------------- cut 2: the shield is laid into the weight grid

def _resample(pts, m, closed=True):
    """m points evenly spaced by arc length along a polyline, plus the arc fraction of every input vertex."""
    P = list(pts) + ([pts[0]] if closed else [])
    seg = [math.hypot(P[i + 1][0] - P[i][0], P[i + 1][1] - P[i][1]) for i in range(len(P) - 1)]
    total = sum(seg) or 1.0
    frac, acc = [], 0.0
    for s in seg:
        frac.append(acc / total)
        acc += s
    out, i, acc = [], 0, 0.0
    for k in range(m):
        target = total * k / m
        while i < len(seg) - 1 and acc + seg[i] < target:
            acc += seg[i]
            i += 1
        u = (target - acc) / seg[i] if seg[i] else 0.0
        out.append(lerp(P[i], P[i + 1], u))
    return out, frac


def _at_frac(pts, f):
    """Point at arc fraction f along a closed polyline."""
    P = list(pts) + [pts[0]]
    seg = [math.hypot(P[i + 1][0] - P[i][0], P[i + 1][1] - P[i][1]) for i in range(len(P) - 1)]
    target, acc = sum(seg) * (f % 1.0), 0.0
    for i, s in enumerate(seg):
        if acc + s >= target:
            return lerp(P[i], P[i + 1], (target - acc) / s if s else 0.0)
        acc += s
    return P[-1]


FRAME_RECT = (24, 56, 1164, 604)
FRAME_PATH = [(24, 56), (1164, 56), (1164, 604), (24, 604)]


class C02(Cut):
    """protection -> pieces. MORPH: the shield lights up; its dots leave one by one, top row first, and each is
    laid into the next cell of the weight grid, which loads as it lands (cell 001 on the cut). The '#' outline
    stretches out into the load_weights frame and locks on the beat; the old log gives way from the left, the
    direction the cells load in. The chrome powers on around the frame as the shell staging ends."""
    pre, post = 0.32, 0.86
    FLY = 0.24
    LAND = 0.23  # after T: the outline is the frame (beat 3.851)

    def dots(self):
        if not hasattr(self, "_dots"):
            _, dots = B.shield_cells()
            f = tk.font(tk.F_MONO_B, 16)
            l, tp, r, b = f.getbbox(".")
            order = sorted(dots, key=lambda p: (p[3], p[2]))
            out = []
            for k, (x, y, q, rr) in enumerate(order):
                td = self.T - 0.22 + k * 0.010
                out.append(dict(src=(x + (l + r) / 2, y + (tp + b) / 2), cell=k, td=td, tl=td + self.FLY,
                                bend=0.16 if k % 2 else 0.1))
            self._dots = out
        return self._dots

    def landed(self):
        return {p["cell"]: p["tl"] for p in self.dots()}

    def outline(self):
        if not hasattr(self, "_outline"):
            edge, _ = B.shield_cells()
            f = tk.font(tk.F_MONO_B, 16)
            l, tp, r, b = f.getbbox("#")
            src = [(x + (l + r) / 2, y + (tp + b) / 2) for x, y, q, rr in edge]
            _, frac = _resample(src, 260)
            fw, fh = FRAME_RECT[2] - FRAME_RECT[0], FRAME_RECT[3] - FRAME_RECT[1]
            per = 2 * (fw + fh)
            corners = [0.0, fw / per, (fw + fh) / per, (2 * fw + fh) / per]  # the frame's corners stay sharp
            ts = sorted(set([k / 260 for k in range(260)] + corners))
            path_a = [_at_frac(src, f_) for f_ in ts]
            path_b = [_at_frac(FRAME_PATH, f_) for f_ in ts]
            glyphs = [(src[k], _at_frac(FRAME_PATH, frac[k])) for k in range(len(src))]
            self._outline = (path_a, path_b, glyphs)
        return self._outline

    def render(self, t, n):
        T = self.T
        land = T + self.LAND
        oc, octx = self.old(t, n, shield=False)
        nc, nctx = self.new(t, n, frame=t >= land)
        content = reveal(oc, nc, t, sweep((24, 0), (1, 0), T - 0.32, 2400.0), region=FULLR, seed=2)
        over = blank()
        d = ImageDraw.Draw(over)
        lift = clamp((t - (T - self.pre)) / 0.12)
        f16 = tk.font(tk.F_MONO_B, 16)
        # the outline: in place and lit, then stretching out into the frame
        path_a, path_b, glyphs = self.outline()
        u = ease_io((t - (T - 0.15)) / (self.LAND + 0.15))
        if t < land + 0.1:
            k_out = 1.0 if t < land else 1 - (t - land) / 0.1
            if u > 0:
                pts = [lerp(a, b, u) for a, b in zip(path_a, path_b)]
                d.line(pts + [pts[0]], fill=tk.amb(0.55 + 0.4 * (1 - u)) + (int(255 * k_out * min(1.0, u * 4)),),
                       width=2 if u < 0.8 else 1)
            for (a, b) in glyphs:
                x, y = lerp(a, b, u)
                al = k_out * (1 - clamp((u - 0.7) / 0.3))
                if al > 0.02:
                    d.text((x - 4, y - 9), "#", font=f16, fill=B.lit(tk.amb(0.9), 0.55 * lift) + (int(255 * al),))
        # the dots: waiting in the shield, then laid into the grid one by one, each growing into its cell
        for p in self.dots():
            if t >= p["tl"]:
                continue
            cx, cy = B.cell_center(p["cell"])
            v = clamp((t - p["td"]) / self.FLY)
            if v <= 0:
                sx, sy = p["src"]
                d.rectangle([sx - 1.5, sy - 1.5, sx + 1.5, sy + 1.5], fill=B.lit(tk.amb(0.9), 0.6 * lift) + (255,))
                continue
            x, y = bezier(p["src"], (cx, cy), p["bend"], ease_io(v))
            g = clamp((v - 0.55) / 0.45)
            s0 = 3.5 + 3.0 * math.sin(math.pi * min(1.0, v / 0.55))  # a little larger in flight
            hw, hh = lerp(s0, B.GRID["w"] / 2, ease_in(g)), lerp(s0, B.GRID["h"] / 2, ease_in(g))
            sp = Image.new("RGBA", (int(2 * hw) + 2, int(2 * hh) + 2), (0, 0, 0, 0))
            ImageDraw.Draw(sp).rectangle([1, 1, 2 * hw, 2 * hh], fill=HOT + (255,))
            place(over, haloed(sp, 0.8 * (1 - g), radius=4), (x, y))
        return Frame(content, self.pick(t, octx, nctx), over)


# ---------------------------------------------------------------- cut 3: her birth

class C03(Cut):
    """pieces -> creation. MORPH: the 161 loaded cells drain toward the grid's centre, far ones first, each
    shrinking to a point and turning from the system's colour to hers, and gather into one 8x8 cell. The object's
    pane (me = Object()) opens from that point while the cell flies on an arc into the empty left pane and lands
    on the beat where her chest will be. It is her seed: her pane's frame draws out around it and she grows out
    of it, glyph by glyph, behind a lit front; the me.* fields start typing as she appears."""
    pre, post = 0.6, 1.42
    GATHER = 0.10  # after T: one cell
    LAND = 0.46    # after T: the seed is in her pane (beat 5.697)
    FRAME = 0.34   # the pane frame draws out around the seed
    GROW = 0.92    # she has grown out of it at T + LAND + GROW (≈ 6.62, a beat)
    G = (597.0, 240.0)

    def seed(self):
        if not hasattr(self, "_seed"):
            x, y = her_mod().her_anchor(self.T + self.LAND + 0.2, "chest")
            self._seed = (round(x), round(y))
        return self._seed

    def grown(self, t, n):
        """Her layer (no frame) revealed outward from the seed, with a lit front."""
        v2 = her_mod()
        layer = v2.her(t, n, 0.0, 0.0).copy()
        x0, y0, x1, y1 = kit.LEFT
        S_ = self.seed()
        u = clamp((t - (self.T + self.LAND + 0.04)) / self.GROW)
        if u >= 1:
            return layer
        rmax = max(math.hypot(S_[0] - x, S_[1] - y) for x in (x0, x1) for y in (y0, y1)) + 20
        r = rmax * ease_io(u) if u > 0 else 0.0
        cw, ch = 6, 9
        cols, rows = (x1 - x0) // cw + 1, (y1 - y0) // ch + 1
        m, fr = Image.new("L", (cols, rows), 0), Image.new("L", (cols, rows), 0)
        M, FR = m.load(), fr.load()
        for q in range(cols):
            for rr in range(rows):
                dd = math.hypot(x0 + q * cw + cw / 2 - S_[0], y0 + rr * ch + ch / 2 - S_[1])
                p = clamp((r - dd) / 30.0)
                M[q, rr] = int(255 * p)
                if 0 < p < 1:
                    FR[q, rr] = int(255 * (1 - abs(2 * p - 1)))
        size = (cols * cw, rows * ch)
        m = m.resize(size, Image.NEAREST).crop((0, 0, x1 - x0, y1 - y0))
        fr = fr.resize(size, Image.NEAREST).crop((0, 0, x1 - x0, y1 - y0))
        a = layer.getchannel("A")
        sub = a.crop(kit.LEFT)
        a.paste(ImageChops.multiply(sub, m), kit.LEFT[:2])
        layer.putalpha(a)
        front = Image.new("RGBA", (x1 - x0, y1 - y0), HOT + (0,))
        front.putalpha(ImageChops.multiply(sub, fr))
        layer.alpha_composite(front, kit.LEFT[:2])
        return layer

    def render(self, t, n):
        T = self.T
        G, S_ = self.G, self.seed()
        land = T + self.LAND
        oc, octx = self.old(t, n, cells=False)
        nc, nctx = self.new(t, n)
        bg = kit.stage.background(t)
        stage1 = reveal(oc, bg, t, inward(G, T - 0.52, T + 0.08, 760.0), region=FULLR, seed=3)
        # the object's own pane opens from the point where the weights gathered, as the seed leaves it
        content = reveal(stage1, nc, t, radial(G, T + self.GATHER, 1400.0), region=FULLR, seed=33)
        over = blank()
        d = ImageDraw.Draw(over)
        lift = clamp((t - (T - self.pre)) / 0.05)
        # 1. the loaded grid gathers into one cell, turning from amber to her blue
        if t < T + self.GATHER:
            maxd = max(math.hypot(B.cell_center(i)[0] - G[0], B.cell_center(i)[1] - G[1]) for i in range(161))
            fl = tk.font(tk.F_MONO, 13)
            arrived = 0
            for i in sorted(range(B.GRID["n"]), key=lambda i: -math.hypot(B.cell_center(i)[0] - G[0],
                                                                        B.cell_center(i)[1] - G[1])):
                cx, cy = B.cell_center(i)
                dist = math.hypot(cx - G[0], cy - G[1])
                # the far cells go first: each shrinks to a point in a quarter second, then rushes in; the grid
                # drains toward its centre over half a second (evenly, so the picture never drops at once)
                t0 = T - 0.55 + 0.3 * (1 - dist / maxd)
                s = clamp((t - t0) / 0.25)
                v = clamp((t - t0 - 0.1) / (T + self.GATHER - t0 - 0.1))
                if v >= 1:
                    arrived += 1
                    continue
                x, y = lerp((cx, cy), G, ease_in(v))
                hw, hh = lerp(21, 3, s), lerp(18, 3, s)
                col = lerp(B.lit(tk.amb(0.55), 0.3 * lift), tk.BLUE_HI, s)
                d.rectangle([x - hw, y - hh, x + hw, y + hh], fill=tuple(int(c_) for c_ in col) + (255,))
                if s < 0.3:
                    d.text((x - hw + 6, y - hh + 10), f"{i + 1:03d}", font=fl, fill=tk.BG + (int(255 * (1 - s / 0.3)),))
            k = arrived / B.GRID["n"]
            if k > 0:
                sp = Image.new("RGBA", (12, 12), (0, 0, 0, 0))
                ImageDraw.Draw(sp).rectangle([1, 1, 9, 9], fill=tk.BLUE_HI + (255,))
                place(over, haloed(sp, 0.4 + 0.6 * k, radius=6), G, 1.0, min(1.0, 0.4 + k))
        # 2. the 8x8 cell flies on an arc into her pane and becomes her seed
        elif t < land:
            u = clamp((t - (T + self.GATHER)) / (self.LAND - self.GATHER))
            for gdt, ga in ((0.05, 0.25), (0.025, 0.5), (0.0, 1.0)):
                ug = clamp(u - gdt)
                x, y = bezier(G, S_, 0.28, ease_back(ug, 1.0) if gdt == 0 else ease_io(ug))
                s = 4.5 + 4.5 * math.sin(math.pi * ug)  # an 8x8 cell, larger in flight
                sp = Image.new("RGBA", (int(2 * s) + 2, int(2 * s) + 2), (0, 0, 0, 0))
                ImageDraw.Draw(sp).rectangle([1, 1, 2 * s, 2 * s], fill=tk.BLUE_HI + (255,))
                place(over, haloed(sp, 0.9, radius=6) if gdt == 0 else sp, (x, y), 1.0, ga)
        # 3. her pane's frame draws out around the seed
        her_alpha = 0.0
        if t >= land:
            e = ease_out((t - land) / self.FRAME)
            rect = lerp((S_[0] - 4, S_[1] - 4, S_[0] + 4, S_[1] + 4), kit.LEFT, e)
            if t >= T + self.LAND + 0.04:
                over.alpha_composite(kit.her_glow(self.grown(t, n), 0.8 * max(0.0, 1 - (t - land) / 0.5)))
            layer = blank()
            level = 0.45 + 0.35 * kit.engine.pulse(t)
            title = "/dev/me  pid 4471" if e > 0.97 else ""
            tk.box(ImageDraw.Draw(layer), *rect, title, level if e > 0.97 else level + 0.35 * (1 - e),
                   spinner=t if title else None)
            over.alpha_composite(layer)
            k = max(0.0, 1 - (t - land) / self.GROW)
            if k > 0:  # the seed itself, fading as she takes its place
                s = 4 + 3 * kit.engine.pulse(t)
                sp = Image.new("RGBA", (int(2 * s) + 2, int(2 * s) + 2), (0, 0, 0, 0))
                ImageDraw.Draw(sp).rectangle([1, 1, 2 * s, 2 * s], fill=tk.BLUE_HI + (255,))
                place(over, haloed(sp, 0.9 * k, radius=6), S_, 1.0, k)
            if t >= T + self.LAND + 0.04 + self.GROW and e >= 1:
                return Frame(content, nctx, None, 0.0, None, 1.0)
        return Frame(content, self.pick(t, octx, nctx), over, 0.0, None, her_alpha)


# ---------------------------------------------------------------- cut 4: the object's fields stay

class C04(Cut):
    """creation -> parameters. RETAIN: the me.* block lights up before the cut and stays exactly where it is;
    the chrome retracts into the shell staging and the Object() frame fades with it. She does not change. Row by
    row, the block is then filled in with config.json in place."""
    pre, post = 0.22, 0.34

    def render(self, t, n):
        T = self.T
        k = clamp((t - (T - self.pre)) / 0.12) * (1 - clamp((t - T) / 0.16))
        if t < T:
            oc, octx = self.old(t, n, lift=0.55 * k)
            return Frame(oc, octx)
        nc, nctx = self.new(t, n, lift=0.55 * k)
        e = ease_out((t - T) / 0.3)
        layer = blank()
        tk.box(ImageDraw.Draw(layer), *B.PANE_BOX, "me = Object()", 0.5, spinner=t + 0.3)
        return Frame(nc, nctx, tk.scale_alpha(layer, 1 - e), under=True)


# ---------------------------------------------------------------- cut 5: the parameter count titles the histogram

def _sprite_center(s, size, xy):
    sp, off = text_sprite(s, tk.F_HEAD, size, tk.blue(0.95))
    return sp, (xy[0] + off[0] + sp.width / 2, xy[1] + off[1] + sp.height / 2)


class C05(Cut):
    """parameters -> init. CARRY: the finished count '552,000,000,000 params' lights up, rises on an arc and
    lands as the histogram's title on the beat. The config rows give way outward from that title slot, ahead of
    the count (it never crosses a line of text), and the weights rise from the baseline under it as it climbs.
    'seed = you' sits on the line below the title."""
    pre, post = 0.3, 0.62
    LAND = 0.46  # beat 10.312
    GROW = 0.20  # the bars start rising (half a beat before the count lands)

    def render(self, t, n):
        T = self.T
        land = T + self.LAND
        oc, octx = self.old(t, n, counter=False)
        nc, nctx = self.new(t, n)
        _, slot = _sprite_center(B.COUNT_TEXT, B.TITLE_SIZE, B.TITLE_XY)
        content = reveal(oc, nc, t, radial((B.TITLE_XY[0], slot[1]), T - 0.34, 2000.0), seed=5)
        over = blank()
        if t < land:
            lift = clamp((t - (T - self.pre)) / 0.2)
            sp, c0 = _sprite_center(B.COUNT_TEXT, B.COUNT_SIZE, B.COUNT_XY)
            _, c1 = _sprite_center(B.COUNT_TEXT, B.TITLE_SIZE, B.TITLE_XY)
            u = clamp((t - (T - 0.06)) / (self.LAND + 0.06))
            xy = bezier(c0, c1, -0.1, ease_back(u, 0.35))
            scale = lerp(1.0, B.TITLE_SIZE / B.COUNT_SIZE, ease_io(u)) * (1 + 0.1 * math.sin(math.pi * u))
            s2 = kit.brighten(sp, 0.35 * lift * (1 - u))
            place(over, haloed(s2, 0.8 * lift * (1 - 0.6 * u)) if lift > 0 else s2, xy, scale)
        return Frame(content, self.pick(t, octx, nctx), over)


# ---------------------------------------------------------------- cut 6: the bars become the globe

class C06(Cut):
    """init -> world. MORPH: the settled bars light up and break into columns of dots; every dot flies to a
    point of the globe (a bar's top to the globe's upper rim, its body to the latitudes below), centre bars first,
    and turns into the globe's glyph as it arrives. The globe is whole on the beat and keeps turning."""
    pre, post = 0.26, 0.32
    T0, T1 = -0.23, 0.23  # beats 10.774 and 11.235

    def sources(self):
        if not hasattr(self, "_bars"):
            a = self.a
            ts = self.T + self.T0
            self._bars = B.init_bars(ts, (ts - a.start) / (a.end - a.start))
        return self._bars

    def render(self, t, n):
        T = self.T
        oc, octx = self.old(t, n, bars=False)
        nc, nctx = self.new(t, n, globe=t >= T + self.T1)
        content = reveal(oc, nc, t, radial((B.GLOBE["cx"], B.GLOBE["cy"]), T - 0.12, 1400.0), seed=6)
        over = blank()
        d = ImageDraw.Draw(over)
        bars = self.sources()
        lift = clamp((t - (T - self.pre)) / 0.1)
        ms = T + self.T0
        if t < ms + 0.14:  # the bars, lit; their bodies thin out into the columns of dots
            k = clamp((t - (ms - 0.06)) / 0.2)
            hw = 4.5 * (1 - ease_io(k))
            for xx, hgt, v in bars:
                if hgt > 0 and hw > 0.3:
                    col = B.lit(tk.amb(0.35 + 0.6 * v), 0.4 * lift)
                    d.rectangle([xx + 4.5 - hw, B.INIT_BASE - hgt, xx + 4.5 + hw, B.INIT_BASE],
                                fill=col + (int(255 * (1 - 0.5 * k)),))
        if t >= ms - 0.06 and t < T + self.T1 + 0.02:
            R, cx, cy = B.GLOBE["R"], B.GLOBE["cx"], B.GLOBE["cy"]
            f = tk.font(tk.F_MONO_B, 15)
            span = self.T1 - self.T0
            for gx, gy, z in B.globe_points(t):
                fx = clamp((gx - (cx - R)) / (2 * R))
                fy = clamp((gy - (cy - R)) / (2 * R))
                xx, hgt, v = bars[min(59, max(0, round(fx * 59)))]
                sx, sy = xx + 4.5, B.INIT_BASE - hgt * (1 - fy)
                t0 = ms + 0.1 * abs(fx - 0.5) * 2
                u = ease_io(clamp((t - t0) / (span - 0.1)))
                x, y = lerp((sx, sy), (gx, gy), u)
                if u < 0.6:
                    col = B.lit(tk.amb(0.35 + 0.6 * v), 0.4 * (1 - u))
                    d.rectangle([x - 4, y - 1, x + 4, y + 1], fill=col + (255,))
                else:
                    d.text((x - 4, y - 8), B.globe_glyph(z), font=f, fill=tk.amb(0.35 + 0.65 * z) + (255,))
        return Frame(content, self.pick(t, octx, nctx), over)


# ---------------------------------------------------------------- cut 7: me and you go into the status line

ROWS = 18  # countdown digit height in cell rows (the original 14 left most of the pane empty)


def _word_box(word):
    f = tk.font(tk.F_MONO_B, 18)
    i = B.POP_TEXT.index(word + ("," if word == "me" else ")"))
    x = B.POP_XY[0] + f.getlength(B.POP_TEXT[:i])
    l, tp, r, b = f.getbbox(B.POP_TEXT)
    return x - 3, B.POP_XY[1] + tp - 3, x + f.getlength(word) + 3, B.POP_XY[1] + b + 3


class C07(Cut):
    """world -> begin_sim. CARRY+MORPH: me and you light up and leave their orbits; each flies into its own word
    of the population line, which stays where it is and becomes the simulation's status line, and locks in as an
    inverted chip. The globe's dots collapse into the dot-matrix '3' of the countdown, which is whole on the beat:
    the countdown is built from the world."""
    pre, post = 0.26, 0.45
    LAND = 0.23  # beat 12.62

    def cells(self):
        if not hasattr(self, "_cells"):
            self._cells = sorted(S.countdown_cells(3, ROWS), key=lambda c: (c[1], c[0]))
        return self._cells

    def render(self, t, n):
        T = self.T
        land = T + self.LAND
        oc, octx = self.old(t, n, globe=False, markers=False)
        nc, nctx = self.new(t, n, count=t >= land)
        content = reveal(oc, nc, t, radial((B.GLOBE["cx"], B.GLOBE["cy"]), T - 0.1, 1500.0), seed=7)
        over = blank()
        d = ImageDraw.Draw(over)
        lift = clamp((t - (T - self.pre)) / 0.12)
        f15, f16 = tk.font(tk.F_MONO_B, 15), tk.font(tk.F_MONO_B, 16)
        if t < land:
            # the globe gathers into the '3'
            pts = sorted(B.globe_points(t), key=lambda p: (p[1], p[0]))
            cells = self.cells()
            for j, (gx, gy, z) in enumerate(pts):
                cx_, cy_, ch = cells[j * len(cells) // len(pts)]
                t0 = T - 0.16 + 0.06 * (j / len(pts))
                u = ease_io(clamp((t - t0) / (land - t0)))
                x, y = lerp((gx - 4, gy - 8), (cx_, cy_), u)
                if u < 0.7:
                    d.text((x, y), B.globe_glyph(z), font=f15,
                           fill=B.lit(tk.amb(0.35 + 0.65 * z), 0.3 * lift) + (255,))
                else:
                    d.text((x, y), ch, font=f16, fill=tk.amb(0.95) + (255,))
            # me and you leave their orbits for their words in the status line
            for k, word in enumerate(("me", "you")):
                x0, y0, x1, y1 = _word_box(word)
                gx, gy = B.marker_pos(min(t, T - 0.1), k)
                u = clamp((t - (T - 0.1)) / (self.LAND + 0.1))
                x, y = bezier((gx, gy), ((x0 + x1) / 2, (y0 + y1) / 2), 0.22 if k else -0.22, ease_back(u, 0.9))
                col = B.MARKERS[k][1](1.0)
                s = lerp(5, (x1 - x0) / 2, ease_in(u)), lerp(5, (y1 - y0) / 2, ease_in(u))
                sp = Image.new("RGBA", (int(2 * s[0]) + 2, int(2 * s[1]) + 2), (0, 0, 0, 0))
                ImageDraw.Draw(sp).rectangle([1, 1, 2 * s[0], 2 * s[1]], fill=B.lit(col, 0.5 * lift) + (255,))
                place(over, haloed(sp, 0.9 * lift * (1 - 0.5 * u), radius=5), (x, y), 1.0 + 0.6 * math.sin(math.pi * u))
                if u < 0.6:
                    text_at(over, word, tk.F_MONO_B, 16, B.lit(col, 0.5 * lift), (x + 10 + 6 * u, y - 10),
                            1.0 + 0.5 * math.sin(math.pi * u), 1 - u / 0.6)
                elif u > 0.72:  # the square is becoming the word's chip: the word shows through it, inverted
                    d.text((x0 + 3, B.POP_XY[1]), word, font=tk.font(tk.F_MONO_B, 18),
                           fill=tk.BG + (int(255 * clamp((u - 0.72) / 0.15)),))
        return Frame(content, self.pick(t, octx, nctx), over)


RUN_U = 0.55  # begin_sim's countdown ends and RUN starts at this fraction of the shot (scenes.shot_begin_sim)


def pop_line(c):
    """begin_sim's status line: the world's population line, kept, with me and you locked in as chips. When the
    countdown ends the screen is cleared for RUN and the line is erased left to right with it (cut 8 lands the
    token counter on this row)."""
    d = c.d
    f = tk.font(tk.F_MONO_B, 18)
    gone = (c.lt - RUN_U * c.dur) / 0.22
    if gone >= 1:
        return
    text = B.POP_TEXT if gone <= 0 else B._mixed(B.POP_TEXT, "", gone, c.rng)
    d.text(B.POP_XY, text, font=f, fill=tk.amb(0.9))
    land = ALL[7].start + C07.LAND
    if c.t < land:
        return
    k = max(0.0, 1 - (c.t - land) / 0.3)
    for word, col in (("me", tk.blue), ("you", tk.amb)):
        x0, y0, x1, y1 = _word_box(word)
        if gone > 0 and (x0 - B.POP_XY[0]) / f.getlength(B.POP_TEXT) < gone:
            continue
        d.rectangle([x0, y0, x1, y1], fill=B.lit(col(0.95), 0.6 * k))
        d.text((x0 + 3, B.POP_XY[1]), word, font=f, fill=tk.BG)


CUTS = {1: C01, 2: C02, 3: C03, 4: C04, 5: C05, 6: C06, 7: C07}
OWN = {0: own_power}


def setup(v1):
    """Hooks that hold for whole shots (idempotent: a lazy `import v2` calls this again)."""
    T2, T5 = v1.ALL[2].start, v1.ALL[5].start
    c2 = C02(v1.ALL[1], v1.ALL[2])
    landed = c2.landed()
    # the ordered loading resumes after the last dot and is whole before cut 3 starts gathering the grid
    C.SHOT_HOOKS["shot_pieces"] = {"landed": landed, "seq_t0": max(landed.values()) - T2 + 0.05,
                                   "seq_end": v1.ALL[3].start - C03.pre - 0.04 - T2}
    C.SHOT_HOOKS["shot_init"] = {"title_t": T5 + C05.LAND, "grow_t": T5 + C05.GROW, "seed_t": T5 + C05.LAND + 0.04}
    C.SHOT_HOOKS["shot_world"] = {"radius": 1.0, "mark_t": beat(25)}  # "our new world" (11.697)
    C.SHOT_HOOKS["shot_begin_sim"] = {"rows": ROWS, "extra": pop_line}
