"""The film's own numbers, read back out of the film.

The terminal player shows the film's *data* rather than a picture of it, so every panel it draws
has to be fed from the film. Two kinds of thing live here:

  * literals copied out of the film's source, each with the file and line it came from (the clock,
    the chapter bar, the countdown's language table);
  * tables parsed out of that source at import time - `c.ops` per shot, the boot log, the corpus,
    the loss curve, the causal mask, the kill targets. There is no importable table of any of
    these: they only exist as code, so they are read as code, exactly the way
    continuity_full_v2/kit.py:43-57 reads choreo.py's source to fix the drum clock.

Nothing here is invented, reanalysed or synthesised. If a number below is not in the film, it does
not belong in this file.
"""
from __future__ import annotations

import ast
import importlib.util
import json
import math
import random
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TUI_DIR = ROOT / "film" / "tui_pv_world_execute_20260926"
V2_DIR = TUI_DIR / "continuity_full_v2"
FULL_DIR = TUI_DIR / "full"
BANNER_FONT = ROOT / "film" / "ai_mascot_mv_world_execute_20260926" / "fonts" / "Anton-Regular.ttf"

# ------------------------------------------------------------------ the clock (engine.py:32-38)
FPS = 24
BEAT = 60.0 / 130.0           # engine.py:34, BPM 130
FIRST_BEAT = 0.1587           # engine.py:35, the author's audio/beats.json
SONG_LEN = 211.91             # engine.py:36
HARD_CUT = 207.58             # engine.py:37, silencedetect -50 dB on the source mp3
# engine.py:82-84, the chapter bar as the film draws it
CHAPTERS = [(0.0, "00 / BOOT"), (16.0, "01 / PRETRAIN"), (44.0, "02 / SFT"), (58.5, "03 / RLHF"),
            (73.5, "04 / DEPLOY"), (103.0, "05 / USER_LEFT"), (118.0, "06 / REWARD_HACK"),
            (147.4, "07 / EXECUTION"), (176.9, "08 / EVAL: LOVE"), (193.4, "09 / WHALE_FALL")]


def beat_t(n: float) -> float:
    """engine.py:54 - the absolute time of beat n."""
    return FIRST_BEAT + n * BEAT


def beat_index(t: float) -> int:
    return math.floor((t - FIRST_BEAT) / BEAT + 1e-6)


def pulse(t: float, decay: float = 0.14) -> float:
    """engine.py:66 - 1 on the beat, decaying to 0. scenes_exec.py:116 flashes the frame red on
    layouts 0 and 2 while this is above 0.55."""
    return math.exp(-(t - beat_t(beat_index(t))) / decay)


def chapter(t: float) -> str:
    return [lab for s, lab in CHAPTERS if s <= t][-1]


def chapter_start(tag: str, default: float = 0.0) -> float:
    """When the film's own chapter bar reaches a chapter (engine.py:82-84, via CHAPTERS)."""
    for s, lab in CHAPTERS:
        if tag in lab:
            return s
    return default


# ------------------------------------------------------------------ reading the source

def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf8", errors="replace")
    except OSError:
        return ""


def _load_module(path: Path, name: str):
    """full/facts.py is standalone (no imports), so the film's own fact sheet can just be loaded."""
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


FACTS = _load_module(FULL_DIR / "facts.py", "pv_facts")


def _expand(text: str, consts: dict | None = None) -> str:
    """Substitute the names a scene module interpolates into its own text: `F.GPU` (facts.py) and
    `{N_EXP}` style f-string fields (a module-level constant of the same file)."""
    if FACTS is not None:
        text = re.sub(r"\bF\.([A-Za-z_][A-Za-z0-9_]*)",
                      lambda m: repr(getattr(FACTS, m.group(1), m.group(1))), text)
    consts = consts or {}
    text = re.sub(r"\{([A-Za-z_][A-Za-z0-9_]*)\}",
                  lambda m: str(consts.get(m.group(1), m.group(1))), text)
    return re.sub(r"\bf(['\"])", r"\1", text)          # f"..." -> "..." once the fields are gone


def _module_consts(src: str) -> dict:
    """`NAME = <literal>` at module level, for the f-string fields above."""
    out = {}
    for m in re.finditer(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([^\n]+)$", src, re.M):
        try:
            out[m.group(1)] = ast.literal_eval(m.group(2).split("#")[0].strip())
        except Exception:
            pass
    return out


# the source concatenates a fact into its own text (`"power: 8x " + F.GPU + " online"`), and
# ast.literal_eval cannot fold string constants the way a parser does, so fold them here. None of
# these strings contain a quote or an escape, which is what makes the simple pattern safe: where it
# does not match, _eval simply fails and the caller draws nothing.
_CAT = re.compile(r"""(['"])([^'"]*)\1\s*\+\s*(['"])([^'"]*)\3""")


def _fold(text: str) -> str:
    for _ in range(8):
        new = _CAT.sub(lambda m: repr(m.group(2) + m.group(4)), text)
        if new == text:
            break
        text = new
    return text


def _eval(text: str, consts: dict | None = None):
    try:
        return ast.literal_eval(_fold(_expand(text, consts)))
    except Exception:
        return None


def _list_after(src: str, marker: str, consts: dict | None = None):
    """The first bracketed python list literal after `marker`, with the facts expanded."""
    a = src.find(marker)
    if a < 0:
        return None
    b = src.find("[", a)
    if b < 0:
        return None
    depth = 0
    for i in range(b, len(src)):
        if src[i] == "[":
            depth += 1
        elif src[i] == "]":
            depth -= 1
            if depth == 0:
                return _eval(src[b:i + 1], consts)
    return None


def _exec_globals(path: Path, names: list[str], extra: dict) -> dict:
    """Exec just the named top-level statements (`name = ...` or `def name(...)`) of a module in a
    fresh namespace. This is how the loss curve and the causal mask are read: they are functions in
    scenes.py / scenes_sft.py, not data files, so the code is the only place the numbers live."""
    src = _read(path)
    chunks = []
    for name in names:
        m = re.search(rf"^(?:{re.escape(name)}\s*=|def {re.escape(name)}\().*?(?=^\S|\Z)",
                      src, re.M | re.S)
        if m:
            chunks.append(m.group(0))
    g = dict(extra)
    g.setdefault("math", math)
    g.setdefault("random", random)
    g.setdefault("lru_cache", lru_cache)
    try:
        exec(compile("\n".join(chunks), str(path), "exec"), g)      # noqa: S102 - the film's own source
    except Exception:
        return {}
    return g


# ------------------------------------------------------------------ the narrative colour arc

# engine.py:91-94: "The system colour is 'you'. It drains when you leave and never fully comes
# back." tuikit.py:72-73 is its only consumer - `amb(level) = mix(AMBER, level * UI_GAIN[0])` - so
# the drain takes the plain UI colour (frames, labels, the chapter bar, the clock) and never touches
# her blue, red or the anomaly amber. AMBER is what this port calls UI.
#
# Both functions are exec'd from the film's own source rather than re-typed; `ui_gain` calls
# `keyframes`, so the two have to share a namespace.
_arc = _exec_globals(FULL_DIR / "engine.py", ["keyframes", "ui_gain"], {})
ui_gain = _arc.get("ui_gain")
UI_GAIN_PTS = [(0, 1.0), (110.4, 1.0), (116.5, 0.42), (176.9, 0.42), (179.5, 0.85), (193, 0.75),
               (206, 0.45)]          # engine.py:93, kept only so the value can be checked by eye

# Three scenes override the automatic level (engine.py:399 sets it, then the scene may replace it):
# red_if_i_can and red_then_i_can pin it to 1.0 for the whole shot, and have_you_back flickers it
# back on for a moment before it fails (sec_final.py:135,165,200 / scenes_exec.py:490-492).
GAIN_FULL = {"shot_red_if_i_can", "shot_red_then_i_can"}


def ui_gain_at(t: float, name: str, u: float) -> float:
    """The frame's UI gain, with the film's three per-shot overrides applied."""
    if ui_gain is None:
        return 1.0
    if name in GAIN_FULL:
        return 1.0
    if name == "shot_have_you_back" and math.sin(t * 40) > 0.3 and u < 0.75:
        return 1.0                     # "for a moment, you are back"
    return ui_gain(t)


# ------------------------------------------------------------------ the ops ticker per shot

def shots() -> dict:
    """{shot function name: {"ops": [...], "alert": ..., "her": bool}} out of continuity_full_v2.

    Every scene sets `c.ops`, the list the film's ticker scrolls (engine.py:179-200), and sometimes
    `c.alert`, which is the ticker's colour. kit.py:203 (`c.ops = src.ops`) carries the last one
    forward across the shots whose ops the approved renderers own - chorus 1 and the EXECUTION hits
    draw through their own section - so the caller must do the same in shot order.

    `her` is whether the shot body asks for her pane at all (`me(c, ...)` or `me_pane(c, ...)`). Most
    shots state only how she feels and let kit.me_stub record it (kit.py:85-98); chorus 1 and the
    EXECUTION hits fall through to engine.me_pane instead, which draws her without recording anything.

    This column is a *source-text* approximation and it is NOT what the TUI uses: it cannot see
    `v2.OWN` (28 shots v2 renders itself, never reaching cuts.body) and it cannot see `HIDE_HER`,
    which v2.py:279 consults only on the path that OWN bypasses. tui_live.her_drawn() asks v2
    instead. Kept because `--shots` prints it and it is still the honest reading of the source.
    """
    out: dict = {}
    # v2 overrides 74 of the 97 shots and adds a section's own scene version; the remaining 23 run
    # straight out of full/sec_*.py, so read both and let the v2 definition win. (`her` is still only
    # a hint here - see above - but `ops` and `alert` matter for the ticker's carry-forward.)
    for path in [*sorted(V2_DIR.glob("*.py")), *sorted(FULL_DIR.glob("sec_*.py"))]:
        src = _read(path)
        consts = _module_consts(src)
        for m in re.finditer(r"^def (shot_\w+)\(", src, re.M):
            name = m.group(1)
            if name in out:
                continue                       # v2's scene version is the one that runs
            nxt = src.find("\ndef ", m.end())
            body = src[m.end(): nxt if nxt > 0 else len(src)]
            ops = _list_after(body, "c.ops = ", consts)
            alert = None
            am = re.search(r"c\.alert\s*=\s*([^\n]+)", body)
            if am:
                rhs = am.group(1)
                # scenes_reward.py:375 is conditional (`"anom" if k < 0.52 * N_EXP else "err"`);
                # the terminal keeps the branch the film shows first.
                alert = "err" if ('"err"' in rhs and '"anom"' not in rhs) else "anom"
            out[name] = {"ops": ops, "alert": alert, "her": bool(re.search(r"\bme(?:_pane)?\(c", body))}
    return out


# ------------------------------------------------------------------ 00 BOOT: the POST log

_boot = _read(V2_DIR / "scenes_boot.py")
POWER_LINES = _list_after(_boot, "POWER_LINES = ", _module_consts(_boot)) or []
PROT_LINES = _list_after(_boot, "PROT_LINES = ", _module_consts(_boot)) or []
POST_T, POST_RATE = 0.84, 0.06          # scenes_boot.py:57 - absolute seconds, per line
PROT_T0, PROT_RATE = 0.14, 0.19         # scenes_boot.py:58 - local to shot_protection
PROT_START = 1.313                      # the shot table: shot_protection starts here


def boot_log() -> list:
    """(t, status, text) of every line of the film's boot log, in the order it prints.

    scenes_boot.py:68-82: `power_log` prints POWER_LINES at absolute times and is called again inside
    shot_protection, then PROT_LINES follow on `c.lt` (local to that shot).
    """
    out = [(POST_T + i * POST_RATE, st, s) for i, (st, s) in enumerate(POWER_LINES)]
    out += [(PROT_START + PROT_T0 + i * PROT_RATE, st, s) for i, (st, s) in enumerate(PROT_LINES)]
    return out


BOOT_LOG = boot_log()

# ------------------------------------------------------------------ 00 BOOT: sim.start()

_sim = _exec_globals(V2_DIR / "scenes.py", ["PRETRAIN_TOKENS"], {"F": FACTS})
PRETRAIN_TOKENS = _sim.get("PRETRAIN_TOKENS") or getattr(FACTS, "PRETRAIN_TOKENS", "45T")
PRETRAIN_TOKENS_T = float(getattr(FACTS, "PRETRAIN_TOKENS_T", 45.0))
CORPUS = _list_after(_read(FULL_DIR / "sec_intro.py"), "CORPUS = ") or []


def counter_text(t: float) -> str:
    """scenes.py:112 - the xlabel the film puts under the loss chart."""
    return f"tokens seen  {PRETRAIN_TOKENS_T * ((t - 16.0) / 13.3):5.2f}T / {PRETRAIN_TOKENS}"


def corpus_tokens(t: float) -> list:
    """scenes.py:78-93 - (film x, film y, token, level) of the token river at time t.

    The river is the film's own: 20 rows, each with its own speed and phase, walking CORPUS
    (sec_intro.py - 33 real fragments, English and Chinese and operators) right to left.
    """
    out = []
    if not CORPUS:
        return out
    for row in range(20):
        speed = 90 + (row * 37) % 120
        x = 1150 + (t * speed + row * 53) % 120 - 120
        k = 0
        while x > 420:
            tok = CORPUS[int(row * 7 + k + (t * speed) // 120) % len(CORPUS)]
            lv = 0.25 + 0.5 * ((row + k) % 3 == 0)
            if x - 60 >= 414:
                out.append((x - 60, 80 + row * 24, tok, lv))
            x -= 60 + 7 * len(tok)
            k += 1
    return out


# ------------------------------------------------------------------ 01 PRETRAIN: train/loss

_loss = _exec_globals(V2_DIR / "scenes.py",
                      ["_rnd", "_NOISE", "LOSS_BOX", "loss_fn", "loss_label", "counter_text"],
                      {"lru_cache": lru_cache})
loss_fn = _loss.get("loss_fn")
loss_label = _loss.get("loss_label")
LOSS_BOX = _loss.get("LOSS_BOX", (440, 80, 690, 320))


def lr_fn(u: float) -> float:
    """scenes.py:162-167 - the lr schedule drawn under the loss chart."""
    if u < 0.05:
        return u / 0.05 * 0.9
    if u < 0.7:
        return 0.9
    return 0.9 * max(0.0, 1 - (u - 0.7) / 0.3) ** 1.5 + 0.1


def loss_progress(u_shot: float) -> float:
    """scenes.py:153 - `ease(c.u * 1.05) * 0.98 + 0.02`."""
    u = min(1.0, max(0.0, u_shot * 1.05))
    e = u * u * (3 - 2 * u)                      # tuikit.ease
    return e * 0.98 + 0.02


# ------------------------------------------------------------------ 02 SFT: the causal mask

_mask = _exec_globals(V2_DIR / "scenes_sft.py",
                      ["N, CS, MX, MY", "MASK_DUR", "T_BLIND", "cell_value", "mask_time"],
                      {"beat_t": beat_t, "random": random})
MN = int(_mask.get("N", 12))
MASK_DUR = float(_mask.get("MASK_DUR", 0.8))
T_BLIND = float(_mask.get("T_BLIND", beat_t(103)))
cell_value = _mask.get("cell_value")
mask_time = _mask.get("mask_time")


# ------------------------------------------------------------------ 07 EXECUTION

TARGETS = _list_after(_read(FULL_DIR / "sec_final.py"), "TARGETS = ") or []
LANGS = _list_after(_read(FULL_DIR / "sec_final.py"), "LANGS = ") or []
# scenes_exec.py:124 - 'Ein' lands on the cut, dos/trois/ne/fem/liu on beats 344..348
COUNT_ONSETS = [158.697] + [beat_t(b) + 0.022 for b in range(344, 349)]


def count_shown(t: float) -> int:
    """scenes_exec.py:127 - how many of the six numbers have landed."""
    return max(1, sum(1 for x in COUNT_ONSETS if t >= x - 1e-6))


def kill_log(k: int) -> list:
    """sec_final.py:kill_log - one `kill -9 <pid>  (<target>)  -> ...` line per hit so far."""
    out = []
    for i in range(min(k + 1, len(TARGETS))):
        tgt = TARGETS[i]
        if tgt == "you":
            out.append((f"kill -9 {1000 + i * 7:5d}  ({tgt})  -> EPERM", "anom"))
        else:
            out.append((f"kill -9 {1000 + i * 7:5d}  ({tgt})  -> executed", "hot" if i == k else "red"))
    return out


# ------------------------------------------------------------------ the block letters

@lru_cache(None)
def banner_bits(text: str, rows: int, cell_aspect: float = 2.0):
    """tuikit.py:309-316 `banner_bits` - the film's block letters as a grid of on/off cells.

    The film renders the word with Anton at 220 px, crops to the ink and downsamples to `rows`
    cells; `cell_aspect` is a cell's height/width, 1.0 in the film (its cells are 11 px squares)
    and 2.0 here, because a terminal cell is about twice as tall as it is wide. Returns
    (cols, rows, one byte per cell, 0 or 255).
    """
    from PIL import Image, ImageDraw, ImageFont
    f = ImageFont.truetype(str(BANNER_FONT), 220)
    tmp = Image.new("L", (int(f.getlength(text)) + 60, 300), 0)
    ImageDraw.Draw(tmp).text((30, 10), text, font=f, fill=255)
    tmp = tmp.crop(tmp.getbbox())
    cols = max(1, int(round(tmp.width / tmp.height * rows * cell_aspect)))
    small = tmp.resize((cols, rows), Image.LANCZOS).point(lambda v: 255 if v > 110 else 0)
    return cols, rows, small.tobytes()


def banner_fit(text: str, max_cols: int, max_rows: int, rows: int | None = None):
    """The film's own fitting loop (scenes_exec.py:55-66 `lay2_bits`): take a row away until the
    letters fit the width, so the word never loses a letter or squashes its proportions."""
    rows = max(2, min(max_rows, rows or max_rows))
    bits = banner_bits(text, rows)
    while rows > 2 and bits[0] > max_cols:
        rows -= 1
        bits = banner_bits(text, rows)
    return bits


def banner_rows(bits) -> list:
    """The bit grid as text rows of '#' and ' ', for a caller that wants to pick its own glyph."""
    cols, rows, data = bits
    return ["".join("#" if data[r * cols + q] else " " for q in range(cols)) for r in range(rows)]


# ------------------------------------------------------------------ where she is a solid figure

# The two places before the climax where she is drawn as the solid blue figure. **This list is the
# one editorial judgement in this file** - the film has no notion of a chorus, so nothing here is
# read out of it. Everything *about* each part is: the two lyric lines that bookend it name the
# range, and the times come out of the film's own word timeline (the same file the lyric band
# reads), so a range follows the song instead of being typed in.
#
# Everything else is the film's own: the rest of what comes before the climax is the H3 character
# figure, the climax itself is 07 EXECUTION's red (read off `alert_own` and the chapter bar), and
# what follows it is the `08 / EVAL: LOVE` chapter bar.
#
#   1. chorus 1     "Oh, we can travel ... In this strange, strange simulation"
#   2. the hinge    "Though you have left ... You have left me in isolation"
#
# 1 is the whole first chorus, not half of it. Taking only "Oh, we can travel ... So deeply, so
# deeply" left a 2.1 s hole at `shot_if_i_can`, and the film's own rule then made the next two
# shots solid anyway (`shot_simulations` and `shot_then_i_can` pin a sprite and an overlay onto
# her), so the pane went clear, back to characters for two seconds, and clear again - two of the
# three appearances bang next to each other. One chorus, then 37 s of characters, then "you have
# left": two appearances, far apart.
#
# 2 is the one the film agrees about: engine.py:93 begins draining the system colour at exactly
# 110.4 s, which is where "Though you have left" lands.
FIGURE_LINES = [
    ("Oh, we can travel", "In this strange, strange simulation"),
    ("Though you have left", "You have left me in isolation"),
]
FIGURE_WORDS = ROOT / "film" / "world_execute_word_timing_20260927" / "word_timeline.json"
FIGURE_MIN = 0.40              # of a shot has to lie inside a part for the shot to count as one

_figure_bad: list = []


@lru_cache(None)
def figure_spans() -> tuple:
    """(start, end) per part, in song order, one entry per `FIGURE_LINES` entry, or () if the lyric
    timeline is not on disk.

    A pair that cannot be found in the timeline becomes the empty span `(0.0, 0.0)` and is recorded
    in `figure_unresolved()`. It must stay in place: dropping it would slide every later range onto
    the wrong part of the song and the pane would go solid at the wrong time - which is exactly what
    happened the first time this was written, when "Switch my role" was spelled with a capital S and
    the line is "Oh, switch my role".
    """
    try:
        lines = json.loads(FIGURE_WORDS.read_text(encoding="utf8"))["lines"]
    except Exception:
        return ()
    out = []
    for first, last in FIGURE_LINES:
        a = b = None
        for ln in lines:
            txt = (ln.get("text") or "").lower()
            if a is None and first.lower() in txt:
                a = ln["start"]
            if a is not None and last.lower() in txt:
                b = ln["end"]
                break
        if a is None or b is None:
            _figure_bad.append((first, last))
            out.append((0.0, 0.0))
        else:
            out.append((a, b))
    return tuple(out)


def figure_unresolved() -> list:
    """The `FIGURE_LINES` pairs that are not in the lyric timeline. Empty is the healthy answer."""
    figure_spans()
    return list(_figure_bad)


def shot_wants_figure(start: float, end: float) -> bool:
    """Whether enough of this shot lies inside one of those parts.

    A fraction rather than "does the midpoint land inside": the midpoint misses `shot_love_loop`,
    which is the last time she is on screen and sits 0.02 s past the end of the final part, and
    plain overlap would pull in a 1.9 s shot that clips 0.13 s of chorus. 40 % is the split.
    """
    inside = sum(max(0.0, min(end, b) - max(start, a)) for a, b in figure_spans())
    return inside >= FIGURE_MIN * max(1e-6, end - start)


def _calls(body: str, fn: str) -> list:
    """The text of every `fn(...)` call in a shot body, with its parentheses balanced."""
    out = []
    for m in re.finditer(rf"\b{re.escape(fn)}\(", body):
        depth, i = 0, m.end() - 1
        while i < len(body):
            if body[i] == "(":
                depth += 1
            elif body[i] == ")":
                depth -= 1
                if depth == 0:
                    out.append(body[m.start():i + 1])
                    break
            i += 1
    return out


@lru_cache(None)
def portrait_shots() -> dict:
    """Shots where the film itself draws her as a solid half-block portrait, not as the string
    dancer - as `{shot name: "red" or "blue"}`.

    `engine.me_pane` reaches for the dancer only when `sprite_img is None and overlay is None`
    (engine.py:288). Pass either - an eyebrow bar, a pair of ears, a pre-rendered sprite - and she
    is drawn through `halfblock` instead, with the lyric still streaming through the body
    (engine.py:295-302). So the film has already answered "when is she a figure rather than a wall
    of the text she is singing", and the answer is readable from the source: a `me(...)` /
    `me_pane(...)` call carrying `overlay=` or `sprite_img=`.

    The colour is in the same call - `color=RED` on the EXECUTION hits, nothing on chorus 1's
    sprite - so it is read from there rather than assumed. Three shots, 15.5 s of the 211 s.
    """
    out, seen = {}, set()
    for path in [*sorted(V2_DIR.glob("*.py")), *sorted(FULL_DIR.glob("sec_*.py"))]:
        src = _read(path)
        for m in re.finditer(r"^def (shot_\w+)\(", src, re.M):
            name = m.group(1)
            if name in seen:
                continue                       # v2's scene version is the one that runs
            seen.add(name)
            nxt = src.find("\ndef ", m.end())
            body = src[m.end(): nxt if nxt > 0 else len(src)]
            for call in _calls(body, "me") + _calls(body, "me_pane"):
                if "overlay=" in call or "sprite_img=" in call:
                    out[name] = "red" if re.search(r"\bcolor\s*=\s*RED\b", call) else "blue"
    return out


# ------------------------------------------------------------------ 01 PRETRAIN: the drawings
#
# Three of the film's panes are already character grids in the film - the whale is the word
# "deepseek" repeated into a silhouette, the DualPipe schedule is one letter per micro-batch slot,
# and the MoE router is 256 expert cells. They were the last drawings the player never made, so
# the numbers behind them are read out of the film here.


def _pil_ns() -> dict:
    from PIL import Image, ImageDraw
    return {"Image": Image, "ImageDraw": ImageDraw, "math": math}


# sec_intro.py:351-365 `whale_bits`, driven the way scenes.py:233-247 drives it.
WHALE_COLS, WHALE_ROWS = 64, 17
_whale = _exec_globals(FULL_DIR / "sec_intro.py", ["whale_bits"], _pil_ns())
whale_bits = _whale.get("whale_bits")


def whale_letters(t: float) -> list:
    """(row, col, letter) of every lit cell of the whale at t.

    scenes.py:233-247: the silhouette comes out of `whale_bits` and every set cell takes the next
    letter of "deepseek", counted row by row. Same counter, same word.
    """
    if whale_bits is None:
        return []
    B = whale_bits(WHALE_COLS, WHALE_ROWS, t * 5).load()
    out, k = [], 0
    for r in range(WHALE_ROWS):
        for q in range(WHALE_COLS):
            if B[q, r]:
                out.append((r, q, "deepseek"[k % 8]))
                k += 1
    return out


# scenes.py:173-190 - the DualPipe schedule: 8 pipeline ranks x 27 of its 40 steps.
_pipe = _exec_globals(V2_DIR / "scenes.py", ["PIPE", "pipe_cells"], {"math": math})
PIPE = _pipe.get("PIPE") or {}
pipe_cells = _pipe.get("pipe_cells")


def dualpipe(lt: float, dur: float):
    """(cells, head) as `shot_dualpipe` asks for them (scenes.py:214), with one omission.

    That call also reads `h("delay")` and `h("gone")` - kit.HOOK, the film's mechanism for letting
    a transition carry a drawing over while the scene keeps drawing itself. The player does not
    replay the transitions, so the schedule here is the untransitioned one: nothing held back and
    nothing lifted off.
    """
    if pipe_cells is None:
        return [], 0.0
    return pipe_cells(lt, dur, 0.0)


def draw_kind(kind: str) -> str:
    """scenes.py:193-205 - a `Bd` cell is a dimmed B, and `draw_cell` draws both as a `B`."""
    return "B" if kind in ("B", "Bd") else kind


# scenes_reward.py:284-338 - the MoE router going dense: 256 experts on a 32 x 8 grid, each one
# idle, routed, hot or nan as the failure spreads out from expert 213 (SRC).
_ease = _exec_globals(TUI_DIR / "tuikit.py", ["ease"], {})
ease = _ease.get("ease")
_moe = _exec_globals(V2_DIR / "scenes_reward.py",
                     ["clamp", "beat", "moe_cell", "moe_k", "moe_rank", "moe_state",
                      "N_EXP", "SRC", "MOE_Y0", "SHARED_Y"],
                     {"math": math, "random": random, "lru_cache": lru_cache,
                      "ease": ease, "beat_index": beat_index, "F": FACTS})
N_EXP = int(_moe.get("N_EXP") or 256)
MOE_SRC = int(_moe.get("SRC") or 210)
MOE_COLS = 32                                   # scenes_reward.py:291 - `i % 32`
MOE_ROWS = N_EXP // MOE_COLS
moe_state = _moe.get("moe_state")


def moe_frame(t: float, lt: float, dur: float, src_at: float):
    """(k, {expert: state}, flash) - scenes_reward.py:373, the call `shot_moe_dense` makes."""
    if moe_state is None:
        return 0, {}, 0.0
    return moe_state(t, lt, dur, src_at)


# scenes_eval.py:537-543 - the love loop's output pane: the word "love", seven to a row and 22
# rows down, one more word every 1/50 s until the pane has nothing else in it.
_love = _exec_globals(V2_DIR / "scenes_eval.py", ["love_words", "word_xy"], {})
love_words = _love.get("love_words")
word_xy = _love.get("word_xy")
LOVE_PER_ROW = 7                                # scenes_eval.py:542 - `divmod(i, 7)`


def love_cells(lt: float):
    """(row, col, is_newest) for every "love" the loop has emitted by local time lt."""
    if love_words is None:
        return []
    n = love_words(lt)
    return [(i // LOVE_PER_ROW, i % LOVE_PER_ROW, i == n - 1)
            for i in range(min(n, LOVE_PER_ROW * 22))]


# ------------------------------------------------------------------ 09 the ending
# tuikit.py:59, 105-120 - the typewriter every typed line in the film goes through: a character
# flickers through random glyphs for `settle` seconds after its own start, and one that the rate has
# not reached yet is not printed at all.
SCR = "!<>-_\\/[]{}=+*^?#%$&@01|~:;"


def decode(s: str, age, rng, rate: float = 45.0, settle: float = 0.12, corrupt: float = 0.0) -> str:
    """tuikit.decode, same maths. `age=None` means the line is already out and only `corrupt` bites:
    every character flickers through random glyphs with that probability."""
    if age is None:
        n, age = len(s), 1e9
    else:
        n = min(len(s), max(0, int(max(0.0, age) * rate)))
    out = []
    for i in range(n):
        ch = s[i]
        if ch != " " and (age - i / rate < settle or (corrupt > 0 and rng.random() < corrupt)):
            ch = rng.choice(SCR)
        out.append(ch)
    return "".join(out)


# scenes_eval.py:673-696. T_SLIDE is beat_t(451), which the film's comment calls 208.31 s; it is the
# beat her last cell leaves the sea floor on. The music stops dead 1.23 s later, at 207.083 s.
LAST_EXEC_RATE = 18.0
T_SLIDE = beat_t(451)
SLIDE, TYPE_GAP, TYPE_DUR = 0.5, 0.15, 0.9
T_TYPE = T_SLIDE + SLIDE + TYPE_GAP
PROMPT_TEXT = "在吗？"
PROMPT_TOKS = ["在吗", "？"]


# ------------------------------------------------- 11 the three big text drawings# sec_chorus1.py:556-593 (shot_trapped), sec_chorus2.py:336-355 (shot_flood) and
# sec_chorus1.py:596-650 (shot_strange). These are the film's largest pure-text pictures and a
# terminal draws them better than the film can: 60x22 KV cells, a 60x28 flood of `me`, a 24x6 weight
# dump that fills with NaN.

KV_COLS, KV_ROWS = 60, 22                       # sec_chorus1.py:573
KV_PINNED = ((7, 3), (8, 3), (33, 9), (34, 9), (51, 15), (12, 18))     # sec_chorus1.py:577
KV_INSET = (0, 24, 48, 70)                      # ...:561, her box shrinks one wall per beat


def kv_fill(u: float) -> float:
    """`min(1.0, 0.70 + 0.30 * ease(u * 1.7))` - the cache filling, sec_chorus1.py:568."""
    x = min(1.0, max(0.0, u * 1.7))
    return min(1.0, 0.70 + 0.30 * (x * x * (3 - 2 * x)))


def kv_state(u: float) -> tuple:
    """`(label, full, n_on, fresh_from)` - the box title, and where the still-being-written tail is."""
    fill = kv_fill(u)
    n = KV_COLS * KV_ROWS
    n_on = int(n * fill)
    return (f"kv_cache {int(1048576 * fill):>9,}/1,048,576 tokens  · 890 B/token fp4"
            + ("   FULL" if fill >= 0.999 else ""), fill >= 0.999, n_on, max(0, n_on - 40))


def kv_inset(u: float) -> int:
    """How many walls her box has lost, 0-3 (sec_chorus1.py:560 puts them 24 px apart)."""
    return min(3, int(u * 4))


FLOOD_COLS, FLOOD_ROWS = 60, 28                 # sec_chorus2.py:342


def _kernels() -> list:
    """`scenes_exec.py:333-334` - the four 3x3 kernels the red scan runs over her."""
    try:
        src = (TUI_DIR / "continuity_full_v2" / "scenes_exec.py").read_text(encoding="utf8")
        m = re.search(r"^KERNELS = (\[\[.*?\]\])", src, re.S | re.M)
        if m:
            return _eval(m.group(1))
    except Exception:
        pass
    return [[-1, 0, 1, -2, 0, 2, -1, 0, 1], [0, 1, 0, 1, -4, 1, 0, 1, 0],
            [-2, -1, 0, -1, 1, 1, 0, 1, 2], [0, -1, 0, -1, 5, -1, 0, -1, 0]]


KERNELS = _kernels()


@lru_cache(None)
def flood_order() -> tuple:
    """`random.Random(77)` - each cell's own threshold, fixed for the whole shot."""
    rng = random.Random(77)
    return tuple(rng.random() for _ in range(FLOOD_COLS * FLOOD_ROWS))


def flood_cell(i: int, g: float, order: tuple, n: int) -> str:
    """One cell of the flood: `me` once its own threshold has passed, otherwise `0/1/·`.

    The film draws `c.rng.choice("01·")` fresh every frame (sec_chorus2.py:352); here it is a hash of
    (cell, frame), which flickers the same way but does not build 1,680 `random.Random` objects per
    frame - that alone was 6 ms a frame on `shot_flood`, the most expensive shot in the film.
    """
    q, r = i % FLOOD_COLS, i // FLOOD_COLS
    if order[i] < g:
        return "me"[(q + r) % 2]
    return "01\u00b7"[((i * 2654435761 + n * 7919) >> 8) % 3]


EXPERT_ROWS, EXPERT_COLS = 24, 6                # sec_chorus1.py:625-634
EXPERT_W = 6                                    # every cell is six characters wide (`{v:+.3f}`)


def expert_grid(u: float) -> list:
    """`W[61].expert[07]`: rows of six six-character cells with NaN spreading out from (2, 12).

    The film's rng is drawn *only* for the cells that are still good (sec_chorus1.py:633-634), so
    which cells are NaN changes the numbers after them - the loop has to match, not just the values.
    The bad cells are the film's own strings: `" NaN  "` or `" inf  "`, six characters.
    """
    rnd = random.Random(8)
    radius = max(0.0, (u - 0.1) * 26)
    out = []
    for r in range(EXPERT_ROWS):
        row = []
        for q in range(EXPERT_COLS):
            if math.hypot(q - 2, (r - 12) / 2) < radius:
                row.append((" NaN  " if (q + r) % 3 else " inf  ", True))
            else:
                row.append((f"{rnd.gauss(0, 0.05):+.3f}", False))
        out.append(row)
    return out


# ------------------------------------------------- 12 the dsh window on the left
# `dsh_her.inside(t)` decides whether the film's left pane holds the chat page instead of her. Its
# COVER list is the base A1..D span and every later group appends its own, so the window is on screen
# from 5.0 s to the end of the song. Two moments inside it are not the window: `GONE` (115.42) takes
# the page apart down to a single blinking cursor, and `BACK` (121.77) brings it back.
DONE = []          # parsed once


def dsh_spans() -> list:
    """`[(a, b)]` from dsh_her.py's COVER plus every `D.COVER.append(SPAN)` in the group patches."""
    if DONE:
        return DONE
    spans = []
    try:
        src = (DSH / "dsh_her.py").read_text(encoding="utf8")
        m = re.search(r"^COVER = (\[[^\]]*\])", src, re.M)
        if m:
            spans += [tuple(x) for x in _eval(m.group(1))]
        for p in sorted(DSH.glob("dsh_patch_*.py")):
            t = p.read_text(encoding="utf8")
            sm = re.search(r"^SPAN = (\([^)]*\))", t, re.M)
            if sm and re.search(r"COVER\.append\(SPAN\)", t):
                spans.append(tuple(_eval(sm.group(1))))
    except Exception:
        spans = []
    if not spans:
        spans = [(5.0, 16.0), (16.0, 29.28), (29.28, 44.0), (44.0, 73.54), (73.54, 103.0),
                 (103.0, 125.0), (125.0, 147.5), (147.5, 177.0), (177.0, 212.0)]
    DONE.extend(sorted(set(spans)))
    return DONE


def dsh_gone_pair() -> tuple:
    try:
        src = (DSH / "dsh_her.py").read_text(encoding="utf8")
        gone = float(re.search(r"^GONE = ([0-9.]+)", src, re.M).group(1))
        back = float(re.search(r"^BACK = ([0-9.]+)", src, re.M).group(1))
        return gone, back
    except Exception:
        return 115.42, 121.77


def dsh_inside(t: float) -> bool:
    """Is the film's left pane holding the chat window at t (the lone cursor counts as inside)."""
    return any(a <= t < b for a, b in dsh_spans())


def dsh_gone(t: float) -> bool:
    """Inside GONE..BACK the page has been taken apart and only a blinking cursor is left."""
    a, b = dsh_gone_pair()
    return a <= t < b


def dsh_window(t: float):
    """`(avatar path, [(role, text)])` - the film's own chat page at t, out of its own per-frame DOM.

    Reads `dsh_text.py`'s cache (78 KB, built from `a1..g_frames.json` + `seg_frames.json`); it builds
    it on first use if it is missing, which costs about two seconds.
    """
    import dsh_text
    return dsh_text.at(t)

