"""Is the song you put in `input/` the one this film was timed on?

    python _tools\\check_song.py                     check input\\song.mp3
    python _tools\\check_song.py "C:\\path\\my.flac"   check any file

`data/song.json` is the film's own fingerprint (upstream `build.py check` reads the same file), so
this answers three questions:

  1. can the player even open it - it plays through Windows' MCI `mpegvideo` device, which handles
     mp3/wav and *not* flac;
  2. is it the same file the film was timed on (sha256), or the same song re-encoded (length and
     bitrate are then what matter);
  3. is it the untrimmed master: the film's clock starts at the first sample of the *trimmed* file,
     so a file 0.124 s longer runs 124 ms behind the picture.

Only the standard library, like the other tools here.
"""
from __future__ import annotations

import ctypes
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = json.loads((ROOT / "data" / "song.json").read_text(encoding="utf8"))
TRIM_S = 0.124


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def mci_length(path: Path) -> float | None:
    """Seconds MCI reports, or None when it refuses the file (which is what flac does)."""
    winmm = ctypes.windll.winmm
    alias = "checksong"
    winmm.mciSendStringW(f"close {alias}", None, 0, None)
    rc = winmm.mciSendStringW(f'open "{path}" type mpegvideo alias {alias}', None, 0, None)
    if rc:
        return None
    buf = ctypes.create_unicode_buffer(64)
    winmm.mciSendStringW(f"status {alias} length", buf, 64, None)
    winmm.mciSendStringW(f"close {alias}", None, 0, None)
    try:
        return int(buf.value) / 1000.0
    except ValueError:
        return None


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "input" / "song.mp3"
    print(f"fingerprint: {EXPECTED['title']}  {EXPECTED['duration_s']} s  "
          f"{EXPECTED['bit_rate'] // 1000} kbps  {EXPECTED['sample_rate']} Hz  {EXPECTED['channels']}ch")
    if not target.exists():
        print(f"missing: {target}\n  把音频放到 input\\song.mp3(或者把这个脚本指向你的文件)")
        sys.exit(1)
    size = target.stat().st_size / 2 ** 20
    digest = sha256(target)
    print(f"file       : {target}  ({size:.1f} MB)")
    print(f"sha256     : {digest}")
    length = None if target.suffix.lower() == ".flac" else mci_length(target)
    if target.suffix.lower() == ".flac":
        print("player     : NO - MCI cannot open flac")
    elif length is None:
        print(f"player     : NO - MCI refused it (rc != 0); only mp3/wav play")
    else:
        print(f"player     : yes - MCI opens it, length {length:.3f} s")

    ok = True
    if digest == EXPECTED["sha256"]:
        print("identity   : EXACT - this is the very file the film was timed on")
    elif length is not None:
        d = length - EXPECTED["duration_s"]
        print(f"identity   : same song, re-encoded? length differs by {d:+.3f} s")
        if abs(d) <= 0.05:
            print("             length matches: fine to play")
        elif abs(d - TRIM_S) <= 0.03:
            print(f"             it looks like the master before the {TRIM_S * 1000:.0f} ms trim was cut:")
            print(f"             the audio will run {TRIM_S * 1000:.0f} ms behind the picture. Fix with")
            print(f'             ffmpeg -y -i "{target}" -ss {TRIM_S} -c:a libmp3lame -b:a 320k input/song.mp3')
            ok = False
        else:
            print("             length is off by more than a frame budget; the sync will drift")
            ok = False
    else:
        ok = False
    if target.suffix.lower() == ".flac":
        print('             convert it:  ffmpeg -y -i "你的.flac" -ss 0.124 -c:a libmp3lame -b:a 320k input/song.mp3')
        ok = False
    print("\nVERDICT:", "usable" if ok else "not usable as it is - see above")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
