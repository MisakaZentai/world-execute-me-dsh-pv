"""Sung-word onsets from the word-level alignment (the lyric band uses the same file).

The right side's cuts follow the LRC line starts; the left's echoes land on the sung word, which is often 0.4-1.3 s
later. w(line, i) is the onset of word i of lyric line `line` (the timeline's line_id).
"""
from __future__ import annotations

import json
from pathlib import Path

WORDS = json.loads(Path(__file__).resolve().parents[1].joinpath("world_execute_word_timing_20260927/word_timeline.json")
                   .read_text(encoding="utf8"))["words"]


def w(line, i):
    return next(x["start"] for x in WORDS if x["line_id"] == line and x["word_index"] == i)
