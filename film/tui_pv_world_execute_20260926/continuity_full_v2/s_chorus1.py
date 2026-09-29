"""Chorus 1 (shots 24 unite .. 33 strange): the author-approved renderer, with cuts 24, 26 and 31 restaged.

Every frame of shots 24-33 outside those three cut windows is `continuity_chorus_v1.render_frame`, unchanged (OWN).
Inside a window the cut composes over the approved content before chrome and post (`approved_pre`, an in-memory
copy of render_frame that stops before the chrome); the frame loop then draws the chrome once, last, as everywhere
else. Scene copies with hooks (scenes_chorus1) are used only inside the windows; with their hooks at the default
they draw the originals, so each window ends on the approved frame.

  24  travel -> unite       CARRY  the position-id bars merge in pairs and fly into the tokenizer rows as token
                                   chips (v1 HANDOFFS['shot_unite']); she re-renders top-down from the string dancer
                                   into the approved glyph portrait
  26  deeply -> if_i_can    UNFOLD her glyph rows stream out of her pane; the IF I CAN field is written behind them,
                                   from her pane's edge across the body; the pane frame fades
  31  happy -> execution    CAMERA the grad-cam close-up pulls back into her head in the pane (mirror of cut 30);
                                   the panel frame contracts into her pane frame; the agent loop fills the body
"""
from __future__ import annotations

import math
import random
from types import SimpleNamespace

from PIL import Image, ImageChops, ImageDraw, ImageFilter

import cuts as C
import kit
import scenes_chorus1 as SC
from kit import BEAT, FPS, blank, brighten, clamp, ease_io, engine, lerp, tk

A = kit.v1.approved  # continuity_chorus_v1/continuity.py (read-only import)
FIRST, LAST = 24, 33


def _approved(t, n):
    return A.render_frame(n)


OWN = {i: _approved for i in range(FIRST, LAST + 1)}


# ---------------------------------------------------------------- the approved frame, before chrome and post

def approved_pre(shot, t, n, fn=None, hooks=None, skip=()):
    """continuity_chorus_v1.render_frame for `shot` at time t, before chrome and post: (image RGB, ctx).
    fn: a hooked copy of the scene (scenes_chorus1) drawn instead of the original; hooks: its HOOK values.
    skip: 'scan' leaves out the approved band reveal of an ordinary workspace, 'handoff' the two full-screen
    handoffs (portrait -> #0000, sidebar head -> happy close-up)."""
    name = shot.fn.__name__
    orig = shot.fn
    if fn is not None:
        shot.fn = fn
    kit.HOOK.clear()
    kit.HOOK.update(hooks or {})
    try:
        body = A.raw(t, n, shot)
    finally:
        shot.fn = orig
        kit.HOOK.clear()
    c = body["ctx"]
    im = A.body_image(body, name)
    if c.black:
        return im, c
    ordered = list(A.SHOTS.values())
    at = ordered.index(shot) if shot in ordered else -1
    if "handoff" not in skip:
        if name == "shot_simulations" and c.lt < .46:
            prev = A.SHOTS["shot_if_i_can"]
            before = A.raw(prev.end - 1 / FPS, round(prev.end * FPS) - 1, prev)["canvas"]
            portrait = before.crop((288, 82, 912, 594))
            dest = A.mapped((414, 70, 592, 214))
            u = A.ease(min(1., c.lt / .36))
            rect = A.lerp_rect((288, 82, 912, 594), dest, u)
            if c.lt > .32:
                local = A.ease((c.lt - .32) / .14)
                target = A.sample_object().resize(portrait.size, Image.Resampling.LANCZOS)
                portrait = Image.blend(portrait, target, local)
            ImageDraw.Draw(im).rectangle(dest, fill=tk.BG)
            A.paste_at(im, portrait, rect)
        if name == "shot_happy" and c.lt < .42:
            prev = A.SHOTS["shot_satisfaction"]
            before = A.body_image(A.raw(prev.end - 1 / FPS, round(prev.end * FPS) - 1, prev), "shot_satisfaction")
            im.paste(before.crop((24, 56, 700, 604)), (24, 56))
            u = A.ease(c.lt / .42)
            rect = A.lerp_rect((116, 92, 268, 226), (24, 56, 700, 604), u)
            old_face = before.crop((116, 92, 268, 226))
            happy_face = body["canvas"].crop((24, 56, 700, 604))
            local = A.ease((c.lt - .12) / .22)
            obj = Image.blend(old_face.resize(happy_face.size, Image.Resampling.LANCZOS), happy_face, local)
            A.paste_at(im, obj, rect)
    scan_names = {"shot_deeply", "shot_then_i_can", "shot_satisfaction", "shot_execution", "shot_trapped"}
    if "scan" not in skip and name in scan_names and c.lt < .26 and at > 0:
        prev = ordered[at - 1]
        before = A.body_image(A.raw(prev.end - 1 / FPS, round(prev.end * FPS) - 1, prev), prev.fn.__name__)
        u = A.ease(c.lt / .26)
        if name == "shot_then_i_can":
            y = round(56 + 478 * u)
            im.paste(before.crop((404, y, 1164, 534)), (404, y))
            ImageDraw.Draw(im).line((404, y, 1164, y), fill=tk.blue(.65))
        elif name == "shot_satisfaction":
            x = round(404 + 760 * u)
            im.paste(before.crop((x, 56, 1164, 534)), (x, 56))
        elif name in ("shot_trapped", "shot_deeply"):
            y = round(56 + 478 * u)
            im.paste(before.crop((404, y, 1164, 534)), (404, y))
        else:
            y = round(534 - 478 * u)
            im.paste(before.crop((404, 56, 1164, y)), (404, 56))
    assert not (name == "shot_strange" and c.lt < .58), "strange's own opening is not used by these cut windows"
    A.retained_objects(im, t, name, c)
    return im, c


def glyph_figure(shot, t, height, base=54):
    """Her figure in an approved pane (sidebar_chorus_v1: the native 3x5 glyph video), as sidebar.replacement
    draws it at time t of `shot`: (RGBA sprite, x offset of the pane rect)."""
    source = min(159, max(54, base + int(math.floor((t - shot.start) * 24 + 1e-6))))
    return A.sb.glyph(source, 340, height, "blue")


def sharp_ink(img, t, rect):
    """kit.ink with a hard edge: every pixel that differs from the stage background is kept at full strength, so
    the object composites back onto the background exactly where it was taken from."""
    rect = tuple(int(v) for v in rect)
    crop = img.crop(rect).convert("RGB")
    r, g, b = ImageChops.difference(crop, kit.stage.background(t).crop(rect)).split()
    a = ImageChops.lighter(ImageChops.lighter(r, g), b).point(lambda v: min(255, v * 64))
    out = crop.convert("RGBA")
    out.putalpha(a)
    return out


def lock_path(u: float) -> float:
    """Lift off gently, speed up into the target (a snap, not a drift), touch it a frame early, overshoot a little
    and lock in at u = 1."""
    if u >= 1:
        return 1.0
    if u < 0.92:
        return (u / 0.92) ** 1.5
    return 1.0 + 0.035 * math.sin(math.pi * (u - 0.92) / 0.08)


def paste_layer(layer, sp, x, y, clip):
    """engine.paste_clipped onto a transparent layer."""
    kit._composite_clipped(layer, sp, x, y, clip)


# ---------------------------------------------------------------- cut 24: travel -> unite

class C24(C.Cut):
    """travel -> unite (enters the approved chorus). The 30 position-id bars light up, merge in pairs (BPE.MERGE)
    and fly on arcs into the two tokenizer rows, where each pair locks in as a token chip on the beat; the unite
    panels decode outward from where the bars took off. In her pane the string dancer re-renders top-down, cell
    by cell, into the approved glyph portrait (held at full density, never through an empty pane)."""
    pre, post = 0.3, 0.62
    STRIP = (428, 300, 1146, 382)  # the bar strip of shot_travel (bars at x = 430 + 24 i, bottom 380, h <= 70)
    SEED = (784, 345)
    SIDE = (20, 42, 388, 614)  # her pane, a little oversize so the frame lines are inside the cell grid
    BODY = (400, 36, 1168, 612)

    def __init__(self, a, b):
        super().__init__(a, b)
        self.LAND = self.T + BEAT  # beat 118
        self.MERGE = self.T - 0.1  # pairs have merged; the bars stop changing height
        self.SIDE0 = self.T - 0.08  # her top-down re-render: starts here, ends on the landing beat
        self._plan = None
        self._merged = None

    def bars(self, t, canvas):
        """The 30 bars as travel draws them at t (measured on its canvas, so any version of the scene works),
        frozen once the pairs have merged: (x0, y0, x1, y1, colour)."""
        if t >= self.MERGE:
            if self._merged is None:
                self._merged = self.bars(self.MERGE - 1e-6, self.old(self.MERGE - 1e-6, round(self.MERGE * FPS))[0])
            return self._merged
        B = canvas.load()
        G = kit.stage.background(t).load()
        out = []
        for i in range(30):
            x = 430 + i * 24 + 9
            top = next((y for y in range(self.STRIP[1], 381)
                        if max(abs(B[x, y][j] - G[x, y][j]) for j in range(3)) > 24), 370)
            out.append((430 + i * 24, top, 430 + i * 24 + 18, 380, tk.amb(0.3 + 0.02 * i)))
        return out

    @staticmethod
    def chip_rect(row, g, t):
        """Screen rect of a token chip in the approved frame (the body is squeezed to 478/548 vertically)."""
        x = SC.chip_x(row, g, t)
        y = 80 + row * 170
        m = lambda v: 56 + (v - 56) * 478 / 548  # noqa: E731
        return x, m(y), x + 70, m(y + 22)

    def plan(self):
        """Which merged pair lands on which chip: monotone in x, nearest slots, both rows interleaved."""
        if self._plan is None:
            tl = self.LAND
            slots = []
            for row in (0, 1):
                v = SC.CHIP_SPEED[row]
                F = int((tl * v) // 90)
                for k in range(12):
                    x = 420 + k * 90 - (tl * v) % 90
                    if 410 < x < 1090:  # a chip further right has only just scrolled in: it appears on its own
                        slots.append((x, row, k + F))
            slots.sort()
            pairs = [430 + 48 * p + 21 for p in range(15)]
            n, m = len(pairs), len(slots)
            if m >= n:  # monotone matching that leaves m - n slots out
                INF = 1e18
                best = [[INF] * (m + 1) for _ in range(n + 1)]
                best[0] = [0.0] * (m + 1)
                for i in range(1, n + 1):
                    for j in range(i, m + 1):
                        best[i][j] = min(best[i][j - 1], best[i - 1][j - 1] + abs(pairs[i - 1] - slots[j - 1][0] - 35))
                pick, j = [], m
                for i in range(n, 0, -1):
                    while j > i and best[i][j] == best[i][j - 1]:
                        j -= 1
                    pick.append(j - 1)
                    j -= 1
                pick.reverse()
            else:
                pick = [round(p * (m - 1) / (n - 1)) for p in range(n)]
            self._plan = []
            for p, j in enumerate(pick):
                sx, row, g = slots[j]
                k = g - int((tl * SC.CHIP_SPEED[row]) // 90)
                word = SC.VOCAB[(k * 7 + row * 3 + int(tl * 2)) % len(SC.VOCAB)]
                if row == 0:
                    # the long hop bows toward the middle, clear of the 'me' and 'you' tokens (x 430-510, 1060-1140)
                    x160 = pairs[p] + 0.72 * (sx + 35 - pairs[p])
                    near = x160 < 560 or x160 > 1010
                    bend = (0.55 if near else 0.2) * (-1 if pairs[p] < 784 else 1)
                else:
                    bend = 0.25 * (1 if p % 4 == 0 else -1)
                self._plan.append(dict(p=p, row=row, g=g, word=word, depart=self.MERGE + 0.012 * p, bend=bend))
            self.targets = {(d["row"], d["g"]) for d in self._plan}
        return self._plan

    def shown(self, t):
        """Chip visibility for the hooked unite: a chip is placed when its carrier locks in on the beat."""
        self.plan()

        def f(row, g):
            return 1.0 if t >= self.LAND else 0.0
        return f

    def render(self, t, n):
        import v2
        T = self.T
        plan = self.plan()
        # the outgoing picture: travel's own drawing (its bars are lifted off it) with her, the string dancer
        oc, octx = self.old(t, n)
        bars = self.bars(t, oc)
        oc = oc.copy()
        oc.paste(kit.stage.background(t).crop(self.STRIP), self.STRIP[:2])
        old = oc.convert("RGBA")
        old.alpha_composite(kit.her_layer(t, v2.call_of(self.a), 1.0))
        old = old.convert("RGB")
        # the approved unite picture; her glyph portrait at full density, chips only where a carrier has landed
        nc, nctx = approved_pre(self.b, t, n, fn=SC.shot_unite, hooks={"reveal": 1.0, "chip": self.shown(t)})
        content = kit.reveal(old, nc, t, kit.radial(self.SEED, T - 0.08, 2400.0), region=self.BODY, cell=(8, 16),
                             seed=24)
        side_speed = (self.SIDE[3] - self.SIDE[1]) / (self.LAND - self.SIDE0)
        content = kit.reveal(content, nc, t, kit.sweep((0, self.SIDE[1]), (0, 1), self.SIDE0, side_speed),
                             region=self.SIDE, cell=(8, 13), seed=124)
        over = blank()
        d = ImageDraw.Draw(over)
        # her re-render front: a lit line, as for every change of her render
        fy = self.SIDE[1] + (t - self.SIDE0) * side_speed
        if 58 < fy < 602:
            d.line([30, fy, 378, fy], fill=tk.blue(0.9) + (230,), width=1)
        self.carriers(over, t, bars)
        return C.Frame(content, octx if t < T else nctx, over, her_alpha=0.0)

    def carriers(self, over, t, bars):
        T = self.T
        if t >= self.LAND + 0.1:
            return
        lift = clamp((t - (T - self.pre)) / 0.18)
        merge = ease_io((t - (self.MERGE - 0.1)) / 0.1)
        d = ImageDraw.Draw(over)
        glow = blank()
        gd = ImageDraw.Draw(glow)
        for c_ in self.plan():
            p = c_["p"]
            b0, b1 = bars[2 * p], bars[2 * p + 1]
            col = lerp(lerp(b0[4], b1[4], 0.5), (236, 240, 252), 0.55 * lift)
            if t < c_["depart"]:
                # lit in place, then the two bars of a pair close their gap and even out (the merge)
                hm = (b0[3] - b0[1] + b1[3] - b1[1]) / 2
                for (x0, y0, x1, y1, bc), side in ((b0, 0), (b1, 1)):
                    hh = lerp(y1 - y0, hm, merge)
                    if side == 0:
                        x1 = lerp(x1, x1 + 3, merge)
                    else:
                        x0 = lerp(x0, x0 - 3, merge)
                    cc = lerp(bc, (236, 240, 252), 0.55 * lift)
                    gd.rectangle([x0 - 3, y1 - hh - 3, x1 + 3, y1 + 3], fill=tk.blue(1.0) + (int(90 * lift),))
                    d.rectangle([x0, y1 - hh, x1, y1], fill=C.rgba(cc))
                continue
            # flight: an arc to its chip (which keeps scrolling), 1.3x a chip mid-flight, dimming to the chip's own
            # look as it arrives; on the beat the real chip takes its place and the carrier is gone (lock-in)
            x0, y0, x1, y1 = self.chip_rect(c_["row"], c_["g"], t)
            if t >= self.LAND:
                k = 1 - (t - self.LAND) / 0.1
                gd.rectangle([x0 - 3, y0 - 3, x1 + 3, y1 + 3], fill=tk.blue(1.0) + (int(110 * k),))
                continue
            u = clamp((t - c_["depart"]) / (self.LAND - c_["depart"]))
            pth = lock_path(u)
            e = clamp(pth)
            hm = (b0[3] - b0[1] + b1[3] - b1[1]) / 2
            src = (b0[0] + 21, 380 - hm / 2)
            dst = ((x0 + x1) / 2, (y0 + y1) / 2)
            cx, cy = kit.bezier(src, dst, c_["bend"], pth)
            grow = 1 + 0.3 * math.sin(math.pi * min(1.0, e / 0.9))
            w = lerp(42, 70, e) * grow
            hh = lerp(hm, y1 - y0, e) * grow
            fill_a = 1 - clamp((u - 0.6) / 0.32)
            rect = [cx - w / 2, cy - hh / 2, cx + w / 2, cy + hh / 2]
            gd.rectangle([rect[0] - 4, rect[1] - 4, rect[2] + 4, rect[3] + 4],
                         fill=tk.blue(1.0) + (int(40 + 80 * (1 - u)),))
            if fill_a > 0.02:
                d.rectangle(rect, fill=C.rgba(col, 255 * fill_a))
            d.rectangle(rect, outline=C.rgba(lerp(col, tk.amb(0.45), clamp((u - 0.6) / 0.32))),
                        width=2 if u < 0.85 else 1)
            if u > 0.15:
                sp, off = kit.text_sprite(c_["word"], tk.F_MONO, 15,
                                          tk.BG if fill_a > 0.5 else C.rgba(lerp((236, 240, 252), tk.amb(0.5), e))[:3])
                sc = lerp(1.45, 1.0, e)
                # centred in flight, at the chip's own text origin (x + 6, y + 3) on arrival
                fin = (rect[0] + 6 + off[0] + sp.width / 2, rect[1] + 3 * 478 / 548 + off[1] + sp.height / 2)
                kit.place(over, sp, lerp((cx, cy), fin, e ** 4), sc, clamp((u - 0.15) / 0.15))
        glow = glow.filter(ImageFilter.GaussianBlur(4))
        glow.alpha_composite(over)
        for rect in self.tokens(t):  # the carriers pass behind the 'me' and 'you' tokens, never over their text
            glow.paste((0, 0, 0, 0), rect)
        over.paste(glow)

    def tokens(self, t):
        """Screen rects of unite's 'me' and 'you' tokens with their id labels (they converge from lt = 0.3)."""
        b = self.b
        m = SC.ease((max(t, b.start) - b.start - 0.3) / ((b.end - b.start) * 0.62))
        sq = lambda v: round(56 + (v - 56) * 478 / 548)  # noqa: E731
        out = []
        for x_from, x_to in ((430, 784 - 45), (1060, 784 + 5)):
            x = x_from + (x_to - x_from) * m
            out.append((round(x) - 3, sq(147), round(x) + 84, sq(216)))
        return out


# ---------------------------------------------------------------- cut 26: deeply -> if_i_can

class C26(C.Cut):
    """deeply -> if_i_can (the chorus hook). Her glyph rows light up and stream out of her pane to the right; each
    row is the write head of one row of the glyph field. They cross her pane's edge on the cut, and IF I CAN is
    written behind the heads from that edge across the body, complete on the beat of the first 'can'. Behind her the
    field backfills her pane, whose frame fades over six frames instead of breaking."""
    pre, post = 0.34, 0.8
    REGION = (20, 36, 1172, 612)  # 8 x 16 cells; the field rows (y = 68 + 16 r) are rows 2..34 of this grid
    EDGE = 384  # her pane's right edge
    RIGHT = 1172

    def __init__(self, a, b):
        super().__init__(a, b)
        self.END = self.T + 1.5 * BEAT  # beat at 59.236: the heads reach the right edge
        self.START = self.T - 0.33
        self._rows = None

    def pane_call(self, t):
        a = self.a
        return SC.deeply_pane(SimpleNamespace(lt=min(t, a.end - 1 / FPS) - a.start, dur=a.end - a.start))

    def figure(self, t):
        """Her figure in the deeply pane at t (still dancing after the cut): RGBA full-frame layer."""
        call = self.pane_call(t)
        fig = glyph_figure(self.a, t, 294)
        layer = blank()
        out = Image.new("RGBA", (352, fig.height))
        out.alpha_composite(fig, (6, 0))
        paste_layer(layer, out, 28, 56 + 14 + call["dy"], (26, 68, 382, 526))
        return layer, call

    def rows(self):
        """Per 16 px band of the region: when its front starts (t0), crosses her pane's edge (tm) and reaches the
        right edge (t1), and her extent in that band (L, R), if she is in it."""
        if self._rows is None:
            layer, _ = self.figure(self.START)
            al = layer.getchannel("A").point(lambda v: 255 if v > 60 else 0)
            x0, y0, x1, y1 = self.REGION
            nb = (y1 - y0) // 16
            ext = []
            for k in range(nb):
                bb = al.crop((0, y0 + 16 * k, 400, y0 + 16 * k + 16)).getbbox()
                ext.append((bb[0], min(bb[2], self.EDGE - 8)) if bb and bb[2] - bb[0] > 6 else None)
            her = [k for k in range(nb) if ext[k]]
            kc = (her[0] + her[-1]) / 2
            span = max(1.0, (her[-1] - her[0]) / 2)
            rows = []
            for k in range(nb):
                jit = ((k * 37) % 5 - 2) / FPS * 0.25
                if ext[k]:
                    d = abs(k - kc) / span
                    t0, tm = self.START + 0.05 * d, self.T + 0.03 * d
                    L, R = ext[k]
                else:
                    dk = min(abs(k - j) for j in her)
                    t0 = tm = self.T - 0.06 + 0.02 * dk
                    L = R = self.EDGE
                rows.append(dict(k=k, t0=t0, tm=tm, t1=self.END + jit, L=L, R=R, her=bool(ext[k])))
            self._rows = rows
        return self._rows

    def band(self, y):
        k = int((y - self.REGION[1]) // 16)
        return self.rows()[max(0, min(len(self.rows()) - 1, k))]

    def front_x(self, r, t):
        """The write head of a row: her row eases out to her pane's edge (until tm), then runs to the right edge."""
        if t < r["tm"]:
            if not r["her"]:
                return self.EDGE
            u = clamp((t - r["t0"]) / (r["tm"] - r["t0"]))
            return r["R"] + (self.EDGE - r["R"]) * u * u
        v = clamp((t - r["tm"]) / (r["t1"] - r["tm"]))
        return self.EDGE + (self.RIGHT - self.EDGE) * (0.8 * v + 0.2 * v * v)

    def x_time(self, r, X):
        """Inverse of front_x: when the head of row r is at X."""
        if X >= self.EDGE or not r["her"]:
            y = clamp((X - self.EDGE) / (self.RIGHT - self.EDGE))
            v = (-0.8 + math.sqrt(0.64 + 0.8 * y)) / 0.4
            return r["tm"] + v * (r["t1"] - r["tm"])
        u = math.sqrt(clamp((X - r["R"]) / max(1.0, self.EDGE - r["R"])))
        return r["t0"] + u * (r["tm"] - r["t0"])

    def front_time(self, x, y):
        """When a cell of the field is written: behind the head of its row, behind her tail as she leaves, and in
        the rest of her pane from the cut on, back toward her pane's left edge."""
        r = self.band(y)
        if x >= r["R"]:
            return self.x_time(r, x)
        if r["her"] and x >= r["L"]:
            return self.x_time(r, r["R"] + (x - r["L"]))
        if r["her"]:
            return self.T - 0.06 + (r["L"] - x) / 1500.0
        return r["t0"] + (self.EDGE - x) / 1500.0

    def pane_ui(self, t, k):
        """Her pane without her: frame, title, bubbles and softmax, faded by k."""
        call = dict(self.pane_call(t))
        layer = blank()
        c = engine.Ctx(layer, ImageDraw.Draw(layer), t, 0.0, 1.0, random.Random(int(t * FPS) * 7919))
        engine.me_pane(c, call.pop("expr"), morph=0.0, **call)
        return tk.scale_alpha(layer, k)

    def scan_line(self, layer, t, k):
        """The pitch scan line of her pane, drawn over her as the pane draws it, faded by k."""
        import music
        feat = music.at(t)
        ly = 70 + self.pane_call(t)["dy"] + int((0.92 - 0.84 * feat.cent) * 294)
        if 68 < ly < 526 and k > 0.01:
            line = blank()
            ImageDraw.Draw(line).line([36, ly, 372, ly], fill=tk.blue(0.25 + 0.4 * feat.loud) + (255,))
            layer.alpha_composite(tk.scale_alpha(line, k))

    def render(self, t, n):
        T = self.T
        oc, octx = approved_pre(self.a, t, n, fn=SC.shot_deeply, hooks={"pane": False})
        nc, nctx = approved_pre(self.b, t, n, fn=SC.shot_if_i_can, hooks={"front": self.front_time})
        content = kit.reveal(oc, nc, t, self.front_time, region=self.REGION, cell=(8, 16), seed=26, dur=0.07)
        content = content.convert("RGBA")
        box_k = 1 - ease_io((t - (T - 0.12)) / 0.25)
        if box_k > 0.01:
            content.alpha_composite(self.pane_ui(t, box_k))
        over = blank()
        fig, _ = self.figure(t)
        lift = clamp((t - self.START) / 0.14)
        f = tk.font(tk.F_MONO_B, 14)
        cw = f.getlength("M")
        heads = blank()
        hd = ImageDraw.Draw(heads)
        for r in self.rows():
            y = self.REGION[1] + 16 * r["k"]
            if t < r["t0"] - 0.02:
                if r["her"]:
                    over.alpha_composite(brighten(fig.crop((0, y, 400, y + 16)), 0.45 * lift), (0, y))
                continue
            X = self.front_x(r, t)
            if r["her"]:  # her row, lit, slides out ahead of the field it writes
                strip = fig.crop((0, y, 400, y + 16))
                strip = brighten(strip, 0.45 * lift)
                travel = clamp((X - r["R"]) / (self.RIGHT - r["R"]))
                strip = tk.scale_alpha(strip, (1 - 0.8 * travel ** 1.5) * clamp(1 - (t - r["t1"]) / 0.06))
                dx = round(X - r["R"])
                if 1164 - dx > 0:
                    over.alpha_composite(strip.crop((0, 0, min(400, 1164 - dx), 16)), (dx, y))
            if 2 <= r["k"] <= 34 and X < 1160 and r["t0"] <= t < r["t1"] + 0.04:  # the write head of this row
                q = int(t * FPS) + r["k"]
                s = "IFICAN"[q % 6] + "IFICAN"[(q + 2) % 6]
                hd.text((X - 2 * cw, y), s, font=f, fill=(226, 234, 255, 255))
        self.scan_line(over, t, box_k)
        if t < self.END + 0.1:
            halo = heads.filter(ImageFilter.GaussianBlur(3)).point(lambda v: min(255, v * 2))
            glow = Image.new("RGBA", heads.size, tk.blue(1.0) + (0,))
            glow.putalpha(halo.getchannel("A"))
            over.alpha_composite(glow)
            over.alpha_composite(heads)
        return C.Frame(content, octx if t < T else nctx, over, her_alpha=0.0)


# ---------------------------------------------------------------- cut 31: happy -> execution

class C31(C.Cut):
    """happy -> execution (mirror of cut 30's push-in). The grad-cam close-up pulls back: the face shrinks into her
    head in the pane while the panel frame contracts onto her pane frame and retitles to /dev/me. On the beat the
    face re-renders cell by cell as the glyph dancer's head and her body grows out from it; the agent loop and the
    tool call fill the body behind the retreating frame, left to right. ONLY stays where it is."""
    pre, post = 0.09, 0.8
    REGION = (20, 36, 1172, 612)
    FACE = (30, 60, 696, 600)  # where the grad-cam face and its heat map are drawn

    def __init__(self, a, b):
        super().__init__(a, b)
        self.S0 = self.T - 2 / FPS
        self.S1 = self.T + BEAT  # beat at 68.466: the face is her head again
        self._head = None

    def u(self, t):
        return ease_io((t - self.S0) / (self.S1 - self.S0))

    def head(self):
        """Where the face lands: her head in the execution pane at the landing beat, as (x0, y0, x1, y1)."""
        if self._head is None:
            fig = glyph_figure(self.b, self.S1, 444)
            al = fig.getchannel("A").point(lambda v: 255 if v > 60 else 0)
            bb = al.getbbox()
            top = al.crop((0, bb[1], fig.width, bb[1] + 110)).getbbox()
            cx = 34 + (top[0] + top[2]) / 2
            cy = 70 + bb[1] + 62
            w = 150
            hh = w * 510 / 640
            # the face centre of the close-up (338, 350 of its 640 x 510 sprite) goes on her face
            fx, fy = 338 / 640 * w, 350 / 510 * hh
            x0, y0 = cx - fx, cy - fy
            self._head = (x0, y0, x0 + w, y0 + hh), (cx, cy)
        return self._head

    def edge_time(self, x):
        """When the contracting frame's right edge (700 -> 384) passes x."""
        e = clamp((700 - x) / 316)
        if e <= 0:
            return -1e9
        u = (e / 4) ** (1 / 3) if e < 0.5 else 1 - (2 * (1 - e)) ** (1 / 3) / 2
        return self.S0 + u * (self.S1 - self.S0)

    def delay(self, x, y):
        (hx0, hy0, hx1, hy1), (cx, cy) = self.head()
        if x < 388:
            if hx0 <= x < hx1 and hy0 <= y < hy1:  # the face itself becomes her glyph head on the beat
                return self.S1 - 0.02
            # her body grows out from around her head while the face settles into it
            return self.S1 - 0.16 + math.hypot(x - cx, (y - cy) * 0.8) / 2000.0
        return max(self.T + 0.17 + (x - 388) / 2680.0, self.edge_time(x) + 0.02)

    def render(self, t, n):
        T = self.T
        e = self.u(t)
        hc, hctx = approved_pre(self.a, t, n, fn=SC.shot_happy, hooks={"face_frame": False})
        face = sharp_ink(hc, t, self.FACE)
        old = hc.copy()
        old.paste(kit.stage.background(t).crop((22, 40, 706, 612)), (22, 40))
        od = ImageDraw.Draw(old)
        # the grad-cam frame contracts onto her pane frame and retitles
        x1 = round(lerp(700, 384, e))
        lvl = lerp(0.55 + 0.3 * engine.pulse(t), 0.45 + 0.35 * engine.pulse(t), e)
        t_title = self.S0 + 0.45 * (self.S1 - self.S0)
        if t < t_title:
            title = SC.HAPPY_TITLE
        else:
            title = tk.decode("/dev/me  pid 4471", t - t_title, random.Random(n), 40.0, 0.1) or "/"
        tk.box(od, 24, 56, x1, 604, title, lvl, spinner=t)
        # the face shrinks back into her head (its centre travels to her face)
        (hx0, hy0, hx1, hy1), _ = self.head()
        fx0, fy0, fx1, fy1 = self.FACE
        rect = (lerp(fx0, hx0 - (42 - fx0) * (hx1 - hx0) / 640, e), lerp(fy0, hy0 - (70 - fy0) * (hy1 - hy0) / 510, e))
        sc = lerp(1.0, (hx1 - hx0) / 640, e)
        fw, fh = max(1, round(face.width * sc)), max(1, round(face.height * sc))
        sp = face.resize((fw, fh), Image.LANCZOS) if (fw, fh) != face.size else face
        old = old.convert("RGBA")
        old.alpha_composite(sp, (round(rect[0]), round(rect[1])))
        old = old.convert("RGB")
        fa = 1 - clamp((t - self.S0) / 0.16)  # the panel's attribution line goes with the panel
        if fa > 0.02:
            ImageDraw.Draw(old).text((40, 576), SC.attribution((t - self.a.start) / (self.a.end - self.a.start)),
                                     font=tk.font(tk.F_MONO_B, 16), fill=tk.mix(tk.amb(0.95), fa))
        nc, nctx = approved_pre(self.b, t, n, skip=("scan",))
        content = kit.reveal(old, nc, t, self.delay, region=self.REGION, cell=(8, 16), seed=31)
        over = None
        k = max(0.0, 1 - abs(t - self.S1) / 0.15)
        if k > 0.01:  # the frame locks around her
            over = blank()
            tk.box(ImageDraw.Draw(over), 24, 56, 384, 604, "", 0.9 * k)
            over = tk.scale_alpha(over, k)
        return C.Frame(content, hctx if t < T else nctx, over, her_alpha=0.0)


CUTS = {24: C24, 26: C26, 31: C31}
