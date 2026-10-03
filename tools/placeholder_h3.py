"""Stand-in dancer frames: write the dance takes the film draws her from, made from the whale maid art.

The right-hand side of the film (point clouds, sample grids, feature maps, heat maps, the glyph figure) is drawn from
frame caches of a dancing figure. The film's own takes are not part of this repository (see NOTICE.md). This tool
writes stand-ins with exactly the same take names, frame counts and file names, so the film renders unchanged:
the maid from film/third_party_references/whale_maid_expanded_20260926/maid-left.webp, standing, swaying gently
from side to side once a bar and dipping slightly on every beat of the song.

    python tools/placeholder_h3.py              write every take that is missing
    python tools/placeholder_h3.py --force      also rewrite the takes this tool wrote before
    python tools/placeholder_h3.py --workers 4  processes for tracing (default: up to 8)

Takes that are already complete are left alone, so you can drop in your own takes (same format) and only the
missing ones are filled in. Takes this tool wrote are listed in <cache>/_standin.json; takes it did not write are
never overwritten, even with --force.

Caches and format (data/h3_takes.json lists every take, its frame count and its image indices):

    film/mmd_motion_eval_20260927/pv_cache/                            read by pv_full.py (entries named mmd_<take>)
    film/tui_pv_world_execute_20260926/continuity_full_v2/cache/h3_full_v1/   read by h3_full.py (PLAN names)

    <cache>/<take>.json            a list with one entry per frame of the take (24 fps; h3_full.py expects 124 or
                                   192): {"frame": i, "art": [...], "shade": [...], "part": [...]}, each a list of
                                   45 strings of 70 characters, one character per glyph cell: the glyph (art), the
                                   cell's brightness 0-7 (shade), the body part ('b', or ' ' for an empty cell)
    <cache>/rgba/<take>/NNN.png    frame NNN (000, 001, ...) as a 420x540 RGBA image on a transparent background:
                                   the figure standing on y 528, about 408 px tall, the shoes centred on x 228. The
                                   film crops it with the boxes full (0, 60, 420, 540), upper (0, 70, 420, 350),
                                   bust (40, 70, 390, 310) and face (80, 80, 335, 250)

The grids are traced from the images with the film's own tracer (continuity_full_v2/grok_rig.py: feet, matte and
trace on the figure composited over white, one glyph cell per 6x12 px), exactly as the original takes were.

How the stand-in moves: one bar (four beats) is rendered as a loop of LOOP frames and every frame of every take
reuses the loop frame for its bar phase. The phase comes from the song time the take plays at in the film (read
from pv_full.py's T0 and h3_full.py's PLAN), on the song's beat grid (beat k at FIRST_BEAT + k * BEAT seconds), so
the sway and the dips land on the music. The frames written are derived from the whale maid art and share its
licence, CC BY-NC-SA 4.0 (see NOTICE.md).
"""
from __future__ import annotations

import argparse
import ast
import json
import math
import os
import shutil
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
FILM = ROOT / "film"
V2 = FILM / "tui_pv_world_execute_20260926" / "continuity_full_v2"
PV_FULL = FILM / "mmd_motion_eval_20260927" / "pv_full.py"
ART = FILM / "third_party_references" / "whale_maid_expanded_20260926" / "maid-left.webp"
TAKES = ROOT / "data" / "h3_takes.json"
MARK = "_standin.json"                  # in each cache folder: the takes this tool wrote
WORK = V2 / "cache" / "_standin_loop"   # the rendered loop, while the takes are written

FPS = 24
FIRST_BEAT = 0.1807                     # the song's beat grid: beat k at FIRST_BEAT + k * BEAT seconds
BEAT = 60 / 130
LOOP = 44                               # frames per bar in the loop (a bar is 4 beats = 44.3 frames at 24 fps)
SIZE = (420, 540)                       # the take canvas
FOOT_Y, HEIGHT, AXIS_X = 528, 408, 228  # feet line, standing height, shoe centre
SWAY = 8.0                              # px the top of her head sways to each side, once a bar
DIP = 0.014                             # how much she sinks on each beat, as a fraction of her height
STRIP = 6                               # rows per strip of the warp mesh


# ---------------------------------------------------------------- the loop

def _tracer():
    if str(V2) not in sys.path:
        sys.path.insert(0, str(V2))
    import grok_rig
    grok_rig.GROWS = 45                 # the take grid is 45 rows (grok_rig's default is the rig's 42)
    return grok_rig


def _on_white(im: Image.Image) -> Image.Image:
    out = Image.new("RGB", im.size, "white")
    out.paste(im, (0, 0), im)
    return out


@lru_cache(None)
def figure() -> Image.Image:
    """The art fitted into the take canvas like the original takes: standing height HEIGHT from the feet line to the
    top of the figure, the shoes (the tracer's feet()) centred on AXIS_X, the feet on FOOT_Y."""
    gr = _tracer()
    art = Image.open(ART).convert("RGBA")
    top = art.getchannel("A").point(lambda v: 255 if v >= 100 else 0).getbbox()[1]
    x0, x1, foot = gr.feet(_on_white(art))
    scale = HEIGHT / (foot - top)
    small = art.resize((round(art.width * scale), round(art.height * scale)), Image.Resampling.LANCZOS)
    out = Image.new("RGBA", SIZE)
    out.alpha_composite(small, (round(AXIS_X - (x0 + x1) / 2 * scale), round(FOOT_Y - foot * scale)))
    return out


def motion(phase: float) -> tuple[float, float]:
    """(sway px at the top of her head, dip as a fraction of her height) at a bar phase in [0, 1)."""
    beat = (4 * phase) % 1
    return SWAY * math.sin(2 * math.pi * phase), DIP * (0.5 + 0.5 * math.cos(2 * math.pi * beat)) ** 2


def pose(phase: float) -> Image.Image:
    """The figure bent by motion(phase), feet planted: every row above the feet shifts sideways by the sway times
    (height above the feet / HEIGHT) ** 1.5, and the body sinks towards the feet by the dip (widening by half as
    much), as a piecewise-linear mesh of STRIP-row strips."""
    sway, dip = motion(phase)
    w, h = SIZE

    def src(x, y):  # output point -> source point
        ys = FOOT_Y - (FOOT_Y - y) / (1 - dip)
        u = max(0.0, (FOOT_Y - ys) / HEIGHT)
        return AXIS_X + (x - AXIS_X - sway * u ** 1.5) / (1 + dip / 2), ys

    mesh = []
    for y0 in range(0, h, STRIP):
        y1 = min(h, y0 + STRIP)
        mesh.append(((0, y0, w, y1), (*src(0, y0), *src(0, y1), *src(w, y1), *src(w, y0))))
    return figure().transform(SIZE, Image.Transform.MESH, mesh, Image.Resampling.BICUBIC)


def render(task) -> dict:
    """Loop frame j: the posed figure over white, matted and traced as the original takes were (grok_rig feet,
    matte and trace; every figure pixel is part 'b'). Saves the RGBA image, returns the grid."""
    j, folder = task
    gr = _tracer()
    rgb = _on_white(pose(j / LOOP))
    alpha = gr.matte(rgb, gr.feet(rgb)[2])
    black = Image.new("RGB", SIZE)
    im = Image.composite(rgb, black, alpha)   # nothing but black under the transparent background
    im.putalpha(alpha)
    im.save(Path(folder) / f"{j:03}.png")
    fr = gr.trace(im, ["b" if a >= 100 else "" for a in alpha.tobytes()], [(-100, -100, ":")])
    return dict(art=fr.art, shade=fr.shade, part=fr.part)


# ---------------------------------------------------------------- when each take plays

def _literal(path: Path, name: str):
    for node in ast.parse(path.read_text(encoding="utf8")).body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise KeyError(name)


def anchors() -> dict:
    """take -> (song time of its source second a, a, song seconds per source second), from the film's code: the
    pv_full takes play at T0[take] + i / FPS; an h3_full take is anchored on the PLAN entry the film shows most of
    (the stretches pv_full keeps), with that entry's speed. Anything unreadable falls back to 'starts on a beat'."""
    out = {}
    try:
        for take, t0 in _literal(PV_FULL, "T0").items():
            out[take] = (t0, 0.0, 1.0)
        keep = [(s, e) for s, e, kind, *_ in _literal(PV_FULL, "TIMELINE") if kind == "keep"]
        best = {}
        for start, end, name, a, b, mode in _literal(V2 / "h3_full.py", "PLAN"):
            shown = sum(max(0.0, min(end, e) - max(start, s)) for s, e in keep)
            rate = (16 * BEAT if mode == "loop" else end - start) / (b - a)
            if name not in best or shown > best[name][0]:
                best[name] = (shown, (start, a, rate))
        out.update({name: v for name, (_, v) in best.items()})
    except (OSError, SyntaxError, KeyError, ValueError) as e:
        print(f"note: could not read the film's timeline ({e}); the stand-in keeps its own beat")
    return out


def phase(anchor, i: int) -> float:
    t0, a, rate = anchor or (FIRST_BEAT, 0.0, 1.0)
    t = t0 + (i / FPS - a) * rate
    return ((t - FIRST_BEAT) / BEAT / 4) % 1


# ---------------------------------------------------------------- the caches

def indices(runs) -> list[int]:
    return [i for a, b in runs for i in range(a, b + 1)]


def state(folder: Path, take: str, spec: dict, ours: set) -> str:
    grid = folder / f"{take}.json"
    pngs = [folder / "rgba" / take / f"{i:03}.png" for i in indices(spec["rgba"])]
    have = [p.exists() for p in pngs]
    if grid.exists() and all(have):
        return "stand-in" if take in ours else "present"
    if take in ours or (not grid.exists() and not any(have)):
        return "missing"
    return "partial"


def write_take(folder: Path, take: str, spec: dict, anchor, loop_grids: list, loop_dir: Path) -> None:
    rgba = folder / "rgba" / take
    rgba.mkdir(parents=True, exist_ok=True)
    pick = lambda i: round(phase(anchor, i) * LOOP) % LOOP  # noqa: E731
    grids = [dict(frame=i, **loop_grids[pick(i)]) for i in range(spec["frames"])]
    (folder / f"{take}.json").write_text(json.dumps(grids), encoding="utf-8")
    for i in indices(spec["rgba"]):
        target = rgba / f"{i:03}.png"
        target.unlink(missing_ok=True)
        source = loop_dir / f"{pick(i):03}.png"
        try:
            os.link(source, target)       # the loop frames are shared: hard links where the disk allows
        except OSError:
            shutil.copyfile(source, target)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--force", action="store_true", help="also rewrite the takes this tool wrote before")
    ap.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    args = ap.parse_args()
    started = time.time()
    caches = json.loads(TAKES.read_text(encoding="utf-8"))["caches"]

    todo, counts, partial = [], {"present": 0, "stand-in": 0}, []
    for cache in caches:
        folder = ROOT / cache["folder"]
        mark = folder / MARK
        ours = set(json.loads(mark.read_text(encoding="utf-8"))["takes"]) if mark.exists() else set()
        for take, spec in cache["takes"].items():
            s = state(folder, take, spec, ours)
            if s == "missing" or (s == "stand-in" and args.force):
                todo.append((folder, take, spec))
            elif s == "partial":
                partial.append(f"{cache['folder']}/{take}")
            else:
                counts[s] += 1
    total = sum(len(c["takes"]) for c in caches)
    if not todo:
        print(f"stand-in dancer: all {total} takes present ({counts['present']} yours, {counts['stand-in']} "
              f"stand-in), nothing to do")
    else:
        if WORK.exists():
            shutil.rmtree(WORK)
        WORK.mkdir(parents=True)
        with ProcessPoolExecutor(max_workers=max(1, args.workers)) as pool:
            loop = list(pool.map(render, [(j, str(WORK)) for j in range(LOOP)]))
        looped = time.time() - started
        when = anchors()
        written = {}
        for folder, take, spec in todo:
            write_take(folder, take, spec, when.get(take), loop, WORK)
            written.setdefault(folder, []).append(take)
        for folder, takes in written.items():
            mark = folder / MARK
            old = json.loads(mark.read_text(encoding="utf-8"))["takes"] if mark.exists() else []
            mark.write_text(json.dumps(dict(
                about="Stand-in takes written by tools/placeholder_h3.py (derived from the whale maid art, "
                      "CC BY-NC-SA 4.0). Delete a take's files and its name here to replace it with your own.",
                takes=sorted(set(old) | set(takes))), indent=1) + "\n", encoding="utf-8")
        shutil.rmtree(WORK)
        frames = sum(spec["frames"] for _, _, spec in todo)
        print(f"stand-in dancer: wrote {len(todo)} of {total} takes ({frames} frames) from a {LOOP}-frame loop "
              f"(traced in {looped:.0f} s with {args.workers} processes); left {counts['present']} of yours and "
              f"{counts['stand-in']} earlier stand-ins alone; {time.time() - started:.0f} s in all")
    if partial:
        print("incomplete takes (some files there, not written by this tool; left as they are): " + ", ".join(partial))
        print("complete them, or delete their files to get stand-ins")
        sys.exit(1)


if __name__ == "__main__":
    main()
