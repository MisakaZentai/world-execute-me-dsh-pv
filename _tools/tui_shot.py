"""Render frames of the terminal player to PNG, so they can actually be looked at.

The player writes ANSI to a terminal; there is no way to screenshot that from here, and judging the
picture from `Screen.text_dump()` means judging it from glyphs alone - which is exactly how a solid
block of `▀` hid the fact that the avatar had been averaged into flat grey.

This rasterises `Screen.buf` instead: one cell is `--cw` x `--ch` pixels, the cell's background is
filled, and the glyph is drawn in the cell's foreground. Wide characters advance two cells; CJK comes
from a second font because Consolas has none.

    python _tools/tui_shot.py 30                 one frame at t=30
    python _tools/tui_shot.py 30 44 73 --out tmp/shots
    python _tools/tui_shot.py --avatar            the header avatar through the whole training run
    python _tools/tui_shot.py 29.35 --size 197x52 --ripple 4
    python _tools/tui_shot.py --cut 5 --into 0.15 0.30 0.45   a named cut, N seconds into it

`--cut` plays a second of the outgoing shot and then steps through the cut, so the transition is
real: a cut is noticed where the shot index changes, so a jump lands *on* the cut with nothing
revealed yet (`--ripple` is measured from there and cannot show a mechanism mid-flight).
"""
from __future__ import annotations

import argparse
import sys
import unicodedata
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "_tools"))
import tui_live as T  # noqa: E402

MONO = "C:/Windows/Fonts/consola.ttf"
MONO_B = "C:/Windows/Fonts/consolab.ttf"
CJK = "C:/Windows/Fonts/msyh.ttc"

# Block elements are drawn as rectangles, not as glyphs. Consolas has none of them and msyh's are
# narrower than the cell, so a half-block pane came out as a grid of blocks with seams ("the avatar
# looked averaged into flat grey" is what this file exists to prevent, and a seam every cell reads no
# better). The colours are already exact: `▀` carries the upper colour in fg and the lower in bg.
HALF_BLOCKS = {"\u2580": "top", "\u2584": "bot", "\u2588": "all"}
RAMP_FILL = {"\u2581": 1, "\u2582": 2, "\u2583": 3, "\u2584": 4, "\u2585": 5, "\u2586": 6, "\u2587": 7}


def _font(path: str, size: int):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


class Painter:
    def __init__(self, size: int = 16, cw: int = 8, ch: int = 17):
        self.cw, self.ch = cw, ch
        self.f_ascii = _font(MONO, size)
        self.f_wide = _font(CJK, int(size * 1.05))

    def paint(self, s: T.Screen, path: Path, title: str = "") -> Path:
        w, h = s.cols * self.cw, s.rows * self.ch
        im = Image.new("RGB", (w, h), T.BG)
        d = ImageDraw.Draw(im)
        for y in range(s.rows):
            base = y * self.ch
            x = 0
            while x < s.cols:
                ch, fg, bg = s.buf[y][x]
                wide = s.wide[y][x]
                if wide and ch == "":
                    x += 1
                    continue
                cells = 2 if T._wide_char(ch) else 1
                d.rectangle([x * self.cw, base, (x + cells) * self.cw - 1, base + self.ch - 1], fill=bg)
                if ch in HALF_BLOCKS:
                    x1p, y1p = (x + cells) * self.cw - 1, base + self.ch - 1
                    kind = HALF_BLOCKS[ch]
                    if kind in ("top", "all"):
                        d.rectangle([x * self.cw, base, x1p, base + self.ch // 2 - 1], fill=fg)
                    if kind in ("bot", "all"):
                        d.rectangle([x * self.cw, base + self.ch // 2, x1p, y1p], fill=fg)
                elif ch in RAMP_FILL and ch.strip():
                    y0 = base + self.ch - max(1, round(self.ch * RAMP_FILL[ch] / 8))
                    d.rectangle([x * self.cw, y0, (x + cells) * self.cw - 1,
                                 base + self.ch - 1], fill=fg)
                elif ch.strip():
                    # Consolas has no U+2581..U+2587 (the waveform ramp) and no box drawing, and PIL
                    # draws those as `?` boxes - which looked exactly like the header being corrupted.
                    # msyh has them all, so anything past ASCII comes from it.
                    f = self.f_ascii if ord(ch) < 128 else self.f_wide
                    d.text((x * self.cw, base - 1), ch, font=f, fill=fg)
                x += cells
        if title:
            d.text((2, 0), title, font=_font(MONO_B, 12), fill=(255, 255, 255))
        path.parent.mkdir(parents=True, exist_ok=True)
        im.save(path)
        return path


def frame(t: float, cols: int, rows: int, painter: Painter, out: Path, warm: float = 1.0,
          ripple: float = 0.0, title: bool = True) -> Path:
    """One frame at t, having played `warm` seconds up to it - a jump is a cut, and a cut reveals."""
    d = T.Data()
    eng = T.Engine()
    T.FX.update(on=True, reveal=True, trail=True, vig=True, shake=True)
    T.fx_clear()
    s = T.Screen(cols, rows)
    import io
    sink = io.StringIO()
    steps = int(warm * 24)
    for k in range(steps):
        T.draw(s, d, eng, max(0.0, t - warm + k / 24), True, 24.0)
        s.render_diff(sink)
    T.draw(s, d, eng, t + ripple / 24, True, 24.0)
    s.render_diff(sink)
    ent = eng.entry_at(t)
    label = f"t={t:.2f}  {ent['name'] if ent else '-'}  win={T.WINDOW[0]}" if title else ""
    return painter.paint(s, out, label)


def cut_frame(cut: int, into: float, cols: int, rows: int, painter: Painter, out: Path,
              title: bool = True) -> Path:
    """One frame `into` seconds after cut `cut`, having really played the cut from a second before."""
    d = T.Data()
    eng = T.Engine()
    T.FX.update(on=True, reveal=True, mech=True, trail=True, vig=True, shake=True)
    T.fx_clear()
    s = T.Screen(cols, rows)
    import io
    sink = io.StringIO()
    t0 = eng.table[cut]["start"]
    for k in range(int(round((1.0 + into) * 24)) + 1):
        T.draw(s, d, eng, max(0.0, t0 - 1.0 + k / 24.0), True, 24.0)
        s.render_diff(sink)
    ent = eng.entry_at(t0 + into)
    label = (f"cut {cut} ({'+'.join(T.CUT_MECH.get(cut, ())) or 'delay field'})  "
             f"{ent['name'] if ent else '-'}  +{into:.2f}s") if title else ""
    return painter.paint(s, out, label)


def avatar_sheet(painter: Painter, out: Path, cols: int = 14, rows: int = 7) -> Path:
    """The header avatar across the film, laid out in a strip: seed -> noise -> parameters -> face."""
    times = [5.05, 5.6, 7.0, 8.6, 10.0, 11.0, 12.0, 15.0, 18.0, 22.0, 26.0, 30.0,
             38.0, 44.5, 52.0, 60.0, 66.0, 73.5, 80.0, 90.0, 100.0, 112.0, 130.0, 200.0]
    pad, lab = 4, 11
    cw, ch = painter.cw, painter.ch
    im = Image.new("RGB", (len(times) * (cols * cw + pad) + pad, rows * ch + lab + pad * 2),
                   (10, 12, 18))
    d = ImageDraw.Draw(im)
    f = _font(MONO, 11)
    for i, t in enumerate(times):
        av, theme, items = T.FP.dsh_window(t)
        blk = T._avatar_block(av, cols, rows) if av else None
        ox = pad + i * (cols * cw + pad)
        if blk:
            for r, row in enumerate(blk):
                for c, (top, bot) in enumerate(row):
                    x0 = ox + c * cw
                    y0 = lab + pad + r * ch
                    d.rectangle([x0, y0, x0 + cw - 1, y0 + ch // 2 - 1], fill=top)
                    d.rectangle([x0, y0 + ch // 2, x0 + cw - 1, y0 + ch - 1], fill=bot)
        d.text((ox, 1), f"{t:.0f}s", font=f, fill=(190, 200, 215))
        d.text((ox, 1 + 6), (av or "").split("/")[-1][:13], font=f, fill=(120, 130, 150))
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("times", nargs="*", type=float)
    ap.add_argument("--size", default="197x52")
    ap.add_argument("--out", default="tmp/shots")
    ap.add_argument("--warm", type=float, default=1.0)
    ap.add_argument("--ripple", type=float, default=0.0, help="frames into the cut reveal")
    ap.add_argument("--avatar", action="store_true", help="the avatar sheet instead of frames")
    ap.add_argument("--no-title", action="store_true",
                    help="no label in the top-left corner (the player does not draw one)")
    ap.add_argument("--cut", type=int, help="render frames N seconds into this cut instead of at times")
    ap.add_argument("--into", nargs="*", type=float, default=[0.15, 0.30, 0.45],
                    help="seconds into the cut, for --cut (default 0.15 0.30 0.45)")
    args = ap.parse_args()
    c, _, r = args.size.partition("x")
    cols, rows = int(c), int(r)
    p = Painter()
    out = ROOT / args.out
    if args.avatar:
        print(avatar_sheet(p, out / "avatar_sheet.png"))
        return
    if args.cut is not None:
        for into in args.into:
            print(cut_frame(args.cut, into, cols, rows, p,
                            out / f"cut{args.cut:02d}_into{into:04.2f}.png".replace(".", "_", 1),
                            title=not args.no_title))
        return
    for t in (args.times or [30.0]):
        name = f"t{t:07.2f}".replace(".", "_") + ".png"
        print(frame(t, cols, rows, p, out / name, args.warm, args.ripple,
                    title=not args.no_title))


if __name__ == "__main__":
    main()
