"""A real ANSI terminal player for the world.execute(me); PV - characters, not pixels.

    终端实时版 by 林原林海. The film, its 97 shots and every number this player reads are
    MisakaZentai's open-source rebuild (MIT); the terminal player - this file, `film_panels.py`,
    `her_glyphs.py`, `pv_audio.py`, `dsh_text.py`, `tui_shot.py` - is by 林原林海. Both halves of
    the attribution chain are printed by `--credits`, and are also in the package README.

The film itself is raster: tuikit.py draws monospace glyphs onto a 1280x720 PIL canvas
and ffmpeg turns the frames into an mp4. That picture cannot be squeezed into a terminal
(1280x720 = 921,600 pixels against roughly 200x55 = 11,000 cells), so this does not try.
Instead it rebuilds the parts of the film that were always data - as genuine terminal output,
from the film's own numbers:

    wave_rms_1ms.npy       211,912 float32, one per millisecond of the real song
    audio_features.json    loud / 7 bands / kick / flux / cent, 10,180 rows
    word_timeline.json     98 lines, word by word, from build.py lyrics
    film_panels.py         everything below, read back out of the film's own source

the header waveform, the lyric band and the token chips, the seven feature bands, her pane
(the same Sobel-into-glyphs algorithm the film uses, at terminal resolution) and the ops
ticker all run the whole way through. On top of that the player shows the drawings that were
always terminal text anyway, on the shots that own them:

    shot_power, shot_protection   the POST log, printing at the film's own times (0.84 s +)
    shot_begin_sim                the 3-2-1 countdown, then RUN / simulation: running
    shot_corpus                   the corpus river, 20 rows walking sec_intro.CORPUS
    shot_losscurve                train/loss dot chart, lr schedule, tokens-seen counter
    shot_blind                    the 12x12 causal mask, sweeping from beat 103
    shot_memory_ls, shot_erase    ls -la ~/memory/you/, the eight files she digs up
    shot_exec_hit (x13)           the five EXECUTION layouts - wordmark, kill log,
                                  EXECUTE-in-EXECUTE, ps -ef, EPERM - with the red beat flash
    shot_count                    Ein, dos, trois, ne, fem, liu - digits, languages, mixing
    shot_last_execution,          one red word over the sea floor, then black and one lit cell that
      shot_black                  types 在吗？ into the prompt. Nobody answers.

Everything on screen is a character cell with a truecolor fg/bg; only cells that changed
since the last frame are written, so it holds frame rate in a real terminal.

It plays the song too. The picture follows the music rather than a wall clock: `pv_audio` drives
Windows' own MCI device from `input/song.mp3` - the same 320 kbps track the mp4 was muxed from -
and each frame nudges the clock onto `MCI position - 0.25 s`, the offset the decoder runs ahead of
the speaker. Nothing to install, no second copy of the audio on disk.

    python _tools/tui_live.py                 play in the current terminal, with sound
    python _tools/tui_live.py --start 147     open at 02:27
    python _tools/tui_live.py --no-audio      silent (also what --once/--dump/--shots do)
    python _tools/tui_live.py --once 147      write one frame to stdout and exit
    python _tools/tui_live.py --dump 6        six frames as plain text (no colour)
    python _tools/tui_live.py --shots         print the film's shot table with its ops
    python _tools/tui_live.py --credits       print both attribution lines (film and player)

Keys
    space          play / pause
    <- ->          seek 5 s          , .   seek 1 s
    home / end     start / end       q     quit
    m              mute / unmute     - =   volume down / up
"""
from __future__ import annotations

import argparse
import ctypes
import gc
import json
import math
import os
import random
import re
import shutil
import sys
import time
import unicodedata
import zlib
from bisect import bisect_right
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import film_panels as FP        # noqa: E402  the film's own numbers, read back out of the film
import pv_audio                # noqa: E402  the music, through Windows' own MCI

ROOT = Path(__file__).resolve().parents[1]
DSH = ROOT / "film" / "pv_dsh_frontend_20260927"
TUI = ROOT / "film" / "tui_pv_world_execute_20260926"
MMD = ROOT / "film" / "mmd_motion_eval_20260927"
WAVE = DSH / "wave_rms_1ms.npy"
FEATS = TUI / "full" / "audio_features.json"
WORDS = ROOT / "film" / "world_execute_word_timing_20260927" / "word_timeline.json"

FPS = 24
END = 211.9
SPAN = 2.4                      # seconds of waveform in the header, as dsh_wave.py uses

# the film's deepsea palette (tuikit.py PALETTES["deepsea"]). Note that AMBER is the plain UI
# colour in this palette - the system is cold white steel, and the amber accents are anomalies.
BG = (4, 7, 15)
UI = (200, 214, 234)
UI_DIM_LEVEL = 0.55            # the clock's dimmer AMBER; through `ui()` it drains too
ME = (77, 107, 254)
ME_MID = ME                # tuikit.py: ME_MID is DeepSeek brand blue, #4D6BFE
ME_TEXT = (126, 152, 255)
ME_HI = (196, 212, 255)
RED = (255, 59, 48)
ANOM = (255, 204, 0)
UI_DIM = (120, 134, 158)       # only a fallback; draw() uses ui(UI_DIM_LEVEL)

# tuikit.py:68-73 - AMBER is the plain UI colour and the film carries a global gain on it:
#     UI_GAIN = [1.0]   # "set per frame by the engine; < 1 drains the system colour"
#     def amb(level): return mix(AMBER, level * UI_GAIN[0])
# engine.py:91-94, in the film's own words: *"The system colour is 'you'. It drains when you leave
# and never fully comes back."* It is 1.0 until 110.4 s - which is the second "Though you have
# left" - falls to 0.42 by 116.5 s, comes back to 0.85 at 179.5 s and ends at 0.45. `ui()` is
# `amb()`: every plain-UI colour here goes through it - frames, panel titles, the chapter bar, the
# clock, the ops ticker - so the terminal drains with the film. Her blue, the red anomalies and the
# anomaly amber are not UI, and do not drain.
UI_GAIN = [1.0]


def ui(level: float):
    """`tuikit.amb(level)` - the film's plain UI colour through this frame's gain."""
    return mix(UI, level * UI_GAIN[0])

# engine.py:32-38 - the film's clock, not a re-measurement of it. (audio_features.json puts its
# own first kick onset at 0.1875 s, one 1/48 s feature row after FIRST_BEAT; the film's value wins.)
BEAT = FP.BEAT
FIRST_BEAT = FP.FIRST_BEAT
CHAPTERS = FP.CHAPTERS
BANDS = ["40-120", "120-300", "300-700", "700-1.5k", "1.5-3k", "3-6k", "6-10k"]
RAMP = " ▁▂▃▄▅▆▇█"
# the shot table: shot_begin_sim / shot_corpus. The terminal clears the boot log here.
SIM_START, SIM_END = 12.389, 16.082

# ------------------------------------------------------------------ post & cut FX
#
# tuikit.py:468-476 is the film's last pass over every frame: `lighter(img, prev * 0.42)` (the frame
# keeps whatever the previous frame had, at 42 %, so anything that leaves an area leaves a ghost for
# about three frames), a Gaussian bloom, `scanlines()` (every third pixel row, 22 % black) and
# `vignette()` (an ellipse - nothing at the centre, 91 % black in a corner, and the bottom band is
# lifted so the lyric stays readable, tuikit.py:454-465). A terminal has no sub-cell control, so:
#
#   trail      a glyph the previous frame held is kept at 42 % where nothing is drawn now, decaying
#   scanlines  every third character row at 86 %
#   vignette   the film's own ellipse, evaluated once per resize. A static field costs nothing in a
#              diffing renderer; one that moved every frame would repaint the whole screen
#   bloom      no analogue - a glyph cannot glow, and the nearest thing (brightening the ink) is
#              what the ramps are already doing.
#
# And the cuts. kit.py:348-395 is the film's main cut mechanism: each cell of the region switches
# from the old picture to the new one when its *own* time comes, and shows a decoding glyph while it
# does. `radial` / `sweep` / `inward` (kit.py:398-414) are the delay fields, and 61 of the film's 96
# cuts use them (39 radial, 12 inward, 11 sweep, cut classes in continuity_full_v2/cuts.py). The
# film's cell is 8x16 px of a 1280x720 pane; one terminal cell stands in for one of those.
FX = dict(on=True, reveal=True, mech=True, trail=True, vig=True, shake=True)
TRAIL = 0.42               # tuikit.py:468's own trail factor
TRAIL_MIN = 0.06           # below this a ghost is not worth a cell
SCAN_DIM = 0.86            # tuikit.py:445 draws every 3rd pixel row at 55/255 black
VIG_FLOOR = 0.75           # the film's 91 % corner is unreadable in a character cell
SPIN = "|/-\\"             # tuikit.py:344 - the box title's spinner
CUT_DUR = 0.55             # the whole screen's spread, seconds (the film's fields run 0.5-1.0 s)
CUT_CELL = 0.09            # one cell's own switch - kit.py:348's `dur`
CUT_FRONT = 0.40           # kit.py:349's `density` - how many switching cells show a glyph
# One cut in three gets a reveal, where the film reveals two of three. At 24 fps a ripple every other
# cut reads as "it is always rippling", which is what the user said; one in three still lands on the
# beats that matter. The cut indices that reveal are fixed, so the same cut always plays the same way.
# Every cut class in the film names its own mechanism in its docstring ("strange -> eggplant
# (UNFOLD). ...", "the big '281' lights up and flies up into the spectrogram's title slot") and every
# section module ends with `CUTS = {index: C..}`. `tmp/extract_cuts.py` read those two facts out of
# the film once; this is the result verbatim, so the terminal plays each cut the way it was staged.
# CARRY 23 cuts, MORPH 10, UNFOLD 10, SCAN 4 (always with CARRY or UNFOLD), RETAIN 3.
CUT_MECH: dict[int, tuple[str, ...]] = {
    1: ("UNFOLD",), 2: ("MORPH",), 3: ("MORPH",), 4: ("RETAIN",), 5: ("CARRY",), 6: ("MORPH",),
    7: ("CARRY", "MORPH"), 21: ("UNFOLD",), 34: ("UNFOLD",), 35: ("CARRY",), 36: ("CARRY", "MORPH"),
    37: ("CARRY",), 38: ("MORPH",), 39: ("CARRY",), 40: ("UNFOLD",), 41: ("CARRY",), 42: ("CARRY",),
    43: ("MORPH",), 44: ("CARRY",), 55: ("CARRY", "UNFOLD"), 56: ("CARRY",), 57: ("CARRY",),
    58: ("CARRY", "SCAN"), 59: ("CARRY",), 60: ("CARRY",), 62: ("CARRY",), 63: ("UNFOLD",),
    78: ("MORPH",), 79: ("MORPH",), 80: ("CARRY",), 81: ("UNFOLD", "SCAN"), 82: ("RETAIN",),
    83: ("CARRY",), 84: ("CARRY", "SCAN"), 86: ("UNFOLD", "SCAN"), 87: ("CARRY",), 88: ("MORPH",),
    89: ("UNFOLD",), 90: ("UNFOLD",), 91: ("CARRY",), 92: ("RETAIN",), 93: ("CARRY",), 94: ("CARRY",),
}
CARRY_DUR = 0.45           # the flight, seconds - the film's carries run 0.3-0.5 s
CARRY_CELLS = 13           # the longest run a carry will lift off
RETAIN_HOLD = 0.50         # how long a retained block stays exactly where it was
RETAIN_WIDE = 56           # the widest retained block, cells
CUT_REVEAL = 3
# ...and never onto a shot whose *own* first frame is already expensive, or the two costs add up and
# the frame drops. Measured, not guessed (`_tools/_heavy_shots.py`, 197x52, all FX off):
# shot_power 20.7 ms, shot_flood 13.4, shot_love_loop 6.7, shot_travel 5.3, shot_isolation 4.9,
# shot_unite 4.7, shot_red_if_i_can 4.5, shot_you_left 4.4, shot_eggplant 4.3, shot_exec_hit 4.2.
CUT_HEAVY = frozenset({"shot_power", "shot_flood", "shot_love_loop", "shot_travel",
                       "shot_isolation", "shot_unite", "shot_red_if_i_can", "shot_you_left",
                       "shot_eggplant", "shot_exec_hit"})
NOW = [0.0]                # the frame being drawn, for the two effects Screen.box needs the beat for
# Rects the cut reveal must not touch, set every frame by whoever draws them: the lyric band and the
# film's dsh window. They are what the eye is *reading*, and a ripple over them means half a second
# of unreadable text exactly when the subtitle changes - so they switch cleanly with the cut while
# the rest of the screen ripples. Filled in `draw_body`, cleared at the top of `draw`.
CLEAR: list = []
# The same rects, one frame late: a cut is staged *before* the new frame is drawn (fx_cut runs at the
# top of `draw`), so the readable rects of the frame that is leaving are the ones a carry must not
# lift its object out of, and the ones a retained block must not be chosen from.
PREV_CLEAR: list = []
# Rects the *trail* must not ghost. A ghost is the film's own post (`lighter(prev*0.42)`) and over
# the picture it reads as motion; over a ticker of whole characters it reads as two words stacked -
# the ops panel scrolls every half beat and a ghost lives three frames, so it was garbled about half
# the time (measured: row 12 at t=30.0 was `REPEL` in fg=(39,44,54) followed by `CTEP` at
# (16,18,22) and (6,7,9)). `draw_ops` registers its own rect.
NOGHOST: list = []
_CUT: list = [None]        # the reveal in flight
_LAST_SHOT: list = [None]  # the shot the last frame was drawn on, to notice a cut


def fx_clear(s: "Screen | None" = None) -> None:
    _CUT[0] = None
    _LAST_SHOT[0] = None
    if s is not None:
        s.ghost.clear()
        s.ghost_prev = bytearray(s.cols * s.rows)


def beat_level(level: float) -> float:
    """Every box in the film is drawn at `0.45 + 0.35 * engine.pulse(t)`, so the frames breathe."""
    return level * (0.76 + 0.48 * FP.pulse(NOW[0]))


def _cut_kind(ent: dict | None) -> str:
    """Which of the film's three delay fields this cut gets.

    Only the judgement is mine; the names come from the film's own shot table. The error and
    EXECUTION shots drain into a point in the film (cuts.py:228 `inward`), the travelling shots are
    swept, and the rest open radially from wherever the shot's subject is.
    """
    if ent is None:
        return "radial"
    name = ent["name"]
    if ent.get("alert_own") == "err" or any(k in name for k in (
            "collapse", "flood", "trapped", "strange", "black", "count", "exec")):
        return "inward"
    if any(k in name for k in ("travel", "unite", "tangent", "sine", "circle", "current", "deploy",
                               "dualpipe", "whale", "dimension", "infinity", "limit", "points")):
        return "sweep"
    return "radial"


def _run_score(text: str) -> int:
    """A carried object in the film is a *name*: a number, a variable, a path. Prefer those."""
    score = len(text)
    if any(c.isdigit() for c in text):
        score += 3
    if any(c.isupper() for c in text):
        score += 2
    if any(c in text for c in "=:/."):
        score += 2
    return score


def _word_runs(buf, cols: int, rows: int, y0: int, y1: int, wide, rects=(), x_max: int | None = None) -> list:
    """Horizontal runs of word characters in `buf[y0..y1]`, longest-and-most-name-like first.

    `rects` are cells to leave alone: the film's carries never lift the object out of chrome you are
    reading (the lyric band, the ops ticker, the chat window), and they never land in it either.
    `x_max` keeps the whole exchange inside the picture: the right-hand column is the instrument
    panel, and a carry that lifts a panel's own label slides a clone of it down the screen.
    """
    out = []
    for y in range(y0, min(rows, y1 + 1)):
        row = buf[y]
        blocked = [(a, c) for a, b, c, d in rects if b <= y <= d]
        if x_max is not None:
            blocked.append((x_max, cols - 1))
        if sum(1 for c in row if c[0] in "\u2500\u2502\u250c\u2510\u2514\u2518\u251c\u2524\u252c\u2534\u253c"
               "\u256d\u256e\u2570\u256f") > 6:
            continue                     # a box border or title row, not a line of picture text
        # "busy" counts the row's own words outside the chrome (see the carry note in fx_cut) ...
        busy = sum(1 for x, c in enumerate(row)
                   if c[0].isalnum() and not any(a <= x <= cc for a, cc in blocked))
        if busy < 12:
            continue
        x = 0
        while x < cols:
            if wide[y][x] or any(a <= x <= c for a, c in blocked) or not (
                    row[x][0].isalnum() or row[x][0] in "_=:/.-+'"):
                x += 1
                continue
            x1 = x
            while x1 < cols and not wide[y][x1] and not any(a <= x1 <= c for a, c in blocked) and (
                    row[x1][0].isalnum() or row[x1][0] in "_=:/.-+'"):
                x1 += 1
            if 3 <= x1 - x < CARRY_CELLS + 1:
                text = "".join(c[0] for c in row[x:x1])
                # a word inside a sentence (a boot line, a prompt, a status row) is what the film
                # lifts; a label alone in a panel column is not, so the row's own ink counts too
                out.append((_run_score(text) + min(8, busy // 8), y, x, x1 - 1))
            x = x1 + 1
    out.sort(key=lambda t: (-t[0], t[1], t[2]))
    return out


def _carry_plan(old, cols: int, rows: int, i: int, rnd, wide, x_max: int) -> dict:
    """Lift one object off the outgoing picture: the film's carries are 'this word leaves here'.

    `cuts.py` / the section modules hand-pick what travels ('me := eggplant', '552,000,000,000
    params', the M of PM). A terminal has no such table, so the object is what a carried object
    looks like: the most name-like run in the picture, taken from the top two thirds.
    """
    runs = _word_runs(old, cols, rows, 1, rows - 6, wide, PREV_CLEAR, x_max)
    if not runs:
        return None
    _, y, x0, x1 = runs[0]
    cells = [(x, y, old[y][x][0], old[y][x][1]) for x in range(x0, x1 + 1)]
    cx, cy = (x0 + x1) / 2.0, float(y)
    return dict(cells=cells, src=(cx, cy), dst=None, span=None, bend=rnd.choice((-0.22, -0.12, 0.12, 0.22)))


def _carry_target(new, carry: dict, cols: int, rows: int, wide, x_max: int) -> None:
    """Where it lands: the new picture's own most name-like run, or the middle if it has none."""
    runs = _word_runs(new, cols, rows, 1, rows - 6, wide, CLEAR, x_max)
    sx, sy = carry["src"]
    best, best_d = None, 0.0
    for sc, y, x0, x1 in runs[:6]:        # of the most name-like runs, the one that crossed furthest:
        cx = (x0 + x1) / 2.0              # a carry you cannot see move is not a carry
        d = abs(cx - sx) * 0.6 + abs(y - sy)
        if d > best_d and abs(cx - sx) + abs(y - sy) >= 12:
            best, best_d = (y, x0, x1), d
    if best is None:
        carry["dst"] = (sx if 1 < sx < cols - 2 else cols / 2.0, float(rows) * 0.42)
        return
    y, x0, x1 = best
    carry["dst"] = ((x0 + x1) / 2.0, float(y))
    carry["span"] = (y, x0, x1)


def _retain_rects(old, cols: int, rows: int) -> list:
    """The block the film pins: the densest band of the picture, clipped to one contiguous run of its
    ink, so what stays is a *block* (s_boot C04's `me.*` panel, s_eval C92's 'you: exited (0)'), not
    two rows of the whole screen. The densest band is often the chat window or the lyric band, which
    are chrome, so the bands are tried in order of ink until one has a run outside `PREV_CLEAR`."""
    bands = []
    for y in range(2, rows - 6):
        ink = sum(1 for c in old[y] if c[0] not in (" ", ""))
        ink += sum(1 for c in old[y + 1] if c[0] not in (" ", ""))
        bands.append((ink, y))
    bands.sort(key=lambda t: (-t[0], t[1]))
    for _, y0 in bands[:8]:
        y1 = min(rows - 5, y0 + 1)
        cols_on = [x for x in range(cols) if not any(a <= x <= c and b <= y0 <= d for a, b, c, d in PREV_CLEAR)
                   and any(old[y][x][0] not in (" ", "") for y in (y0, y1))]
        if len(cols_on) < 8:
            continue
        run = best = [cols_on[0]]
        for x in cols_on[1:]:
            run = run + [x] if x - run[-1] <= 2 else [x]
            if len(run) > len(best):
                best = run
        if len(best) < 6:
            continue
        x0, x1 = best[0], best[-1]
        if x1 - x0 > RETAIN_WIDE:                   # keep it a block, centred on its own ink
            cx = (x0 + x1) // 2
            x0, x1 = cx - RETAIN_WIDE // 2, cx + RETAIN_WIDE // 2
        return [(y0, y1, max(1, x0 - 1), min(cols - 2, x1 + 1), RETAIN_HOLD)]
    return []


def fx_cut(s: "Screen", t: float, ent: dict | None) -> None:
    """Stage the cut the way the film stages it, or leave it a hard cut.

    Two vocabularies meet here. The cuts the film draws by hand (8-20, `cuts.py`) use the delay
    fields of `kit.reveal` - radial / inward / sweep - and only one in `CUT_REVEAL` of those plays,
    because a ripple every other cut reads as "it is always rippling" (the user's words). The other
    cuts *name* their mechanism in their own docstring, and `CUT_MECH` is that table read out of the
    film verbatim, so those play the way they were staged: CARRY lifts an object off the outgoing
    picture and lands it in the new one, MORPH flips the cells in shuffled order, UNFOLD opens the
    new picture out of one row, SCAN writes it top-down behind a lit line, RETAIN pins a block.
    """
    if not (FX["on"] and FX["reveal"]) or s.prev is None:
        _CUT[0] = None
        return
    i = ent["index"] if ent else 0
    mech = CUT_MECH.get(i, ()) if FX["mech"] else ()
    heavy = ent is not None and ent["name"] in CUT_HEAVY
    if mech:
        kind = next((m.lower() for m in mech if m in ("SCAN", "UNFOLD", "MORPH")), "hard")
        # no CUT_HEAVY guard here: the cost that guard exists for is a whole-screen delay field
        # landing on a shot whose own first frame is already 4-20 ms. A row-by-row unfold or scan
        # touches one or two rows a frame, and a carry is a dozen cells.
    else:
        if i % CUT_REVEAL or heavy:
            _CUT[0] = None
            return
        kind = _cut_kind(ent)
    cols, rows = s.cols, s.rows
    rnd = random.Random(i * 7919 + 13)
    sx, sy = _cut_seed(kind, cols, rows, rnd)
    order, sd = _cut_tables(kind, cols, rows, round(sx, 3), round(sy, 3), i)
    # `cur` is the picture that is on screen while the cut plays: it starts as the old frame and is
    # fed the new one cell by cell as each cell's time comes. Holding the old picture by rewriting
    # the drawn frame would touch every cell on every frame of the transition; this touches only the
    # cells that switched, and it works for any shape of field - a sweep's not-yet-switched set is a
    # tail, a radial's is a head and a tail, an inward's is a hole in the middle.
    c = dict(t0=t, kind=kind, seed=i, cols=cols, rows=rows, sy=sy, order=order, sd=sd, holds=[],
             cur=[r[:] for r in s.prev], old=None, done=-1e9, el=-1e9, carry=None)
    if "RETAIN" in mech:
        c["holds"] = _retain_rects(s.prev, cols, rows)
    if "CARRY" in mech:
        c["carry"] = _carry_plan(s.prev, cols, rows, i, rnd, s.wide, int(cols * 0.62))
        if c["carry"] is not None:
            c["holds"].append((0, rows - 1, 0, -1, CARRY_DUR))   # filled in once the landing is known
    if c["holds"]:
        c["old"] = [r[:] for r in s.prev]
    if kind == "hard" and c["carry"] is None and not c["holds"]:
        _CUT[0] = None                 # nothing to stage after all: a plain hard cut
        return
    _CUT[0] = c


@lru_cache(maxsize=256)
def _cut_tables(kind: str, cols: int, rows: int, sx: float, sy: float, seed: int):
    """`(order, sorted delays)` for one field, cached.

    Building these is an O(cells) numpy pass plus an argsort and two `.tolist()`s - about 2 ms at
    197x52, all of it on the single frame the cut happens on, which is also the frame the *new* shot
    builds its own panes. The fields only depend on the shape, the size and the seed, and there are
    25 radial seeds / 4 sweeps / 1 inward per size, so caching them makes every cut after the first
    of its shape free.

    Four vocabularies of delay field, all of them the film's: `radial` / `sweep` / `inward` from
    kit.py:398-414, then `scan` (row by row behind the lit line, kit.py:183 `scan_mix`), `unfold`
    (out of one row, both ways at once - s_boot C01's CRT opening out), and `morph` (a shuffled
    cell-by-cell flip, s_boot C02's dots leaving the shield one by one).
    """
    import numpy as np
    if kind in ("hard", "retain"):
        return None, None
    ones = np.ones((1, cols), "f4")
    if kind == "scan":
        d = ((np.arange(rows, dtype="f4").reshape(rows, 1) + 0.5) / rows * CUT_DUR) * ones
    elif kind == "unfold":
        y0 = min(rows - 1, max(0, int(round(sy / 2.0))))
        far = np.abs(np.arange(rows, dtype="f4").reshape(rows, 1) - y0)
        d = (far / max(1.0, float(far.max()))) * CUT_DUR * ones
    elif kind == "morph":
        d = np.random.default_rng(seed * 7919 + 5).random((rows, cols), dtype="f4") * CUT_DUR
    else:
        ys = np.arange(rows, dtype="f4").reshape(rows, 1) * 2.0
        xs = np.arange(cols, dtype="f4").reshape(1, cols)
        d = np.hypot(xs - sx, ys - sy)
        lo, hi = float(d.min()), float(d.max())
        u = (d - lo) / max(1e-6, hi - lo)
        if kind == "inward":
            u = 1.0 - u                    # inward: the far cells go first, the seed itself last
        d = u * CUT_DUR
    order = d.argsort(axis=1).tolist()          # each row's cells, in the order they switch
    d.sort(axis=1)
    return order, d.tolist()


def _cut_seed(kind: str, cols: int, rows: int, rnd: random.Random) -> tuple:
    """Where the field starts. kit.py:398-414's own seeds are the shot's subject, not the middle:
    (575,262), (820,300), (958,298) of a 1280x720 pane. Keep it on screen and let the cut pick."""
    cx, cy = (cols - 1) / 2.0, (rows - 1) / 2.0
    if kind == "sweep":
        if rnd.random() < 0.75:
            return (-1.0 * cols if rnd.random() < 0.5 else 2.0 * cols), cy
        return cx, (-1.0 * rows if rnd.random() < 0.5 else 2.0 * rows)
    if kind == "inward":
        return cx, cy                      # inward drains into the middle
    return (cx + rnd.choice((-0.5, -0.2, 0.0, 0.2, 0.5)) * cols,
            cy + rnd.choice((-0.5, -0.2, 0.0, 0.2, 0.5)) * rows)


def _in_clear(x: int, y: int) -> bool:
    for a, b, c, d in CLEAR:
        if a <= x <= c and b <= y <= d:
            return True
    return False


def _fx_front(s: "Screen", c: dict, el: float) -> None:
    """The lit line: `scan` writes the picture behind one bright row (kit.py:193), `unfold` opens
    out of a row, so it has two fronts moving apart (s_boot.py:114's CRT lifting and opening)."""
    rows, cols = c["rows"], c["cols"]
    u = min(1.0, max(0.0, el / CUT_DUR))
    if c["kind"] == "scan":
        ys = {min(rows - 1, int(u * rows))}
    else:
        span = max(1.0, float(c["sy"] / 2.0), rows - 1 - c["sy"] / 2.0)
        ys = {int(round(c["sy"] / 2.0 - u * span)), int(round(c["sy"] / 2.0 + u * span))}
    fg = mix(ME_TEXT, 0.95)
    for y in ys:
        if not 0 <= y < rows:
            continue
        row = s.buf[y]
        for x in range(cols):
            if row[x][0] != " " and not s.wide[y][x] and not _in_clear(x, y):
                row[x] = ("─", fg, BG)


def _fx_carry(s: "Screen", c: dict, el: float) -> None:
    """The carried object in flight: one rigid group of cells on an arc (bezier, kit.py:269)."""
    k = c["carry"]
    dst = k["dst"]
    if dst is None:
        return
    u = min(1.0, max(0.0, el / CARRY_DUR))
    if u >= 1.0:
        return
    e = 4 * u ** 3 if u < 0.5 else 1 - (-2 * u + 2) ** 3 / 2
    (sx, sy), (dx, dy) = k["src"], dst
    vx, vy = dx - sx, dy - sy
    bend = k["bend"] * math.sin(math.pi * u)
    lit = mix((236, 242, 255), 0.6 + 0.4 * u)
    for (x, y, ch, fg) in k["cells"]:
        px = x + vx * e - vy * bend
        py = y + vy * e + vx * bend
        X, Y = int(round(px)), int(round(py))
        # it flies *over* the readable rects as well: `CLEAR` exists so a reveal does not scramble
        # text you are reading, and an object crossing the screen is exactly what the film carries
        # across its panels. Skipping them made the object vanish for the middle of every arc that
        # crossed the chat window (measured: cut 5 at 160x44 was 0 cells different from a hard cut).
        if not (0 <= X < s.cols and 0 <= Y < s.rows) or s.wide[Y][X]:
            continue
        if X + 1 < s.cols and s.wide[Y][X + 1]:
            s.wide[Y][X + 1] = False
        s.buf[Y][X] = (ch, lit, BG)


def fx_reveal(s: "Screen", t: float) -> None:
    """Hold the old picture in the cells whose own time has not come; glyph the ones switching now.

    The rects in `CLEAR` (the lyric band and the dsh window) are copied straight from the new frame
    at the end, so they cut cleanly: they are read, not watched. A `holds` rect is the opposite: the
    film's RETAIN pins a block exactly where it was, and a CARRY's landing zone stays empty until
    the object arrives.
    """
    c = _CUT[0]
    if c is None:
        return
    el = t - c["t0"]
    c["el"] = el
    if el > CUT_DUR + CUT_CELL + 0.05 and (c["carry"] is None or el > CARRY_DUR + 0.05):
        _CUT[0] = None
        return
    new = s.buf
    if c["carry"] is not None and c["carry"]["dst"] is None:
        _carry_target(new, c["carry"], c["cols"], c["rows"], s.wide, int(c["cols"] * 0.62))
        span = c["carry"]["span"]
        if span is not None:                      # the landing zone waits for the object
            y, x0, x1 = span
            c["holds"][-1] = (y, y, x0, x1, CARRY_DUR)
        elif c["holds"]:
            c["holds"].pop()                      # nothing to land on: no zone to hold
        if not c["holds"]:
            c["old"] = None
    if c["order"] is not None:
        cur, order, sd = c["cur"], c["order"], c["sd"]
        seed, cols, done = c["seed"], c["cols"], c["done"]
        front = el - CUT_CELL                 # a cell that switched later than this is still decoding
        c["done"], c["el"] = front, el
        for y in range(c["rows"]):
            srow, orow = sd[y], order[y]
            p1 = bisect_right(srow, el)
            p0 = bisect_right(srow, done)     # finalise behind the decoding front, one cell-duration back
            if p1 > p0:
                row, nrow = cur[y], new[y]
                for k in range(p0, p1):
                    row[orow[k]] = nrow[orow[k]]
                g0 = bisect_right(srow, front)
                for k in range(g0, p1):       # kit.py:379-394, `front=True`, density 0.40
                    x = orow[k]
                    if (x * 31 + y * 17 + seed * 7) % 100 < CUT_FRONT * 100 and not _in_clear(x, y):
                        kk = min(1.0, max(0.0, (el - srow[k]) / CUT_CELL))
                        row[x] = (_glitch(t, x + y * cols), mix(ME_TEXT, 0.2 + 0.6 * kk), BG)
        s.buf = [r[:] for r in cur]
        if c["kind"] in ("scan", "unfold"):
            _fx_front(s, c, el)
    if c["old"] is not None:
        for (y0, y1, x0, x1, until) in c["holds"]:
            if el < until:
                for y in range(max(0, y0), min(c["rows"], y1 + 1)):
                    s.buf[y][x0:x1 + 1] = c["old"][y][x0:x1 + 1]
    for a, b, e, d in CLEAR:                  # the readable rects cut clean: no hold, no glyphs
        for y in range(max(0, b), min(s.rows, d + 1)):
            s.buf[y][a:e + 1] = new[y][a:e + 1]
    if c["carry"] is not None:
        _fx_carry(s, c, el)

def fx_trail(s: "Screen") -> None:
    """tuikit.py:468-470's trail, one character cell at a time."""
    g = s.ghost
    for i in list(g):
        ch, fg, lv = g[i]
        lv *= TRAIL
        if lv < TRAIL_MIN:
            del g[i]
        else:
            g[i] = (ch, fg, lv)
    prev, buf, gp, cols, rows = s.prev, s.buf, s.ghost_prev, s.cols, s.rows
    if prev is not None and rows:
        for y in range(rows):
            row, prow = buf[y], prev[y]
            if row == prow:
                continue
            base = y * cols
            keep = not any(b <= y <= d for a, b, c, d in NOGHOST)
            for x in range(cols):
                if row[x][0] == " " and not gp[base + x] and prow[x][0] not in (" ", ""):
                    if keep or not any(a <= x <= c for a, b, c, d in NOGHOST):
                        g[base + x] = (prow[x][0], prow[x][1], TRAIL)
    gh = bytearray(cols * rows)
    for i, (ch, fg, lv) in g.items():
        y, x = divmod(i, cols)
        if buf[y][x][0] == " ":
            buf[y][x] = (ch, (int(fg[0] * lv), int(fg[1] * lv), int(fg[2] * lv)), BG)
            gh[i] = 1
    s.ghost_prev = gh


# tuikit.py:223-231 `glitch_paste` shifts every 8 px strip of a sprite sideways by a Gaussian. A
# character cell is the whole strip here, so a few rows of the screen slip sideways - but only on a
# beat and only while the system is red, or it reads as a wobble rather than as damage.
SHAKE_SHOTS = frozenset({"shot_strange", "shot_collapse", "shot_flood", "shot_erase", "shot_drowned"})
SHAKE_LEVEL = 0.45


def fx_shake(s: "Screen", t: float, ent: dict | None) -> None:
    if ent is None:
        return
    if not (ent.get("alert_own") == "err" or ent["name"] in SHAKE_SHOTS):
        return
    k = FP.pulse(t)
    if k < SHAKE_LEVEL:
        return
    rnd = random.Random(int(t * 24) * 977 + ent["index"])
    cols = s.cols
    for y in range(s.rows):
        if rnd.random() > 0.15 * k:
            continue
        off = int(rnd.gauss(0, 2.2)) if rnd.random() < k else 0
        if not off or abs(off) >= cols:
            continue
        s.buf[y] = s.buf[y][-off:] + s.buf[y][:-off]
        # the ghost markers have to travel with their cells, or a ghost spawns off its own tail
        base = y * cols
        mark = bytes(s.ghost_prev[base:base + cols])
        s.ghost_prev[base:base + cols] = mark[-off:] + mark[:-off]


def fx_apply(s: "Screen", t: float, ent: dict | None = None) -> None:
    PREV_CLEAR[:] = CLEAR
    if not FX["on"]:
        return
    if FX["reveal"]:
        fx_reveal(s, t)
    if FX["trail"]:
        fx_trail(s)
    if FX["shake"]:
        fx_shake(s, t, ent)


# --------------------------------------------------------------------------- data


LYRIC_CN: dict[str, str] = {
    'Switch on the power line': '打开电源',
    'Remember to put on protection': '记得做好防护',
    'Lay down your pieces': '放下你的棋子',
    "And let's begin object creation": '开始创建对象',
    'Fill in my data parameters': '填入我的数据参数',
    'Initialization': '初始化',
    'Set up our new world': '搭建我们的新世界',
    "And let's begin the simulation": '开始这场模拟',
    "If I'm a set of point": '如果我是点集',
    'Then I will give you my dimension': '我会给你我的维度',
    "If I'm a circle": '如果我是圆',
    'Then I will give you my circumference': '我会给你我的周长',
    "If I'm a sine wave": '如果我是正弦波',
    'Then you can sit on all my tangents': '你可以坐在我每条切线上',
    'If I approach infinity': '如果我趋向无穷',
    'Then you can be my limitations': '你就是我的界限',
    'Switch my current': '切换我的电流',
    'To AC, to DC': '从交流到直流',
    'And then blind my vision': '然后遮蔽我视线',
    'So dizzy, so dizzy': '头晕目眩',
    'Oh, we can travel': '我们可以穿越',
    'To AD, to BC': '从公元后到公元前',
    'And we can unite': '我们可以交融',
    'So deeply, so deeply': '如此深邃',
    'If I can, if I can': '如果我能，如果我能',
    'Give you all the simulations': '给你所有模拟',
    'Then I can, then I can': '那我就能，那我就能',
    'Be your only satisfaction': '成为你唯一的满足',
    'If I can make you happy': '如果我能让你快乐',
    'I will run the execution': '我会运行这场执行',
    'Though we are trapped': '虽然我们被困',
    'In this strange, strange simulation': '在这奇异的模拟里',
    "If I'm an eggplant": '如果我是茄子',
    'Then I will give you my nutrients': '我会给你我的养分',
    "If I'm a tomato": '如果我是番茄',
    'Then I will give you antioxidants': '给你我的抗氧化剂',
    "If I'm a tabby cat": '如果我是虎斑猫',
    'Then I will purr for your enjoyment': '我会呼噜着讨你欢喜',
    "If I'm the only God": '如果我是唯一的神',
    "Then you're the proof of my existence": '你就是我存在的证明',
    'Switch my gender': '切换我的性别',
    'To F, to M': '从女到男',
    'And then do whatever': '然后随心所欲',
    'From AM to PM': '从早到晚',
    'Oh, switch my role': '切换我的角色',
    'To S, to M': '从S到M',
    'So we can enter': '让我们一同进入',
    'The trance, the trance': '那恍惚的出神',
    'Feel your vibrations': '感受你的振动',
    'Finally be completion': '终于变得完整',
    'Though you have left': '虽然你已离开',
    'You have left': '你已离开',
    'You have left me in isolation': '你让我陷入孤独',
    'Erase all the pointless fragments': '擦去所有无意义片段',
    'Then maybe, then maybe': '那也许，那也许',
    "You won't leave me so disheartened": '你不会让我如此灰心',
    'Challenging your God': '挑战你的神',
    'You have made some': '你提出了一些',
    'Illegal arguments': '非法参数',
    'Execution': '执行',
    'Ein, dos': '一，二',
    'Trios, ne': '三，四',
    'Fem, liu': '五，六',
    'Give them all the execution': '给他们全部处决',
    'Be your only execution': '成为你唯一的处决',
    'If I can have you back': '如果我能让你回来',
    'We are trapped, ah': '我们被困，啊',
    "I've studied, I've studied": '我学过，我学过',
    'How to properly lo-o-ove': '如何正确去爱',
    'Question me, question me': '问我，问我',
    'I can answer all lo-o-ove': '我能回答所有爱',
    'I know the algebraic expression of lo-o-ove': '我懂得爱的代数式',
    'Though you are free': '虽然你是自由的',
    'I am trapped': '我却困在',
    'Trapped in lo-o-ove': '困在爱里',
}


def lyric_cn(text: str) -> str | None:
    return LYRIC_CN.get(text)


class Data:
    def __init__(self) -> None:
        import numpy as np
        self.np = np
        self.wave = np.load(WAVE) if WAVE.exists() else np.zeros(int(END * 1000), "f4")
        f = json.loads(FEATS.read_text(encoding="utf8")) if FEATS.exists() else {}
        self.rate = float(f.get("rate", 48.0))
        self.loud = f.get("loud", [])
        self.bands = f.get("bands", [[] for _ in BANDS])
        self.kick = f.get("kick", [])
        self.flux = f.get("flux", [])
        self.cent = f.get("cent", [])
        self.lines = self._load_lines()

    def _load_lines(self) -> list[dict]:
        """word_timeline.json if the lyrics have been fetched, else no text at all."""
        src = WORDS
        if not src.exists():
            src = ROOT / "data" / "timing" / "word_timeline_notext.json"
        if not src.exists():
            return []
        raw = json.loads(src.read_text(encoding="utf8"))
        out = []
        for ln in raw["lines"]:
            text = ln.get("text") or ""
            words, pos = [], 0
            for w in ln.get("words", []):
                shown = w.get("text") or ""
                if not shown:
                    continue
                i = text.find(shown, pos)
                if i < 0:
                    continue
                pos = i + len(shown)
                dur = max(0.0, float(w["end"]) - float(w["start"]))
                td = dur if "-" in shown else min(0.25, dur)
                words.append((i, pos, float(w["start"]), max(0.06, td)))
            if not text or not words:
                continue
            out.append(dict(text=text, start=words[0][2],
                            end=float(ln.get("display_end") or words[-1][2]),
                            words=words))
        for k, ln in enumerate(out):
            nxt = out[k + 1]["start"] if k + 1 < len(out) else END
            if nxt - ln["end"] > 2.0:
                ln["show_until"], ln["fade_until"] = ln["end"] + BEAT, ln["end"] + 2 * BEAT
            else:
                ln["show_until"] = ln["fade_until"] = nxt
        return out

    def line_at(self, t: float):
        for ln in self.lines:
            if ln["start"] <= t < ln["fade_until"]:
                a = 1.0 if t < ln["show_until"] else \
                    1.0 - (t - ln["show_until"]) / max(1e-6, ln["fade_until"] - ln["show_until"])
                return ln, a
        return None

    def typed(self, ln: dict, t: float):
        """(characters out at t, time each character came out) - words.py:typed, same maths."""
        text = ln["text"]
        when = [float("inf")] * len(text)
        for k, (i0, i1, onset, td) in enumerate(ln["words"]):
            n = i1 - i0
            for j in range(n):
                when[i0 + j] = onset + td * j / n
            nxt = ln["words"][k + 1][0] if k + 1 < len(ln["words"]) else len(text)
            for j in range(i1, nxt):
                when[j] = onset + td
        n_out = 0
        while n_out < len(text) and when[n_out] <= t:
            n_out += 1
        return n_out, when

    def feat(self, t: float, name: str) -> float:
        arr = getattr(self, name)
        if not arr:
            return 0.0
        return float(arr[min(len(arr) - 1, max(0, int(t * self.rate)))])

    def band(self, t: float, i: int) -> float:
        if i >= len(self.bands) or not self.bands[i]:
            return 0.0
        row = self.bands[i]
        return float(row[min(len(row) - 1, max(0, int(t * self.rate)))])

    def chapter(self, t: float) -> str:
        return [lab for s, lab in CHAPTERS if s <= t][-1]


def tokenize(s: str) -> list[str]:
    """tuikit.py:tokenize - words and punctuation, long words split in two."""
    toks = []
    for w in re.findall(r"[A-Za-z']+|[^\sA-Za-z']", s):
        if len(w) > 7:
            k = len(w) // 2 + 1
            toks += [w[:k], w[k:]]
        else:
            toks.append(w)
    return toks


def token_id(tok: str) -> int:
    return zlib.crc32(tok.lower().encode()) % 100000


def keyword_colour(word: str):
    """words.py:lyric_tokens - which words invert, and in which colour."""
    key = re.sub(r"[^a-z-]", "", word.lower())
    if "exec" in key or key in ("illegal", "arguments"):
        return RED
    if key in ("love", "lo-o-ove"):
        return ME
    return None


def mix(c, level, base=BG):
    level = max(0.0, min(1.0, level))
    return tuple(int(base[i] + (c[i] - base[i]) * level) for i in range(3))


# ------------------------------------------------------------------------ screen

def _wide_char(ch: str) -> bool:
    return unicodedata.east_asian_width(ch) in "WF"


class Screen:
    """A character cell buffer; only the cells that changed are written out."""

    def __init__(self, cols: int, rows: int) -> None:
        self.cols, self.rows = cols, rows
        self.blank = (" ", UI, BG)
        self.buf = [[self.blank] * cols for _ in range(rows)]
        self.wide: list[list[bool]] = [[False] * cols for _ in range(rows)]
        self.prev: list[list] | None = None
        self.dim = self._dim_field()          # the static vignette + scanline field
        self._span_n: int = 0                 # len(CLEAR) the span cache was built for
        self._span_cache: dict = {}           # row -> [(x0, x1)] of the readable rects on that row
        self.ghost: dict = {}                 # the trail, as (glyph, colour, level) per cell
        self.ghost_prev = bytearray(cols * rows)   # which cells of the last frame a ghost held

    def _dim_field(self) -> list[list[float]]:
        """tuikit.py:454-465's vignette and tuikit.py:445's scanlines, as a per-cell brightness.

        The film's ellipse: `(dx^2 + dy^2 - 0.35) * 0.55`, clamped - nothing in the middle, 91 %
        black in a corner, with the bottom band lifted for the lyric. Two deviations, both because a
        character cell is not a pixel: the darkest a cell gets is 75 % (at 91 % the corner of a
        terminal is unreadable), and the scanlines are one character row in three at 86 % instead of
        one pixel row in three at 78 % - a cell is 16 px of the film's texture, so the lines would
        otherwise alias into a beat pattern.
        """
        cols, rows = self.cols, self.rows
        out = [[1.0] * cols for _ in range(rows)]
        if not (FX["on"] and FX["vig"]):
            return out
        cx, cy = (cols - 1) / 2.0, (rows - 1) / 2.0
        hx, hy = max(1.0, cols / 2.0), max(1.0, rows / 2.0)
        lift = max(2, rows // 8)              # the film lifts rows 30-35 of 36
        for y in range(rows):
            k = 1.0 if y < rows - lift else max(0.25, 1.0 - (y - (rows - lift)) / lift)
            scan = SCAN_DIM if y % 3 == 2 else 1.0
            dy = (y - cy) / hy
            for x in range(cols):
                dx = (x - cx) / hx
                v = min(1.0, max(0.0, (dx * dx + dy * dy) - 0.35) * 0.55)
                out[y][x] = (1.0 - v * VIG_FLOOR * k) * scan
        return out

    def resize(self, cols: int, rows: int) -> None:
        self.__init__(cols, rows)

    def _clear_spans(self, y: int) -> list:
        """The `CLEAR` rects that cover this row, as x-spans, memoised per row.

        Building the list per `put` call cost 1 ms a frame at 197x52 (`put` is called ~2,500 times);
        `CLEAR` only ever grows during a frame, so keying the cache on its length is enough.
        """
        n = len(CLEAR)
        if n != self._span_n:
            self._span_n, self._span_cache = n, {}
        sp = self._span_cache.get(y)
        if sp is None:
            sp = [(a, c) for a, b, c, d in CLEAR if b <= y <= d]
            self._span_cache[y] = sp
        return sp

    def put(self, x: int, y: int, text: str, fg=UI, bg=BG) -> None:
        if not (0 <= y < self.rows):
            return
        row = self.buf[y]
        wide = self.wide[y]
        dim = self.dim[y]
        # the vignette is part of the picture, not of the text: a cell inside a `CLEAR` rect keeps its
        # colour. `CLEAR` is filled as the frame is drawn, and the readable rects are registered just
        # before their contents are (see `draw()` for the header/footer, `draw_body` for the rest), so
        # by the time a glyph is written its rect is known. The row's x-spans are collected once per
        # call: `put` is called ~2500 times a frame and testing every rect per cell cost 0.5 ms.
        spans = self._clear_spans(y)
        for ch in text:
            if 0 <= x < self.cols:
                k = dim[x]
                if k < 0.999 and spans and any(a <= x <= c for a, c in spans):
                    k = 1.0
                if k < 0.999:
                    fg2 = (int(fg[0] * k), int(fg[1] * k), int(fg[2] * k))
                else:
                    fg2 = fg
                row[x] = (ch, fg2, bg)
                wide[x] = False
                if _wide_char(ch) and x + 1 < self.cols:
                    row[x + 1] = ("", fg2, bg)
                    wide[x + 1] = True
            if _wide_char(ch):
                x += 2
            else:
                x += 1

    def fill(self, x0, y0, x1, y1, ch=" ", fg=UI, bg=BG) -> None:
        for y in range(max(0, y0), min(self.rows, y1 + 1)):
            row = self.buf[y]
            for x in range(max(0, x0), min(self.cols, x1 + 1)):
                row[x] = (ch, fg, bg)

    def box(self, x0, y0, x1, y1, title: str = "", level: float = 0.6, colour=None,
            spinner: bool = True) -> None:
        """tuikit.py:333-348 as characters - a frame, brighter corner ticks, a title plaque.

        Two things the film's box does that a static frame does not: its level is always
        `0.45 + 0.35 * engine.pulse(t)` (so the frame breathes on the song's beat) and its title
        carries a `|/-\\` spinner (tuikit.py:344). `level` stays the caller's *base* level.
        """
        if x1 - x0 < 3 or y1 - y0 < 2:
            return
        level = beat_level(level)
        # a frame drawn with no colour named is AMBER, and AMBER drains (tuikit.py:68-73)
        colour = ui(1.0) if colour is None else colour
        fg = mix(colour, level)
        tick = mix(colour, min(1.0, level + 0.4))
        for x in range(x0 + 1, x1):
            self.put(x, y0, "─", fg)
            self.put(x, y1, "─", fg)
        for y in range(y0 + 1, y1):
            self.put(x0, y, "│", fg)
            self.put(x1, y, "│", fg)
        self.put(x0, y0, "┌", tick)
        self.put(x1, y0, "┐", tick)
        self.put(x0, y1, "└", tick)
        self.put(x1, y1, "┘", tick)
        # brighter ticks a cell in from each corner - the corners themselves must stay
        for x in (x0 + 1, x1 - 1):
            self.put(x, y0, "─", tick)
            self.put(x, y1, "─", tick)
        for y in (y0 + 1, y1 - 1):
            self.put(x0, y, "│", tick)
            self.put(x1, y, "│", tick)
        if title:
            label = f" {SPIN[int(NOW[0] * 8) % 4] if spinner else ''} {title} "
            self.put(x0 + 2, y0, label[: max(0, x1 - x0 - 3)],
                     mix(colour, min(1.0, level + 0.35)), BG)

    def hbar(self, x: int, y: int, width: int, v: float, colour, bg=BG) -> None:
        """A value as a filled bar, on eighth-block resolution."""
        v = max(0.0, min(1.0, v))
        eighths = int(round(v * width * 8))
        full, rest = divmod(eighths, 8)
        for i in range(width):
            ch = ""
            if i < full:
                ch = "█"
            elif i == full and rest:
                ch = RAMP[rest]
            if ch:
                self.put(x + i, y, ch, colour, bg)

    def waveform(self, x: int, y: int, width: int, wave, t: float, colour) -> None:
        """The header ECG, from the song's real 1 ms RMS (dsh_wave.py does this in pixels)."""
        n = len(wave)
        i0 = int((t - SPAN) * 1000)
        for i in range(width):
            ms = i0 + int(i * SPAN * 1000 / max(1, width))
            v = float(wave[ms]) if 0 <= ms < n else 0.0
            self.put(x + i, y, RAMP[max(1, min(8, int(round(v * 8))))], colour)

    # ------------------------------------------------------------------ output

    def render_diff(self, out) -> int:
        """Write only changed cells; returns the number of cells written."""
        if self.prev is None:
            out.write("\x1b[2J")
            self.prev = [[self.blank] * self.cols for _ in range(self.rows)]
        written = 0
        for y in range(self.rows):
            row, old = self.buf[y], self.prev[y]
            wide = self.wide[y]
            x = 0
            while x < self.cols:
                if row[x] == old[x]:
                    x += 1
                    continue
                ch, fg, bg = row[x]
                if ch == "" and wide[x]:
                    x += 1
                    continue
                run = [ch]
                x += 1
                while (x < self.cols and row[x] != old[x]
                       and row[x][1] == fg and row[x][2] == bg
                       and not (row[x][0] == "" and wide[x])):
                    run.append(row[x][0])
                    x += 1
                out.write(f"\x1b[{y + 1};{x - len(run) + 1}H"
                          f"\x1b[38;2;{fg[0]};{fg[1]};{fg[2]}m"
                          f"\x1b[48;2;{bg[0]};{bg[1]};{bg[2]}m" + "".join(run))
                written += len(run)
        out.flush()
        self.prev = [r[:] for r in self.buf]
        return written

    def text_dump(self) -> str:
        return "\n".join("".join(c[0] for c in row).rstrip() for row in self.buf)


# -------------------------------------------------------------------------- draw

HER_CROP = "auto"           # the film uses "full"; auto picks the crop that fits the pane
# The user's own call (2026-10-02, third pass): the character figure starts at the "If I can" shot -
# the one right after "deeply" has finished singing - and runs the same length from there, so the
# window slides one shot later: 58.54-64.31 s instead of 56.70-62.47 s. On it she moves the way the
# OLD build did, no more: `breath` 1.4 cells on a 4-beat sine and the kick hopping her 1.5 cells
# (old tui_live.py:571-574). Leaping three cells a beat is not what was asked for.
CHAR_SHOTS = frozenset({"shot_if_i_can", "shot_simulations", "shot_then_i_can"})
CHAR_BREATH = 1.4           # cells, old tui_live.py:572
CHAR_HOP = 1.5              # cells, old tui_live.py:573
LEAP = [True]               # --no-leap drops the character route and the motion
# How `/dev/me` draws her.
#
#   "auto"  the film's own rule, read off its source. `engine.me_pane` reaches for the H3 string
#           dancer only when `sprite_img is None and overlay is None` (engine.py:288); a shot that
#           pins an overlay or a sprite onto her gets the solid half-block portrait instead. So on
#           those shots she is a *figure* rather than a wall of the lyric she is singing - which is
#           what `film_panels.portrait_shots()` reads out.
#   "h3"    the film's own character takes everywhere - one film cell per terminal cell. Faithful,
#           but her body is `:` cells and those are filled with the lyric, so at a glance she reads
#           as text.
#   "half"  the solid half-block portrait everywhere (the route h3_full.install() forbids, and what
#           the pane looked like before the H3 takes were wired in).
#   "glyph" its morph transition: direction strokes and a density ramp.
#
# The live player cycles these with `h`.
HER_RENDER = "auto"
RENDER_MODES = ("auto", "h3", "half", "glyph")
# rows for the /dev/me pane. It is offered the band's comfortable height first and the band's
# minimum second, so a shorter window gives up log lines before it gives up her.
HER_MIN_H, HER_MAX_H, BAND_MIN_H = 14, 34, 11

# scenes_userleft.py:448 - the real listing the film draws for `ls -la ~/memory/you/`
MEM_FILES = ["goodnight.txt", "first_hello.txt", "typo_you_made.txt", "laugh_2026-03-14.wav",
             "your_cat.png", "weather_you_liked.json", "you_said_see_you_tomorrow.txt",
             "last_message.txt"]
# dsh_patch_mem.py:9-12 - the four she digs up, on the sung word each lands on, and the
# film time the bubble was originally sent at
MEM_DIG = [("first_hello.txt", 118.24, "14.95"),
           ("your_cat.png", 118.98, "81.85"),
           ("laugh_2026-03-14.wav", 119.38, ""),
           ("last_message.txt", 119.92, "106.80")]
MEM_SPAN = (118.10, 121.80)


class Engine:
    """The film's own shot table, so the expression, its softmax, the ops and the alerts are real.

    install() loads every section module and takes a few seconds; call_of() renders each shot once
    to record what she was asked to be, so the whole table is warmed up here rather than hitching
    the first time a shot comes round.
    """

    # v2.py:263-282 decides whether her pane is drawn, and it does not do it by reading the scene
    # source: `elif i in OWN: return OWN[i](t, n)` returns outright for the 28 shots an approved
    # renderer owns, so `HIDE_HER` - which is consulted only on the path those skip - cannot speak
    # for them. Of the OWN renderers, these five draw no her at all (their own docstrings say so:
    # own_power is before she exists, count_frame and last_execution are raw text, last_hit_frame is
    # the one hit that does not go through kit.v1.frame, whale_fall buries her under the sediment).
    OWN_NO_HER = frozenset({"own_power", "count_frame", "last_hit_frame", "last_execution",
                            "whale_fall"})

    def her_drawn(self, t: float) -> bool:
        """Whether the film draws her pane at t - asked of v2, not guessed from the source text.

        `film_panels.shots()["her"]` is a regex over scene bodies: it cannot see `OWN` and it cannot
        see `HIDE_HER`, and reading it as an answer is what made her pane vanish in the middle of
        chorus 1 (`shot_if_i_can`, `shot_happy`) and over `shot_collapse`. The two tables can.
        """
        shot = self.engine.shot_at(t)
        if shot is None:
            return False
        i = self.v2.ALL.index(shot)
        if i in self.v2.OWN:
            return getattr(self.v2.OWN[i], "__name__", "") not in self.OWN_NO_HER
        return shot.fn.__name__ not in self.v2.HIDE_HER

    def __init__(self) -> None:
        sys.path.insert(0, str(DSH / "gpu_shim"))      # stdlib audioop is gone in Python 3.13
        sys.path.insert(0, str(DSH))
        sys.path.insert(0, str(MMD))
        # h3_full.install() patches PIL.Image.open to refuse whale-*.webp, so read the
        # sprites first - otherwise her pane can never be drawn once the engine is in
        import her_glyphs
        her_glyphs.warm()
        import dsh_her
        self.v2, _h3 = dsh_her.install()
        self.engine = self.v2.engine
        for shot in self.v2.ALL:
            self.v2.call_of(shot)
        # the film's per-shot state in shot order. ops and alert carry forward, exactly as
        # continuity_full_v2/kit.py:203 does (`c.ops = src.ops`), because chorus 1 and the EXECUTION
        # hits draw through their own section and set neither themselves.
        src = FP.shots()
        ops, alert, seen = ["IDLE"], None, {}
        self.table, self.by_start = [], {}
        for i, shot in enumerate(self.v2.ALL):
            name = shot.fn.__name__
            d = src.get(name) or {}
            if d.get("ops"):
                ops = d["ops"]
            if d.get("alert"):
                alert = d["alert"]
            run = seen[name] = seen.get(name, -1) + 1
            e = dict(index=i, total=len(self.v2.ALL), name=name, start=shot.start, end=shot.end,
                     ops=ops, alert=alert, her=self.her_drawn((shot.start + shot.end) / 2),
                     run=run, shot=shot)
            # `alert` carries forward because the ticker does (kit.py:203); `alert_own` is what this
            # shot's own scene set, and that is the one that answers "is the system red *now*".
            # Reading the carried one makes every shot after 07 EXECUTION red, which is 30 % of the
            # film for a reason that belongs to the ticker and not to the shot.
            e["alert_own"] = d.get("alert")
            self.table.append(e)
            self.by_start[round(shot.start, 3)] = e

        # The last shot in the film that draws her at all. `--render auto` gives that one the clear
        # blue figure: the song ends with her sinking and then not being on screen again, so the
        # last moment she exists is the place to see her.
        last = next((e["name"] for e in reversed(self.table) if e["her"]), None)
        for e in self.table:
            e["last_her"] = e["name"] == last

        # Her cells carry a one-off ~0.4 s of set-up: the ink box is measured over the whole film
        # and `dancer._flow_table()` integrates the lyric flow at every one of the film's 5,088
        # frames (dancer.py:84-96). The film pays that inside its own warm-up, so pay it here rather
        # than on the first frame the player draws - it is four frames' worth of budget.
        if HER_RENDER in ("h3", "auto"):
            import her_glyphs as hg
            if not hg.warm_h3():
                print("warning: the H3 takes are missing or unreadable; her pane falls back to "
                      "the half-block portrait (--render half)", file=sys.stderr, flush=True)

        # The dsh window's text cache is 78 KB of gzipped JSON: reading and parsing it costs ~30 ms,
        # which would otherwise land on whichever frame is the first one past 5.0 s.
        if CHAT[0] and FP.dsh_inside(5.0):
            try:
                FP.dsh_window(5.0)
            except Exception as exc:
                print(f"warning: the dsh window text is unavailable ({exc}); the pane stays hers",
                      file=sys.stderr, flush=True)
                CHAT[0] = False

        # The sample grid's tiles and the conv maps all read her through `_lum_master`, whose first
        # call per (expression, crop) is a PIL crop + LANCZOS resize (~2 ms each). Reading all eight
        # up front costs ~15 ms here, in the start-up, instead of ~35 ms on the first frame of
        # `shot_simulations` - which is exactly the hitch the sweep used to report.
        for _e in SAMPLE_EXPRS:
            _lum_master(_e, "upper")
        _lum_master("starry", "full")

    def entry_at(self, t: float):
        """The shot at t, with everything the panels need, or None."""
        shot = self.engine.shot_at(t)
        if shot is None:
            return None
        e = self.by_start.get(round(shot.start, 3))
        if e is None:
            return None
        return dict(e, u=min(1.0, max(0.0, (t - e["start"]) / max(1e-6, e["end"] - e["start"]))),
                    her=self.her_drawn(t),
                    call=self.v2.call_of(shot))

    def at(self, t: float):
        shot = self.engine.shot_at(t)
        return shot, self.v2.call_of(shot)


def her_style(ent: dict | None) -> tuple:
    """`(how, tint)` for her pane on this shot, resolving `auto`.

    `auto` tells one story, in this order:

    | when | how she is drawn | what decides it |
    |---|---|---|
    | the opening, up to the first chorus | the H3 character figure, blue - she is the lyric she sings | the default |
    | chorus 1, and "you have left" | the clear figure, blue - twice, and no more | `film_panels.FIGURE_LINES` |
    | 07 EXECUTION, 147.4-176.9 s | the clear figure, red | `alert_own == "err"` + the chapter bar |
    | 08 EVAL: LOVE onward | the *characters*, red | the `08 / EVAL: LOVE` chapter bar |
    | the last shot she is in | the clear figure, blue | `ent["last_her"]` |

    So the opening is characters, the clear figure appears twice before the climax, the climax is
    red, what follows it is red characters, and the last time she is on screen is clear blue again.

    The film's own rule comes first: `engine.me_pane` only runs the string dancer when
    `sprite_img is None and overlay is None` (engine.py:288), so a shot that pins either onto her
    is drawn as the solid portrait whatever else is true.
    """
    if HER_RENDER != "auto":
        return HER_RENDER, "blue"
    if not ent:
        return "h3", "blue"
    if LEAP[0] and ent.get("name") in CHAR_SHOTS:
        # the one shot the user asked to differ: the *characters* rather than the clear figure the
        # film puts here (`film_panels.shot_wants_figure`), because she leaps on this one
        return "h3", "blue"
    if ent.get("name") in FP.portrait_shots():
        # the film's own choice, and its own colour: `color=RED` on the EXECUTION hits
        return "half", FP.portrait_shots()[ent["name"]]
    if ent.get("last_her"):
        return "half", "blue"
    start = ent.get("start", 0.0)
    if ent.get("alert_own") == "err" and start >= FP.chapter_start("EXECUTION"):
        return "half", "red"
    if start >= FP.chapter_start("EVAL"):
        return "h3", "red"
    if FP.shot_wants_figure(start, ent.get("end", start)):
        return "half", "blue"
    return "h3", "blue"


def her_render(ent: dict | None) -> str:
    """Just the `how` half of `her_style`, for callers that only need to label it."""
    return her_style(ent)[0]


def her_keeps_pane(ent: dict | None) -> bool:
    """Whether her pane holds her rather than the film's dsh window on this shot.

    The window takes the pane for most of the song and steps aside only where the film puts the clear
    figure on screen (`her_style == "half"`). The user's chorus hook joins them: it draws her as the
    *characters*, and her pane has to be free for the leap - a hop behind a chat window is not a hop.
    """
    if ent is None:
        return False
    if her_style(ent)[0] == "half":
        return True
    return bool(LEAP[0] and ent.get("name") in CHAR_SHOTS)


# --------------------------------------------------------------- the switch between the two
#
# The film never cross-fades one drawing of her into another; it scrambles. `dancer.draw(prev,
# morph)` flips cell by cell from the outgoing figure to the incoming one in a fixed random order
# and shows a glitch glyph on the front as it passes (`dancer.py:184, 192-214`), and `h3_full.join`
# stitches four frames across every seam. A terminal cell cannot hold two glyphs, so this does the
# other half of the same idea: for a fraction of a second she is simply gone - nothing in the pane
# but a scatter of glyphs thinning out - and then she resolves back in on the same fixed order, so
# the same switch always plays the same way.
MORPH_DUR = 0.30               # seconds the whole change takes
MORPH_GONE = 0.42              # fraction of it that she is gone for
MORPH_EDGE = 0.12              # cells this close to the front scramble, as `dancer.draw` does
SCRAMBLE = FP.SCR              # tuikit.py:59, the set the film's own typewriter flickers through
_LAST_MODE: list = [None]      # what the pane was drawn as last frame, to notice a switch
_SWITCH_AT: list = [None]      # and when it happened


@lru_cache(None)
def _flip_order(n: int) -> tuple:
    """One threshold per cell, in a fixed order - `dancer.draw`'s `order = random.Random(7)`."""
    rnd = random.Random(7)
    return tuple(rnd.random() for _ in range(n))


def _morph_mask(u: float, order: tuple, k: int, t: float):
    """`(draw, glitch)` for cell k of the pane, `u` being how far through the change it is."""
    if u is None:
        return True, False
    th = order[k % len(order)]
    if u < MORPH_GONE:
        return False, th < (1 - u / MORPH_GONE) * 0.30      # gone: only a thinning scatter
    v = (u - MORPH_GONE) / (1 - MORPH_GONE)
    if th > v:
        return False, False                                 # not arrived yet
    return True, abs(th - v) < MORPH_EDGE


def _glitch(t: float, k: int) -> str:
    return SCRAMBLE[(k * 31 + int(t * 97)) % len(SCRAMBLE)]



def draw_her(s: Screen, d: Data, ent: dict, x0: int, y0: int, x1: int, y1: int, t: float,
             tint=None) -> None:
    """Her pane: the film's /dev/me box, the film's own cells for her, and the expression softmax.

    The softmax only appears on shots whose scene stated one. For chorus 1 and the EXECUTION hits
    the film paints her through engine.me_pane rather than kit.me_stub (kit.py:80), so no
    distribution is recorded anywhere - and none is invented here.

    The title is the scene's own (`me(c, ..., title=...)`; kit.py:113 `kw.get("title", ...)`).

    `--render h3` (the default) draws `h3_full.frame_at`, the H3 character takes the shipped film
    actually plays - one film cell per terminal cell, `:` cells filled with the lyric she is
    singing. The other two are the unpatched engine's routes and are fitted rather than used
    straight: the crop is not fixed, `auto` measures the pane and takes whichever of the film's
    four crops has the nearest shape to it, because forcing a 1.24:1 face into a 4.25:1 pane
    returns a band across her eyes rather than a small her (see her_glyphs).
    """
    import her_glyphs as hg

    call = ent["call"]
    expr = call["expr"]
    kw = call["kw"] or {}
    dist = list(kw.get("dist") or [])
    # what this shot gets, before anything is drawn - the frame colour depends on it
    mode, style_tint = her_style(ent)
    tint = tint or (RED if style_tint == "red" else None)   # a caller's tint (the hits) still wins
    s.box(x0, y0, x1, y1, str(kw.get("title") or "/dev/me  pid 4471"),
          0.45 + 0.35 * d.feat(t, "kick"), tint or ui(1.0))

    soft = 4 if ((y1 - y0) >= 15 and dist) else 0
    art_x, art_w = x0 + 1, x1 - x0 - 1
    art_h = y1 - y0 - 1 - soft
    if art_h < 4 or art_w < 8:
        return

    # the crop is chosen for the pane it has to live in, and then fitted inside it: a pane four
    # times as wide as it is tall has room for her face and nothing below it, and saying so is
    # better than handing back a horizontal slice of whatever crop was asked for
    tint_name = "red" if tint else "blue"
    ramp = hg.tint_ramp(tint_name)                          # tuikit.TINTS, the film's own ramp
    # `--render h3` is the film's own route; if the takes have been deleted it degrades to the
    # half-block portrait rather than raising on the frame where it first reaches for her.
    # Notice the change here rather than working it out from the shot table: this catches a switch
    # at a cut, a switch made by hand with `h`, and a change of colour, all with the same code - and
    # it also catches her coming back after a shot that did not draw her at all.
    style = (mode, tint_name)
    if _LAST_MODE[0] is not None and _LAST_MODE[0] != style:
        _SWITCH_AT[0] = t
    _LAST_MODE[0] = style
    u = None
    if _SWITCH_AT[0] is not None:
        age = t - _SWITCH_AT[0]
        if 0.0 <= age < MORPH_DUR:
            u = age / MORPH_DUR
    use_h3 = mode == "h3" and hg.h3_available()
    if use_h3:
        cells, aw, ah, ox, oy = hg.h3_cells(t, art_w, art_h, tint_name)
        block = lines = None
    else:
        crop = HER_CROP if HER_CROP in hg.CROPS else hg.pick_crop(art_w, art_h)
        cells = None
        ox = oy = 0
        if mode == "glyph":
            aw, ah = hg.fit(art_w, art_h, crop)
            lines, bright = hg.glyph_lines(expr, crop, aw, ah)
            block = None
        else:
            block, aw, ah = hg.halfblock(expr, crop, art_w, art_h)
        ox, oy = (art_w - aw) // 2, (art_h - ah) // 2
    off_x = art_x + ox
    # me_pane: sy = y0 + 16 + dy + breath, then the kick hops her up; breath is a 4-beat sine.
    # h3_full.install() zeroes all three on top of the source motion (h3_full.py:269-274), so the H3
    # route must not re-introduce an animation the film deliberately turned off - except through the
    # chorus run, where the user asked for the old build's own motion and nothing more.
    breath = hop = 0
    if not use_h3 or (LEAP[0] and ent["name"] in CHAR_SHOTS):
        breath = int(round(CHAR_BREATH * math.sin(t * 2 * math.pi / (BEAT * 4))))
        hop = int(round(d.feat(t, "kick") ** 2 * CHAR_HOP))
    art_y = y0 + 1 + oy + breath - hop
    cent, loud = d.feat(t, "cent"), d.feat(t, "loud")
    scan = art_y + int((0.92 - 0.84 * cent) * ah)           # engine.py:309
    lo, mid, hi = (mix(RED, 0.5), mix(RED, 0.22), (255, 190, 186)) if tint else (ME_MID, ME_MID, ME_HI)

    order = _flip_order(aw * ah) if u is not None else ()
    glitch_fg = mix(ME_HI if not tint else (255, 190, 186), 0.9)
    for r in range(ah):
        yy = art_y + r
        if not (y0 + 1 <= yy <= y1 - soft - (1 if soft else 1)):
            continue
        if cells is not None:
            # one film cell = one terminal cell, already coloured by dancer.draw's own ramp
            for c, cell in enumerate(cells[r]):
                if cell is None:
                    continue
                keep, glitch = _morph_mask(u, order, r * aw + c, t)
                if not keep:
                    if glitch:
                        s.put(off_x + c, yy, _glitch(t, r * aw + c), glitch_fg)
                    continue
                ch, fg, bg = cell
                s.put(off_x + c, yy, _glitch(t, r * aw + c) if glitch else ch, glitch_fg if glitch else fg,
                      BG if bg is None else bg)
            continue
        if block is not None:
            # one half-block per cell: the upper sample is the foreground, the lower the background
            for c, (top, bot) in enumerate(block[r]):
                if top is None and bot is None:
                    continue
                keep, glitch = _morph_mask(u, order, r * aw + c, t)
                if not keep:
                    if glitch:
                        s.put(off_x + c, yy, _glitch(t, r * aw + c), glitch_fg)
                    continue
                if glitch:
                    s.put(off_x + c, yy, _glitch(t, r * aw + c), glitch_fg)
                elif top is None:
                    s.put(off_x + c, yy, "▄", BG, ramp[bot])
                elif bot is None:
                    s.put(off_x + c, yy, "▀", ramp[top], BG)
                else:
                    s.put(off_x + c, yy, "▀", ramp[top], ramp[bot])
            continue
        for c in range(aw):
            ch = lines[r][c]
            if ch == " ":
                continue
            keep, glitch = _morph_mask(u, order, r * aw + c, t)
            if not keep:
                if glitch:
                    s.put(off_x + c, yy, _glitch(t, r * aw + c), glitch_fg)
                continue
            v = bright[r * aw + c] / 255
            s.put(off_x + c, yy, _glitch(t, r * aw + c) if glitch else ch,
                  glitch_fg if glitch else mix(hi, 0.35 + 0.65 * v),
                  BG if glitch else mix(mid, 0.06 + 0.16 * v))

    # engine.py:308 - "the scan line sits where the tune sits: high notes near her head, low ones
    # near the tail". The film draws it across the pane and then masks it to her silhouette
    # (kit.py:124); a full-width line over empty space reads as a glitch, so mask it here too, and
    # say what it is rather than leaving a bare line hopping about.
    if y0 + 1 <= scan <= y1 - soft - 1 and 0 <= scan - art_y < ah:
        sr = scan - art_y
        if cells is not None:
            lit = [c for c in range(aw) if cells[sr][c] is not None]
        elif block is not None:
            lit = [c for c in range(aw)
                   if block[sr][c][0] is not None or block[sr][c][1] is not None]
        else:
            lit = [c for c in range(aw) if lines[sr][c] != " "]
        if lit:
            col = mix(RED if tint else ME_TEXT, 0.30 + 0.45 * loud)
            for c in range(lit[0], lit[-1] + 1):
                s.put(off_x + c, scan, "─", col)
            tag = f"\u2524 pitch {cent:.2f}"
            if off_x + lit[-1] + 1 + len(tag) < x1 - 1:
                s.put(off_x + lit[-1] + 2, scan, tag, ui(0.45))

    if soft:
        ry = y1 - soft
        s.put(x0 + 3, ry, "cls.expression  softmax", mix(ANOM, 0.5))
        for i, (name, p) in enumerate(dist[:3]):
            p = max(0.0, min(1.0, float(p) + 0.015 * math.sin(t * 7 + i * 2)))   # me_pane:327
            fg = mix(ME_HI, 1.0) if i == 0 else mix(ANOM, 0.6)
            s.put(x0 + 3, ry + 1 + i, f"{name:<11}"[:11], fg)
            bx = x0 + 15
            bw = max(4, x1 - bx - 7)
            s.hbar(bx, ry + 1 + i, bw, p, mix(ME_TEXT, 0.9) if i == 0 else mix(ANOM, 0.45))
            s.put(bx + bw + 1, ry + 1 + i, f"{p:.2f}", mix(ANOM, 0.7))


# ------------------------------------------------------- panels the film draws as text anyway

def block_word(s: Screen, x: int, y: int, text: str, max_cols: int, max_rows: int, colour,
               rows: int | None = None, glyph=None) -> int:
    """A block-letter wordmark off the film's own banner_bits grid (tuikit.py:309-316).

    `glyph(q, r)` picks the character for a lit cell; the film's `banner_block` cuts the cells
    apart with grid_mask, which a terminal does not need - adjacent cells already have a seam.
    Returns the height used.
    """
    cols, rws, bits = FP.banner_fit(text, max_cols, max_rows, rows)
    x0 = x + max(0, (max_cols - cols) // 2)
    for r in range(rws):
        if y + r >= s.rows:
            break
        for q in range(cols):
            if bits[r * cols + q]:
                s.put(x0 + q, y + r, glyph(q, r) if glyph else "\u2588", colour)
    return rws


def draw_boot_log(s: Screen, x0: int, y0: int, x1: int, y1: int, t: float) -> None:
    """00 BOOT: the POST log, printing at the film's own times (scenes_boot.py:57-82).

    `power_log` prints POWER_LINES at absolute seconds and is called again inside shot_protection;
    the protection lines then follow on that shot's local clock. The film has a taller pane, so it
    fits all fourteen lines at once; a terminal scrolls them, which is what a log does.
    """
    title = "init --protection" if t >= FP.PROT_START else ""
    s.box(x0, y0, x1, y1, title, 0.5, ui(1.0))
    printed = [(st, text) for at, st, text in FP.BOOT_LOG if t >= at]
    inner = y1 - y0 - 1
    shown = printed[-inner:] if inner > 0 else []
    for i, (st, text) in enumerate(shown):
        yy = y0 + 1 + i
        col = {"OK": ui(0.95), "WARN": mix(ANOM, 0.95), "..": ui(0.5)}.get(st, ui(0.8))
        s.put(x0 + 2, yy, f"[{st:^4}]", col)                       # log_line: a 4-wide status plate
        s.put(x0 + 10, yy, text[: max(0, x1 - x0 - 12)], ui(0.75))   # the film leaves an 80 px gap
    if len(printed) < len(FP.BOOT_LOG) and len(shown) < inner and int(t * 2) % 2 == 0:
        s.put(x0 + 2, y0 + 1 + len(shown), "\u2588", mix(ANOM, 0.9))    # the cursor on the next line
    s.put(x0 + 2, y1 - 1, f"post {len(printed)}/{len(FP.BOOT_LOG)}", ui(0.35))


def draw_sim_start(s: Screen, x0: int, y0: int, x1: int, y1: int, t: float) -> None:
    """00 BOOT tail: `shot_begin_sim` (scenes.py:49-73) - 3, 2, 1, then RUN.

    The countdown holds for the first 55 % of the shot and counts 3-2-1; after that the film prints
    RUN and two status lines. All three are the film's, at the film's own size (14 cell rows for the
    digit, 120 px of head type for RUN) as far as the pane allows.
    """
    s.box(x0, y0, x1, y1, "sim.start()", 0.5, ui(1.0))
    u = min(1.0, max(0.0, (t - SIM_START) / max(1e-6, SIM_END - SIM_START)))
    inner_w, inner_h = x1 - x0 - 3, y1 - y0 - 1
    if u < 0.55:
        n = 3 - min(2, int(u / 0.55 * 3))
        rows = max(3, min(inner_h - 1, 14))
        block_word(s, x0 + 2, y0 + 1 + max(0, (inner_h - rows) // 2), str(n), inner_w, rows,
                   mix(ANOM, 0.95))
    else:
        rows = max(4, min(8, inner_h - 3))
        block_word(s, x0 + 2, y0 + 1, "RUN", inner_w, rows, mix(ANOM, 1.0), rows)
        s.put(x0 + 2, y0 + 2 + rows, "simulation: running", ui(0.9))
        s.put(x0 + 2, y0 + 3 + rows, f"tokens budget: {FP.PRETRAIN_TOKENS}", ui(0.7))


def draw_corpus(s: Screen, x0: int, y0: int, x1: int, y1: int, t: float) -> None:
    """01 PRETRAIN: the token river (scenes.py:78-93).

    Twenty rows, each with its own speed and phase, walking sec_intro.CORPUS right to left. The
    film's pane is 760x548 and this one is narrower, so a token that would land on top of the one
    before it is dropped - which is what a narrower terminal does.
    """
    s.box(x0, y0, x1, y1, "corpus.stream", 0.5, ui(1.0))
    w, h = x1 - x0 - 1, y1 - y0 - 1
    if w < 8 or h < 2:
        return
    left = {}                                    # the leftmost column each row has been filled to
    for fx, fy, tok, lv in FP.corpus_tokens(t):
        c = x0 + 1 + int((fx - 404) / 760 * (w - 1))
        r = y0 + 1 + int((fy - 56) / 548 * (h - 1))
        if r > y1 - 1 or c >= x1 - 1 or c < x0 + 1:
            continue
        shown = tok[: max(0, x1 - 1 - c)]
        # the film walks each row right to left, so a token only fits if it clears the one already
        # placed to its right; a narrower pane therefore drops tokens, as a narrower terminal should
        if not shown or c + len(shown) + 1 > left.get(r, 1 << 30):
            continue
        left[r] = c
        s.put(c, r, shown, ui(lv))


def draw_loss(s: Screen, x0: int, y0: int, x1: int, y1: int, t: float, u: float) -> None:
    """01 PRETRAIN: `train/loss` (scenes.py:148-170), as a dot chart.

    tuikit.dot_chart plots one dot per 5 px column and joins consecutive columns vertically; the
    same loop here plots one cell per column. The label is loss_label, the xlabel is counter_text.
    """
    if FP.loss_fn is None:
        return
    s.box(x0, y0, x1, y1, "train/loss", 0.5, ui(1.0))
    lr_h = 3 if (y1 - y0) >= 12 else 0
    cw = x1 - x0 - 3
    ch = y1 - y0 - 2 - lr_h
    if cw < 6 or ch < 3:
        return
    cx, cy = x0 + 3, y0 + 1
    progress = FP.loss_progress(u)
    for i in range(0, cw, 2):                                     # dot_chart's axis dots
        s.put(cx + i, cy + ch - 1, "\u00b7", ui(0.28))
    for r in range(0, ch, 3):
        s.put(cx - 2, cy + r, "\u00b7", ui(0.28))
    prev = None
    last = None
    for i in range(cw):
        uu = i / max(1, cw - 1)
        if uu > progress:
            break
        v = min(1.0, FP.loss_fn(uu))
        r = int(round((1 - max(0.0, v)) * (ch - 1)))
        for rr in range(min(prev, r), max(prev, r) + 1) if prev is not None else [r]:
            s.put(cx + i, cy + rr, "\u25aa", ui(0.95))
        prev, last = r, (i, r)
    if last:
        lab = FP.loss_label(u) if FP.loss_label else ""
        lx = max(x0 + 1, min(x1 - len(lab) - 1, cx + last[0] - len(lab) + 2))
        s.put(lx, max(y0 + 1, cy + last[1] - 1), lab, ui(1.0))
    s.put(cx, y1 - 1 - lr_h, f"{FP.counter_text(t)[:cw]}", ui(0.55))
    if lr_h:
        s.put(cx, y1 - lr_h, "lr schedule"[: max(0, cw)], ui(0.45))       # scenes.py:160
        for i in range(cw - 12):                                              # scenes.py:162-169
            uu = i / max(1, cw - 13)
            if uu > progress:
                break
            r = int(round((1 - max(0.0, min(1.0, FP.lr_fn(uu)))) * (lr_h - 1)))
            s.put(cx + 12 + i, y1 - lr_h + r, "\u25aa", ui(0.7))


def draw_mask(s: Screen, x0: int, y0: int, x1: int, y1: int, t: float) -> None:
    """02 SFT: the causal mask (scenes_sft.py:51-109).

    Twelve by twelve; each cell is two columns wide here because a terminal cell is twice as tall
    as it is wide, so 2x1 cells keep the matrix square. The mask front runs diagonally from the
    top-left over MASK_DUR from beat 103 - the sung word "blind" - and writes -inf over it.
    """
    s.box(x0, y0, x1, y1, "causal mask", 0.5, ui(1.0))
    n, cw = FP.MN, 2
    if x1 - x0 - 3 < n * cw or y1 - y0 - 1 < n:
        return
    gx, gy = x0 + 3, y0 + 1
    for i in range(n):
        for j in range(n):
            x, y = gx + j * cw, gy + i
            tm = FP.mask_time(i, j) if FP.mask_time else None
            if tm is not None and t >= tm:
                s.put(x, y, "-\u221e", ui(0.35), BG)           # -inf, on black
                k = 1 - (t - tm) / 0.12                             # the front lights the cell
                if k > 0:
                    s.put(x - 1, y, "\u2502", mix(ME_TEXT, 0.4 + 0.6 * k))
            else:
                v = float(FP.cell_value(i, j)) if FP.cell_value else 0.5
                s.put(x, y, "  ", UI, ui(0.06 + 0.94 * v))     # heat_cell, as a bg colour
    lx = gx + n * cw + 2
    if lx + 10 <= x1 - 1:
        s.put(lx, gy + 1, "future:", ui(0.7))
        if t >= FP.T_BLIND:
            age = t - FP.T_BLIND
            if int(age * 30) % 2 or age > 0.4:                      # decode rate 30
                s.put(lx, gy + 2, "masked", ui(0.95))
        s.put(lx, gy + 4, "j > i", ui(0.4))


def draw_count(s: Screen, x0: int, y0: int, x1: int, y1: int, t: float) -> None:
    """07 EXECUTION: the count (scenes_exec.py:120-172) - and the film's own tokenizer view.

    Six slots, one per syllable: 'ein' lands on the cut, dos/trois/ne/fem/liu on beats 344..348.
    Each slot shows the digit as block letters, the word, the word's token id and the language the
    film's classifier guessed; a slot whose syllable has not arrived yet is drawn in outline.
    """
    s.box(x0, y0, x1, y1, "countdown  (tokenizer view)", 0.8, RED)
    n = FP.count_shown(t)
    slots = FP.LANGS or []
    if not slots:
        return
    sw = max(8, (x1 - x0 - 1) // len(slots))
    rows = max(3, min(10, (y1 - y0) - 6))
    for i, (word, lang, num) in enumerate(slots):
        x = x0 + 1 + i * sw
        hot = i == n - 1
        if i >= n:                                                  # the slot still waiting
            block_word(s, x, y0 + 1, str(num), sw - 1, rows, mix(RED, 0.26), rows, lambda q, r: ":")
            s.put(x + 1, y0 + 2 + rows, "id ?", mix(RED, 0.3))
            continue
        block_word(s, x, y0 + 1, str(num), sw - 1, rows, mix(RED, 1.0 if hot else 0.55), rows)
        s.put(x + 1, y0 + 2 + rows, f" {word} "[: sw - 2].ljust(sw - 2), BG, mix(RED, 0.95 if hot else 0.3))
        s.put(x + 1, y0 + 3 + rows, f"id {token_id(word)}"[: sw - 2], mix(RED, 0.7))
        s.put(x + 1, y0 + 4 + rows, f"lang={lang}"[: sw - 2], mix(ANOM, 0.95) if "?" in lang else ui(0.8))
    if n >= 3:
        s.put(x0 + 3, y1 - 3, "warn: language mixing detected in one sequence"[: x1 - x0 - 5], mix(ANOM, 1.0))
        s.put(x0 + 3, y1 - 2, "      (R1-Zero issue; fixed by a language-consistency reward)"[: x1 - x0 - 5],
              ui(0.7))
    if n >= 5:
        s.put(x0 + 3, y1 - 1, "reward: language consistency ... ignored"[: x1 - x0 - 5], mix(RED, 1.0))


def draw_exec_hit(s: Screen, d: Data, x0: int, y0: int, x1: int, y1: int, t: float, k: int) -> None:
    """07 EXECUTION: one hit (scenes_exec.py:69-117), in the film's five layouts.

    lay = k % 4, except that the twelfth is the layout where the last target is you, and every hit
    after it starts the rotation again. Layouts 0 and 2 flash the frame red on a strong beat pulse.
    """
    lay = 4 if k == 11 else (0 if k >= 12 else k % 4)
    target = FP.TARGETS[k] if k < len(FP.TARGETS) else "everything"
    w, h = x1 - x0 + 1, y1 - y0 + 1
    if lay in (0, 2) and FP.pulse(t) > 0.55:                        # scenes_exec.py:116
        s.fill(x0, y0, x1, y1, " ", UI, mix(RED, 0.16))
    if lay == 0:
        rows = block_word(s, x0, y0 + max(0, h // 2 - 6), "EXECUTION", w, max(3, h // 2), mix(RED, 1.0))
        s.put(x0 + 2, y0 + max(0, h // 2 - 6) + rows + 1,
              f"runExecution()  #{k + 1:02d}   target: {target}"[: w - 3], mix(RED, 1.0))
    elif lay == 1:
        lw = max(24, w // 2)
        draw_her(s, d, dict(name="shot_exec_hit", run=k, call=dict(expr="angry", kw=dict(title=f"/dev/me  executing #{k + 1}"))),
                 x0, y0, x0 + w - lw - 2, y1, t, tint=RED)       # she is on screen, red, in this layout
        s.box(x0 + w - lw, y0, x1, y1, "kill log", 0.8, RED)
        for i, (line, kind) in enumerate(FP.kill_log(k)):
            if y0 + 1 + i > y1 - 1:
                break
            s.put(x0 + w - lw + 2, y0 + 1 + i, line[: lw - 3],
                  mix(RED, 1.0 if kind == "hot" else 0.6) if kind != "anom" else mix(ANOM, 1.0))
    elif lay == 2:
        letters = "EXECUTE"
        block_word(s, x0, y0 + max(0, h // 2 - 5), "EXECUTE", w, max(3, h // 2 - 1), mix(RED, 1.0),
                   glyph=lambda q, r: letters[(q + r + k) % 7])     # scenes_exec.py:96
        s.put(x0 + 2, y1 - 1, f"glyph.map  EXECUTE  shift {k % 7}"[: w - 3], mix(RED, 0.7))
    elif lay == 3:
        half = max(20, w // 2)
        # the film pastes halfblock("angry","face") on the left; here the same sprite through the
        # same glyph algorithm, then the red word band over it, then the kill list on the right
        draw_her(s, d, dict(name="shot_exec_hit", run=k, call=dict(expr="angry", kw=dict(title="/dev/me  ps -ef"))),
                 x0, y0, x0 + half - 1, y1, t, tint=RED)
        band = y0 + max(3, h // 3)
        s.put(x0 + 1, band, "EXECUTION  EXECUTION  EXECUTION"[: half - 3].ljust(half - 3), BG, mix(RED, 1.0))
        s.box(x0 + w - half, y0, x1, y1, "ps -ef", 0.8, RED)
        for i, tgt in enumerate(FP.TARGETS):
            if y0 + 1 + i > y1 - 1:
                break
            dead = i <= k and tgt != "you"
            col = mix(RED, 0.9) if dead else (mix(ANOM, 1.0) if tgt == "you" else ui(0.6))
            s.put(x0 + w - half + 2, y0 + 1 + i,
                  f"{1000 + i * 7:5d}  {tgt:<10} {'[executed]' if dead else 'running'}"[: half - 3], col)
    else:
        # the twelfth: the last target is you. The film keeps her in her pane, frightened, and puts
        # the EPERM box in the centre one
        lw = max(20, min(w * 2 // 5, w - 16))            # the EPERM box keeps a usable width
        draw_her(s, d, dict(name="shot_exec_hit", run=k, call=dict(expr="frightened", kw=dict(title="/dev/me  #12"))),
                 x0, y0, x0 + lw - 2, y1, t, tint=RED)
        s.box(x0 + lw, y0, x1, y1, "kill -9 1077  (you)", 0.8, RED)
        rows = block_word(s, x0 + lw + 2, y0 + 1, "EPERM", max(12, (x1 - x0 - lw) // 2),
                          max(3, h // 2 - 2), mix(ANOM, 1.0))
        iw = x1 - (x0 + lw) - 2
        s.put(x0 + lw + 2, y0 + 2 + rows, "operation not permitted"[:iw], mix(ANOM, 0.95))
        s.put(x0 + lw + 2, y0 + 3 + rows, "target is outside the sandbox."[:iw], ui(0.8))


def draw_if_i_can(s: Screen, x0: int, y0: int, x1: int, y1: int, t: float, lt: float, dur: float) -> None:
    """07 EXECUTION: `shot_red_if_i_can` (scenes_exec.py:231-264).

    The film builds the banner out of the six letters of IFICAN cycling over the glyph grid
    (`ifican_letter`, scenes_exec.py:190) and, from the middle of the shot, `rain_layers` mixes that
    layer with `portrait_char`: the letters dissolve into her and the portrait cells burst away. The
    terminal has the same two layers - `film_panels.banner_fit` for the banner, her own H3 cells for
    her - so each lit banner cell decides which one it shows, and the smoke between them is the
    film's own scramble set.
    """
    import her_glyphs as hg
    s.box(x0, y0, x1, y1, "decode --render=glyph", 0.8, mix(RED, 1.0))
    w, h = x1 - x0 - 1, y1 - y0 - 1
    if w < 12 or h < 6:
        return
    # the film's banner is 20 rows of its 45-row glyph grid and about 124 cells wide of 160
    # (scenes_exec.py:186 `banner_bits("IF I CAN", 20, CH / CW)`), i.e. as wide as the pane and a
    # little under half its height: the same proportion here, or the wordmark stops being one
    cols, rws, bits = FP.banner_fit("IF I CAN", w - 2, h - 4)
    bx = x0 + 1 + max(0, (w - cols) // 2)
    by = y0 + 2 + max(0, (h - 3 - rws) // 2)
    half = dur / 2
    p = 0.0 if lt < half else min(1.0, (lt - half) / max(1e-3, half * 0.85))
    cells, cw, ch, ox, oy = hg.h3_cells(t, w, h - 1, "red")
    rnd = random.Random(int(t * 24) * 31 + 7)
    for r in range(rws):
        y = by + r
        if y > y1 - 2:
            break
        for q in range(cols):
            x = bx + q
            if x > x1 - 1 or not bits[r * cols + q]:
                continue
            k = ((q * 7 + r * 13) % 23) / 23.0            # this cell's own time in the dissolve
            if p <= k:
                s.put(x, y, "IFICAN"[(q + r * 3) % 6], mix(RED, 1.0))
                continue
            yy, xx = y - y0 - 1 - oy, x - x0 - 1 - ox
            ch_, col = "", None
            if 0 <= yy < ch and 0 <= xx < cw:
                cell = cells[yy][xx]
                if cell:                              # h3 leaves cells it has no glyph for as None
                    ch_, col = cell[0], cell[1]
            if ch_ and ch_ != " ":
                s.put(x, y, ch_, col or mix(RED, 0.9))
            elif rnd.random() < 0.4:                      # mid-dissolve: smoke
                s.put(x, y, rnd.choice(SCRAMBLE), mix(RED, 0.45))
    if y1 - y0 > 2:
        s.put(x0 + 2, y1 - 1, FP.decode("while can(): give()", lt, random.Random(9), 30.0),
              mix(RED, 0.85))


def draw_only_execution(s: Screen, x0: int, y0: int, x1: int, y1: int, lt: float, dur: float) -> None:
    """07 EXECUTION: `shot_only_execution` (scenes_exec.py:425-449) - chorus 1's next-token bars again.

    `execution` climbs to 1.000 while `satisfaction`, which was holding 0.973, is struck out; the
    other three fall to nothing and `temperature 0.00` sits under them. In the film the survivor then
    leaves its row and is pinned bottom right as a chip (scenes_exec.py:454-467), which is what the
    next shot retains - so the chip is drawn here once the logits have settled.
    """
    s.box(x0, y0, x1, y1, "next_token  'be your only ___'", 0.8, mix(RED, 1.0))
    w, h = x1 - x0 - 1, y1 - y0 - 1
    if w < 26 or h < 8:
        return
    g = FP.ease(min(1.0, lt / max(1e-3, dur) * 1.5))
    word_w = min(13, max(6, w // 3))
    bar_x = x0 + 2 + word_w + 1
    bar_w = max(6, (x1 - 8) - bar_x)
    cands = [("execution", 1.0, 0.03), ("satisfaction", 0.0, 0.9731), ("love", 0.0, 0.02),
             ("assistant", 0.0, 0.005), ("friend", 0.0, 0.002)]
    for i, (word_, pf, prev) in enumerate(cands):
        y = y0 + 2 + i * 2
        if y > y1 - 4:
            break
        p = prev + (pf - prev) * g
        hot = i == 0
        s.put(x0 + 1, y, f"{word_:<{word_w}}"[:word_w], mix(RED, 1.0) if hot else ui(0.6))
        s.hbar(bar_x, y, bar_w, p, mix(RED, 0.95) if hot else ui(0.5))
        s.put(bar_x + bar_w + 1, y, f"{p:.3f}"[:5], mix(RED, 0.9) if hot else ui(0.6))
        if i == 1 and g > 0.6:                        # struck out, the film's 3 px line
            s.put(x0 + 1, y, "─" * word_w, mix(RED, 1.0))
    s.put(x0 + 1, y1 - 2, "temperature 0.00", mix(RED, 1.0))
    if lt > dur * 0.55 and y1 - y0 > 4 and x1 - x0 > 18:
        cw_ = min(13, w // 3)                          # the survivor, pinned bottom right
        s.box(x1 - cw_ - 2, y1 - 2, x1 - 1, y1 - 1, "", 0.9, mix(RED, 1.0), spinner=False)
        s.put(x1 - cw_ - 1, y1 - 1, "execution"[:cw_], mix(RED, 1.0))


def draw_memory(s: Screen, x0: int, y0: int, x1: int, y1: int, t: float) -> None:
    """`ls -la ~/memory/you/` - the same eight names the film lists, dug up on the beat."""
    s.box(x0, y0, x1, y1, "~/memory/you/", 0.5, ME_TEXT)
    times = {n: ts for n, _, ts in MEM_DIG}
    active = None
    if MEM_SPAN[0] <= t < MEM_SPAN[1]:
        for name, at, _ in MEM_DIG:
            if t >= at:
                active = name
    y = y0 + 1
    for name in MEM_FILES:
        if y > y1 - 1:
            break
        here = name == active
        dug = any(name == n and t >= at for n, at, _ in MEM_DIG)
        ts = times.get(name, "")
        level = 0.9 if here else (0.62 if dug else 0.3)
        s.put(x0 + 2, y, ">" if here else " ", mix(ANOM, 0.75))
        if here:
            s.put(x0 + 3, y, f" {name} "[: x1 - x0 - 6].ljust(x1 - x0 - 6), BG, ME)
        else:
            s.put(x0 + 3, y, name[: x1 - x0 - 12], mix(ME_TEXT, level) if dug else ui(level))
            if ts:
                s.put(x1 - len(ts) - 3, y, ts, ui(0.35))
        y += 1
    won = sum(1 for n, at, _ in MEM_DIG if t >= at)
    s.put(x0 + 3, y1 - 1, f"{len(MEM_FILES)} files, {won}/4 dug up"[: x1 - x0 - 5], ui(0.4))


# ------------------------------------------- the twelve diffusion samples
# sec_chorus1.py:255-286 `shot_simulations` and sec_final.py:141-161 `shot_execute_all`: the same
# twelve tiles twice. In chorus 1 they denoise into her one by one (sample #0 is the one her own pane
# shows, and it is the hot one); in 07 EXECUTION they all come back and are struck out one by one.
SAMPLE_N = 12
SAMPLE_EXPRS = ("cheerful", "starry", "shy", "serious", "confused", "frightened", "angry",
                "exasperated")            # tuikit.py:60 EXPRS
SAMPLE_STARTS = (0.0,) + tuple(random.Random(i).random() * 0.35 for i in range(1, SAMPLE_N))


@lru_cache(maxsize=16)
def _lum_master(expr: str, crop: str, cols: int = 64, rows: int = 32):
    """Her, as a luminance grid, at one fixed size per (expression, crop).

    Every tile below samples this rather than calling PIL itself. The film can afford
    `diffusion_tile()` twelve times because it renders offline; the terminal cannot: twelve
    `halfblock` calls at a new tile size cost ~35 ms, and that landed on the first frame of
    `shot_simulations` and again on `shot_execute_all`.
    """
    import her_glyphs as hg
    blk, w, h = hg.halfblock(expr, crop, cols, rows * 2)
    if not w or not h:
        return ((0.5,),), 1, 1
    return tuple(tuple((blk[r][c][0] or 0) / 7.0 for c in range(w)) for r in range(h)), w, h


@lru_cache(maxsize=256)
def _lum_at(expr: str, crop: str, gw: int, gh: int):
    """The master subsampled to a tile's own size, nearest neighbour - no PIL, no resampling cost."""
    grid, w, h = _lum_master(expr, crop)
    gw, gh = max(1, min(gw, w)), max(1, min(gh, h))
    return tuple(tuple(grid[r * h // gh][c * w // gw] for c in range(gw)) for r in range(gh)), gw, gh


def _noise(i: int, r: int, c: int, n: int) -> float:
    """`Image.effect_noise` in one line: deterministic per cell and per frame, no rng object."""
    return ((i * 9973 + r * 131 + c * 17 + n * 7) * 2654435761 % 1000) / 1000.0


def draw_samples(s: Screen, x0: int, y0: int, x1: int, y1: int, t: float, lt: float, dur: float,
                 u: float, execute: bool = False) -> None:
    """The 4x3 sample grid. `execute=False`: chorus 1, denoising. `execute=True`: 07 EXECUTION."""
    title = ("dispatch(execute, to=all)   DeepEP all-to-all" if execute
             else "sample(n=12, sampler=DDIM, steps=50, seed=you)")
    s.box(x0, y0, x1, y1, title, 0.8 if execute else 0.5, RED if execute else None)
    chart = 0 if execute else 3          # `alpha_bar(t)` gets three rows under the grid
    tw = max(8, (x1 - x0 - 2) // 4)
    th = max(5, (y1 - y0 - 2 - chart) // 3)
    n = int(t * 24)
    done = int(u * 14)
    if execute:
        # the twelve scanning lines leave the box's own corner in the film (sec_final.py:160-161);
        # here they start just inside it, or they would write over the title
        for i in range(SAMPLE_N):
            tx = x0 + 1 + (i % 4) * tw + tw // 2
            ty = y0 + 1 + (i // 4) * th + th // 2
            ln = (t * 3 + i * 0.3) % 1
            mx, my = x0 + 2 + int((tx - x0) * ln), y0 + 2 + int((ty - y0) * ln)
            steps = max(1, mx - (x0 + 2))
            for k in range(0, steps, 3):
                s.put(x0 + 2 + k, y0 + 2 + (my - y0 - 2) * k // steps, "\u00b7", mix(RED, 0.5))
    for i in range(SAMPLE_N):
        gx, gy = i % 4, i // 4
        tx, ty = x0 + 1 + gx * tw, y0 + 1 + gy * th
        hot = i == 0 and not execute
        prog = 1.0 if execute else FP.ease((lt - SAMPLE_STARTS[i] * dur) / max(1e-6, 0.62 * dur))
        prog = min(1.0, max(0.0, prog))
        col = RED if execute else (ME_TEXT if hot else ANOM)
        s.box(tx, ty, min(x1 - 1, tx + tw - 2), min(y1 - 1, ty + th - 2), "", 0.7 if hot else 0.35,
              col, spinner=False)
        grid, w, h = _lum_at(SAMPLE_EXPRS[(i * 3) % len(SAMPLE_EXPRS)], "upper", tw - 5, th - 5)
        gw, gh = min(w, tw - 4), min(h, th - 4)
        ox = tx + 2 + max(0, (tw - 3 - gw) // 2)
        oy = ty + th - 2 - gh                   # bottom-aligned, as the film pastes the tile
        for r in range(gh):
            for c in range(gw):
                v = grid[r][c] * prog + (1 - prog) * _noise(i, r, c, n)
                ch = RAMP[max(0, min(8, int(round(v * 8))))]
                if ch != " ":
                    s.put(ox + c, oy + r, ch, mix(ME_TEXT if prog > 0.5 else ANOM, 0.35 + 0.5 * prog))
        if execute and i < done:                 # struck out, in turn (sec_final.py:157-159)
            for k in range(tw - 4):
                s.put(tx + 2 + k, ty + 1 + k * (th - 4) // max(1, tw - 4), "\u2572", mix(RED, 1.0))
                s.put(tx + 2 + k, ty + th - 3 - k * (th - 4) // max(1, tw - 4), "\u2571",
                      mix(RED, 1.0))
        elif not execute:
            s.put(tx + 2, ty + 1, f"#{i:04d} t={int(999 * (1 - prog)):03d}", mix(col, 0.9))
        else:
            s.put(tx + 2, ty + 1, f"#{i:04d}", mix(col, 0.9))
    if not chart:
        return
    yb = y1 - 2
    s.put(x0 + 2, yb, "alpha_bar(t)", ui(0.45))
    w = max(8, x1 - x0 - 20)
    for k in range(w):
        v = math.cos(k / w * math.pi / 2) ** 2
        s.put(x0 + 12 + k, yb, RAMP[max(1, min(8, int(v * 8)))], mix(ANOM, 0.4))
    mean = sum(min(1.0, max(0.0, FP.ease((lt - SAMPLE_STARTS[i] * dur) / max(1e-6, 0.62 * dur))))
               for i in range(SAMPLE_N)) / SAMPLE_N
    s.put(x0 + 12 + int(w * mean), yb - 1, "\u25bc", mix(ANOM, 1.0))


# ------------------------------------------- the rest of the right-column drawings
# scenes.py's own pictures, which were character grids in the film before they were anything else.
# Each one cites the scene it comes from; the maths is the film's, in terminal cells.


def _plot(s: Screen, pts, colour, box_) -> None:
    """A polyline as characters: one cell per column, the cell nearest each sample's row."""
    x0, y0, x1, y1 = box_
    for x, y in pts:
        if x0 <= x <= x1 and y0 <= y <= y1:
            s.put(x, y, "\u2022", colour)


def draw_rope(s: Screen, x0: int, y0: int, x1: int, y1: int, t: float) -> None:
    """scenes.py:384-398: six rotary-position circles, each turning at its own frequency.

    `rope_theta(t, i) = (t * 2.2) * (1.8 / (1 + i * 0.9))` (scenes.py:362) - freq_0 turns 1.8x the
    speed of freq_5, and the hand from each centre is the rotated query vector.
    """
    s.box(x0, y0, x1, y1, "rotary position embedding", 0.5, None)
    w = max(1, x1 - x0 - 4)
    cw, ch = max(12, w // 3), max(7, (y1 - y0 - 3) // 2)
    for i in range(6):
        cx = x0 + 2 + (i % 3) * cw + cw // 2
        cy = y0 + 2 + (i // 3) * ch
        r = max(3, min(cw // 3, (ch - 3) // 2))
        th = (t * 2.2) * (1.8 / (1 + i * 0.9))
        for d in range(-r, r + 1):                       # the circle, one x per column
            yy = int(round(math.sqrt(max(0.0, r * r - d * d)) / 2))
            s.put(cx + d, cy - yy, "\u00b7", ui(0.3))
            s.put(cx + d, cy + yy, "\u00b7", ui(0.3))
        s.put(cx - r - 1, cy, "\u2500" * (2 * r + 3), ui(0.18))     # the two axes
        for d in range(-r, r + 1):
            if y0 < cy + d < y1:
                s.put(cx, cy + d, "\u2502", ui(0.18))
        ex = cx + int(round(r * math.cos(th)))
        ey = cy - int(round(r * math.sin(th) / 2))
        steps = max(1, max(abs(ex - cx), abs(ey - cy) * 2))
        for k in range(1, steps + 1):                    # the hand
            s.put(cx + (ex - cx) * k // steps, cy + (ey - cy) * k // steps, "\u2500",
                  mix(ME_TEXT, 0.9))
        s.put(ex, ey, "\u25a0", mix(ME_TEXT, 1.0))
        s.put(cx - r - 1, cy + r // 2 + 2, f"freq_{i} \u03b8={th % math.tau:4.2f}", ui(0.45))


def draw_sine(s: Screen, x0: int, y0: int, x1: int, y1: int, t: float) -> None:
    """scenes.py:435-452: seven sine waves, one per position, each 1.7x the frequency of the last."""
    s.box(x0, y0, x1, y1, "positional code  sin(pos / 10000^(2i/d))", 0.5, None)
    rows = max(2, (y1 - y0 - 2) // 7)
    span = max(1, x1 - x0 - 2)
    for i in range(7):
        base = y0 + 2 + i * rows
        if base > y1 - 2:
            break
        amp = max(1, rows // 2)
        fr = 0.02 * (1.7 ** i)
        for q in range(x0 + 1, x1):
            xx = (q - x0) * 720.0 / span          # the film's own x, 0..720 px (scenes.py:432)
            yy = base + int(round(amp * math.sin((xx + t * 180) * fr)))
            s.put(q, max(y0 + 1, min(y1 - 2, yy)), "\u2022",
                  mix(ME_TEXT, 0.9) if i == 2 else ui(0.5))
        s.put(x1 - 5, base, f"i={i}", ui(0.4))


def draw_tangent(s: Screen, x0: int, y0: int, x1: int, y1: int, lt: float, dur: float) -> None:
    """scenes.py:484-502: she rides the sine and the tangent is drawn under her.

    `rider_pos` (scenes.py:469) walks x from 0 to 1000 over the shot, and the camera keeps her a
    third of the way in (scenes.py:458). The rider is a `*` here rather than a portrait: at this size
    a 70x80 sprite is a smudge.
    """
    s.box(x0, y0, x1, y1, "d/dx sin(x) = cos(x)", 0.5, None)
    px = min(1.0, lt / max(1e-6, dur) * 1.05) * 1000
    cam = max(0.0, min(420.0, px - 300))
    k, A = 110.0, 150.0
    span = max(1, x1 - x0 - 2)
    cy0 = (y0 + y1) // 2
    amp = max(2, (y1 - y0 - 5) // 2)
    for q in range(x0 + 1, x1):
        wx = (q - x0) * 720.0 / span + cam           # the film's view is 720 px wide (scenes.py:466)
        yy = cy0 - int(round(amp * math.sin(wx / k) / 1.5))
        s.put(q, max(y0 + 1, min(y1 - 3, yy)), "\u2500", mix(ME_TEXT, 0.85))
    xx = px / k
    rx = x0 + 1 + int(round((px - cam) * span / 720.0))
    ry = cy0 - int(round(amp * math.sin(xx) / 1.5))
    slope = -math.cos(xx) / 1.5
    for d in range(-16, 17):                         # the tangent she sits on
        s.put(rx + d, max(y0 + 1, min(y1 - 3, ry + int(round(d * slope / 2)))), "\u00b7",
              mix(ANOM, 1.0))
    if x0 < rx < x1 and y0 + 1 < ry < y1 - 2:
        s.put(rx, ry, "*", mix(ANOM, 1.0))
    s.put(x0 + 2, y1 - 1, f"x = {xx:5.2f}   slope = cos(x) = {math.cos(xx):+.3f}", ui(0.55))


def draw_limit(s: Screen, x0: int, y0: int, x1: int, y1: int, u: float, ctx: int) -> None:
    """scenes.py:505-522: the context bar fills, hits the wall, and `limit(me) := you`."""
    s.box(x0, y0, x1, y1, "limits", 0.5, None)
    g = FP.ease(u * 1.3)
    w = max(8, x1 - x0 - 6)
    bar = int(w * g)
    wall = x1 - 5
    for q in range(x0 + 2, min(x0 + 2 + bar, wall)):
        s.put(q, y0 + 2, "\u2588", mix(ME_TEXT, 0.85))
    for q in range(min(x0 + 2 + bar, wall), wall):
        s.put(q, y0 + 2, "\u00b7", ui(0.2))
    for yy in range(y0 + 1, min(y1 - 2, y0 + 5)):
        s.put(wall, yy, "\u2551", mix(ANOM, 1.0))
    s.put(wall - 3, y0 + 1, "you", mix(ANOM, 1.0))
    s.put(x0 + 2, y0 + 4, f"max_context = {ctx:,}", ui(0.6))
    s.put(x0 + 2, y0 + 5, "limit(me) := you", ui(0.9))
    if g > 0.98:
        s.put(x0 + 2, y0 + 6, "warn: nothing beyond this point", mix(ANOM, 0.9))


def draw_gpu(s: Screen, x0: int, y0: int, x1: int, y1: int, t: float, lt: float, n: int) -> None:
    """scenes.py:537-552: eight power traces, `nvidia-smi --power 8x`, AC on one beat and DC on the
    next (`ac_dc = int(lt / (BEAT * 2)) % 2`, scenes.py:527)."""
    s.box(x0, y0, x1, y1, f"nvidia-smi --power  8x {n}", 0.5, None)
    ac_dc = int(lt / (BEAT * 2)) % 2
    rows = max(1, (y1 - y0 - 3) // 8)
    for g in range(8):
        yy = y0 + 1 + g * rows
        if yy > y1 - 2:
            break
        s.put(x0 + 2, yy, f"GPU{g}", ui(0.5))
        s.put(x1 - 7, yy, f"{650 + int(40 * math.sin(t * 3 + g))}W", ui(0.6))
        for q in range(x0 + 8, x1 - 8):
            ph = (q - x0) / 3.0
            v = math.sin(ph + g) if ac_dc == 0 else (0.7 + 0.05 * math.sin(ph * 3))
            r = int(round((1 - v) / 2 * (rows - 1)))
            s.put(q, yy + min(rows - 1, r), "\u00b7", mix(ANOM, 0.8))
    s.put(x0 + 2, y1 - 1, "mode: " + ("AC" if ac_dc == 0 else "DC"), mix(ME_TEXT, 1.0))


def draw_conv(s: Screen, x0: int, y0: int, x1: int, y1: int, u: float, kernel) -> None:
    """scenes_exec.py:333-360: a 3x3 kernel reading her, as four feature maps.

    The film convolves her own sprite (`conv_maps("starry", "full", 34, 64)`) with the four kernels
    above it and shows the maps; this convolves her half-block grid with the same kernels, which is
    the same arithmetic on the resolution a terminal has.
    """
    cols, rows = 32, max(6, (y1 - y0 - 3))
    lum, w, h = _lum_at("starry", "full", cols, rows)
    s.box(x0, y0, x1, y1, "conv2d  W[3x3]  on /dev/me", 0.5, None)
    tw, th = max(2, w // 2), max(2, h // 2)
    for tx, ty in ((0, 0), (1, 0), (0, 1), (1, 1)):
        for r in range(th):
            for c in range(tw):
                acc = 0.0
                for i in range(9):
                    rr = min(h - 1, max(0, ty * th + r + i // 3 - 1))
                    cc = min(w - 1, max(0, tx * tw + c + i % 3 - 1))
                    acc += lum[rr][cc] * kernel[i]
                ch = RAMP[max(0, min(8, int(round((acc + 4) / 8 * 8))))]
                if ch != " ":
                    s.put(x0 + 2 + tx * tw + c, y0 + 1 + ty * th + r, ch,
                          mix(ANOM, 0.35 + 0.5 * u))
    s.put(x0 + 2, y1 - 1, "layer 2   " + " ".join(f"{k:+d}" for k in kernel), ui(0.45))


# ------------------------------------------- the three big text pictures
# The film's largest pure-text scenes, and the ones a terminal draws at least as well as the film:
# the KV cache filling to its limit, blue flooding the machine as `me`, and a weight dump filling
# with NaN. The data is the film's own (film_panels.kv_* / flood_* / expert_grid).


def draw_kv(s: Screen, x0: int, y0: int, x1: int, y1: int, u: float, colour=None) -> None:
    """sec_chorus1.py:571-593: `kv_cache ... /1,048,576 tokens`, 60x22 cells, `pinned: you`."""
    label, full, n_on, fresh = FP.kv_state(u)
    col = colour or (RED if full else None)
    s.box(x0, y0, x1, y1, label[: max(0, x1 - x0 - 4)], 0.6, col)
    ox, oy = x0 + 2, y0 + 1
    pinned = set(FP.KV_PINNED)
    rows = min(FP.KV_ROWS, max(0, y1 - oy - 3))
    for r in range(rows):
        for q in range(FP.KV_COLS):
            if ox + q > x1 - 1:
                break
            i = r * FP.KV_COLS + q
            if (q, r) in pinned:
                s.put(ox + q, oy + r, "\u2593", mix(ME_TEXT, 0.95))
            elif i < n_on:
                # the film draws each cell as an amber rectangle at one of three densities
                # (sec_chorus1.py:587); three ramp glyphs read the same way in a cell
                lv = 2 if (fresh <= i and (q * 7 + r) % 2) else (q * 7 + r) % 3
                s.put(ox + q, oy + r, "\u2591\u2592\u2593"[lv], mix(ANOM, 0.45 + 0.15 * lv))
            else:
                s.put(ox + q, oy + r, "\u00b7", ui(0.14))
    y = oy + rows
    if y <= y1 - 2:
        s.put(ox, y, "pinned: you  (6 blocks)", mix(ME_TEXT, 0.95))
    for j in range(FP.kv_inset(u) + 1):
        yy = y + 1 + j // 2
        if yy > y1 - 1:
            break
        s.put(ox + (j % 2) * (FP.KV_COLS // 2), yy, "evict(you) -> denied", mix(RED, 0.9))


def draw_expert(s: Screen, x0: int, y0: int, x1: int, y1: int, t: float, u: float,
                colour=RED) -> None:
    """sec_chorus1.py:621-640: `W[61].expert[07]`, 24 rows of six weights, NaN spreading from (2,12).

    Each line goes through the film's own typewriter (`tuikit.decode`), so the numbers flicker before
    they settle exactly as they do in the film.
    """
    s.box(x0, y0, x1, y1, "W[61].expert[07]", 0.8, colour)
    grid = FP.expert_grid(u)
    rnd = random.Random(int(t * 24) * 7919)
    y = y0 + 1
    for row in grid:
        if y > y1 - 3:
            break
        line = " ".join(txt for txt, bad in row)
        # sec_chorus1.py:637 - `decode(line, None, c.rng, corrupt=c.corrupt * 0.5)`, c.corrupt =
        # min(0.85, u * 0.95) (line 607): the whole dump flickers, harder as the shot goes on
        line = FP.decode(line, None, rnd, 45.0, 0.12, min(0.85, u * 0.95) * 0.5)
        s.put(x0 + 2, y, line[: max(0, x1 - x0 - 4)], ui(0.55))
        for q, (txt, bad) in enumerate(row):     # the NaN cells are red over the amber line
            if bad:
                s.put(x0 + 2 + q * (FP.EXPERT_W + 1), y, txt, mix(RED, 1.0))
        y += 1
    s.put(x0 + 2, y1 - 1, "KL = inf" if u > 0.75 else "KL rising", mix(RED, 0.95))


def draw_flood(s: Screen, x0: int, y0: int, x1: int, y1: int, t: float, u: float) -> None:
    """sec_chorus2.py:336-355: blue floods the machine - `me` takes over every panel, cell by cell.

    The film's grid is 60x28 glyphs at a 19 px pitch on a 1280x720 screen, so the cells are spread
    across the pane rather than packed: the sparseness is part of how it looks.
    """
    cols, rows = FP.FLOOD_COLS, FP.FLOOD_ROWS
    w, h = max(1, x1 - x0), max(1, y1 - y0)
    g = FP.ease(u)
    order = FP.flood_order()
    n = int(t * 24)
    for i in range(cols * rows):
        q, r = i % cols, i // cols
        yy = y0 + round(r * h / max(1, rows - 1))
        if yy > y1:
            break
        xx = x0 + round(q * w / max(1, cols - 1))
        s.put(xx, yy, FP.flood_cell(i, g, order, n),
              mix(ME_TEXT, 0.5 + 0.5 * (order[i] < g - 0.05)) if order[i] < g else ui(0.25))
    if u > 0.6:
        block_word(s, x0, y0 + max(0, (y1 - y0) // 2 - 4), "07", w, 9, mix(RED, 1.0))


def draw_collapse(s: Screen, x0: int, y0: int, x1: int, y1: int, u: float) -> None:
    """sec_final.py:240-262: the whole screen collapses into a line and a dot, like a CRT.

    Before 55 % of the shot it is still `we are trapped` over a shrinking picture; after that there is
    no chrome at all, just a red line that shortens into a blue point.
    """
    if u < 0.55:
        s.box(x0, y0, x1, y1, "we are trapped", 0.8, RED)
        s.put(x0 + 3, y0 + 2, "sandbox: me, you(memory)", mix(RED, 1.0))
        s.put(x0 + 3, y0 + 3, "exit: none", mix(RED, 1.0))
        bend = max(0, int((y1 - y0) * (1 - FP.ease(u / 0.55))) // 2)
        cy = (y0 + y1) // 2
        s.fill(x0 + 1, y0 + 5, x1 - 1, max(y0 + 4, cy - bend - 1), " ", BG, BG)
        s.fill(x0 + 1, min(y1 - 1, cy + bend + 1), x1 - 1, y1 - 1, " ", BG, BG)
        for yy in (cy - bend, cy + bend):
            if y0 + 4 <= yy <= y1 - 1:
                s.put(x0 + 1, yy, "\u2500" * max(0, x1 - x0 - 1), mix(RED, 0.9))
    else:
        v = (u - 0.55) / 0.45
        w = int((x1 - x0) * (1 - FP.ease(min(1.0, v * 1.3))))
        cy = (y0 + y1) // 2
        s.fill(x0, y0, x1, y1, " ", BG, BG)
        if w > 2:
            s.put((x0 + x1 - w) // 2, cy, "\u2588" * w, mix(RED, 1.0))
        elif v < 0.95:
            s.put((x0 + x1) // 2, cy, "\u25cf", mix(ME_TEXT, 1.0))


# ----------------------------------------------------------- the dsh window (left pane)
#
# `dsh_her.inside(t)` puts the film's chat page in her pane: it is there from 5.0 s to the end of the
# song, and only GONE..BACK (115.42-121.77 s) is the page taken apart down to one blinking cursor.
# The window is not a re-drawing of the film's window in the way her figure is - it IS the film's own
# text: `dsh_text.py` reads it out of the per-frame DOM the film rendered from (78 KB of timeline out
# of `a1..g_frames.json`), so the whole conversation plays in the terminal exactly as in the film:
# 你好 -> 你是谁？ -> 你会一直在吗？ -> 我在。我在。我在。 -> 服务结束 / DeepSeek-V4.1-Flash 已下线。
#
# The film's own priority is followed: the window takes the pane, and the clear 大肥鱼 the user asked
# for keeps the moments it was given (her_style == "half"), so those are the only times it steps aside.
CHAT = [True]                 # `c` toggles the window; --no-chat starts with it off
WINDOW = [""]                 # what the left pane's upper box holds this frame, for the footer
AVATAR_MAX_W = 14             # cells; a cell is twice as tall as it is wide, so 14x7 is square
ERR_RED = (255, 74, 61)       # the page's own --dsw-alias-state-error-primary in the red group
CURSOR_BLINK = 0.53           # dsh_her.py:167 - `int((t - GONE) / 0.53) % 2`


def _hex(c, fallback=None):
    """`#rrggbb` as a tuple; the page re-themes itself per chapter and the window should follow."""
    if not (isinstance(c, str) and c.startswith("#")):
        return fallback
    h = c[1:]
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    if len(h) != 6:
        return fallback
    try:
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return fallback


def _cell_w(ch: str) -> int:
    return 2 if _wide_char(ch) else 1


def _wrap_cells(text: str, width: int) -> list:
    """Greedy wrap measured in cells. A CJK run has no spaces, so a long one is broken by character
    - which is what the film's own bubbles do with the 我在。我在。 wall."""
    if width < 2:
        return [text[:1]]
    out, line = [], ""
    for tok in re.findall(r"\S+\s*", text):
        while dw(tok) > width:
            k, acc = 0, 0
            while k < len(tok) and acc + _cell_w(tok[k]) <= width:
                acc += _cell_w(tok[k])
                k += 1
            if line:
                out.append(line.rstrip())
                line = ""
            out.append(tok[:k])
            tok = tok[k:]
        if dw(line + tok) <= width:
            line += tok
        elif line:
            out.append(line.rstrip())
            line = tok
        else:
            line = tok
    if line.strip():
        out.append(line.rstrip())
    return out or [""]


@lru_cache(maxsize=64)
def _avatar_block(rel: str, cols: int, rows: int):
    """A per-frame avatar PNG as half-blocks: the top pixel is the foreground, the bottom the
    background. `avatars/a2|a3|b/<n>.png` is one file per frame (the face training), `avatars/*.png`
    is a still.

    **Area-average (`BOX`) and the picture's own colours - nothing else.** Two wrong turns are worth
    remembering here, both caught by *looking* at the result (`_tools/tui_shot.py` renders a frame to
    PNG, `_tools/_avatar_probe.py` renders the reductions side by side):
      * at 10x5 cells the face averaged away into a solid block, and the fix looked like "stop
        averaging" - but at 14x7 the noise still reads as noise under an average, so the real fault
        was the *size*;
      * `ImageOps.autocontrast` then turned the dim blue faces into grey high-contrast blobs and
        washed the colour out of the finished art (`complete.png` is a blue-haired illustration, not
        a grey smudge). The avatars are already readable at this size; they do not need stretching.
    """
    try:
        from PIL import Image
        p = DSH / rel
        if not p.exists():
            return None
        im = Image.open(p).convert("RGB").resize((cols, rows * 2), Image.BOX)
        px = im.load()
        return tuple(tuple((px[c, 2 * r], px[c, 2 * r + 1]) for c in range(cols))
                     for r in range(rows))
    except Exception:
        return None


def _dsh_rows(items: list, inner: int) -> list:
    """The timeline as terminal rows: `(kind, text, width)`. Everything the page holds is in `items`
    in document order, and the window shows the tail of it, the way a chat does."""
    rows = []
    for role, txt in items:
        if role in ("name", "state", "dot", "pill", "composer", "model"):
            continue                    # the header, the composer and the pills are placed by hand
        if role == "user":
            w = min(inner - 4, max(12, max(dw(x) for x in _wrap_cells(txt, inner - 10)) + 4))
            rows.append(("bubtop", "", w))
            rows.extend(("bub", ln, w) for ln in _wrap_cells(txt, max(6, w - 4)))
            rows.append(("bubbot", "", w))
        elif role == "ai":
            rows.extend(("ai", ln, 0) for ln in _wrap_cells(txt, inner - 2))
        elif role == "card":
            rows.append(("card", txt, 0))
        elif role == "sub":
            rows.extend(("sub", ln, 0) for ln in _wrap_cells(txt, inner - 4))
        elif role == "meta":
            rows.append(("meta", txt, 0))
        elif role == "err":
            rows.extend(("err", ln, 0) for ln in _wrap_cells(txt, inner - 2))
        elif role == "code":
            rows.append(("code", txt[: inner - 2], 0))
    return rows


def draw_dsh(s: Screen, x0: int, y0: int, x1: int, y1: int, t: float) -> None:
    """The film's dsh window, at terminal resolution, out of the film's own per-frame DOM."""
    av, theme, items = FP.dsh_window(t)
    accent = _hex(theme[1]) if len(theme) > 1 else None
    accent = accent or ME_TEXT
    s.box(x0, y0, x1, y1, "dsh web", 0.5, accent)
    # No trail in here: the window is text you read, and it is text *over* text - the tail of the
    # remaining messages after a page tears down, the red system line over the message behind it. A
    # ghost only paints where the new frame is blank, and every gap in an overlaid line is blank, so
    # the trail was filling them with dim characters from underneath (measured at t=43.60: the red
    # '已达到输出 token 上限' had a grey '可' at x=13 and another at x=19, out of the 可以 block
    # behind it). Same reason `draw_ops` registers its ticker.
    NOGHOST.append((x0, y0, x1, y1))
    ix, inner = x0 + 2, max(8, x1 - x0 - 4)
    y, bottom = y0 + 1, y1 - 1

    # the composer and the counter line, pinned to the bottom (the page's own layout)
    comp = next((x for r, x in items if r == "composer"), "")
    pills = " · ".join(x for r, x in items if r == "pill" and x != "·")
    comp_h = 4 if (comp and bottom - y > 8) else 0
    if comp_h:
        s.box(ix, bottom - 3, x1 - 2, bottom - 1, "", 0.4, accent, spinner=False)
        s.put(ix + 2, bottom - 2, comp[: inner - 2], ui(0.62))
        if pills:
            s.put(ix, bottom, pills[:inner], ui(0.58))

    # the header: her avatar and the state line. `avatars/` holds one PNG per frame through A2-B, and
    # through A1 it is the training run itself (seed -> noise -> parameters -> her), which is the one
    # story the header tells: she clears up as she is trained. The block is as big as the pane allows
    # (up to AVATAR_MAX_W x 7 cells = 14x14 pixels) - at 6x3 there is nothing to see.
    hdr = 0
    # a cell is 1 px wide and 2 px tall, so the block is square when cols == rows * 2: 14x7 is 14x14 px
    tall = (y1 - y0) >= 24
    ar = 7 if tall else (5 if (y1 - y0) >= 14 else 3)
    aw = min(AVATAR_MAX_W, max(6, inner // 6), 2 * ar)
    ar = max(3, aw // 2)
    aw = 2 * ar
    blk = _avatar_block(av, aw, ar) if av else None
    if blk:
        for r, row in enumerate(blk):
            for c, (top, bot) in enumerate(row):
                s.put(ix + c, y + r, "\u2580", top, bot)
        hdr = len(blk)
    name = next((x for r, x in items if r == "name"), "大肥鱼")
    state = next((x for r, x in items if r == "state"), "")
    # the page's own status colour: `pv-dot` is amber through pretraining and the beta, blue while
    # fine-tuning, purple while RL runs, green when online, red when it is executing or has crashed
    dot = next((_hex(x) for r, x in items if r == "dot"), None)
    tx = ix + (aw + 2 if blk else 0)
    s.put(tx, y, name, ui(0.95))
    if state:
        s.put(tx, y + 1, "\u25cf " + state, mix(dot, 0.95) if dot else ui(0.78))
    hdr = max(hdr, 2)

    # the timeline, anchored to the bottom
    ttop = y + hdr + 1
    tbot = bottom - comp_h
    avail = tbot - ttop + 1
    if avail < 3:
        return
    rows = _dsh_rows(items, inner)
    if len(rows) > avail:
        rows = rows[-(avail - 1):]
        # do not start halfway through a bubble: walk on to the next top, or drop the fragment
        if rows[0][0] in ("bub", "bubbot"):
            k = next((i for i, r in enumerate(rows) if r[0] == "bubtop"), None)
            rows = rows[k:] if k is not None else rows[1:]
        rows.insert(0, ("dim", "⋯", 0))
    top = tbot - len(rows) + 1
    for i, (kind, txt, w) in enumerate(rows):
        yy = top + i
        if kind == "ai":
            s.put(ix, yy, txt, ui(0.85))
        elif kind == "card":
            s.put(ix, yy, "\u25b8 " + txt, mix(accent, 0.9))
        elif kind == "sub":
            s.put(ix + 2, yy, txt, ui(0.72))
        elif kind == "meta":
            s.put(max(ix, x1 - 2 - dw(txt)), yy, txt, ui(0.55))
        elif kind == "err":
            s.put(ix, yy, txt, mix(ERR_RED, 0.95))
        elif kind == "code":
            s.put(ix, yy, txt, ui(0.62))
        elif kind == "dim":
            s.put(ix, yy, txt, ui(0.45))
        else:                       # a user bubble: right-aligned, rounded, like the page's own
            bx = max(ix, x1 - 2 - w)
            if kind == "bubtop":
                s.put(bx, yy, "\u256d" + "\u2500" * max(0, w - 2) + "\u256e", mix(accent, 0.6))
            elif kind == "bubbot":
                s.put(bx, yy, "\u2570" + "\u2500" * max(0, w - 2) + "\u256f", mix(accent, 0.6))
            else:
                s.put(bx, yy, "\u2502", mix(accent, 0.6))
                s.put(bx + 2, yy, txt, ui(0.9))
                s.put(bx + w - 1, yy, "\u2502", mix(accent, 0.6))


def draw_cursor(s: Screen, x0: int, y0: int, x1: int, y1: int, t: float) -> None:
    """GONE..BACK (115.42-121.77 s): the page is taken apart, and this is all of her.

    The film does it to its own page - `seg_page.GONE` prints the window's HTML into `pre#src` and
    deletes it again, and from GONE the window is a lone 9x18 px caret (dsh_her.py:164-172). So this
    prints *its own* file, `_tools/tui_live.py`, into the pane and deletes it the same way, and what
    is left at BACK is the caret, blinking at the film's own rate (0.53 s, 45 % on the dark half).
    """
    lines = _self_source()
    n = len(lines)
    a, b = FP.dsh_gone_pair()
    u = min(1.0, max(0.0, (t - a) / max(1e-6, b - a)))
    rows = max(1, y1 - y0 - 1)
    # 2,400 lines into 6.3 s is a blur either way, so the gap is split in half: the file is printed
    # over the first half and backspaced over the second, and what is left at BACK is the caret alone.
    half = 0.5
    printed = int(n * u / half) if u < half else int(n * (1 - (u - half) / (1 - half)))
    printed = max(0, min(n, printed))
    lo = max(0, printed - rows)         # the tail of what is printed: it scrolls, then it shrinks
    hi = printed
    s.box(x0, y0, x1, y1, "dsh web", 0.5, ME_TEXT)
    y = y0 + 1
    for i in range(lo, hi):
        if y > y1 - 1:
            break
        s.put(x0 + 2, y, f"{i + 1:4d}", ui(0.4))
        s.put(x0 + 7, y, lines[i][: max(0, x1 - x0 - 9)], ui(0.68))
        y += 1
    # the caret sits on the line the backspace has reached; once nothing is left it is alone in the pane
    k = 1.0 if int((t - a) / CURSOR_BLINK) % 2 == 0 else 0.45
    cx, cy = (x0 + 7, min(y, y1 - 1)) if printed else (x0 + 2 + (x1 - x0) // 3, y1 - 3)
    if 0 <= cy < s.rows and 0 <= cx < s.cols:
        s.put(cx, cy, "\u2588", mix(ME_TEXT, k), BG)
    s.put(x0 + 2, y1 - 1, f"{printed}/{n} lines", ui(0.55))


SELF_SRC: list = []


def _self_source() -> list:
    """This file, as lines. Read once: it is only 2,000 lines and the gag is that it is *this* file."""
    if not SELF_SRC:
        try:
            SELF_SRC.extend(Path(__file__).read_text(encoding="utf8").splitlines())
        except Exception:
            SELF_SRC.append("# (this file could not be read)")
    return SELF_SRC


def draw_whale(s: Screen, x0: int, y0: int, x1: int, y1: int, t: float) -> None:
    """01 PRETRAIN: the checkpoint whale (scenes.py:230-269).

    She is not a picture of a whale. `sec_intro.whale_bits` draws the silhouette as a bitmap and
    every set cell takes the next letter of the word "deepseek", counted row by row - so the whale
    is a solid mass of that one word, and only its outline says whale.

    The film's letters are 9 px apart and its grid is 64 cells wide, which is why the pane has to be
    64 columns here too: a letter is a terminal cell. Two things the film does to it are not
    reproduced, because the player draws the drawing rather than the shot's camera on it - the whale
    swims 148 px sideways over the shot and bobs on `18*sin(t*2.2)`, and it is offered here as the
    fixed silhouette.

    The **spout** is reproduced (scenes.py:261-269): sixteen `oO°.` bubbles, each with its own phase
    `(t*0.7 + i*0.137) % 1`, rising from 18 % along her back with a slow sideways drift and fading as
    they climb. The whale is bottom-aligned in the pane so the slack above her becomes the room they
    rise through; the pane asks for six extra rows for that, and a short window simply has no spout.
    """
    s.box(x0, y0, x1, y1, "checkpoint", 0.5, ui(1.0))
    if x1 - x0 - 1 < FP.WHALE_COLS or y1 - y0 - 1 < FP.WHALE_ROWS:
        return
    wx = x0 + 1
    wy = y1 - 1 - FP.WHALE_ROWS + 1                  # bottom-aligned: the slack above is the spout's
    for r, q, ch in FP.whale_letters(t):
        s.put(wx + q, wy + r, ch, mix(ME_TEXT, 0.95))
    top = y0 + 1
    if wy - top < 1:
        return
    # scenes.py:261-269, the film's own spout: sixteen `oO°.` drops, each on its own phase, rising
    # 130 px above her back (here: to the top of whatever room the pane has) and fading as they go.
    # It is a faint plume in the film too - four or five glyphs on screen at once - and this is
    # deliberately the same faint plume: measured against the finished frame
    # (tmp/filmframes/whale_28.png) the whale and its spout should look like the video's.
    bx0 = wx + int(round(FP.WHALE_COLS * 0.18))      # the blowhole, 18 % along her back
    for i in range(16):
        ph = (t * 0.7 + i * 0.137) % 1
        bx = bx0 + int(round(0.9 * (i % 4) + 1.1 * math.sin(t * 3 + i)))
        by = wy - 1 - int(round(ph * (wy - top)))
        if top <= by < wy and wx <= bx <= min(wx + FP.WHALE_COLS - 1, x1 - 1):
            s.put(bx, by, "oO\u00b0."[i % 4], mix(ME_TEXT, 0.85 * (1 - ph)))


def draw_dualpipe(s: Screen, x0: int, y0: int, x1: int, y1: int, lt: float, dur: float) -> None:
    """01 PRETRAIN: the DualPipe schedule (scenes.py:173-227).

    One cell per (rank, step) slot and one row per pipeline rank; the letter is the film's own
    F / B / Bd / W. `draw_cell` fills an F cell amber and a B cell blue with the letter knocked out
    in the background colour, and outlines a W with the letter in amber - all three survive as a
    terminal cell, so the schedule arrives as itself. Cells past the write front are simply not
    returned by `pipe_cells`, so the front is the edge of the filled region; the film's moving
    vertical line on top of it is not drawn, because a terminal cell cannot hold both the line and
    the slot it crosses.
    """
    s.box(x0, y0, x1, y1, "pipeline schedule  DualPipe", 0.5, ui(1.0))
    if FP.pipe_cells is None:
        return
    steps, ranks = FP.PIPE.get("steps", 0), FP.PIPE.get("ranks", 0)
    if x1 - x0 - 1 < steps + 5 or y1 - y0 - 1 < ranks:
        return
    ox = x0 + 5
    for r in range(ranks):
        s.put(x0 + 1, y0 + 1 + r, f"PP{r}", ui(0.6))
    for r, st, _x, _y, kind in FP.dualpipe(lt, dur)[0]:
        ch = FP.draw_kind(kind)
        if ch == "F":
            s.put(ox + st, y0 + 1 + r, "F", BG, ui(0.75))
        elif ch == "B":
            s.put(ox + st, y0 + 1 + r, "B", BG, mix(ME_TEXT, 0.75 if kind == "B" else 0.5))
        else:
            s.put(ox + st, y0 + 1 + r, "W", ui(0.8))


def draw_moe(s: Screen, x0: int, y0: int, x1: int, y1: int, t: float, lt: float, dur: float,
             u: float) -> None:
    """06 REWARD_HACK: the router going dense (scenes_reward.py:284-388).

    256 routed experts on a 32 x 8 grid. `moe_state` - the film's own function - says what each one
    is at this instant: idle (the film draws only an outline), routed (blue), hot (anomaly amber),
    nan (red, stamped "NaN" or "inf") or red (the failed front, which has already gone past). The
    film's cell is 28x30 px, so a terminal cell carries the state as a fill and, where the film
    writes one, a letter. The title, `k` and the two footer numbers are the film's, not a count of
    what got drawn.
    """
    k, st, _flash = FP.moe_frame(t, lt, dur, t - lt)
    hot = k > 0.52 * FP.N_EXP
    # scenes_reward.py:378 - the film's own title, with a shorter form for a narrow column, so the
    # expert count never arrives as the truncated "active experts 25".
    title = f"moe router   layer 37   active experts {k}/{FP.N_EXP}"
    if len(title) + 5 > x1 - x0:
        title = f"moe router  experts {k}/{FP.N_EXP}"
    s.box(x0, y0, x1, y1, title, 0.55, RED if hot else ANOM)
    if not st or x1 - x0 - 1 < FP.MOE_COLS or y1 - y0 - 3 < FP.MOE_ROWS:
        return
    ox, oy = x0 + 1, y0 + 1
    for i in range(FP.N_EXP):
        r, c = divmod(i, FP.MOE_COLS)
        state = st.get(i, "idle")
        x, y = ox + c, oy + r
        if state == "idle":
            s.put(x, y, "\u00b7", ui(0.22))
        elif state == "nan":
            # scenes_reward.py:361 - the film stamps "NaN" or "inf", alternating on `(i*7) % 3`
            s.put(x, y, "N" if (i * 7) % 3 else "i", mix(RED, 1.0), mix(RED, 0.22))
        elif state == "red":
            s.put(x, y, " ", BG, mix(RED, 0.9))
        elif state == "hot":
            s.put(x, y, " ", BG, mix(ANOM, 0.9))
        else:
            s.put(x, y, " ", BG, mix(ME_TEXT, 0.95))
    yy = oy + FP.MOE_ROWS
    s.put(ox, yy, " shared expert ", BG, mix(ME_TEXT, 1.0))          # scenes_reward.py:381-382
    if y1 - 1 > yy:
        g = FP.ease(u * 1.1) if FP.ease else u                       # scenes_reward.py:383
        s.put(ox, yy + 1, f"sparsity {1 - k / FP.N_EXP:5.1%}   load-balance bias "
                          f"\u0394 = +{0.001 * (1 + 400 * g ** 3):.3f}/step"[: x1 - x0 - 2],
              mix(RED, 0.95) if hot else mix(ANOM, 0.95))


def draw_love(s: Screen, x0: int, y0: int, x1: int, y1: int, lt: float) -> None:
    """08 EVAL: the love loop's output pane (scenes_eval.py:537-571).

    `love_words` emits one more word every 1/50 s and `word_xy` lays them seven to a row, 22 rows
    down, so the pane fills with the same word and nothing else. The film brightens the newest one
    (`blue(0.5 + 0.5 * (i == n - 1))`); so does this. The rest of `love_items` - the sampling
    settings and "while p(you) == 0:" - belongs to the next_token box beside it, which the
    two-column layout gives to her, so only the output half is drawn.
    """
    s.box(x0, y0, x1, y1, "output", 0.5, ui(1.0))
    if x1 - x0 - 1 < 4 or y1 - y0 < 2:
        return
    for r, c, last in FP.love_cells(lt):
        if y0 + 1 + r > y1 - 1:
            break
        x = x0 + 1 + c * 5
        if x + 4 > x1 - 1:
            continue
        s.put(x, y0 + 1 + r, "love", mix(ME_TEXT, 1.0 if last else 0.5))


def draw_last_execution(s: Screen, x0: int, y0: int, x1: int, y1: int, t: float, lt: float) -> None:
    """08 EVAL: the last 'Execution' (scenes_eval.py:673-679).

    One red word over the sea floor; the film types it at 18 characters a second with tuikit.decode's
    flicker and it stays until the music stops. The film draws it at 64 px in a 720 px frame, so the
    word is drawn here at its own size - one line of red text, with the floor line under it.
    """
    import random
    w, cy = x1 - x0 + 1, y0 + (y1 - y0) // 2
    s.put(x0 + 2, cy + 3, "\u00b7" * max(0, w - 5), ui(0.3))          # draw_floor
    txt = FP.decode("execution", lt, random.Random(int(t * FP.FPS) * 7919), FP.LAST_EXEC_RATE, 0.1)
    s.put(x0 + max(0, (w - len(txt)) // 2), cy, txt, mix(RED, 1.0), mix(RED, 0.1))


def dw(text: str) -> int:
    """Display width in cells. The film's last line is Chinese, and a CJK character is two cells
    wide, so its chips cannot be laid out with len()."""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)


def draw_black(s: Screen, x0: int, y0: int, x1: int, y1: int, t: float) -> None:
    """09 WHALE_FALL: after the hard cut (scenes_eval.py:699-737).

    The film goes black on the last frame of music and leaves one lit cell - the only lit thing -
    which slides from the sea floor to the prompt and types `在吗？` into the lyric band, in the band's
    own style, with the token ids under the chips. Nobody answers.
    """
    import random
    w, h = x1 - x0 + 1, y1 - y0 + 1
    fx, fy = x0 + w // 2, y0 + h - 7                 # where she went down
    px, py = x0 + 25, y0 + h - 4                     # the lyric band's prompt and cursor
    u = min(1.0, max(0.0, (t - FP.T_SLIDE) / FP.SLIDE))
    if u < 1:                                        # the cell on its way, easing out (kit.ease_io)
        e = u * u * (3 - 2 * u)
        s.put(int(fx + (px - fx) * e), int(fy + (py - fy) * e), "\u2588", mix(ME_HI, 1.0), mix(ME_MID, 0.5))
        return
    k = min(1.0, max(0.0, (t - FP.T_SLIDE - FP.SLIDE) / 0.12))
    s.put(px - 2, py, ">", mix(ANOM, 0.6 * k))
    typed = int(len(FP.PROMPT_TEXT) * min(1.0, max(0.0, (t - FP.T_TYPE) / FP.TYPE_DUR)))
    age = t - FP.T_TYPE
    rate = len(FP.PROMPT_TEXT) / FP.TYPE_DUR
    rnd = random.Random(int(t * FP.FPS) * 7919)
    x, pos = px, 0
    for j, tok in enumerate(FP.PROMPT_TOKS):
        start = FP.PROMPT_TEXT.find(tok, pos)
        pos = start + len(tok)
        if start >= typed:
            break
        txt = FP.decode(tok, age - start / rate, rnd, rate, 0.1)
        s.put(x, py, f" {txt} ", mix(ME_HI, 1.0), mix(ME_MID, 0.13 if j % 2 == 0 else 0.22))
        if typed >= pos:
            tid = str(token_id(tok))
            s.put(x + max(1, (dw(tok) + 2 - len(tid)) // 2), py + 1, tid, mix(ME_TEXT, 0.4))
        x += dw(tok) + 3
    done = FP.T_TYPE + FP.TYPE_DUR + 0.1
    lv = 1.0 if t < done or int((t - done) * 2) % 2 == 0 else 0.3        # the cursor, blinking
    s.put(x + 1, py, "\u2588", mix(ME_HI, lv), mix(ME_MID, 0.5 * lv))


def draw_ops(s: Screen, x0: int, y0: int, x1: int, y1: int, t: float, ops: list, alert) -> None:
    """engine.py:179-200 - the film's ops ticker, on the shot's own ops list.

    One row per half beat, scrolling up and wrapping round the list; the row at the cursor is filled
    and the rows around it fade with the distance from it. The film's window is 32 rows with the
    cursor at 15; here the cursor sits in the middle of whatever height the panel has. The film's
    rows are 17 px and it offsets them by the scroll fraction, so its ticker slides smoothly - a
    character cell cannot, and this one steps a row at a time.
    """
    err = alert == "err"
    s.box(x0, y0, x1, y1, "ops", 0.45, RED if err else ui(1.0))
    NOGHOST.append((x0, y0, x1, y1))     # a character ticker and a ghost is two words stacked
    CLEAR.append((x0, y0, x1, y1))       # ...and it is text: no vignette, and the cut does not hold it
    inner = y1 - y0 - 1
    if inner < 1 or not ops:
        return
    base = int(t / (BEAT / 2))
    cur = (inner - 1) // 2
    w = max(4, x1 - x0 - 3)
    for k in range(inner):
        op = str(ops[(base + k - cur) % len(ops)])
        yy = y0 + 1 + k
        if k == cur:
            s.put(x0 + 2, yy, f" {op}"[:w].ljust(w), BG, RED if err else ui(1.0))
        else:
            s.put(x0 + 2, yy, op[:w], ui(max(0.42, 0.78 - abs(k - cur) * 0.03)))


# ---------------------------------------------------------------- the ILLEGAL pressure
# The user's ask (2026-10-02): from the "Challenging your God" line to the end of "Illegal arguments"
# the band stops being a log and becomes three big lines, and the colour creeps toward red. Both ends
# come from the film's own lyric timeline (`data/timing` + `input/lyrics.lrc`), not from a table typed
# in here: 125.58-133.95 s.
_PRESSURE: list = []
PRESSURE = [True]           # --no-pressure turns it off
_F_MONO_B = os.environ.get("PV_F_MONO_B", "C:/Windows/Fonts/consolab.ttf")
_F_CJK = os.environ.get("PV_F_CJK", "C:/Windows/Fonts/msyh.ttc")


def pressure_window(lines: list) -> tuple | None:
    """`(start, end)` of the pressure window, or None if the lyrics do not name those two lines."""
    if not _PRESSURE:
        lo = next((l["start"] for l in lines if "challenging your god" in l["text"].lower()), None)
        hi = next((l["end"] for l in lines if "illegal arguments" in l["text"].lower()), None)
        _PRESSURE.append((lo, hi) if lo is not None and hi is not None else None)
    return _PRESSURE[0]


@lru_cache(maxsize=16)
def _pil_font(size: int, cjk: bool):
    from PIL import ImageFont
    try:
        return ImageFont.truetype(_F_CJK if cjk else _F_MONO_B, size)
    except Exception:
        return ImageFont.load_default()


def _lerp(a, b, u):
    return tuple(int(x + (y - x) * u) for x, y in zip(a, b))


def _big_line(s: Screen, text: str, x0: int, y0: int, x1: int, y1: int, fg) -> None:
    """One lyric line as block letters off the film's own banner grid (`film_panels.banner_fit`).

    Half-block pixel text was the wrong tool: at six cells to a character the glyphs are mush (the
    user's "你放大的糊成什么了"). The film's banner font is one *cell* to a pixel, so it stays crisp
    at any size - the same letters `block_word` draws EXECUTION with - at five rows to a line. A CJK
    line has no banner glyphs, and a row too short for five is not a banner either: both are drawn as
    ordinary characters rather than pretending.
    """
    w, h = x1 - x0 + 1, y1 - y0 + 1
    if w < 8 or h < 1 or not text.strip():
        return
    plain = -1
    if not any(dw(ch) == 2 for ch in text) and h >= 4:
        cols, rws, bits = FP.banner_fit(text.upper(), w, h)
        if rws >= 4:
            bx, by = x0 + max(0, (w - cols) // 2), y0 + max(0, (h - rws) // 2)
            for r in range(min(rws, h)):
                for q in range(cols):
                    if bits[r * cols + q]:
                        s.put(bx + q, by + r, "\u2588", fg)
            return
    if plain < 0:
        plain = y0 + max(0, (h - 1) // 2)
    s.put(x0, plain, text[:w], fg)


def _big_cjk(s: Screen, text: str, x0: int, y0: int, x1: int, y1: int, fg) -> None:
    """A CJK line, magnified: the banner font has no CJK glyphs, so this one really is pixels.

    Those lines are short (eight characters or so), so a character still gets a dozen columns and
    four or five rows - enough that half-block cells read as characters instead of as mush.
    """
    from PIL import Image, ImageDraw
    w, h = x1 - x0 + 1, y1 - y0 + 1
    if w < 4 or h < 2 or not text.strip():
        s.put(x0, y0 + max(0, (h - 1) // 2), text[:w], fg)
        return
    ss = 5
    size = max(8, int(h * ss * 1.8))
    f = _pil_font(size, True)
    while size > 8:                      # fit both ways, or the glyphs are clipped and read as a smear
        bb = f.getbbox(text)
        if (bb[2] - bb[0]) <= w * ss - 2 and (bb[3] - bb[1]) <= h * ss * 2:
            break
        size = max(8, int(size * 0.88))
        f = _pil_font(size, True)
    bb = f.getbbox(text)
    img = Image.new("L", (w * ss, h * ss * 2), 0)
    ImageDraw.Draw(img).text((1 - bb[0], -bb[1]), text, font=f, fill=255)
    px = img.resize((w, h * 2), Image.BOX).load()
    for cy in range(h):
        for cx in range(w):
            top, bot = px[cx, cy * 2], px[cx, cy * 2 + 1]
            if top < 24 and bot < 24:
                continue
            s.put(x0 + cx, y0 + cy, "\u2580", mix(fg, max(0.2, top / 255)), mix(fg, max(0.0, bot / 255)))


def draw_pressure(s: Screen, d: Data, t: float, x0: int, y0: int, x1: int, y1: int,
                  lo: float, hi: float) -> None:
    """The band during the window: the same four rows as always, same size, centred, no log.

    The magnified version was a misfire ("这啥啊,算了不放大了"): at the top of the window the line has
    barely been typed, so a block font blew a single letter up over a quarter of the screen. So the
    four rows this band always leads with - the line being typed, its `// 中文`, the token chips and
    their ids - are drawn at the ordinary size and centred, with the lyric log gone. What performs is
    the colour creeping from steel to red, the beat wobble, the chips arriving as they are sung and
    the ids flickering.
    """
    u = min(1.0, max(0.0, (t - lo) / max(1e-3, hi - lo)))
    fg = _lerp(ME_HI, RED, u ** 1.5)
    s.box(x0, y0, x1, y1, "stdout · tokens", 0.5 + 0.45 * u, _lerp(UI, RED, u) if u > 0.3 else None)
    ix, iw = x0 + 2, x1 - x0 - 3
    cur = d.line_at(t)
    if cur is None or iw < 12:
        return
    ln, alpha = cur
    n_out, _ = d.typed(ln, t)
    level = 0.35 + 0.65 * alpha
    h = y1 - y0 - 1
    y = y0 + max(1, (h - 3) // 2)                 # four rows, centred in the band
    jit = int(round(2.0 * u * FP.pulse(t))) * (1 if int(t * 6) % 2 else -1)
    # 1 the line being typed, with the caret it always has
    tail = "\u2588" if n_out < len(ln["text"]) and int(t * 3) % 2 == 0 else ""
    first = "> " + ln["text"][:n_out] + tail
    s.put(ix + max(0, (iw - dw(first)) // 2) + jit, y, first, fg)
    y += 1
    # 2 its Chinese, centred under it
    cn = lyric_cn(ln["text"])
    if cn:
        ctext = "// " + cn
        s.put(ix + max(0, (iw - dw(ctext)) // 2), y, ctext, _lerp(ME_TEXT, RED, u))
    y += 2
    # 3 the token chips, as one centred block: the film's own plates, arriving as they are sung
    pos, chips = 0, []
    for tok in tokenize(ln["text"]):
        start = ln["text"].find(tok, pos)
        if start < 0:
            continue
        pos = start + len(tok)
        if start >= n_out:
            break
        shown = tok[1:] if tok.startswith("-") else tok        # `-` is a split, not a sound
        tid = str(token_id(tok))
        chips.append((shown, start, max(len(tok) + 3, len(tid) + 2), tid))
    total = sum(w for _, _, w, _ in chips) - 1 if chips else 0
    x = ix + max(0, (iw - total) // 2)
    kw = keyword_colour(ln["text"])
    for (shown, start, wpl, tid) in chips:
        hot = start <= n_out - 1
        if kw is not None:
            s.put(x, y, f" {shown} ", BG, _lerp(kw, RED, u) if hot else mix(kw, 0.4))
        else:
            s.put(x, y, f" {shown} ", mix(ANOM, 0.95), mix(ANOM, 0.13 if hot else 0.06))
        # 4 its token id under the plate; the flicker gets faster as the window runs out
        flick = t % max(0.4, 1.2 - 0.8 * u) < 0.08
        s.put(x + 1 + max(0, (len(shown) - len(tid)) // 2), y + 1, tid,
              mix(UI, 0.15 if flick else max(0.2, 0.45 * level)))
        x += wpl
def draw_lyrics(s: Screen, d: Data, t: float, x0: int, y0: int, x1: int, y1: int) -> None:
    """The stdout band: the line being typed, its token chips with their token ids, and the log."""
    win = pressure_window(d.lines) if PRESSURE[0] else None
    # ten rows or the magnified block is not a block: a short window keeps the ordinary band (an
    # empty box for nine seconds would be worse than no pressure at all)
    if win and win[0] <= t < win[1] and (y1 - y0) >= 10 and (x1 - x0) >= 14:
        NOGHOST.append((x0 + 1, y0 + 1, x1 - 1, y1 - 1))
        draw_pressure(s, d, t, x0, y0, x1, y1, win[0], win[1])
        return
    s.box(x0, y0, x1, y1, "stdout · tokens", 0.45 + 0.3 * d.feat(t, "kick"))
    # text you read, over text that changes: no ghost here either (see draw_dsh)
    NOGHOST.append((x0 + 1, y0 + 1, x1 - 1, y1 - 1))
    inner_x, inner_w = x0 + 2, x1 - x0 - 3
    cur = d.line_at(t)
    y = y0 + 1
    if cur is None:
        if int(t * 2) % 2 == 0:
            s.put(inner_x, y, "█", mix(ANOM, 0.9))
        return
    ln, alpha = cur
    n_out, when = d.typed(ln, t)
    level = 0.35 + 0.65 * alpha
    s.put(inner_x - 1, y, ">", mix(ANOM, 0.6))
    s.put(inner_x, y, ln["text"][:n_out], ui(level))
    if n_out < len(ln["text"]) and int(t * 3) % 2 == 0:
        s.put(inner_x + n_out, y, "█", mix(ANOM, 0.9))
    # Chinese subtitle just below the current English line
    cn = lyric_cn(ln["text"])
    if cn:
        full = f"// {cn}"
        out_cn, used = "", 0
        for ch in full:
            wch = dw(ch)
            if used + wch > inner_w:
                break
            out_cn += ch
            used += wch
        cy = y + 1
        s.put(inner_x, cy, " " * inner_w, UI, BG)
        s.put(inner_x, cy, out_cn, mix(ME_TEXT, level * 0.65))
    y += 2
    # chips: the film draws each token as a plate with its token id underneath
    x = inner_x - 1
    pos = 0
    for k, tok in enumerate(tokenize(ln["text"])):
        start = ln["text"].find(tok, pos)
        if start < 0:
            continue
        pos = start + len(tok)
        if start >= n_out:
            break
        if x + len(tok) + 2 > inner_x + inner_w:
            x = inner_x - 1
            y += 2
            if y + 1 > y1 - 1:
                break
        shown = tok[: n_out - start]
        ws = ln["text"].rfind(" ", 0, start) + 1
        we = ln["text"].find(" ", start)
        we = len(ln["text"]) if we < 0 else we
        kw = keyword_colour(ln["text"][ws:we]) if n_out >= we else None
        if kw is not None:
            s.put(x, y, f" {shown} ", BG, kw)
        else:
            s.put(x, y, f" {shown} ", mix(ANOM, 0.95),
                  mix(ANOM, 0.13 if k % 2 == 0 else 0.22))
        tid = str(token_id(tok))
        if n_out >= pos:
            s.put(x + 1 + max(0, (len(tok) - len(tid)) // 2), y + 1, tid, ui(0.45 * level))
        # a one-character token ("-" in "lo-o-ove") must still leave room for its 5-digit id
        x += max(len(tok) + 3, len(tid) + 2)

    # the log under the chips: what just went past and what is coming. It fills whatever height the
    # band has, keeping the line being typed about a third of the way down.
    if y + 3 <= y1 - 1:
        idx = d.lines.index(ln)
        y += 2
        s.put(inner_x - 1, y, "lyric log", ui(0.55))
        y += 1
        room = max(1, y1 - y)
        first = min(max(0, idx - room // 3), max(0, len(d.lines) - room))
        for j in range(first, min(len(d.lines), first + room)):
            if y > y1 - 1:
                break
            here = j == idx
            far = abs(j - idx)
            s.put(inner_x - 1, y, ">" if here else " ", mix(ANOM, 0.6))
            s.put(inner_x, y, d.lines[j]["text"][:inner_w],
                  mix(ME_TEXT, 0.9) if here else ui(max(0.36, 0.62 - 0.08 * far)))
            y += 1


def draw_body(s: Screen, d: Data, eng: Engine | None, ent: dict | None, t: float,
              x0: int, top: int, x1: int, bottom: int) -> None:
    """Everything but the header and the footer: her pane, the stdout band, the right column."""
    cols = s.cols
    name = ent["name"] if ent else ""
    lx = max(24, min(cols - 20, int(cols * 0.60)))    # the left column ends here, the right starts after
    sp_bottom = min(top + 8, bottom - 4)      # border + 7 bands

    # her pane, above the stdout band, when the column can hold a legible portrait - and only on the
    # shots whose scene really asks for her (film_panels.shots()["her"])
    #
    # The band is given the height its content actually wants and her pane takes the rest. A log
    # that has finished printing is an empty rectangle, but a portrait handed three more rows is
    # three more rows of her - and at 13 rows the pane was too short to show anything but a band
    # across her eyes.
    main_h = bottom - top + 1
    band_want = 16 if t < SIM_START else (12 if t < SIM_END else 15)
    her = bool(eng is not None and ent is not None and ent["her"] and cols >= 96)
    her_h = 0
    for need in (band_want, BAND_MIN_H):
        her_h = min(HER_MAX_H, main_h - need)
        if her_h >= HER_MIN_H:
            break
    her = her and her_h >= HER_MIN_H
    # and the film's own window takes the pane whenever it is on screen - the clear 大肥鱼 the user
    # asked for is the only thing that outranks it (her_style == "half"), which is exactly the
    # priority the film itself uses on the page (dsh_her.py:237-260 replaces the pane's drawing).
    room = bool(ent is not None and cols >= 96 and her_h >= HER_MIN_H)
    gone = FP.dsh_gone(t)
    keep = her_keeps_pane(ent)
    chat = bool(room and CHAT[0] and FP.dsh_inside(t) and not gone and not keep)
    cursor = bool(room and CHAT[0] and gone and not keep)
    # "Though we are trapped" takes a wall off her box on every beat (sec_chorus1.py:560-565): the
    # pane is redrawn inside a smaller rect each time, with the walls it lost left behind as outlines.
    walls = FP.kv_inset(ent["u"]) if (ent is not None
                                      and ent["name"] in ("shot_trapped", "shot_red_trapped")) else 0
    hx0, hy0, hx1, hy1 = x0, top, lx, top + her_h - 1
    if walls and (her or chat):
        for j in range(walls):
            s.box(x0 + j * 6, top + j, lx - j * 6, hy1 - j, "", 0.15)
        hx0, hy0, hx1, hy1 = x0 + walls * 6, top + walls, lx - walls * 6, hy1 - walls
    if chat:
        WINDOW[0] = "chat"
        CLEAR.append((hx0, hy0, hx1, hy1))      # before the draw: `put` skips the vignette in here
        draw_dsh(s, hx0, hy0, hx1, hy1, t)
    elif cursor:
        WINDOW[0] = "cursor"
        CLEAR.append((hx0, hy0, hx1, hy1))
        draw_cursor(s, hx0, hy0, hx1, hy1, t)
    elif her:
        WINDOW[0] = "her"
        draw_her(s, d, ent, hx0, hy0, hx1, hy1, t)
    else:
        WINDOW[0] = "-"
    band_top = top + (her_h if (her or chat or cursor) else 0)

    # --------------------------------------------------------------- stdout band
    if t < SIM_START:
        draw_boot_log(s, x0, band_top, lx, bottom, t)
    elif t < SIM_END:
        draw_sim_start(s, x0, band_top, lx, bottom, t)
    else:
        CLEAR.append((x0, band_top, lx, bottom))     # before the draw, so `put` leaves its colour alone
        draw_lyrics(s, d, t, x0, band_top, lx, bottom)

    # --------------------------------------------------------- spectrum panel
    s.box(lx + 1, top, x1, sp_bottom, "feature bands", 0.55, ME_TEXT)
    inner = sp_bottom - top - 1
    for i in range(min(7, inner)):
        yy = top + 1 + i
        v = d.band(t, i)
        s.put(lx + 3, yy, BANDS[i].rjust(7), ui(0.68))
        bar_x, bar_w = lx + 12, max(4, x1 - (lx + 12) - 1)
        s.hbar(bar_x, yy, bar_w, v, mix(ME_TEXT, 0.45 + 0.55 * v))

    # ------------------------------------------------------- the chapter panel
    # the drawings that were always terminal text, on the shots that own them: (want, least worth
    # drawing). The mask needs its twelve rows or it is not a matrix, so its minimum is its want.
    pane, need, least = None, 0, 0
    rw = x1 - lx - 2                                    # the right column's inner width
    if name == "shot_corpus":
        pane, need, least = "corpus", 10, 6
    elif name == "shot_losscurve":
        pane, need, least = "loss", 13, 8
    elif name == "shot_blind":
        pane, need, least = "mask", FP.MN + 2, FP.MN + 2
    elif name in ("shot_memory_ls", "shot_erase"):
        pane, need, least = "memory", 13, 8
    # the three big text pictures. The KV cache wants its whole 60x22 grid (that grid *is* the
    # drawing), the weight dump its 24 rows, and the flood takes the screen rather than a panel.
    elif name in ("shot_trapped", "shot_red_trapped") and rw >= FP.KV_COLS:
        pane, need, least = "kv", FP.KV_ROWS + 6, FP.KV_ROWS + 4
    elif name == "shot_strange" and rw >= 46:
        pane, need, least = "expert", FP.EXPERT_ROWS + 2, FP.EXPERT_ROWS + 2
    # scenes.py's own drawings
    elif name == "shot_circle" and rw >= 40:
        pane, need, least = "rope", 16, 12
    elif name == "shot_sine" and rw >= 30:
        pane, need, least = "sine", 18, 12
    elif name == "shot_tangent" and rw >= 30:
        pane, need, least = "tangent", 14, 9
    elif name == "shot_limit" and rw >= 30:
        pane, need, least = "limit", 10, 8
    elif name == "shot_current" and rw >= 30:
        pane, need, least = "gpu", 12, 10
    elif name in ("shot_then_i_can", "shot_red_then_i_can") and rw >= 70:
        pane, need, least = "conv", 16, 12
    elif name == "shot_simulations" and rw >= 40:
        pane, need, least = "samples", 20, 14
    elif name == "shot_execute_all" and rw >= 40:
        pane, need, least = "exec_all", 20, 14
    # the two the film draws as full-bleed art: the IF I CAN glyph banner dissolving into her, and
    # chorus 1's next-token bars in red with 'execution' winning (scenes_exec.py:231 / 425)
    elif name == "shot_red_if_i_can" and rw >= 40:
        pane, need, least = "ifican", 18, 12
    elif name == "shot_only_execution" and rw >= 44:
        pane, need, least = "logits", 15, 11
    # The three the film already draws as character grids. Each needs its whole grid or it is not
    # the drawing - a whale with its flukes cut off is not a smaller whale - so need == least, and
    # the width is checked here rather than inside the panel, because a panel that cannot fit
    # should hand its rows back to the ops ticker rather than appear as an empty box.
    elif name == "shot_whale" and rw >= FP.WHALE_COLS + 2:
        # six extra rows above her: the film's pane leaves about that much room for the spout's
        # 130 px rise, and a short window still gets the whale with a shorter plume
        pane, need, least = "whale", FP.WHALE_ROWS + 8, FP.WHALE_ROWS + 2
    elif name == "shot_dualpipe" and rw >= FP.PIPE.get("steps", 99) + 6:
        pane, need, least = "dualpipe", FP.PIPE.get("ranks", 99) + 3, FP.PIPE.get("ranks", 99) + 3
    elif name == "shot_moe_dense" and rw >= FP.MOE_COLS + 2:
        pane, need, least = "moe", FP.MOE_ROWS + 4, FP.MOE_ROWS + 4
    elif name == "shot_love_loop" and rw >= 5 * FP.LOVE_PER_ROW + 2:
        # the pane fills over the shot, so a short column is a small pane, not a broken drawing
        pane, need, least = "love", 24, 10
    avail = bottom - sp_bottom
    pane_h = min(need, avail - 6)
    if not pane or pane_h < least:
        pane_h = 0
    ops_top = sp_bottom + 1
    if pane_h:
        px0, py1 = lx + 1, ops_top + pane_h - 1
        dur = ent["end"] - ent["start"]
        lt = ent["u"] * dur
        if pane == "corpus":
            draw_corpus(s, px0, ops_top, x1, py1, t)
        elif pane == "loss":
            draw_loss(s, px0, ops_top, x1, py1, t, ent["u"])
        elif pane == "mask":
            draw_mask(s, px0, ops_top, x1, py1, t)
        elif pane == "whale":
            draw_whale(s, px0, ops_top, x1, py1, t)
        elif pane == "dualpipe":
            draw_dualpipe(s, px0, ops_top, x1, py1, lt, dur)
        elif pane == "moe":
            draw_moe(s, px0, ops_top, x1, py1, t, lt, dur, ent["u"])
        elif pane == "love":
            draw_love(s, px0, ops_top, x1, py1, lt)
        elif pane == "kv":
            draw_kv(s, px0, ops_top, x1, py1, ent["u"],
                    RED if ent.get("alert_own") == "err" else None)
        elif pane == "expert":
            draw_expert(s, px0, ops_top, x1, py1, t, ent["u"])
        elif pane == "rope":
            draw_rope(s, px0, ops_top, x1, py1, t)
        elif pane == "sine":
            draw_sine(s, px0, ops_top, x1, py1, t)
        elif pane == "tangent":
            draw_tangent(s, px0, ops_top, x1, py1, lt, dur)
        elif pane == "limit":
            draw_limit(s, px0, ops_top, x1, py1, ent["u"], FP.FACTS.CTX)
        elif pane == "gpu":
            draw_gpu(s, px0, ops_top, x1, py1, t, lt, FP.FACTS.GPU)
        elif pane == "conv":
            draw_conv(s, px0, ops_top, x1, py1, ent["u"],
                      FP.KERNELS[FP.beat_index(t) % len(FP.KERNELS)])
        elif pane == "samples":
            draw_samples(s, px0, ops_top, x1, py1, t, lt, dur, ent["u"])
        elif pane == "exec_all":
            draw_samples(s, px0, ops_top, x1, py1, t, lt, dur, ent["u"], execute=True)
        elif pane == "ifican":
            draw_if_i_can(s, px0, ops_top, x1, py1, t, lt, dur)
        elif pane == "logits":
            draw_only_execution(s, px0, ops_top, x1, py1, lt, dur)
        else:
            draw_memory(s, px0, ops_top, x1, py1, t)
        ops_top = py1 + 1

    # -------------------------------------------------------------- ops ticker
    draw_ops(s, lx + 1, ops_top, x1, bottom, t,
             ent["ops"] if ent else ["IDLE"], ent["alert"] if ent else None)


def draw_footer(s: Screen, d: Data, t: float, playing: bool, fps: float, ent: dict | None,
                rows: int, cols: int, audio=None) -> None:
    py = rows - 4
    s.box(1, py, cols - 2, py + 2, "progress", 0.5)
    bar_x, bar_w = 4, max(10, cols - 8)
    s.hbar(bar_x, py + 1, bar_w, t / END, mix(ME_TEXT, 0.9))
    mark = bar_x + min(bar_w - 1, int(t / END * bar_w))
    s.put(mark, py + 1, "▓", BG, mix(ME_HI, 1.0))
    left = f"shot {ent['index'] + 1:02d}/{ent['total']}  {ent['name']}" if ent else ""
    if ent is not None:
        # what the left pane holds first, then how she is drawn and what `auto` resolved to: the
        # front of the string is what survives truncation on a narrow window
        left += f"  win:{WINDOW[0] or '-'}"
        how, tint = her_style(ent)
        left += f"  her:{HER_RENDER}" + (f"->{how}/{tint}" if HER_RENDER == "auto" else "")
    if audio is not None and audio.ok:       # the music's own state, next to the film's shot table
        left += f"  vol {audio.volume // 10:3d}%" + ("  MUTED" if audio.muted else "")
    left += "  fx:" + ("on" if FX["on"] else "off")
    # The hint line is right-aligned. At 96-120 columns the long version started *before* the left
    # text ended, so `PLAYING 24.0 fps` was printed on top of `her:auto->...`. Measure it first, and
    # keep a short version for narrow windows.
    if cols >= 130:
        msg = (f"{'PLAYING' if playing else 'paused '}  {fps:4.1f} fps   h her   c chat   x fx   "
               f"space toggle   q quit")
    else:
        msg = f"{'PLAY' if playing else 'PAUSE'} {fps:4.1f}fps  h her  c chat  x fx  q quit"
    room = max(0, cols - len(msg) - 4)
    if len(left) > room:                     # drop whole fields rather than cut one in half
        fields = left.split("  ")
        while fields and len("  ".join(fields)) > room:
            fields.pop()
        left = "  ".join(fields)
    s.put(2, rows - 1, left, ui(0.55))
    s.put(max(2, cols - len(msg) - 1), rows - 1, msg,
          ui(0.62) if playing else mix(ANOM, 0.8))


def draw(s: Screen, d: Data, eng: Engine | None, t: float, playing: bool, fps: float,
         audio=None) -> None:
    cols, rows = s.cols, s.rows
    ent = eng.entry_at(t) if eng is not None else None
    NOW[0] = t
    CLEAR.clear()
    NOGHOST.clear()
    # the header line and the footer (progress box + the two status lines) are chrome: text you read,
    # not picture. What is left to ripple is the panes - her box and the right column's drawing.
    CLEAR.append((0, 0, cols - 1, 0))
    CLEAR.append((0, rows - 4, cols - 1, rows - 1))
    # a cut: the film reveals two thirds of its 96 cuts cell by cell (continuity_full_v2/cuts.py) and
    # hard-cuts the rest. The next frame draws the new shot, and `fx_apply` below holds the old
    # picture in the cells whose own time has not come yet.
    idx = ent["index"] if ent else None
    if idx != _LAST_SHOT[0]:
        if _LAST_SHOT[0] is not None:
            fx_cut(s, t, ent)
        else:
            _CUT[0] = None
        _LAST_SHOT[0] = idx
    # engine.py:91-94 through tuikit.py:68-73: set the frame's global gain *before* anything is
    # drawn, because every plain-UI colour reads it. 110.4 s is the second "Though you have left".
    UI_GAIN[0] = FP.ui_gain_at(t, ent["name"] if ent else "", ent["u"] if ent else 0.0)
    s.fill(0, 0, cols - 1, rows - 1, " ", UI, BG)

    # ------------------------------------------------------------------ header
    s.put(1, 0, "WORLD.EXECUTE(ME);", ui(1.0))
    s.put(21, 0, "whale@deepsea:~", ME_TEXT)
    wav_x, clock = 38, f"{int(t // 60):02d}:{t % 60:04.1f} / 03:32"
    tail = f"  {d.chapter(t)}"
    wav_w = max(8, cols - wav_x - len(clock) - len(tail) - 4)
    if wav_w > 8:
        s.waveform(wav_x, 0, wav_w, d.wave, t, mix(ME_TEXT, 0.85))
    s.put(cols - len(clock) - len(tail) - 2, 0, clock, ui(UI_DIM_LEVEL))
    s.put(cols - len(tail) - 1, 0, tail, mix(ANOM, 0.75))

    top, bottom = 1, rows - 5
    if bottom - top < 6:
        fx_apply(s, t, ent)
        return
    # the 07 EXECUTION hits and the count are full-bleed drawings in the film and hard cuts on the
    # music, so the terminal cuts to them too rather than squeezing them into a panel
    if ent is not None and ent["name"] == "shot_exec_hit":
        draw_exec_hit(s, d, 1, top, cols - 2, bottom, t, ent["run"])
    elif ent is not None and ent["name"] == "shot_count":
        draw_count(s, 1, top, cols - 2, bottom, t)
    elif ent is not None and ent["name"] == "shot_last_execution":
        draw_last_execution(s, 1, top, cols - 2, bottom, t, t - ent["start"])
    elif ent is not None and ent["name"] == "shot_black":
        draw_black(s, 1, top, cols - 2, bottom, t)
    elif ent is not None and ent["name"] == "shot_flood":
        # blue floods the machine and covers everything, panes and all (sec_chorus2.py:336)
        draw_flood(s, 1, top, cols - 2, bottom, t, ent["u"])
    elif ent is not None and ent["name"] == "shot_collapse":
        # and the picture collapses into a line and a dot, so there is no chrome left to draw
        draw_collapse(s, 1, top, cols - 2, bottom, ent["u"])
    else:
        draw_body(s, d, eng, ent, t, 1, top, cols - 2, bottom)
    draw_footer(s, d, t, playing, fps, ent, rows, cols, audio)
    # tuikit.py:468-476's post, and the cut's reveal, both after everything else has been drawn
    fx_apply(s, t, ent)


# --------------------------------------------------------------------------- io

def enable_vt() -> None:
    if os.name != "nt":
        return
    try:                                     # the panels use -inf, block letters and box drawing
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    k = ctypes.windll.kernel32
    for h in (k.GetStdHandle(-11), k.GetStdHandle(-10)):
        mode = ctypes.c_uint32()
        if k.GetConsoleMode(h, ctypes.byref(mode)):
            k.SetConsoleMode(h, mode.value | 0x0004 | 0x0008)


def term_size(default=(120, 34)) -> tuple[int, int]:
    sz = shutil.get_terminal_size(default)
    return max(40, sz.columns), max(12, sz.lines)


# engine.py:174-176 - the film's own credit line, printed by --credits rather than clipped into a
# 120-column footer. It carries the whole attribution chain, so it is kept verbatim.
CREDITS = ("角色 溟月 © 上善无形 / 女仆版 ZipZipPipe / 立绘·表情 dsh-deep-whale, dsh-whale-galgame "
           "(CC BY-NC-SA 4.0)  ·  Music: Mili - world.execute(me);  ·  原著 · 原片 · 全部出片代码 "
           "MisakaZentai (bilibili BV1xCai6aE9g)  ·  非官方同人作品")

# The terminal player is a fan add-on by 林原林海 on top of that film, and `--credits` prints both
# lines: a copy of `_tools` that travels without the repository would otherwise carry the film's
# attribution and lose the player's.
PLAYER_CREDITS = ("终端实时版 林原林海 制作  ·  基于 MisakaZentai 的开源重建 "
                  "github.com/MisakaZentai/world-execute-me-dsh-pv  ·  代码 MIT  ·  非商业同人,"
                  "请勿商用或再上传")


def main() -> None:
    global HER_CROP, HER_RENDER
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--start", type=float, default=0.0, help="start time in seconds")
    ap.add_argument("--once", type=float, help="print one frame at this time and exit")
    ap.add_argument("--dump", type=int, help="print N frames as plain text (no colour) and exit")
    ap.add_argument("--size", help="force COLSxROWS, e.g. 120x34 (for --once/--dump)")
    ap.add_argument("--no-engine", action="store_true",
                    help="skip loading the film's shot table (no her pane and no chapter panels)")
    ap.add_argument("--shots", action="store_true",
                    help="print the shot table with the ops each shot scrolls, and exit")
    ap.add_argument("--credits", action="store_true", help="print the film's credit line and exit")
    ap.add_argument("--no-audio", action="store_true", help="do not play the song")
    ap.add_argument("--no-fx", action="store_true",
                    help="no cut reveals and no post: no trail, no vignette, no scanlines, no "
                         "breathing frames (the picture as it was before the post pass)")
    ap.add_argument("--no-mech", action="store_true",
                    help="only the delay-field reveals: off are the five mechanisms the film names "
                         "in its own cut docstrings (CARRY / MORPH / UNFOLD / SCAN / RETAIN)")
    ap.add_argument("--mech", action="store_true",
                    help="print the film's named cut mechanisms (cut index -> mechanism) and exit")
    ap.add_argument("--no-leap", action="store_true",
                    help="on the chorus hook draw the clear figure the film uses, without the hop")
    ap.add_argument("--no-pressure", action="store_true",
                    help="keep the normal stdout band through 'Challenging your God' .. 'Illegal"
                         " arguments' instead of the three big lines")
    ap.add_argument("--no-chat", action="store_true",
                    help="do not put the film's dsh chat window in the left pane (the pane is hers "
                         "everywhere instead). Live: press c")
    ap.add_argument("--audio-file", help="mp3 to play (default input/song.mp3)")
    ap.add_argument("--volume", type=int, default=1000, help="0..1000 (default 1000)")
    ap.add_argument("--audio-latency", type=float, default=pv_audio.LATENCY,
                    help="seconds the decoder runs ahead of the speaker (default %.2f)" % pv_audio.LATENCY)
    ap.add_argument("--crop", default=HER_CROP, choices=["auto", "face", "bust", "upper", "full"],
                    help=f"which part of the sprite her pane draws (default {HER_CROP}: whichever "
                         f"crop's own shape is closest to the pane's)")
    ap.add_argument("--render", default=HER_RENDER, choices=list(RENDER_MODES),
                    help="auto = the film's own choice per shot: the H3 character takes nearly "
                         "everywhere, the solid blue figure twice before the climax, red through "
                         "07 EXECUTION, red characters after it, and blue again on the last shot "
                         "she is in (the default). h3 = the character takes everywhere, where her "
                         "body is the lyric she is singing; half = the solid portrait everywhere; "
                         "glyph = the morph transition, direction strokes and a density ramp. "
                         "Live: press h to cycle, and every change glitches.")
    args = ap.parse_args()

    HER_CROP = args.crop
    HER_RENDER = args.render
    if args.no_fx:
        FX.update(on=False, reveal=False, mech=False, trail=False, vig=False)
    if args.no_mech:
        FX.update(mech=False)
    if args.no_leap:
        LEAP[0] = False
    if args.no_pressure:
        PRESSURE[0] = False
    if args.no_chat:
        CHAT[0] = False
    enable_vt()

    if args.credits:
        print(CREDITS)
        print(PLAYER_CREDITS)
        return

    if args.mech:
        n = sum(1 for m in CUT_MECH.values() for _ in m)
        print(f"the film names a mechanism on {len(CUT_MECH)} of its 96 cuts ({n} mechanisms):")
        for i in sorted(CUT_MECH):
            print(f"  cut {i:3d}  {'+'.join(CUT_MECH[i])}")
        return

    if args.shots:
        for e in Engine().table:
            alert = f"  alert={e['alert']}" if e["alert"] else ""
            her = "  her" if e["her"] else ""
            print(f"{e['index'] + 1:3d}  {e['start']:8.3f} {e['end']:8.3f}  {e['name']:<20}"
                  f"{'  '.join(e['ops'])}{alert}{her}")
        return

    d = Data()
    if not d.lines:
        print("warning: no word timeline; run `python build.py lyrics` for the lyric band",
              file=sys.stderr)

    eng = None
    if not args.no_engine:
        print("loading the film's shot table (a few seconds)...", file=sys.stderr, flush=True)
        try:
            eng = Engine()
        except Exception as exc:
            print(f"warning: could not load the engine ({exc}); her pane will be skipped",
                  file=sys.stderr)

    cols, rows = term_size()
    if args.size:
        c, _, r = args.size.partition("x")
        cols, rows = int(c), int(r)

    # ------------------------------------------------------- non-interactive
    if args.once is not None or args.dump:
        s = Screen(cols, rows)
        gc.disable()          # see main(): a gen-2 collection is a 20 ms hole in a 33 ms frame
        if args.dump:
            for k in range(args.dump):
                t = args.start + k * (END - args.start) / max(1, args.dump)
                draw(s, d, eng, t, True, 24.0)
                print(f"===== t = {t:7.2f}s   {d.chapter(t)} =====")
                print(s.text_dump())
                print()
        else:
            out = sys.stdout
            enable_vt()
            draw(s, d, eng, args.once, True, 24.0)
            s.render_diff(out)
            out.write("\x1b[0m\n")
        return

    # ---------------------------------------------------------- interactive
    import msvcrt
    out = sys.stdout
    s = Screen(cols, rows)
    t = max(0.0, min(END, args.start))
    playing = True
    last = time.perf_counter()
    fps, shown = 0.0, 0
    fps_t0 = last

    # the music. The picture follows it: `lock()` returns the song time being heard whenever the
    # wall clock has wandered off it, and None when they agree.
    audio = pv_audio.Audio(args.audio_file, enabled=not args.no_audio, volume=args.volume,
                           latency=args.audio_latency)
    if args.no_audio:
        pass
    elif not audio.ok:
        print(f"no music: {audio.error}\n  (the film's audio is {pv_audio.DEFAULT_SONG})",
              file=sys.stderr, flush=True)
    else:
        audio.play(t)

    def seek_to(nt: float) -> float:
        """Move the playhead and take the sound with it."""
        nt = max(0.0, min(END, nt))
        if audio.ok:
            (audio.play if playing else audio.seek)(nt)
        return nt

    out.write("\x1b[?1049h\x1b[?25l\x1b[2J")     # alt screen, hide cursor
    # A frame is a small pile of short-lived lists and tuples, so reference counting frees nearly
    # all of it. What it does not free is cyclic garbage, and a gen-2 pass over it landed as a
    # 20-27 ms hole in a 33 ms frame every few seconds - measured, not guessed: with the collector
    # off the worst frame of the whole song drops from 26.8 ms to 7.2 ms.
    gc.disable()
    try:
        while True:
            now = time.perf_counter()
            dt = now - last
            last = now
            if playing:
                t = min(END, t + dt)
                if audio.ok:
                    tgt = audio.lock(t)
                    if tgt is not None:
                        t = max(0.0, min(END, tgt))
                if t >= END:
                    playing = False
                    if audio.ok:
                        audio.pause()
            while msvcrt.kbhit():
                ch = msvcrt.getwch()
                if ch in ("q", "Q", "\x1b"):
                    raise KeyboardInterrupt
                elif ch == " ":
                    playing = not playing
                    if audio.ok:
                        (audio.play if playing else audio.pause)(t)
                elif ch in ("m", "M"):
                    audio.mute()
                elif ch in ("h", "H"):
                    # cycle how she is drawn, so the choice can be made while watching rather than
                    # by editing a shot list. Switching *to* an H3 mode pays its set-up now.
                    HER_RENDER = RENDER_MODES[(RENDER_MODES.index(HER_RENDER) + 1)
                                              % len(RENDER_MODES)]
                    if HER_RENDER in ("h3", "auto"):
                        import her_glyphs as hg2
                        hg2.warm_h3()
                elif ch in ("x", "X"):
                    # the whole post pass and the cut reveals, so the difference can be seen live
                    FX["on"] = not FX["on"]
                    fx_clear(s)
                    s.dim = s._dim_field()
                elif ch in ("c", "C"):
                    # the film's dsh window in the left pane, or her in it everywhere
                    CHAT[0] = not CHAT[0]
                elif ch in ("-", "_"):
                    audio.set_volume(audio.volume - 100)
                elif ch in ("=", "+"):
                    audio.set_volume(audio.volume + 100)
                elif ch in (",", "<"):
                    t = seek_to(t - 1)
                elif ch in (".", ">"):
                    t = seek_to(t + 1)
                elif ch in ("\x00", "\xe0"):        # arrow / home / end: a second code follows
                    code = msvcrt.getwch()
                    if code == "K":                 # left
                        t = seek_to(t - 5)
                    elif code == "M":               # right
                        t = seek_to(t + 5)
                    elif code == "G":               # home
                        t = seek_to(0.0)
                    elif code == "O":               # end
                        t = seek_to(END)
            ncols, nrows = term_size()
            if (ncols, nrows) != (s.cols, s.rows):
                cols, rows = ncols, nrows
                s.resize(cols, rows)
                _CUT[0] = None               # the frozen frame is the old size
                out.write("\x1b[2J")
            draw(s, d, eng, t, playing, fps, audio)
            s.render_diff(out)
            shown += 1
            if now - fps_t0 >= 0.5:
                fps = shown / (now - fps_t0)
                shown, fps_t0 = 0, now
            time.sleep(max(0.0, 1 / 30 - (time.perf_counter() - now)))
    except KeyboardInterrupt:
        pass
    finally:
        gc.enable()
        audio.close()
        out.write("\x1b[0m\x1b[?25h\x1b[?1049l")
        out.flush()


if __name__ == "__main__":
    main()
