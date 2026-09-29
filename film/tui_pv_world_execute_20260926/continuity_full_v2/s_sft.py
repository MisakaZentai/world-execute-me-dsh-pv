"""Section 02 SFT (cuts 21-23): current -> blind -> dizzy -> travel. Scenes in scenes_sft.py.

  cut 21  current -> blind   MORPH   the eight power traces quantise into rows of cells and lock into the attention
                                     matrix on beat 102.5; the missing rows unfold out of the landed ones. On "blind"
                                     (beat 103) the mask sweeps and a filled eye bar drops onto her eyes.
  cut 22  blind -> dizzy     CAMERA  the masked matrix lies down, starts to spin and bends into the loss landscape;
                                     every cell tumbles into the dots of its patch of the bowl, and the diagonal
                                     cell (9, 9) becomes the ball theta. Only the pane content turns. She wobbles
                                     in her pane on "So dizzy", blindfolded.
  cut 23  dizzy -> travel    CAMERA  the camera pans backwards inside the pane: the spinning bowl leaves to the right,
                                     the year strip comes in from the left and lands on beat 110.5; the eye bar
                                     lifts off her on "Oh, we can travel".
Cut 24 (travel -> unite) belongs to s_chorus1: travel ends with nothing of this section in flight.
"""
from __future__ import annotations

import math
import random

from PIL import Image, ImageChops, ImageDraw

import kit
import scenes as S
import sec_intro
import sec_verse1

import scenes_sft as SS
from cuts import Cut, Frame
from kit import (BEAT, BG, blank, clamp, ease_back, ease_in, ease_io, ease_out, lerp, radial, reveal, sweep, tk)

STUB = [sec_intro, sec_verse1]
REPLACE = SS.REPLACE
SPLIT = SS.SPLIT
beat_t = kit.engine.beat_t


# ---------------------------------------------------------------- her: a stronger wobble on "So dizzy"

def install_dizzy() -> None:
    """In memory, for the four beats of "so dizzy, so dizzy" only: the rig's wobble move circles her body about
    11 degrees each way (the default is 4.5) with the head swinging against it, and her sway may reach 14 degrees
    in that window (elsewhere it stays capped at 8). Idempotent: v2 may be imported a second time."""
    import choreo
    if getattr(choreo, "_sft_dizzy", False):
        return
    SW, BE, HE = choreo.SW, choreo.BE, choreo.HE

    def wobble(x, L, p, m, b):
        e = choreo._win(x, L, 0.5, 0.5)
        ph = math.pi * x
        m[SW] += 11.0 * math.sin(ph) * e
        m[BE] += 5.0 * math.cos(ph) * e
        m[HE] -= 6.0 * math.sin(ph + 0.8) * e
        return 0.85 * e

    choreo._MOVE_FN["wobble"] = wobble
    orig = choreo.at
    lo, hi = choreo.btime(choreo.B_DIZZY - 0.3), choreo.btime(choreo.B_DIZZY + 4.3)

    def at(t, base="shy", pinned=False):
        st = orig(t, base, pinned)
        if lo <= t < hi and st.motion is not None and not pinned:
            m = choreo._body(t, pinned)
            st.motion.sway = choreo._soft(m[SW], 14.0)
            st.motion.bend = choreo._soft(m[BE], 9.0)
            st.motion.head = choreo._soft(m[HE], 9.0)
        return st

    choreo.at = at
    choreo._drive.cache_clear()
    choreo._sft_dizzy = True


install_dizzy()


# ---------------------------------------------------------------- her eyes, for the eye bar

def _grid():
    """Her glyph grid in the pane: (cols, rows, screen x and y of cell (0, 0), cell w, cell h). Mirrors
    engine.me_pane (with a softmax under her, as in all shots of this section) and dancer.render."""
    import dancer
    x0, y0, x1, y1 = kit.LEFT
    size = (x1 - x0 - 8, y1 - 78 - y0 - 16)
    cw, chh = dancer._cell()
    cols, rows = size[0] // cw, size[1] // chh
    return cols, rows, x0 + 4 + (size[0] - cols * cw) // 2, y0 + 14 + size[1] - rows * chh, cw, chh


def eye_points(t: float, expr: str):
    """Screen centres of her two eyes at time t (the dancer in `expr`), sub-cell exact: the traced face points of
    the pose, followed through the rig's moves by finding the two eye glyphs in the posed grid."""
    import choreo
    import rig
    import v2
    from motion import Motion
    if v2.HER != "dancer":  # another figure (V2_HER=grok): no rig to follow, estimate from her head
        hx, hy = v2.her_anchor(t, "head")
        return (hx - 12, hy + 16), (hx + 12, hy + 16)
    cols, rows, ox, oy, cw, chh = _grid()
    st = choreo.at(t, expr, False)
    m = st.motion or Motion()
    fr = rig.frame(st.pose, st.flip, m, cols, rows)
    fit = rig.FIT[st.pose]
    mirror = st.flip != (min(1.0, max(0.0, m.turn)) > 0.5)
    key = []
    for fx, fy, g in fit["face"][:2]:
        c = (fx - (rig.AXIS - rig.AXIS_COL * rig.CW)) / rig.CW
        r = (fy - fit["foot"] + rig.KROWS * rig.RH) / rig.RH
        key.append((r, rig.KCOLS - c if mirror else c, g))
    (ra, ca, ga), (rb, cb, gb) = key
    want = (math.floor(rb) - math.floor(ra), math.floor(cb) - math.floor(ca))
    cand = {g: [(r, c) for r in range(rows) for c in range(cols) if fr.art[r][c] == g and fr.part[r][c] == "h"]
            for g in {ga, gb}}
    best, score = None, 1e9
    for pa in cand[ga]:
        for pb in cand[gb]:
            if pa != pb:
                s = abs(pb[0] - pa[0] - want[0]) + abs(pb[1] - pa[1] - want[1]) + 0.01 * pa[0]
                if s < score:
                    best, score = (pa, pb), s
    if best is None or score > 3:  # no face in the grid (mid-turn): her head anchor
        hx, hy = v2.her_anchor(t, "head")
        return (hx - 10, hy + 20), (hx + 10, hy + 20)
    return tuple((ox + (c + ck - math.floor(ck)) * cw, oy + (r + rk - math.floor(rk)) * chh)
                 for (r, c), (rk, ck, _) in zip(best, key))


def eyes_now(t: float):
    """Her eyes as drawn at t: while a new expression re-renders top-down after a cut (v2._her), the eyes move to
    the new pose when the scan line passes them."""
    import v2
    s = kit.engine.shot_at(t)
    i = v2.ALL.index(s)
    cur = eye_points(t, v2.call_of(s)["expr"])
    p = (t - s.start) / 0.3
    if i and p < 1 and v2.HER == "dancer":
        prev_call = v2.call_of(v2.ALL[i - 1])
        if v2.key(prev_call) != v2.key(v2.call_of(s)):
            prev = eye_points(t, prev_call["expr"])
            y0, y1 = kit.LEFT[1], kit.LEFT[3]
            scan = y0 + (y1 - y0) * ease_io(p)
            w = clamp((scan - (prev[0][1] + prev[1][1]) / 2 + 8) / 16)
            return tuple(lerp(a, b, w) for a, b in zip(prev, cur))
    return cur


# ---------------------------------------------------------------- the eye bar (OVERLAY on her, 47.4 - 51.2 s)

T_BAR = SS.T_BLIND          # it lands on "blind"
FALL = 0.3                  # seconds of fall from above her head (7 frames)
T_LIFT = beat_t(110)        # "Oh, we can travel": it lifts off
BAR_W, BAR_H = 78, 12


def bar_state(t: float):
    """(y offset, alpha, halo, width scale) of the eye bar at t, or None when it is not on screen."""
    if t < T_BAR - FALL or t >= T_LIFT + 0.3:
        return None
    if t < T_BAR:
        u = (t - (T_BAR - FALL)) / FALL
        return -84 * (1 - clamp(u) ** 2), clamp(u / 0.25), 0.9, 0.86  # it falls (gravity), lit
    if t < T_LIFT - 0.06:
        k = t - T_BAR
        bounce = 3.5 * math.sin(k * 40) * math.exp(-k / 0.05) if k < 0.2 else 0.0  # it snaps on and settles
        return bounce, 1.0, 1.0 - clamp(k / 0.25), 0.86 + 0.14 * ease_back(clamp(k / 0.14), 2.0)
    u = clamp((t - (T_LIFT - 0.06)) / 0.36)  # she takes it off: up and away, fading as it goes
    return -70 * ease_out(u), 1 - ease_io(clamp((u - 0.15) / 0.85)), 0.6 * (1 - u), 1.0 + 0.1 * u


def blindfold(t: float, n: int):
    st = bar_state(t)
    if st is None:
        return None
    dy, alpha, halo, widen = st
    (ax, ay), (bx, by) = eyes_now(t)
    import choreo
    import v2
    swing = choreo.at(t, v2.call_of(kit.engine.shot_at(t))["expr"]).motion.hair
    cx, cy = (ax + bx) / 2, (ay + by) / 2 + dy
    ang = 0.6 * math.atan2(by - ay, bx - ax)  # the band wraps round her head: it follows a head tilt half-way
    sp = bar_sprite(ang, widen, swing)
    if halo > 0.02:
        sp = kit.haloed(sp, halo, radius=5)
    layer = blank()
    kit.place(layer, sp, (cx, cy), 1.0, alpha)
    return layer


def bar_sprite(ang: float, widen: float, swing: float) -> Image.Image:
    """A filled dark band with a lit top edge and a knot whose two ribbon ends hang off the back of her head."""
    size = 200
    sp = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(sp)
    c = size / 2
    ux, uy = math.cos(ang), math.sin(ang)
    nx, ny = -uy, ux
    L, Hh = BAR_W * widen / 2, BAR_H / 2

    def pt(a, b):
        return c + ux * a + nx * b, c + uy * a + ny * b

    band = [pt(-L, -Hh), pt(L, -Hh), pt(L, Hh), pt(-L, Hh)]
    d.polygon(band, fill=(10, 14, 30, 250))
    d.line([pt(-L + 1, -Hh), pt(L - 1, -Hh)], fill=tk.blue(0.85) + (255,), width=1)
    d.line([pt(-L + 1, Hh), pt(L - 1, Hh)], fill=tk.blue(0.35) + (255,), width=1)
    for k in range(1, 6):  # weave: faint cross threads so it reads as cloth, not as a UI box
        a = -L + k * 2 * L / 6
        d.line([pt(a - 2, -Hh + 3), pt(a + 2, Hh - 3)], fill=(28, 36, 70, 255), width=1)
    kx, ky = pt(L + 2, 0)
    d.ellipse([kx - 4, ky - 4, kx + 4, ky + 4], fill=(14, 18, 38, 255), outline=tk.blue(0.6) + (255,))
    for sgn, ln in ((1, 17), (-1, 13)):  # two ribbon ends, swinging with her hair
        a0 = math.radians(70 + sgn * 16 - 30 * swing)
        ex, ey = kx + ln * math.cos(a0 + ang), ky + ln * math.sin(a0 + ang)
        d.line([kx, ky, ex, ey], fill=(14, 18, 38, 255), width=5)
        d.line([kx, ky, ex, ey], fill=tk.blue(0.45) + (255,), width=1)
    return sp


def overlay_travel(t: float, n: int):
    return blindfold(t, n) if t < T_LIFT + 0.3 else None


OVERLAY = {"shot_blind": blindfold, "shot_dizzy": blindfold, "shot_travel": overlay_travel}


# ---------------------------------------------------------------- cut 21: the power traces quantise into the matrix

ROWS21 = [round(g * 11 / 7) for g in range(8)]    # trace g lands as matrix row 0 2 3 5 6 8 9 11
UNFOLD21 = {1: 0, 4: 3, 7: 6, 10: 9}               # the other rows unfold out of the landed row above them


class C21(Cut):
    """current -> blind. The eight power traces light up, quantise into twelve dashes each (sample and hold on the
    matrix columns) and swell into cells, packing into the attention matrix row by row; the last row locks in on
    beat 102.5 and each landed row unfolds the row under it. The GPU labels decode away from the matrix origin.
    Then, on "blind" (beat 103), the mask sweeps from the top-left and the eye bar drops onto her."""
    pre, post = 0.34, 0.45
    SEG = 640 / 12

    def q_start(self, g):
        return self.T - 0.30 + g * 0.01

    def depart(self, g):
        return self.q_start(g) + 0.12

    def land(self, g):
        return self.T + BEAT / 2 - (7 - g) * 0.02

    def unfold(self, i):
        """(start, end) of gap row i sliding out of the row above."""
        g = ROWS21.index(UNFOLD21[i])
        return self.land(g) + 0.02, self.land(g) + 0.18

    def cell_a(self, t):
        land = {ROWS21[g]: self.land(g) for g in range(8)}
        land.update({i: self.unfold(i)[1] for i in UNFOLD21})
        return lambda i, j: 1.0 if t >= land[i] else 0.0

    @staticmethod
    def rect(i, j):
        x, y = SS.cell_xy(i, j)
        return x, y, x + SS.CS - 2, y + SS.CS - 2

    def render(self, t, n):
        T = self.T
        a = self.a
        oc, octx = self.old(t, n, traces=False)
        nc, nctx = self.new(t, n, cell_a=self.cell_a(t))
        content = reveal(oc, nc, t, radial((SS.MX, SS.MY), T - 0.12, 1600.0), seed=21)
        mx = (SS.MX, SS.MY, SS.MX + SS.N * SS.CS, SS.MY + SS.N * SS.CS)
        content.paste(nc.crop(mx), mx[:2])  # the matrix area held only the traces: the landed cells show as is
        over = blank()
        glow = blank()
        d, dg = ImageDraw.Draw(over), ImageDraw.Draw(glow)
        lift = clamp((t - (T - self.pre)) / 0.15)
        white = (232, 238, 255)
        for g in range(8):
            r = ROWS21[g]
            if t >= self.land(g):
                continue
            live, _ = S.current_trace(g, t, t - a.start)
            q = ease_io((t - self.q_start(g)) / 0.12)
            u = clamp((t - self.depart(g)) / (self.land(g) - self.depart(g)))
            for j in range(12):
                seg = [p for p in live if 460 + j * self.SEG <= p[0] < 460 + (j + 1) * self.SEG]
                if not seg:
                    continue
                mean = sum(p[1] for p in seg) / len(seg)
                col = lerp(lerp(tk.amb(0.85), white, 0.7 * lift), SS.cell_color(r, j), ease_out(u))
                col = tuple(int(v) for v in col) + (255,)
                if u <= 0:  # sample and hold: the wave flattens onto its mean inside each column, gaps open
                    trim = 7 * q
                    pts = [(x, y + (mean - y) * q) for x, y in seg if seg[0][0] + trim <= x <= seg[-1][0] - trim]
                    if len(pts) > 1:
                        d.line(pts, fill=col, width=2 if lift > 0.5 else 1)
                        dg.line(pts, fill=tk.blue(1.0) + (int(90 * lift),), width=7)
                    continue
                x0, x1 = seg[0][0] + 7, seg[-1][0] - 7
                e, eh = ease_io(u), ease_io(u)
                tx0, ty0, tx1, ty1 = self.rect(r, j)
                cx = lerp((x0 + x1) / 2, (tx0 + tx1) / 2, e)
                cy = lerp(mean, (ty0 + ty1) / 2, e)
                w = lerp(x1 - x0, tx1 - tx0, e) / 2
                hh = lerp(1.0, (ty1 - ty0) / 2, eh)
                d.rectangle([cx - w, cy - hh, cx + w, cy + hh], fill=col)
                if u < 0.6:
                    dg.rectangle([cx - w - 2, cy - hh - 2, cx + w + 2, cy + hh + 2],
                                 fill=tk.blue(1.0) + (int(70 * (1 - u / 0.6)),))
        for i, src in UNFOLD21.items():  # a landed row unfolds the next row out of itself
            t0, t1 = self.unfold(i)
            if not t0 <= t < t1:
                continue
            e = ease_out((t - t0) / (t1 - t0))
            for j in range(12):
                sx0, sy0, sx1, sy1 = self.rect(src, j)
                _, ty0, _, ty1 = self.rect(i, j)
                col = tuple(int(v) for v in lerp(SS.cell_color(src, j), SS.cell_color(i, j), e)) + (255,)
                y0 = lerp(sy0, ty0, e)
                d.rectangle([sx0, y0, sx1, y0 + (ty1 - ty0)], fill=col)
        for g in range(8):  # the lock-in: a landed row glows white and settles to its values in a few frames
            k = 1 - (t - self.land(g)) / 0.12
            if 0 < k <= 1:
                for j in range(12):
                    d.rectangle(self.rect(ROWS21[g], j), fill=white + (int(90 * k * k),))
        glow.alpha_composite(over)
        return Frame(content, self.pick(t, octx, nctx), glow)


# ---------------------------------------------------------------- cut 22: the matrix lies down and spins into the bowl

class C22(Cut):
    """blind -> dizzy. Only the pane content turns: the masked matrix lies down (the camera tilts over it), starts
    to spin on "So dizzy" and bends into the loss landscape; every cell tumbles and shrinks into the dots of its
    patch of the bowl, and the diagonal cell (9, 9) becomes the ball theta. The spin runs on into the scene without
    a jump (scenes_sft.dizzy_rot). Her pane, the header and the lyric band do not move."""
    pre, post = 0.3, 0.5
    M0 = (SS.MX + SS.N * SS.CS / 2 - 1.5, SS.MY + SS.N * SS.CS / 2 - 0.5)  # centre of the matrix: the plane origin
    U = SS.CS / SS.DZ["kx"]  # a matrix cell in landscape units
    BALL = (9, 9)

    def params(self, t):
        T = self.T
        return ease_io((t - (T - 0.12)) / 0.45), ease_io((t - T) / 0.42)  # lie down, bend

    def proj(self, t):
        a, b = self.params(t)
        cx, cy = lerp(self.M0, (SS.DZ["cx"], SS.DZ["cy"]), a)
        ky, kz, rot = lerp(SS.DZ["kx"], SS.DZ["ky"], a), SS.DZ["kz"] * b, SS.dizzy_rot(t)
        return lambda x, y, z=None: SS.project(x, y, rot, cx, cy, ky, kz, z)

    def shrink_t(self, i, j):
        """When cell (i, j) starts to tumble into dots: from the centre out, with a little scatter."""
        rr = random.Random(i * 31 + j).random()
        d = math.hypot(i - 5.5, j - 5.5) / 7.8
        return self.T + 0.16 * d + 0.06 * rr

    def parent(self, x, y):
        f = lambda v: min(SS.N - 1, max(0, int(math.floor(v / self.U + SS.N / 2))))  # noqa: E731
        return f(y), f(x)

    def dot_a(self, t):
        return lambda il, jl: clamp((t - self.shrink_t(*self.parent(*SS.grid_xy(il, jl))) - 0.06) / 0.14)

    def render(self, t, n):
        T = self.T
        oc, octx = self.old(t, n, matrix=False)
        bare, _ = self.old(t, n, matrix=False, labels=False)
        nc, nctx = self.new(t, n, dots=False, ball=False)
        oc = reveal(oc, bare, t, radial((990, 140), T - 0.14, 1400.0), seed=122)  # "future: masked" goes first
        content = reveal(oc, nc, t, radial((SS.DZ["cx"], SS.DZ["cy"]), T + 0.12, 1500.0), seed=22)
        layer = blank()
        d = ImageDraw.Draw(layer)
        proj = self.proj(t)
        lift = clamp((t - (T - self.pre)) / 0.2) * (1 - clamp((t - T) / 0.3))
        dot_a = self.dot_a(t)
        for il in range(SS.DZ["n"]):  # the dots of the bowl, born where their cell shrinks
            for jl in range(SS.DZ["n"]):
                al = dot_a(il, jl)
                if al <= 0.01:
                    continue
                x, y = SS.grid_xy(il, jl)
                z = SS.surface_z(x, y)
                px, py = proj(x, y, z)
                if SS.inside(px, py, 2):
                    d.rectangle([px, py, px + 2, py + 2], fill=tk.mix(SS.dot_color(z), al, BG) + (255,))
        h0 = (SS.CS - 3) / 2 / SS.DZ["kx"]  # the drawn cell leaves a gap to its neighbours, as in the scene
        fm = tk.font(tk.F_MONO, 13)
        for i in range(SS.N):
            for j in range(SS.N):
                s = ease_in((t - self.shrink_t(i, j)) / 0.18)
                if s >= 1:
                    continue
                x, y = (j - 5.5) * self.U, (i - 5.5) * self.U
                hs = h0 * (1 - s) + 0.01 * s
                ph = s * 2.4 * (1 if (i + j) % 2 else -1)  # the tumble
                cs, sn = math.cos(ph), math.sin(ph)
                pts = [proj(x + cs * u - sn * v, y + sn * u + cs * v)
                       for u, v in ((-hs, -hs), (hs, -hs), (hs, hs), (-hs, hs))]
                if all(not SS.inside(px, py) for px, py in pts):
                    continue
                if SS.masked(i, j, t):
                    col = (0, 0, 0)
                else:
                    col = tuple(int(v) for v in lerp(SS.cell_color(i, j), (232, 238, 255), 0.2 * lift))
                if (i, j) == self.BALL:
                    col = tuple(int(v) for v in lerp(col, tk.blue(1.0), s))
                d.polygon(pts, fill=col + (255,))
                if SS.masked(i, j, t) and t < T - 0.02:  # the -inf labels stay with their cells until the turn
                    k = clamp((T - 0.02 - t) / 0.1)
                    x0, y0 = SS.cell_xy(i, j)
                    d.text((x0 + 6, y0 + 10), "-∞", font=fm, fill=tk.amb(0.35) + (int(255 * k),))
        bs = clamp((t - self.shrink_t(*self.BALL)) / 0.2)
        if bs > 0:
            SS.draw_ball(d, t, lambda x, y: proj(x, y), bs)
        clip = Image.new("L", (kit.W, kit.H), 0)
        ImageDraw.Draw(clip).rectangle(SS.CLIP, fill=255)
        layer.putalpha(ImageChops.multiply(layer.getchannel("A"), clip))
        content = content.convert("RGBA")
        content.alpha_composite(layer)
        return Frame(content.convert("RGB"), self.pick(t, octx, nctx))


# ---------------------------------------------------------------- cut 23: the camera travels back

class C23(Cut):
    """dizzy -> travel. The camera pans backwards inside the pane only: the spinning bowl leaves to the right and
    the year strip, already at 2026 AD, comes in from the left, landing on beat 110.5 ("Oh, we can travel"). The
    pane title decodes from the left with it. The eye bar lifts off her on "Oh"."""
    pre, post = 0.25, 0.3
    IN = (406, 68, 1163, 603)
    TITLE = (404, 44, 1164, 68)

    def render(self, t, n):
        T = self.T
        oc, octx = self.old(t, n)
        nc, nctx = self.new(t, n)
        e = ease_io((t - (T - BEAT / 2)) / BEAT)
        out = reveal(oc, nc, t, sweep((404, 0), (1, 0), T - 0.2, 1900.0), region=self.TITLE, cell=(8, 12), seed=23)
        x0, y0, x1, y1 = self.IN
        w = x1 - x0
        out.paste(kit.stage.background(t).crop(self.IN), (x0, y0))
        off = round(w * e)
        if off < w:
            out.paste(oc.crop((x0, y0, x1 - off, y1)), (x0 + off, y0))
        if off > 0:
            out.paste(nc.crop((x1 - off, y0, x1, y1)), (x0, y0))
        return Frame(out, self.pick(t, octx, nctx))


CUTS = {21: C21, 22: C22, 23: C23}
