"""The cuts of the 01 PRETRAIN sample (CONTINUITY_V2_PLAN.md section 7, cuts 8-20), each staged by hand.

A cut owns a window around its time T. Inside it, the outgoing scene keeps running past its end and the incoming
one starts on time; the cut decides which objects cross (drawn as ink on the carrier layer), how the rest of the
old drawing gives way (per-cell glyph switch from a seed, never a band wipe), and whether she reacts.
"""
from __future__ import annotations

import math
import random

from PIL import Image, ImageDraw

import kit
import scenes as S
from kit import (BEAT, FPS, H, PANE, W, bezier, blank, brighten, clamp, ease_back, ease_in, ease_io, ease_out,
                 haloed, ink, inward, lerp, place, radial, reveal, sweep, text_sprite, tk)

def rgba(col, a: float = 255) -> tuple:
    return tuple(int(v) for v in col[:3]) + (int(a),)


# persistent per-shot hooks: what an earlier transition left behind stays for the whole shot
SHOT_HOOKS: dict = {}
DELAY: dict = {}  # shot name -> seconds its own clock starts late (it waits for the carrier to land)


def body(shot, t: float, n: int, hooks: dict | None = None):
    """The shot's own drawing at time t (it may run past its end), before chrome and without her.
    SHOT_HOOKS and DELAY are keyed by shot name, or by shot index for scenes used more than once."""
    name = shot.fn.__name__
    idx = kit.v1.INDEX[id(shot)]
    kit.HOOK.clear()
    kit.HOOK.update(SHOT_HOOKS.get(name, {}))
    kit.HOOK.update(SHOT_HOOKS.get(idx, {}))
    kit.HOOK.update(hooks or {})
    te = max(shot.start, t - DELAY.get(idx, DELAY.get(name, 0.0)))
    kit.STUB_ON[0] = True
    try:
        b = kit.sb.body(te, n, shot)
    finally:
        kit.STUB_ON[0] = False
        kit.HOOK.clear()
    canvas = b["canvas"].convert("RGB")
    if b["kind"] == "full" and not b["black"]:
        # a full-width painting stays inside the body viewport (the chrome frames it)
        clipped = kit.stage.background(te)
        clipped.paste(canvas.crop(kit.engine.FULL), kit.engine.FULL[:2])
        canvas = clipped
    return canvas, b["ctx"]


class Frame:
    """What a cut hands to the frame loop. her_shift / her_alpha override the automatic pane slide (full-width
    art) and visibility; under=True draws the carriers below her instead of above."""

    def __init__(self, content, ctx, over=None, glow: float = 0.0, her_shift=None, her_alpha: float = 1.0,
                 under: bool = False):
        self.content, self.ctx, self.over, self.glow = content, ctx, over, glow
        self.her_shift, self.her_alpha, self.under = her_shift, her_alpha, under


class Cut:
    pre, post = 0.3, 0.5

    def __init__(self, a, b):
        self.a, self.b, self.T = a, b, b.start

    def active(self, t: float) -> bool:
        return self.T - self.pre <= t < self.T + self.post

    def old(self, t, n, **hooks):
        return body(self.a, t, n, hooks)

    def new(self, t, n, **hooks):
        return body(self.b, max(t, self.T), n, hooks)

    def pick(self, t, oc, nc):
        return oc if t < self.T else nc

    def render(self, t: float, n: int) -> Frame:
        raise NotImplementedError


def text_at(layer, s, path, size, color, xy, scale=1.0, alpha=1.0, halo=0.0, lift=0.0):
    """Draw text as a sprite whose draw origin is xy (scaled about its centre)."""
    sp, off = text_sprite(s, path, size, color)
    if lift > 0:
        sp = brighten(sp, lift)
    if halo > 0:
        sp2 = haloed(sp, halo)
        pad = (sp2.width - sp.width) // 2
        sp, off = sp2, (off[0] - pad, off[1] - pad)
    cx, cy = xy[0] + off[0] + sp.width / 2, xy[1] + off[1] + sp.height / 2
    place(layer, sp, (cx, cy), scale, alpha)


# ---------------------------------------------------------------- cut 8: RUN breaks into the corpus

class C08(Cut):
    """begin_sim -> corpus. RUN lights up on the lift, then breaks into word chips that fly out to their places in
    the token river; the river decodes outward from RUN. 'tokens budget' flies down and becomes the counter."""
    pre, post = 0.3, 0.62
    ORIGIN = (575, 262)
    SPEED = 1500.0

    def chips(self):
        if not hasattr(self, "_chips"):
            rng = random.Random(8)
            f = tk.font(tk.F_HEAD, 120)
            mask = Image.new("L", (400, 180), 0)
            ImageDraw.Draw(mask).text((0, 0), "RUN", font=f, fill=255)
            M = mask.load()
            inside = [(x, y) for x in range(0, 400, 3) for y in range(0, 180, 3) if M[x, y] > 128]
            chips = []
            T = self.T
            for j in range(26):
                sx, sy = rng.choice(inside)
                land_guess = T + 0.05 + 0.3
                toks = S.corpus_tokens(land_guess)
                x, y, tok, lv = toks[(j * 37 + 11) % len(toks)]
                d = math.hypot(x - self.ORIGIN[0], y - self.ORIGIN[1])
                tl = T + 0.06 + d / self.SPEED
                chips.append(dict(src=(460 + sx, 200 + sy), dst=(x, y), tok=tok, lv=lv, tl=max(T + 0.14, tl),
                                  bend=rng.uniform(-0.25, 0.25)))
            self._chips = chips
        return self._chips

    def render(self, t, n):
        T = self.T
        oc, octx = self.old(t, n, run=False, budget=False)
        nc, nctx = self.new(t, n, counter=t >= T + 0.46)
        delay = radial(self.ORIGIN, T + 0.06, self.SPEED)
        content = reveal(oc, nc, t, delay, seed=8)
        over = blank()
        lift = clamp((t - (T - self.pre)) / self.pre)
        if t < T + 0.12:  # RUN, lit, breaking apart
            a = 1.0 if t < T else 1 - (t - T) / 0.12
            text_at(over, "RUN", tk.F_HEAD, 120, tk.amb(1.0), (460, 200), 1 + 0.06 * lift, a, halo=0.8 * lift,
                    lift=0.35 * lift)
        if t >= T:
            for ch in self.chips():
                u = clamp((t - T) / (ch["tl"] - T))
                if t > ch["tl"] + 0.1:
                    continue
                pos = bezier(ch["src"], ch["dst"], ch["bend"], ease_out(u))
                a = 1.0 if t <= ch["tl"] else 1 - (t - ch["tl"]) / 0.1
                text_at(over, ch["tok"], S.corpus_font(ch["tok"]).path, 15, tk.amb(1.0), pos,
                        2.1 - 1.1 * ease_out(u), a, halo=0.9 * (1 - u))
        # the budget line becomes the counter
        if t < T + 0.56:
            u = clamp((t - T) / 0.46)
            xy = bezier((460, 440), (430, 572), 0.18, ease_back(u, 0.9))
            a = 1.0 if t < T + 0.46 else 1 - (t - T - 0.46) / 0.1
            text_at(over, f"tokens budget: {S.F.PRETRAIN_TOKENS}", tk.F_MONO, 20, tk.amb(0.95), xy, 1.0, a,
                    halo=0.7 * lift * (1 - u), lift=0.3 * (1 - u))
        return Frame(content, self.pick(t, octx, nctx), over)


# ---------------------------------------------------------------- cut 9: the corpus pours into the loss curve

class C09(Cut):
    """corpus -> losscurve. The words accelerate into one point, the origin of the loss curve, which starts
    drawing from there; the token counter moves under the chart as its x label."""
    pre, post = 0.42, 0.5

    def origin(self):
        return S.loss_points()[0][1:]

    def render(self, t, n):
        T = self.T
        O = self.origin()
        oc, octx = self.old(t, n, words=False, counter=False)
        label = S.counter_text(T)
        land = T + 0.42
        nc, nctx = self.new(t, n, xlabel=label if t >= land else None)
        content = reveal(oc, nc, t, radial(O, T, 1300.0), seed=9)
        over = blank()
        d = ImageDraw.Draw(over)
        t0 = T - self.pre
        arrived = 0
        for j, (x, y, tok, lv) in enumerate(S.corpus_tokens(min(t, T + 0.1))):
            dist = math.hypot(x - O[0], y - O[1])
            ts = t0 + 0.22 * (1 - min(1.0, dist / 800))  # the far words set off first
            ta = T + 0.05 + 0.2 * ((j * 7919) % 97) / 97
            u = clamp((t - ts) / (ta - ts))
            if u >= 1:
                arrived += 1
                continue
            e = ease_in(u)
            px, py = x + (O[0] - x) * e, y + (O[1] - y) * e
            size = max(7, int(15 - 8 * e))
            lvl = lv + (1 - lv) * e
            col = tk.amb(lvl)
            a = 1.0 if u < 0.75 else (1 - u) / 0.25
            d.text((px, py), tok, font=S.corpus_font(tok, size), fill=col + (int(255 * a),))
        if t0 < t < T + 0.45:  # the origin takes them in
            k = min(1.0, arrived / 120) * (1 - clamp((t - T - 0.25) / 0.2))
            r = 2 + 5 * k
            d.ellipse([O[0] - r, O[1] - r, O[0] + r, O[1] + r], fill=tk.blue(1.0) + (int(255 * min(1, 0.3 + k)),))
        if t < land + 0.08:
            lift = clamp((t - t0) / 0.3)
            u = clamp((t - T) / (land - T))
            xy = bezier((430, 572), (446, 400), -0.2, ease_back(u, 0.8))
            scale = 1 - (1 - 13 / 18) * ease_io(u)
            a = 1.0 if t < land else 1 - (t - land) / 0.08
            text_at(over, label, tk.F_MONO_B, 18, tk.amb(0.95), xy, scale, a, halo=0.6 * lift * (1 - u),
                    lift=0.3 * (1 - u))
        return Frame(content, self.pick(t, octx, nctx), over)


# ---------------------------------------------------------------- cut 10: the loss curve rewinds into DualPipe

class C10(Cut):
    """losscurve -> dualpipe. The endpoint grows and runs back along the curve, eating it, to the origin; there it
    hops into the first cell of pipeline rank 0, and the schedule unrolls from that cell."""
    pre, post = 0.35, 0.6
    LAND = 0.42  # after T: the first F cell is placed

    def render(self, t, n):
        T = self.T
        t0, t1, t2 = T - 0.35, T - 0.1, T + 0.3
        r = 1.0 - ease_io((t - t1) / (t2 - t1))
        u_end, ex, ey = S.loss_at(max(0.02, r))
        oc, octx = self.old(t, n, **({"progress": max(0.02, r), "label": False} if t >= t1 else {}))
        nc, nctx = self.new(t, n)
        O = S.loss_points()[0][1:]
        content = reveal(oc, nc, t, inward(O, T - 0.15, T + 0.32, 760.0), seed=10)
        over = blank()
        d = ImageDraw.Draw(over)
        grow = clamp((t - t0) / 0.2)
        if t < t2:
            rad = 1.5 + 4.5 * grow
            place(over, haloed(self.dot(rad), 0.9 * grow), (ex + 1, ey + 1))
            lab = S.loss_label(1.0)
            k = clamp((t - t1) / (t2 - t1))
            text_at(over, lab, tk.F_MONO_B, 16, tk.amb(1.0), (ex - 80 + 60 * k, ey - 26), 1 - 0.4 * k,
                    1 - ease_in(k), lift=0.3 * grow)
        else:
            u = clamp((t - t2) / (T + self.LAND - t2))
            e = ease_back(u, 1.0)
            P = S.PIPE
            cell = (P["ox"], P["oy"], P["ox"] + P["cw"] - 3, P["oy"] + P["ch"] - 6)
            cx, cy = lerp(O, ((cell[0] + cell[2]) / 2, (cell[1] + cell[3]) / 2), e)
            w, hh = lerp(12, cell[2] - cell[0], ease_io(u)), lerp(12, cell[3] - cell[1], ease_io(u))
            if t < T + self.LAND + 0.05:
                col = tk.blue(1.0) if u < 0.5 else tk.amb(0.75 + 0.25 * (1 - u))
                d.rectangle([cx - w / 2, cy - hh / 2, cx + w / 2, cy + hh / 2], fill=rgba(col))
                if u > 0.6:
                    d.text((cx - w / 2 + 7, cy - hh / 2 + 13), "F", font=tk.font(tk.F_MONO_B, 11), fill=tk.BG + (255,))
        return Frame(content, self.pick(t, octx, nctx), over)

    @staticmethod
    def dot(rad):
        s = int(rad * 2 + 4)
        im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        ImageDraw.Draw(im).ellipse([2, 2, s - 2, s - 2], fill=tk.blue(1.0) + (255,))
        return im


# ---------------------------------------------------------------- cut 11: pipeline cells swim off as the whale

class C11(Cut):
    """dualpipe -> whale. Rank by rank, the pipeline's cells lift off as letters and swim to their places in the
    whale; the whale is complete when the last rank lands."""
    pre, post = 0.3, 0.42
    FLY = 0.42

    def depart(self, r):
        return self.T - 0.3 + r * 0.03

    def render(self, t, n):
        T = self.T
        a, b = self.a, self.b
        lt_a = t - a.start
        cells, _ = S.pipe_cells(lt_a, a.end - a.start, C10.LAND)
        gone = lambda r, s: clamp((t - self.depart(r)) / 0.06)  # noqa: E731
        oc, octx = self.old(t, n, gone=gone, notes=True)
        last_land = self.depart(7) + self.FLY + 0.03
        nc, nctx = self.new(t, n, whale=1.0 if t >= last_land else 0.0)
        content = reveal(oc, nc, t, radial((820, 300), T - 0.12, 1500.0), seed=11)
        over = blank()
        d = ImageDraw.Draw(over)
        ub = clamp((t - b.start) / (b.end - b.start))
        glyphs = S.whale_glyphs(max(t, T), ub if t >= T else 0.0)
        if t < last_land and cells:
            cells = sorted(cells, key=lambda c: (c[3], c[2]))
            order = sorted(range(len(glyphs)), key=lambda k: (glyphs[k][1], glyphs[k][0]))
            f = tk.font(tk.F_MONO_B, 15)
            fs = tk.font(tk.F_MONO_B, 11)
            for rank_k, k in enumerate(order):
                r, s, cx, cy, kind = cells[rank_k * len(cells) // len(glyphs)]
                td = self.depart(r) + (k % 3) * 0.01
                u = clamp((t - td) / self.FLY)
                if u <= 0:
                    continue
                gx, gy, letter = glyphs[k]
                sx, sy = cx + 6 + (k % 3) * 5, cy + 10 + (k % 2) * 12
                px, py = bezier((sx, sy), (gx, gy), 0.18 if r % 2 else -0.18, ease_io(u))
                if u < 0.55:
                    col = tk.amb(0.9) if kind == "F" else tk.blue(0.8) if kind != "W" else tk.amb(0.7)
                    d.text((px, py), kind[0], font=fs, fill=col + (255,))
                else:
                    d.text((px, py), letter, font=f, fill=tk.blue(0.95) + (255,))
        return Frame(content, self.pick(t, octx, nctx), over)


# ---------------------------------------------------------------- cut 12: every letter of the whale becomes a point

class C12(Cut):
    """whale -> points. Each letter shrinks into a dot where it stands; the dots then set off from there and
    scatter into the point set that the next scene will gather into her shape."""
    pre, post = 0.22, 0.5

    def render(self, t, n):
        T = self.T
        a = self.a
        ua = lambda tt: clamp((tt - a.start) / (a.end - a.start))  # noqa: E731
        src = [(x + 4, y + 8) for x, y, _ in S.whale_glyphs(T, ua(T))]
        oc, octx = self.old(t, n, whale=0.0)
        blend = lambda i: ease_io((t - T - 0.03 * ((i * 13) % 7) / 7) / 0.42)  # noqa: E731
        nc, nctx = self.new(t, n, **({"from": (src, blend)} if t >= T else {"points": False}))
        content = reveal(oc, nc, t, radial((720, 290), T - 0.02, 3000.0), seed=12)
        over = blank()
        if t < T + 0.05:
            d = ImageDraw.Draw(over)
            k = clamp((t - (T - self.pre)) / self.pre)
            f = tk.font(tk.F_MONO_B, 15)
            for x, y, ch in S.whale_glyphs(min(t, T), ua(min(t, T))):
                if k < 0.9:
                    d.text((x, y), ch, font=f, fill=tk.blue(0.95) + (int(255 * (1 - k)),))
                r = 1 + 0.5 * k
                d.rectangle([x + 4 - r, y + 8 - r, x + 4 + r, y + 8 + r], fill=tk.blue(1.0) + (int(255 * k),))
        return Frame(content, self.pick(t, octx, nctx), over)


# ---------------------------------------------------------------- cut 13: the point portrait flies into her

class C13(Cut):
    """points -> dimension. The points, gathered into her shape, lift and fly left along an arc into her pane,
    landing on her own glyph cells; she flares as she takes them in. Her vector then streams out to the right."""
    pre, post = 0.35, 0.75

    def targets(self):
        if not hasattr(self, "_targets"):
            import v2
            layer = v2.her(self.T + 0.4)
            A = layer.crop(kit.LEFT).getchannel("A").load()
            x0, y0, x1, y1 = kit.LEFT
            cells = [(x0 + x, y0 + y) for x in range(4, x1 - x0 - 4, 2) for y in range(14, y1 - y0 - 80, 2)
                     if A[x, y] > 60]
            rng = random.Random(13)
            rng.shuffle(cells)
            self._targets = cells
        return self._targets

    def render(self, t, n):
        T = self.T
        a = self.a
        oc, octx = self.old(t, n, points=False)
        bare, _ = self.old(t, n, points=False, labels=False)
        nc, nctx = self.new(t, n)
        oc = reveal(oc, bare, t, radial((840, 170), T - 0.12, 900.0), seed=113)  # the old labels go first
        content = reveal(oc, nc, t, sweep((404, 0), (1, 0), T + 0.2, 1400.0), seed=13)
        # the old labels go quickly; the new vector streams in from her side
        over = blank()
        d = ImageDraw.Draw(over)
        tg = self.targets()
        lift = clamp((t - (T - self.pre)) / self.pre)
        pts = S.points_pos(min(t, T), clamp((min(t, T) - a.start) / (a.end - a.start)))
        for i, (x, y, col) in enumerate(pts):
            td = T - 0.12 + 0.3 * clamp((x - 440) / 260)
            u = clamp((t - td) / 0.42)
            if u >= 1 and t > td + 0.5:
                continue
            tx, ty = tg[i % len(tg)]
            px, py = bezier((x, y), (tx, ty), -0.28, ease_io(u))
            c = lerp(col, (200, 214, 255), 0.5 * lift * (1 - u))
            al = 1.0 if u < 1 else 1 - (t - td - 0.42) / 0.08
            d.rectangle([px, py, px + 2, py + 2], fill=tuple(int(v) for v in c) + (int(255 * clamp(al)),))
        glow = max(0.0, 1 - abs(t - (T + 0.42)) / 0.3) * 0.7
        return Frame(content, self.pick(t, octx, nctx), over, glow)


# ---------------------------------------------------------------- cut 14: the 'you' vector folds into a hand

class C14(Cut):
    """dimension -> circle. The received vector folds column-wise into a narrow strip, which turns into the hand of
    the first rotary pair; its circle draws around it, and the other five pairs are born from it, one per eighth."""
    pre, post = 0.3, 1.45

    def strip(self, n):
        if not hasattr(self, "_strip"):
            c, _ = self.old(self.T - 0.3, n)
            self._strip = ink(c, self.T - 0.3, S.YOU_GRID)
        return self._strip

    def spawn(self, k):
        return self.T + 0.45 + (k - 1) * BEAT / 2

    def render(self, t, n):
        T = self.T
        c0 = S.rope_center(0)

        def circles(i):
            cx, cy = S.rope_center(i)
            if i == 0:
                if t < T + 0.3:
                    return None
                return dict(sweep=clamp((t - T - 0.3) / 0.15), hand=t >= T + 0.4, labels=t >= T + 0.45)
            ts = self.spawn(i)
            if t < ts:
                return None
            u = ease_out((t - ts) / 0.2)
            return dict(cx=lerp(c0[0], cx, u), cy=lerp(c0[1], cy, u), R=lerp(18, 70, u), a=0.3 + 0.7 * u,
                        labels=u >= 1)

        oc, octx = self.old(t, n, you=t < T - 0.3)
        nc, nctx = self.new(t, n, circles=circles)
        content = reveal(oc, nc, t, radial((958, 298), T - 0.1, 1400.0), seed=14)
        over = blank()
        if t < T + 0.4:
            sp = self.strip(n)
            g0 = ((S.YOU_GRID[0] + S.YOU_GRID[2]) / 2, (S.YOU_GRID[1] + S.YOU_GRID[3]) / 2)
            if t < T + 0.05:  # fold the columns together
                u = ease_in((t - (T - 0.3)) / 0.35)
                w = max(6, round(sp.width * (1 - 0.92 * u)))
                s2 = brighten(sp.resize((w, sp.height), Image.LANCZOS), 0.15 * u)
                place(over, haloed(s2, 0.4 * u), g0)
            else:  # the strip becomes the hand of freq_0
                u = ease_io((t - (T + 0.05)) / 0.35)
                th = S.rope_theta(t, 0)
                end = (c0[0] + 35 * math.cos(th), c0[1] + 35 * math.sin(th))
                cxy = lerp(g0, end, u)
                L = lerp(sp.height, 70, u)
                wd = lerp(max(6, sp.width * 0.08), 4, u)
                target = (math.degrees(th) - 90.0 + 180.0) % 360.0 - 180.0 + 90.0  # nearest turn from upright
                ang = lerp(90.0, target, u)
                self.bar(over, cxy, L, wd, ang, lerp(tk.amb(0.6), tk.blue(0.95), u))
        return Frame(content, self.pick(t, octx, nctx), over)

    @staticmethod
    def bar(layer, c, L, w, ang, col):
        a = math.radians(ang)
        dx, dy = math.cos(a) * L / 2, math.sin(a) * L / 2
        nx, ny = -math.sin(a) * w / 2, math.cos(a) * w / 2
        pts = [(c[0] - dx + nx, c[1] - dy + ny), (c[0] + dx + nx, c[1] + dy + ny), (c[0] + dx - nx, c[1] + dy - ny),
               (c[0] - dx - nx, c[1] - dy - ny)]
        ImageDraw.Draw(layer).polygon(pts, fill=tuple(int(v) for v in col) + (255,))


# ---------------------------------------------------------------- cut 15: the first circle grows and unrolls

class C15(Cut):
    """circle -> circumference. The other five pairs shrink back into the first, which moves and grows into the
    circle that will unroll (the new scene's clock waits for it)."""
    pre, post = 0.3, 0.45
    LAND = 0.4

    def render(self, t, n):
        T = self.T
        c0 = S.rope_center(0)

        def circles(i):
            if i == 0:
                return None if t >= T - 0.05 else {}
            u = ease_in((t - (T - 0.3 + (i - 1) / FPS)) / 0.2)
            cx, cy = S.rope_center(i)
            if u >= 1:
                return None
            return dict(cx=lerp(cx, c0[0], u), cy=lerp(cy, c0[1], u), R=lerp(70, 4, u), a=1 - 0.7 * u,
                        labels=u < 0.2)

        oc, octx = self.old(t, n, circles=circles)
        land = T + self.LAND
        nc, nctx = self.new(t, n, dots=t >= land, labels=t >= land)
        content = reveal(oc, nc, t, radial((600, 240), T + 0.2, 1400.0), seed=15)
        over = blank()
        if T - 0.05 <= t < land + 0.06:
            u = ease_io((t - (T - 0.05)) / (land - T + 0.05))
            cx, cy = lerp(c0, (S.CIRC["cx"], S.CIRC["cy"]), u)
            R = lerp(70, S.CIRC["R"], u)
            d = ImageDraw.Draw(over)
            a = 255 if t < land else int(255 * (1 - (t - land) / 0.06))
            col = lerp(tk.amb(0.8), tk.blue(0.9), u)
            d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=tuple(int(v) for v in col) + (a,), width=2)
            th = S.rope_theta(t, 0)
            d.line([cx, cy, cx + R * math.cos(th), cy + R * math.sin(th)], fill=tk.blue(0.95) + (a,), width=2)
        return Frame(content, self.pick(t, octx, nctx), over)


# ---------------------------------------------------------------- cut 16: the unrolled line becomes channel i=2

class C16(Cut):
    """circumference -> sine. The unrolled blue line lifts to channel 2 and starts to wave; the other channels
    peel off it, the nearest first."""
    pre, post = 0.25, 0.7

    def render(self, t, n):
        T = self.T

        def waves(i):
            if i == 2:
                return None if t < T + 0.35 else {}
            ts = T + 0.25 + abs(i - 2) * 2 / FPS
            if t < ts:
                return None
            u = ease_out((t - ts) / 0.2)
            return dict(y0=lerp(240, 100 + i * 70, u), amp=22 * u, a=u)

        oc, octx = self.old(t, n, line=t < T - self.pre)
        nc, nctx = self.new(t, n, waves=waves)
        content = reveal(oc, nc, t, radial((600, 440), T - 0.05, 1500.0), seed=16)
        over = blank()
        if t < T + 0.35:
            d = ImageDraw.Draw(over)
            lift = clamp((t - (T - self.pre)) / 0.2)
            u = ease_io((t - T) / 0.35) if t >= T else 0.0
            fr = 0.02 * 1.7 ** 2
            pts = []
            for xs in range(0, 720, 3):
                x = lerp(440 + xs * 678 / 720, 430 + xs, u)
                y = lerp(440, 240 + 22 * math.sin((xs + t * 180) * fr), u)
                pts.append((x, y))
            if lift > 0:
                glow = blank()
                ImageDraw.Draw(glow).line(pts, fill=tk.blue(1.0) + (int(120 * lift),), width=9)
                over.alpha_composite(glow)
            d.line(pts, fill=rgba(lerp(tk.blue(1.0), (220, 228, 255), 0.4 * lift * (1 - u))), width=3)
        return Frame(content, self.pick(t, octx, nctx), over)


# ---------------------------------------------------------------- cut 17: channel 2 grows into the tangent's sine

class C17(Cut):
    """sine -> tangent. Channel 2 grows in amplitude and period until it is the big sine; the other channels slide
    away. The rider is a small copy of her, launched from her pane onto the tangent point."""
    pre, post = 0.3, 0.62
    LAND = 0.45

    def render(self, t, n):
        T = self.T
        b = self.b

        def waves(i):
            if i == 2:
                return None
            u = ease_in((t - (T - 0.2)) / 0.35)
            if u >= 1:
                return None
            return dict(y0=100 + i * 70 + (-90 if i < 2 else 90) * u, a=1 - u)

        land = T + self.LAND
        oc, octx = self.old(t, n, waves=waves)
        nc, nctx = self.new(t, n, curve=t >= T + 0.35, rider=t >= land, tangent=t >= land)
        content = reveal(oc, nc, t, sweep((404, 0), (1, 0), T, 2000.0), seed=17)
        over = blank()
        d = ImageDraw.Draw(over)
        if t < T + 0.35:
            e = ease_io((t - (T - 0.3)) / 0.65)
            lt_b = max(0.0, t - T)
            _, cam = S.tangent_state(lt_b, b.end - b.start)
            fr = 0.02 * 1.7 ** 2
            y0, A = lerp(240, S.TAN["y0"], e), lerp(22, S.TAN["A"], e)
            pts = []
            for xs in range(0, 720, 3):
                pa = (xs + t * 180) * fr + math.pi
                pb = (xs + cam) / S.TAN["k"]
                pts.append((430 + xs, y0 - A * math.sin(lerp(pa, pb, e))))
            d.line(pts, fill=tk.blue(0.9) + (255,), width=2 if e < 0.5 else 3)
        if T <= t < land + 0.02:
            u = clamp((t - (T + 0.02)) / (self.LAND - 0.02))
            rx, ry, _ = S.rider_pos(max(0.0, t - T), b.end - b.start)
            sp = S.rider_sprite(t)
            dst = (rx, ry - sp.height / 2 + 6)
            src = (204, 300)
            for g, ga in ((0.12, 0.25), (0.06, 0.45), (0.0, 1.0)):
                ug = clamp(u - g)
                if ug <= 0:
                    continue
                place(over, sp, bezier(src, dst, -0.35, ease_io(ug)), lerp(0.7, 1.0, ug), ga)
        glow = max(0.0, 1 - abs(t - (T + 0.05)) / 0.18) * 0.5
        return Frame(content, self.pick(t, octx, nctx), over, glow)


# ---------------------------------------------------------------- cut 18: the camera keeps following the rider

class C18(Cut):
    """tangent -> infinity. Only the visualisation pane pans: the camera keeps travelling toward +x after the rider
    and arrives at the context window. Her pane, the header and the lyric band do not move."""
    pre, post = 0.25, 0.3
    IN = (406, 58, 1163, 603)

    def render(self, t, n):
        T = self.T
        oc, octx = self.old(t, n)
        nc, nctx = self.new(t, n)
        e = ease_io((t - (T - self.pre)) / (self.pre + self.post))
        x0, y0, x1, y1 = self.IN
        w = x1 - x0
        out = (oc if e < 0.5 else nc).copy()
        bg = kit.stage.background(t).crop(self.IN)
        out.paste(bg, (x0, y0))
        off = round(w * e)
        if off < w:
            out.paste(oc.crop((x0 + off, y0, x1, y1)), (x0, y0))
        if off > 0:
            out.paste(nc.crop((x0, y0, x0 + off, y1)), (x1 - off, y0))
        return Frame(out, self.pick(t, octx, nctx))


# ---------------------------------------------------------------- cut 19: the wall comes down on the beat

class C19(Cut):
    """infinity -> limit. A wall drops onto the growing context bar exactly on the cut. What was past it
    shatters, the bar turns blue and thickens against it, and the impact pushes the interface chrome away."""
    pre, post = 0.18, 0.45

    def render(self, t, n):
        T = self.T
        oc, octx = self.old(t, n)
        nc, nctx = self.new(t, n, wall=t >= T + 0.02, draw_bar=t >= T + 0.2)
        content = reveal(oc, nc, t, radial((1050, 230), T, 1700.0), seed=19)
        over = blank()
        d = ImageDraw.Draw(over)
        if t < T + 0.02:
            u = ease_in((t - (T - self.pre)) / self.pre)
            y = lerp(-140, 170, u)
            d.rectangle([1040, y, 1060, y + 120], fill=tk.amb(1.0) + (255,))
        if T <= t < T + 0.2:
            u = ease_out((t - T) / 0.2)
            d.rectangle([430, 200, 1030, lerp(240, 260, u)], fill=rgba(lerp(tk.amb(0.85), tk.blue(0.8), u)))
        if T <= t < T + 0.12:
            k = 1 - (t - T) / 0.12
            d.rectangle([1036, 150, 1064, 310], outline=(235, 240, 255, int(255 * k)), width=3)
        if T <= t < T + 0.45:
            rng = random.Random(19)
            f = (t - T)
            for q in range(36):
                x0 = 1060 + (q % 9) * 8
                y0 = 202 + (q // 9) * 9
                vx, vy = rng.uniform(80, 420), rng.uniform(-260, 160)
                x, y = x0 + vx * f, y0 + vy * f + 700 * f * f
                a = int(255 * max(0.0, 1 - f / 0.45))
                d.rectangle([x, y, x + 5, y + 5], fill=tk.amb(0.85) + (a,))
        return Frame(content, self.pick(t, octx, nctx), over)


# ---------------------------------------------------------------- cut 20: the bar splits into eight power traces

class C20(Cut):
    """limit -> current. The bar pressed against the wall splits into eight lines, one per GPU, which spread to
    their rows and start to alternate on 'Switch my current'. The wall falls apart; the chrome comes back."""
    pre, post = 0.15, 0.55
    DONE = 0.4

    def render(self, t, n):
        T = self.T
        b = self.b
        oc, octx = self.old(t, n, draw_bar=t < T - self.pre)
        nc, nctx = self.new(t, n, traces=t >= T + self.DONE)
        content = reveal(oc, nc, t, radial((740, 230), T - 0.05, 1500.0), seed=20)
        over = blank()
        if t < T + self.DONE + 0.02:
            d = ImageDraw.Draw(over)
            for g in range(8):
                u = ease_io((t - (T - self.pre) - abs(g - 3.5) * 0.015) / (self.DONE + self.pre))
                live, _ = S.current_trace(g, t, max(0.0, t - T))
                thick = lerp(7.5, 1.0, u)
                pts = []
                for j, (lx, ly) in enumerate(live):
                    bx = 430 + j * 3 * 600 / 640
                    by = 200 + g * 7.5 + 3.75
                    pts.append((lerp(bx, lx, u), lerp(by, ly, u)))
                col = lerp(tk.blue(0.8), tk.amb(0.85), u)
                d.line(pts, fill=tuple(int(v) for v in col) + (255,), width=max(1, round(thick)))
        return Frame(content, self.pick(t, octx, nctx), over)


# cut index = index of the incoming shot in v1.ALL (the numbering of the audit and the plan)
CUTS = {8: C08, 9: C09, 10: C10, 11: C11, 12: C12, 13: C13, 14: C14, 15: C15, 16: C16, 17: C17, 18: C18, 19: C19,
        20: C20}


# what a transition leaves behind for the rest of the incoming shot
SHOT_HOOKS["shot_losscurve"] = {"xlabel": S.counter_text(0.0)}  # replaced with the real value by v2.setup()
SHOT_HOOKS["shot_dualpipe"] = {"delay": C10.LAND}
SHOT_HOOKS["shot_limit"] = {"bar": 1030}
DELAY["shot_circumference"] = C15.LAND
DELAY["shot_dimension"] = 0.4  # her vector is complete when it streams out of her, then the transfer starts
