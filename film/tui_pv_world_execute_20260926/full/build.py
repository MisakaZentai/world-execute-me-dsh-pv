"""Registers every section's shots, fills any not-yet-written span with a placeholder, and renders.

Usage (from this folder):
  python build.py --stills 3,20,35,65          # test frames -> stills/<palette>_<t>.png
  python build.py --render [--t0 54 --t1 74]   # full song (or a range) -> tui_pv_full[_range].mp4
Palette: set TUI_PALETTE=amber|deepsea|phosphor.
"""

from __future__ import annotations

import argparse
import importlib
import math
from pathlib import Path

import engine
from engine import END_T, FPS, SHOTS, Ctx, add, chapter_at, finalize, render_frame, render_video
from tuikit import F_HEAD, F_MONO, PALETTE, amb, box, font

HERE = Path(__file__).resolve().parent
SECTIONS = ["sec_intro", "sec_verse1", "sec_chorus1", "sec_verse2", "sec_chorus2", "sec_final", "sec_outro"]


def shot_placeholder(c: Ctx) -> None:
    c.ops = ["TODO"]
    box(c.d, 24, 56, 1164, 604, f"{c.chapter}  (not written yet)", 0.4, spinner=c.t)
    c.text((60, 300), c.chapter, font(F_HEAD, 48), amb(0.5))
    c.text((60, 370), f"t = {c.t:6.2f}", font(F_MONO, 20), amb(0.4))


def register() -> None:
    if SHOTS:
        return
    for name in SECTIONS:
        importlib.import_module(name).build()
    spans = sorted((s.start, s.end) for s in SHOTS)
    t, gaps = 0.0, []
    for a, b in spans:
        if a > t + 1e-6:
            gaps.append((t, a))
        t = max(t, b)
    if t < END_T - 1e-6:
        gaps.append((t, END_T))
    for a, b in gaps:
        add(a, b, shot_placeholder)
    finalize()


register()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stills", type=str, default="")
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--t0", type=float, default=0.0)
    ap.add_argument("--t1", type=float, default=None)
    ap.add_argument("--workers", type=int, default=7)
    a = ap.parse_args()
    if a.stills:
        out = HERE / "stills"
        out.mkdir(exist_ok=True)
        for t in [float(x) for x in a.stills.split(",")]:
            tag = "_focus" if engine.FOCUS else "_anchor" if engine.ANCHOR else ""
            p = out / f"{PALETTE}{tag}_{t:06.2f}.png"
            render_frame(t, None, int(t * FPS)).save(p)
            print(p)
    if a.render:
        tag = "" if a.t0 == 0 and a.t1 is None else f"_{a.t0:05.1f}-{(a.t1 or END_T):05.1f}"
        mode = "_focus" if engine.FOCUS else "_anchor" if engine.ANCHOR else ""
        out = HERE / f"tui_pv_full_{PALETTE}{mode}{tag}.mp4"
        print(render_video(out, a.workers, a.t0, a.t1))


if __name__ == "__main__":
    main()
