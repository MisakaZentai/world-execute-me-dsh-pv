# SPDX-License-Identifier: MIT
"""The film's two lyric files, rebuilt from your own copy of the synced lyrics.

This repository carries no lyric text. The film reads two lyric files:

  film/ai_mascot_mv_world_execute_20260926/audio/lyrics_synced.lrc
      the synced lyrics (LRC). The film's structure hangs on it: cut times and every lyric_start() lookup.
  film/world_execute_word_timing_20260927/word_timeline.json
      word-level timing of the vocals; the lyric band types each word when it is sung.

data/timing/ holds both without their text: every time, flag and count, and per line the sha256 of its text and
the character span of each word. `merge` puts the text of your LRC back in and checks every line against its
sha256, so what it writes is exactly what the film was made with, or nothing.

    python tools/lyrics.py fetch [--out input/lyrics.lrc] [--force]
        Download the synced lyrics of LRCLIB entry 36914646 (the LRC the film was timed on) from
        https://lrclib.net/api/get/36914646 into input/lyrics.lrc. Skipped if that file exists (--force replaces
        it).

    python tools/lyrics.py merge [--lrc input/lyrics.lrc]
        Rebuild both files from your LRC. Your LRC's own timestamps are not used (the film keeps its timing), so
        a copy with other timestamps works as long as the text of each line is the same. Lines are matched in
        order; extra lines (credits, tags) are ignored. If a line of the film is missing or has other text in your
        copy, merge lists those lines and writes nothing: your LRC is then probably a different version, and
        `fetch --force` gets the right one.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "timing"
LRC_DATA = DATA / "lyrics_synced_notext.json"
TIMELINE_DATA = DATA / "word_timeline_notext.json"
DEFAULT_LRC = ROOT / "input" / "lyrics.lrc"
LRCLIB_ID = 36914646
LRCLIB_URL = f"https://lrclib.net/api/get/{LRCLIB_ID}"
USER_AGENT = "world-execute-film/1.0 (tools/lyrics.py)"

TAGS = re.compile(r"^\s*((?:\[\d+:\d+(?:[.:]\d+)?\]\s*)+)(.*)$")    # one or more leading time tags, then text
TIME = re.compile(r"\[(\d+):(\d+)(?:[.:](\d+))?\]")
INLINE = re.compile(r"<\d+:\d+(?:[.:]\d+)?>")                        # enhanced-LRC word stamps


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def rel(p: Path) -> str:
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(p)


def seconds(tag: str) -> float:
    m = TIME.match(tag)
    return int(m[1]) * 60 + int(m[2]) + (float("0." + m[3]) if m[3] else 0.0)


def fmt(t: float) -> str:
    return f"[{int(t // 60):02d}:{t % 60:05.2f}]"


# ---------------------------------------------------------------- fetch

def fetch(a) -> None:
    out = resolve(a.out)
    if out.exists() and not a.force:
        print(f"{rel(out)} already exists, left as is (--force replaces it)")
        return
    print(f"fetching the synced lyrics of LRCLIB entry {LRCLIB_ID} from {LRCLIB_URL}")
    req = urllib.request.Request(LRCLIB_URL, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        sys.exit(f"download failed: {e}\nSave the synced lyrics yourself as {rel(out)} (LRC, UTF-8), then run merge.")
    synced = data.get("syncedLyrics") if isinstance(data, dict) else None
    if not synced or data.get("id") != LRCLIB_ID:
        sys.exit(f"unexpected answer from {LRCLIB_URL} (no synced lyrics for entry {LRCLIB_ID}); nothing written")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(synced.encode("utf-8"))
    timed = sum(1 for line in synced.splitlines() if TAGS.match(line))
    print(f"got \"{data.get('trackName')}\" by {data.get('artistName')} ({data.get('albumName')}): "
          f"{timed} timed lines -> {rel(out)}")


# ---------------------------------------------------------------- merge

def read_lrc(path: Path) -> list[dict]:
    """Timed lines with text, in time order: [{t, line (1-based in the file), variants: {text}}]."""
    try:
        text = path.read_bytes().decode("utf-8-sig")
    except UnicodeDecodeError:
        sys.exit(f"{rel(path)} is not UTF-8 text; save it as UTF-8 and run again")
    rows = []
    for n, line in enumerate(text.splitlines(), 1):
        m = TAGS.match(line)
        if not m:
            continue                                          # [ar:...] and other header tags, plain text
        body = m[2]
        # the same line written a little differently; any of them only counts if its sha256 is the film's
        variants = {body.strip(), " ".join(body.split()), " ".join(INLINE.sub("", body).split())} - {""}
        for tag in TIME.findall(m[1]):
            t = int(tag[0]) * 60 + int(tag[1]) + (float("0." + tag[2]) if tag[2] else 0.0)
            if variants:
                rows.append({"t": t, "line": n, "variants": variants})
    rows.sort(key=lambda r: (r["t"], r["line"]))
    return rows


def match(film: list[dict], mine: list[dict]) -> tuple[dict, list[str], int, int]:
    """Film LRC line index -> its text from your LRC. Also the problems, the number of extra lines of yours, and
    how many matched lines carry other timestamps."""
    want = [ln["sha256"] for ln in film if ln["sha256"]]
    at = [k for k, ln in enumerate(film) if ln["sha256"]]
    known = set(want)
    keys, texts = [], []
    for j, row in enumerate(mine):
        hit = next(((sha(v), v) for v in sorted(row["variants"]) if sha(v) in known), None)
        keys.append(hit[0] if hit else f"yours:{j}")
        texts.append(hit[1] if hit else max(row["variants"], key=len))
    found, problems, extra, retimed = {}, [], 0, 0
    sm = difflib.SequenceMatcher(None, want, keys, autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            for i, j in zip(range(i1, i2), range(j1, j2)):
                found[at[i]] = texts[j]
                retimed += abs(mine[j]["t"] - seconds(film[at[i]]["tag"])) > 0.005
            continue
        extra += max(0, (j2 - j1) - (i2 - i1))
        for off, i in enumerate(range(i1, i2)):
            ln = film[at[i]]
            head = f"  film LRC line {at[i] + 1:3d} {ln['tag']} ({ln['len']} chars): "
            if j1 + off < j2:
                j = j1 + off
                problems.append(head + f"your line {mine[j]['line']} {fmt(mine[j]['t'])} has other text "
                                       f"({len(texts[j])} chars)")
            else:
                problems.append(head + "not in your LRC")
    return found, problems, extra, retimed


def apply_patch(text: str, ops: list[dict]) -> str:
    words = text.split()
    for op in ops:
        if op["op"] == "reorder_words":
            if len(op["order"]) != len(words):
                return text                                   # not the expected line; the sha256 check reports it
            words = [words[k] for k in op["order"]]
        elif op["op"] == "replace_words":
            words[op["at"]:op["at"] + op["remove"]] = op["insert"]
        else:
            sys.exit(f"{rel(TIMELINE_DATA)}: unknown patch {op['op']!r}")
    return " ".join(words)


def dumps_exact(obj: dict, f: dict) -> bytes:
    text = json.dumps(obj, ensure_ascii=f["ensure_ascii"], indent=f["json_indent"])
    text = text.replace("\n", f["newline"]) + (f["newline"] if f["final_newline"] else "")
    return text.encode("utf-8")


def merge(a) -> None:
    src = resolve(a.lrc)
    if not src.exists():
        sys.exit(f"{rel(src)} not found: run `python tools/lyrics.py fetch`, or put your own LRC there")
    lrc = json.loads(LRC_DATA.read_text(encoding="utf-8"))
    tl = json.loads(TIMELINE_DATA.read_text(encoding="utf-8"))
    mine = read_lrc(src)
    print(f"merging {rel(src)} ({len(mine)} timed lines with text) with {rel(DATA)}")
    film = lrc["lines"]
    found, problems, extra, retimed = match(film, mine)

    # the LRC: the film's tags and spacing around your text
    rows = []
    for k, ln in enumerate(film):
        text = found.get(k, "") if ln["sha256"] else ""
        rows.append(ln["tag"] + ln["pre"] + text + ln["post"])
    f = lrc["format"]
    lrc_bytes = (f["newline"].join(rows) + (f["newline"] if f["final_newline"] else "")).encode(f["encoding"])

    # the word timeline: LRC line `id`, patched, cut into words at the stored spans
    patches = {p["line_id"]: p["ops"] for p in tl["patches"]}
    skel, bad_lines = tl["skeleton"], []
    by_id = {}
    for meta in tl["lines"]:
        i = meta["id"]
        if i not in found:
            continue                                          # reported above
        text = apply_patch(found[i], patches[i]) if i in patches else found[i]
        if sha(text) != meta["sha256"]:
            bad_lines.append(f"  timeline line {i}: the patched text does not match (patch data out of date?)")
            continue
        by_id[i] = (text, meta["spans"])
    if problems or bad_lines:
        total = sum(1 for ln in film if ln["sha256"])
        print(f"\nYour LRC does not match the lyrics the film was timed on in {len(problems)} of {total} lines:")
        print("\n".join(problems + bad_lines))
        sys.exit(f"\nNothing was written. The film's lines are those of LRCLIB entry {LRCLIB_ID}; "
                 f"`python tools/lyrics.py fetch --force` downloads them (and replaces {rel(DEFAULT_LRC)}).")
    for ln in skel["lines"]:
        text, spans = by_id[ln["id"]]
        ln["text"] = text
        ln["words"] = [w for w in skel["words"] if w["line_id"] == ln["id"]]
        if len(ln["words"]) != len(spans):
            sys.exit(f"{rel(TIMELINE_DATA)}: line {ln['id']} has {len(ln['words'])} words but {len(spans)} spans")
        for w in ln["words"]:
            s, e = spans[w["word_index"]]
            w["text"] = text[s:e]
    tl_bytes = dumps_exact(skel, tl["format"])

    for name, data, expected in [(lrc["target"], lrc_bytes, lrc["sha256"]), (tl["target"], tl_bytes, tl["sha256"])]:
        got = hashlib.sha256(data).hexdigest()
        if got != expected:
            sys.exit(f"{name}: every line matched but the rebuilt file does not (sha256 {got[:12]}..., expected "
                     f"{expected[:12]}...); {rel(DATA)} is inconsistent. Nothing was written.")
    for name, data in [(lrc["target"], lrc_bytes), (tl["target"], tl_bytes)]:
        out = ROOT / name
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        print(f"wrote {name}: identical to the film's file (sha256 {hashlib.sha256(data).hexdigest()[:12]}...)")
    if extra:
        print(f"note: {extra} line(s) of your LRC are not in the film's and were ignored")
    if retimed:
        print(f"note: {retimed} line(s) of your LRC have other timestamps; the film's timing was kept")


def resolve(p: str | Path) -> Path:
    """A path as given (absolute, or relative to the current folder), else relative to the repository root."""
    p = Path(p)
    if p.is_absolute() or p.exists():
        return p
    return ROOT / p if (ROOT / p).exists() else p


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", help=f"download LRCLIB entry {LRCLIB_ID} into input/lyrics.lrc")
    f.add_argument("--out", default=DEFAULT_LRC, help="where to save it (default: input/lyrics.lrc)")
    f.add_argument("--force", action="store_true", help="replace an existing file")
    m = sub.add_parser("merge", help="rebuild the film's lyric files from your LRC")
    m.add_argument("--lrc", default=DEFAULT_LRC, help="your synced lyrics (default: input/lyrics.lrc)")
    a = ap.parse_args()
    {"fetch": fetch, "merge": merge}[a.cmd](a)


if __name__ == "__main__":
    main()
