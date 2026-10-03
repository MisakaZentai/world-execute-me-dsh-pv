"""Build the film from this repository.

    python build.py all [--gpu] [--workers N] [--4k]    everything below, in order
    python build.py check                               tools, fonts, your song and lyrics
    python build.py lyrics                              fetch the synced lyrics (if input/lyrics.lrc is missing), merge
    python build.py dancer                              stand-in dancer frames (skipped if the real caches are present)
    python build.py pages                               the dsh window: one HTML page per frame -> screenshots
    python build.py render [--gpu] [--workers N] [--4k] the film -> out/film.mp4 (and out/film_4k.mp4); the lossless
                                                        720p master stays in out/film_master.mp4

Inputs you supply (not in the repository, see input/README.md): input/song.mp3 and, optionally, input/lyrics.lrc.
Requirements: Python 3.12+ with Pillow and NumPy, Node 20+ with `npm install` run here (Playwright's Chromium:
`npx playwright install chromium`), ffmpeg on PATH. --gpu needs a Python with torch and CUDA (see docs/).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FILM = ROOT / "film"
DSH = FILM / "pv_dsh_frontend_20260927"
OUT = ROOT / "out"
SONG = ROOT / "input" / "song.mp3"
LRC = ROOT / "input" / "lyrics.lrc"
EXPECTED = json.loads((ROOT / "data" / "song.json").read_text(encoding="utf8"))
END = 211.9                     # the song's length, rounded down to a frame
CHIME_MS = 207873               # the turn's chime (batch_g.CHIME_T)
PAGES = ["batch_a1", "batch_a2", "batch_a3", "batch_b", "batch_c", "seg_page", "batch_e", "batch_g", "batch_f"]
FRAMES = {"batch_a1": "a1", "batch_a2": "a2", "batch_a3": "a3", "batch_b": "b", "batch_c": "c",
          "seg_page": "seg", "batch_e": "e", "batch_g": "g", "batch_f": "f"}   # batch_f reads E's end and G's start


def env(gpu: bool = False) -> dict:
    e = dict(os.environ, PYTHONUTF8="1", PV_PACKAGE_JSON=str(ROOT / "package.json"))
    shim = str(DSH / "gpu_shim")                           # stdlib audioop is gone in Python 3.13
    if sys.version_info >= (3, 13) or gpu:
        e["PYTHONPATH"] = os.pathsep.join(p for p in [shim, e.get("PYTHONPATH", "")] if p)
    if gpu:
        e["DSH_GPU"] = "1"
    return e


def run(cmd, cwd=ROOT, **kw):
    print("$", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run([str(c) for c in cmd], cwd=cwd, check=True, **kw)


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check(_=None) -> None:
    ok = True
    for tool in ["ffmpeg", "ffprobe", "node"]:
        if not shutil.which(tool):
            print(f"missing: {tool} on PATH")
            ok = False
    if not (ROOT / "node_modules" / "playwright").exists():
        print("missing: node_modules/playwright (run `npm install` and `npx playwright install chromium`)")
        ok = False
    fonts = {"PV_F_MONO": "C:/Windows/Fonts/consola.ttf", "PV_F_MONO_B": "C:/Windows/Fonts/consolab.ttf",
             "PV_F_CJK": "C:/Windows/Fonts/msyh.ttc", "PV_F_SYM": "C:/Windows/Fonts/seguisym.ttf"}
    for var, default in fonts.items():
        p = os.environ.get(var, default)
        if not Path(p).exists():
            print(f"missing font: {p} (set {var} to a substitute, see docs/FONTS.md)")
            ok = False
    if not SONG.exists():
        print(f"missing: {SONG.relative_to(ROOT)} (see input/README.md)")
        ok = False
    else:
        got = sha256(SONG)
        if got != EXPECTED["sha256"]:
            print(f"note: input/song.mp3 is not the file the film was timed on (sha256 {got[:12]}..., expected "
                  f"{EXPECTED['sha256'][:12]}...). It will render, but words and cuts may drift if your copy is "
                  f"offset; see input/README.md.")
    print("check:", "ok" if ok else "problems above")
    if not ok:
        sys.exit(1)


def lyrics(_=None) -> None:
    if not LRC.exists():
        run([sys.executable, "tools/lyrics.py", "fetch"])
    run([sys.executable, "tools/lyrics.py", "merge", "--lrc", LRC])


def dancer(_=None) -> None:
    run([sys.executable, "tools/placeholder_h3.py"])


def pages(_=None) -> None:
    for script in PAGES:
        run([sys.executable, f"{script}.py"], cwd=DSH, env=env())
        run(["node", "seg_shot.mjs", f"{FRAMES[script]}_frames.json"], cwd=DSH, env=env())


def render(a) -> None:
    """dsh_her renders a lossless RGB 720p master; every delivery is converted from it with the BT.709 matrix."""
    OUT.mkdir(exist_ok=True)
    e = env(a.gpu)
    e["DSH_MASTER"] = "1"
    python = a.python or sys.executable
    run([python, "dsh_her.py", "render", "0", str(END), "film_master.mp4", str(a.workers)], cwd=DSH, env=e)
    master = OUT / "film_master.mp4"
    shutil.move(DSH / "film_master.mp4", master)
    audio = ["-i", SONG, "-i", DSH / "chime_g.wav", "-filter_complex",
             f"[1:a]atrim=0:{END},asetpts=PTS-STARTPTS[s];[2:a]adelay={CHIME_MS}|{CHIME_MS}[c];"
             f"[s][c]amix=inputs=2:duration=first:normalize=0[a]", "-map", "0:v", "-map", "[a]"]
    tags = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv"]
    run(["ffmpeg", "-v", "error", "-y", "-i", master, *audio,
         "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p", "-c:v", "libx264", "-crf", "16",
         "-preset", "slow", *tags, "-c:a", "aac", "-b:a", "320k", "-movflags", "+faststart", "-shortest",
         OUT / "film.mp4"])
    if a.k4:   # the frames are pixel art at 1280 x 720: three times, pixel for pixel
        run(["ffmpeg", "-v", "error", "-y", "-i", master, *audio,
             "-vf", "scale=3840:2160:flags=neighbor:out_color_matrix=bt709:out_range=tv,format=yuv420p",
             "-c:v", "libx265", "-preset", "medium", "-crf", "16", *tags, "-tag:v", "hvc1",
             "-c:a", "aac", "-b:a", "320k", "-movflags", "+faststart", "-shortest", OUT / "film_4k.mp4"])
    print("done:", OUT / "film.mp4", "+ film_4k.mp4" if a.k4 else "")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=["all", "check", "lyrics", "dancer", "pages", "render"])
    ap.add_argument("--gpu", action="store_true", help="bloom, trail and scanlines on the GPU (torch + CUDA)")
    ap.add_argument("--python", help="the Python to render with (e.g. one with torch for --gpu)")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 2))
    ap.add_argument("--4k", dest="k4", action="store_true", help="also out/film_4k.mp4 (3x, nearest neighbour)")
    a = ap.parse_args()
    steps = {"check": check, "lyrics": lyrics, "dancer": dancer, "pages": pages, "render": render}
    for name in (["check", "lyrics", "dancer", "pages", "render"] if a.step == "all" else [a.step]):
        steps[name](a)


if __name__ == "__main__":
    main()
