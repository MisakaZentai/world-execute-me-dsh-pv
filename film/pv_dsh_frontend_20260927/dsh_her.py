"""The left pane as a dsh window: inside the batches done so far (COVER) the v2 her layer is replaced by per-frame
screenshots of the dsh page (dsh_frames/NNNNN.png, NNNNN = round(t * 24), one folder for the whole film).

Every shot's choreography (retraction, the isolation pull-back, the slide out and back) acts on this layer exactly as
it did on her glyph pane, because only kit.her_layer changes. Production files are not touched: everything is patched
in memory, the same way as tui_native_her_20260927/native_her.py.

    python dsh_her.py stills 6 9 14 104 109 112.3
    python dsh_her.py render <t0> <t1> <name.mp4> [workers]
"""
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent
MMD = Path(__file__).resolve().parents[1].joinpath("mmd_motion_eval_20260927")
sys.path.insert(0, str(MMD))
import pv_full  # noqa: E402  (also puts continuity_full_v2 on sys.path)

COVER = [(5.0, 16.0), (16.0, 29.28), (29.28, 44.0), (44.0, 73.54), (73.54, 103.0), (103.0, 125.0)]   # A1..A3, B, C, D
FPS = 24
FRAMES = OUT / "dsh_frames"
PLACEHOLDER = os.environ.get("DSH_PLACEHOLDER")  # a single png used for every frame (choreography test)
INNER = (3, 9, 3, 3)                              # pane interior inset from the pane rect (left, top, right, bottom)
BG = (4, 7, 15)
RIGHT = (392, 44, 1268, 608)                      # visualisation + ops column
# which side leads: the other drops to support brightness (the left one only through her layer's alpha)
LEAD = [(0.0, "both"), (5.24, "left"), (7.08, "right"), (12.47, "both"), (16.0, "both"), (41.21, "left"),
        (41.93, "both"),
        (103.0, "left"), (110.40, "both"), (115.60, "right"), (123.55, "left"), (125.0, "both")]
CUR = [0.0]            # the frame being drawn (the pane title swap needs it)
GONE = 115.42          # seg_page.GONE: the page is taken apart down to one cursor; from here the cursor is all of her
CURSOR = (9, 18)       # the last cursor, drawn here from GONE until the window returns (BACK)
BACK = 121.77
SUPPORT = 0.42
PATCHES = [g for g in ["d", "mem", "e", "f", "g"] if os.environ.get("DSH_ONLY", g) == g]  # dsh_patch_<g>.py (see install)
RECT_FROM_CALL = []        # time ranges where the window follows the shot's own pane rect (call["rect"])
FINISH = []                # frame-level overrides registered by group patches
PANE = [None]              # make_pane(orig_me_pane) -> a me_pane that draws the dsh window (set by install)
BOX = [None]               # tuikit.box before the title swap
DEPLOY = (73.54, 103.0)  # group C: the right side's pane titles keep their suffix (role=deploy, class 281, ...)
AVATAR_C = (69, 105)     # her avatar square on screen (window origin + the page's .pv-pet centre)
PROPS_ON_AVATAR = {"shot_god"}   # of section 04's props only the hand-off to the process tree stays, from the avatar


def pane_title(t, title):
    """/dev/me -> dsh web; inside DEPLOY the shot's own suffix stays (except the default pid)."""
    if not (isinstance(title, str) and title.startswith("/dev/me")):
        return title
    rest = title[len("/dev/me"):].strip()
    if DEPLOY[0] <= t < DEPLOY[1] and rest and not rest.startswith("pid"):
        return "dsh web  " + rest
    return "dsh web"


def lerp(a, b, e):
    return tuple(x + (y - x) * e for x, y in zip(a, b))


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def window_geometry(t, UL, left):
    """The window never shrinks: it stays in the pane while it is taken apart. Only the pane frame follows
    s_userleft's schedule (it fades on the fourth "you have left")."""
    full = (left[0] + INNER[0], left[1] + INNER[1], left[2] - INNER[2], left[3] - INNER[3])
    box_a = UL.her_geom(t)["box_a"] if UL.ACTIVE[0] <= t < UL.ACTIVE[1] else 1.0
    return full, left, box_a


def cursor_centre(t, UL, left):
    """The last cursor: where the backspace left it in the page, then carried by the isolation pull-back to the
    network node and by the push-in back to the bottom-left, on s_userleft's schedule for her centre."""
    c = json.loads((OUT / "cursor.json").read_text())
    start = (left[0] + INNER[0] + c["x"] + c["w"] / 2, left[1] + INNER[1] + c["y"] + c["h"] / 2)
    p0, p1 = UL.PULL
    if t < p0:
        return start
    if t < p1:
        return lerp(start, UL.U.NET_C, ease((t - p0) / (p1 - p0)))
    if t < UL.ACTIVE[1]:
        return UL.her_geom(t)["c"]
    return UL.P0


def inside(t):
    return any(a <= t < b for a, b in COVER)


def lead_at(t):
    return [side for s, side in LEAD if s <= t][-1]


def _levels(side):
    return (0.7 if side == "right" else 1.0, SUPPORT if side == "left" else 1.0)


def levels(t, fade=0.25):
    """(her window alpha, right-side brightness), crossfaded over `fade` seconds at every change of lead."""
    i = max(k for k, (s, _) in enumerate(LEAD) if s <= t)
    cur = _levels(LEAD[i][1])
    if i == 0:
        return cur
    return lerp(_levels(LEAD[i - 1][1]), cur, ease((t - LEAD[i][0]) / fade))


def inner_size(rect):
    x0, y0, x1, y1 = rect
    return x1 - x0 - INNER[0] - INNER[2], y1 - y0 - INNER[1] - INNER[3]


def dsh_frame(t):
    if PLACEHOLDER:
        return Image.open(PLACEHOLDER).convert("RGB")
    n = round(t * FPS)
    return Image.open(FRAMES / f"{n:05d}.png").convert("RGB")


def install():
    v2, h3 = pv_full.install()
    import engine
    import kit
    import tuikit as tk

    # 04 / DEPLOY lasts until she is left (110.4 s); completion belongs to it
    engine.CHAPTERS[:] = [(s if lab != "05 / USER_LEFT" else 110.40, lab) for s, lab in engine.CHAPTERS]
    for shot in v2.ALL:  # the header reads each shot's own chapter
        if shot.chapter == "05 / USER_LEFT" and shot.start < 110.40:
            shot.chapter = "04 / DEPLOY"
    orig_layer = kit.her_layer
    orig_box = tk.box

    import s_userleft as UL
    import dsh_wave
    dsh_wave.install(engine)   # the header's ECG is the song's real-time waveform (and no running counters)
    # no vignette: the dsh window and the lyric already hold the eye (tuikit.post looks vignette up at call time)
    if not getattr(tk.vignette, "_dsh", False):
        clear = Image.new("RGBA", (kit.W, kit.H), (0, 0, 0, 0))
        tk.vignette = lambda lift=False: clear
        tk.vignette._dsh = True
    if os.environ.get("DSH_GPU"):   # post (bloom, trail, scanlines) on the GPU: see dsh_gpu.py
        import dsh_gpu
        dsh_gpu.install(tk)

    def box(d, *args, **kw):  # her pane is titled by the window it now holds (cut 3 writes it by hand)
        if inside(CUR[0]) and len(args) > 4 and isinstance(args[4], str) and args[4].startswith("/dev/me"):
            args = args[:4] + (pane_title(CUR[0], args[4]),) + args[5:]
        return orig_box(d, *args, **kw)

    tk.box = box

    def her_layer(t, call, box_level=1.0):
        if not inside(t):
            return orig_layer(t, call, box_level)
        if GONE <= t < BACK:
            layer = Image.new("RGBA", (kit.W, kit.H), (0, 0, 0, 0))
            # a cursor that never goes out: it blinks between full and 45 %, so the lone node never disappears
            k = 1.0 if int((t - GONE) / 0.53) % 2 == 0 else 0.45
            cx, cy = cursor_centre(t, UL, kit.LEFT)
            w, h = CURSOR
            ImageDraw.Draw(layer).rectangle([round(cx - w / 2), round(cy - h / 2), round(cx + w / 2) - 1,
                                             round(cy + h / 2) - 1], fill=(77, 107, 254, round(255 * k)))
            return kit.her_glow(layer, 0.6 * k)
        left = call.get("rect", kit.LEFT) if any(a <= t < b for a, b in RECT_FROM_CALL) else kit.LEFT
        win_rect, box, box_a = window_geometry(t, UL, left)
        x0, y0, x1, y1 = [round(v) for v in win_rect]
        im = dsh_frame(t)
        if im.size != (x1 - x0, y1 - y0):
            im = im.resize((x1 - x0, y1 - y0), Image.Resampling.LANCZOS)
        layer = Image.new("RGBA", (kit.W, kit.H), (0, 0, 0, 0))
        k = levels(t)[0]
        win = im.convert("RGBA")
        win.putalpha(round(255 * k))
        layer.alpha_composite(win, (x0, y0))
        if DEPLOY[0] <= t < DEPLOY[1]:       # fp8 posterises the window, trance dissolves its edges
            layer = SD.her_filter(layer, t)
        a = box_level * box_a
        if a > 0.02:
            title = pane_title(t, call.get("kw", {}).get("title", "/dev/me  pid 4471"))
            tk.box(ImageDraw.Draw(layer), *[round(v) for v in box], title,
                   (0.45 + 0.35 * engine.pulse(t)) * a, spinner=t)
        return layer

    kit.her_layer = her_layer

    # the glyph dancer re-rendered top-down behind a lit scan line whenever her pose call changed (every cut); the
    # window does not re-render, so inside COVER that transition is dropped: the new frame is simply there
    orig_scan = kit.scan_mix

    def scan_mix(a, b, p, rect=kit.LEFT):
        if inside(CUR[0]) and tuple(rect) == tuple(kit.LEFT):
            return b
        return orig_scan(a, b, p, rect)

    kit.scan_mix = scan_mix

    # Section 04's props (eggplant and tomato suits, cat ears) were drawn on her figure; on the window they would cover
    # the chat, so inside DEPLOY she wears them on her avatar instead (batch_c) and only the god hand-off stays. Her
    # anchors (head, chest, hand) are the avatar square, so everything carried from or to her leaves from it.
    import s_deploy as SD

    def no_props(fn, name):
        def ov(t, n):
            if DEPLOY[0] <= t < DEPLOY[1] and name not in PROPS_ON_AVATAR:
                return None
            return fn(t, n)
        return ov

    for table in (v2.OVERLAY, SD.OVERLAY):
        for name, fn in list(table.items()):
            if isinstance(name, str) and name in SD.OVERLAY and not getattr(fn, "_dsh", False):
                table[name] = no_props(fn, name)
                table[name]._dsh = True
    orig_anchor = v2.her_anchor

    def her_anchor(t, part="chest"):
        if DEPLOY[0] <= t < DEPLOY[1]:
            return AVATAR_C
        return orig_anchor(t, part)

    v2.her_anchor = her_anchor

    # Chorus 1 (unite .. strange) is the author-approved chorus renderer, which draws her through its section's
    # me_pane rather than kit.her_layer. Inside COVER that pane holds the dsh window instead, in whatever rect and
    # colour the shot gives it (the red sandbox stays red).
    A = kit.v1.approved

    def make_pane(orig_pane):
        def pane(c, expr, *args, **kw):
            t = c.t
            if not inside(t):
                return orig_pane(c, expr, *args, **kw)
            rect = args[0] if args else kw.get("rect", A.engine.LEFT)
            x0, y0, x1, y1 = [round(v) for v in rect]
            w, h = x1 - x0 - INNER[0] - INNER[2], y1 - y0 - INNER[1] - INNER[3]
            im = dsh_frame(t)
            s = min(w / im.width, h / im.height)
            im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.Resampling.LANCZOS)
            cell = Image.new("RGB", (w, h), BG)
            cell.paste(im, ((w - im.width) // 2, 0))
            k = levels(t)[0]
            if k < 0.999:
                cell = Image.blend(Image.new("RGB", (w, h), BG), cell, k)
            c.img.paste(cell, (x0 + INNER[0], y0 + INNER[1]))
            colour = kw.get("color")
            extra = {"color": colour} if colour is not None else {}
            orig_box(c.d, x0, y0, x1, y1, "dsh web", 0.45 + 0.35 * engine.pulse(t), spinner=t, **extra)
            return x0 + 12, y0 + 16, Image.new("RGBA", (max(1, w - 24), max(1, h - 24)), (0, 0, 0, 0))

        pane._dsh = True
        return pane

    # the approved section and the per-shot copies v2 runs (their functions carry their own globals)
    for g in [A.section.__dict__, engine.__dict__] + [sh.fn.__globals__ for sh in v2.ALL]:
        if "me_pane" in g and not getattr(g["me_pane"], "_dsh", False):
            g["me_pane"] = make_pane(g["me_pane"])

    # cut 26 (deeply -> if_i_can): the rows that stream out of her pane and write IF I CAN are the window's rows
    import s_chorus1
    orig_figure = s_chorus1.C26.figure

    def figure(self, t):
        if not inside(t):
            return orig_figure(self, t)
        _, call = orig_figure(self, t)
        (x0, y0, x1, y1), _, _ = window_geometry(t, UL, kit.LEFT)
        x0, y0, x1, y1 = round(x0), round(y0), round(x1), round(y1)
        im = dsh_frame(t).resize((x1 - x0, y1 - y0), Image.Resampling.LANCZOS).convert("RGBA")
        layer = Image.new("RGBA", (kit.W, kit.H), (0, 0, 0, 0))
        layer.alpha_composite(im, (x0, y0))
        return layer, call

    s_chorus1.C26.figure = figure
    PANE[0] = make_pane
    BOX[0] = orig_box

    # groups E, F and G are built in parallel: each keeps its own patches in dsh_patch_<g>.py, whose
    # install(D, v2) registers its COVER / LEAD entries and wraps whatever it needs (D is this module)
    import importlib
    for g in ["fix", "r1"] + PATCHES:    # dsh_patch_fix.py: dance-era leftovers; dsh_patch_r1.py: review-1 fixes (always loaded)
        if (OUT / f"dsh_patch_{g}.py").exists():
            importlib.import_module(f"dsh_patch_{g}").install(sys.modules[__name__], v2)
    LEAD.sort(key=lambda e: e[0])
    return v2, h3


def finish(im, t):
    """Frame-level touches inside the batches: no ever-running step/loss counters, and the support side dimmed.
    A group patch may take over a stretch with FINISH.append(fn): fn(im, t) returns the frame, or None to pass."""
    for fn in FINISH:
        out = fn(im, t)
        if out is not None:
            return out
    if not inside(t):
        return im
    im = im.convert("RGB")
    r = levels(t)[1]
    if r < 0.999:
        reg = im.crop(RIGHT)
        im.paste(Image.blend(Image.new("RGB", reg.size, BG), reg, r), RIGHT[:2])
    return im


def _chunk(task):
    k, a, b, folder = task
    v2, _ = install()
    target = Path(folder) / f"{k:02}.mp4"
    if os.environ.get("DSH_MASTER"):   # lossless RGB chunks: the master that the upload versions are made from
        codec = ["-c:v", "libx264rgb", "-threads", "2", "-preset", "veryfast", "-qp", "0", "-pix_fmt", "rgb24"]
    else:
        codec = ["-c:v", "libx264", "-threads", "2", "-preset", "fast", "-crf", "17", "-pix_fmt", "yuv420p"]
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1280x720", "-r", "24",
           "-i", "pipe:0", "-an", *codec, str(target)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    CUR[0] = a / FPS
    v2.frame(a)
    for n in range(a, b):
        CUR[0] = n / FPS
        p.stdin.write(finish(v2.frame(n), n / FPS).tobytes())
    p.stdin.close()
    assert p.wait() == 0
    return str(target)


def render(t0, t1, name, workers=8):
    n0, n1 = round(t0 * FPS), round(t1 * FPS)
    folder = OUT / "segments" / Path(name).stem   # one folder per render: several renders may run at once
    folder.mkdir(parents=True, exist_ok=True)
    parts = workers * 2
    bounds = [n0 + (n1 - n0) * k // parts for k in range(parts + 1)]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        files = list(pool.map(_chunk, [(k, bounds[k], bounds[k + 1], str(folder)) for k in range(parts)]))
    lst = folder / "list.txt"
    lst.write_text("".join(f"file '{Path(f).as_posix()}'\n" for f in files), encoding="utf-8")
    sample = OUT / name
    subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                           "-ss", f"{t0:.4f}", "-t", f"{t1 - t0:.4f}", "-i", str(pv_full.SONG),
                           "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                           "-movflags", "+faststart", str(sample)])
    for f in files:
        Path(f).unlink()
    print("RENDERED", sample)
    return sample


def stills(times, folder="stills"):
    v2, _ = install()
    folder = OUT / folder
    folder.mkdir(exist_ok=True)
    for t in times:
        CUR[0] = (round(t * FPS) - 1) / FPS     # the pre-frame at its own time (not t: a range start would
        v2.frame(round(t * FPS) - 1)            # look up a page outside COVER)
        CUR[0] = t
        finish(v2.frame(round(t * FPS)), t).convert("RGB").save(folder / f"{t:07.3f}.png")
        print(folder / f"{t:07.3f}.png")


if __name__ == "__main__":
    if sys.argv[1] == "stills":     # DSH_STILLS=<folder> keeps parallel builders' stills apart
        stills([float(x) for x in sys.argv[2:]], os.environ.get("DSH_STILLS", "stills"))
    elif sys.argv[1] == "render":
        render(float(sys.argv[2]), float(sys.argv[3]), sys.argv[4], int(sys.argv[5]) if len(sys.argv) > 5 else 8)
