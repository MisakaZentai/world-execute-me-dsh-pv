"""Dance-era leftovers around the dsh window (loaded first by dsh_her.install, before the group patches).

Everything here is patched in memory and is active only while the frame being drawn is inside COVER
(D.inside(D.CUR[0])); outside it every wrapped function falls through to what it wrapped. Every wrap is guarded by
an attribute, so install() may run more than once per process.

  P1  kit.her_glow         no halo / bloom around the window (the lone cursor GONE..BACK keeps its glow)
  P2  titles               tuikit.box and tuikit.decode, also where they were imported by name: /dev/me -> dsh web
                           (the grad-cam panel keeps its suffix), and 'input: /dev/me' -> 'input: dsh web'
  1   happy (66.2-68.5)    the grad-cam close-up is the window itself: halfblock(.., "face") -> the window image, the
                           satisfaction -> happy hand-off grows the window out of its pane (no stretch), and cut 31
                           shrinks it back exactly onto the pane window
  2   SFT (47.4-51.2)      no eye bar on the window
  3   cut 13 (30.5-31.6)   the points land in her avatar square, not all over the window
  4   cut 17, tangent      the rider is her avatar, launched from the avatar
  5   cut 26 (58.2-59.4)   no pitch scan line, the fading pane is only its frame, the rows lift less
  6   cut 24 (53.9-54.8)   no lit re-render line, no glyph sweep over the window (it simply is the new one)
  7   cut 3 (5.7-6.6)      the window grows from the seed without the lit ring
  8   cut 38 (80.4-81.3)   the lycopene nodes land on the avatar's outline
  9   sprite sources       every picture of her in the visualisations (point cloud, IF I CAN field, sampling grid,
                           #0000, feature maps, ViT patches, glyph figures) is made from her current avatar in the
                           dsh page (the window image when the page shows no avatar)
"""
from __future__ import annotations

import hashlib
import math
import random
import sys
from functools import lru_cache

from PIL import Image, ImageChops, ImageDraw, ImageOps

D = None                      # dsh_her, set by install
# The author (2026-09-28): the dance stays. The right side's pictures of her (the grad-cam face, the rider, the point
# cloud, the IF I CAN portrait, the samples, the conv maps, the ViT input: everything drawn from her dancer sprites)
# are the approved visuals; only the leftovers ON and AROUND the dsh window go. KEEP_DANCE switches off the parts of
# items 1, 3, 4 and 9 that replaced those pictures with the window or the avatar.
KEEP_DANCE = True
PAGE = (354, 537)             # a dsh frame
CHAT = ((4, 2, 80, 78), 62)   # where .pv-pet sits in a chat page (search box, size incl. its border)
WELCOME = ((120, 120, 234, 234), 74)  # the larger avatar of the welcome page
H3_BOXES = {"full": (0, 60, 420, 540), "upper": (0, 70, 420, 350), "bust": (40, 70, 390, 310),
            "face": (80, 80, 335, 250)}
HAPPY_MAX = (650, 520)        # halfblock(expr, "face", 650, 520, 5) in shot_happy
GRID = (70, 45)               # her rig grid (cells of 5 x 10 px)
RAMP = ".-=+*#%@"             # density glyphs for the avatar grid (':' would stream the lyric through it)


# ---------------------------------------------------------------- time and place

def cover() -> bool:
    return D.inside(D.CUR[0])


def clock() -> float:
    """The time a sprite is drawn for: h3's song clock (set around every frame and every scene body), else CUR."""
    import h3_full
    t = h3_full.CLOCK.get()
    return D.CUR[0] if t is None else t


def win_rect():
    import kit
    x0, y0, x1, y1 = kit.LEFT
    i = D.INNER
    return x0 + i[0], y0 + i[1], x1 - i[2], y1 - i[3]


# ---------------------------------------------------------------- her avatar in the dsh page

@lru_cache(64)
def _page(n: int) -> Image.Image:
    return D.dsh_frame(n / D.FPS)


def _locate(page: Image.Image):
    """(kind, page box) of her avatar in a dsh page: the chat header's .pv-pet or the welcome page's; else None."""
    bg = page.getpixel((2, 2))
    diff = ImageChops.difference(page, Image.new("RGB", page.size, bg)).convert("L").point(
        lambda v: 255 if v > 14 else 0)
    for kind, (search, size) in (("chat", CHAT), ("welcome", WELCOME)):
        bb = diff.crop(search).getbbox()
        if not bb:
            continue
        box = (bb[0] + search[0], bb[1] + search[1], bb[2] + search[0], bb[3] + search[1])
        if abs(box[2] - box[0] - size) <= 4 and abs(box[3] - box[1] - size) <= 4:
            return kind, box
    return None, None


def _rounded(im: Image.Image, r: float) -> Image.Image:
    out = im.convert("RGBA")
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=round(r), fill=255)
    out.putalpha(m)
    return out


@lru_cache(48)
def asset(n: int) -> dict:
    """Her picture in dsh frame n: the avatar (rounded RGBA) with its page box, or the window image."""
    page = _page(n)
    kind, box = _locate(page)
    if kind:
        im = _rounded(page.crop(box), 0.14 * (box[2] - box[0]))
        sig = ("avatar", hashlib.md5(im.tobytes()).hexdigest())
    else:
        im = page.convert("RGBA")
        sig = ("window", n)
    return dict(kind=kind, box=box, img=im, sig=sig)


def asset_at(t: float) -> dict:
    return asset(round(t * D.FPS))


def avatar_screen_box(t: float):
    """Her avatar on screen at time t (the window's origin + its page box), or a box round AVATAR_C."""
    a = asset_at(t)
    if a["kind"]:
        x0, y0 = win_rect()[:2]
        b = a["box"]
        return x0 + b[0], y0 + b[1], x0 + b[2], y0 + b[3]
    cx, cy = D.AVATAR_C
    return cx - 31, cy - 31, cx + 31, cy + 31


def fit(im: Image.Image, w: int, h: int) -> Image.Image:
    """im scaled to fit w x h (aspect kept), centred on a transparent canvas."""
    s = min(w / im.width, h / im.height)
    sp = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.Resampling.LANCZOS)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.alpha_composite(sp.convert("RGBA"), ((w - sp.width) // 2, (h - sp.height) // 2))
    return out


_FRAMES: dict = {}


def grid_frame(t: float):
    """Her picture as a rig Frame (70 x 45 cells): density glyphs and shades from its luminance, no lyric cells."""
    import rig
    a = asset_at(t)
    if a["sig"] in _FRAMES:
        return _FRAMES[a["sig"]]
    cw, ch = 5, 10
    im = a["img"]
    s = min(GRID[0] * cw / im.width, GRID[1] * ch / im.height)
    if a["kind"]:
        s *= 0.86
    cols, rows = max(1, round(im.width * s / cw)), max(1, round(im.height * s / ch))
    small = im.resize((cols, rows), Image.Resampling.BOX)
    L, A = small.convert("L").load(), small.getchannel("A").load()
    c0, r0 = (GRID[0] - cols) // 2, (GRID[1] - rows) // 2
    art = [[" "] * GRID[0] for _ in range(GRID[1])]
    shade = [[" "] * GRID[0] for _ in range(GRID[1])]
    part = [[" "] * GRID[0] for _ in range(GRID[1])]
    for r in range(rows):
        for c in range(cols):
            if A[c, r] < 110:
                continue
            v = L[c, r] / 255
            art[r0 + r][c0 + c] = RAMP[min(len(RAMP) - 1, int(v * len(RAMP)))]
            shade[r0 + r][c0 + c] = str(1 + min(6, int(v * 7)))
            part[r0 + r][c0 + c] = "b"
    fr = rig.Frame(["".join(x) for x in art], ["".join(x) for x in shade], ["".join(x) for x in part])
    if len(_FRAMES) > 64:
        _FRAMES.clear()
    _FRAMES[a["sig"]] = fr
    return fr


class _Grids:
    """Stands in for an H3 take inside COVER: the same length (so the take's timing is unchanged), and every
    frame is her current picture."""

    def __init__(self, real):
        self.n = len(real)

    def __len__(self):
        return self.n

    def __getitem__(self, i):
        return grid_frame(clock())


# ---------------------------------------------------------------- the happy close-up (item 1)

def happy_geom():
    """Where shot_happy draws the window instead of her face: (w, h, x, y) of the sprite."""
    s = min(HAPPY_MAX[0] / PAGE[0], HAPPY_MAX[1] / PAGE[1])
    w, h = round(PAGE[0] * s), round(PAGE[1] * s)
    return w, h, 24 + (676 - w) // 2, 70


def face_src():
    """Source rect of the satisfaction -> happy hand-off: the region of the old frame that, grown into the happy
    panel (24, 56, 700, 604), puts the pane window exactly onto the window in the panel (no stretch)."""
    if not cover():
        return 116, 92, 268, 226
    w, _, sx, sy = happy_geom()
    x0, y0, x1, _ = win_rect()
    s = (x1 - x0) / w
    ox, oy = x0 - (sx - 24) * s, y0 - (sy - 56) * s
    return round(ox), round(oy), round(ox + 676 * s), round(oy + 548 * s)


# ---------------------------------------------------------------- titles (P2)

def fix_title(t, s):
    if not (isinstance(s, str) and s.startswith("/dev/me")):
        return s
    rest = s[len("/dev/me"):].strip()
    if "grad-cam" in rest:
        return "dsh web  " + rest
    return D.pane_title(t, s)


def _boxer(orig):
    def box(d, *args, **kw):
        if cover():
            if len(args) > 4:
                args = args[:4] + (fix_title(D.CUR[0], args[4]),) + args[5:]
            elif "title" in kw:
                kw = dict(kw, title=fix_title(D.CUR[0], kw["title"]))
        return orig(d, *args, **kw)
    box._dsh_fix = True
    box._dsh_orig = orig
    return box


def _decoder(orig):
    def decode(s, *args, **kw):
        if cover() and isinstance(s, str):
            if s.startswith("/dev/me"):
                s = fix_title(D.CUR[0], s)
            elif "input: /dev/me" in s:
                s = s.replace("input: /dev/me", "input: dsh web")
        return orig(s, *args, **kw)
    decode._dsh_fix = True
    decode._dsh_orig = orig
    return decode


# ---------------------------------------------------------------- install

def _patch(fn, pairs, **names):
    """kit.patch_code once per function object, with the helper names it needs put in its globals."""
    import kit
    if getattr(fn, "_dsh_fix", False):
        return
    fn.__globals__.update(names)
    kit.patch_code(fn, pairs)
    fn._dsh_fix = True


def install(D_, v2):
    global D
    D = D_
    import engine
    import h3_full
    import kit
    import scenes
    import s_boot
    import s_chorus1
    import s_deploy as SD
    import scenes_chorus1 as SC
    import sec_chorus1
    import sec_verse1
    import tuikit as tk
    import cuts as C

    spaces = None

    def ns():
        nonlocal spaces
        if spaces is None:
            spaces = h3_full.namespaces()
        return spaces

    # P1: no halo or bloom around the window
    if not getattr(kit.her_glow, "_dsh_fix", False):
        og = kit.her_glow

        def her_glow(layer, k):
            if cover() and not D.GONE <= D.CUR[0] < D.BACK:
                return layer
            return og(layer, k)
        her_glow._dsh_fix = True
        kit.her_glow = her_glow

    # P2: pane titles wherever box / decode were imported by name, and through the module attributes
    eb = engine.__dict__.get("box")
    if eb is not None and not getattr(eb, "_dsh_fix", False):
        h3_full.replace_alias(eb, _boxer(eb), ns())
    if not getattr(tk.box, "_dsh_fix", False):
        tk.box = _boxer(tk.box)
    ed = tk.__dict__.get("decode")
    if ed is not None and not getattr(ed, "_dsh_fix", False):
        h3_full.replace_alias(ed, _decoder(ed), ns())   # tuikit's own name included
    if not getattr(tk.decode, "_dsh_fix", False):
        tk.decode = _decoder(tk.decode)

    # 1. happy: the grad-cam close-up is the window
    def face_halfblock(orig):
        def halfblock(expr, crop, max_w, max_h, *args, **kw):
            if cover() and crop == "face":
                w, h, _, _ = happy_geom()
                return D.dsh_frame(clock()).resize((w, h), Image.Resampling.LANCZOS).convert("RGBA")
            return orig(expr, crop, max_w, max_h, *args, **kw)
        halfblock._dsh_fix = True
        return halfblock

    if not KEEP_DANCE:   # the close-up stays her dancer's face; its hand-off grows from the window's avatar corner
        for g in (sec_chorus1.__dict__, SC.__dict__):
            if "halfblock" in g and not getattr(g["halfblock"], "_dsh_fix", False):
                g["halfblock"] = face_halfblock(g["halfblock"])
        A = kit.v1.approved
        _patch(A.render_frame, [("(116,92,268,226)", "DSH_FACE_SRC()")], DSH_FACE_SRC=face_src)
        _patch(s_chorus1.approved_pre, [("(116, 92, 268, 226)", "DSH_FACE_SRC()")], DSH_FACE_SRC=face_src)
    if not getattr(s_chorus1.C31.head, "_dsh_fix", False):
        o_head = s_chorus1.C31.head

        def head(self):
            if not cover():
                return o_head(self)
            w, _, sx, sy = happy_geom()
            x0, y0, x1, y1 = win_rect()
            sc = (x1 - x0) / w
            hx0, hy0 = x0 - (sx - 42) * sc, y0 - (sy - 70) * sc
            return (hx0, hy0, hx0 + 640 * sc, hy0 + 510 * sc), ((x0 + x1) / 2, (y0 + y1) / 2)
        head._dsh_fix = True
        s_chorus1.C31.head = head

    # 2. SFT: no eye bar on the window
    for name in ("shot_blind", "shot_dizzy", "shot_travel"):
        fn = v2.OVERLAY.get(name)
        if fn is not None and not getattr(fn, "_dsh_fix", False):
            def ov(t, n, fn=fn):
                return None if cover() else fn(t, n)
            ov._dsh_fix = True
            v2.OVERLAY[name] = ov

    # 3. cut 13: the points land in her avatar
    if not getattr(C.C13.targets, "_dsh_fix", False):
        o_targets = C.C13.targets

        def targets(self):
            if not cover():
                return o_targets(self)
            if not hasattr(self, "_dsh_targets"):
                x0, y0, x1, y1 = avatar_screen_box(self.T + 0.4)
                cells = [(x, y) for x in range(round(x0) + 3, round(x1) - 3, 2) for y in range(round(y0) + 3,
                                                                                            round(y1) - 3, 2)]
                random.Random(13).shuffle(cells)
                self._dsh_targets = cells
            return self._dsh_targets
        targets._dsh_fix = True
        C.C13.targets = targets

    # 4. the rider is launched from her avatar (and, without KEEP_DANCE, is the avatar)
    if not KEEP_DANCE and not getattr(scenes.RIDER[0], "_dsh_fix", False):
        o_rider = scenes.RIDER[0]

        def rider(t):
            if not cover():
                return o_rider(t)
            a = asset_at(t)
            return fit(a["img"], 52, 52) if a["kind"] else fit(a["img"], 40, 60)
        rider._dsh_fix = True
        scenes.RIDER[0] = rider

    def rider_src():
        if not cover():
            return 204, 300
        x0, y0, x1, y1 = avatar_screen_box(D.CUR[0])
        return (x0 + x1) / 2, (y0 + y1) / 2
    _patch(C.C17.render, [("src = (204, 300)", "src = DSH_RIDER_SRC()")], DSH_RIDER_SRC=rider_src)

    # 5. cut 26: no scan line, the pane that fades is only its frame, the rows lift less
    if not getattr(s_chorus1.C26.scan_line, "_dsh_fix", False):
        o_scan = s_chorus1.C26.scan_line

        def scan_line(self, layer, t, k):
            if not cover():
                return o_scan(self, layer, t, k)
        scan_line._dsh_fix = True
        s_chorus1.C26.scan_line = scan_line
    if not getattr(s_chorus1.C26.pane_ui, "_dsh_fix", False):
        o_ui = s_chorus1.C26.pane_ui

        def pane_ui(self, t, k):
            if not cover():
                return o_ui(self, t, k)
            layer = kit.blank()
            D.BOX[0](ImageDraw.Draw(layer), *kit.LEFT, "dsh web", 0.45 + 0.35 * engine.pulse(t), spinner=t)
            return tk.scale_alpha(layer, k)
        pane_ui._dsh_fix = True
        s_chorus1.C26.pane_ui = pane_ui
    _patch(s_chorus1.C26.render, [("0.45 * lift", "DSH_LIFT() * lift")],
           DSH_LIFT=lambda: 0.15 if cover() else 0.45)

    # 6. cut 24: no lit re-render line, and the window side is simply the new frame from SIDE0
    def side(self, content, nc, t):
        if t < self.SIDE0:
            return content
        out = content.copy()
        out.paste(nc.crop(self.SIDE), self.SIDE[:2])
        return out
    _patch(s_chorus1.C24.render, [
        ("if 58 < fy < 602:", "if 58 < fy < 602 and not DSH_INSIDE():"),
        ("content = kit.reveal(content, nc, t, kit.sweep((0, self.SIDE[1])",
         "content = DSH_SIDE(self, content, nc, t) if DSH_INSIDE() else kit.reveal(content, nc, t, "
         "kit.sweep((0, self.SIDE[1])"),
    ], DSH_INSIDE=cover, DSH_SIDE=side)

    # 7. cut 3: the window grows from its seed without the lit ring
    _patch(s_boot.C03.grown, [("layer.alpha_composite(front, kit.LEFT[:2])",
                               "(None if DSH_INSIDE() else layer.alpha_composite(front, kit.LEFT[:2]))")],
           DSH_INSIDE=cover)

    # 8. cut 38: the lycopene nodes land on her avatar's outline (where it is when they land)
    if not getattr(SD.ear_targets, "_dsh_fix", False):
        o_ears = SD.ear_targets

        def ear_targets(t):
            if not (cover() and D.DEPLOY[0] <= t < D.DEPLOY[1]):
                return o_ears(t)
            x0, y0, x1, y1 = avatar_screen_box(SD.T38 - 0.04)
            w, h = x1 - x0, y1 - y0
            per = 2 * (w + h)
            pts = []
            for k in range(21):
                p = per * (k + 0.5) / 21
                if p < w:
                    pts.append((x0 + p, y0))
                elif p < w + h:
                    pts.append((x1, y0 + p - w))
                elif p < 2 * w + h:
                    pts.append((x1 - (p - w - h), y1))
                else:
                    pts.append((x0, y1 - (p - 2 * w - h)))
            return sorted(pts, key=lambda q: q[0])
        ear_targets._dsh_fix = True
        SD.ear_targets = ear_targets

    # 9. (off with KEEP_DANCE) every picture of her in the visualisations comes from her avatar
    if KEEP_DANCE:
        return
    if not getattr(h3_full.rgba, "_dsh_fix", False):
        o_rgba = h3_full.rgba

        def rgba(name, i):
            if not cover():
                return o_rgba(name, i)
            out = Image.new("RGBA", (420, 540), (0, 0, 0, 0))
            out.alpha_composite(fit(asset_at(clock())["img"], 170, 170), (125, 80))  # inside every crop box
            return out
        rgba._dsh_fix = True
        h3_full.rgba = rgba
    if not getattr(h3_full.grids, "_dsh_fix", False):
        o_grids = h3_full.grids

        def grids(name):
            real = o_grids(name)
            return _Grids(real) if cover() else real
        grids._dsh_fix = True
        h3_full.grids = grids
    if not getattr(h3_full, "_dsh_fix_sprite", False):
        o_src = h3_full.sprite_src

        def sprite_src(expr, crop):
            if not cover():
                return o_src(expr, crop)
            x0, y0, x1, y1 = H3_BOXES[crop]
            return fit(asset_at(clock())["img"], x1 - x0, y1 - y0)
        h3_full.replace_alias(o_src, sprite_src, ns())
        h3_full._dsh_fix_sprite = True
    if not getattr(h3_full.source_key, "_dsh_fix", False):
        o_key = h3_full.source_key

        def source_key(t):  # the renderer caches (h3_full.dynamic) are keyed by what is drawn
            if cover():
                return ("dsh",) + asset_at(t)["sig"], None
            return o_key(t)
        source_key._dsh_fix = True
        h3_full.source_key = source_key
    if not getattr(sec_verse1.her_points, "_dsh_fix", False):
        o_points = sec_verse1.her_points

        def her_points(n, w, h, seed=3):
            """The point cloud gathers into her avatar: a square (w/h of the target box), denser where it is lit."""
            if not cover():
                return o_points(n, w, h, seed)
            im = asset_at(clock())["img"]
            side = 96
            sp = fit(im, side, side)
            L = ImageOps.autocontrast(sp.convert("L"), cutoff=2).load()
            A = sp.getchannel("A").load()
            fy = w / h
            rnd = random.Random(seed)
            pts, tries = [], 0
            while len(pts) < n and tries < n * 60:
                tries += 1
                x, y = rnd.randrange(side), rnd.randrange(side)
                lv = L[x, y] / 255
                if A[x, y] > 100 and rnd.random() < 0.02 + 0.98 * lv ** 2.2:
                    pts.append((x / side, (1 - fy) / 2 + fy * y / side, lv))
            return pts
        her_points._dsh_fix = True
        sec_verse1.her_points = her_points
        import scenes as S0
        if hasattr(S0, "point_set") and hasattr(S0.point_set, "cache_clear"):
            S0.point_set.cache_clear()
