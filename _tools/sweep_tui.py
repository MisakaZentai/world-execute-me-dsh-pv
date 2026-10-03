"""Sweep the terminal player over the whole song at several window sizes.

In-process, so it can afford every frame at the reference size. Reports, per size:
  * any exception (with the frame that raised it)
  * cells the draw tried to put outside a screen that exists (Screen guards these, so the count
    stays 0; a nonzero count would mean the guard is what is hiding an overflow)
  * the slowest frame, against the 41.7 ms a 24 fps frame has
  * whether her pane is on screen, sampled at the shots that decide it
"""
from __future__ import annotations

import gc
import io
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "_tools"))

import tui_live as T  # noqa: E402

# the live player turns the cyclic collector off (tui_live.main): a gen-2 pass is a 20-27 ms hole in
# a 33 ms frame, which without this would be charged to whichever frame happened to trigger it and
# read as a slow draw. Measure the renderer, not the collector.
gc.disable()

SIZES = [(197, 52), (240, 70), (160, 44), (120, 34), (100, 28), (96, 30), (80, 22), (60, 20)]
STEP = {197: 1, 240: 5, 160: 3, 120: 3, 100: 3, 96: 3, 80: 7, 60: 7}

d = T.Data()
print("loading the film's shot table...")
t0 = time.time()
eng = T.Engine()
print(f"  {time.time() - t0:.1f} s")

# --render auto turns her into a solid portrait on the parts of the song that are about her, and
# wherever the system has gone red. The ranges are named by their first and last lyric, so a
# mistyped line is a silent no-match - and a *dropped* range slides every later one onto the wrong
# part of the song. Fail loudly instead of drawing the wrong thing.
unresolved = T.FP.figure_unresolved()
spans = T.FP.figure_spans()
if unresolved or len(spans) != len(T.FP.FIGURE_LINES):
    bad_climax = True
    print(f"\n!! figure ranges unresolved: {unresolved}")
else:
    bad_climax = False
    print("\nthe story `--render auto` tells (per shot):")
    for (first, last), (a, b) in zip(T.FP.FIGURE_LINES, spans):
        print(f"    {a:7.2f}-{b:7.2f}  {b - a:5.1f}s   solid blue: {first} ... {last}")
    print(f"    {T.FP.chapter_start('EXECUTION'):7.2f}            solid red: 07 EXECUTION, "
          f"alert_own=err")
    print(f"    {T.FP.chapter_start('EVAL'):7.2f}            red characters: 08 EVAL: LOVE onward")
    last_her = next((e for e in reversed(eng.table) if e["her"]), None)
    if last_her:
        print(f"    {last_her['start']:7.2f}-{last_her['end']:7.2f}  solid blue: the last shot she "
              f"is in ({last_her['name']})")
    from collections import Counter
    tally = Counter(T.her_style(e) for e in eng.table if e["her"])
    tot = sum(e["end"] - e["start"] for e in eng.table)
    for (how, tint), n in sorted(tally.items()):
        secs = sum(e["end"] - e["start"] for e in eng.table
                   if e["her"] and T.her_style(e) == (how, tint))
        print(f"    -> {how}/{tint}: {n} shots, {secs:.1f} s of {tot:.1f} s ({100 * secs / tot:.0f} %)")

# what the film does with her pane, per shot, straight out of the table
her_shots = [e for e in eng.table if e["her"]]
noher = [e for e in eng.table if not e["her"]]
tot = sum(e["end"] - e["start"] for e in eng.table)
print(f"\nher pane drawn in {len(her_shots)}/{len(eng.table)} shots "
      f"= {sum(e['end'] - e['start'] for e in her_shots):.1f} s / {tot:.1f} s "
      f"({100 * sum(e['end'] - e['start'] for e in her_shots) / tot:.1f} %)")
print("her absent: " + ", ".join(f"{e['name']}({e['start']:.1f})" for e in noher))

# What the left pane's upper box holds over the whole song, by the rule `draw_body` applies: the
# film's dsh window when it is on screen, the lone caret over GONE..BACK, her figure on the shots
# `her_style` gives a solid portrait, and nothing when the pane is too short for either.
from collections import Counter  # noqa: E402
pane = Counter()
psec = Counter()
for e in eng.table:
    mid = (e["start"] + e["end"]) / 2
    dur = e["end"] - e["start"]
    if T.FP.dsh_gone(mid):
        k = "caret  "
    elif T.FP.dsh_inside(mid) and T.her_style(e)[0] != "half":
        k = "window "
    elif e["her"]:
        k = "her    "
    else:
        k = "empty  "
    pane[k] += 1
    psec[k] += dur
print("\nleft pane, by what is in it (per shot, sampled at the shot's middle):")
for k, n in sorted(pane.items()):
    print(f"    {k} {n:3d} shots  {psec[k]:6.1f} s of {tot:.1f} s ({100 * psec[k] / tot:2.0f} %)")

print(f"\n{'size':>9} {'frames':>7} {'mean':>9} {'p95':>9} {'worst':>9} {'off':>5}  errors")
bad = 0
for cols, rows in SIZES:
    s = T.Screen(cols, rows)
    out = io.StringIO()
    step = STEP[cols]
    times = []
    n = 0
    off = 0
    err = None
    for k in range(0, round(T.END * 24), step):
        t = k / 24
        t1 = time.perf_counter()
        try:
            T.draw(s, d, eng, t, True, 24.0)
        except Exception:
            err = f"t={t:.3f}\n" + traceback.format_exc()
            break
        times.append((time.perf_counter() - t1) * 1000)
        # every cell the draw wrote must be printable; None would mean a missed blank
        off += sum(1 for row in s.buf for c in row if c is None or not isinstance(c[0], str))
        s.render_diff(out)
        n += 1
    if err:
        bad += 1
        print(f"{cols:>4}x{rows:<4} {n:>7}  FAILED\n{err}")
    else:
        ts = sorted(times)
        mean = sum(ts) / len(ts)
        p95 = ts[int(len(ts) * 0.95)]
        print(f"{cols:>4}x{rows:<4} {n:>7} {mean:>8.2f}ms {p95:>8.2f}ms {ts[-1]:>8.2f}ms {off:>5}  "
              f"{'ok' if ts[-1] < 41.7 else 'SLOW'}")

# the left pane's upper box, on the shots that decide it. Two things can be in it now: her figure
# (`/dev/me`), or the film's own dsh window (`dsh web`), which is what the film itself puts there from
# 5.0 s to the end - so a shot where the film draws her and the box holds the window is the film's
# answer, not a regression. What would be a regression is an *empty* box on a shot the film draws her.
print("\nleft pane presence (her '/dev/me', or the film's 'dsh web'), sampled per shot:")
FULL_BLEED = {"shot_exec_hit", "shot_count", "shot_last_execution", "shot_black",
              "shot_flood", "shot_collapse"}   # the last two take the whole screen, no pane at all
probes = [("shot_power", 0.5), ("shot_protection", 2.4), ("shot_pieces", 4.4), ("shot_infinity", 40.8),
          ("shot_unite", 55.4), ("shot_deeply", 57.6), ("shot_simulations", 61.5), ("shot_strange", 72.5),
          ("shot_erase", 120.7), ("shot_moe_dense", 136.3), ("shot_flood", 145.9),
          ("shot_collapse", 175.5), ("shot_whale_fall", 199.5), ("shot_have_you_back", 170.2),
          ("shot_grpo", 177.5), ("shot_me_trapped", 189.6)]
s = T.Screen(197, 52)
print(f"  {'shot':<22} {'t':>7}  film  hers  win")
wrong = 0
for name, t in probes:
    ent = eng.entry_at(t)
    # play the last second up to t: a jump *is* a cut, and the reveal the cut starts holds the old
    # picture in the box for half a second, so a probe drawn at a jump would read the previous
    # probe's pane.
    for k in range(24):
        T.draw(s, d, eng, max(0.0, t - 1 + k / 24), True, 24.0)
    dump = s.text_dump()
    box = "dsh web" in dump
    hers = "/dev/me" in dump
    film_her = bool(ent and ent["her"])
    film_win = T.FP.dsh_inside(t) and not T.FP.dsh_gone(t)
    if name in FULL_BLEED:
        flag = "   n/a (TUI draws this shot full-bleed)"
    elif film_her and not (box or hers):
        flag = "   <-- MISMATCH: the film draws her and the box is empty"
        wrong += 1
    elif box and not (film_win or film_her or T.FP.dsh_gone(t)):
        flag = "   <-- MISMATCH: the film has neither a window nor her here"
        wrong += 1
    else:
        flag = ""
    print(f"  {name:<22} {t:>7.2f}  {str(film_her):>5} {str(hers):>5} {str(box):>5}{flag}")
print(f"\n{'OK' if bad == 0 and wrong == 0 and not bad_climax else 'PROBLEMS: %d crashes, %d her mismatches, %d unresolved climax ranges' % (bad, wrong, len(unresolved))}")
