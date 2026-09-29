"""The v2 film (V2_HER=h3) with the MMD choreography: every H3 window of choreo_plan.json in h3_full.PLAN, in
memory only (no production file is edited).

  python pv_full.py plan                 print the timeline
  python pv_full.py render [workers]     tui_pv_full_h3_mmd.mp4 (song audio muxed in)
  python pv_full.py range <t0> <t1> out  one stretch

Takes are the traced windows in pv_cache/<name>.json (pv_pilot.py trace). Kinds of timeline entry:
  direct  a window plays at its own song time
  reuse   a window replays on the same melody elsewhere (chorus 2 and the red chorus replay chorus 1; the EXECUTION
          flashes replay the pilot)
  keep    the existing h3_full entry: the author-approved turn / reach / downbeat / release, the boot acting and
          the whale fall, and short stretches where she is hidden
"""
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
import json
import os
from pathlib import Path
import subprocess
import sys

from PIL import Image

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
CACHE = OUT / "pv_cache"
V2 = Path(__file__).resolve().parents[1].joinpath("tui_pv_world_execute_20260926/continuity_full_v2")
SONG = Path(__file__).resolve().parents[2].joinpath("input", "song.mp3")
sys.path.insert(0, str(V2))

T0 = {"mmd01": 14.90, "W0": 9.95, "W2a": 29.60, "W2b": 36.70, "W3": 44.37, "W4": 59.14, "W5": 73.91, "W6": 88.68,
      "W7": 118.21, "W8": 138.00, "W10": 177.35}
# (start, end, kind, take, original song time the take is taken from - reuse only)
TIMELINE = [
    (0.0, 10.0, "keep", None, None),
    (10.0, 14.90, "direct", "W0", None),
    (14.90, 29.719, "direct", "mmd01", None),
    (29.719, 33.292, "direct", "W2a", None),
    (33.292, 36.851, "keep", None, None),          # approved turn (circle)
    (36.851, 44.488, "direct", "W2b", None),
    (44.488, 59.258, "direct", "W3", None),
    (59.258, 74.027, "direct", "W4", None),
    (74.027, 88.796, "direct", "W5", None),
    (88.796, 103.565, "direct", "W6", None),
    (103.565, 110.416, "reuse", "W4", 59.258),     # chorus 2 = chorus 1
    (110.416, 118.335, "keep", None, None),        # approved reach, then the isolation hold
    (118.335, 133.104, "direct", "W7", None),
    (133.104, 138.0, "keep", None, None),          # she is hidden 135-138.5
    (138.0, 146.0, "direct", "W8", None),
    (146.0, 147.873, "keep", None, None),          # hidden
    (147.873, 162.642, "reuse", "mmd01", 14.950),  # EXECUTION flashes replay the pilot dance
    (162.642, 164.125, "reuse", "W4", 59.258),     # red chorus = chorus 1 ...
    (164.125, 166.792, "keep", None, None),        # ... with the approved downbeat
    (166.792, 177.411, "reuse", "W4", 63.408),
    (177.411, 188.167, "direct", "W10", None),
    (188.167, 212.0, "keep", None, None),          # approved release, whale fall
]


def build(orig):
    plan = []
    for s, e, kind, take, src in TIMELINE:
        if kind == "keep":
            for p in orig:
                ps, pe, n, sa, sb, mode = p
                if pe <= s or ps >= e:
                    continue
                a, b = max(ps, s), min(pe, e)
                if mode == "loop":
                    plan.append((a, b, n, sa, sb, mode))
                else:
                    f = lambda t: sa + (sb - sa) * (t - ps) / (pe - ps)
                    plan.append((a, b, n, f(a) if a > ps else sa, f(b) if b < pe else sb, mode))
        else:
            base = (s if kind == "direct" else src) - T0[take]
            plan.append((s, e, f"mmd_{take}", base, base + (e - s), "once"))
    for p, q in zip(plan, plan[1:]):
        assert abs(p[1] - q[0]) < 1e-9, (p, q)
    return plan


def install():
    os.environ["V2_HER"] = "h3"
    os.environ.pop("V2_SECTIONS", None)
    import v2
    import h3_full as h3
    import rig
    orig_grids, orig_rgba = h3.grids, h3.rgba

    @lru_cache(None)
    def grids(n):
        if n.startswith("mmd_"):
            data = json.loads((CACHE / f"{n[4:]}.json").read_text(encoding="utf-8"))
            return [rig.Frame(x["art"], x["shade"], x["part"]) for x in data]
        return orig_grids(n)

    def rgba(n, i):
        if n.startswith("mmd_"):
            return Image.open(CACHE / "rgba" / n[4:] / f"{i:03}.png").convert("RGBA")
        return orig_rgba(n, i)

    h3.grids, h3.rgba = grids, rgba
    h3.PLAN[:] = build(list(h3.PLAN))
    # 'once' sources are clamped to the take; a take must reach the end of its entry
    for s, e, n, sa, sb, mode in h3.PLAN:
        if n.startswith("mmd_"):
            assert sb * 24 <= len(grids(n)) + 1, (n, s, e, sb, len(grids(n)))
    return v2, h3


def _chunk(task):
    k, a, b, folder = task
    v2, h3 = install()
    target = Path(folder) / f"{k:02}.mp4"
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1280x720", "-r", "24",
           "-i", "pipe:0", "-an", "-c:v", "libx264", "-threads", "2", "-preset", "fast", "-crf", "17",
           "-pix_fmt", "yuv420p", str(target)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    v2.frame(a)
    for n in range(a, b):
        p.stdin.write(v2.frame(n).tobytes())
    p.stdin.close()
    assert p.wait() == 0
    return str(target)


def render(n0, n1, out, workers=4):
    folder = OUT / "pv_segments"
    folder.mkdir(exist_ok=True)
    parts = max(1, min(workers * 3, (n1 - n0) // 120))
    bounds = [n0 + (n1 - n0) * k // parts for k in range(parts + 1)]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        files = list(pool.map(_chunk, [(k, bounds[k], bounds[k + 1], str(folder)) for k in range(parts)]))
    lst = folder / "list.txt"
    lst.write_text("".join(f"file '{Path(f).as_posix()}'\n" for f in files), encoding="utf-8")
    subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                           "-ss", f"{n0 / 24:.4f}", "-t", f"{(n1 - n0) / 24:.4f}", "-i", str(SONG),
                           "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                           "-movflags", "+faststart", str(OUT / out)])
    for f in files:
        Path(f).unlink()
    print("RENDERED", OUT / out)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "plan":
        _, h3 = install()
        for p in h3.PLAN:
            print(f"{p[0]:8.3f} {p[1]:8.3f}  {p[2]:10s} {p[3]:7.3f} {p[4]:7.3f} {p[5]}")
    elif cmd == "render":
        render(0, 5064, "tui_pv_full_h3_mmd.mp4", int(sys.argv[2]) if len(sys.argv) > 2 else 4)
    elif cmd == "range":
        render(round(float(sys.argv[2]) * 24), round(float(sys.argv[3]) * 24), sys.argv[4])
