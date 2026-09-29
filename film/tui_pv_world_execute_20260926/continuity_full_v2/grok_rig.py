"""Her from Grok keyframes: the Grok acting clips as motion source for her own glyph rig (V2_HER=grokrig).

The clips (tui_pv_grok_motion_20260926, read-only) are never shown. Each clip is normalised onto the rig's frame
of reference, reduced to its distinct poses, and each pose is traced into a rig keyframe (art / shade / part, the
layers of full/poses/*.txt). She is drawn from those keyframes by the string dancer's own rig (rig.frame's string
operations) and glyph renderer (dancer.draw), so scale, feet, centre line, glyph style and lyric fill are the
dancer's.

  prepare()                   observe, dedupe and trace every clip in TIMELINE into cache/grok_rig/  (CLI: prepare)
  install()                   route dancer.render through render() (v2.py does this for V2_HER=grokrig)
  render(t, size, base, ...)  her figure at t: the dancer's own when no clip acts, else from the keyframes
  acting(t)                   a gesture draws her, or a join into or out of one runs
  report(), sheet()           grokrig_report.json, grokrig_keyframes.png  (CLI: report, sheet; all = all three)

Offline:
  matte     figure = differs from white by more than 40 (the library's rule; 20 on the legs, whose light
            stockings would lose rows), closed; holes filled from the border unless small and as white as the
            background (the ahoge's loop, gaps between curls); in the 4 px above the foot line only dark or
            saturated pixels stay (the grey contact shadow between the shoes goes); nothing below the feet
  frame 0   every clip starts on the same standing image, mapped like poses/serious.txt: its top (the ahoge) on
            serious's top row, the shoe bottoms on the last row, the body's centre line (head, legs, hem) on
            serious's (centre_shift)
  camera    observe(): per frame the foot line, the shoe centre, her height over the shoes and the frame-to-frame
            change. drift(): the foot line smoothed (a step stays a step), the sideways drift as a cubic, and the
            zoom s = 1 + KAPPA * foot-line creep: Grok zooms about a point near her upper chest, so the zoom grows
            with the creep at the same rate in every clip (fitted on the clips whose pose holds while the camera
            creeps); where the foot line holds still there is no zoom and a changing height is the action (M02's
            lean). Every frame is resampled through the inverse of the fitted camera
  dedupe    a frame is kept when it differs from the last kept one by DUP (thumbnails, camera removed): one frame
            per pose of the ~8 fps clips; the frames in between give the source's own progress between two kept
            poses (a slow drift, a partial blend frame)
  trace     rig._trace per cell (coverage, part vote, shade, _colour_class, _tensor / _line_glyph outlines and
            colour boundaries, the face box of features); parts by rig._classify's model with landmarks read off
            frame 0 (GFIT), the head moved with the face (the largest skin region near it), the tail as navy
            reaching out right of the skirt; a cell that could be two things gets a rigid part (body, skirt);
            the eyes by matching frame 0's eyes near where the face track puts them
Playback (gestures, not clips: TIMELINE puts one action per sung line on the beats, see there):
  tween     between two kept poses the cells that differ flip in order of their distance from the cells both
            share (the body that stays): a hand arrives after its shoulder. The timing follows the source's
            progress, never later than an even spread over the last STEP frames, so a pose repeated 3 times at
            ~8 fps turns into the next one frame by frame
  motion    rig.frame with choreo's Motion: the kick squash, hops, hem, tail and hair at full while she acts
            (the lower body keeps dancing), the lean and head eased back while the action runs (ACT_MOVE); a pose
            that holds shifts its weight, tilts its head and lifts a held arm a row on the beat (ACT_HOLD, LIFE,
            BOB)
  join      between any two sources (gesture, gesture, the dancer): what leaves retracts tip first while what
            arrives grows out of the body, the cells mid-flip lit like the dancer's own pose morph; two beats in
            and out of the dance, one into the verse, half a beat between gestures
"""
from __future__ import annotations

import json
import math
import sys
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent
FULL = ROOT.parent / "full"
for _p in (FULL, ROOT.parent):  # rig, dancer, choreo, motion; tuikit
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import rig  # noqa: E402

GROK = Path(__file__).resolve().parents[2].joinpath("tui_pv_grok_motion_20260926")
CACHE = ROOT / "cache" / "grok_rig"
NFRAMES = 241

# the keyframe grid: rig's rows (FIG_ROWS figure + 2 above), but as wide as her pane, because Grok's tail and
# stretched arms reach past rig's 48 columns
GROWS = rig.KROWS
GCOLS = 70
GAXIS = GCOLS // 2
SX, SY = rig.SX, rig.SY
CUT = 40                    # figure: differs from white by more than this (tui_pv_grok_motion's normalize.py)
CUT_LEGS = 20               # the same between the hem and the shadow strip, where the stockings are light
LEGS = 80                   # source px above the foot line where CUT_LEGS applies (the hem is ~88 px up)
HOLE_WHITE = 8              # a small enclosed hole this white (median difference from white) is background:
HOLE_SMALL = 400            # the ahoge's loop, gaps between curls (half-res px; the apron and face are larger and
                            # shaded, median 11 and up)


# ---------------------------------------------------------------- source frames and the matte

def src(clip: str, f: int) -> Image.Image:
    return Image.open(GROK / clip / "oof_frames" / f"{f:04d}.png").convert("RGB")


def _diff(im: Image.Image) -> Image.Image:
    r, g, b = ImageChops.difference(im, Image.new("RGB", im.size, (255, 255, 255))).split()
    return ImageChops.lighter(ImageChops.lighter(r, g), b)


def feet(im: Image.Image, core: Image.Image | None = None) -> tuple[int, int, int]:
    """(shoe left, shoe right, foot line = one past the lowest shoe pixel): the dark pixels near the bottom."""
    core = core or _diff(im).point(lambda v: 255 if v > CUT else 0)
    bb = core.getbbox()
    y1 = bb[3]
    dark = im.convert("HSV").getchannel("V").point(lambda v: 255 if v < 120 else 0)
    band = ImageChops.multiply(dark.crop((0, y1 - 70, im.width, y1)), core.crop((0, y1 - 70, im.width, y1)))
    fb = band.getbbox() or (bb[0], 0, bb[2], 70)
    # the shoes: lowest 40 px of dark
    low = band.crop((0, fb[3] - 40, im.width, fb[3])).getbbox() or fb
    return low[0], low[2], y1 - 70 + fb[3]


def matte(im: Image.Image, foot: float) -> Image.Image:
    """Figure alpha (L, 0/255) at source resolution: thresholded, closed, holes filled from the border; the grey
    contact shadow at the foot line removed and nothing below the feet."""
    diff = _diff(im)
    core = diff.point(lambda v: 255 if v > CUT else 0)
    # the legs: light stockings differ from white by less than CUT at their edges and a thin leg would lose rows;
    # between the hem and the shadow strip a lower threshold holds them (no shadow reaches that high)
    fy = int(round(foot))
    legs = (0, fy - LEGS, im.width, fy - 4)
    core.paste(diff.crop(legs).point(lambda v: 255 if v > CUT_LEGS else 0), legs[:2])
    closed = core.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5))
    # holes: flood the background from the border at half resolution (gaps under 2 px are closed above)
    size = (im.width // 2, im.height // 2)
    half = closed.resize(size, Image.BOX).point(lambda v: 255 if v > 100 else 0)
    bgm = Image.new("L", (half.width + 2, half.height + 2), 0)
    bgm.paste(half, (1, 1))
    ImageDraw.floodfill(bgm, (0, 0), 128)
    fill = bgm.crop((1, 1, half.width + 1, half.height + 1))
    # an enclosed hole that is as white as the background is background
    fp, dp = fill.load(), diff.resize(size, Image.BOX).load()
    w, h = size
    for y in range(h):
        for x in range(w):
            if fp[x, y] != 0:
                continue
            comp, stack = [], [(x, y)]
            fp[x, y] = 1
            while stack:
                p = stack.pop()
                comp.append(p)
                px, py = p
                for q in ((px + 1, py), (px - 1, py), (px, py + 1), (px, py - 1)):
                    if 0 <= q[0] < w and 0 <= q[1] < h and fp[q] == 0:
                        fp[q] = 1
                        stack.append(q)
            if len(comp) < HOLE_SMALL and sorted(dp[p] for p in comp)[len(comp) // 2] <= HOLE_WHITE:
                for p in comp:
                    fp[p] = 128
    fill = fill.point(lambda v: 0 if v == 128 else 255)
    # the filled silhouette has no inner edges left: shrink its blocky outer edge and let the closed strokes draw it
    fill = fill.resize(im.size, Image.NEAREST).filter(ImageFilter.MinFilter(5))
    alpha = ImageChops.lighter(fill, closed)
    # the contact shadow: at and below the foot line only dark or saturated pixels are figure
    hsv = im.convert("HSV")
    keep = ImageChops.lighter(hsv.getchannel("V").point(lambda v: 255 if v < 130 else 0),
                              hsv.getchannel("S").point(lambda v: 255 if v > 70 else 0))
    band = (0, fy - 4, im.width, fy)
    alpha.paste(ImageChops.multiply(alpha.crop(band), keep.crop(band)), band[:2])
    alpha.paste(0, (0, fy, im.width, im.height))
    return alpha


# ---------------------------------------------------------------- frame 0 and the camera drift

@lru_cache(None)
def _serious_top_row() -> float:
    """The row serious's top (its ahoge) lands on in poses/serious.txt's frame of reference (fractional)."""
    sp = rig._sprite("serious").getchannel("A").point(lambda v: 255 if v > 100 else 0)
    top = sp.getbbox()[1]
    dy = rig.GROUND - rig.FIT["serious"]["foot"]
    return 2 + (top + dy - rig.TOP) / rig.RH


def calibrate(clip: str) -> dict:
    """Frame 0 in source px: top (ahoge), foot line, shoe centre, and the grid it maps to."""
    im = src(clip, 0)
    core = _diff(im).point(lambda v: 255 if v > CUT else 0)
    x0, x1, foot = feet(im, core)
    top = core.getbbox()[1]
    rh = (foot - top) / (GROWS - _serious_top_row())
    return dict(top=top, foot=foot, cx=(x0 + x1) / 2, shoe=(x0, x1), rh=rh, cw=rh / 2,
                gx0=(x0 + x1) / 2 - GAXIS * rh / 2, gy0=foot - GROWS * rh)


def _polyfit(xs: list, ys: list, deg: int = 3) -> list:
    """Least-squares polynomial coefficients (lowest first), x scaled to 0..1, two rounds of outlier rejection."""
    use = list(range(len(xs)))
    coef = [0.0] * (deg + 1)
    for _ in range(3):
        n = deg + 1
        A = [[0.0] * n for _ in range(n)]
        B = [0.0] * n
        for i in use:
            p = [xs[i] ** k for k in range(n)]
            for r in range(n):
                B[r] += p[r] * ys[i]
                for c in range(n):
                    A[r][c] += p[r] * p[c]
        for c in range(n):  # Gauss-Jordan with partial pivoting
            piv = max(range(c, n), key=lambda r: abs(A[r][c]))
            A[c], A[piv], B[c], B[piv] = A[piv], A[c], B[piv], B[c]
            for r in range(n):
                if r != c and A[c][c]:
                    q = A[r][c] / A[c][c]
                    A[r] = [a - q * b for a, b in zip(A[r], A[c])]
                    B[r] -= q * B[c]
        coef = [B[c] / A[c][c] if A[c][c] else 0.0 for c in range(n)]
        res = [ys[i] - sum(cf * xs[i] ** k for k, cf in enumerate(coef)) for i in range(len(xs))]
        sd = math.sqrt(sum(res[i] ** 2 for i in use) / max(1, len(use))) or 1e-9
        use = [i for i in range(len(xs)) if abs(res[i]) <= 2.5 * sd]
    return coef


def _poly(coef: list, x: float) -> float:
    return sum(c * x ** k for k, c in enumerate(coef))


CREEP = 4.0                 # foot-line creep (source px, ~0.3 rows) from which a clip counts as pushing in
COLUMN = 50                 # half-width (source px) of the column over the shoes where her head top is measured
STATIC = 0.9                # raw frame-to-frame difference (grey levels) under which the pose holds still
OBS_VERSION = 2


def observe(clip: str, log=print) -> dict:
    """Per-frame camera observations for the whole clip (cached in cache/grok_rig/<clip>/observe.json).

    dy = foot line - frame 0's (the shoe bottoms: the feet stay on the floor in every clip used), dx = shoe centre
    - frame 0's, h = her height from the shoe bottoms to the top of the column over her shoes (her head; a hand
    held above or beside the head does not count) relative to frame 0's, and motion = the raw frame-to-frame
    difference (where the pose holds still)."""
    path = CACHE / clip / "observe.json"
    if path.exists():
        d = json.loads(path.read_text(encoding="utf-8"))
        if d.get("version") == OBS_VERSION:
            return d
    cal = calibrate(clip)
    obs, prev, h0 = [], None, None
    for f in range(NFRAMES):
        im = src(clip, f)
        core = _diff(im).point(lambda v: 255 if v > CUT else 0)
        x0, x1, foot = feet(im, core)
        cx = (x0 + x1) / 2
        top_c = core.crop((int(cx - COLUMN), 0, int(cx + COLUMN), foot)).getbbox()[1]
        h0 = h0 or foot - top_c
        small = im.convert("L").resize((146, 96), Image.BOX)
        motion = _tdiff(small, prev) if prev is not None else 0.0
        prev = small
        obs.append(dict(f=f, foot=foot, top=core.getbbox()[1], top_c=top_c, cx=cx, dx=cx - cal["cx"],
                        dy=foot - cal["foot"], h=(foot - top_c) / h0, motion=round(motion, 3)))
        if f % 60 == 0:
            log(f"  {clip} observe f{f}: foot={foot} top_c={top_c} h={obs[-1]['h']:.4f}")
    out = dict(version=OBS_VERSION, cal=cal, obs=obs)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out), encoding="utf-8")
    return out


def _still_runs(obs: list, min_len: int = 10) -> list[list[int]]:
    """Runs of frames where the pose holds still: the frame-to-frame difference stays under STATIC within +-3
    frames (an ~8 fps clip changes its pose every third frame)."""
    mv = [o["motion"] for o in obs]
    ok = [max(mv[max(1, f - 3):f + 4]) < STATIC for f in range(len(mv))]
    runs, cur = [], []
    for f, v in enumerate(ok):
        if v:
            cur.append(f)
        else:
            if len(cur) >= min_len:
                runs.append(cur)
            cur = []
    if len(cur) >= min_len:
        runs.append(cur)
    return runs


KAPPA = 0.0023              # zoom per px of foot-line creep: Grok zooms about a point near her upper chest (about
                            # y = 250 px in the source, 435 px above the feet: 1 / 435 = 0.0023), the same in every
                            # clip; fitted on M06, M13 and M20, whose pose holds while the camera creeps (0.00225,
                            # 0.00235, 0.0019)


@lru_cache(None)
def drift(clip: str) -> dict:
    """The fitted camera of a clip: dx as a cubic over the clip (a slow pan; a step she takes stays hers), dy as
    the smoothed foot line (_smooth_series: the feet stay on the bottom row even where the creep comes in a step),
    the scale s = 1 + KAPPA * dy.

    A push-in scales the frame about a fixed point, so the zoom grows in step with the foot-line creep, and a clip
    whose foot line holds still (creep under CREEP) has no zoom (s = 1): a changing height there is the action
    (M02's lean). The zoom per px of creep is the camera's (KAPPA), not the clip's: a clip that zooms while she
    moves (M12 creeps 20 px during the arm fold and nowhere else) cannot tell its zoom from its pose. As a check,
    kappa is also fitted per clip to her height over the stretches where the pose holds still, each stretch with
    its own pose factor (h = A_stretch * (1 + kappa * dy)), and the height residual of KAPPA is reported."""
    ob = observe(clip)
    obs = ob["obs"]
    xs = [o["f"] / (NFRAMES - 1) for o in obs]
    fit = {"dx": _polyfit(xs, [o["dx"] for o in obs]), "dy": _smooth_series([o["dy"] for o in obs])}
    dyf = fit["dy"]
    creep = max(abs(v) for v in dyf)
    push_in = creep >= CREEP
    runs = _still_runs(obs) if push_in else []

    def resid(k):
        err, n = 0.0, 0
        for run in runs:
            q = [obs[f]["h"] / (1 + k * dyf[f]) for f in run]
            a = sum(q) / len(q)
            err += sum((obs[f]["h"] - a * (1 + k * dyf[f])) ** 2 for f in run)
            n += len(run)
        return math.sqrt(err / n)
    kappa_fit = min((j * 0.00005 for j in range(-40, 161)), key=resid) if runs else None
    kappa = KAPPA if push_in else 0.0
    fit["s"] = [1.0 + kappa * v for v in dyf]
    return dict(ob, fit=fit, creep_px=creep, push_in=push_in, kappa=kappa, kappa_fit=kappa_fit,
                still_runs=[[r[0], r[-1]] for r in runs], height_residual=resid(kappa) if runs else None)


def _smooth_series(v: list, med: int = 4, box: int = 6) -> list:
    """A running median (+-med frames: a foot-detection glitch goes) then a running mean (+-box: the 1 px encoder
    wobble goes); a step in the series (M12 creeps 14 px within half a second, during the move) stays a step."""
    n = len(v)
    m = [sorted(v[max(0, i - med):i + med + 1])[len(v[max(0, i - med):i + med + 1]) // 2] for i in range(n)]
    return [sum(m[max(0, i - box):i + box + 1]) / len(m[max(0, i - box):i + box + 1]) for i in range(n)]


def camera(dr: dict, f: float) -> tuple[float, float, float]:
    """(s, dx, dy) at source frame f: dx from its cubic, dy and s from the smoothed series (interpolated)."""
    fit = dr["fit"]
    i = max(0, min(NFRAMES - 2, int(f)))
    u = max(0.0, min(1.0, f - i))
    lerp = lambda a: a[i] + (a[i + 1] - a[i]) * u  # noqa: E731
    return lerp(fit["s"]), _poly(fit["dx"], f / (NFRAMES - 1)), lerp(fit["dy"])


def grid_box(dr: dict, f: float, shift: float | None = None) -> tuple[float, float, float, float]:
    """The source box that frame f's keyframe grid samples: frame 0's grid (moved sideways by the centre-line
    calibration, in cells) moved by the fitted camera."""
    cal = dr["cal"]
    s, dx, dy = camera(dr, f)
    cx, fy = cal["cx"], cal["foot"]
    gx0, gy0 = cal["gx0"] + (centre_shift() if shift is None else shift) * cal["cw"], cal["gy0"]
    gx1, gy1 = gx0 + GCOLS * cal["cw"], fy
    return (cx + dx + s * (gx0 - cx), fy + dy + s * (gy0 - fy), cx + dx + s * (gx1 - cx), fy + dy + s * (gy1 - fy))


CLIP0 = "M03_present"       # any clip: every frame 0 is the same start image


@lru_cache(None)
def centre_shift() -> float:
    """Columns to move the grid so that frame 0's centre line is serious's: the mean column of the head, leg and
    hem parts of frame 0 traced with the shoe centre on the axis, against the same in poses/serious.txt (the
    rig's centre line is the body's, heads and feet together, not the shoes'). Cached in cache/grok_rig."""
    path = CACHE / "centre.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))["shift"]

    def centre(k: rig.Frame, axis: int) -> list:
        out = []
        for tags in ("hw", "f", "m"):
            cs = [c for row in k.part for c, p in enumerate(row) if p in tags]
            out.append(sum(cs) / len(cs) + 0.5 - axis)
        return out
    fr, _ = keyframe(CLIP0, 0, shift=0.0)
    g, s = centre(fr, GAXIS), centre(rig.keyframe("serious"), rig.AXIS_COL)
    shift = sum(g) / 3 - sum(s) / 3
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(shift=shift, grok=g, serious=s, parts="head (h w), legs (f), hem (m)")),
                    encoding="utf-8")
    return shift


def sample(clip: str, f: int, shift: float | None = None) -> Image.Image:
    """Frame f matted and resampled onto the keyframe grid (GCOLS * SX x GROWS * SY samples), camera removed."""
    dr = drift(clip)
    im = src(clip, f)
    a = matte(im, dr["obs"][f]["foot"])
    rgba = im.convert("RGBA")
    rgba.putalpha(a)
    x0, y0, x1, y1 = grid_box(dr, f, shift)
    pad = 200
    big = Image.new("RGBa", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    big.paste(rgba.convert("RGBa"), (pad, pad))
    out = big.resize((GCOLS * SX, GROWS * SY), Image.LANCZOS, box=(x0 + pad, y0 + pad, x1 + pad, y1 + pad))
    return out.convert("RGBA")


def thumb(clip: str, f: int) -> Image.Image:
    """Frame f on white, camera removed, at 2 x 4 samples per cell (grey): what dedupe compares."""
    x0, y0, x1, y1 = grid_box(drift(clip), f)
    return src(clip, f).convert("L").resize((GCOLS * 2, GROWS * 4), Image.BOX, box=(x0, y0, x1, y1))


# ---------------------------------------------------------------- keyframes from motion

DUP = 2.5                   # mean grey difference (thumb) under which a frame repeats the last kept pose


def _tdiff(a: Image.Image, b: Image.Image) -> float:
    h = ImageChops.difference(a, b).histogram()
    return sum(i * c for i, c in enumerate(h)) / (a.width * a.height)


def dedupe(clip: str, f0: int, f1: int) -> tuple[list[tuple[int, float]], dict]:
    """Distinct poses in frames f0..f1: [(source frame, difference to the previous kept frame)], and the source's
    own progress between each pair of kept poses: {frame: 0..1} for the frames in between (how far the frame has
    gone from the pose before toward the pose after). A frame is kept when it differs from the last KEPT frame by
    DUP or more, so a slow drift still yields keys, the ~8 fps clips keep one frame per pose, and their partial
    blend frames (M14) count as progress, not as poses."""
    ths = {f: thumb(clip, f) for f in range(f0, f1 + 1)}
    kept, last = [(f0, 0.0)], ths[f0]
    for f in range(f0 + 1, f1 + 1):
        d = _tdiff(ths[f], last)
        if d >= DUP:
            kept.append((f, d))
            last = ths[f]
    progress = {}
    for (a, _), (b, _) in zip(kept, kept[1:]):
        run = 0.0
        for f in range(a + 1, b):
            da, db = _tdiff(ths[f], ths[a]), _tdiff(ths[f], ths[b])
            run = max(run, da / max(1e-6, da + db))  # monotone: a pose does not go back
            progress[f] = round(run, 3)
    return kept, progress


# ---------------------------------------------------------------- parts and tracing

# The start image's landmarks in keyframe cells (col, row), read off frame 0 on the grid, the way rig.FIT holds
# the sprites' (every clip starts on this image, and the normalisation puts it on the same cells)
GFIT = dict(
    neck=(35.5, 9.2),           # where the chin meets the collar
    head=(10.5, 3.65, 7.3),     # head ellipse: half-width, centre above the neck, half-height (rig: 215/150/300 px)
    band=4.6,                   # headdress: white cells more than this above the neck (rig: 190 px)
    waist=15.0,                 # top of the apron: below it the dark cloth is skirt
    hem=36.0,                   # bottom of the skirt frill at the centre
    skirt=((28.5, 16.0, 19.5, 33.0), (44.3, 16.0, 51.0, 32.5)),  # the overskirt's left and right outline
    torso=6.0,                  # half-width of the bodice column; beside it, above the waist, are the sleeves
    tail_top=19.5,              # the fluke's top: the tail is dark cloth right of the skirt below this row
    face=[(33.6, 7.05, "o"), (37.65, 6.55, "o"), (36.0, 7.7, "o")],  # eyes and mouth
)


def _edge(line: tuple, row: float) -> float:
    c0, r0, c1, r1 = line
    return c0 + (c1 - c0) * (row - r0) / (r1 - r0)


def _classes(img: Image.Image):
    rgba = rig._pixels(img)
    hsv = rig._pixels(img.convert("RGB").convert("HSV"))
    return rgba, hsv, [rig._colour_class(p, q) for p, q in zip(rgba, hsv)]


def _components(cand: set, w: int) -> list[list[int]]:
    """4-connected components of a set of sample indices."""
    out, seen = [], set()
    for i in cand:
        if i in seen:
            continue
        comp, stack = [], [i]
        seen.add(i)
        while stack:
            j = stack.pop()
            comp.append(j)
            for k in (j + 1, j - 1, j + w, j - w):
                if k in cand and k not in seen and (abs(k - j) == w or k // w == j // w):
                    seen.add(k)
                    stack.append(k)
        out.append(comp)
    return out


def face_at(img: Image.Image, cls: list, ref: tuple | None = None) -> tuple[float, float]:
    """Centroid (col, row) of her face: the largest skin region near where the start image has it (hands reaching
    past the window do not count)."""
    w, h = img.width, img.height
    fx, fy = ref or (GFIT["neck"][0], GFIT["neck"][1] - 1.5)
    x0, x1 = max(0, int((fx - 20) * SX)), min(w, int((fx + 20) * SX))   # M02's lean moves her face 16 columns
    y0, y1 = max(0, int((fy - 4) * SY)), min(h, int((fy + 7) * SY))
    cand = {y * w + x for y in range(y0, y1) for x in range(x0, x1) if cls[y * w + x] == 3}
    comps = _components(cand, w)
    if not comps:
        return fx, fy
    best = max(comps, key=len)
    return (sum(i % w for i in best) / len(best) + 0.5) / SX, (sum(i // w for i in best) / len(best) + 0.5) / SY


def _navy(p, q) -> bool:
    """The tail's colour (and the overskirt's): dark, bluish, opaque."""
    return p[3] >= 100 and q[2] < 140 and (q[1] >= 30 or q[2] < 80)


def _tail(img: Image.Image, rgba: list, hsv: list, off: float = 0.0) -> set:
    """Samples of the tail: navy right of the overskirt's outline below the fluke's top, in pieces big enough and
    reaching out far enough to be the tail (not a cuff or a dark lock of hair), regrown half a cell into navy
    where the stem meets the skirt."""
    w, h = img.width, img.height
    r0, r1 = int(GFIT["tail_top"] * SY), int((GFIT["hem"] + 0.6) * SY)
    cand = set()
    for y in range(r0, r1):
        e = (_edge(GFIT["skirt"][1], (y + 0.5) / SY) + off + 0.3) * SX
        for x in range(int(e) + 1, w):
            if _navy(rgba[y * w + x], hsv[y * w + x]):
                cand.add(y * w + x)
    out = set()
    for comp in _components(cand, w):
        reach = max(i % w / SX - _edge(GFIT["skirt"][1], i // w / SY) - off for i in comp)
        if len(comp) >= 60 and reach >= 2.0:
            out.update(comp)
    for _ in range(3):
        grow = {k for j in out for k in (j + 1, j - 1, j + w, j - w)
                if 0 <= k < w * h and k not in out and r0 <= k // w < r1 and _navy(rgba[k], hsv[k])}
        out |= grow
    return out


def classify(img: Image.Image, rgba: list, hsv: list, cls: list, face: tuple[float, float],
             ref: tuple[float, float], off: float = 0.0) -> list[str]:
    """Part letter per sample ('' where empty): rig._classify's model with Grok's start-image landmarks (GFIT),
    the head moved by the face's offset from the start image. Below the waist all cloth is skirt, as in the rig
    (a lean shifts the skirt, so its outline is not transferred), and only hands are arm there. Where a cell could
    be two things it gets a rigid part (body or skirt) rather than a guess."""
    w = img.width
    tail = _tail(img, rgba, hsv, off)
    dxc, dyr = face[0] - ref[0], face[1] - ref[1]
    nx0 = GFIT["neck"][0] + off          # GFIT columns are read at shift 0: off = -centre_shift()
    nx, ny = nx0 + dxc, GFIT["neck"][1] + dyr
    rx, up, ry = GFIT["head"]
    hx, hy = nx, ny - up
    waist, hem = GFIT["waist"], GFIT["hem"]
    hem_top = hem - 0.25 * (hem - waist)
    left, right = GFIT["skirt"]
    # the bodice column runs from the neck (wherever the head went) down to the start image's waist centre; a
    # lean that lowers the head lowers the waist with it
    waist_here = waist + max(0.0, dyr) * 0.5
    out = []
    for i, (p, k) in enumerate(zip(rgba, cls)):
        if p[3] < 100:
            out.append("")
            continue
        col, row = (i % w + 0.5) / SX, (i // w + 0.5) / SY
        ex, ey = (col - hx) / rx, (row - hy) / ry
        if i in tail:
            out.append("t")
        elif ex * ex + ey * ey < 1 and row < ny + 0.25:
            out.append("w" if k == 4 and row < ny - GFIT["band"] else "h")
        elif k == 2 and (row < 24.5 or not _edge(left, row) + off - 3 <= col <= _edge(right, row) + off + 3):
            out.append("H")
        elif k == 3:
            out.append("a")
        elif row >= hem - 0.12:
            out.append("f")
        elif row >= hem_top:
            out.append("m")
        elif row >= waist_here:
            out.append("b" if k == 4 else "s")
        else:
            tx = nx + (nx0 - nx) * max(0.0, min(1.0, (row - ny) / max(1.0, waist_here - ny)))
            half = GFIT["torso"] if row > ny + 1.5 else GFIT["torso"] - 1
            out.append("a" if abs(col - tx) > half else "b")
    return out


def trace(img: Image.Image, parts: list[str], face: list) -> rig.Frame:
    """rig._trace on a Grok sample image: per cell coverage, part vote, shade, colour classes; outline glyphs from
    the alpha's structure tensor, inner lines where two colour regions meet; the face box holds only the features."""
    w = img.width
    rgba = rig._pixels(img)
    cls = [rig._colour_class(p, q) for p, q in zip(rgba, rig._pixels(img.convert("RGB").convert("HSV")))]
    alpha = [a / 255 for (_, _, _, a) in rgba]
    lum = [(0.3 * r + 0.59 * g + 0.11 * b) / 255 if a > 20 else 0.0 for (r, g, b, a) in rgba]

    part, shade, classes = {}, {}, {}
    for row in range(GROWS):
        for col in range(GCOLS):
            idx = [(row * SY + j) * w + col * SX + i for j in range(SY) for i in range(SX)]
            c = sum(alpha[k] for k in idx) / len(idx)
            ps = [parts[k] for k in idx if parts[k]]
            if c < 0.42 or not ps:
                continue
            counts = {}
            for q in ps:
                counts[q] = counts.get(q, 0) + 1
            best = max(counts, key=counts.get)
            for q in "thw":
                if counts.get(q, 0) * 3 >= len(ps) and best not in "thw":
                    best = q
            part[row, col] = best
            lv = sum(lum[k] * alpha[k] for k in idx) / max(1e-6, sum(alpha[k] for k in idx))
            shade[row, col] = min(7, max(0, round(7 * lv ** 0.9)))
            cc = {}
            for k in idx:
                if cls[k]:
                    cc[cls[k]] = cc.get(cls[k], 0) + 1
            classes[row, col] = sorted(((n / len(idx), q) for q, n in cc.items()), reverse=True) or [(1.0, 1)]
    # drop wisps: cells with at most one filled neighbour (rig drops two, but a stretched arm is one row thick
    # at this scale and would vanish)
    for cell in [c for c in part if sum((c[0] + dr, c[1] + dc) in part for dr in (-1, 0, 1) for dc in (-1, 0, 1)) <= 2]:
        del part[cell], shade[cell], classes[cell]

    fr0, fr1 = min(f[0] for f in face), max(f[0] for f in face)
    fc0, fc1 = min(f[1] for f in face) - 1, max(f[1] for f in face) + 1
    art, indicator = {}, {}
    for (row, col) in part:
        x0, y0 = col * SX, row * SY
        edge = any((row + dr, col + dc) not in part for dr, dc in ((0, 1), (0, -1), (1, 0), (-1, 0)))
        if edge:
            st, coh, ang, cy = rig._tensor(alpha, w, x0, y0)
            if st < 0.004 or coh < 0.25:
                art[row, col] = "." if cy > 0.5 else "'"
                continue
            left = sum(alpha[(y0 + j) * w + x0 + i] for j in range(SY) for i in range(SX // 2))
            right = sum(alpha[(y0 + j) * w + x0 + i] for j in range(SY) for i in range(SX // 2, SX))
            art[row, col] = rig._line_glyph(ang, cy, 1 if right > left else -1)
            continue
        if fr0 <= row <= fr1 and fc0 <= col <= fc1:
            art[row, col] = ":"
            continue
        cl = classes[row, col]
        top = cl[0][1]
        mixed = len(cl) >= 2 and cl[1][0] >= 0.28
        meets = any(0 < classes[n][0][1] < top for n in ((row + dr, col + dc) for dr, dc in
                                                          ((0, 1), (0, -1), (1, 0), (-1, 0))) if n in classes)
        if mixed or meets:
            ind = indicator.setdefault(top, [1.0 if q == top else 0.0 for q in cls])
            st, coh, ang, cy = rig._tensor(ind, w, x0, y0, 0 if mixed else SX // 2)
            art[row, col] = rig._line_glyph(ang, cy, 0) if coh > 0.45 and st > 0.002 else ":"
        else:
            art[row, col] = ":"
    for row, col, g in face:
        if (row, col) in part:
            art[row, col] = g
    grid = lambda d: ["".join(d.get((r, c), " ") for c in range(GCOLS)) for r in range(GROWS)]  # noqa: E731
    return rig.Frame(grid(art), ["".join(str(shade[r, c]) if (r, c) in shade else " " for c in range(GCOLS))
                                 for r in range(GROWS)], grid(part))


EYE = (8, 7)                # half-size of an eye template, samples (about 2.7 x 1.2 cells)


@lru_cache(16)
def _eye_templates(clip: str, shift: float) -> list:
    """Frame 0's two eyes as grey templates, with their cells (the start image is the same in every clip)."""
    g = sample(clip, 0, shift).convert("L")
    out = []
    for x, y, _ in GFIT["face"][:2]:
        cx, cy = (x - shift) * SX, y * SY
        out.append((g.crop((round(cx) - EYE[0], round(cy) - EYE[1], round(cx) + EYE[0], round(cy) + EYE[1])),
                    x - shift, y))
    return out


def _match_eyes(img: Image.Image, clip: str, shift: float, dxc: float, dyr: float) -> list | None:
    """Each eye found near where the face track puts it: the best match of frame 0's eye within 3 columns and 2
    rows, a little dearer the further it is. None when the two do not look like a pair (then the track is used)."""
    g = img.convert("L")
    found = []
    for tmpl, ex, ey in _eye_templates(clip, shift):
        px, py = round((ex + dxc) * SX), round((ey + dyr) * SY)
        best = None
        for step, (rx, ry, cx0, cy0) in ((2, (18, 24, px, py)), (1, (2, 2, None, None))):
            cx0, cy0 = (px, py) if cx0 is not None else (best[1], best[2])
            for yy in range(cy0 - ry, cy0 + ry + 1, step):
                for xx in range(cx0 - rx, cx0 + rx + 1, step):
                    e = _tdiff(g.crop((xx - EYE[0], yy - EYE[1], xx + EYE[0], yy + EYE[1])), tmpl)
                    d2 = ((xx - px) / 10) ** 2 + ((yy - py) / 10) ** 2
                    e *= 1 + 0.15 * d2
                    if best is None or e < best[0]:
                        best = (e, xx, yy)
        found.append((best[1] / SX, best[2] / SY))
    (x0, y0), (x1, y1) = found
    if not (2.5 <= x1 - x0 <= 6.5 and abs(y1 - y0) <= 2.0):
        return None
    return found


def features(face: tuple[float, float], ref: tuple[float, float], off: float = 0.0, eyes: list | None = None
             ) -> list[tuple[int, int, str]]:
    """Eyes and mouth as (row, col, glyph): the eyes where they were matched (or moved with the face), the mouth
    moved with them; the mouth at least a row under the lower eye."""
    dxc, dyr = face[0] - ref[0], face[1] - ref[1]
    pred = [(x + dxc + off, y + dyr) for x, y, _ in GFIT["face"]]
    if eyes:
        cx = sum(e[0] - p[0] for e, p in zip(eyes, pred)) / 2
        cy = sum(e[1] - p[1] for e, p in zip(eyes, pred)) / 2
        pred = list(eyes) + [(pred[2][0] + cx, pred[2][1] + cy)]
    pts = [(int(y), int(x), g) for (x, y), (_, _, g) in zip(pred, GFIT["face"])]
    eye, mouth = pts[:2], pts[2]
    mouth = (max(mouth[0], max(e[0] for e in eye) + 1), mouth[1], mouth[2])
    return eye + [mouth]


PART_RGB = {"h": (240, 190, 160), "w": (250, 250, 250), "H": (70, 130, 255), "a": (255, 150, 40),
            "b": (150, 150, 160), "s": (40, 60, 150), "m": (180, 90, 220), "t": (40, 200, 110), "f": (150, 90, 50)}


def tile(fr: rig.Frame, label: str = "", k: int = 2) -> Image.Image:
    """A keyframe for the contact sheet: the art layer as glyphs (shade as brightness), and the part layer as
    colours, side by side."""
    from tuikit import F_MONO_B, font
    cw, ch = 5 * k, 10 * k
    rows, cols = len(fr.art), len(fr.art[0])
    out = Image.new("RGB", (2 * cols * cw + 8, rows * ch + 16), (12, 14, 24))
    d = ImageDraw.Draw(out)
    fnt = font(F_MONO_B, 9 * k)
    for r in range(rows):
        for c in range(cols):
            g, s, p = fr.art[r][c], fr.shade[r][c], fr.part[r][c]
            if g == " ":
                continue
            lv = int(s) if s.isdigit() else 4
            v = 150 + lv * 15
            d.text((c * cw, 16 + r * ch - k), g, font=fnt, fill=(int(v * 0.6), int(v * 0.8), v))
            x = cols * cw + 8 + c * cw
            d.rectangle([x, 16 + r * ch, x + cw - 1, 16 + r * ch + ch - 1], fill=PART_RGB.get(p, (255, 0, 255)))
            if g not in ":":
                d.text((x, 16 + r * ch - k), g, font=fnt, fill=(0, 0, 0))
    d.text((4, 1), label, font=font(F_MONO_B, 12), fill=(230, 230, 230))
    return out


def keyframe(clip: str, f: int, ref: tuple | None = None, shift: float | None = None) -> tuple[rig.Frame, dict]:
    """Source frame f of clip traced into a keyframe, plus what was measured on it."""
    shift = centre_shift() if shift is None else shift
    img = sample(clip, f, shift)
    rgba, hsv, cls = _classes(img)
    if ref is None:
        img0 = sample(clip, 0, shift)
        ref = face_at(img0, _classes(img0)[2])
    face = face_at(img, cls, ref)
    parts = classify(img, rgba, hsv, cls, face, ref, -shift)
    eyes = _match_eyes(img, clip, shift, face[0] - ref[0], face[1] - ref[1])
    feats = features(face, ref, -shift, eyes)
    return trace(img, parts, feats), dict(face=face, ref=ref, features=feats, eyes=eyes)


# ---------------------------------------------------------------- the timeline: gestures on the beat

FPS = 24
BEAT = 60.0 / 130.0         # engine.BEAT
FIRST_BEAT = 0.1587         # engine.FIRST_BEAT


def beat_t(n: float) -> float:
    """engine.beat_t"""
    return FIRST_BEAT + n * BEAT


# Gestures are accents, not clips: each takes one action out of a clip (the source frames between its anchors)
# and puts it on the song's beats. (source, anchors [(song beat, source frame), ...], join into it (first beat,
# beats), why). Between two anchors the source frames run at an even rate, so an action keeps its own pacing at
# the speed its window gives it; after the last anchor the pose holds (alive, see motion/arm_bob) until the next
# join. A join is a glyph morph from whatever drew her before, while the new action already runs: two beats in
# and out of the dance, one beat from the dance into the verse, half a beat between two gestures (the dancer's
# own pose morph takes a quarter beat; a longer mix of two unlike silhouettes reads as noise). Sung onsets
# are from world_execute_word_timing_20260927/word_timeline.json (film time); beat n is at 0.1587 + n * 60/130.
TIMELINE = [
    ("dancer", None, None,
     "the string dancer: the crouch in the two-beat break, the hop-in when the drums return (14.95)"),
    ("M02_inspect", [(34, 42), (36, 88)], (34, 2),
     "the corpus starts streaming (cut at 16.08): she leans in over two beats, arriving on downbeat 36 (16.77)"),
    ("dancer", None, (37, 2),
     "back into the dance over two beats (17.24-18.16); she dances the rest of the instrumental"),
    ("M03_present", [(65, 42), (67, 96)], (65, 1),
     "'If I'm a set ...' (29.77): one arm goes out, palm up, landing on 'point' (30.98 -> beat 67, 31.08)"),
    ("M06_invite", [(69, 66), (70.5, 110)], (69, 0.5),
     "'Then I will give ...': both arms open, landing on 'dimension' (32.71 -> 32.70)"),
    ("M09_decide", [(72, 100), (73, 114), (75, 150)], (72, 0.5),
     "'If I'm a circle': the arm goes up during the join (33.40-33.86), then she turns once around through "
     "'a circle' (34.31 = beat 74) into hands on hips at its end (beat 75, 34.77); the turn runs after the join, "
     "not inside it"),
    ("M28_cup_hands", [(76.5, 14), (78.5, 70)], (76.5, 0.5),
     "'Then I will give ...': the hands cup a round shape on 'circumference' (36.41 -> 36.39)"),
    ("M21_wave_goodbye", [(80.5, 50), (82, 64), (84, 110)], (80.5, 0.5),
     "'If I'm a sine ...': the hand comes up on 'sine' (38.01 = beat 82) and waves through 'wave'"),
    ("M18_bow", [(84, 60), (85.5, 110)], (84, 0.5),
     "'Then you can sit ...': she bows into 'sit' (39.37 -> 39.62)"),
    ("M20_reach_up_one", [(88, 50), (90, 118)], (88, 0.5),
     "'If I approach infinity': arms out and up into a V, landing on 'infinity' (41.52 -> beat 90, 41.70)"),
    ("M12_assert", [(92.5, 48), (94, 96)], (92.5, 0.5),
     "'Then you can be ...': she folds her arms on 'limitations' (43.56 -> beat 94, 43.54)"),
    ("M09_decide", [(95, 74), (96, 100), (98, 114)], (95, 0.5),
     "'Switch my current': the arm snaps straight up on 'Switch' (44.41 -> beat 96, 44.47), comes down by "
     "'current' (45.32 -> beat 98, 45.39)"),
    ("M15_clear_away", [(98.5, 50), (100, 96)], (98.5, 0.5),
     "'To AC, to DC': the arm sweeps out across, landing on 'AC' (46.35 -> beat 100, 46.31)"),
]


def anchors(i: int) -> list[tuple[float, float]]:
    """TIMELINE entry i's anchors as (song time, source frame)."""
    return [(beat_t(b), f) for b, f in TIMELINE[i][1]]


def phi(i: int, t: float) -> float:
    """Source frame of clip entry i at song time t: even between anchors, held before the first and after the
    last."""
    an = anchors(i)
    if t <= an[0][0]:
        return an[0][1]
    for (t0, f0), (t1, f1) in zip(an, an[1:]):
        if t <= t1:
            return f0 + (f1 - f0) * (t - t0) / (t1 - t0)
    return an[-1][1]


def holding(i: int, t: float) -> float:
    """0 while entry i's action runs, easing to 1 over a quarter beat once it has landed (its pose then holds)."""
    if TIMELINE[i][0] == "dancer":
        return 0.0
    return _smooth((t - anchors(i)[-1][0]) / (BEAT / 4))


def plan() -> dict:
    """Source frames each clip needs: the span of its anchors over all its gestures."""
    out = {}
    for name, an, _, _ in TIMELINE:
        if name == "dancer":
            continue
        lo, hi = min(f for _, f in an), max(f for _, f in an)
        a, b = out.get(name, (lo, hi))
        out[name] = (min(a, lo), max(b, hi))
    return out


def state(t: float):
    """(entry index, previous entry index or None, join progress 0..1 or None) at song time t."""
    k = 0
    for i, (_, _, jn, _) in enumerate(TIMELINE):
        if jn is not None and t >= beat_t(jn[0]):
            k = i
    jn = TIMELINE[k][2]
    if jn is not None and t < beat_t(jn[0] + jn[1]):
        return k, k - 1, (t - beat_t(jn[0])) / (jn[1] * BEAT)
    return k, None, None


def acting(t: float) -> bool:
    """A gesture draws her, or a join into or out of one is running."""
    k, prev, _ = state(t)
    return TIMELINE[k][0] != "dancer" or prev is not None


def _smooth(u: float) -> float:
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


# ---------------------------------------------------------------- prepare (offline)

VERSION = 5                 # of the keys.json layout and the tracing rules: a change re-traces


def _trace_task(args):
    clip, f, ref = args
    fr, info = keyframe(clip, f, ref)
    return clip, f, fr.art, fr.shade, fr.part, info


def prepare(workers: int = 4, log=print) -> dict:
    """Observe the camera, dedupe and trace every clip in TIMELINE over the frames it needs (cache/grok_rig/)."""
    from concurrent.futures import ProcessPoolExecutor
    todo, meta = [], {}
    for clip, (lo, hi) in plan().items():
        path = CACHE / clip / "keys.json"
        if path.exists():
            old = json.loads(path.read_text(encoding="utf-8"))
            same = ([lo, hi], DUP, centre_shift(), VERSION)
            if (old["range"], old["dup"], old.get("shift"), old.get("version")) == same:
                continue
        observe(clip, log)
        kept, prog = dedupe(clip, lo, hi)
        img0 = sample(clip, 0)
        ref = face_at(img0, _classes(img0)[2])
        meta[clip] = dict(range=[lo, hi], dup=DUP, ref=ref, kept=kept, progress=prog)
        todo += [(clip, f, ref) for f, _ in kept]
        log(f"{clip}: frames {lo}-{hi}, {len(kept)} distinct poses")
    if not todo:
        return plan()
    res = {}
    with ProcessPoolExecutor(workers) as ex:
        for n, (clip, f, art, shade, part, info) in enumerate(ex.map(_trace_task, todo, chunksize=2)):
            res[clip, f] = dict(f=f, art=art, shade=shade, part=part, face=info["face"], features=info["features"],
                                eyes=info["eyes"])
            if n % 20 == 0:
                log(f"  traced {n + 1}/{len(todo)}")
    for clip, m in meta.items():
        ks = [dict(res[clip, f], diff=d) for f, d in m["kept"]]
        (CACHE / clip).mkdir(parents=True, exist_ok=True)
        d = dict(range=m["range"], dup=DUP, shift=centre_shift(), version=VERSION, ref=m["ref"], keys=ks,
                 progress=m["progress"])
        (CACHE / clip / "keys.json").write_text(json.dumps(d), encoding="utf-8")
    for fn in (keys, progress, _anchors, _pair_order):
        fn.cache_clear()
    return plan()


@lru_cache(None)
def keys(clip: str) -> tuple[list[int], list[rig.Frame]]:
    d = json.loads((CACHE / clip / "keys.json").read_text(encoding="utf-8"))
    return [k["f"] for k in d["keys"]], [rig.Frame(k["art"], k["shade"], k["part"]) for k in d["keys"]]


# ---------------------------------------------------------------- playback: tween, pose, join

def _jitter(r: int, c: int) -> float:
    return ((r * 7919 + c * 104729) % 1000) / 1000.0


def order(a: rig.Frame, b: rig.Frame, phased: bool = True) -> dict:
    """Flip time 0..1 of every cell that differs between a and b, by its distance from the glyphs both share (the
    body that stays). In a join (phased) what only a has retracts tip first toward the body while what only b has
    grows out of the body, tip last, over the same span: a limb shortens at its old angle as it grows at the new
    one, and a head that moves is never gone (two half heads meet at the neck rather than none). Unphased (the
    tween between two kept poses, a step of a cell or two) every glyph change goes by distance. Glyphs that change
    on the shared figure (outline, features) go by distance, and cells whose glyph stays while shade or part
    change are spread evenly. Flip times are ranks within each group, so every frame flips a similar share of
    cells; a little jitter keeps the front from being a straight line."""
    rows, cols = len(a.art), len(a.art[0])
    shape, other, dist, front = [], [], {}, []
    for r in range(rows):
        ra, rb, sa, sb, pa, pb = a.art[r], b.art[r], a.shade[r], b.shade[r], a.part[r], b.part[r]
        for c in range(cols):
            if ra[c] != rb[c]:
                shape.append((r, c))
            else:
                if ra[c] != " ":
                    dist[r, c] = 0
                    front.append((r, c))
                if sa[c] != sb[c] or pa[c] != pb[c]:
                    other.append((r, c))
    if not shape and not other:
        return {}
    if not front:  # nothing shared: grow from the bottom
        r0 = max(r for r, _ in shape)
        front = [(r0, c) for r, c in shape if r == r0]
        for p in front:
            dist[p] = 1
    while front:
        nxt = []
        for r, c in front:
            d = dist[r, c] + 1
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    q = (r + dr, c + dc)
                    if 0 <= q[0] < rows and 0 <= q[1] < cols and q not in dist:
                        dist[q] = d
                        nxt.append(q)
        front = nxt
    dmax = max([dist[p] for p in shape] or [1])
    leave, come, change = [], [], []
    for p in shape:
        k = dist[p] + 0.9 * _jitter(*p)
        if b.art[p[0]][p[1]] == " ":
            leave.append((-k, p))
        elif a.art[p[0]][p[1]] == " ":
            come.append((k, p))
        else:
            change.append((k, p))
    change += [(dmax * _jitter(*p) + 0.5, p) for p in other]
    out = {}
    if not phased:
        change += [(-k, p) for k, p in leave] + come
        leave, come = [], []
    for group, lo, hi in ((leave, 0.0, 1.0), (come, 0.0, 1.0), (change, 0.0, 1.0)):
        group.sort()
        n = len(group)
        for i, (_, p) in enumerate(group):
            out[p] = lo + (hi - lo) * (i + 0.5) / n
    return out


def mix(a: rig.Frame, b: rig.Frame, flip: dict, u: float) -> rig.Frame:
    """a with every changed cell whose flip time is under u taken from b."""
    if u <= 0:
        return a
    if u >= 1:
        return b
    by_row = {}
    for (r, c), v in flip.items():
        if v < u:
            by_row.setdefault(r, []).append(c)
    out = ([], [], [])
    for r in range(len(a.art)):
        cs = by_row.get(r)
        for k, (la, lb) in enumerate(((a.art, b.art), (a.shade, b.shade), (a.part, b.part))):
            if cs:
                row = list(la[r])
                for c in cs:
                    row[c] = lb[r][c]
                out[k].append("".join(row))
            else:
                out[k].append(la[r])
    return rig.Frame(*out)


@lru_cache(512)
def _pair_order(clip: str, k: int) -> dict:
    fs, ks = keys(clip)
    return order(ks[k], ks[k + 1], phased=False)


STEP = 3                    # a tween spreads over at least this many frames before the next pose (8 fps steps)


@lru_cache(None)
def progress(clip: str) -> dict:
    d = json.loads((CACHE / clip / "keys.json").read_text(encoding="utf-8"))
    return {int(f): p for f, p in d["progress"].items()}


@lru_cache(4096)
def _anchors(clip: str, k: int) -> tuple:
    """The source's progress from kept pose k to k + 1 as (frame, progress) anchors: frames that repeat a pose
    (a plateau of equal progress) are one anchor, on the plateau's last frame but one - the middle of a pose shown
    3 times at ~8 fps, the end of a hold - so that interpolating the anchors spreads a stepwise source over its
    frames, while a hold stays a hold until just before the move."""
    fs, _ = keys(clip)
    a, b = fs[k], fs[k + 1]
    pr = progress(clip)
    seq = [(a, 0.0)] + [(f, pr.get(f, 0.0)) for f in range(a + 1, b)]
    out, start = [], 0
    for i in range(1, len(seq) + 1):
        if i == len(seq) or abs(seq[i][1] - seq[start][1]) >= 0.08:
            run = seq[start:i]
            out.append((max(run[0][0], run[-1][0] - 1), sum(v for _, v in run) / len(run)))
            start = i
    return tuple(out) + ((b, 1.0),)


def clip_frame(clip: str, phi: float) -> rig.Frame:
    """The clip at source frame position phi as a keyframe grid: the kept pose before phi tweened toward the next
    one. The tween follows the source's own progress between the two poses (_anchors: a slow drift flips its cells
    as it drifts, a partial blend frame counts for what it is, a pose repeated at ~8 fps is spread over its
    frames), and never later than an even spread over the last STEP frames before the next pose."""
    import bisect
    fs, ks = keys(clip)
    k = bisect.bisect_right(fs, phi) - 1
    if k < 0:
        return ks[0]
    if k >= len(fs) - 1:
        return ks[-1]
    an = _anchors(clip, k)
    j = bisect.bisect_right([f for f, _ in an], phi)
    if j == 0:
        u_src = an[0][1]
    elif j >= len(an):
        u_src = 1.0
    else:
        (f0, v0), (f1, v1) = an[j - 1], an[j]
        u_src = v0 + (v1 - v0) * (phi - f0) / (f1 - f0)
    b = fs[k + 1]
    w = min(STEP, b - fs[k])
    u = max(u_src, (phi - (b - w)) / w)
    if u <= 0:
        return ks[k]
    return mix(ks[k], ks[k + 1], _pair_order(clip, k), min(1.0, u))


def arm_bob(fr: rig.Frame) -> rig.Frame:
    """A held arm lifted one row: the arm cells beside the body (part a, more than 7 columns off the centre line,
    above the hips) move up a row where it is empty."""
    cells = [(r, c) for r in range(1, 20) for c, p in enumerate(fr.part[r]) if p == "a" and abs(c + 0.5 - GAXIS) > 7]
    if len(cells) < 4:
        return fr
    art, shade, part = ([list(row) for row in layer] for layer in (fr.art, fr.shade, fr.part))
    for r, c in cells:
        art[r][c] = shade[r][c] = part[r][c] = " "
    for r, c in cells:
        if art[r - 1][c] == " ":
            art[r - 1][c], shade[r - 1][c], part[r - 1][c] = fr.art[r][c], fr.shade[r][c], fr.part[r][c]
    return rig.Frame(*(["".join(row) for row in layer] for layer in (art, shade, part)))


def pose(fr: rig.Frame, m, cols: int, rows: int, bob: bool = False) -> rig.Frame:
    """rig.frame on a Grok keyframe: the same sway, bend, squash, hop, head, hair, hem and tail string operations,
    with rig's grid width set to the Grok grid's for the call; bob lifts a held arm a row first."""
    if bob:
        fr = arm_bob(fr)
    saved = rig.KCOLS, rig.AXIS_COL, rig.keyframe, rig._key
    try:
        rig.KCOLS, rig.AXIS_COL = GCOLS, GAXIS
        rig.keyframe = lambda _pose: fr
        key = rig._Key("grokrig", False)
        rig._key = lambda _pose, _mirror: key
        return rig.frame("grokrig", False, m, cols, rows)
    finally:
        rig.KCOLS, rig.AXIS_COL, rig.keyframe, rig._key = saved


LIT = 0.04                  # a join lights the glyph changes within this of the flip front (8% of them)

# While a gesture runs, the dance goes on below it: the kick squash, the hops, hem, tail and hair at full. What the
# gesture owns (the lean, the head) is eased back while the action runs, and comes back while its pose holds; a
# holding pose also shifts its weight every two beats, tilts the head on each beat and lifts a held arm a row on
# each beat (BOB), so no pose stands still.
ACT_MOVE = dict(sway=0.6, bend=0.5, squash=1.0, hop=1.0, shift=0.5, head=0.5, hair=1.0, hem=1.0, tail=1.0, turn=0.0)
ACT_HOLD = dict(sway=1.0, bend=0.8, squash=1.0, hop=1.0, shift=1.0, head=1.0, hair=1.0, hem=1.0, tail=1.0, turn=0.0)
LIFE = dict(sway=1.5, head=2.0)   # degrees added while a pose holds
BOB = 0.35                  # the first part of each beat a held arm stays lifted


def _tick(u: float, a: float = 0.15) -> float:
    """Snap to 1 in a, ease back to 0 by 1."""
    if u <= 0 or u >= 1:
        return 0.0
    return _smooth(u / a) if u < a else 0.5 + 0.5 * math.cos(math.pi * (u - a) / (1 - a))


def motion(m, k: float, hold: float = 0.0, t: float = 0.0):
    """choreo's Motion for a gesture: scaled by k (0 dancing .. 1 acting) toward ACT_MOVE / ACT_HOLD (by hold), plus
    the holding pose's own life."""
    from motion import Motion
    m = m or Motion()
    out = {}
    for f in ACT_MOVE:
        s = ACT_MOVE[f] + (ACT_HOLD[f] - ACT_MOVE[f]) * hold
        out[f] = getattr(m, f) * (1 + (s - 1) * k)
    b = (t - FIRST_BEAT) / BEAT
    life = k * hold
    out["sway"] += life * LIFE["sway"] * math.sin(math.pi * b / 2)
    out["head"] += life * LIFE["head"] * (1 if math.floor(b) % 2 else -1) * _tick(b - math.floor(b))
    return Motion(**out)


def placed(i: int, t: float, st, m, cols: int, rows: int, bob: bool = False) -> rig.Frame:
    """TIMELINE entry i at song time t, posed on the pane grid."""
    name = TIMELINE[i][0]
    if name == "dancer":
        return rig.frame(st.pose, st.flip, m, cols, rows)
    return pose(clip_frame(name, phi(i, t)), m, cols, rows, bob)


def frame_at(t: float, base: str, cols: int, rows: int, pinned: bool = False, still: bool = False):
    """(her Frame on the pane grid, cells mid-flip in a join, choreo's Step) at song time t; still: no Motion and no
    arm bob (the pose alone)."""
    import choreo
    from motion import Motion
    st = choreo.at(t, base, pinned)
    k, prev, u = state(t)
    e = _smooth(u) if u is not None else 1.0
    acts = [TIMELINE[j][0] != "dancer" for j in (prev if prev is not None else k, k)]
    holds = [holding(j, t) for j in (prev if prev is not None else k, k)]
    hold = holds[0] + (holds[1] - holds[0]) * e
    m = Motion() if still else motion(st.motion, acts[0] + (acts[1] - acts[0]) * e, hold, t)
    up = not still and ((t - FIRST_BEAT) / BEAT) % 1 < BOB
    b = placed(k, t, st, m, cols, rows, up and holds[1] > 0.5)
    if u is None:
        return b, (), st
    a = placed(prev, t, st, m, cols, rows, up and holds[0] > 0.5)
    fl = order(a, b)
    lit = [p for p, v in fl.items() if abs(v - u) < LIT and a.art[p[0]][p[1]] != b.art[p[0]][p[1]]]
    return mix(a, b, fl, u), lit, st


# ---------------------------------------------------------------- drawing: dancer.draw, and the join's lit cells

def render(t: float, size, base: str = "shy", pinned: bool = False, tint: str = "blue", under: float = 0.5):
    """dancer.render with her figure from the Grok keyframes while she acts (same cells, lyric fill and ramp)."""
    import random

    import dancer
    from tuikit import BLUE_HI
    if not acting(t):
        return _INNER[0](t, size, base, pinned, tint, under)
    cw, chh = dancer._cell()
    cols, rows = size[0] // cw, size[1] // chh
    fr, flips, st = frame_at(t, base, cols, rows, pinned)
    g = dancer.draw(fr, t, tint, None, 1.0, st.scramble, seed=int(t * FPS))
    rnd = random.Random(int(t * FPS) * 31)
    for r, c in flips:  # the join's front: cells mid-flip show a lit scramble glyph, as in the dancer's pose morph
        if fr.art[r][c] == " ":
            continue
        g.paste((0, 0, 0, 0), (c * cw, r * chh, (c + 1) * cw, (r + 1) * chh))
        ch = dancer.SCRAMBLE[rnd.randrange(len(dancer.SCRAMBLE))]
        g.paste(BLUE_HI + (255,), (c * cw, r * chh), dancer._glyph(ch))
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    out.alpha_composite(g, ((size[0] - g.width) // 2, size[1] - g.height))
    return out, st


_INNER = [None]


def install() -> None:
    """Route dancer.render through render() (once)."""
    import dancer
    if _INNER[0] is None:
        _INNER[0] = dancer.render
        dancer.render = render


# ---------------------------------------------------------------- report and contact sheet

RETURNS = {"M14_reach_withdraw": 240, "M15_clear_away": 240}   # clips that end standing again: checked at f240


def _rows(fr: rig.Frame) -> tuple[int, int]:
    rs = [r for r, s in enumerate(fr.art) if s.strip()]
    return rs[0], rs[-1]


def _centre(fr: rig.Frame, axis: int) -> float:
    vals = []
    for tags in ("hw", "f", "m"):
        cs = [c for row in fr.part for c, p in enumerate(row) if p in tags]
        vals.append(sum(cs) / len(cs) + 0.5 - axis if cs else 0.0)
    return sum(vals) / 3


def _stray(fr: rig.Frame, row0: int = 36) -> int:
    """Cells from the hem down (row0) that are not joined to her figure (8-connected to its largest piece): a floor
    shadow or a speck. A wide stance or a low skirt is figure, not stray."""
    cells = {(r, c) for r, row in enumerate(fr.art) for c, ch in enumerate(row) if ch != " "}
    best, seen = set(), set()
    for p in cells:
        if p in seen:
            continue
        comp, stack = {p}, [p]
        seen.add(p)
        while stack:
            r, c = stack.pop()
            for q in ((r + dr, c + dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1)):
                if q in cells and q not in seen:
                    seen.add(q)
                    comp.add(q)
                    stack.append(q)
        if len(comp) > len(best):
            best = comp
    return sum(1 for p in cells - best if p[0] >= row0)


def _extra(clip: str, f: int) -> rig.Frame:
    """A keyframe outside the traced ranges (the return frames), cached."""
    path = CACHE / clip / f"extra_{f:04d}.json"
    if path.exists():
        d = json.loads(path.read_text(encoding="utf-8"))
        if (d.get("shift"), d.get("version")) == (centre_shift(), VERSION):
            return rig.Frame(d["art"], d["shade"], d["part"])
    observe(clip)
    fr, _ = keyframe(clip, f)
    path.parent.mkdir(parents=True, exist_ok=True)
    d = dict(shift=centre_shift(), version=VERSION, art=fr.art, shade=fr.shade, part=fr.part)
    path.write_text(json.dumps(d), encoding="utf-8")
    return fr


WORDS = Path(__file__).resolve().parents[2].joinpath("world_execute_word_timing_20260927/word_timeline.json")


def _words(t0: float, t1: float) -> list:
    """Sung words starting in [t0, t1): (onset, text)."""
    try:
        d = json.loads(WORDS.read_text(encoding="utf-8"))
    except OSError:
        return []
    return [(round(w["start"], 2), w["text"]) for w in d["words"] if t0 <= w["start"] < t1]


def report(path: Path = ROOT / "grokrig_report.json", videos: dict | None = None) -> dict:
    """grokrig_report.json: the gestures (anchors on beats and sung words, source span and how much faster or
    slower than Grok it runs), per clip what was used and kept, the camera drift and what is left of it, how the
    neutral lands against serious.txt at the start and on return, stray cells under the feet, the geometry of
    every join, pose holds (the pose grid without motion) and body motion measured on the videos."""
    ser = rig.keyframe("serious")
    ser_top, ser_bot = _rows(ser)
    f0 = _extra(CLIP0, 0)
    top0, bot0 = _rows(f0)
    gestures = []
    for i, (name, an, jn, why) in enumerate(TIMELINE):
        g = dict(source=name, why=why)
        if jn is not None:
            g["join"] = dict(beats=[jn[0], jn[0] + jn[1]], t=[round(beat_t(jn[0]), 3), round(beat_t(jn[0] + jn[1]), 3)])
        if an:
            g["anchors"] = [dict(beat=b, t=round(beat_t(b), 3), frame=f) for b, f in an]
            (b0, f0_), (b1, f1_) = an[0], an[-1]
            g["source_frames"] = [f0_, f1_]
            g["speed_vs_source"] = round(((f1_ - f0_) / FPS) / ((b1 - b0) * BEAT), 2)
            g["lands"] = dict(beat=b1, t=round(beat_t(b1), 3))
            g["sung_words_in_gesture"] = _words(beat_t(jn[0]), beat_t(b1) + 0.3)
        gestures.append(g)
    out = dict(
        method="see README.md, 'Her from Grok keyframes (V2_HER=grokrig)'",
        grid=dict(rows=GROWS, cols=GCOLS, axis_col=GAXIS, fig_rows=rig.FIG_ROWS, cell_px=[5, 10]),
        centre_shift_cols=round(centre_shift(), 3),
        neutral_vs_serious=dict(
            serious=dict(top_row=ser_top, foot_row=ser_bot, centre=round(_centre(ser, rig.AXIS_COL), 2)),
            frame0=dict(top_row=top0, foot_row=bot0, centre=round(_centre(f0, GAXIS), 2)),
            rows_off_top=top0 - ser_top, rows_off_feet=bot0 - ser_bot,
            cols_off_centre=round(_centre(f0, GAXIS) - _centre(ser, rig.AXIS_COL), 2)),
        gestures=gestures,
        clips={})
    for clip in list(plan()) + [c for c in RETURNS if c not in plan()]:
        dr = drift(clip)
        obs, rh = dr["obs"], dr["cal"]["rh"]
        dy_fit = [camera(dr, o["f"])[2] for o in obs]
        foot_res = [(o["dy"] - d) / rh for o, d in zip(obs, dy_fit)]
        cam = dict(foot_line_creep_px=round(dr["creep_px"], 1), push_in=dr["push_in"],
                   kappa_per_px=dr["kappa"], kappa_fit_per_clip=dr["kappa_fit"],
                   zoom_at_f240_pct=round(100 * (camera(dr, 240)[0] - 1), 2),
                   foot_residual_rows=dict(rms=round(math.sqrt(sum(r * r for r in foot_res) / len(foot_res)), 3),
                                           max=round(max(abs(r) for r in foot_res), 3)))
        if dr["push_in"]:
            cam["still_stretches"] = dr["still_runs"]
            cam["height_residual_rows_rms"] = round(dr["height_residual"] * rig.FIG_ROWS, 3)
            # her height in the still stretches after the camera is taken out, first and last frame of each
            cam["height_in_stretches_after_correction_rows"] = [
                [round(rig.FIG_ROWS * (obs[f]["h"] / camera(dr, f)[0] - 1), 2) for f in (a, b)]
                for a, b in dr["still_runs"]]
        else:
            cam["note"] = "foot line still (creep under 4 px): no zoom; changes in her height are the action"
        c = dict(camera=cam)
        if clip in plan():
            lo_f, hi_f = plan()[clip]
            fs, ks = keys(clip)
            d = json.loads((CACHE / clip / "keys.json").read_text(encoding="utf-8"))
            cam["zoom_over_used_frames_pct"] = [round(100 * (camera(dr, lo_f)[0] - 1), 2),
                                                round(100 * (camera(dr, hi_f)[0] - 1), 2)]
            gaps = [b - a for a, b in zip(fs, fs[1:])] or [0]
            c.update(frames_used=[lo_f, hi_f], frames_in_range=hi_f - lo_f + 1, keyframes_kept=len(fs),
                     keyframe_source_frames=fs,
                     keyframe_gap_frames=dict(min=min(gaps), max=max(gaps), three=sum(g == 3 for g in gaps),
                                              one=sum(g == 1 for g in gaps)),
                     feet=dict(foot_row_min=min(_rows(k)[1] for k in ks), foot_row_max=max(_rows(k)[1] for k in ks)),
                     stray_cells_below_feet=dict(total=sum(_stray(k) for k in ks),
                                                 keyframes_with_any=sum(_stray(k) > 0 for k in ks)),
                     eyes_matched=sum(1 for k in d["keys"] if k.get("eyes")),
                     faces=[k["features"] for k in d["keys"]][::max(1, len(fs) // 6)])
            fk = _extra(clip, 0)
            c["neutral_at_start"] = dict(top_row=_rows(fk)[0], foot_row=_rows(fk)[1],
                                         rows_off_top=_rows(fk)[0] - top0, rows_off_feet=_rows(fk)[1] - bot0)
        if clip in RETURNS:
            fr = _extra(clip, RETURNS[clip])
            top, bot = _rows(fr)
            c["neutral_at_return"] = dict(frame=RETURNS[clip], top_row=top, foot_row=bot, rows_off_top=top - top0,
                                          rows_off_feet=bot - bot0,
                                          within_one_row=abs(top - top0) <= 1 and abs(bot - bot0) <= 1,
                                          stray_cells_below_feet=_stray(fr))
        out["clips"][clip] = c
    out["joins"] = joins()
    out["pose_holds"] = dict(dancer=pose_holds("dancer"), grokrig_r1=POSE_HOLDS_R1, grokrig=pose_holds("grokrig"),
                             note="pose grid without motion, 2x2-cell body blocks, a hold lasts while at most 6 "
                                  "blocks differ from its first frame; verse from 29.28 (beat 63)")
    out["body_motion_video"] = {name: video_motion(p) for name, p in (videos or {}).items() if Path(p).exists()}
    path.write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


def joins(cols: int = 70, rows: int = 45) -> list:
    """Both sides of every join at its middle, posed without motion on her pane grid (70 x 45 cells with the
    softmax): top row, foot row, centre column (mean of the leg cells), hem width (the widest row of hem cells).
    The dancer's pose is the one choreo gives the shot's expression (read through v2)."""
    import choreo
    from motion import Motion
    still = Motion()

    def geo(fr):
        top, bot = _rows(fr)
        legs = [c for r in range(bot - 3, bot + 1) for c, p in enumerate(fr.part[r]) if p == "f"]
        ms = [[c for c, p in enumerate(row) if p == "m"] for row in fr.part]
        hem = max((m[-1] - m[0] + 1 for m in ms if m), default=0)
        return dict(top_row=top, foot_row=bot, centre_col=round(sum(legs) / max(1, len(legs)) + 0.5, 1), hem=hem)
    out = []
    for i, (name, _, jn, _) in enumerate(TIMELINE):
        if jn is None:
            continue
        t = beat_t(jn[0] + jn[1] / 2)
        st = choreo.at(t, _base(t))
        a, b = placed(i - 1, t, st, still, cols, rows), placed(i, t, st, still, cols, rows)
        out.append(dict(t=round(t, 3), frm=TIMELINE[i - 1][0], to=name, dancer_pose=st.pose, frm_geo=geo(a),
                        to_geo=geo(b)))
    return out


def _base(t: float) -> str:
    """The expression the shot at t gives her (through v2, which the report needs loaded)."""
    import os
    os.environ.setdefault("V2_SECTIONS", "s_pretrain")
    import v2
    return v2.call_of(v2.engine.shot_at(t))["expr"]


def pose_holds(mode: str, t0: float = 14.5, t1: float = 46.0, verse: float = 29.28, tol: int = 6) -> dict:
    """How long her pose holds, ignoring motion and the lyric fill: per frame the pose grid alone (the dancer's
    keyframe with its pose morph, or grokrig's gesture / tween / join grid, no Motion, no arm bob) as body blocks
    of 2 x 2 cells (on when 2+ cells are body, hair and tail excluded); a hold lasts while the blocks stay within
    `tol` of the frame that started it."""
    import choreo
    from motion import Motion
    still = Motion()
    cols, rows = 70, 45

    def grid(t):
        b = _base(t)
        if mode == "dancer" or not acting(t):
            st = choreo.at(t, b)
            fr = rig.frame(st.pose, st.flip, still, cols, rows)
            if st.prev and st.morph < 1:
                pv = rig.frame(st.prev, st.prev_flip, still, cols, rows)
                fr = mix(pv, fr, order(pv, fr), st.morph)
            return fr
        return frame_at(t, b, cols, rows, still=True)[0]

    def blocks(fr):
        on = lambda r, c: fr.part[r][c] not in " Ht"  # noqa: E731
        return [on(r, c) + on(r, c + 1) + on(r + 1, c) + on(r + 1, c + 1) >= 2
                for r in range(0, rows - 1, 2) for c in range(0, cols - 1, 2)]
    n0, n1 = round(t0 * FPS), round(t1 * FPS)
    runs, start, anchor = [], n0, None
    for n in range(n0, n1):
        bl = blocks(grid(n / FPS))
        if anchor is None:
            anchor = bl
        elif sum(x != y for x, y in zip(anchor, bl)) > tol:
            runs.append((start / FPS, (n - start) / FPS))
            start, anchor = n, bl
    runs.append((start / FPS, (n1 - start) / FPS))
    runs.sort(key=lambda r: -r[1])
    fmt = lambda rs: [dict(t=round(a, 2), s=round(l, 2)) for a, l in rs]  # noqa: E731
    vr = sorted(((max(a, verse), min(a + l, t1) - max(a, verse)) for a, l in runs if a + l > verse),
                key=lambda r: -r[1])  # the part of each hold inside the verse
    return dict(longest=fmt(runs[:6]), longest_in_verse=fmt(vr[:4]),
                over_one_bar_in_verse=fmt([r for r in vr if r[1] > 4 * BEAT]))


# pose_holds("grokrig") of the first iteration (r1: the clips at their own speed), measured the same way before
# the gestures replaced it: its code is gone, so the numbers are kept here for the comparison
POSE_HOLDS_R1 = dict(longest=[dict(t=33.29, s=4.75), dict(t=38.46, s=2.58), dict(t=44.38, s=1.62),
                              dict(t=28.75, s=1.54), dict(t=27.17, s=1.25), dict(t=19.12, s=1.21)],
                     longest_in_verse=[dict(t=33.29, s=4.75), dict(t=38.46, s=2.58), dict(t=44.38, s=1.62),
                                       dict(t=43.08, s=1.08)],
                     over_one_bar_in_verse=[dict(t=33.29, s=4.75), dict(t=38.46, s=2.58)])


def video_motion(path: str, box=(30, 110, 380, 540)) -> dict:
    """Body motion on a rendered video, ignoring the lyric inside her (the coordinator's measure): her pane as
    10 x 10 px blocks lit or not, blocks that toggle per frame."""
    import subprocess
    w, h = box[2] - box[0], box[3] - box[1]
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(path), "-vf",
                          f"crop={w}:{h}:{box[0]}:{box[1]},scale={w // 10}:{h // 10}:flags=area",
                          "-f", "rawvideo", "-pix_fmt", "gray", "-"], stdout=subprocess.PIPE)
    n = (w // 10) * (h // 10)
    prev, d = None, []
    while True:
        b = p.stdout.read(n)
        if len(b) < n:
            break
        m = [v > 22 for v in b]
        if prev is not None:
            d.append(sum(x != y for x, y in zip(m, prev)))
        prev = m
    p.wait()
    runs, r = [], 0
    for v in d:
        r = r + 1 if v <= 2 else (runs.append(r) or 0)
    runs.append(r)
    return dict(still_frames_pct=round(100 * sum(v <= 2 for v in d) / len(d), 1),
                longest_still_s=round(max(runs) / FPS, 2), mean_toggles=round(sum(d) / len(d), 1),
                per_second=[round(sum(d[i:i + FPS]) / FPS) for i in range(0, len(d), FPS)])


def sheet(path: Path = ROOT / "grokrig_keyframes.png", per: int = 6) -> Path:
    """grokrig_keyframes.png: per gesture a row of its traced keyframes (evenly through the kept ones inside the
    gesture's source frames, ending on the pose it lands on), each as the art layer and the part layer in colour
    side by side; a last row with frame 0, the return frames and serious.txt for scale."""
    from tuikit import F_MONO_B, font
    rows = []
    for i, (name, an, _, _) in enumerate(TIMELINE):
        if name == "dancer":
            continue
        fs, ks = keys(name)
        lo, hi = min(f for _, f in an), max(f for _, f in an)
        inside = [j for j, f in enumerate(fs) if lo <= f <= hi] or [0]
        pick = sorted({inside[round(j * (len(inside) - 1) / (per - 1))] for j in range(per)})
        land = an[-1][1]
        rows.append((name, [tile(ks[j], f"{name} f{fs[j]}" + ("  lands" if abs(fs[j] - land) < 3 else ""), 1)
                            for j in pick]))
    last = [tile(_extra(CLIP0, 0), "frame 0 (every clip)", 1)]
    last += [tile(_extra(c, f), f"{c} f{f} (return)", 1) for c, f in RETURNS.items()]
    ser = rig.keyframe("serious")
    pad = GAXIS - rig.AXIS_COL
    wide = rig.Frame(*[[" " * pad + r + " " * (GCOLS - pad - len(r)) for r in layer]
                       for layer in (ser.art, ser.shade, ser.part)])
    last.append(tile(wide, "poses/serious.txt (the dancer)", 1))
    rows.append(("neutral", last))
    tw, th = rows[0][1][0].size
    legend = 24
    img = Image.new("RGB", (tw * per, legend + th * len(rows)), (12, 14, 24))
    d = ImageDraw.Draw(img)
    x = 6
    for p, name in (("h", "head"), ("w", "headdress"), ("H", "long hair"), ("a", "arm/hand"), ("b", "body"),
                    ("s", "skirt"), ("m", "hem"), ("t", "tail"), ("f", "legs/shoes")):
        d.rectangle([x, 6, x + 12, 18], fill=PART_RGB[p])
        d.text((x + 16, 5), f"{p} {name}", font=font(F_MONO_B, 12), fill=(230, 230, 230))
        x += 130
    for r, (_, ts) in enumerate(rows):
        for j, t in enumerate(ts):
            img.paste(t, (j * tw, legend + r * th))
    img.save(path)
    return path


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["prepare", "report", "sheet", "all"])
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    if a.cmd in ("prepare", "all"):
        print(prepare(a.workers))
    if a.cmd in ("report", "all"):
        vids = {"dancer": ROOT / "sample_pretrain_v2.mp4", "grokrig_r1": ROOT / "sample_pretrain_v2_grokrig_r1.mp4",
                "grokrig": ROOT / "sample_pretrain_v2_grokrig.mp4"}
        r = report(videos=vids)
        print(json.dumps(dict(holds=r["pose_holds"], video={k: {x: y for x, y in v.items() if x != "per_second"}
                                                            for k, v in r["body_motion_video"].items()}), indent=1))
    if a.cmd in ("sheet", "all"):
        print(sheet())
