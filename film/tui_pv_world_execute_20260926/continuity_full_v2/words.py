"""The lyric band, word by word: each word appears when it is sung.

Word onsets come from the word timeline in ../../world_execute_word_timing_20260927/word_timeline.json (vocal
stem forced-aligned per LRC line; time zero is the decoded MP3, the same clock as the film). The LRC stays the
source of the film's structure - cut times, her choreography and every lyric_start() lookup are unchanged; only
what the band shows, and when, follows the sung words.

  line_at(t)      the line on screen at t: (line, fade) or None
  typed(line, t)  how many characters of the line are out at t, and when each character came out
  install()       replaces engine.lyric_tokens and stage.lyric_now (the band and every layout that reads it)

A line comes up with its first sung word. It stays on screen until the next line starts; before an instrumental
break (a gap over 2 s) it is held one beat after its last word and fades over the next beat. A word types in from
its onset over its sung length, at most 0.25 s, so short words land whole on the beat; a melisma written with
hyphens ("lo-o-ove") types over the whole held note.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

import kit
from kit import engine, stage, tk

SOURCE = kit.PROJECT.parent / "world_execute_word_timing_20260927" / "word_timeline.json"
BREAK = 2.0          # a gap longer than this before the next line is an instrumental break
MAX_TYPE = 0.25      # a word is fully typed at most this long after its onset
MIN_TYPE = 0.06
FIXES = {"Trios": "Trois"}  # the LRC's typo, also fixed by s_exec in engine.LYRICS


@lru_cache(None)
def lines() -> list[dict]:
    """[{text, start, end, show_until, fade_until, words: [(char_start, char_end, onset, type_dur)]}]"""
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    out = []
    for ln in data["lines"]:
        text = ln["text"]
        for a, b in FIXES.items():
            text = text.replace(a, b)
        words, pos = [], 0
        for w in ln["words"]:
            shown = w["text"]
            for a, b in FIXES.items():
                shown = shown.replace(a, b)
            i = text.find(shown, pos)
            assert i >= 0, (text, shown)
            pos = i + len(shown)
            dur = max(0.0, w["end"] - w["start"])
            td = dur if "-" in shown else min(MAX_TYPE, dur)
            words.append((i, pos, w["start"], max(MIN_TYPE, td)))
        out.append(dict(text=text, start=words[0][2], end=ln["display_end"], words=words))
    for k, ln in enumerate(out):
        nxt = out[k + 1]["start"] if k + 1 < len(out) else engine.SONG_LEN
        if nxt - ln["end"] > BREAK:
            ln["show_until"] = ln["end"] + engine.BEAT
            ln["fade_until"] = ln["end"] + 2 * engine.BEAT
        else:
            ln["show_until"] = ln["fade_until"] = nxt
    return out


def line_at(t: float):
    """(line, alpha) on screen at t, or None."""
    for ln in lines():
        if ln["start"] <= t < ln["fade_until"]:
            if t < ln["show_until"]:
                return ln, 1.0
            return ln, 1.0 - (t - ln["show_until"]) / (ln["fade_until"] - ln["show_until"])
    return None


def typed(ln: dict, t: float) -> tuple[int, list[float]]:
    """(characters out at t, the time each character of the line came out; inf for those still to come)."""
    text = ln["text"]
    when = [float("inf")] * len(text)
    for k, (i0, i1, onset, td) in enumerate(ln["words"]):
        n = i1 - i0
        for j in range(n):
            when[i0 + j] = onset + td * j / n
        # the space and punctuation after a word come out with its last letter
        nxt = ln["words"][k + 1][0] if k + 1 < len(ln["words"]) else len(text)
        for j in range(i1, nxt):
            when[j] = onset + td
    n_out = 0
    while n_out < len(text) and when[n_out] <= t:
        n_out += 1
    return n_out, when


SETTLE = 0.08  # a letter flickers through random glyphs this long after it comes out, then holds


def flicker(shown: str, ages: list[float], rng, corrupt: float = 0.0) -> str:
    """tk.decode per letter: each letter is on screen from its own sung time (decode's typing clock is not used)."""
    return "".join(ch if ch == " " or (a >= SETTLE and not (corrupt > 0 and rng.random() < corrupt))
                   else rng.choice(tk.SCR) for ch, a in zip(shown, ages))


def lyric_tokens(c) -> None:
    """engine.lyric_tokens with sung-word timing: the same band, chips, token ids and keyword colours."""
    d = c.d
    tk.box(d, 24, 616, 1256, 680, "stdout · tokens", 0.45 + 0.3 * engine.pulse(c.t))
    f, fi = tk.font(tk.F_HEAD, 21), tk.font(tk.F_MONO, 11)
    x, y = 48, 626
    d.text((x, y), ">", font=f, fill=tk.amb(0.6))
    x += 26
    cur = line_at(c.t)
    if cur is None:
        if int(c.t * 2) % 2 == 0:
            d.rectangle([x, y + 4, x + 11, y + 28], fill=tk.amb(0.9))
        return
    ln, alpha = cur
    s = ln["text"]
    n_out, when = typed(ln, c.t)
    layer = d if alpha >= 0.999 else None
    if layer is None:  # fading before a break: draw on a layer and fade it
        from PIL import Image, ImageDraw
        ov = Image.new("RGBA", c.img.size, (0, 0, 0, 0))
        layer = ImageDraw.Draw(ov)
    pos = 0
    for k, tok in enumerate(tk.tokenize(s)):
        start = s.find(tok, pos)
        if start < 0:
            continue
        gap = start > pos
        pos = start + len(tok)
        if start >= n_out:
            break
        if gap:
            x += 8
        shown = tok[: n_out - start]
        txt = flicker(shown, [c.t - when[start + j] for j in range(len(shown))], c.rng, c.corrupt)
        tw = layer.textlength(tok, font=f)
        ws = s.rfind(" ", 0, start) + 1
        we = s.find(" ", start)
        we = len(s) if we < 0 else we
        key = re.sub(r"[^a-z-]", "", s[ws:we].lower())
        if key in engine.KEYWORDS and n_out >= we:
            bg = tk.red(0.95) if "exec" in key or key in ("illegal", "arguments") else \
                tk.blue(0.95) if key in ("love", "lo-o-ove") else tk.amb(0.95)
            layer.rectangle([x - 3, y + 2, x + tw + 3, y + 30], fill=bg)
            layer.text((x, y), txt, font=f, fill=tk.BG)
        else:
            layer.rectangle([x - 3, y + 2, x + tw + 3, y + 30], fill=tk.amb(0.13 if k % 2 == 0 else 0.22))
            layer.text((x, y), txt, font=f, fill=tk.amb(0.95))
        if n_out >= pos:
            tid = str(tk.token_id(tok))
            layer.text((x + (tw - layer.textlength(tid, font=fi)) / 2, y + 33), tid, font=fi, fill=tk.amb(0.45))
        x += tw + 6
    if alpha < 0.999:
        c.img.alpha_composite(tk.scale_alpha(ov, max(0.0, alpha)))
        return
    if n_out < len(s) or int(c.t * 3) % 2 == 0:
        d.rectangle([x + 2, y + 4, x + 13, y + 28], fill=tk.amb(0.9))


def lyric_now(c):
    """stage.lyric_now for the other layouts (token chips, lyric log, inline shell): (a, b, s, typed, rate)."""
    cur = line_at(c.t)
    if cur is None:
        return None
    ln, _ = cur
    n_out, when = typed(ln, c.t)
    span = max(0.2, ln["end"] - ln["start"])
    return ln["start"], ln["fade_until"], ln["text"], n_out, len(ln["text"]) / span


def install() -> None:
    if getattr(engine.lyric_tokens, "_words", False):
        return
    lyric_tokens._words = True
    engine.lyric_tokens = lyric_tokens   # engine's own frames look the name up in its module at call time
    stage.lyric_tokens = lyric_tokens    # stage imported the name
    stage.lyric_now = lyric_now
