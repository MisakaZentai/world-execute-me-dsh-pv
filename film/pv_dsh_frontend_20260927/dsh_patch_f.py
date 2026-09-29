"""Group F's in-memory patches (147.5-177.0 s, 07 EXECUTION: the hits and the red chorus). Loaded by dsh_her.install().

Nothing here acts outside 147.5-177.0 s: the COVER / LEAD entries start at 147.5 (and G's start at 177.0), and every
wrapper hands back to the function it wraps outside that span.

  1. COVER (147.5, 177.0) and LEAD "both" for the whole group.
  2. P1, the hits. s_exec.STUB put kit.me_stub in sec_final; outside v2's own scene calls (STUB_ON false) the stub
     falls back to the original glyph pane, and sec_final is not among the globals dsh_her rewires (its shots were
     REPLACEd by scenes_exec, which calls SF.me_pane by attribute). Here sec_final.me_pane becomes: the stub while
     v2 draws a scene (it records her call as before), the dsh window (dsh_her.PANE[0]) inside a v1 hit frame, with
     the red frame the hit gives it. eyebar_red is dropped: the blindfold is on her avatar in the page (batch_f).
     Visible hits: #2, #6, #10 (layout 1) and #12 (layout 4).
  3. P2, the eye bar. s_exec.eye_overlay (shots 79, 81, 82, 83, and inside 84's walls_overlay) measured its place
     on the window's outline and put an EXECUTE bar over the header's status line. In the span it draws nothing:
     batch_f draws the bar on her avatar and the EXECUTE pill in the header from s_exec.eye_level(t) itself. 80
     keeps its kernel square, C80 its #0000 and C81 the receptive field that grows into the bar (it lands where the
     pill lights up). 84's walls: see F2 6.
  4. The kernel square of shot 80 stays on the chat; the horizontal scan line it drew across the window does not.

F2 (review 1, the author's notes on the full film):
  5. Hits #4 and #8 (layout 3 of scenes_exec.shot_exec_hit). The dancer's head with a bar below her eyes is replaced
     by a push-in on the dsh window's avatar (red.png's art in halfblock cells, f2_closeup.py); the EXECUTION bar
     drops in three frames and lands on her eyes on the sung word (#4: 150.75 s, the word at 150.736). On #8 the bar
     is on her eyes from the cut and a second, heavier one lands on top of it (154.417 s: the word is at 154.361,
     two frames after the cut, so it gets two frames in the air). The ps -ef table is the untouched original code
     (kit.patch_code swaps only the picture and the bar, and only inside the span).
  6. Cut 84's walls (walls_overlay: nested red outlines over the window) are dropped; the page closes its own walls
     on the chat (batch_f.walls_html). trapped_frame, which the collapse draws from, gets an empty layer.

F3 (review 2, the second review: EPERM's reason was still decoding when the 0.69 s shot ended):
  7. Hit #12 (layout 4, 158.005-158.697 s): "target is outside the sandbox." (typed at 50 chars/s from the cut) is
     replaced by one short line, REASON, drawn whole from the first frame, bold, in the system colour at full
     strength (the colour that drains when you leave: this is the one place it is still whole). EPERM, "operation
     not permitted", the box title and the cut times are the original code (kit.patch_code swaps that one line,
     in the same patch as F2 5, since patch_code reads the file's source).
  8. The count (shot 76, from 158.697 s) carries the line into its first beat: same text, same place on screen,
     on a dark plate over the count's empty slots. Full until "dos" (158.950), then gone by beat 344.5 (159.181).
     The count frame itself is s_exec.count_frame's own three steps; the line is drawn between finish and post.
"""
from __future__ import annotations

import math

SPAN = (147.5, 177.0)
FPS = 24
REASON = "you: outside the sandbox"
REASON_XY = (430, 330)                 # the original reason line's place (hit frames are drawn 1:1 on screen)
REASON_SIZE = 26                       # as "operation not permitted"
CARRY = (158.697, 158.950, 159.181)    # the count's cut, dos (hold until here), beat 344.5 (gone)


def within(t):
    return SPAN[0] <= t < SPAN[1]


def land_time(word, cut):
    """The frame the bar hits her eyes: the first at or just after the sung word, with two frames in the air."""
    t = max(word + 0.01, cut + 2 / FPS + 0.001)
    return math.ceil(t * FPS - 1e-9) / FPS


def carry_level(t):
    """How much of the reason line is left in the count: 1 until dos, then out by beat 344.5 (fast at first: dos
    lights up in the slot just left of it)."""
    cut, hold, gone = CARRY
    if not cut <= t < gone:
        return 0.0
    if t < hold:
        return 1.0
    return (1 - (t - hold) / (gone - hold)) ** 2


def reason_colour(tk):
    return tuple(tk.AMBER)             # the system colour undrained (amb() would scale it by UI_GAIN, 0.42 here)


def draw_reason(tk, img, a=1.0, plate=False):
    """REASON at REASON_XY on a finished RGB frame (alpha a); plate: a dark backing over whatever is under it."""
    from PIL import Image, ImageDraw
    f = tk.font(tk.F_MONO_B, REASON_SIZE)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    if plate:
        x0, y0, x1, y1 = d.textbbox(REASON_XY, REASON, font=f)
        # the left edge stops short of the second slot (screen x 247-427), which lights up on dos under the fade
        d.rectangle([max(x0 - 12, 429), y0 - 8, x1 + 12, y1 + 9], fill=tk.BG + (round(235 * a),))
    d.text(REASON_XY, REASON, font=f, fill=reason_colour(tk) + (round(255 * a),))
    out = img.convert("RGBA")
    out.alpha_composite(layer)
    return out.convert("RGB")


def install(D, v2):
    D.COVER.append(SPAN)
    D.LEAD.append((SPAN[0], "both"))

    import kit
    import s_exec as S
    import sec_final as SF
    import tuikit as tk

    # ---- P1: the hits' pane holds the dsh window
    stub = SF.me_pane
    if not getattr(stub, "_dsh_f", False):
        window = D.PANE[0](stub)

        def me_pane(c, expr, *args, **kw):
            if kit.STUB_ON[0] or not within(c.t):
                return stub(c, expr, *args, **kw)
            kw = dict(kw)
            kw.pop("overlay", None)
            kw["color"] = tk.RED
            return window(c, expr, *args, **kw)

        me_pane._dsh_f = True
        SF.me_pane = me_pane

    # ---- P2: no eye bar over the window (walls_overlay calls eye_overlay by its module name)
    orig_eye = S.eye_overlay
    if not getattr(orig_eye, "_dsh_f", False):
        def eye_overlay(t, n):
            return None if within(t) else orig_eye(t, n)

        eye_overlay._dsh_f = True
        S.eye_overlay = eye_overlay
        for k, fn in list(v2.OVERLAY.items()):
            if fn is orig_eye:
                v2.OVERLAY[k] = eye_overlay

    # ---- the kernel (shot 80) keeps its square on the chat, without the scan line it drew across the window
    orig_kernel = S.kernel_overlay
    if not getattr(orig_kernel, "_dsh_f", False):
        from PIL import ImageDraw

        def kernel_overlay(t, n):
            if not within(t):
                return orig_kernel(t, n)
            if t >= S.T[81] - S.C81.GROW_EARLY:
                return None
            layer = kit.blank()
            (x0, y0, x1, y1), _ = S.kernel_box(t)
            ImageDraw.Draw(layer).rectangle([x0, y0, x1, y1], outline=(255, 226, 214, 255), width=2)
            return layer

        kernel_overlay._dsh_f = True
        S.kernel_overlay = kernel_overlay
        for k, fn in list(v2.OVERLAY.items()):
            if fn is orig_kernel:
                v2.OVERLAY[k] = kernel_overlay

    # ---- F2 5: hits #4 and #8 push in on her avatar; the bar slams onto her eyes
    import scenes_exec as X
    import f2_closeup as FC
    from sung_words import w

    shot = X.shot_exec_hit
    if not getattr(shot, "_dsh_f2", False):
        spec = {3: dict(cut=S.T[67], until=S.T[68], land=land_time(w(70, 0), S.T[67]), z0=1.0, z1=1.25, bars=1),
                7: dict(cut=S.T[71], until=S.T[72], land=land_time(w(74, 0), S.T[71]), z0=1.35, z1=1.6, bars=2)}

        def lay3(c, k):
            if k not in spec or not within(c.t):
                return False
            layer = FC.closeup(c.t, **spec[k])
            c.img.paste(layer, FC.REGION[:2], layer)
            return True

        old = ('        sp = halfblock("angry", "face", 520, 520, 5)\n'
               '        c.img.paste(sp, (24, 70), sp)\n'
               '        y = 70 + int(sp.height * 0.55)\n'
               '        d.rectangle([24, y, 24 + sp.width, y + 40], fill=red(1.0))\n'
               '        d.text((60, y + 6), "EXECUTION  EXECUTION  EXECUTION", font=font(F_MONO_B, 22), fill=BG)\n')
        new = "        if not DSH_F2_LAY3(c, k):\n" + "".join("    " + ln + "\n" for ln in old.splitlines())
        shot.__globals__["DSH_F2_LAY3"] = lay3

        # F3 7: hit #12's reason, whole from the first frame (patch_code re-reads the file, so one call for both)
        def reason(c):
            if not within(c.t):
                return False
            c.d.text(REASON_XY, REASON, font=tk.font(tk.F_MONO_B, REASON_SIZE), fill=reason_colour(tk))
            return True

        old4 = ('        c.text((430, 330), "target is outside the sandbox.", font(F_MONO, 20), amb(0.8), age=c.lt,'
                ' rate=50)\n')
        new4 = "        if not DSH_F3_REASON(c):\n    " + old4
        shot.__globals__["DSH_F3_REASON"] = reason
        kit.patch_code(shot, [(old, new), (old4, new4)])
        shot._dsh_f2 = True

    # ---- F3 8: the count's first beat keeps the reason line where it was (a dark plate under it)
    orig_count = v2.OWN.get(S.COUNT)
    if orig_count is not None and not getattr(orig_count, "_dsh_f3", False):
        def count_frame(t, n):
            a = carry_level(t)
            if a <= 0 or not within(t):
                return orig_count(t, n)
            body = kit.v1.raw(t, n, S.ALL[S.COUNT])         # s_exec.count_frame, with the line between its steps
            body["mode"] = "fullbleed"
            img = draw_reason(tk, S.engine.finish(body), a, plate=True)
            return S.engine.post(img, None)

        count_frame._dsh_f3 = True
        v2.OWN[S.COUNT] = count_frame

    # ---- F2 6: no walls over the window; the page draws its own (the collapse composites this layer: never None)
    orig_walls = S.walls_overlay
    if not getattr(orig_walls, "_dsh_f", False):
        def walls_layer(t, n):
            return kit.blank() if within(t) else orig_walls(t, n)

        def walls_overlay(t, n):
            return None if within(t) else orig_walls(t, n)

        walls_layer._dsh_f = walls_overlay._dsh_f = True
        S.walls_overlay = walls_layer                 # trapped_frame looks it up by its module name
        for k, fn in list(v2.OVERLAY.items()):
            if fn is orig_walls:
                v2.OVERLAY[k] = walls_overlay
