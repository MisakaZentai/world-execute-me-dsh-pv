"""Music for the two players, through Windows' own MCI - nothing to install.

Neither player had any: `tui_live.py` draws characters and `preview.py` shows frames, and neither
ever opened the song. Windows ships an MCI "mpegvideo" device that plays an mp3 directly, so this
wraps `winmm.mciSendStringW` and plays the film's own `input/song.mp3` - no extra file on disk, no
package to install, and it is the same 320 kbps track the mp4 was muxed from.

Two things measured on this machine; the interface below is shaped around them.

  * `status <alias> length` is 211871 ms and, once running, `status <alias> position` advances at
    exactly 1.000x wall clock and is the same 320 kbps track the mp4 was muxed from. The song is a
    usable clock.
  * `position` is the *decoder's* position, and the decoder runs ahead of the speaker. Asked to
    start at t, MCI reports `t + D` until the buffer fills, then advances at 1.000x; what you hear
    is `position - D`. `D` is `LATENCY` below. Twelve starts on this machine gave
    0, 723, 312, 243, 241, 233, 209, 210, 267, 246, 198, 211 ms: a median of 237 ms, with the
    clean readings all inside 198-312 ms. (The 0 is a stale first read and the 723 a slow start;
    the position moves in ~100 ms steps, so anything finer than that is not resolvable from
    outside.) Per-start estimation was tried and dropped - the plateau it keyed on is not always
    observable at a caller's poll rate, while the constant is within 100 ms of every clean reading.
    `--audio-latency` overrides it if your ears disagree.

If any of it fails - no MCI device, no sound card, no mp3 - the object turns itself off and every
method becomes a no-op, so callers never have to check.

    import pv_audio
    a = pv_audio.Audio()
    if a.ok:
        a.play(120.0)                 # seek there and start
        t = a.lock(t) or t            # None means "your clock is close enough"
        a.set_volume(600); a.mute(True); a.close()
"""
from __future__ import annotations

import ctypes
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SONG = ROOT / "input" / "song.mp3"
LATENCY = 0.25                   # seconds the decoder runs ahead of the speaker; see the module docstring


def find_song(explicit: str | os.PathLike | None = None) -> Path | None:
    """`--audio-file`, else $PV_AUDIO, else the film's own input/song.mp3."""
    for cand in (explicit, os.environ.get("PV_AUDIO"), DEFAULT_SONG):
        if not cand:
            continue
        p = Path(cand)
        if p.exists():
            return p
    return None


class Audio:
    """One mp3, played by Windows. Every method is a no-op once `ok` is False."""

    def __init__(self, path=None, enabled: bool = True, volume: int = 1000,
                 latency: float = LATENCY) -> None:
        self.ok = False
        self.error = ""
        self.path = find_song(path)
        self.latency = max(0.0, float(latency))
        self.volume = max(0, min(1000, int(volume)))
        self.muted = False
        self._mode = "stopped"
        self._base = 0.0
        self._alias = f"pv{os.getpid()}"
        if not enabled:
            self.error = "off"
            return
        if os.name != "nt":
            self.error = "MCI is Windows only"
            return
        if self.path is None:
            self.error = f"no audio file ({DEFAULT_SONG})"
            return
        self._winmm = ctypes.windll.winmm
        self._buf = ctypes.create_unicode_buffer(512)
        # `mpegvideo` is the MCI device that knows mp3. Its name has nothing to do with video here:
        # for an audio-only file it opens no window and plays only sound.
        r, _ = self._send(f'open "{self.path.as_posix()}" type mpegvideo alias {self._alias}')
        if r:
            self.error = self._why(r)
            return
        self.ok = True
        self.set_volume(self.volume)

    # ------------------------------------------------------------------ the device

    def _send(self, cmd: str) -> tuple[int, str]:
        r = self._winmm.mciSendStringW(cmd, self._buf, 511, None)
        return r, self._buf.value

    def _why(self, code: int) -> str:
        err = ctypes.create_unicode_buffer(512)
        if self._winmm.mciGetErrorStringW(code, err, 511):
            return err.value or f"MCI error {code}"
        return f"MCI error {code}"

    @property
    def length(self) -> float | None:
        if not self.ok:
            return None
        _, v = self._send(f"status {self._alias} length")
        try:
            return int(v) / 1000.0
        except ValueError:
            return None

    def position(self) -> float | None:
        """Where MCI says it is, in seconds - about 250 ms ahead of what you hear."""
        if not self.ok:
            return None
        _, v = self._send(f"status {self._alias} position")
        try:
            return int(v) / 1000.0
        except ValueError:
            return None

    # ------------------------------------------------------------------ transport

    def play(self, t: float) -> None:
        """Seek to t and start."""
        if not self.ok:
            return
        t = max(0.0, float(t))
        self._send(f"seek {self._alias} to {int(t * 1000)}")
        self._send(f"play {self._alias}")
        self._mode = "playing"
        self._base = t

    def resume(self) -> None:
        if self.ok:
            self._send(f"resume {self._alias}")
            self._mode = "playing"

    def pause(self) -> None:
        if self.ok:
            self._send(f"pause {self._alias}")
            self._mode = "paused"

    def seek(self, t: float) -> None:
        """Move without changing the play state (a scrub while paused, or a jump while playing)."""
        if not self.ok:
            return
        if self._mode == "playing":
            self.play(t)
        else:
            self._send(f"seek {self._alias} to {int(max(0.0, t) * 1000)}")

    def set_volume(self, v: int) -> None:
        if not self.ok:
            return
        self.volume = max(0, min(1000, int(v)))
        self._send(f"setaudio {self._alias} volume to {self.volume}")

    def mute(self, on: bool | None = None) -> bool:
        """Mute or unmute; with no argument, toggle. Uses MCI's own `setaudio off`, so the volume
        setting survives."""
        if not self.ok:
            return False
        self.muted = (not self.muted) if on is None else bool(on)
        self._send(f"setaudio {self._alias} {'off' if self.muted else 'on'}")
        return self.muted

    # ------------------------------------------------------------------ the clock

    def lock(self, t: float, tolerance: float = 0.15, max_step: float = 0.12) -> float | None:
        """The song time the picture should show, or None to keep the caller's own clock.

        The song time being heard is `position - latency`. A correction larger than `tolerance` is
        taken in `max_step` slices so it never reads as a jump - unless it is a real jump, over
        0.6 s, which is taken at once.
        """
        if not self.ok or self._mode != "playing":
            return None
        p = self.position()
        if p is None:
            return None
        target = p - self.latency
        if target < 0:
            return None
        d = target - t
        if abs(d) <= tolerance:
            return None
        if abs(d) > 0.6:
            return target
        return t + max(-max_step, min(max_step, d))

    def status(self) -> str:
        """One short line for a player's status bar."""
        if not self.ok:
            return f"audio off ({self.error})"
        p = self.position()
        return (f"audio {p:6.1f}s  lat {self.latency * 1000:.0f}ms  vol {self.volume // 10:3d}%"
                + ("  MUTED" if self.muted else ""))

    def close(self) -> None:
        if self.ok:
            self._send(f"close {self._alias}")
        self.ok = False
        self._mode = "stopped"

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass


def main() -> None:
    """`python _tools/pv_audio.py [--seconds N]` - play the song, or just report what MCI says."""
    import argparse
    ap = argparse.ArgumentParser(description="play the film's song through MCI (test only)")
    ap.add_argument("--file", help="mp3 to play (default the film's input/song.mp3)")
    ap.add_argument("--seconds", type=float, default=0.0, help="play this long, then stop")
    ap.add_argument("--at", type=float, default=0.0, help="start here")
    ap.add_argument("--volume", type=int, default=1000, help="0..1000")
    ap.add_argument("--latency", type=float, default=LATENCY, help="seconds the decoder leads the speaker")
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    a = Audio(args.file, volume=args.volume, latency=args.latency)
    print(f"file       {a.path}")
    print(f"open       {'ok' if a.ok else 'FAILED: ' + a.error}")
    if not a.ok:
        raise SystemExit(1)
    print(f"length     {a.length:.3f} s   (the film is 211.9 s)")
    if not args.seconds:
        print("\nplayable. --seconds 6 --at 120 to actually put sound on it\n")
        a.close()
        return
    a.play(args.at)
    w0, t = time.perf_counter(), args.at
    while time.perf_counter() - w0 < args.seconds:
        time.sleep(0.1)
        tgt = a.lock(t)
        if tgt is not None:
            t = tgt
        print(f"  wall {time.perf_counter() - w0:5.2f}s  pos {a.position():7.3f}s  "
              f"picture {t:7.3f}s  drift {(a.position() - a.latency) - t:+.3f}s")
    a.close()


if __name__ == "__main__":
    main()
