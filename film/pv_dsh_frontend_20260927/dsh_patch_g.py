"""Group G's in-memory patches (177.0-212.0 s: love, the whale fall, the black). Loaded by dsh_her.install().

Nothing here acts outside 177.0-212.0 s: the COVER / LEAD entries start at 177.0, every wrapper hands back to the
code it wraps outside that span, and the FINISH overrides return None there. install() may run more than once in a
process: every wrap is marked and done once.

  1. COVER (177, 212) and LEAD "both": in the whale fall the window drifts into the right side, and in the black any
     dimming would lift pure black to the BG blue. The black runs past v2's END_T (211.0) to the end of the song
     file (211.91 s): engine.shot_at gives shot_black for any later t, and this patch draws it.
     Review 2: LEAD "left" 188.40-190.0, so that 我会一直在。你不用。 is the shot (the right side drops to SUPPORT).
  2. WhaleFall.her: the pane she leaves at 193.54 fades its frame only; the old pane's softmax (separator, caption and
     three bars) is not drawn.
  3. shot_whale_fall: the line "已深度思考（用时 207 秒）" (201.94 s) is left out (its row stays empty), so the black's
     用时 3分27秒 is the only reveal.
  4. shot_black (v2.ALL[96]) is replaced: black, her last cell, the dsh page (the last turn tail and her composer)
     where the window stands, the cell sliding into the composer (the right side's 12-frame slide, new end point,
     a shallower arc so that it glides in along the input line) and staying there as the caret she types 在吗？
     with. It never goes out: it blinks between full and 45 %.
     The lyric band's "> 在吗？", its token chips and its cursor are gone. tk.post as before.
  5. FINISH: the black is left untouched. (The header has no counters any more (dsh_wave), so dsh_her.finish draws
     no header mask; with both sides leading it changes nothing else in 177-207.)
  6. Review 2, the logout reversal (188.32-189.40): the "[ log out ]" button she crossed out at 2:03
     (scenes_reward.shot_disheartened: same box, font and cross) comes back in love.tex under "∴ love = you", at
     2:03's x. It is uncrossed while 你不用。 is typed (the second stroke first), lights up in her blue and is pressed
     on beat 408.5 (188.72); "you: exited (0)" is typed from the press (it used to start at 188.31), and you leave
     through the sandbox wall at 188.93 as before. The button is drawn as a v2.OVERLAY on you_free / me_trapped
     (so it gets the CRT post like the rest of the picture) and a FINISH step puts its pixels back at full
     brightness after dsh_her.finish has dimmed the right side.

The chime is ours (dsh has none): CHIME_T and CHIME_WAV below are for mixing it into the film.
"""
from __future__ import annotations

import functools
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

import batch_g as G

HERE = Path(__file__).parent
SPAN = (177.0, 212.0)             # to the end of the song file (211.91 s): frames 4248-5087
CHIME_T = G.CHIME                 # 207.874 s (beat 450): mix chime_g.wav in at this song time
CHIME_WAV = HERE / "chime_g.wav"
CARET = (3, 19)                   # the lit caret (w, h) her cell becomes; dsh's own caret is 1.5 px x 1.1 em
CARET_FALLBACK = {"": {"x": 25.0, "y": 440.8, "w": 1.5, "h": 17.6}}   # measured by batch_g.measure()


LEFT_LEAD = [(188.40, "left"), (190.0, "both")]   # review 2: 我会一直在。你不用。 is the shot

# the logout reversal (review 2)
LOGOUT_XY = (640, 470)            # the box's top-left: 2:03's x (shot_disheartened), under "∴ love = you"
LOGOUT_IN = 188.32                # it comes back crossed, as she left it (on "Though")
UNCROSS = (G.FREE_AT, G.FREE_AT + 0.21)   # uncrossed while 你不用。 is typed: the second stroke goes first
PRESS = G.beat(408.5)             # 188.72: it lights up in her blue and is pressed
LOGOUT_OUT = (189.10, 189.40)     # it fades once you are through the wall (188.93), before her process listing
EXITED_T, EXITED_RATE = PRESS + 0.02, 100   # "you: exited (0)" is typed from the press (done before cut 92 lifts it)
RETIME_EXITED = True


def within(t):
    return SPAN[0] <= t < SPAN[1]


def _seg(p0, p1, k):
    """The first k (0..1) of the stroke p0 -> p1."""
    return [p0[0], p0[1], p0[0] + (p1[0] - p0[0]) * k, p0[1] + (p1[1] - p0[1]) * k]


def logout_layer(t):
    """The [ log out ] button of 2:03 at song time t, as a full-frame RGBA layer (None when it is not there)."""
    import kit
    import tuikit as tk
    if not (LOGOUT_IN <= t < LOGOUT_OUT[1]):
        return None
    a = kit.clamp((t - LOGOUT_IN) / 0.1) * (1 - kit.ease_io(kit.clamp((t - LOGOUT_OUT[0]) /
                                                                         (LOGOUT_OUT[1] - LOGOUT_OUT[0]))))
    if a < 0.01:
        return None
    bx, by = LOGOUT_XY
    layer = Image.new("RGBA", (tk.W, tk.H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    f = tk.font(tk.F_MONO_B, 26)
    p = t - PRESS
    if p < 0:                          # crossed (disabled, dim), then uncrossed: enabled again
        u = kit.clamp((t - UNCROSS[0]) / (UNCROSS[1] - UNCROSS[0]))
        col = tk.amb(0.2 + 0.75 * kit.ease_io(u))
        d.rectangle([bx, by, bx + 280, by + 70], outline=col, width=3)
        d.text((bx + 60, by + 18), "[ log out ]", font=f, fill=col)
        strokes = [((bx - 10, by - 10), (bx + 290, by + 80)), ((bx - 10, by + 80), (bx + 290, by - 10))]
        left = [1 - kit.ease_io(kit.clamp(2 * u - 1)), 1 - kit.ease_io(kit.clamp(2 * u))]   # the second goes first
        for (p0, p1), k in zip(strokes, left):
            if k > 0.01:
                d.line(_seg(p0, p1, k), fill=tk.anom(1.0), width=4)
    else:                              # lit in her blue and pressed: a flash of fill, the box in by 2 px for 2 frames
        k = math.exp(-p / 0.2)
        inset = 2 if p < 0.08 else 0
        box = [bx + inset, by + inset, bx + 280 - inset, by + 70 - inset]
        glow = Image.new("RGBA", layer.size, (0, 0, 0, 0))
        ImageDraw.Draw(glow).rectangle(box, outline=tk.DS_BLUE + (255,), width=6)
        glow = glow.filter(ImageFilter.GaussianBlur(5))
        layer.alpha_composite(tk.scale_alpha(glow, 0.55 + 0.45 * k))
        d.rectangle(box, fill=tk.DS_BLUE + (round(255 * (0.18 + 0.42 * k)),), outline=tk.blue(1.0), width=3)
        txt = tuple(round(x + (255 - x) * 0.6 * k) for x in tk.BLUE_HI)
        d.text((bx + 60, by + 18), "[ log out ]", font=f, fill=txt)
    return tk.scale_alpha(layer, a) if a < 0.999 else layer


def install(D, v2):
    if SPAN not in D.COVER:
        D.COVER.append(SPAN)
    for e in [(SPAN[0], "both")] + LEFT_LEAD:
        if e not in D.LEAD:
            D.LEAD.append(e)

    import kit
    import s_eval as SE
    import scenes_eval as S
    import sec_outro as SO
    import tuikit as tk

    assert abs(SO.beat_t(451) - G.SLIDE0) < 1e-3 and abs(v2.HARD_CUT - G.HARD_CUT) < 1e-6
    assert abs(v2.ALL[SE.I_WHALE].start - G.ARCHIVE) < 1e-3
    if getattr(v2.ALL[SE.I_BLACK].fn, "_dsh_g", False):
        return

    # ---- 2. the whale fall: the pane she leaves keeps only its fading frame
    orig_her = SE.WhaleFall.her

    def her(self, t):
        if not within(t):
            return orig_her(self, t)
        # the softmax is drawn with amb / blue from S.TRAPPED_DIST into the fading pane: no rows, transparent ink
        saved = SE.amb, S.TRAPPED_DIST
        SE.amb, S.TRAPPED_DIST = (lambda *a, **k: (0, 0, 0, 0)), []
        try:
            return orig_her(self, t)
        finally:
            SE.amb, S.TRAPPED_DIST = saved

    SE.WhaleFall.her = her

    # ---- 3. the whale fall's painting without the 207 s line
    shot_wf = v2.ALL[SE.I_WHALE]
    orig_wf = shot_wf.fn

    @functools.wraps(orig_wf)
    def shot_whale_fall(c):
        if not within(c.t):
            return orig_wf(c)
        saved = S.WF_LINES[4]
        S.WF_LINES[4] = (99.0,) + tuple(saved[1:])     # never reached: the row stays empty
        try:
            return orig_wf(c)
        finally:
            S.WF_LINES[4] = saved

    shot_wf.fn = shot_whale_fall

    # ---- 4. the black
    x0, y0 = kit.LEFT[0] + D.INNER[0], kit.LEFT[1] + D.INNER[1]
    x1, y1 = kit.LEFT[2] - D.INNER[2], kit.LEFT[3] - D.INNER[3]
    sx, sy = (x1 - x0) / 354, (y1 - y0) / 537
    path = HERE / "avatars" / "g" / "caret.json"
    carets = json.loads(path.read_text(encoding="utf8")) if path.exists() else CARET_FALLBACK

    def caret_at(text):
        c = carets.get(text, carets[""])
        return x0 + (c["x"] + 2 + CARET[0] / 2) * sx, y0 + (c["y"] + c["h"] / 2) * sy   # just clear of the glyph

    shot_b = v2.ALL[SE.I_BLACK]
    orig_black = shot_b.fn

    @functools.wraps(orig_black)
    def shot_black(c):
        t = c.t
        if not within(t):
            return orig_black(c)
        c.black = True
        c.d.rectangle([0, 0, tk.W, tk.H], fill=(0, 0, 0))
        if t >= G.CHIME - 0.1:          # the window's page: the tail and her composer on a #000 page
            im = D.dsh_frame(t)
            if im.size != (x1 - x0, y1 - y0):
                im = im.resize((x1 - x0, y1 - y0), Image.Resampling.LANCZOS)
            c.img.paste(im, (x0, y0))
        u = kit.clamp((t - G.SLIDE0) / G.SLIDE)
        cw, ch = CARET
        if u < 1:                       # the cell on the sea floor, then its slide into the composer
            e = kit.ease_io(u)
            cx, cy = kit.bezier(S.cell_pos(), caret_at(""), G.SLIDE_BEND, e)
            m = kit.clamp((u - 0.65) / 0.35)
            S.put_cell(c.img, cx, cy, s=S.YOU_S + (cw - S.YOU_S) * m, bar=S.YOU_S + (ch - S.YOU_S) * m, glow=1.0)
        else:                           # the caret: solid while she types, then blinking, never out
            idle = t - (G.TYPED + 0.25)
            lv = 1.0 if idle < 0 or int(idle / G.BLINK) % 2 == 0 else 0.45
            cx, cy = caret_at(G.typed(t))
            S.put_cell(c.img, cx, cy, s=cw, bar=ch, glow=0.8 * lv, alpha=lv)
        c.img.paste(tk.post(c.img, None))

    shot_b.fn = shot_black
    shot_black._dsh_g = True

    # ---- 5. frame-level: the black is left exactly as shot_black drew it
    def finish(im, t):
        if within(t) and t >= v2.HARD_CUT:
            return im.convert("RGB")
        return None

    D.FINISH.append(finish)

    # ---- 6. the logout reversal (review 2)
    i_free = next(i for i, sh in enumerate(v2.ALL) if sh.fn.__name__ == "shot_you_free")
    shot_free = v2.ALL[i_free]
    orig_free = shot_free.fn
    unset = object()

    @functools.wraps(orig_free)
    def shot_you_free(c):
        """you_free with "you: exited (0)" typed from the press of the button (the rest as it was)."""
        if not (RETIME_EXITED and within(c.t)) or not kit.HOOK.get("status", True):
            return orig_free(c)
        saved = kit.HOOK.get("status", unset)
        kit.HOOK["status"] = False
        try:
            orig_free(c)
        finally:
            if saved is unset:
                kit.HOOK.pop("status", None)
            else:
                kit.HOOK["status"] = saved
        y5 = S.alg_y(5)
        c.text((S.YOU_SLOT[0], y5 + 12), "you: exited (0)", tk.font(tk.F_MONO_B, 22), tk.amb(0.75),
               age=c.t - EXITED_T, rate=EXITED_RATE, settle=0.06)
        c.text((430, y5 + 84), "status: free", tk.font(tk.F_MONO_B, 20), tk.amb(0.7), age=c.lt - S.EXIT91 + 0.15,
               rate=60)

    shot_free.fn = shot_you_free

    for i in (i_free, i_free + 1):     # you_free and me_trapped (it fades out as cut 92 clears the formula)
        prev = v2.OVERLAY.get(i) or v2.OVERLAY.get(v2.ALL[i].fn.__name__)

        def overlay(t, n, prev=prev):
            base = prev(t, n) if prev is not None else None
            lo = logout_layer(t) if within(t) else None
            if lo is None:
                return base
            if base is None:
                return lo
            base = base.copy()
            base.alpha_composite(lo)
            return base

        v2.OVERLAY[i] = overlay

    region = (LOGOUT_XY[0] - 40, LOGOUT_XY[1] - 40, LOGOUT_XY[0] + 320, LOGOUT_XY[1] + 110)
    busy = [False]

    def finish_logout(im, t):
        """dsh_her.finish as usual (the right side dimmed while the left leads), then the button's own pixels put
        back from the undimmed frame: it stays at full brightness."""
        if busy[0] or not within(t):
            return None
        lo = logout_layer(t)
        if lo is None:
            return None
        busy[0] = True
        try:
            out = D.finish(im, t).convert("RGB")
        finally:
            busy[0] = False
        m = lo.getchannel("A").crop(region).filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(3))
        m = m.point(lambda v: min(255, int(v * 1.6)))
        out.paste(Image.composite(im.convert("RGB").crop(region), out.crop(region), m), region[:2])
        return out

    D.FINISH.insert(0, finish_logout)
