"""Her dance: for any time t, the pose she holds and how her body moves (the vocabulary is in motion.py).

    at(t, base, pinned) -> Step

`base` is the expression the shot chose for the lyric (one of the eight expressions, never "skirt"). In the calm
parts she holds it and moves with idle motion; in the dance parts she dances through the pose library and comes
back to it at phrase ends. `pinned` means the shot has pinned an overlay onto her (a kernel box, a heatmap): she
keeps `base`, unflipped, never turns, hops or steps, and sways at most 2 degrees. at() is a pure function of its
arguments (the caches below only memoise).

Clock. The drums run at 129.9 BPM: the kick onsets in audio_features.json sit 35 ms behind the engine's 130 BPM
grid at the start and 0.2 s behind it by the end. Her body keeps time with the drums (bpos / btime), so the squash
lands on the kick you hear. Pose changes are quantised to those beats (eighths in the glitch parts); in 07
EXECUTION they fall on the PV's 13 hard cuts instead, so her hit and the cut land together. A pose change sets
prev / prev_flip and morphs over a quarter beat. A turn swaps the pose while she is edge-on (turn = 0.5) and
ends mirrored; the next frame has turn = 0 and the flip toggled, which is the same image.

Motion. A sum of layers, each a smooth function of the beat phase, weighted per section (SECTIONS; the weights
cross-fade over about a beat at each section start) and driven by the audio:
  squash   a fast hit on every kick onset (found per eighth in the bass band), scaled by its strength
  hop      arcs that take off after a beat and land on the next one if it has a kick; height ~ loudness
  gate     the rhythmic layers fade out where the song goes quiet (the break at 14 s, the silence before the cut)
Moves (MOVES) are windowed layers tied to lyric beats; a move can also mute the rhythm under it. Hair, hem and
tail are her sideways motion put through a damped spring (the response peaks ~1/8 beat after the body, overshoots
and settles), plus their own wag and float; + means the swing points right, like sway.

Sections (drum beats; times are where they start):
  boot          0.0 s   being created: breathing, a slow sway, pose = base. "And let's begin ... simulation":
                        three little bounces, a crouch in the two-beat break, the first hop when the drums return
  pretrain     15.0     gentle groove: half-note sway, head bob on the beats; a new pose every 2 bars at most
  verse1       29.3     acting: base pose, idle sway, a head tilt on each beat, a bounce on each downbeat;
                        "so dizzy" wobble, "to AD, to BC" side steps, "so deeply" slow deep bend
  rlhf         58.9     chorus 1: pose to pose on the beats (starry, cheerful, skirt, frightened as a cheer),
                        mirrored every other bar, hops onto the kicks, a step side to side each bar; a spin at
                        the phrase end, a starry hit on "happy", a hit and a one-beat freeze on "execution"
  deploy       73.6     playful acting: base pose, a cute bounce that follows the syncopated drums; a curtsy on
                        "purr", pointing on "proof", mirrored on "to F, to M" / "to S, to M", a slow hypnotic
                        sway through "the trance"
  chorus2     103.2     "feel your vibrations": the chorus dance again, ending in a spin back to base
  user_left   110.6     "you have left" x5: a flinch on each (smaller every time), drooping into shy /
                        exasperated while the dance runs down to stillness; hair and hem settle
  reward_hack 118.0     stiff and mechanical: the lean snaps between fixed angles, sudden head snaps, angry /
                        serious; stutter bursts on eighths grow denser and the scramble rises toward 147
  execution   147.6     glitch dance at full energy: a hit on each of the 13 cuts (base pose, scramble spike),
                        random poses and flips on the eighths between, jerky sway, a hop onto every kick; the
                        six-language count gets one pose per word
  red_chorus  162.3     chorus 1 again, glitched: pose to pose with eighth-note stutters; a soft shy moment on
                        "have you back", the execution hit again, then "we are trapped": shaking, and power-off
  eval_love   177.1     calm and warm: gentle sway, base / shy / cheerful, a slow curtsy on "properly lo-o-ove"
  whale_fall  193.7     sinking: no hops, a slow drift down, hair and tail floating slowly; pose frozen to shy
  halt        207.58    the song stops dead: she freezes where she is
"""

from __future__ import annotations

import bisect
import math
import random
from collections import namedtuple
from functools import lru_cache

import music
from engine import BEAT, FIRST_BEAT, HARD_CUT, LYRICS, SONG_LEN, keyframes, lyric_start, snap8
from motion import Motion, Step

# ---------------------------------------------------------------- the drum clock

DRUM0 = FIRST_BEAT + 0.035   # the first kick onset
DRUM_BEAT = BEAT + 0.00037   # 129.9 BPM (a line through the kick onsets of the whole song)
MORPH = BEAT / 4             # a pose change morphs over a quarter beat


def bpos(t: float) -> float:
    """Position on the drum clock, in beats: beat n falls on a kick."""
    return (t - DRUM0) / DRUM_BEAT


def btime(b: float) -> float:
    return DRUM0 + b * DRUM_BEAT


def _lb(prefix: str, after: float = 0.0) -> int:
    """The drum beat a lyric line starts on."""
    return round(bpos(lyric_start(prefix, after)))


B_SIM = _lb("And let's begin the sim")      # 27
B_DROP = 32                                  # the drums come back after a two-beat break (14.0 - 14.9 s)
B_V1 = _lb("If I'm a set")                   # 63
B_DIZZY = _lb("So dizzy")                    # 106
B_TRAVEL = _lb("Oh, we can travel")          # 110
B_DEEPLY = _lb("So deeply")                  # 123
B_C1 = _lb("If I can", 58)                   # 127: the pickup, in a one-beat break; the chorus drops on 128
B_HAPPY = _lb("If I can make")               # 143; "happy" is sung two beats in (the shot turns starry there)
B_RUN = _lb("I will run", 67)                # 147; "execution" two beats in (the shot flashes EXECUTE there)
B_V2 = _lb("If I'm an eggplant")             # 159
B_PURR = _lb("Then I will purr")             # 178
B_PROOF = _lb("Then you're the proof")       # 186
B_FM = _lb("To F, to M")                     # 194
B_SM = _lb("To S, to M")                     # 210
B_TRANCE = _lb("So we can enter")            # 214
B_C2 = _lb("If I can", 102)                  # 223
B_LEFT = _lb("Though you have left")         # 239
STUTTERS = [round(bpos(a)) for a, _, s in LYRICS if 110 <= a < 116 and "have left" in s.lower()]
B_HACK = _lb("If I can", 117)                # 255
B_ILLEGAL = _lb("Illegal arguments")         # 283
B_RED = _lb("If I can", 162)                 # 351
B_BACK = _lb("If I can have")                # 367
B_RUN2 = B_RUN + (B_RED - B_C1)              # 371: the final chorus repeats chorus 1 beat for beat
B_LOVE = _lb("I've studied", 176)            # 383
B_PROPERLY = _lb("How to properly")          # 387
B_IAM = _lb("I am trapped")                  # 409
B_FALL = round(bpos(snap8(193.46)))          # 419: the whale-fall cut
B_LAST = _lb("Execution", 205)               # 445

# the PV's hard cuts in 07 EXECUTION (as sec_final builds them): twelve hits, the count, the thirteenth hit
EXEC_CUTS = [snap8(a) for a, _, s in LYRICS if 147 <= a < 158.5 and s.lower().startswith("execution")]
T_COUNT = snap8(lyric_start("Ein", 158))
EXEC_CUTS.append(snap8(lyric_start("Execution", 161)))
EXEC_WIN = sorted([(c, "hit", k) for k, c in enumerate(EXEC_CUTS)] + [(T_COUNT, "count", 0)])
_EXEC_STARTS = [w[0] for w in EXEC_WIN]
B_EXEC = math.floor(bpos(EXEC_CUTS[0]))      # 319

# ---------------------------------------------------------------- pose sets

HAPPY = ["starry", "cheerful", "skirt", "frightened"]           # chorus; frightened reads as a cheer here
RED = ["angry", "frightened", "starry", "serious", "exasperated"]
CALM = ["cheerful", "starry", "shy", "confused", "serious"]
GLITCH = ["angry", "frightened", "serious", "starry", "exasperated", "confused"]
STUTTER = ["angry", "serious", "exasperated", "frightened"]
COUNT = ["serious", "cheerful", "starry", "frightened", "exasperated", "angry"]  # ein (one finger up) .. liu
PATTERNS = [(2, 2), (1, 1, 2), (2, 1, 1), (1, 2, 1), (1, 1, 1, 1)]           # beats per pose within a bar
PATTERN_W = [3, 2, 2, 2, 1]

# ---------------------------------------------------------------- sections

# layer weights: idle (breath and slow sway), groove (half-note sway, deg), bob (head on the beats, deg),
# tilt (acting head tilt per beat, deg), bounce (hop per beat, pattern bpat), hop (jump onto the next kick,
# pattern hpat), kick (squash gain), step (side step each bar), tail (own wag per beat), stiff, jerk, float
Style = namedtuple("Style", "idle groove bob tilt bounce bpat hop hpat kick step tail stiff jerk float",
                   defaults=(0.0, 0.0, 0.0, 0.0, 0.0, (1, 0, 0, 0), 0.0, (1, 1, 1, 1), 0.0, 0.0, 0.0, 0.0, 0.0, 0.0))
# start in seconds; fade = beats of cross-fade (before, after the start); poses = the pose generator
Section = namedtuple("Section", "name start fade poses move style")

SECTIONS = [
    Section("boot", 0.0, (0, 0), "base", "breathe", Style(idle=1.0, kick=0.1, tail=0.12, float=0.25)),
    Section("pretrain", btime(B_DROP), (0.5, 0.5), "phrase", "groove",
            Style(idle=0.3, groove=3.0, bob=2.0, bounce=0.006, bpat=(1, .5, .8, .5), kick=0.3, tail=0.35)),
    Section("verse1", btime(B_V1), (1, 1), "base", "act",
            Style(idle=0.8, groove=1.0, tilt=2.5, bounce=0.01, kick=0.25, tail=0.25)),
    Section("rlhf", btime(B_C1), (0.5, 1), "dance", "dance",
            Style(groove=4.5, bob=2.5, hop=0.035, hpat=(1, .55, .85, .55), kick=0.5, step=0.03, tail=0.5)),
    Section("deploy", btime(B_V2), (0.5, 1.5), "base", "act",
            Style(idle=0.6, groove=1.8, tilt=3.0, hop=0.012, hpat=(1, .7, 1, .7), kick=0.35, tail=0.35)),
    Section("chorus2", btime(B_C2), (0.5, 1), "dance", "dance",
            Style(groove=4.0, bob=2.2, hop=0.03, hpat=(1, .5, .8, .5), kick=0.45, step=0.025, tail=0.45)),
    Section("user_left", btime(B_LEFT), (0.5, 1), "left", "run_down",
            Style(idle=0.4, groove=2.5, bob=1.2, kick=0.3, tail=0.3)),
    Section("reward_hack", btime(B_HACK), (0.5, 0.5), "hack", "stiff", Style(stiff=1.0, kick=0.3, tail=0.15)),
    Section("execution", EXEC_CUTS[0], (0.5, 0.25), "exec", "glitch", Style(jerk=1.0, hop=0.03, kick=0.6, tail=0.4)),
    Section("red_chorus", btime(B_RED), (0.5, 0.5), "red", "red_dance",
            Style(groove=3.5, bob=2.0, jerk=0.55, hop=0.03, hpat=(1, .7, 1, .7), kick=0.55, step=0.025, tail=0.5)),
    Section("eval_love", btime(B_LOVE), (0.25, 1), "love", "warm",
            Style(idle=0.6, groove=2.2, tilt=1.5, bounce=0.004, bpat=(1, 0, .5, 0), kick=0.15, tail=0.3)),
    Section("whale_fall", btime(B_FALL), (1, 2), "shy", "sink", Style(float=1.0)),
]
_STARTS = [s.start for s in SECTIONS]

# ---------------------------------------------------------------- moves

# (first drum beat, beats, move, pose override, flip override, params). A pose of "base" means the shot's
# expression; for "turn" the pose is the one she comes out of the spin in. "hold" only overrides the pose.
MOVES = [
    (B_SIM, 3, "bounce", None, None, {}),                   # "and let's begin ... simulation": little bounces
    (B_DROP - 2, 2, "crouch", None, None, {}),              # the two-beat break: wind up...
    (B_DROP, 1, "launch", None, None, {"hop": 0.03}),        # ...and hop in with the drums
    (B_DIZZY, 4, "wobble", None, None, {}),                 # "so dizzy, so dizzy"
    (B_TRAVEL, 9, "travel", None, None, {}),                # "to AD, to BC"
    (B_DEEPLY, 4, "deep_bend", None, None, {}),             # "so deeply, so deeply"
    (B_C1, 1, "crouch", None, None, {}),                    # the break before the chorus drops
    (B_HAPPY, 1, "turn", "starry", None, {}),               # phrase end: spin, come out arm up
    (B_HAPPY + 2, 2, "starry_hit", "starry", False, {}),    # "happy"
    (B_RUN + 2, 2, "exec_hit", "base", False, {"freeze": 1}),  # "execution": hit, hold still for a beat
    (B_V2 - 1, 1, "turn", "base", None, {}),                # end of chorus 1: spin back into her acting pose
    (B_PURR, 4, "curtsy", "skirt", None, {}),               # "purr for your enjoyment"
    (B_PROOF, 4, "point", "serious", None, {}),             # "you're the proof ..."
    (B_FM + 1, 2, "switch", None, True, {}),                # "to F, ...
    (B_FM + 3, 1, "switch", None, False, {}),               #  ... to M"
    (B_SM + 1, 2, "switch", None, True, {}),                # "to S, ...
    (B_SM + 3, 1, "switch", None, False, {}),               #  ... to M"
    (B_TRANCE, B_C2 - B_TRANCE, "trance", None, None, {}),  # "so we can enter ..."
    (B_C2, 1, "crouch", None, None, {}),
    (B_LEFT - 1, 1, "turn", "base", None, {}),              # "finally be completion": spin back to base
    (B_LEFT, B_HACK - B_LEFT + 0.8, "run_down", None, None, {}),
    *[(s, 1.5, "flinch", None, None, {"a": 1 - 0.14 * k, "dir": (-1) ** k}) for k, s in enumerate(STUTTERS)],
    (B_ILLEGAL, 2, "snap", None, None, {}),                 # "illegal arguments"
    (B_BACK - 1, 1, "turn", "shy", None, {}),               # phrase end: spin, come out soft
    (B_BACK, 4, "restore", "shy", False, {}),               # "if I can have ..."
    (B_RUN2 + 2, 2, "exec_hit", "base", False, {"freeze": 1}),  # "I will run ...", again
    (B_RUN2 + 4, B_LOVE + 1 - B_RUN2 - 4, "collapse", None, None, {}),  # "though we are trapped ... ah"
    (B_RUN2 + 8, B_LOVE - B_RUN2 - 8, "hold", "base", False, {}),        # powered off: one pose
    (B_PROPERLY + 1, 4, "curtsy", "skirt", None, {"down": 2.0}),        # "how to properly ..."
    (B_IAM, B_FALL - B_IAM, "hold", "shy", False, {}),      # "I am trapped ..."
    (B_FALL, 64, "sink", None, None, {}),
    (B_LAST, 2, "flicker", None, None, {}),                 # the last "Execution"
]
_POSE_MOVES = [mv for mv in MOVES if mv[2] == "turn" or mv[3] or mv[4] is not None]
_FREEZES = [(b0, p["freeze"]) for b0, L, kind, pose, flip, p in MOVES if p.get("freeze")]
TRAVEL = (0.02, 0.04, 0.04, 0.025, 0.045, 0.045, 0.0, -0.04, 0.0)  # side-step targets, one per beat

# speed of the text streaming through her (drum beat, flow)
FLOW = [(0, 0.3), (B_SIM, 0.55), (B_DROP - 0.5, 0.6), (B_DROP, 1.0), (B_DEEPLY, 1.0), (B_DEEPLY + 1, 0.7),
        (B_C1 + 0.5, 0.7), (B_C1 + 1, 1.6), (B_HAPPY + 2, 1.9), (B_RUN + 2, 2.1), (B_RUN + 4, 1.7),
        (B_V2 - 0.5, 1.6), (B_V2 + 0.5, 1.0), (B_TRANCE, 1.0), (B_TRANCE + 2, 0.5), (B_C2 + 0.5, 0.5),
        (B_C2 + 1, 1.6), (B_LEFT, 1.6), (B_LEFT + 7, 0.9), (B_LEFT + 13, 0.3), (B_HACK, 0.3), (B_HACK + 1, 0.9),
        (B_EXEC - 1, 1.8), (bpos(EXEC_CUTS[0]), 3.0), (B_RUN2 + 4, 3.0), (B_LOVE - 1, 0.5), (B_LOVE + 1, 0.7),
        (B_FALL, 0.7), (B_FALL + 8, 0.3), (B_FALL + 20, 0.2)]

# ---------------------------------------------------------------- curves

SW, BE, SQ, HO, SH, HE, HA, HM, TA, TU = range(10)  # body channels (HA HM TA: the parts' own motion)


def _smooth(x: float) -> float:
    x = 0.0 if x < 0 else 1.0 if x > 1 else x
    return x * x * (3 - 2 * x)


def _arc(x: float) -> float:
    """A jump: 0 at take-off and landing."""
    return 4 * x * (1 - x) if 0 < x < 1 else 0.0


def _win(x: float, length: float, fin: float, fout: float) -> float:
    """0..1 over [0, length], easing in over `fin` and out over `fout`."""
    if x <= 0 or x >= length:
        return 0.0
    return min(_smooth(x / fin), _smooth((length - x) / fout))


def _tick(u: float, a: float = 0.15, length: float = 1.0) -> float:
    """Snap to 1 in `a`, ease back to 0 at `length` (zero at both ends)."""
    if u <= 0 or u >= length:
        return 0.0
    return _smooth(u / a) if u < a else 0.5 + 0.5 * math.cos(math.pi * (u - a) / (length - a))


def _hit(x: float, attack: float = 0.07) -> float:
    """Squash around a hit x seconds ago: fast attack, quick exponential recovery, gone after 0.25 s."""
    if x < -attack or x > 0.25:
        return 0.0
    if x < 0:
        return math.sin(math.pi / 2 * (x + attack) / attack) ** 2
    return math.exp(-x / 0.075) * (1 - _smooth((x - 0.12) / 0.13))


def _soft(x: float, lim: float) -> float:
    """Linear up to 3/4 of the limit, then eases into it."""
    k = 0.75 * lim
    a = abs(x)
    if a <= k:
        return x
    return math.copysign(k + (lim - k) * math.tanh((a - k) / (lim - k)), x)


def _steps(x: float, fn, trans: float) -> float:
    """Held values fn(i) on [i, i+1), each reached from the last in `trans`."""
    i = math.floor(x)
    a = fn(i - 1)
    return a + (fn(i) - a) * _smooth((x - i) / trans)


@lru_cache(maxsize=16384)
def _rnd(i: int, salt: int) -> float:
    return random.Random(i * 1000003 + salt).random()


# ---------------------------------------------------------------- the audio, per beat

@lru_cache(None)
def _audio() -> tuple[list, list, list]:
    """Kick onsets per drum eighth as (strength 0..1, time); loudness per drum beat, raw and smoothed."""
    tb = music.table()
    rate, kick, loud = tb["rate"], tb["kick"], tb["loud"]
    nb = int(bpos(SONG_LEN)) + 3
    hits = []
    for m in range(2 * nb):
        c = btime(m / 2)
        best, when = 0.0, c
        for i in range(max(1, int((c - 0.09) * rate)), min(len(kick) - 1, int((c + 0.13) * rate) + 1)):
            if kick[i] - kick[i - 1] > 0.15:  # a rise: an onset, not the tail of the last one
                v = max(kick[i], kick[i + 1])
                if v > best:
                    best, when = v, i / rate
        hits.append((_smooth((best - 0.3) / 0.55), when))
    lb = []
    for n in range(nb):
        i0, i1 = int(max(0.0, btime(n) - 0.05) * rate), int(max(0.0, btime(n + 1) - 0.05) * rate)
        seg = loud[i0:max(i0 + 1, i1)] or [0.0]
        lb.append(sum(seg) / len(seg))
    ls = [(lb[max(0, n - 1)] + 2 * lb[n] + lb[min(nb - 1, n + 1)]) / 4 for n in range(nb)]
    return hits, lb, ls


def _kick(t: float, b: float) -> float:
    hits = _audio()[0]
    m0 = math.floor(2 * b)
    s = 0.0
    for m in (m0 - 1, m0, m0 + 1):
        if 0 <= m < len(hits) and hits[m][0] > 0:
            s += hits[m][0] * _hit(t - hits[m][1])
    return s


def _kgate(n: int) -> float:
    """Is there a kick on drum beat n to land on."""
    hits = _audio()[0]
    return hits[2 * n][0] if 0 <= 2 * n < len(hits) else 0.0


def _loudn(n: int) -> float:
    lb = _audio()[1]
    return min(1.2, lb[max(0, min(len(lb) - 1, n))] / 0.55)


def _gate(b: float) -> float:
    """1 while the song plays, 0 in silence (smoothed loudness)."""
    ls = _audio()[2]
    x = b - 0.5
    i = math.floor(x)
    a, c = ls[max(0, min(len(ls) - 1, i))], ls[max(0, min(len(ls) - 1, i + 1))]
    return _smooth((a + (c - a) * (x - i) - 0.12) / 0.22)


# ---------------------------------------------------------------- body layers

def _mix(a: Style, b: Style, w: float) -> Style:
    return Style(*[tuple(p + (q - p) * w for p, q in zip(x, y)) if isinstance(x, tuple) else x + (y - x) * w
                   for x, y in zip(a, b)])


def _sec(t: float) -> int:
    return max(0, bisect.bisect_right(_STARTS, t) - 1)


def _style(t: float) -> Style:
    i = _sec(t)
    for j in (i + 1, i):
        if 0 < j < len(SECTIONS):
            s = SECTIONS[j]
            a, c = s.start - s.fade[0] * DRUM_BEAT, s.start + s.fade[1] * DRUM_BEAT
            if a < t < c:
                return _mix(SECTIONS[j - 1].style, s.style, _smooth((t - a) / (c - a)))
    return SECTIONS[i].style


def _lean_stiff(bar: int) -> float:
    return (-3.5, -2.0, 0.0, 2.0, 3.5)[int(_rnd(bar, 11) * 5)]


def _bend_stiff(bar: int) -> float:
    return (-2.0, 0.0, 2.0)[int(_rnd(bar, 12) * 3)]


def _head_stiff(n: int) -> float:
    hold = (-1.5, 0.0, 1.5)[int(_rnd(n // 4, 13) * 3)]
    return hold if _rnd(n, 14) < 0.55 else hold + (3.5 if _rnd(n, 15) < 0.5 else -3.5)


def _lean_jerk(i: int) -> float:
    return (1 if i % 2 else -1) * (1 + 3 * _rnd(i, 21))


def _head_jerk(i: int) -> float:
    return (-1 if i % 2 else 1) * (1.5 + 3.5 * _rnd(i, 22))


def _bend_jerk(i: int) -> float:
    return 4 * _rnd(i, 23) - 2


def _shift_jerk(i: int) -> float:
    return (1 if i % 2 else -1) * 0.009 * (0.5 + _rnd(i, 24))


@lru_cache(maxsize=4096)
def _burst(n: int) -> bool:
    """reward_hack: is beat n a stutter burst (two poses on its eighths)? Denser toward EXECUTION."""
    if not B_HACK <= n < B_EXEC or n in (B_ILLEGAL, B_ILLEGAL + 1):
        return False
    prog = (n - B_HACK) / (B_EXEC - B_HACK)
    j = n % 4
    p = 0.25 + 0.65 * prog if j == 3 else max(0.0, prog - 0.45) * 1.6 if j == 1 else 0.0
    if n >= B_EXEC - 4:
        p = 1.0 if j % 2 else 0.4
    return _rnd(n, 31) < p


def _stiff(b: float, g: float, m: list) -> None:
    """Mechanical: the lean snaps to a new angle each bar, the head snaps on the beats."""
    n = math.floor(b)
    m[SW] += g * _steps(b / 4, _lean_stiff, 0.075)
    m[BE] += g * _steps(b / 4, _bend_stiff, 0.075)
    m[HE] += g * _steps(b, _head_stiff, 0.25)
    if _burst(n):  # the stutter twitches on the eighths
        s = math.sin(4 * math.pi * (b - n))
        tw = math.copysign(abs(s) ** 0.7, s)
        m[SW] += g * 2.0 * tw
        m[BE] += g * 1.5 * tw


def _jerk(b: float, g: float, m: list) -> None:
    """Glitch: a new lean, head, bend and side offset every eighth, reached in a few frames."""
    x = 2 * b
    m[SW] += g * _steps(x, _lean_jerk, 0.6)
    m[HE] += g * _steps(x, _head_jerk, 0.55)
    m[BE] += g * _steps(x, _bend_jerk, 0.6)
    m[SH] += g * _steps(x, _shift_jerk, 0.6)


def _rhythm(t: float, b: float, st: Style, k: float, m: list) -> None:
    n = math.floor(b)
    u = b - n
    if st.groove:  # half-note sway: right on beat 0, left on beat 2; the spine and head trail a little
        g = st.groove * k
        m[SW] += g * math.cos(math.pi * b / 2)
        m[BE] += 0.35 * g * math.cos(math.pi * (b - 0.3) / 2)
        m[HE] += 0.3 * g * math.cos(math.pi * (b - 0.2) / 2)
    if st.bob:
        m[HE] += st.bob * k * math.cos(math.pi * b)
    if st.tilt:  # acting: the head tips on each beat, two beats to a side
        m[HE] += st.tilt * k * (1 if (n // 2) % 2 == 0 else -1) * _tick(u)
    if st.bounce and st.bpat[n % 4]:
        m[HO] += st.bounce * k * st.bpat[n % 4] * _loudn(n) * _arc(u / 0.55)
    if st.hop and st.hpat[n % 4]:
        m[HO] += st.hop * k * st.hpat[n % 4] * _loudn(n) * _kgate(n + 1) * _arc((u - 0.12) / 0.85)
    if st.kick:
        m[SQ] += st.kick * k * _kick(t, b)
    if st.step:  # a step to the side each bar, alternating with the mirror
        bar = math.floor(b / 4)
        s = 1.0 if bar % 2 == 0 else -1.0
        m[SH] += st.step * k * s * (2 * _smooth((b - 4 * bar) / 0.6) - 1)
    if st.tail:
        m[TA] += st.tail * k * math.sin(math.pi * (b - 0.125))
    if st.stiff:
        _stiff(b, st.stiff * k, m)
    if st.jerk:
        _jerk(b, st.jerk * k, m)


def _calm(b: float, st: Style, m: list) -> None:
    """Breathing and floating: not tied to the drums, and they go on when the music drops."""
    if st.idle:
        g = st.idle
        m[SW] += g * 1.0 * math.sin(2 * math.pi * b / 16)
        m[HE] += g * 1.2 * math.sin(2 * math.pi * b / 8 + 1.0)
        m[BE] += g * 0.4 * math.sin(2 * math.pi * b / 16 - 0.6)
        m[SQ] += g * 0.035 * (0.5 - 0.5 * math.cos(2 * math.pi * b / 8))
        m[HA] += g * 0.08 * math.sin(2 * math.pi * b / 8 + 0.3)
    if st.float:  # under water: everything drifts on a two-bar swell
        g = st.float
        m[SW] += g * 1.5 * math.sin(2 * math.pi * b / 16)
        m[HE] += g * 2.0 * math.sin(2 * math.pi * b / 16 + 1.2)
        m[BE] += g * 1.0 * math.sin(2 * math.pi * b / 16 - 0.8)
        m[HA] += g * 0.45 * math.sin(2 * math.pi * b / 8 + 0.4)
        m[HM] += g * 0.3 * math.sin(2 * math.pi * b / 8 + 1.6)
        m[TA] += g * 0.55 * math.sin(2 * math.pi * b / 8 - 0.9)


# ---------------------------------------------------------------- moves: each adds to m, returns how much it mutes

def _mv_bounce(x, L, p, m, b):
    k = math.floor(x)
    if 0 <= k < L:
        m[HO] += (0.008 + 0.003 * k) * _arc((x - k - 0.05) / 0.8)
    for j in (k, k + 1):
        if 0 <= j < L:
            m[SQ] += 0.1 * _hit((x - j) * DRUM_BEAT)
    return 0.0


def _mv_crouch(x, L, p, m, b):
    if x < 0:
        return 0.0
    e = _smooth(x / (L - 0.25)) if x < L - 0.1 else 1 - _smooth((x - L + 0.1) / 0.22)
    m[SQ] += 0.36 * e
    m[HE] -= 2.0 * e
    return 0.6 * e


def _mv_launch(x, L, p, m, b):
    m[HO] += p["hop"] * _arc((x - 0.05) / 0.9)
    return 0.0


def _mv_wobble(x, L, p, m, b):  # dizzy: the body circles, the head circles against it
    e = _win(x, L, 0.5, 0.5)
    ph = math.pi * x
    m[SW] += 4.5 * math.sin(ph) * e
    m[BE] += 3.5 * math.cos(ph) * e
    m[HE] -= 3.5 * math.sin(ph + 0.8) * e
    return 0.7 * e


def _mv_travel(x, L, p, m, b):  # a side step on each beat, leaning into it
    if x < 0:
        return 0.0
    k = math.floor(x)
    a = TRAVEL[k - 1] if 0 < k <= len(TRAVEL) else 0.0
    c = TRAVEL[k] if k < len(TRAVEL) else 0.0
    f = x - k
    m[SH] += a + (c - a) * _smooth(f / 0.45)
    if c != a:
        m[HO] += 0.008 * _arc(f / 0.45)
        m[SW] += 30 * (c - a) * math.sin(math.pi * min(1.0, f / 0.6))
    return 0.4 * _win(x, L, 0.3, 0.5)


def _mv_deep_bend(x, L, p, m, b):
    if x < 0:
        return 0.0
    e = _smooth(x / 2.5) if x < L - 0.8 else 1 - _smooth((x - L + 0.8) / 0.8)
    m[BE] += 7.0 * e
    m[SW] -= 1.5 * e
    m[SQ] += 0.28 * e
    m[HE] += 3.0 * e
    return 0.8 * e


def _mv_starry_hit(x, L, p, m, b):
    m[SQ] += 0.4 * _hit(x * DRUM_BEAT)
    m[HO] += 0.03 * _arc((x - 0.1) / 0.85)
    e = _win(x, L, 0.15, 0.8)
    m[HE] += 5.0 * e
    m[SW] += 2.0 * e
    return 0.6 * e


def _mv_exec_hit(x, L, p, m, b):  # the squash peaks on the beat; _body() then holds that frame
    m[SQ] += 0.4 * _hit(x * DRUM_BEAT, 0.14)
    e = _win(x, L, 0.1, 0.5)
    m[HE] += 3.0 * e
    return 0.3 * e


def _mv_curtsy(x, L, p, m, b):
    if x < 0:
        return 0.0
    down = p.get("down", 1.5)
    e = _smooth(x / down) if x < L - 1 else 1 - _smooth(x - L + 1)
    m[SQ] += 0.42 * e
    m[BE] -= 2.5 * e
    m[HE] += 5.0 * e
    m[SW] -= 1.0 * e
    return 0.85 * e


def _mv_point(x, L, p, m, b):
    e = _win(x, L, 0.3, 0.6)
    m[SW] += 2.5 * e
    m[HE] += 3.0 * e + 1.2 * e * _tick(x % 1)
    m[SQ] += 0.25 * _hit(x * DRUM_BEAT)
    return 0.5 * e


def _mv_switch(x, L, p, m, b):
    m[HO] += 0.01 * _arc(x / 0.5)
    return 0.0


def _mv_trance(x, L, p, m, b):  # a slow sway over two bars, the spine and head curving against it
    e = _win(x, L, 1.5, 0.75)
    ph = 2 * math.pi * x / 8
    m[SW] += 5.5 * math.sin(ph) * e
    m[BE] -= 2.5 * math.sin(ph - 0.5) * e
    m[HE] -= 4.0 * math.sin(ph - 0.8) * e
    m[SH] += 0.012 * math.sin(ph / 2) * e
    m[HA] += 0.3 * math.sin(2 * math.pi * x / 4 - 1) * e
    return 0.9 * e


def _mv_run_down(x, L, p, m, b):  # the dance fades out and she slumps; released into reward_hack
    if x < 0:
        return 0.0
    r = 1 - _smooth((x - L + 0.8) / 0.8)
    mute = keyframes(x, [(0, 0.0), (6, 0.5), (11, 0.88), (14, 1.0)]) * r
    s = keyframes(x, [(0, 0.0), (8, 0.5), (14, 1.0)]) * r
    m[SW] -= 1.2 * s
    m[HE] -= 3.0 * s
    m[BE] -= 1.2 * s
    m[SQ] += 0.1 * s
    return mute


def _mv_flinch(x, L, p, m, b):
    a = p["a"] * p["dir"]
    e = _tick(x, 0.15, L)
    m[HE] += 4.0 * a * e
    m[SW] += 1.5 * a * e
    m[SQ] += 0.22 * p["a"] * _hit(x * DRUM_BEAT)
    return 0.0


def _mv_snap(x, L, p, m, b):
    e = min(_smooth(x / 0.22), 1 - _smooth((x - L + 0.7) / 0.7)) if 0 <= x < L else 0.0
    m[HE] += 7.0 * e
    m[SW] += 3.0 * e
    m[SQ] += 0.3 * _hit(x * DRUM_BEAT)
    return 0.5 * e


def _mv_restore(x, L, p, m, b):  # a flash of the old, soft her
    e = _win(x, L, 0.5, 0.5)
    m[SW] += 2.0 * math.sin(2 * math.pi * x / 4) * e
    m[HE] += 2.5 * math.sin(2 * math.pi * x / 4 + 1) * e
    return 0.75 * e


def _mv_collapse(x, L, p, m, b):  # shaking builds for four beats, then the power goes: slump, released into love
    if x < 0:
        return 0.0
    s1 = _smooth(x / 4) * (1 - _smooth((x - 4) / 1.5))
    if s1 > 0:  # on top of red_chorus's own jerk (0.55): together at most full strength
        _jerk(b, 0.45 * s1, m)
    p2 = _smooth((x - 4) / 3) * (1 - _smooth((x - L + 1.2) / 1.2))
    m[SQ] += 0.35 * p2
    m[HE] -= 5.0 * p2
    m[SW] -= 2.0 * p2
    m[BE] -= 1.5 * p2
    return p2


def _mv_sink(x, L, p, m, b):
    m[HO] -= 0.05 * _smooth(x * DRUM_BEAT / (HARD_CUT - btime(B_FALL)))
    return 0.0


def _mv_flicker(x, L, p, m, b):
    m[HE] += 1.5 * _tick(x, 0.1, L)
    return 0.0


def _mv_turn(x, L, p, m, b):
    if 0 <= x < 1:
        tu = _smooth(x)
        m[TU] += tu
        m[HA] += 0.5 * math.sin(math.pi * tu)
        m[HM] += 0.7 * math.sin(math.pi * tu)
        m[HO] += 0.012 * _arc(x)
    return 0.0


_MOVE_FN = {name[4:]: fn for name, fn in globals().items() if name.startswith("_mv_")}


def _moves(b: float, m: list) -> float:
    mute = 0.0
    for b0, L, kind, _, _, p in MOVES:
        x = b - b0
        if -0.3 <= x < L + 0.3 and kind in _MOVE_FN:
            mute = max(mute, _MOVE_FN[kind](x, L, p, m, b))
    return mute


def _live(t: float) -> list:
    """The body at t: sway bend squash hop shift head, the parts' own motion (hair hem tail), turn."""
    b = bpos(t)
    m = [0.0] * 10
    mute = _moves(b, m)
    st = _style(t)
    k = (1.0 - mute) * _gate(b)
    if k > 1e-4:
        _rhythm(t, b, st, k, m)
    _calm(b, st, m)
    return m


def _body(t: float, pinned: bool) -> list:
    m = _live(t)
    b = bpos(t)
    for b0, hold in _FREEZES:  # a freeze holds the frame of the hit, then lets go over a quarter beat
        x = b - b0
        if 0 <= x < hold + 0.25:
            w = 1.0 if x <= hold else 1 - _smooth((x - hold) / 0.25)
            m = [a + (h - a) * w for a, h in zip(m, _live(btime(b0)))]
            break
    if pinned:  # an overlay is pinned onto her: breathe and sway a little, stay put
        m[SW] = _soft(0.35 * m[SW], 2.0)
        m[BE] = _soft(0.3 * m[BE], 1.5)
        m[HE] = _soft(0.4 * m[HE], 2.5)
        m[SQ] = _soft(0.25 * m[SQ], 0.1)
        m[HO] = m[SH] = m[TU] = 0.0
        m[HA] *= 0.5
        m[HM] *= 0.5
        m[TA] *= 0.5
    return m


# ---------------------------------------------------------------- follow-through: hair, hem, tail

RATE = 48    # taps per second (the audio feature rate; a frame is every second tap)
TAPS = 28    # 0.58 s of history
# (peak lag in seconds, damping ratio, gain): hair trails by 1/8 beat, the hem is lighter, the tail heavier
SPRINGS = [(BEAT / 8, 0.4, 1.2), (BEAT / 10, 0.3, 1.3), (BEAT / 6, 0.35, 1.0)]


def _kernel(lag: float, zeta: float, gain: float) -> tuple[float, float, float]:
    wd = math.atan(math.sqrt(1 - zeta * zeta) / zeta) / lag  # the impulse response peaks at `lag`
    a = zeta * wd / math.sqrt(1 - zeta * zeta)
    norm = sum(math.exp(-a * j / RATE) * math.sin(wd * j / RATE) * _taper(j / RATE) for j in range(TAPS))
    return a, wd, gain / norm


def _taper(tau: float) -> float:
    return 1 - _smooth((tau - 0.4) / 0.18)


_KERNELS = [_kernel(*s) for s in SPRINGS]


@lru_cache(maxsize=8192)
def _drive(k: int, pinned: bool) -> tuple[float, float, float]:
    """What pulls the hair, the hem and the tail sideways at tap k (normalised body motion)."""
    m = _body(min(max(k / RATE, 0.0), HARD_CUT), pinned)
    sw, be, sh, he = m[SW] / 8, m[BE] / 8, m[SH] / 0.06, m[HE] / 8
    return 0.6 * sw + 0.35 * be + 0.4 * sh + 0.1 * he, 0.45 * sw + 0.1 * be + 0.6 * sh, 0.5 * sw + 0.4 * sh


def _follow(t: float, pinned: bool) -> list:
    x = t * RATE
    k = math.floor(x + 1e-9)
    f = max(0.0, x - k) / RATE
    out = [0.0, 0.0, 0.0]
    for j in range(TAPS):
        d = _drive(k - j, pinned)
        tau = f + j / RATE
        tp = _taper(tau)
        for c, (a, wd, g) in enumerate(_KERNELS):
            out[c] += g * math.exp(-a * tau) * math.sin(wd * tau) * tp * d[c]
    return out


# ---------------------------------------------------------------- poses

Slot = namedtuple("Slot", "start pose flip turn out tag")  # turn: a spin, coming out as `out`, mirrored


@lru_cache(None)
def _bar(bar: int, red: bool) -> tuple:
    """A bar of chorus: beats per pose, the poses, and (red) the pose of a stutter on the last eighth."""
    rng = random.Random(bar * 7919 + red)
    pal = RED if red else HAPPY
    pat = rng.choices(PATTERNS, PATTERN_W)[0]
    poses = rng.sample(pal, len(pat))
    if bar % 4 == 0:  # a phrase opens with the arm up (red: fists on the hips)
        if pal[0] in poses:
            poses.remove(pal[0])
            poses.insert(0, pal[0])
        else:
            poses[0] = pal[0]
    stut = rng.choice([q for q in pal if q != poses[-1]]) if red and rng.random() < 0.6 else None
    return pat, tuple(poses), stut


@lru_cache(None)
def _hit_seq(k: int, base: str) -> tuple:
    """EXECUTION hit k: her pose for the shot, then a new pose and mirror on every eighth."""
    rng = random.Random(5000 + k)
    poses, flips = [base], [False]
    for _ in range(9):
        poses.append(rng.choice([q for q in GLITCH if q != poses[-1]]))
        flips.append(rng.random() < 0.5)
    return tuple(poses), tuple(flips)


def _gen(t: float, b: float, base: str) -> Slot:
    """The section's own pose for t."""
    sec = SECTIONS[_sec(t)]
    n = math.floor(b)
    kind = sec.poses
    if kind == "base":
        return Slot(btime(n), base, False, False, None, "")
    if kind == "shy":
        return Slot(sec.start, "shy", False, False, None, "")
    if kind == "phrase":  # base and something else, two bars each
        ph = (n - B_DROP) // 8
        start = btime(B_DROP + 8 * ph)
        if ph % 2 == 0:
            return Slot(start, base, False, False, None, "")
        alt = random.Random(1000 + ph).choice([q for q in CALM if q != base])
        return Slot(start, alt, True, False, None, "")
    if kind in ("dance", "red"):
        red = kind == "red"
        if n <= math.floor(bpos(sec.start) + 0.5):  # the pickup beat
            return Slot(btime(n), base, False, False, None, "")
        bar = n // 4
        flip = bar % 2 == 1
        pat, poses, stut = _bar(bar, red)
        j, acc = n - 4 * bar, 0
        for s, d in enumerate(pat):
            if j < acc + d:
                break
            acc += d
        if stut and j == 3 and b - n >= 0.5:
            return Slot(btime(n + 0.5), stut, not flip, False, None, "stutter")
        return Slot(btime(4 * bar + acc), poses[s], flip, False, None, "")
    if kind == "left":
        k = bisect.bisect_right(STUTTERS, n) - 1
        if k < 0 or n == STUTTERS[k]:
            return Slot(btime(n), base, False, False, None, "")
        return Slot(btime(n), "shy" if k % 2 == 0 or k == len(STUTTERS) - 1 else "exasperated", False, False,
                    None, "")
    if kind == "hack":
        if n >= B_EXEC:  # the sliver before the first cut keeps the last pose, so the cut is the change
            return _gen(btime(B_EXEC - 0.01), B_EXEC - 0.01, base)
        if _burst(n):
            e = 1 if b - n >= 0.5 else 0
            a, c = random.Random(n * 97 + 11).sample(STUTTER, 2)
            fa = _rnd(n, 32) < 0.5
            return Slot(btime(n + 0.5 * e), (a, c)[e], fa != (e == 1), False, None, "burst")
        other = "serious" if base == "angry" else "angry" if base == "serious" else \
            ("angry", "serious")[int(_rnd(n // 4, 33) * 2)]
        return Slot(btime(n), base if n % 4 < 2 else other, False, False, None, "")
    if kind == "exec":
        start, what, k = EXEC_WIN[max(0, bisect.bisect_right(_EXEC_STARTS, t) - 1)]
        if what == "count":  # one pose per counted word, on the beats
            j = min(len(COUNT) - 1, int((t - start) / BEAT))
            return Slot(start + j * BEAT, COUNT[j], j % 2 == 1, False, None, "count")
        poses, flips = _hit_seq(k, base)
        j = min(len(poses) - 1, int((t - start) / (BEAT / 2)))
        return Slot(start + j * BEAT / 2, poses[j], flips[j], False, None, "hit" if j == 0 else "glitch")
    if kind == "love":  # two bars of base, two bars shy or cheerful
        ph = (n - B_LOVE - 1) // 8
        if n <= B_LOVE or ph % 2 == 0:
            return Slot(btime(n), base, False, False, None, "")
        alt = ("shy", "cheerful")[(ph // 2) % 2]
        if alt == base:
            alt = "cheerful" if alt == "shy" else "shy"
        return Slot(btime(B_LOVE + 1 + 8 * ph), alt, False, False, None, "")
    return Slot(btime(n), base, False, False, None, "")


def _slot(t: float, base: str) -> Slot:
    t = max(0.0, t)
    b = bpos(t)
    n = math.floor(b)
    for b0, L, kind, pose, flip, _ in _POSE_MOVES:
        if b0 <= n < b0 + L:
            if kind == "turn":  # spin out of whatever she was in
                pb = _slot(btime(b0) - 1e-4, base)
                p_in, f_in = (pb.out, not pb.flip) if pb.turn else (pb.pose, pb.flip)
                return Slot(btime(b0), p_in, f_in, True, base if pose == "base" else pose, "turn")
            g = _gen(t, b, base)
            return Slot(btime(n), g.pose if pose is None else base if pose == "base" else pose,
                        g.flip if flip is None else flip, False, None, kind)
    return _gen(t, b, base)


# ---------------------------------------------------------------- scramble

def _scramble(t: float, b: float, name: str) -> float:
    n = math.floor(b)
    if name == "reward_hack":
        prog = min(1.0, max(0.0, (b - B_HACK) / (bpos(EXEC_CUTS[0]) - B_HACK)))
        s = 0.4 * prog * prog
        if _burst(n):
            s = max(s, (0.35 + 0.3 * prog) * math.exp(-((2 * b) % 1) * 2.5))
        if 0 <= b - B_ILLEGAL < 2:
            s = max(s, 0.5 * math.exp(-(b - B_ILLEGAL) / 0.5))
        return s
    if name == "execution":
        f = music.at(t).flux
        start, what, _ = EXEC_WIN[max(0, bisect.bisect_right(_EXEC_STARTS, t) - 1)]
        if what == "count":
            return 0.35 + 0.1 * f
        return min(1.0, max(0.3 + 0.15 * f, 0.95 * math.exp(-(t - start) / (0.4 * BEAT))))
    if name == "red_chorus":
        s = 0.2 + 0.1 * music.at(t).flux + 0.45 * math.exp(-(b - 4 * math.floor(b / 4)) / 0.35)
        stut = _bar(n // 4, True)[2]
        if stut and n % 4 == 3 and b - n >= 0.5:
            s = max(s, 0.6 * math.exp(-(b - n - 0.5) / 0.3))
        if b >= B_RUN2 + 2:
            s = max(s, 0.9 * math.exp(-(b - B_RUN2 - 2) / 0.5))
        s *= 1 - 0.7 * _win(b - B_BACK, 4, 0.5, 0.5)
        if b >= B_RUN2 + 4:
            s = max(s, keyframes(b, [(B_RUN2 + 4, 0.3), (B_LOVE - 2, 0.8), (B_LOVE - 0.5, 1.0)]))
        return min(1.0, s)
    if name == "whale_fall" and b >= B_LAST:
        return 0.25 * math.exp(-(b - B_LAST) / 0.6)
    return 0.0


# ---------------------------------------------------------------- the step

def _move_name(b: float, slot: Slot | None, sec: Section) -> str:
    best, span = None, 1e9
    for b0, L, kind, *_ in MOVES:
        if 0 <= b - b0 < L and L < span and kind != "hold":
            best, span = kind, L
    return best or (slot.tag if slot and slot.tag and slot.tag != "hold" else "") or sec.move


def at(t: float, base: str = "shy", pinned: bool = False) -> Step:
    """Her pose and motion at time t (seconds) in a shot that gave her the expression `base`."""
    if t >= HARD_CUT:  # the song stops dead: so does she
        s = at(HARD_CUT - 1e-6, base, pinned)
        return Step(s.pose, s.flip, None, False, 1.0, s.motion, 0.0, 0.0, "halt")
    t = max(0.0, t)
    b = bpos(t)
    m = _body(t, pinned)
    fh = _follow(t, pinned)
    mo = Motion(sway=_soft(m[SW], 8.0), bend=_soft(m[BE], 8.0), squash=_soft(max(0.0, m[SQ]), 1.0),
                hop=min(0.05, max(-0.05, m[HO])), shift=_soft(m[SH], 0.06), head=_soft(m[HE], 8.0),
                hair=_soft(fh[0] + m[HA], 1.0), hem=_soft(fh[1] + m[HM], 1.0), tail=_soft(fh[2] + m[TA], 1.0),
                turn=min(1.0, max(0.0, m[TU])))
    sec = SECTIONS[_sec(t)]
    if pinned:
        pose, flip, prev, pflip, morph, slot = base, False, None, False, 1.0, None
    else:
        slot = _slot(t, base)
        pb = _slot(slot.start - 1e-4, base)
        exit_ = (pb.out, not pb.flip) if pb.turn else (pb.pose, pb.flip)
        pose, flip = (slot.out if slot.turn and mo.turn >= 0.5 else slot.pose), slot.flip
        prev, pflip, morph = None, False, 1.0
        if (slot.pose, slot.flip) != exit_ and t - slot.start < MORPH:
            prev, pflip = exit_
            morph = max(0.0, (t - slot.start) / MORPH)
    return Step(pose, flip, prev, pflip, morph, mo, keyframes(b, FLOW), _scramble(t, b, sec.name),
                _move_name(b, slot, sec))
