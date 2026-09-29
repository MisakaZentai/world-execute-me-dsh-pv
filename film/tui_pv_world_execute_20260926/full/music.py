"""The song as numbers, and her portrait reacting to them.

Features, 48 per second, computed once with ffmpeg band filters and cached in audio_features.json:
  loud      overall RMS
  bands     energy in seven bands, bass (40-120 Hz) to air (6-10 kHz)
  kick      onset strength in the bass band (the drum hits, not the beat grid)
  flux      onset strength over all bands
  cent      where the tune sits: the energy centroid of the 300 Hz - 6 kHz bands, 0 low .. 1 high

react() maps them onto her half-block portrait:
  body = spectrum   each row of cells shifts with the band that matches its height (hair = highs,
                    skirt and tail = bass), as a wave running down her; quiet bands leave the row still
  kick              the whole portrait flares and hops one cell on the drum hits
  flux              a few cells flash to the highest level on onsets
  loud              in quiet passages some cells drop out, and she fills in as the song swells
"""

from __future__ import annotations

import audioop
import json
import math
import os
import random
import subprocess
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageChops

from engine import BPM, MV
from tuikit import BLUE_HI

WAV = MV / "audio" / "song_mono22k.wav"
CACHE = Path(__file__).with_name("audio_features.json")
RATE = 48
BANDS = [(40, 120), (120, 300), (300, 700), (700, 1500), (1500, 3000), (3000, 6000), (6000, 10000)]


def _rms(pcm: bytes, sr: int) -> list[float]:
    hop = sr // RATE
    return [audioop.rms(pcm[i * 2 * hop:(i + 1) * 2 * hop], 2) for i in range(len(pcm) // (2 * hop))]


def _pcm(af: str | None) -> bytes:
    cmd = ["ffmpeg", "-v", "error", "-i", str(WAV)] + (["-af", af] if af else []) + \
          ["-f", "s16le", "-ac", "1", "-ar", "22050", "-"]
    return subprocess.run(cmd, capture_output=True, check=True).stdout


def _norm(v: list[float], q: float = 0.98) -> list[float]:
    ref = sorted(v)[int(len(v) * q)] or 1.0
    return [min(1.0, x / ref) for x in v]


def _follow(v: list[float], attack: float, release: float) -> list[float]:
    out, s = [], 0.0
    for x in v:
        s += (x - s) * (attack if x > s else release)
        out.append(s)
    return out


def _onset(v: list[float]) -> list[float]:
    slow = _follow(v, 0.08, 0.08)
    return _norm([max(0.0, a - b) for a, b in zip(v, slow)])


def _compute() -> dict:
    loud = _follow(_norm(_rms(_pcm(None), 22050)), 0.6, 0.15)
    raw = [_norm(_rms(_pcm(f"highpass=f={lo},highpass=f={lo},lowpass=f={hi},lowpass=f={hi}"), 22050))
           for lo, hi in BANDS]
    n = min(len(loud), *(len(b) for b in raw))
    bands = [[round(x, 3) for x in _follow(b[:n], 0.6, 0.18)] for b in raw]
    kick = _follow(_onset(raw[0][:n]), 0.9, 0.2)
    flux = _follow(_norm([sum(o) for o in zip(*(_onset(b[:n]) for b in raw))]), 0.9, 0.25)
    logs = [math.log2(math.sqrt(lo * hi)) for lo, hi in BANDS]
    cent = []
    for i in range(n):
        w = [raw[b][i] for b in range(2, 6)]
        cent.append(sum(wb * logs[b + 2] for b, wb in enumerate(w)) / sum(w) if sum(w) > 1e-4 else None)
    known = sorted(c for c in cent if c is not None)
    lo_c, hi_c = known[int(len(known) * 0.05)], known[int(len(known) * 0.95)]
    cent = [0.5 if c is None else min(1.0, max(0.0, (c - lo_c) / (hi_c - lo_c))) for c in cent]
    cent = _follow(cent, 0.12, 0.12)
    r = lambda v: [round(x, 3) for x in v]  # noqa: E731
    return dict(rate=RATE, loud=r(loud[:n]), bands=bands, kick=r(kick), flux=r(flux), cent=r(cent))


@lru_cache(None)
def table() -> dict:
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    data = _compute()
    tmp = CACHE.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data), encoding="utf-8")
    os.replace(tmp, CACHE)
    return data


class Feat:
    __slots__ = ("loud", "bands", "kick", "flux", "cent")


def at(t: float) -> Feat:
    tb = table()
    i = max(0, min(len(tb["loud"]) - 1, int(t * RATE)))
    f = Feat()
    f.loud, f.kick, f.flux, f.cent = tb["loud"][i], tb["kick"][i], tb["flux"][i], tb["cent"][i]
    f.bands = [b[i] for b in tb["bands"]]
    return f


@lru_cache(8)
def _noise(cols: int, rows: int, seed: int) -> Image.Image:
    rnd = random.Random(seed)
    im = Image.new("L", (cols, rows))
    im.putdata([rnd.randrange(256) for _ in range(cols * rows)])
    return im


MARGIN = 2  # cells of room on each side for the row shifts


def react(sp: Image.Image, t: float, px: int = 4, amount: float = 1.0) -> tuple[Image.Image, int]:
    """Her sprite moved by the music. Returns (image, x offset): paste at sx - offset."""
    f = at(t)
    w, h = sp.size
    m = MARGIN * px
    rows = max(1, h // px)
    out = Image.new("RGBA", (w + 2 * m, h), (0, 0, 0, 0))
    phase = t * 2 * math.pi * (BPM / 60) / 2
    for r in range(rows):
        u = r / max(1, rows - 1)
        e = f.bands[min(6, int((1 - u) * 7))]
        shift = e ** 1.5 * 2.2 * amount * math.sin(2 * math.pi * u * 2.0 - phase)
        out.paste(sp.crop((0, r * px, w, (r + 1) * px)), (m + int(round(shift)) * px, r * px))
    if h > rows * px:
        out.paste(sp.crop((0, rows * px, w, h)), (m, rows * px))
    r_, g_, b_, a_ = out.split()
    # quiet passages: some cells drop out (a new pattern every half beat)
    drop = max(0.0, min(1.0, (0.32 - f.loud) / 0.32)) * 0.3 * amount
    if drop > 0.01:
        cols = out.width // px
        noise = _noise(cols, rows + 1, int(t * BPM / 30))
        keep = noise.point(lambda v: 0 if v < drop * 255 else 255).resize((cols * px, (rows + 1) * px), Image.NEAREST)
        a_ = ImageChops.multiply(a_, keep.crop((0, 0, out.width, h)))
    # drum hits: the portrait flares
    flare = min(1.0, f.kick * 0.9) * amount
    if flare > 0.02:
        lut = [min(255, int(v * (1 + 0.55 * flare) + 30 * flare)) for v in range(256)]
        r_, g_, b_ = r_.point(lut), g_.point(lut), b_.point(lut)
    out = Image.merge("RGBA", (r_, g_, b_, a_))
    # onsets: a few cells flash to the top level
    n = int(28 * max(0.0, f.flux - 0.35) / 0.65 * amount)
    if n:
        rnd = random.Random(int(t * 48))
        amask = a_.load()
        hi = BLUE_HI + (255,)
        for _ in range(n * 3):
            cx, cy = rnd.randrange(out.width // px), rnd.randrange(rows)
            if amask[cx * px + px // 2, cy * px + px // 2] > 0:
                out.paste(hi, (cx * px, cy * px, cx * px + px - 1, cy * px + px - 1))
                n -= 1
                if n <= 0:
                    break
    return out, m
