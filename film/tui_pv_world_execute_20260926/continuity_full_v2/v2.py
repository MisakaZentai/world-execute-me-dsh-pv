"""Continuity v2: the whole song, section by section.

  python -B -X utf8 v2.py --stills 16.0,16.2,19.6                    PNGs into stills/
  python -B -X utf8 v2.py --range 14.5 46.0 --tag pretrain           a section sample, its v1 comparison, strips
  python -B -X utf8 v2.py --full                                     the whole film (tui_pv_full_v2.mp4)

Sections plug in as modules (SECTIONS, in song order). A section module may define:
  STUB      sec_* modules whose scenes call me_pane: while v2 draws those scenes she is drawn by her own layer
  REPLACE   {shot name: scene function}   in-memory v2 versions of scenes (the originals stay untouched)
  SPLIT     shot names laid out as her pane + the visualisation pane
  FULL_ART  shot names that keep the full body width; her pane slides out before them and back after
  SHELL     {shot name: shell command}    shell staging: header and ticker retract, the lyric stays
  CUTS      {cut index: Cut subclass}     cut index = index of the incoming shot in v1.ALL (audit numbering)
  HIDE_HER  shot names in which her pane is not drawn at all (before she is created, ...)
  OVERLAY   {shot name or index: fn(t, n) -> full-frame RGBA or None}: drawn over her for the whole shot
            (props on her: a blindfold, cat ears ... placed with her_anchor), below the cut's carriers
  OWN       {shot index: fn(t, n) -> finished RGB frame}   frames drawn by an approved renderer (chorus 1,
            the EXECUTION hits); a cut window still takes precedence
  setup(v1) called once after every section is loaded
A Cut's render() returns a cuts.Frame (layered by this loop) or a finished RGB image.
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw

import kit
from kit import FPS, W, H, engine, tk, v1

ROOT = kit.ROOT
ALL = v1.ALL
SECTIONS = ["s_boot", "s_pretrain", "s_sft", "s_chorus1", "s_deploy", "s_userleft", "s_reward", "s_exec", "s_eval"]
if os.environ.get("V2_SECTIONS"):  # e.g. V2_SECTIONS=s_pretrain,s_deploy: load only these (parallel section work)
    SECTIONS = [x for x in SECTIONS if x in os.environ["V2_SECTIONS"].split(",")]

# ---------------------------------------------------------------- owner decisions (CONTINUITY_V2_PLAN.md section 9)
# 2. the song stops dead at 207.08 s (RMS -19 dB at 207.05 -> -36 dB at 207.10); black starts on that frame
HARD_CUT = 4970 / FPS
ALL[-2].end = ALL[-1].start = HARD_CUT
engine.HARD_CUT = HARD_CUT
import choreo  # noqa: E402
import sec_outro  # noqa: E402

choreo.HARD_CUT = sec_outro.HARD_CUT = HARD_CUT

import cuts as C  # noqa: E402
import words  # noqa: E402

words.install()  # the lyric band follows the sung words; before the sections, so their band wrappers wrap it

MODS = []
for _name in SECTIONS:
    if (ROOT / f"{_name}.py").exists():
        MODS.append(importlib.import_module(_name))
SPLIT, FULL_ART, HIDE_HER, SHELL, OWN, OVERLAY = set(), set(), set(), {}, {}, {}
CUT_CLASSES = {}
for _m in MODS:
    kit.install_stub(*getattr(_m, "STUB", []))
    for _name, _fn in getattr(_m, "REPLACE", {}).items():
        for _s in ALL:
            if _s.fn.__name__ == _name:
                _s.fn = _fn
    SPLIT |= set(getattr(_m, "SPLIT", ()))
    FULL_ART |= set(getattr(_m, "FULL_ART", ()))
    HIDE_HER |= set(getattr(_m, "HIDE_HER", ()))
    SHELL.update(getattr(_m, "SHELL", {}))
    OWN.update(getattr(_m, "OWN", {}))
    OVERLAY.update(getattr(_m, "OVERLAY", {}))
    CUT_CLASSES.update(getattr(_m, "CUTS", {}))
_layout = kit.direction.layout


def layout(s):
    name = s.fn.__name__
    if name in SPLIT:
        return "split", "split", {}
    if name in FULL_ART:
        return "split", "full", {}
    return _layout(s)


kit.direction.layout = layout
for _m in MODS:
    # v2 is imported twice (as __main__ and as 'v2' by sections), but the section modules are shared: run setup()
    # once, or two sections wrapping the same kit function re-wrap each other into a cycle
    if hasattr(_m, "setup") and not getattr(_m, "_v2_setup_done", False):
        _m.setup(v1)
        _m._v2_setup_done = True
CUTS = [CUT_CLASSES[i](ALL[i - 1], ALL[i]) for i in sorted(CUT_CLASSES)]

HER = os.environ.get("V2_HER", "h3")  # h3: every character route uses continuous H3 sources
if HER == "h3":
    import h3_full
    h3_full.install()
if HER == "hybrid":
    import h3_motion
    h3_motion.install()
if HER == "grok":
    import grok
    grok.install()
    import scenes
    scenes.RIDER[0] = grok.rider


def active_cut(t):
    return next((c for c in CUTS if c.active(t)), None)


# ---------------------------------------------------------------- her

_CALLS: dict = {}


def call_of(shot):
    """What she was asked to be in this shot (expression, title, softmax); read once from the scene."""
    k = id(shot)
    if k not in _CALLS:
        _, ctx = C.body(shot, shot.start + 0.05, int(shot.start * FPS) + 1)
        _CALLS[k] = getattr(ctx, "her", None) or dict(expr="shy", rect=kit.LEFT, kw={})
    return _CALLS[k]


def key(call):
    return call["expr"], call["kw"].get("title")


def glide(prev, cur, u):
    """Same pose and title, new softmax: the bars slide to their new values instead of jumping."""
    a, b = dict(prev["kw"].get("dist") or []), cur["kw"].get("dist") or []
    kw = dict(cur["kw"], dist=[(name, a.get(name, 0.0) + (p - a.get(name, 0.0)) * u) for name, p in b])
    return dict(cur, kw=kw)


def retract_at(t):
    for s in ALL:
        name = s.fn.__name__
        if name in SHELL and s.start <= t < s.end + 0.35:
            r = kit.ease_out((t - s.start) / 0.3)
            if t >= s.end:
                r *= 1 - kit.ease_io((t - s.end) / 0.3)
            return r, SHELL[name]
    return 0.0, None


def slide_at(t):
    """0..1: how far her pane has slid out to the left for full-width art (out over 0.3 s before such a shot,
    back over 0.35 s after it)."""
    e = 0.0
    for s in ALL:
        if s.fn.__name__ not in FULL_ART:
            continue
        if s.start - 0.3 <= t < s.start:
            e = max(e, kit.ease_io((t - (s.start - 0.3)) / 0.3))
        elif s.start <= t < s.end:
            e = 1.0
        elif s.end <= t < s.end + 0.35:
            e = max(e, 1 - kit.ease_io((t - s.end) / 0.35))
    return e


_HER_CACHE: dict = {}


def her(t, n=None, glow=0.0, box_level=1.0):
    """Her pane as an RGBA layer at time t (cached per frame)."""
    k = (round(t * FPS * 1000), round(box_level, 3))
    if k in _HER_CACHE:
        layer = _HER_CACHE[k]
    else:
        layer = _her(t, box_level)
        if len(_HER_CACHE) > 8:
            _HER_CACHE.clear()
        _HER_CACHE[k] = layer
    return kit.her_glow(layer, glow)


def _her(t, box_level):
    s = engine.shot_at(t)
    i = ALL.index(s)
    cur = call_of(s)
    p = (t - s.start) / 0.3
    prev = call_of(ALL[i - 1]) if i and p < 1 else None
    if HER == "h3":
        if prev:
            cur = glide(prev, cur, kit.ease_io(p))
        return kit.her_layer(t, cur, box_level)
    if HER == "grok":
        if prev:
            cur = glide(prev, cur, kit.ease_io(p))
        src, before, q = grok.source_at(t)
        grok.SOURCE[0] = src
        try:
            layer = kit.her_layer(t, cur, box_level)
            if before is not None:
                grok.SOURCE[0] = before
                layer = kit.scan_mix(kit.her_layer(t, cur, box_level), layer, kit.ease_io(q))
        finally:
            grok.SOURCE[0] = None
        return layer
    # ---- V2_HER=grokrig: her figure from Grok keyframes through her own rig (grok_rig.py) -------------------
    if HER in ("grokrig", "hybrid"):
        import grok_rig
        grok_rig.install()
        continuous = HER == "hybrid" and h3_motion.active(t) is not None
        if prev and (key(prev) == key(cur) or grok_rig.acting(t) or continuous):
            cur, prev = glide(prev, cur, kit.ease_io(p)), None
        layer = kit.her_layer(t, cur, box_level)
        if prev:
            layer = kit.scan_mix(kit.her_layer(t, prev, box_level), layer, kit.ease_io(p))
        return layer
    # ---- end V2_HER=grokrig ------------------------------------------------------------------------------------
    if prev and key(prev) == key(cur):
        cur = glide(prev, cur, kit.ease_io(p))
    layer = kit.her_layer(t, cur, box_level)
    if prev and key(prev) != key(cur):
        layer = kit.scan_mix(kit.her_layer(t, prev, box_level), layer, kit.ease_io(p))
    return layer


def her_anchor(t, part="chest"):
    """Screen point of her head, chest or reaching hand (the rightmost point of her upper body), for carriers
    that leave from or arrive at her. Measured on her rendered figure, so it follows whatever draws her."""
    a = her(t).getchannel("A")
    x0, y0, x1, y1 = kit.LEFT
    box = (x0 + 4, y0 + 14, x1 - 4, y1 - 80)
    fig = a.crop(box).point(lambda v: 255 if v > 60 else 0)
    bb = fig.getbbox()
    if not bb:
        return (x0 + x1) / 2, (y0 + y1) / 2
    bx0, by0, bx1, by1 = bb
    cx, h_ = box[0] + (bx0 + bx1) / 2, by1 - by0
    if part == "head":
        return cx, box[1] + by0 + 0.1 * h_
    if part == "chest":
        return cx, box[1] + by0 + 0.33 * h_
    band = fig.crop((0, int(by0 + 0.2 * h_), fig.width, int(by0 + 0.55 * h_)))
    bb2 = band.getbbox() or (bx0, 0, bx1, 1)
    return box[0] + bb2[2], box[1] + by0 + 0.2 * h_ + (bb2[1] + bb2[3]) / 2


# ---------------------------------------------------------------- the frame loop

def frame(n: int):
    if HER == "h3":
        with h3_full.at(n / FPS):
            return _frame(n)
    return _frame(n)


def _frame(n: int):
    t = n / FPS
    s = engine.shot_at(t)
    i = ALL.index(s)
    cut = active_cut(t)
    if cut:
        fr = cut.render(t, n)
        if isinstance(fr, Image.Image):
            return fr
    elif i in OWN:
        return OWN[i](t, n)
    else:
        canvas, ctx = C.body(s, t, n)
        fr = C.Frame(canvas, ctx)
    if getattr(fr.ctx, "black", False):
        return fr.content
    r, shell = retract_at(t)
    img = fr.content.convert("RGBA")
    if fr.over is not None and fr.under:
        img.alpha_composite(fr.over)
    shift = slide_at(t) if fr.her_shift is None else fr.her_shift
    if s.fn.__name__ in HIDE_HER and fr.her_shift is None and fr.her_alpha >= 0.999:
        shift = 1.0  # she does not exist yet / is not on screen in this shot (a cut can still bring her in)
    if fr.her_alpha > 0.01 and shift < 0.999:
        layer = her(t, n, fr.glow, 1 - r)
        if fr.her_alpha < 0.999:
            layer = tk.scale_alpha(layer, fr.her_alpha)
        img.alpha_composite(layer, (-int(round(410 * shift)), 0)) if shift > 0.001 else img.alpha_composite(layer)
    ov = OVERLAY.get(i) or OVERLAY.get(s.fn.__name__)
    if ov is not None:
        layer = ov(t, n)
        if layer is not None:
            img.alpha_composite(layer)
    if fr.over is not None and not fr.under:
        img.alpha_composite(fr.over)
    img = kit.chrome(img, t, fr.ctx, r, shell)
    return engine.post(img.convert("RGB"), None)


# ---------------------------------------------------------------- output

def stills(times, tag="stills"):
    if HER == "grok":
        grok.prepare()
    out = ROOT / tag
    out.mkdir(exist_ok=True)
    for t in times:
        n = round(t * FPS)
        t0 = time.time()
        frame(n).save(out / f"{n / FPS:07.3f}.png")
        print(f"{n / FPS:.3f}s  {engine.shot_at(n / FPS).fn.__name__}  {time.time() - t0:.2f}s", flush=True)


def worker(k, a, b, seg):
    seg = Path(seg)
    seg.mkdir(exist_ok=True)
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "pipe:0", "-an", "-c:v", "libx264", "-threads", "1", "-preset", "fast", "-crf", "17",
           "-pix_fmt", "yuv420p", str(seg / f"seg_{k:02d}.mp4")]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for n in range(a, b):
            p.stdin.write(frame(n).tobytes())
            if (n - a) % 96 == 0:
                print(f"worker {k}: {n - a}/{b - a}", flush=True)
        p.stdin.close()
        assert p.wait(timeout=120) == 0
    finally:
        if p.poll() is None:
            p.kill()


def run(cmd):
    r = subprocess.run(cmd, capture_output=True)
    assert r.returncode == 0, r.stderr.decode(errors="replace")[-2000:]


def render(t0: float, t1: float, tag: str, workers: int = 8, compare: bool = True) -> Path:
    """Render [t0, t1) with the song's audio to <tag>.mp4, plus a side-by-side with v1 and per-cut strips."""
    if HER == "grok":
        grok.prepare()
    n0, n1 = round(t0 * FPS), round(t1 * FPS)
    seg = ROOT / f"segments_{tag}"
    bounds = [n0 + (n1 - n0) * k // workers for k in range(workers + 1)]
    procs = []
    for k in range(workers):
        cmd = [sys.executable, "-B", "-X", "utf8", str(Path(__file__).resolve()), "--worker", str(k),
               str(bounds[k]), str(bounds[k + 1]), str(seg)]
        procs.append(subprocess.Popen(cmd, cwd=str(ROOT), env=dict(os.environ)))
    for p in procs:
        assert p.wait() == 0, "worker failed"
    (seg / "list.txt").write_text("".join(f"file 'seg_{k:02d}.mp4'\n" for k in range(workers)), encoding="utf-8")
    dur = (n1 - n0) / FPS
    out = ROOT / f"{tag}.mp4"
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(seg / "list.txt"),
         "-ss", f"{n0 / FPS:.4f}", "-i", str(engine.AUDIO), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
         "-c:a", "aac", "-b:a", "192k", "-t", f"{dur:.4f}", "-movflags", "+faststart", str(out)])
    if compare:
        font = r"fontfile='C\:/Windows/Fonts/consolab.ttf'"
        old = kit.PROJECT / "continuity_full_v1/tui_pv_full_continuity.mp4"
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{n0 / FPS:.4f}", "-t", f"{dur:.4f}", "-i", str(old), "-i", str(out),
             "-filter_complex",
             f"[0:v]scale=960:540,drawtext={font}:text='v1':x=12:y=10:fontsize=26:fontcolor=white[a];"
             f"[1:v]scale=960:540,drawtext={font}:text='v2':x=12:y=10:fontsize=26:fontcolor=white[b];[a][b]hstack",
             "-map", "1:a", "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "copy",
             "-movflags", "+faststart", str(ROOT / f"compare_{tag}.mp4")])
    strips(out, t0, t1, tag)
    return out


def strips(video, t0, t1, tag):
    out = ROOT / f"strips_{tag}"
    out.mkdir(exist_ok=True)
    rows = []
    for i in range(1, len(ALL)):
        T = ALL[i].start
        if not t0 < T < t1:
            continue
        a, b = ALL[i - 1], ALL[i]
        name = f"cut_{i:02d}_{T:07.2f}_{a.fn.__name__[5:]}__{b.fn.__name__[5:]}.png"
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0.0, T - 0.6 - t0):.3f}", "-i", str(video),
             "-t", "1.25", "-vf", "fps=12,scale=384:216,tile=5x3", "-frames:v", "1", str(out / name)])
        cls = CUT_CLASSES.get(i)
        rows.append(dict(cut=i, t=round(T, 3), cls=cls.__name__ if cls else None,
                         doc=(cls.__doc__ or "").strip() if cls else None, strip=name))
    (ROOT / f"cuts_{tag}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stills")
    ap.add_argument("--stills-dir", default="stills")
    ap.add_argument("--range", nargs=2, type=float)
    ap.add_argument("--tag")
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--worker", nargs=4)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--no-compare", action="store_true")
    a = ap.parse_args()
    if a.worker:
        worker(int(a.worker[0]), int(a.worker[1]), int(a.worker[2]), a.worker[3])
    elif a.stills:
        stills([float(x) for x in a.stills.split(",")], a.stills_dir)
    elif a.range:
        render(a.range[0], a.range[1], a.tag or f"range_{a.range[0]:.0f}_{a.range[1]:.0f}", a.workers,
               not a.no_compare)
    elif a.full:
        render(0.0, engine.END_T, a.tag or ("tui_pv_full_h3" if HER == "h3" else "tui_pv_full_v2"), a.workers,
               not a.no_compare)
