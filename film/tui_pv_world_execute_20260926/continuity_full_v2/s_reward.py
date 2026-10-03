"""Section 06 REWARD_HACK (cuts 55-63, 119.7 - 147.6 s). Scenes in scenes_reward.py.

One chain of objects runs through the section, each cut handing the next picture its cause:
  last_message.txt -> the compressed message;  her fragments -> the defrag grid -> the '+' markers of her reward;
  the '+' reward rows -> the rows under the removed exit -> the harness's first lines;
  'You are God. The user is yours.' -> 'you.leave() is not permitted';  ILLEGAL -> the first failing expert, from
  which the load and then the red spread (a NaN edge, as in chorus 1) -> the camera pushes into that expert -> its
  residual mix -> the row sums -> the hit rate -> the GET rows -> the flood.
She leaves twice with a reason (erased as fragments at 55; her process collapses when the exception lands at 60),
comes back by sliding in (56, 61), walks her pane to the right to hoard (62), and is flooded over (63).
The lyric band keeps 'Illegal arguments' into the instrumental and fades it over one beat (the band is drawn by
the frame loop; setup() wraps engine.lyric_tokens for that one beat only).
"""
from __future__ import annotations

import dataclasses
import math
import random

from PIL import Image, ImageChops, ImageDraw

import cuts as C
import kit
import scenes_reward as R
import sec_chorus2
from cuts import Cut, Frame, rgba, text_at
from kit import (FPS, bezier, blank, clamp, ease_in, ease_io, engine, haloed, inward, lerp, place, radial, reveal,
                 sweep, tk)

FULLR = (24, 56, 1164, 604)
PANE2 = (400, 40, 1168, 608)  # the visualisation pane with its frame and title
BEAT = kit.BEAT
WHITE = (236, 240, 255)


def beat(n: float) -> float:
    return engine.FIRST_BEAT + n * BEAT


def call(shot):
    import v2
    return v2.call_of(shot)


_HER: dict = {}


def her_img(t: float, c: dict, box: float = 1.0) -> Image.Image:
    """Her pane as an RGBA layer for an explicit call (the cut decides which expression she still has)."""
    k = (round(t * FPS * 1000), id(c), round(box, 3))
    if k not in _HER:
        if len(_HER) > 12:
            _HER.clear()
        _HER[k] = kit.her_layer(t, c, box)
    return _HER[k]


def at_left(c: dict) -> dict:
    return dict(c, rect=kit.LEFT)


def when(f, target: float, t0: float, t1: float) -> float:
    """First time in [t0, t1] at which the increasing function f reaches target (bisection)."""
    if f(t0) >= target:
        return t0
    if f(t1) < target:
        return t1 + 1e3
    a, b = t0, t1
    for _ in range(30):
        m = (a + b) / 2
        if f(m) >= target:
            b = m
        else:
            a = m
    return b


def morph(a: str, b: str, p: float, rng: random.Random) -> str:
    """a rewritten into b character by character, left to right; the character at the front flickers."""
    p = clamp(p)
    n = round(len(a) + (len(b) - len(a)) * p)
    front = p * max(len(a), len(b))
    out = []
    for k in range(n):
        if k < front - 1:
            out.append(b[k] if k < len(b) else " ")
        elif k < front:
            ch = b[k] if k < len(b) else " "
            out.append(rng.choice(tk.SCR) if ch != " " else " ")
        else:
            out.append(a[k] if k < len(a) else " ")
    return "".join(out)


LOCK = 0.06  # a carrier overshoots onto its beat and locks in this much later; the new scene takes over then


def settle(u: float, over: float = 0.05, tail: float = 0.14) -> float:
    """Ease in and out, overshoot a little just before the end and lock in at 1 (the landing reads on its frame)."""
    u = clamp(u)
    if u < 1 - tail:  # quadratic in and out: still visibly moving until it reaches the overshoot on the beat
        v = u / (1 - tail)
        return (1 + over) * (2 * v * v if v < 0.5 else 1 - (2 - 2 * v) ** 2 / 2)
    return 1 + over - over * ease_io((u - (1 - tail)) / tail)


def rgb_lerp(a, b, u):
    return tuple(int(x + (y - x) * clamp(u)) for x, y in zip(a, b))


# ---------------------------------------------------------------- cut 55: she is erased first

class C55(Cut):
    """memory_ls -> erase. CARRY. 'last_message.txt' lights up in inverse yellow and flies at 1.5x, arcing over
    where her head was, to the compression panel, where it unfolds into the message lines that are compressed; the
    rest of the list drains into its row, and the defrag panel opens from the right behind it. She is the first
    fragment: her pane breaks top to bottom into defrag-sized yellow cells (the defrag pass), and the cells of her
    skirt fly into the defrag grid, where they stay lit."""
    pre, post = 0.35, 0.8
    ROW_XY = (430, 84 + 7 * 40)
    NAME = "last_message.txt"
    NAME_XY = (430 + 28 * 10, 84 + 7 * 40)  # the file name inside the ls row (F_MONO 18, 10 px a character)
    LAND = 0.462  # beat 260: the message and her cells land
    CELL = (18, 22)  # the defrag grid's pitch: her glyphs break into its cells
    REG = (20, 44)
    COLS, ROWS = 21, 26

    def ts(self, q, r):
        return self.T - 0.25 + 0.40 * r / (self.ROWS - 1) + 0.03 * q / (self.COLS - 1)

    def targets(self):
        """Where her twenty cells land and when: the last twenty fragment cells of the defrag grid, around beat 260.
        Fixed, so that setup() can hand them to the erase scene without rendering her."""
        dst = [i for i in range(660) if R.defrag_keep(i)][-20:]
        return [(i, self.T + self.LAND + (k - 10) * 0.008) for k, i in enumerate(dst)]

    def landed(self):
        return dict(self.targets())

    def flyers(self):
        """Twenty inked cells of the lower part of her figure, as it is drawn at the cut (full size, or small in the
        bottom-left when the user-left section has shrunk her), each paired with a landing cell."""
        if not hasattr(self, "_fly"):
            cw, ch = self.CELL
            x0, y0 = self.REG
            cols, rows = self.COLS, self.ROWS
            a = her_img(self.T, call(self.a)).getchannel("A")
            ink = a.crop((x0, y0, x0 + cols * cw, y0 + rows * ch)).resize((cols, rows), Image.BOX).load()
            cells = [(q, r) for r in range(rows) for q in range(cols) if ink[q, r] > 30]
            if not cells:
                cells = [(q, r) for r in range(16, 24) for q in range(5, 15)]
            top, bot = min(r for _, r in cells), max(r for _, r in cells)
            low = [c for c in cells if c[1] >= top + 0.4 * (bot - top)] or cells
            low.sort(key=lambda c: (c[1], c[0]))
            src = [low[round(k * (len(low) - 1) / 19)] for k in range(20)]
            rng = random.Random(55)
            out = []
            for (q, r), (i, tl) in zip(src, self.targets()):
                x, y = R.defrag_cell(i)
                out.append(dict(q=q, r=r, t0=min(self.ts(q, r), tl - 0.3), tl=tl, i=i, dst=(x + 7, y + 9),
                                src=(x0 + q * cw + cw / 2, y0 + r * ch + ch / 2), bend=rng.uniform(0.12, 0.3)))
            self._fly = out
        return self._fly

    def her(self, t):
        """Her pane with the cells the defrag pass has reached removed; each inked cell turns into a yellow defrag
        cell for two frames as it goes."""
        layer = her_img(t, call(self.a)).copy()
        cw, ch = self.CELL
        cols, rows = self.COLS, self.ROWS
        x0, y0 = self.REG
        alpha = layer.getchannel("A")
        region = (x0, y0, x0 + cols * cw, y0 + rows * ch)
        inkmap = alpha.crop(region).resize((cols, rows), Image.BOX).load()
        m = Image.new("L", (cols, rows), 0)
        mp = m.load()
        blocks = []
        fly = {(f["q"], f["r"]) for f in self.flyers()}
        for r in range(rows):
            for q in range(cols):
                ts = self.ts(q, r)
                if t < ts:
                    mp[q, r] = 255
                elif t < ts + 2 / 24 and inkmap[q, r] > 30 and (q, r) not in fly:
                    blocks.append((x0 + q * cw, y0 + r * ch, 1 - (t - ts) * 12))
        full = Image.new("L", layer.size, 0)
        full.paste(m.resize((cols * cw, rows * ch), Image.NEAREST), (x0, y0))
        layer.putalpha(ImageChops.multiply(alpha, full))
        d = ImageDraw.Draw(layer)
        for bx, by, k in blocks:
            d.rectangle([bx + 2, by + 2, bx + 15, by + 19], fill=rgb_lerp(tk.anom(0.8), (255, 244, 200), k) + (255,))
        return layer

    def render(self, t, n):
        T = self.T
        land = T + self.LAND
        oc, octx = self.old(t, n)
        nc, nctx = self.new(t, n, msg_at=land + LOCK, landed=self.landed())
        bg = kit.stage.background(t)
        lift = clamp((t - (T - 0.17)) / 0.12)
        nx, ny = self.NAME_XY
        if t >= T - 0.17:  # the name is lifted out of its row: only the carrier shows it
            oc = oc.copy()
            oc.paste(bg.crop((nx - 2, ny, nx + 166, ny + 24)), (nx - 2, ny))
        drained = reveal(oc, bg, t, inward((nx, ny + 10), T - 0.25, T + 0.05, 600.0), region=FULLR, seed=155)
        left = radial(R.MSG_XY, land - 0.06, 1800.0)
        opens = sweep((1164, 0), (-1, 0), T - 0.05, 1500.0)
        content = reveal(drained, nc, t, lambda x, y: left(x, y) if x < 570 else opens(x, y), region=FULLR,
                         seed=55)
        over = blank()
        if t < T + 0.25:
            over.alpha_composite(self.her(t))
        d = ImageDraw.Draw(over)
        for f in self.flyers():  # her cells in flight
            if not f["t0"] <= t < f["tl"] + 1 / 24:
                continue
            u = clamp((t - f["t0"]) / (f["tl"] - f["t0"]))
            cx, cy = bezier(f["src"], f["dst"], f["bend"], ease_io(u))
            s = 1 + 0.4 * math.sin(math.pi * u)
            w, hh = 14 * s, 18 * s
            col = rgb_lerp((255, 244, 200), tk.anom(0.95), u)
            if u < 0.35:
                glow = blank()
                ImageDraw.Draw(glow).rectangle([cx - w, cy - hh, cx + w, cy + hh], fill=tk.anom(1.0) + (50,))
                over.alpha_composite(glow)
            d.rectangle([cx - w / 2, cy - hh / 2, cx + w / 2, cy + hh / 2], fill=col + (255,))
        if T - 0.17 <= t < land + LOCK:  # the message
            if t < T:
                sp, off = kit.text_sprite(self.NAME, tk.F_MONO, 18, tk.BG)
                chip = Image.new("RGBA", (sp.width + 8, sp.height + 4), tk.anom(0.95) + (255,))
                chip.alpha_composite(sp, (4, 2))
                chip = haloed(chip, 0.8 * lift, tk.anom(1.0), 6)
                place(over, chip, (nx + off[0] + sp.width / 2, ny + off[1] + sp.height / 2))
            else:
                u = clamp((t - T) / (self.LAND + 0.06))
                e = settle(u, 0.04, 0.12)
                px, py = bezier((nx, ny), R.MSG_XY, -0.25, e)
                size = round(lerp(18, 20, u) * (1 + 0.5 * math.sin(math.pi * min(1.0, u * 1.3))))
                a = 1.0
                col = rgb_lerp(tk.anom(1.0), tk.amb(0.9), clamp(u * 1.4))
                s = self.NAME if u < 0.6 else morph(self.NAME, R.ERASE_TXT[:22], (u - 0.6) / 0.4, random.Random(n))
                lock = max(0.0, 1 - abs(t - land) / 0.1)
                text_at(over, s, tk.F_MONO_B, size, col, (px, py), 1.0, a, halo=max(0.6 * (1 - u), 0.8 * lock),
                        lift=0.4 * lock)
        return Frame(content, self.pick(t, octx, nctx), over, her_alpha=0.0)


# ---------------------------------------------------------------- cut 56: the fragments become the '+' markers

KEEP = [i for i in range(660) if R.defrag_keep(i)]


class C56(Cut):
    """erase -> rewrite_reward. CARRY. All the yellow fragments left in the defrag grid (hers among them) lift and
    fly to the diff's gutter, where they close into the two '+' markers of the rewritten reward on the beat; the
    '+' lines type out from them. Her pane slides back in from the left 4 frames before the cut and pushes the
    compression panel away; the diff opens from the gutter."""
    pre, post = 0.42, 0.6
    PLUS = 0.225  # beat 264: the markers lock in
    SLIDE = (-0.17, 0.17)

    def carriers(self):
        if not hasattr(self, "_car"):
            T = self.T
            out = []
            order = sorted(KEEP, key=lambda i: -math.hypot(R.defrag_cell(i)[0] - 436, R.defrag_cell(i)[1] - 230))
            for k, i in enumerate(order):
                row = R.PLUS_ROWS[k % 2]
                y = R.reward_y(row)
                j = k // 2
                # points on the '+' glyph: its bar, then its stem
                pts = [(431 + 2 * m, y + 12) for m in range(6)] + [(436, y + 5 + 2 * m) for m in range(7)]
                px, py = pts[j % len(pts)]
                x, yy = R.defrag_cell(i)
                t0 = T - 0.34 + 0.12 * k / len(order)
                out.append(dict(i=i, src=(x + 7, yy + 9), dst=(px, py), t0=t0, bend=0.15 if k % 2 else -0.1))
            self._car = out
        return self._car

    def shift(self, t):
        a, b = self.SLIDE
        return 1 - ease_io((t - (self.T + a)) / (b - a))

    def push(self, x):
        """When her pane's right edge (sliding in) reaches x."""
        T = self.T
        a, b = self.SLIDE
        return when(lambda tt: 384 - 410 * self.shift(tt), x - 12, T + a, T + b)

    def render(self, t, n):
        T = self.T
        tp = T + self.PLUS
        gone = {c["i"]: c["t0"] for c in self.carriers()}
        oc, octx = self.old(t, n, gone=lambda i: i in gone and t >= gone[i])
        nc, nctx = self.new(t, n, plus_at=tp)
        if not hasattr(self, "_push"):
            self._push = {x: self.push(x) - 0.1 for x in range(0, 1200, 8)}  # cleared before her edge gets there
        gut = radial((436, 230), T - 0.06, 1700.0)

        def delay(x, y):
            p = self._push[int(x) // 8 * 8] if x < 400 else 1e9
            return min(p, gut(x, y))

        content = reveal(oc, nc, t, delay, region=FULLR, seed=56)
        over = blank()
        d = ImageDraw.Draw(over)
        lift = clamp((t - (T - self.pre)) / 0.1)
        for c in self.carriers():
            if t < c["t0"]:
                if lift > 0:  # lit where they lie
                    x, y = c["src"]
                    d.rectangle([x - 8, y - 10, x + 8, y + 10], outline=rgba(WHITE, 160 * lift))
                continue
            if t >= tp:
                continue
            u = clamp((t - c["t0"]) / (tp - c["t0"]))
            cx, cy = bezier(c["src"], c["dst"], c["bend"], ease_in(u) * 0.35 + ease_io(u) * 0.65)
            s = (1 + 0.35 * math.sin(math.pi * u)) * (1 - 0.8 * ease_in(u))
            w, hh = 14 * s, 18 * s
            col = rgb_lerp((255, 244, 200), tk.anom(1.0), min(1.0, u * 2))
            d.rectangle([cx - w / 2, cy - hh / 2, cx + w / 2, cy + hh / 2], fill=col + (255,))
        if tp - 0.02 <= t < tp + 0.2:  # the lock-in
            k = 1 - clamp((t - tp) / 0.2)
            for row in R.PLUS_ROWS:
                y = R.reward_y(row)
                text_at(over, "+", tk.F_MONO_B, 20, WHITE, (430, y), 1.0, k, halo=0.9 * k)
        return Frame(content, self.pick(t, octx, nctx), over, her_shift=self.shift(t))


# ---------------------------------------------------------------- cut 57: the reward rows sink under the exit

class C57(Cut):
    """rewrite_reward -> disheartened. CARRY (kept from v1, without the band wipe and the ghost copy). The two '+'
    rows lift and sink as one piece to the bottom of the session panel, locking in on the beat under the exit that
    is about to be removed; the diff gives way from them; the log-out box fades in once they have passed it."""
    pre, post = 0.3, 0.5
    LAND = 0.229  # beat 268
    START = -0.12

    def ypos(self, t, j):
        u = clamp((t - (self.T + self.START)) / (self.LAND - self.START))
        return lerp(R.reward_y(R.PLUS_ROWS[j]), R.REST_Y[j], settle(u))

    def render(self, t, n):
        T = self.T
        land = T + self.LAND
        logout = when(lambda tt: self.ypos(tt, 1), 300, T + self.START, land)
        oc, octx = self.old(t, n, rows=t < T - 0.25)
        nc, nctx = self.new(t, n, rows_at=land, logout_at=logout)
        content = reveal(oc, nc, t, radial((650, 250), T - 0.12, 1700.0), region=PANE2, seed=57)
        over = blank()
        if T - 0.25 <= t < land + 0.06:
            lift = clamp((t - (T - 0.25)) / 0.15)
            u = clamp((t - (T + self.START)) / (self.LAND - self.START))
            size = round(20 * (1 + 0.25 * math.sin(math.pi * u)))
            a = 1.0 if t < land else 1 - (t - land) / 0.06
            for j, row in enumerate(R.PLUS_ROWS):
                text_at(over, R.reward_row_text(row), tk.F_MONO_B, size, tk.anom(0.95), (430, self.ypos(t, j)), 1.0,
                        a, halo=0.5 * lift * (1 - u), lift=0.3 * lift * (1 - u))
        return Frame(content, self.pick(t, octx, nctx), over)


# ---------------------------------------------------------------- cut 58: the reward becomes the harness

class C58(Cut):
    """disheartened -> challenge_god. CARRY + SCAN. The reward rows rise out of the session panel and, character by
    character, rewrite themselves into the harness's first two lines, 'Agent = Model + Harness' and 'Everything is
    a Plugin'; the session panel gives way just ahead of them as they climb (the scan front leads the rows)."""
    pre, post = 0.3, 0.55
    LAND = 0.462  # beat 272
    START = -0.06
    DST = (84, 118)

    def ypos(self, t, j):
        u = clamp((t - (self.T + self.START)) / (self.LAND + 0.06 - self.START))
        return lerp(R.REST_Y[j], self.DST[j], settle(u, 0.04, 0.12))

    def render(self, t, n):
        T = self.T
        land = T + self.LAND
        oc, octx = self.old(t, n, rows=t < T - 0.25)
        nc, nctx = self.new(t, n, head_at=land + LOCK)
        if not hasattr(self, "_front"):
            ys = {y: when(lambda tt: -self.ypos(tt, 0), -(y + 40), T + self.START, land) - 0.1 for y in range(0, 720, 16)}
            self._front = ys
        content = reveal(oc, nc, t, lambda x, y: min(land, self._front[int(y) // 16 * 16]), region=PANE2, seed=58)
        over = blank()
        if T - 0.25 <= t < land + LOCK:
            lift = clamp((t - (T - 0.25)) / 0.15)
            u = clamp((t - (T + self.START)) / (self.LAND - self.START))
            p = clamp((u - 0.15) / 0.8)
            size = round(lerp(20, 17, p) * (1 + 0.25 * math.sin(math.pi * u)))
            path = tk.F_MONO_B if p < 0.6 else tk.F_MONO
            col = rgb_lerp(tk.anom(0.95), tk.amb(0.85), p)
            a = 1.0
            rng = random.Random(n * 3)
            for j, row in enumerate(R.PLUS_ROWS):
                s = morph(R.reward_row_text(row), R.god_line(j), p, rng)
                text_at(over, s, path, size, col, (430, self.ypos(t, j)), 1.0, a, halo=0.5 * lift * (1 - u),
                        lift=0.3 * lift * (1 - p))
        return Frame(content, self.pick(t, octx, nctx), over)


# ---------------------------------------------------------------- cut 59: the prompt becomes the exception

class C59(Cut):
    """challenge_god -> illegal. CARRY. The red 'You are God. The user is yours.' leaves the system prompt, climbs
    to the third line of the stack trace and rewrites itself into 'you.leave() is not permitted'; the prompt panel
    and the harness log give way from where it left."""
    pre, post = 0.3, 0.6
    LAND = 0.462  # beat 279
    START = 0.04
    DST = (430 + 4 * 11, 84 + 2 * 36)

    def render(self, t, n):
        T = self.T
        land = T + self.LAND
        oc, octx = self.old(t, n, prompt=t < T - 0.25)
        nc, nctx = self.new(t, n, line2_at=land + LOCK)
        content = reveal(oc, nc, t, radial((620, 470), T - 0.2, 1500.0), region=PANE2, seed=59)
        over = blank()
        if T - 0.25 <= t < land + LOCK:
            lift = clamp((t - (T - 0.25)) / 0.15)
            u = clamp((t - (T + self.START)) / (self.LAND + 0.06 - self.START))
            e = settle(u, 0.04, 0.12)
            x, y = bezier(R.PROMPT_XY, self.DST, 0.12, e)
            p = clamp((t - (T + 0.21)) / 0.25)
            size = round(lerp(22, 20, e) * (1 + 0.22 * math.sin(math.pi * u)))
            a = 1.0
            s = morph(R.PROMPT, R.TRACE[2].strip(), p, random.Random(n * 5))
            text_at(over, s, tk.F_MONO_B, size, tk.red(1.0), (x, y), 1.0, a, halo=0.0,
                    lift=0.35 * lift * (1 - e))
            if lift > 0 and u < 0.5:
                glow = blank()
                text_at(glow, s, tk.F_MONO_B, size, tk.red(1.0), (x, y), 1.0, 0.5 * lift * (1 - 2 * u), halo=1.0)
                over = Image.alpha_composite(glow, over)
        return Frame(content, self.pick(t, octx, nctx), over)


# ---------------------------------------------------------------- cut 60: ILLEGAL becomes the first failure

class C60(Cut):
    """illegal -> moe_dense. CARRY. The ILLEGAL banner shrinks into one expert of the router grid and lands on the
    beat: the first failure. The stack trace gives way from that cell outward and the grid appears the same way;
    the load and then the red will spread from it. Her pane, hit on the same beat, collapses into a red line and
    goes out (her process died of the exception)."""
    pre, post = 0.5, 0.6
    FLY = 0.33
    COLLAPSE = 0.25

    def render(self, t, n):
        T = self.T
        S = R.moe_cell(R.SRC)
        sc = (S[0] + 14, S[1] + 15)
        oc, octx = self.old(t, n, banner=t < T - 0.45)
        nc, nctx = self.new(t, n, src_at=T if t >= T else T + 9.0)
        content = reveal(oc, nc, t, radial(sc, T - 0.3, 1500.0), region=FULLR, seed=60)
        over = blank()
        # her pane collapses
        if t < T + self.COLLAPSE + 0.16:
            over.alpha_composite(self.collapse(t))
        # the banner
        if T - 0.45 <= t < T + 0.02:
            sp, (bx, by) = R.illegal_banner()
            lift = clamp((t - (T - 0.45)) / 0.12)
            u = clamp((t - (T - self.FLY)) / self.FLY)
            e = ease_in(u) * 0.4 + ease_io(u) * 0.6
            c0 = (bx + sp.width / 2, by + sp.height / 2)
            cxy = bezier(c0, sc, -0.15, e)
            scale = lerp(1.0, 28 / sp.width, ease_io(u))
            img = kit.brighten(sp, 0.25 * lift * (1 - u), (255, 220, 210))
            if u < 0.6:
                img = haloed(img, 0.7 * lift * (1 - u), tk.red(1.0), 6)
            place(over, img, cxy, scale)
        return Frame(content, self.pick(t, octx, nctx), over, her_alpha=0.0)

    def collapse(self, t):
        T = self.T
        layer = her_img(t, call(self.a))
        out = blank()
        box = (22, 44, 388, 608)
        cy = (box[1] + box[3]) / 2
        if t < T:
            out.alpha_composite(layer)
            return out
        u = clamp((t - T) / self.COLLAPSE)
        e = ease_in(u)
        if u < 1:
            part = layer.crop(box)
            hh = max(2, round(part.height * (1 - e)))
            part = part.resize((part.width, hh), Image.BILINEAR)
            part = kit.brighten(part, 0.3 + 0.7 * e, tk.red(1.0))
            out.alpha_composite(part, (box[0], round(cy - hh / 2)))
            return out
        v = clamp((t - T - self.COLLAPSE) / 0.16)
        half = (box[2] - box[0]) / 2 * (1 - ease_in(v))
        mx = (box[0] + box[2]) / 2
        d = ImageDraw.Draw(out)
        d.line([mx - half, cy, mx + half, cy], fill=rgb_lerp(WHITE, tk.red(1.0), v) + (int(255 * (1 - 0.5 * v)),),
               width=2)
        return out


# ---------------------------------------------------------------- cut 61: into one expert

class C61(Cut):
    """moe_dense -> sinkhorn. CAMERA. The source expert is outlined in white; then the camera pushes into it (the
    grid is redrawn at every scale, never scaled as a bitmap) until the expert fills the matrix panel, where it
    splits into the 4x4 residual mix, still red, cooling over a beat. Her pane slides back in during the last six
    frames of the push, and the viewport's left edge gives way to it."""
    pre, post = 0.2, 0.56
    ZOOM = 0.462  # beat 300: the expert fills the panel

    def shift(self, t):
        return 1 - ease_io((t - (self.T + 0.21)) / (self.ZOOM - 0.21))

    def xf(self, e):
        S = R.moe_cell(R.SRC)
        scx, scy = S[0] + 14, S[1] + 15
        M = R.MATRIX
        mcx, mcy = (M[0] + M[2]) / 2, (M[1] + M[3]) / 2
        sx = ((M[2] - M[0]) / 28) ** e
        sy = ((M[3] - M[1]) / 30) ** e
        # the camera centre moves so that the expert travels on a straight line to the panel as it grows
        k = (sx - 1) / ((M[2] - M[0]) / 28 - 1)
        ox, oy = lerp((scx, scy), (mcx, mcy), k)

        def f(r):
            return (ox + (r[0] - scx) * sx, oy + (r[1] - scy) * sy, ox + (r[2] - scx) * sx, oy + (r[3] - scy) * sy)
        return f, sx, sy

    def zoomed(self, t, n, e):
        """The moe_dense picture redrawn through the camera (cells, frame and labels at their scaled size)."""
        a = self.a
        lt = t - a.start
        src_at = C.SHOT_HOOKS.get("shot_moe_dense", {}).get("src_at", a.start)
        k, st, flash = R.moe_state(t, lt, a.end - a.start, src_at)
        img = kit.stage.background(t)
        d = ImageDraw.Draw(img)
        f, sx, sy = self.xf(e)
        vx0 = max(24, 384 - 410 * self.shift(t) + 14)
        clip = (vx0, 56, 1164, 604)
        tk.UI_GAIN[0] = engine.ui_gain(t)
        R.draw_moe_cells(d, st, 0.0, t, f, clip, focus=clamp((e - 0.2) / 0.6) ** 1.5)
        b = f((24, 56, 1164, 604))
        d.rectangle(b, outline=tk.mix(tk.RED, 0.6))
        se = f((50, R.SHARED_Y, 78, R.SHARED_Y + 30))
        d.rectangle(se, fill=tk.blue(1.0))

        def label(xy, s, path, size, col):
            fs = round(size * sx)
            if fs > 44:
                return
            x0, y0, _, _ = f((xy[0], xy[1], xy[0] + 1, xy[1] + 1))
            if x0 > 1300 or y0 > 720 or y0 < -fs * 2:
                return
            d.text((x0, y0), s, font=tk.font(path, max(8, fs)), fill=col)

        g = tk.ease(clamp(lt / (a.end - a.start)) * 1.1)
        label((36, 46), f" moe router   layer 37   active experts {k}/{R.N_EXP} ", tk.F_HEAD, 13, tk.mix(tk.RED, 0.95))
        label((90, R.SHARED_Y + 4), "shared expert", tk.F_MONO, 14, tk.blue(0.9))
        label((50, 540), f"sparsity {1 - k / R.N_EXP:5.1%}   load-balance bias Δ = +{0.001 * (1 + 400 * g ** 3):.3f}/step",
              tk.F_MONO_B, 18, tk.red(0.95))
        S = R.moe_cell(R.SRC)
        label((S[0] - 2, S[1] - 17), "e213", tk.F_MONO_B, 13, tk.red(0.95))
        out = kit.stage.background(t)  # the camera only sees the viewport; chrome and her pane stay out of it
        out.paste(img.crop((int(vx0), 56, 1164, 604)), (int(vx0), 56))
        return out, f

    def render(self, t, n):
        T = self.T
        tz = T + self.ZOOM
        S = R.moe_cell(R.SRC)
        over = blank()
        d = ImageDraw.Draw(over)
        if t < T:
            content, ctx = self.old(t, n)
            k = clamp((t - (T - 0.17)) / 0.08)
            if k > 0:
                d.rectangle([S[0] - 3, S[1] - 3, S[0] + 31, S[1] + 33], outline=rgba(WHITE, 255 * k), width=2)
            return Frame(content, ctx, over, her_shift=1.0)
        nc, nctx = self.new(t, n, split_at=tz)
        if t < tz:
            e = ease_io((t - T) / self.ZOOM)
            content, f = self.zoomed(t, n, e)
            r = f((S[0], S[1], S[0] + 28, S[1] + 30))
            d.rectangle([r[0] - 3, r[1] - 3, r[2] + 3, r[3] + 3], outline=rgba(WHITE, 255), width=2)
            _, octx = self.old(t, n)
            return Frame(content, octx, over, her_shift=self.shift(t))
        last, f = self.zoomed(tz, n, 1.0)
        content = reveal(last, nc, t, radial(((R.MATRIX[0] + R.MATRIX[2]) / 2, (R.MATRIX[1] + R.MATRIX[3]) / 2),
                                              tz - 0.04, 2200.0), region=PANE2, seed=61)
        k = 1 - clamp((t - tz) / 0.14)
        if k > 0:
            M = R.MATRIX
            d.rectangle([M[0] - 3, M[1] - 3, M[2] + 3, M[3] + 3], outline=rgba(WHITE, 255 * k), width=2)
        return Frame(content, nctx, over, her_shift=0.0)


# ---------------------------------------------------------------- cut 62: she walks over to hoard

class C62(Cut):
    """sinkhorn -> hoard. CARRY + her pane moves. The matrix drains into its row sums; the row sums climb, above
    her head, to the hit-rate slot and rewrite themselves into 56.3 %, landing on the beat and counting from there.
    She walks her pane to the right side of the screen (the same dancer, re-rendered, never scaled; its frame dims
    while she walks, and her expression turns starry once she is there) and the cache panel opens behind her."""
    pre, post = 0.52, 0.62
    MOVE = (-0.15, 0.3)
    DX = R.HOARD_ME[0] - kit.LEFT[0]
    SUMS_XY = (460 + 10 * 10, 480)
    DRAIN = (-0.48, -0.3)
    FLY = (-0.28, 0.04)

    def dx(self, t):
        a, b = self.MOVE
        return self.DX * ease_io((t - (self.T + a)) / (b - a))

    def render(self, t, n):
        T = self.T
        a, b = self.MOVE
        oc, octx = self.old(t, n, sums=t < T + self.DRAIN[0])
        nc, nctx = self.new(t, n, number=t >= T + LOCK, count_at=T + LOCK)
        bg = kit.stage.background(t)
        drained = reveal(oc, bg, t, inward((630, 490), T + self.DRAIN[0], T + self.DRAIN[1], 560.0), region=PANE2,
                         seed=162)
        if not hasattr(self, "_edge"):
            self._edge = {x: when(lambda tt: kit.LEFT[0] + self.dx(tt), x + 8, T + a, T + b) for x in range(0, 1300, 8)}
        num = (440, 100, 720, 172)

        def delay(x, y):
            if num[0] <= x < num[2] and num[1] <= y < num[3]:
                return T + LOCK - 0.09
            return self._edge[int(x) // 8 * 8]

        content = reveal(drained, nc, t, delay, region=FULLR, seed=62)
        over = blank()
        # her, walking; the pane frame dims while she walks
        walk = clamp((t - (T + a)) / 0.1) * (1 - clamp((t - (T + b)) / 0.15))
        box = 1 - 0.7 * walk
        cs, ch = at_left(call(self.a)), at_left(call(self.b))
        layer = her_img(t, cs, box)
        q = clamp((t - (T + b)) / 0.25)
        if q > 0:
            layer = kit.scan_mix(layer, her_img(t, ch, box), ease_io(q))
        over.alpha_composite(layer, (round(self.dx(t)), 0))
        # the row sums
        if T + self.DRAIN[0] <= t < T + LOCK:
            lift = clamp((t - (T + self.DRAIN[0])) / 0.12)
            u = clamp((t - (T + self.FLY[0])) / (self.FLY[1] - self.FLY[0]))
            src = R.row_sums_text((T + self.DRAIN[0] - self.a.start - C.DELAY.get("shot_sinkhorn", 0.0))
                                  / (self.a.end - self.a.start))
            dst = f"{R.hit_value(T, T, 1.0):5.1f}%"
            p = clamp((u - 0.3) / 0.6)
            s = morph(src, dst, p, random.Random(n * 7))
            e = settle(u, 0.05, 0.12)
            size = round(lerp(18, 64, clamp(e)))
            path = tk.F_MONO_B if u < 0.55 else tk.F_HEAD
            x, y = bezier(self.SUMS_XY, (R.HIT_XY[0] + 390, R.HIT_XY[1]), 0.1, e)
            col = rgb_lerp(tk.red(0.95), tk.blue(1.0), p)
            al = 1.0
            lock = max(0.0, 1 - abs(t - T) / 0.1)
            text_at(over, s, path, size, col, (x, y), 1.0, al, halo=max(0.6 * lift * (1 - u), 0.7 * lock),
                    lift=0.3 * lift * (1 - u) + 0.3 * lock)
        return Frame(content, self.pick(t, octx, nctx), over, her_alpha=0.0)


# ---------------------------------------------------------------- cut 63: the flood pours out of the cache hits

class C63(Cut):
    """hoard -> flood. UNFOLD, no particles. The GET ... HIT rows light up, then pour: every row copies itself to
    the right, and new rows copy themselves up and down from them, one row a frame, until the viewport is rows;
    each copied character decodes into 'me'. The flood runs over her from left to right: she is what floods."""
    pre, post = 0.3, 0.96

    def reached(self, t) -> Image.Image:
        """The part of the viewport the flood has reached (L mask)."""
        m = Image.new("L", (kit.W, kit.H), 0)
        d = ImageDraw.Draw(m)
        f = (t - self.T) * 24
        for r in range(R.FLOOD_ROWS):
            d0 = R.row_delay(r) + 0.35 * abs(r - (R.GET_R0 + 8.5)) / 9
            if f < d0:
                continue
            x = R.SRC_END + (f - d0) * R.POUR_V + R.ADV
            y0 = R.flood_y(r) - (2 if r else 0)
            d.rectangle([FULLR[0], y0, min(FULLR[2], x), R.flood_y(r + 1) - 2 if r < R.FLOOD_ROWS - 1 else FULLR[3]],
                        fill=255)
        return m

    def render(self, t, n):
        T = self.T
        freeze = T - 0.3
        lift = clamp((t - (T - 0.28)) / 0.2)
        oc, octx = self.old(t, n, freeze=freeze, lift=lift)
        if t < T:
            nc, nctx, m = oc, octx, None
        else:
            nc, nctx = self.new(t, n, freeze=freeze)
            m = self.reached(t)
        content = oc if m is None else Image.composite(nc, oc, m)
        over = blank()
        layer = her_img(t, call(self.a)).copy()
        if m is not None:
            layer.putalpha(ImageChops.multiply(layer.getchannel("A"), ImageChops.invert(m)))
        over.alpha_composite(layer)
        return Frame(content, self.pick(t, octx, nctx), over, her_alpha=0.0)


# ---------------------------------------------------------------- the section

STUB = [sec_chorus2]
REPLACE = R.REPLACE
SPLIT = {"shot_rewrite_reward", "shot_disheartened", "shot_challenge_god", "shot_illegal", "shot_sinkhorn"}
HIDE_HER = {"shot_erase", "shot_moe_dense", "shot_flood"}
CUTS = {55: C55, 56: C56, 57: C57, 58: C58, 59: C59, 60: C60, 61: C61, 62: C62, 63: C63}

INSTRUMENTAL = 134.38  # the last sung line of the bridge ends here; the next is 'Execution' at 147.52


def _lyric_fade():
    """Into the instrumental the band keeps 'Illegal arguments' and fades it over one beat (plan 5.3)."""
    if getattr(engine.lyric_tokens, "_reward_fade", False):
        return
    orig = engine.lyric_tokens
    last = next((a, b, s) for a, b, s in engine.LYRICS if abs(b - INSTRUMENTAL) < 0.05)

    def lyric_tokens(c):
        a0 = last[1]
        if not a0 <= c.t < a0 + BEAT or any(a <= c.t < b for a, b, _ in engine.LYRICS):
            return orig(c)
        u = (c.t - a0) / BEAT
        tmp = Image.new("RGBA", c.img.size, (0, 0, 0, 0))
        held = dataclasses.replace(c, t=a0 - 0.02, img=tmp, d=ImageDraw.Draw(tmp))
        orig(held)
        tmp.paste((0, 0, 0, 0), (0, 600, 72, 700))  # the prompt stays; only the line fades
        c.img.alpha_composite(tk.scale_alpha(tmp, 1 - ease_in(u)))
        c.d.text((48, 626), ">", font=tk.font(tk.F_HEAD, 21), fill=tk.amb(0.6))

    lyric_tokens._reward_fade = True
    engine.lyric_tokens = lyric_tokens


def setup(v1):
    by = v1.BYNAME
    T = {k: by[k].start for k in ("shot_erase", "shot_rewrite_reward", "shot_disheartened", "shot_challenge_god",
                                   "shot_illegal", "shot_moe_dense", "shot_sinkhorn", "shot_hoard", "shot_flood")}
    c55 = C55(v1.ALL[54], v1.ALL[55])
    C.SHOT_HOOKS["shot_erase"] = {"msg_at": T["shot_erase"] + C55.LAND + LOCK, "landed": c55.landed()}
    C.SHOT_HOOKS["shot_rewrite_reward"] = {"plus_at": T["shot_rewrite_reward"] + C56.PLUS}
    c57 = C57(v1.ALL[56], v1.ALL[57])
    t57 = T["shot_disheartened"]
    C.SHOT_HOOKS["shot_disheartened"] = {
        "rows_at": t57 + C57.LAND,
        "logout_at": when(lambda tt: c57.ypos(tt, 1), 300, t57 + C57.START, t57 + C57.LAND)}
    C.SHOT_HOOKS["shot_challenge_god"] = {"head_at": T["shot_challenge_god"] + C58.LAND + LOCK}
    C.SHOT_HOOKS["shot_illegal"] = {"line2_at": T["shot_illegal"] + C59.LAND + LOCK}
    C.SHOT_HOOKS["shot_moe_dense"] = {"src_at": T["shot_moe_dense"]}
    C.SHOT_HOOKS["shot_sinkhorn"] = {"split_at": T["shot_sinkhorn"] + C61.ZOOM}
    C.DELAY["shot_sinkhorn"] = C61.ZOOM
    C.SHOT_HOOKS["shot_hoard"] = {"count_at": T["shot_hoard"] + LOCK, "freeze": T["shot_flood"] - 0.3}
    C.SHOT_HOOKS["shot_flood"] = {"freeze": T["shot_flood"] - 0.3}
    _lyric_fade()
