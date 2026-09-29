"""The header's ECG becomes the song's own waveform, scrolling in real time.

engine.header drew a synthetic heartbeat (one blip per beat) at x 690-840 and the step/loss/tok-s counters at x 340.
Here header is replaced in memory by the same header with neither: across the middle of the header runs the last
SPAN seconds of the actual audio, as mirrored peak bars (1 px bar, 1 px gap). The newest audio is at the right end,
where a small dot breathes with the current level. Bars brighten with recency, each with a brighter core, over a faint
dotted centre line, all in the header's own colour (amber / warn / error follows the frame's alert).

    install(engine)      # idempotent; also rebinds modules that imported `header` by name
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parent
CACHE = OUT / "wave_rms_1ms.npy"
X0, YC, AMP = 364, 23, 11               # the band starts after the title; it ends GAP px before the chapter / clock
GAP = 30
SPAN = 2.4                               # seconds of audio across the band
BAR = 3                                  # px per bar (1 px bar, 2 px gap)
LO, HI, GAMMA = 0.05, 0.62, 1.1          # the 12 ms RMS of this mix spans ~0.06-0.85 (median 0.26): map LO..HI
_PEAKS = [None]


def peaks(wav):
    """Per-millisecond RMS of the song, normalised to its 99.5th percentile (cached)."""
    if _PEAKS[0] is None:
        if CACHE.exists():
            _PEAKS[0] = np.load(CACHE)
        else:
            raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(wav), "-f", "s16le", "-ac", "1", "-ar", "22050",
                                  "-"], capture_output=True, check=True).stdout
            x = np.frombuffer(raw, np.int16).astype(np.float32) ** 2
            per = 22050 // 1000 + 0.05                     # 22.05 samples per ms
            n = int(len(x) / per)
            idx = (np.arange(n + 1) * per).astype(int)
            p = np.sqrt(np.add.reduceat(x, idx[:-1])[:n] / np.diff(idx)[:n])
            p = np.clip(p / np.percentile(p, 99.5), 0, 1).astype(np.float32)
            np.save(CACHE, p)
            _PEAKS[0] = p
    return _PEAKS[0]


def level(rms):
    return min(1.0, max(0.0, (rms - LO) / (HI - LO))) ** GAMMA


def draw(c, col, wav, x1):
    p = peaks(wav)
    d = c.d
    n = (x1 - X0) // BAR
    for x in range(X0, x1, 4):                            # faint dotted centre line
        d.point((x, YC), fill=col(0.14))
    for k in range(n):
        a = c.t - SPAN * (1 - k / n)
        b = a + SPAN / n
        i0, i1 = max(0, int(a * 1000)), max(0, int(b * 1000))
        if i1 <= i0 or i0 >= len(p):
            continue
        v = level(float(p[i0:min(i1, len(p))].mean()))
        h = max(0, round(AMP * v))
        age = k / n                                        # 0 = oldest, 1 = now
        lit = (0.14 + 0.62 * age ** 1.8) * (0.65 + 0.35 * v)   # recent and loud bars are the bright ones
        x = X0 + k * BAR
        if h:
            d.line([x, YC - h, x, YC + h], fill=col(lit))
            core = h // 2
            if core:
                d.line([x, YC - core, x, YC + core], fill=col(min(1.0, lit + 0.18)))
    now = int(c.t * 1000)
    lv = level(float(p[max(0, now - 40):now + 1].mean())) if 0 < now < len(p) else 0.0
    r = 1.5 + 1.5 * lv
    cx = x1 + 7
    d.ellipse([cx - r, YC - r, cx + r, YC + r], fill=col(0.55 + 0.45 * lv))


def install(engine):
    if getattr(engine.header, "_wave", False):
        return
    orig = engine.header
    wav = sys.modules["music"].WAV if "music" in sys.modules else None
    if wav is None:
        import music
        wav = music.WAV

    def header(c):
        """engine.header without the synthetic ECG and the running counters, plus the real-time waveform."""
        d = c.d
        col = engine.red if c.alert == "err" else engine.anom if c.alert == "anom" else engine.amb
        fh = engine.font(engine.F_HEAD, 13)
        c.text((24, 14), "WORLD.EXECUTE(ME);   whale@deepsea:~$", fh, col(0.95))
        mm, ss = divmod(c.t, 60)
        state = {"err": "ERROR", "anom": "WARN"}.get(c.alert, "RUNNING")
        right = f"{c.chapter}   {int(mm):02d}:{ss:04.1f} / 03:32   {state}"
        rx = engine.W - 24 - d.textlength(right, font=fh)
        draw(c, col, wav, int(rx) - GAP)
        c.text((rx, 14), right, fh, col(0.85))
        d.line([24, 38, engine.W - 24, 38], fill=col(0.35))
        fs = engine.font(engine.F_MONO, 12)
        n = 52                  # the progress bar is shorter than engine's 60 so the whole credit fits the frame
        k = int(n * c.t / engine.SONG_LEN)
        d.text((24, 690), "[" + "|" * k + ":" * (n - k) + "]", font=fs, fill=engine.amb(0.4))
        credit = ("角色 溟月 © 上善无形 / 女仆版 ZipZipPipe / 立绘·表情 dsh-deep-whale, dsh-whale-galgame (CC BY-NC-SA 4.0)"
                  "  ·  Music: Mili - world.execute(me);  ·  非官方同人作品")
        fc = engine.font(engine.F_CJK, 11)
        d.text((engine.W - 24 - fc.getlength(credit), 689), credit, font=fc, fill=engine.amb(0.38))

    header._wave = True
    header._orig = orig
    for m in list(sys.modules.values()):                   # modules that did `from engine import header`
        if getattr(m, "header", None) is orig:
            try:
                m.header = header
            except Exception:
                pass
    engine.header = header
