"""Section 07 EXECUTION (cuts 64-85, 147.6 - 176.9 s).

The thirteen EXECUTION hits (shots 64-75, 77) and the count (76) are hard cuts on the music and stay as they were
judged (OWN = the v1 frame), with three fixes: the lay2 EXECUTE banner fits the frame (scenes_exec), the count is
full-bleed instead of letterboxed and each number lands on its own syllable, and the last hit (#13) already draws
the v2 chrome, so the lyric band settles into its standard place on a hit and not on the MORPH that follows.

The red chorus (78-85) mirrors chorus 1 in red, one staged cut each (see the class docstrings):
  78 MORPH   the EXECUTION banner's cells become the IF I CAN glyph cells, left to right as it is sung
  79 MORPH   her glyph portrait bursts into thirteen copies of herself: twelve samples and the dancer in her pane
  80 CARRY   crossed sample #0000 flies into her; red spreads out of her pane over the UI
  81 UNFOLD  the receptive field becomes her eye bar; the conv readout becomes the 'execution' logit
  82 RETAIN  the one 'execution' leaves the logits and is pinned bottom right on 'If I can have ...'
  83 CARRY   'you: not found' rises and becomes the first line of the tool call
  84 CARRY   'reason="have_you_back"' becomes the 'pinned: you' label; EXECUTE breaks into the six pinned blocks;
             the cache fills one row per frame
  85 CRT     the whole frame (chrome, band, her) squashes into a line on the beat, the line into a dot
She is the string dancer throughout; angry/execute is an eye bar (OVERLAY) and a red tint, never another portrait.
"""
from __future__ import annotations

import math
import random
import sys
from functools import lru_cache

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

import cuts as C
import kit
import scenes_exec as X
import sec_final
from cuts import Cut, Frame, text_at
from kit import (BEAT, FPS, H, LEFT, PANE, W, bezier, blank, brighten, clamp, ease_back, ease_in, ease_io, ease_out,
                 engine, haloed, lerp, place, radial, sweep, text_sprite, tk)

ALL = kit.v1.ALL


def _index(name, k=None):
    for i, s in enumerate(ALL):
        if s.fn.__name__ == name and (k is None or s.params.get("k") == k):
            return i
    raise KeyError(name)


# the fn names are swapped by v2's REPLACE; find the shots by their original names and parameters
HITS = [i for i, s in enumerate(ALL) if s.fn.__name__ == "shot_exec_hit"]
COUNT = _index("shot_count")
LAST_HIT = _index("shot_exec_hit", 12)
RED_IF, EXEC_ALL, RED_THEN, ONLY, BACK, RUN, TRAPPED, COLLAPSE = (
    _index(n) for n in ("shot_red_if_i_can", "shot_execute_all", "shot_red_then_i_can", "shot_only_execution",
                        "shot_have_you_back", "shot_run_again", "shot_red_trapped", "shot_collapse"))
assert (HITS[0], COUNT, LAST_HIT, COLLAPSE) == (64, 76, 77, 85), (HITS, COUNT, LAST_HIT, COLLAPSE)
T = {i: ALL[i].start for i in range(64, 87)}  # cut times by incoming shot index

DS_BLUE = tk.BLUE_MID


def _v2():
    """The running frame loop (v2.py as __main__) if there is one, else the importable module."""
    m = sys.modules.get("__main__")
    if m is not None and hasattr(m, "her_anchor") and hasattr(m, "CUT_CLASSES"):
        return m
    import v2
    return v2


def her_bbox(t: float):
    """Her figure's bounding box on screen (as her_anchor measures it)."""
    a = _v2().her(t).getchannel("A")
    x0, y0, x1, y1 = LEFT
    box = (x0 + 4, y0 + 14, x1 - 4, y1 - 80)
    bb = a.crop(box).point(lambda v: 255 if v > 60 else 0).getbbox()
    if not bb:
        return 60, 90, 350, 520
    return box[0] + bb[0], box[1] + bb[1], box[0] + bb[2], box[1] + bb[3]


def mixc(a, b, u):
    return X.mixc(a, b, u)


def rgba(col, a=1.0):
    return tuple(int(v) for v in col[:3]) + (int(255 * clamp(a)),)


def reveal_c(old, new, t, delay, region=PANE, cell=(8, 16), dur=0.08, seed=0, density=0.4, color=tk.red):
    """kit.reveal with the decoding glyphs in the scene's own colour (red in the red chorus)."""
    x0, y0, x1, y1 = region
    cw, ch = cell
    cols, rows = (x1 - x0) // cw, (y1 - y0) // ch
    rw, rh = cols * cw, rows * ch
    box_ = (x0, y0, x0 + rw, y0 + rh)
    m = Image.new("L", (cols, rows), 0)
    mp = m.load()
    ps = []
    for r in range(rows):
        cy = y0 + r * ch + ch / 2
        for q in range(cols):
            cx = x0 + q * cw + cw / 2
            p = clamp((t - delay(cx, cy)) / dur)
            mp[q, r] = int(255 * p)
            if 0.02 < p < 0.98:
                ps.append((q, r, p))
    lo, hi = m.getextrema()
    if not ps and hi == 0:
        return old.copy()
    out = old.copy()
    if not ps and lo == 255:
        out.paste(new.crop(box_), box_[:2])
        return out
    mask = m.resize((rw, rh), Image.NEAREST)
    out.paste(Image.composite(new.crop(box_), old.crop(box_), mask), box_[:2])
    if ps:
        bg = kit.stage.background(t).crop(box_)
        inks = []
        for im in (old, new):
            r_, g_, b_ = ImageChops.difference(im.crop(box_).convert("RGB"), bg).split()
            lv = ImageChops.lighter(ImageChops.lighter(r_, g_), b_).resize((cols, rows), Image.BOX)
            inks.append(lv.load())
        d = ImageDraw.Draw(out)
        f = tk.font(tk.F_MONO_B, 13)
        rng = random.Random(seed * 9973 + int(t * FPS))
        for q, r, p in ps:
            ch_ = rng.choice(kit.GLYPHS)
            if inks[0][q, r] < 6 and inks[1][q, r] < 6 or rng.random() > density:
                continue
            k = 1 - abs(2 * p - 1)
            d.text((x0 + q * cw, y0 + r * ch), ch_, font=f, fill=color(0.25 + 0.65 * k))
    return out


def sprite_center(s, path, size, xy):
    """Centre of the text sprite whose draw origin is xy."""
    sp, off = text_sprite(s, path, size, (255, 255, 255))
    return xy[0] + off[0] + sp.width / 2, xy[1] + off[1] + sp.height / 2


def text_c(layer, s, path, size, color, center, scale=1.0, alpha=1.0, halo=0.0, lift=0.0, halo_color=None):
    sp, _ = text_sprite(s, path, size, tuple(int(v) for v in color[:3]) + (255,))
    if lift > 0:
        sp = brighten(sp, lift)
    if halo > 0:
        sp = haloed(sp, halo, halo_color)
    place(layer, sp, center, scale, alpha)


def quad(p0, c, p1, u):
    a, b, cc = (1 - u) ** 2, 2 * (1 - u) * u, u * u
    return a * p0[0] + b * c[0] + cc * p1[0], a * p0[1] + b * c[1] + cc * p1[1]


# ================================================================ the hits (OWN)

def hit_frame(t, n):
    return kit.v1.frame(n)


def count_frame(t, n):
    """The count, full-bleed (the author removed the cinema letterbox); otherwise exactly the v1 frame."""
    body = kit.v1.raw(t, n, ALL[COUNT])
    body["mode"] = "fullbleed"
    return engine.post(engine.finish(body), None)


def last_hit_frame(t, n):
    """Hit #13 as judged (banner, target line, the red strobe on the next beat), but with the v2 chrome: from this
    hit on the lyric sits in the standard band, so the red chorus starts without a chrome change."""
    canvas, ctx = C.body(ALL[LAST_HIT], t, n)
    img = kit.chrome(canvas.convert("RGBA"), t, ctx).convert("RGB")
    if ctx.flash_red:
        img = ImageOps.colorize(img.convert("L"), black=tk.BG, white=tk.RED, mid=(150, 30, 20)).convert("RGB")
    return engine.post(img, None)


# ================================================================ her: eye bar, kernel, walls (OVERLAY)

def eye_level(t: float) -> float:
    """How far the EXECUTE eye bar is drawn out across her eyes (0..1), over the whole red chorus."""
    keys = [(T[79] + 0.14, 0.0), (T[79] + 0.30, 1.0), (T[80] - 0.18, 1.0), (T[80] - 0.03, 0.0),
            (T[81] + C81.LAND - 0.001, 0.0), (T[81] + C81.LAND, 1.0), (T[82] + 0.02, 1.0), (T[82] + 0.18, 0.0),
            (T[83] - 0.06, 0.0), (T[83] + 0.12, 1.0), (T[84] + 0.02, 1.0), (T[84] + 0.18, 0.0)]
    if t <= keys[0][0] or t >= keys[-1][0]:
        return 0.0
    for (a, va), (b, vb) in zip(keys, keys[1:]):
        if a <= t < b:
            return va + (vb - va) * ease_io((t - a) / (b - a))
    return 0.0


def eye_rect(t: float):
    """The eye bar's full rectangle on her face: under the head anchor, across her face."""
    hx, hy = _v2().her_anchor(t, "head")
    bb = her_bbox(t)
    w = max(112, min(160, 0.45 * (bb[2] - bb[0])))
    y = hy - 8
    return hx - w / 2, y, hx + w / 2, y + 18


def draw_eyebar(layer, rect, level: float = 1.0, alpha: float = 1.0, text: bool = True) -> None:
    if level <= 0.01 or alpha <= 0.01:
        return
    x0, y0, x1, y1 = rect
    cx = (x0 + x1) / 2
    hw = (x1 - x0) / 2 * level
    glow = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).rectangle([cx - hw - 2, y0 - 2, cx + hw + 2, y1 + 2], fill=rgba(tk.RED, 0.5 * alpha))
    layer.alpha_composite(glow.filter(ImageFilter.GaussianBlur(4)))
    d = ImageDraw.Draw(layer)
    d.rectangle([cx - hw, y0, cx + hw, y1], fill=rgba(tk.red(1.0), alpha))
    if text and level > 0.75:
        f = tk.font(tk.F_MONO_B, 14)
        tw = d.textlength("EXECUTE", font=f)
        d.text((cx - tw / 2, y0 + 1), "EXECUTE", font=f, fill=rgba(tk.BG, alpha * clamp((level - 0.75) / 0.2)))


def eye_overlay(t, n):
    k = eye_level(t)
    if k <= 0.01:
        return None
    layer = blank()
    draw_eyebar(layer, eye_rect(t), k)
    return layer


def kernel_box(t: float):
    """The 3x3 receptive field on her figure while the red conv scans her (shot 80), as a screen rect."""
    s = ALL[RED_THEN]
    st = X.conv_state(t, t - s.start, s.end - s.start)
    x0, y0, x1, y1 = her_bbox(t)
    cw_, ch_ = (x1 - x0) / st["mc"], (y1 - y0) / st["mr"]
    x, y = x0 + (st["ki"] - 1) * cw_, y0 + (st["kj"] - 1) * ch_
    return (x, y, x + 3 * cw_, y + 3 * ch_), (x0, x1)


def kernel_overlay(t, n):
    if t >= T[81] - C81.GROW_EARLY:
        return None  # cut 81 carries the square off
    layer = blank()
    (x0, y0, x1, y1), (fx0, fx1) = kernel_box(t)
    d = ImageDraw.Draw(layer)
    ym = (y0 + y1) / 2
    d.line([fx0 - 6, ym, fx1 + 6, ym], fill=rgba(tk.red(1.0), 0.45))
    d.rectangle([x0, y0, x1, y1], outline=(255, 226, 214, 255), width=2)
    return layer


WALL_INSETS = [0, 24, 48, 70]


def walls_overlay(t, n):
    """Though we are trapped: her sandbox closes in one wall per beat, around the dancer (who is not rescaled)."""
    s = ALL[TRAPPED]
    layer = eye_overlay(t, n) or blank()
    u = (t - s.start) / (s.end - s.start)
    k = min(3, int(u * 4))
    d = ImageDraw.Draw(layer)
    x0, y0, x1, y1 = LEFT
    for j in range(1, k + 1):
        i2 = WALL_INSETS[j]
        fresh = clamp(1 - (u * 4 - j) / 0.5) if j == k else 0.0
        col = mixc(tk.red(0.55), (255, 200, 190), 0.6 * fresh)
        d.rectangle([x0 + i2, y0 + i2, x1 - i2, y1 - i2 // 2], outline=rgba(col, 0.85), width=2)
    return layer


# ================================================================ cut 78: the banner's cells become IF I CAN

class C78(Cut):
    """exec_hit #13 -> red_if_i_can. MORPH: the EXECUTION banner lights up, then its red cells travel to the
    nearest IF I CAN glyph cells, left to right, locking in as 'If I can' is sung (If ~162.2, can ~162.5). The
    banner gives way cell by cell exactly where its cells leave; never more than 40 % of the cells are in flight,
    and what has landed is the new letters, so the frame never goes dark."""
    pre, post = 0.27, 0.45
    FLY = 0.15
    START, SPAN = -0.21, 0.44  # departures sweep from T+START over SPAN seconds, by target x

    def plan(self):
        if hasattr(self, "_plan"):
            return self._plan
        T_ = self.T
        sp = tk.banner_block("EXECUTION", 44, 11, tk.RED, tk.BG, 1120)
        bx, by = 24 + (1140 - sp.width) // 2, 300 - sp.height // 2
        self.banner = (sp, bx, by)
        mask = Image.new("L", (W, H), 0)
        mask.paste(sp.getchannel("A").point(lambda v: 255 if v > 100 else 0), (bx, by))
        gx1, gy1 = int(X.GX0 + X.COLS * X.CW), X.GY0 + X.ROWS * X.CH
        cov = mask.crop((X.GX0, X.GY0, gx1, gy1)).resize((X.COLS, X.ROWS), Image.BOX).load()
        src = [(q, r) for r in range(X.ROWS) for q in range(X.COLS) if cov[q, r] > 70]
        tg = sorted(X.ifican_cells(), key=lambda c: (c[0], c[1]))
        xs = [X.cell_xy(q, r)[0] for q, r, _ in tg]
        xmin, xmax = min(xs), max(xs)
        use = {}
        rng = random.Random(78)
        cells = []
        n_tg = len(tg)
        for j, (q, r, letter) in enumerate(tg):
            tx, ty = X.cell_xy(q, r)
            best, bd = None, 1e18
            for sq, sr in src:
                sx, sy = X.cell_xy(sq, sr)
                dd = math.hypot(sx - tx, (sy - ty) * 0.8) + 26 * use.get((sq, sr), 0)
                if dd < bd:
                    best, bd = (sq, sr), dd
            use[best] = use.get(best, 0) + 1
            # left to right at an even rate of cells (not of pixels), so the share in flight stays constant
            td = T_ + self.START + self.SPAN * j / n_tg + rng.uniform(0, 0.02)
            cells.append(dict(q=q, r=r, letter=letter, src=X.cell_xy(*best), dst=(tx, ty), td=td, tl=td + self.FLY,
                              key=best))
        # the departure front as a function of x (for everything that is not a carried cell)
        self.front = sorted((c_["dst"][0], c_["td"]) for c_ in cells)
        sd = {}
        for c_ in cells:
            sd[c_["key"]] = min(sd.get(c_["key"], 1e9), c_["td"])
        for sq, sr in src:  # banner cells nobody needed: they give way with the front
            if (sq, sr) not in sd:
                sd[(sq, sr)] = self.front_t(X.cell_xy(sq, sr)[0]) + 0.04
        self._plan = dict(cells=cells, sd=sd)
        return self._plan

    def front_t(self, x):
        import bisect
        fr = self.front
        k = bisect.bisect_left(fr, (x, -1e9))
        return fr[min(k, len(fr) - 1)][1]

    def lit(self, oc, k):
        """The old banner lights up before it breaks (the carrier's lift)."""
        if k <= 0.01:
            return oc
        sp, bx, by = self.banner
        out = oc.convert("RGBA")
        out.alpha_composite(tk.scale_alpha(brighten(sp, 0.45), k), (bx, by))
        halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        halo.paste(sp, (bx, by))
        halo = halo.filter(ImageFilter.GaussianBlur(6))
        out.alpha_composite(tk.scale_alpha(halo, 0.6 * k))
        return out.convert("RGB")

    def in_flight(self, t):
        cells = self.plan()["cells"]
        return sum(1 for c_ in cells if c_["td"] <= t < c_["tl"]) / len(cells)

    def render(self, t, n):
        P = self.plan()
        T_ = self.T
        landed = {(c_["q"], c_["r"]) for c_ in P["cells"] if t >= c_["tl"]}
        oc, octx = self.old(t, n)
        nc, nctx = self.new(t, n, landed=lambda q, r: (q, r) in landed)
        lift = clamp((t - (T_ - self.pre)) / 0.08) * (1 - clamp((t - (T_ + self.START)) / 0.3))
        oc = self.lit(oc, lift)
        sd = P["sd"]

        def delay(cx, cy):
            v = sd.get((math.floor((cx - X.GX0) / X.CW), math.floor((cy - X.GY0) / X.CH)))
            if v is not None:
                return v
            return self.front_t(cx) + 0.06

        content = reveal_c(oc, nc, t, delay, region=(20, 36, 1164, 612), dur=0.06, seed=78)
        over = blank()
        d = ImageDraw.Draw(over)
        f = tk.font(*X.GF)
        for c_ in P["cells"]:
            if not c_["td"] <= t < c_["tl"]:
                continue
            u = ease_io((t - c_["td"]) / self.FLY)
            x, y = lerp(c_["src"], c_["dst"], u)
            d.rectangle([x, y + 1, x + X.CW - 1, y + X.CH - 1], fill=rgba(tk.red(0.55)))
            d.text((x, y), c_["letter"], font=f, fill=(255, 196, 186, 255))
        return Frame(content, self.pick(t, octx, nctx), over, her_shift=1.0)


# ================================================================ cut 79: her portrait bursts into thirteen

class C79(Cut):
    """red_if_i_can -> execute_all. MORPH: her red glyph portrait lights up and bursts; every glyph flies straight
    to the same spot of her figure in one of thirteen copies of her: the twelve samples and the dancer in her pane.
    A glyph turns DS blue only as it enters its target; each sample decodes where its glyphs land, and she forms
    in her pane from hers on the half beat after 'Give them all' (164.24). Everything stays inside the body, under
    the lyric band."""
    pre, post = 0.33, 0.42
    FLY = 0.34
    LAND = 0.23  # after T: beat 355.5

    def plan(self):
        if hasattr(self, "_plan"):
            return self._plan
        T_ = self.T
        cells = X.portrait_cells()
        qs, rs = [c_[0] for c_ in cells], [c_[1] for c_ in cells]
        q0, q1, r0, r1 = min(qs), max(qs), min(rs), max(rs)
        targets = [her_bbox(T_ + 0.45)]
        for i in range(12):
            art = X.tile_art(i)
            ax, ay = X.tile_art_xy(i)
            bb = art.getchannel("A").getbbox() or (0, 0, art.width, art.height)
            targets.append((ax + bb[0], ay + bb[1], ax + bb[2], ay + bb[3]))
        rng = random.Random(79)
        # the portrait breaks along the layout it is about to become: its left part is her, the rest a 4 x 3 grid
        # of pieces, one per sample. Each piece travels as one body (one arc, one clock) and spreads over its target.
        split = q0 + 0.3 * (q1 - q0)

        def group(q, r):
            if q < split:
                return 0
            col = min(3, int((q - split) / (q1 + 1 - split) * 4))
            row = min(2, int((r - r0) / (r1 + 1 - r0) * 3))
            return 1 + row * 4 + col

        pieces = {}
        for q, r, ch in cells:
            pieces.setdefault(group(q, r), []).append((q, r, ch))
        groups = {k: dict(bend=(0.0 if k == 0 else rng.uniform(-0.15, 0.15)), tl=T_ + self.LAND +
                          (0.0 if k == 0 else rng.uniform(-0.035, 0.035))) for k in range(13)}
        parts = []
        for k, cs in pieces.items():
            pq0, pq1 = min(c_[0] for c_ in cs), max(c_[0] for c_ in cs)
            pr0, pr1 = min(c_[1] for c_ in cs), max(c_[1] for c_ in cs)
            x0, y0, x1, y1 = targets[k]
            for q, r, ch in cs:
                u, v = (q - pq0) / max(1, pq1 - pq0), (r - pr0) / max(1, pr1 - pr0)
                dst = (x0 + u * (x1 - x0), y0 + v * (y1 - y0))
                tl = groups[k]["tl"] + rng.uniform(-0.01, 0.01)
                parts.append(dict(q=q, r=r, ch=ch, src=X.cell_xy(q, r), dst=dst, k=k, td=tl - self.FLY, tl=tl,
                                  rect=targets[k], bend=groups[k]["bend"]))
        land = {}
        for p in parts:
            land.setdefault(p["k"], []).append(p["tl"])
        self._plan = dict(parts=parts, targets=targets, td={(p["q"], p["r"]): p["td"] for p in parts},
                          land={k: sum(v) / len(v) for k, v in land.items()})
        return self._plan

    def render(self, t, n):
        P = self.plan()
        T_ = self.T
        td = P["td"]
        lift = clamp((t - (T_ - self.pre)) / 0.12)
        oc, octx = self.old(t, n, burst=lambda q, r: t >= td.get((q, r), 1e9), lift=lift)
        nc, nctx = self.new(t, n)
        targets, land = P["targets"], P["land"]

        def delay(cx, cy):
            for k in range(1, 13):
                x0, y0, x1, y1 = targets[k]
                tx, ty = X.tile_origin(k - 1)
                if tx <= cx < tx + X.TILE_W and ty <= cy < ty + X.TILE_H:
                    return land[k] - 0.04 + 0.1 * clamp((cy - ty) / X.TILE_H)
            if cx < 404:
                return land[0] - 0.05
            return T_ - 0.12 + math.hypot(cx - 588, cy - 330) / 1600.0

        content = reveal_c(oc, nc, t, delay, region=(20, 36, 1164, 612), dur=0.08, seed=79)
        over = blank()
        d = ImageDraw.Draw(over)
        f = tk.font(*X.GF)
        for p in P["parts"]:
            if t < p["td"] or t >= p["tl"] + 0.1:
                continue
            u = clamp((t - p["td"]) / self.FLY)
            e = ease_io(u)
            x, y = bezier(p["src"], p["dst"], p["bend"], e)
            x0, y0, x1, y1 = p["rect"]
            inside = clamp((e - 0.72) / 0.28)
            col = mixc(mixc(tk.red(1.0), (255, 205, 195), 0.3 * (1 - e)), DS_BLUE, inside)
            a = 1.0 if t < p["tl"] else 1 - (t - p["tl"]) / 0.1
            d.text((x - 3, y - 7), p["ch"], font=f, fill=rgba(col, a))
        hl = land[0]
        her_alpha = clamp((t - (hl - 0.1)) / 0.16)
        glow = max(0.0, 1 - abs(t - hl) / 0.22) * 0.8
        return Frame(content, self.pick(t, octx, nctx), over, glow=glow, her_shift=0.0, her_alpha=her_alpha)


# ================================================================ cut 80: #0000 flies into her, red spreads

class C80(Cut):
    """execute_all -> red_then_i_can. CARRY: the crossed sample #0000 lights up, lifts out of the grid and flies
    on an arc into her, growing onto her upper body; it lands on 'Then I can' (the cut). She re-renders as the red
    input from the top down, and the red spreads out of her pane over the UI: the other samples give way from the
    point where the dispatch rays leave her pane, and the kernel, receptive field and feature maps decode in."""
    pre, post = 0.5, 0.62  # the red front reaches the far corner of the pane at T + 0.57

    def render(self, t, n):
        T_ = self.T
        t_lift, t_go, t_land = T_ - 0.5, T_ - 0.4, T_
        oc, octx = self.old(t, n, gone0=t >= t_go)
        nc, nctx = self.new(t, n)
        content = reveal_c(oc, nc, t, radial((384, 330), T_ + 0.02, 1500.0), region=PANE, seed=80)
        over = blank()
        sp = X.sample0_sprite()
        tx, ty = X.tile_origin(0)
        home = (tx + sp.width / 2, ty + sp.height / 2)
        bx0, by0, bx1, by1 = her_bbox(T_ + 0.4)
        bw = bx1 - bx0
        scale_to = min(bw * 0.95 / sp.width, (by1 - by0) * 0.5 / sp.height)
        dst = ((bx0 + bx1) / 2, by0 + sp.height * scale_to / 2)
        if t < t_go:
            k = clamp((t - t_lift) / 0.1)
            place(over, haloed(brighten(sp, 0.25 * k), 0.8 * k), home)
        elif t < t_land + 0.3:
            u = ease_io((t - t_go) / (t_land - t_go))
            pos = bezier(home, dst, 0.3, u)
            sc = lerp(1.0, scale_to, u)
            s2 = brighten(sp, 0.55 * clamp((u - 0.55) / 0.45), to=tk.RED)
            a = 1.0 if t < t_land else 1 - ease_in((t - t_land) / 0.3)
            if t < t_land:
                s2 = haloed(s2, 0.6)
            place(over, s2, pos, sc, a)
        glow = max(0.0, 1 - abs(t - t_land) / 0.2) * 0.7
        return Frame(content, self.pick(t, octx, nctx), over, glow=glow)


# ================================================================ cut 81: the scan ends; execution takes it all

class C81(Cut):
    """red_then_i_can -> only_execution. UNFOLD: the conv readout lights up and flies to the 'execution' logit,
    where it keeps counting up to 1.000; the logits panel opens from that value outward (red conv panels give way
    to it). In her pane the receptive-field square leaves her tail and stretches across her eyes into the EXECUTE
    bar while she re-renders from red back to her blue, top down, as the scan has finished."""
    pre, post = 0.3, 0.8
    LAND = 0.23       # beat 363.5
    GROW_EARLY = 0.05

    def readout(self):
        a = self.a
        t_go = self.T - 0.1
        return X.conv_state(t_go, t_go - a.start, a.end - a.start)["y"]

    def render(self, t, n):
        T_ = self.T
        t_lift, t_go, t_land = T_ - 0.3, T_ - 0.1, T_ + self.LAND
        y0 = self.readout()
        oc, octx = self.old(t, n, readout=t < t_go)
        nc, nctx = self.new(t, n, value=t >= t_land + 0.04)
        content = reveal_c(oc, nc, t, radial((1062, 124), t_land - 0.14, 1300.0), region=PANE, seed=81)
        over = blank()
        # the readout becomes the logit value
        f_b = tk.F_MONO_B
        src_c = sprite_center(X.readout_text(y0), f_b, 22, X.READOUT_XY)
        num = f"{y0:.3f}"
        num_src = sprite_center(num, f_b, 22, (X.READOUT_XY[0] + tk.font(f_b, 22).getlength("  = "),
                                               X.READOUT_XY[1]))
        dst_c = sprite_center(num, tk.F_MONO, 20, X.VALUE_XY)
        if t < t_go:
            k = clamp((t - t_lift) / 0.1)
            text_c(over, X.readout_text(y0), f_b, 22, tk.red(1.0), src_c, halo=0.8 * k, lift=0.3 * k,
                   halo_color=tk.RED)
        elif t < t_land + 0.05:
            u = ease_io((t - t_go) / (t_land - t_go))
            pos = bezier(num_src, dst_c, -0.25, u)
            sc = lerp(1.0, 20 / 22, u) * (1 + 0.25 * math.sin(math.pi * u))
            text_c(over, num, f_b, 22, tk.red(1.0), pos, sc, halo=0.6 * (1 - u), halo_color=tk.RED)
        # the receptive field becomes the eye bar
        if T_ - self.GROW_EARLY <= t < t_land:
            u = ease_io((t - (T_ - self.GROW_EARLY)) / (t_land - T_ + self.GROW_EARLY))
            kb, _ = kernel_box(T_ - self.GROW_EARLY)
            er = eye_rect(t)
            r = lerp(kb, er, u)
            fill = clamp((u - 0.3) / 0.5)
            glow = blank()
            ImageDraw.Draw(glow).rectangle([r[0] - 2, r[1] - 2, r[2] + 2, r[3] + 2], fill=rgba(tk.RED, 0.5 * u))
            over.alpha_composite(glow.filter(ImageFilter.GaussianBlur(4)))
            dl = ImageDraw.Draw(over)
            if fill > 0.01:
                dl.rectangle(r, fill=rgba(tk.red(1.0), fill))
            dl.rectangle(r, outline=rgba(mixc((255, 226, 214), tk.red(1.0), u)), width=2)
        return Frame(content, self.pick(t, octx, nctx), over)


# ================================================================ cut 82: one 'execution' is pinned

class C82(Cut):
    """only_execution -> have_you_back. RETAIN: the winning 'execution' lights up in its row, leaves it and
    travels once, below the bars, to its pinned slot bottom right, where it locks in (with a small overshoot) on
    'If I can have ...' (169.61) and stays through run_again and red_trapped. The logits give way from the
    row it left; she re-renders shy and the eye bar retracts."""
    pre, post = 0.32, 0.6  # the logits have given way everywhere by T + 0.55
    GO, LAND = -0.24, 0.07

    def render(self, t, n):
        T_ = self.T
        t_lift, t_go, t_land = T_ - self.pre, T_ + self.GO, T_ + self.LAND
        oc, octx = self.old(t, n, exec_word=t < t_go)
        nc, nctx = self.new(t, n, chip=t >= t_land + 0.1)
        content = reveal_c(oc, nc, t, radial((470, 124), T_ - 0.06, 1400.0), region=PANE, seed=82)
        over = blank()
        word = "execution"
        src = sprite_center(word, tk.F_MONO_B, 22, X.WORD_XY)
        dst = sprite_center(word, tk.F_MONO_B, 16, X.chip_text_xy())
        end_scale = 16 / 22
        if t < t_go:
            k = clamp((t - t_lift) / 0.08)
            text_c(over, word, tk.F_MONO_B, 22, tk.red(1.0), src, halo=0.9 * k, lift=0.3 * k, halo_color=tk.RED)
        elif t < t_land + 0.12:
            u = clamp((t - t_go) / (t_land - t_go))
            e = ease_back(u, 1.1) if u < 1 else 1.0
            pos = quad(src, (src[0] - 30, 560), dst, min(1.0, ease_io(u)))
            if u >= 1:
                pos = dst
            sc = lerp(1.15, end_scale, clamp(e))
            text_c(over, word, tk.F_MONO_B, 22, tk.red(1.0), pos, sc, halo=0.6 * (1 - clamp(u)), halo_color=tk.RED)
            if u >= 1:
                k = clamp((t - t_land) / 0.1)
                layer = blank()
                x0, y0, x1, y1 = X.CHIP
                ImageDraw.Draw(layer).rectangle(X.CHIP, outline=rgba(tk.red(0.9), k), width=2)
                over.alpha_composite(layer)
        return Frame(content, self.pick(t, octx, nctx), over)


# ================================================================ cut 83: 'you: not found' becomes the tool call

class C83(Cut):
    """have_you_back -> run_again. CARRY: 'you: not found', decoded in full 0.4 s before the cut, lights up and
    rises on 'I will run ...' (171.77) to the top of the pane, where it stays as the first line of the
    tool call; the checkpoint list gives way where the line passes, and the tool call types in under it. She turns
    angry again and the eye bar draws back across her eyes."""
    pre, post = 0.26, 0.5
    GO, LAND = -0.08, 0.34

    def render(self, t, n):
        T_ = self.T
        t_lift, t_go, t_land = T_ - self.pre, T_ + self.GO, T_ + self.LAND
        oc, octx = self.old(t, n, not_found=False)
        nc, nctx = self.new(t, n, not_found=t >= t_land)
        y_from, y_to = X.NOT_FOUND_XY[1], X.RUN_NOT_FOUND_XY[1]

        def delay(cx, cy):
            return t_go + abs(cy - (y_from + 40)) / 800.0

        content = reveal_c(oc, nc, t, delay, region=PANE, seed=83)
        over = blank()
        u = ease_out((t - t_go) / (t_land - t_go)) if t >= t_go else 0.0
        y = lerp(y_from, y_to, u)
        k = clamp((t - t_lift) / 0.1) * (1 - clamp((t - t_land) / 0.1))
        if t < t_land:
            text_at(over, X.NOT_FOUND, tk.F_HEAD, 44, tk.red(1.0), (430, y), 1.0, 1.0, halo=0.7 * k, lift=0.25 * k)
        return Frame(content, self.pick(t, octx, nctx), over)


# ================================================================ cut 84: the cache pins what is left of you

class C84(Cut):
    """run_again -> red_trapped. CARRY + SCAN: the kv cache is allocated from the top, one row per frame, over the
    tool call. 'reason="have_you_back"' leaves the tool call as glyphs (no background) on 'Though we are trapped'
    and lands on the baseline of the 'pinned: you' label on the half beat (173.47), which types out of it. The
    EXECUTE banner breaks into six pieces that drop into the cache as its six pinned blocks, each as the fill
    reaches its row, turning from red to her blue. She re-renders frightened; the eye bar retracts."""
    pre, post = 0.22, 1.2
    GO, LAND = 0.1, 0.46
    FILL = 456.0  # px per second: one 19 px cache row per frame

    def row_time(self, y):
        return self.T + max(0.0, y - X.KV["oy"]) / self.FILL

    def blocks(self):
        if not hasattr(self, "_blocks"):
            sp = X.run_banner()
            bx, by = X.run_banner_xy()
            order = sorted(X.PINNED, key=lambda qr: X.kv_cell(*qr)[0])
            out = []
            for j, (q, r) in enumerate(order):
                a, b = round(j * sp.width / 6), round((j + 1) * sp.width / 6)
                piece = sp.crop((a, 0, b, sp.height))
                cx, cy = X.kv_cell(q, r)
                land = max(self.T + 0.2, self.row_time(cy) + 0.02)
                out.append(dict(piece=piece, home=(bx + (a + b) / 2, by + sp.height / 2),
                                dst=(cx + X.KV["cw"] / 2 - 1, cy + X.KV["ch"] / 2 - 1), cell=(q, r), land=land,
                                go=land - 0.34))
            self._blocks = out
        return self._blocks

    def render(self, t, n):
        T_ = self.T
        t_lift, t_go, t_land = T_ - self.pre, T_ + self.GO, T_ + self.LAND
        t_break = T_ - 0.12
        blocks = self.blocks()
        pinned = {b["cell"] for b in blocks if t >= b["land"]}
        oc, octx = self.old(t, n, reason=t < t_go, banner=t < t_break)
        label = False if t < t_land else (t - t_land, X.REASON)
        nc, nctx = self.new(t, n, pinned=pinned, label=label)

        lx, ly = X.LABEL_XY

        def delay(cx, cy):
            if ly - 4 <= cy < ly + 22 and lx - 4 <= cx < lx + 260:
                return t_land - 0.03  # the label's line opens where the carried reason lands
            return self.row_time(cy)

        content = reveal_c(oc, nc, t, delay, region=PANE, seed=84, dur=0.05)
        over = blank()
        # the reason, as glyphs
        rxy = X.reason_xy()
        src = sprite_center(X.REASON, tk.F_MONO_B, 20, rxy)
        dst = sprite_center(X.REASON, tk.F_MONO_B, 16, X.LABEL_XY)
        if t < t_go:
            k = clamp((t - t_lift) / 0.1)
            text_c(over, X.REASON, tk.F_MONO_B, 20, tk.red(0.95), src, halo=0.8 * k, lift=0.3 * k, halo_color=tk.RED)
        elif t < t_land:
            u = ease_io((t - t_go) / (t_land - t_go))
            pos = bezier(src, dst, -0.18, u)
            text_c(over, X.REASON, tk.F_MONO_B, 20, tk.red(1.0), pos, lerp(1.2, 0.8, u) if u > 0.5 else
                   lerp(1.0, 1.2, u * 2), halo=0.5 * (1 - u), halo_color=tk.RED)
        # EXECUTE breaks into six pieces that become the pinned blocks
        if t >= t_break:
            for b in blocks:
                if t >= b["land"] + 0.12:
                    continue
                piece = b["piece"]
                if t < b["go"]:
                    k = clamp((t - t_break) / 0.12)
                    jitter = 3 * k * math.sin(t * 60 + b["home"][0])
                    place(over, brighten(piece, 0.2 * k), (b["home"][0] + jitter, b["home"][1]))
                elif t < b["land"]:
                    u = ease_in((t - b["go"]) / (b["land"] - b["go"]))
                    pos = bezier(b["home"], b["dst"], 0.2, u)
                    sc = lerp(1.0, 11 / piece.width, u)
                    col = brighten(piece, clamp((u - 0.5) / 0.5), to=tk.blue(1.0))
                    place(over, col, pos, sc)
                else:  # locked in: flash its cell until the fill has reached it
                    k = 1 - clamp((t - b["land"]) / 0.12)
                    cx, cy = X.kv_cell(*b["cell"])
                    dl = ImageDraw.Draw(over)
                    dl.rectangle([cx - 2, cy - 2, cx + X.KV["cw"], cy + X.KV["ch"]],
                                 outline=rgba((220, 230, 255), k), width=2)
        return Frame(content, self.pick(t, octx, nctx), over)


# ================================================================ shot 85: the whole frame switches off

def trapped_frame(t, n):
    """red_trapped as the frame loop would draw it at time t (it keeps running): content, her, walls, chrome."""
    s = ALL[TRAPPED]
    canvas, ctx = C.body(s, t, n)
    img = canvas.convert("RGBA")
    img.alpha_composite(kit.her_layer(t, _v2().call_of(s)))
    img.alpha_composite(walls_overlay(t, n))
    img = kit.chrome(img, t, ctx)
    return engine.post(img.convert("RGB"), None)


def collapse_frame(t, n):
    """We are trapped, ah: the CRT switches off on the whole current frame. From the cut the picture (chrome,
    lyric band, her, the pinned chip) squashes toward the middle line, slowly at first so the sung line stays
    readable, then fast; it is one line on beat 381, the line shrinks to a dot by beat 382, and the dot stays."""
    if t >= X.LINE_T:
        canvas, _ = C.body(ALL[COLLAPSE], t, n)
        return engine.post(canvas, None)
    base = trapped_frame(t, n)
    hh = X.collapse_height(t)
    k = 1 - hh / H
    sq = base.resize((W, max(1, round(hh))), Image.BOX if hh < H / 2 else Image.BILINEAR)
    gain = 1 + 1.8 * k * k
    if gain > 1.01:
        sq = sq.point(lambda v: min(255, int(v * gain)))
    out = Image.new("RGB", (W, H), tk.BG)
    y0 = round(H / 2 - hh / 2)
    out.paste(sq, (0, y0))
    edge = Image.new("RGB", (W, H), (0, 0, 0))
    de = ImageDraw.Draw(edge)
    col = tk.red(0.55 + 0.45 * k)
    de.line([0, y0, W, y0], fill=col, width=2)
    de.line([0, y0 + sq.height, W, y0 + sq.height], fill=col, width=2)
    out = ImageChops.add(out, edge.filter(ImageFilter.GaussianBlur(3)))
    out = ImageChops.add(out, edge)
    return out


# ================================================================ registration

STUB = [sec_final]
REPLACE = {f.__name__: f for f in (X.shot_exec_hit, X.shot_count, X.shot_red_if_i_can, X.shot_execute_all,
                                   X.shot_red_then_i_can, X.shot_only_execution, X.shot_have_you_back,
                                   X.shot_run_again, X.shot_red_trapped, X.shot_collapse)}
SPLIT = {"shot_execute_all", "shot_red_then_i_can", "shot_only_execution", "shot_have_you_back", "shot_run_again",
         "shot_red_trapped"}
FULL_ART = {"shot_red_if_i_can"}
HIDE_HER = {"shot_exec_hit", "shot_collapse"}
OWN = {i: hit_frame for i in HITS if i != LAST_HIT}
OWN[COUNT] = count_frame
OWN[LAST_HIT] = last_hit_frame
OWN[COLLAPSE] = collapse_frame
OVERLAY = {EXEC_ALL: eye_overlay, RED_THEN: kernel_overlay, ONLY: eye_overlay, BACK: eye_overlay, RUN: eye_overlay,
           TRAPPED: walls_overlay}
CUTS = {78: C78, 79: C79, 80: C80, 81: C81, 82: C82, 83: C83, 84: C84}


def _fix_lyrics():
    """The LRC has 'Trios' for 'trois' (the count's own chip says trois)."""
    for k, (a, b, s) in enumerate(engine.LYRICS):
        if s.startswith("Trios"):
            engine.LYRICS[k] = (a, b, "Trois" + s[5:])


def setup(v1):
    _fix_lyrics()
    # the conv readout that flew in is where 'execution' starts counting from
    s80, s81 = ALL[RED_THEN], ALL[ONLY]
    t_go = s81.start - 0.1
    y0 = X.conv_state(t_go, t_go - s80.start, s80.end - s80.start)["y"]
    C.SHOT_HOOKS.setdefault("shot_only_execution", {}).update(p0=y0, count_t0=C81.LAND)
