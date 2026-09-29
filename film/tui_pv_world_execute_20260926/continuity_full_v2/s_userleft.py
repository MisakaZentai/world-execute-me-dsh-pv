"""Section 05 USER_LEFT (cuts 46-54, 103.1 - 119.7 s): the emotional turn.

The section opens with the whole interface (split pane, header, op ticker, lyric band frame) and, from "Though you
have left", every sung line takes exactly one layer away and never adds one:

  48  110.40  "Though you have left"   the chrome: header up, ticker right, band frame out; the bare shell prompt
                                        ('me@deepsea:~$ ping you') is what is left at the top
  49  111.98  "You have left"          the 'ping you' pane frame
  50  112.89  "You have left"          her expression softmax
  51  113.70  "You have left"          her size: she is re-rendered smaller into the bottom-left, her pane frame
                                        shrinking with her (the same frame, there from frame 0)
  52  114.75  "You have left"          her pane frame (4 frames); she stays there, small and frameless
  53  115.54  "... me in isolation"     camera: the world pulls back from her; her terminal becomes a small screen
                                        in a network, she is the node; every link goes dark, 'you' last
  54  117.85  "If I can"                camera: back into the node, which is now showing ls ~/memory/you/

The system colour drains from 110.4 s (engine.ui_gain, automatic). The ping rows are one thread from 110.47 to
117 s, the 'you' tile another (indexer -> completion -> ping target -> the 'you' peer whose link dies last).
She stays the same string dancer; from 113.6 s she is re-rendered at 0.45 of her size by scenes_userleft.figure
(her rig frame drawn with smaller cells, never a scaled bitmap) and she never grows back in this section.

Two framework functions are wrapped for this time range only (setup, idempotent; see FRAMEWORK below):
  kit.chrome     the staged shell retraction (SHELL cannot span five consecutive shots of the same scene, and its
                 prompt is typed by the retract value, which truncates a command past 11 characters)
  kit.her_layer  her softmax fade, her re-render at a smaller size, and her position during the two camera moves
"""
from __future__ import annotations

import math
import os
import random
import sys

from PIL import Image, ImageDraw

import cuts as C
import kit
import scenes_userleft as U
import sec_chorus2
import sec_verse2
from cuts import Cut, Frame, rgba, text_at
from kit import (FPS, H, W, bezier, blank, brighten, clamp, ease_back, ease_in, ease_io, ease_out, haloed, inward,
                 lerp, place, radial, reveal, sweep, tk)

STUB = [sec_chorus2, sec_verse2]
REPLACE = {f.__name__: f for f in (U.shot_feel_you, U.shot_completion, U.shot_you_left, U.shot_isolation,
                                   U.shot_memory_ls)}
SPLIT = set(REPLACE)
beat_t = kit.engine.beat_t
T46, T47, T48, T49, T50, T51, T52, T53, T54, T55 = (U.T46, U.T47, U.T48, U.T49, U.T50, U.T51, U.T52, U.T53, U.T54,
                                                     U.T55)

def ic(col) -> tuple:
    return tuple(int(v) for v in col[:3])


# ---------------------------------------------------------------- her geometry (one schedule for the section)

LEFT = kit.LEFT
PIP_S = 0.45                              # her size from cut 51 on
GRID_W, GRID_H = 350, 450                 # her rig grid in the full pane (70 x 45 cells of 5 x 10 px)
FULL_C = (29 + GRID_W / 2, 74 + GRID_H / 2)   # grid centre in the full pane (dancer.render placement)
P0 = (110.0, 598 - GRID_H * PIP_S / 2)    # grid centre in the bottom-left: feet on y = 598
PIP_BOX = (24, 372, 200, 604)             # her pane frame, shrunk with her
SOFT_OFF = (U.SUNG["left2"], 0.33)        # layer 3: her softmax
SHRINK = (T51 - 2 / FPS, beat_t(247))     # layer 4: 13 frames, landing on beat 247
FRAME_OFF = (U.SUNG["left4"], 4 / FPS)    # layer 5: her small frame
PULL = (T53 - 3 / FPS, beat_t(251))       # cut 53: the pull-back lands on beat 251
PUSH = (beat_t(254), T54)                 # cut 54: the push-in lands on beat 255 = the cut
Z1 = 0.2                                  # her terminal in the isolation view
SERIOUS = (T54 + 0.55, 0.3)               # in memory_ls she turns serious (re-rendered top-down in her rect)
SMALL_END = beat_t(259) + 1.0             # through reward's cut 55 (she is erased there, hidden in erase)
ACTIVE = (U.SUNG["left2"], SMALL_END)


def her_geom(t: float) -> dict:
    """Her size s (1 = the full pane), grid centre, pane frame rect and alpha, softmax alpha at time t."""
    g = dict(s=1.0, c=FULL_C, box=LEFT, box_a=1.0, soft=1.0 - ease_io((t - SOFT_OFF[0]) / SOFT_OFF[1]))
    if t < SHRINK[0]:
        return g
    e = ease_io((t - SHRINK[0]) / (SHRINK[1] - SHRINK[0]))
    g.update(s=lerp(1.0, PIP_S, e), c=lerp(FULL_C, P0, e), box=lerp(LEFT, PIP_BOX, e), soft=0.0)
    g["box_a"] = 1.0 - ease_io((t - FRAME_OFF[0]) / FRAME_OFF[1])
    if t >= PULL[0]:
        g["c"] = lerp(P0, U.NET_C, ease_io((t - PULL[0]) / (PULL[1] - PULL[0])))
    if t >= PUSH[0]:
        g["c"] = lerp(U.NET_C, P0, ease_io((t - PUSH[0]) / (PUSH[1] - PUSH[0])))
    return g


def cam_zoom(t: float) -> float:
    """Scale of her terminal on screen: 1 until the pull-back, Z1 in the isolation view, back to 1 at cut 54."""
    if t < PULL[0]:
        return 1.0
    if t < PUSH[0]:
        return Z1 ** ease_io((t - PULL[0]) / (PULL[1] - PULL[0]))
    return Z1 ** (1 - ease_io((t - PUSH[0]) / (PUSH[1] - PUSH[0])))


# ---------------------------------------------------------------- framework wrappers (this time range only)

_BASE = {}


def _her_small(t: float, call: dict, g: dict) -> Image.Image:
    layer = blank()
    s = g["s"]
    expr = call.get("expr", U.EXPR_SMALL)
    tint = call.get("kw", {}).get("tint", "blue")
    fig = U.figure(t, expr, s, tint)
    ox, oy = round(g["c"][0] - GRID_W * s / 2), round(g["c"][1] - GRID_H * s / 2)
    if t >= SERIOUS[0]:  # a new expression: re-rendered from the top down inside her own rect
        p = ease_io((t - SERIOUS[0]) / SERIOUS[1])
        new = U.figure(t, "serious", s, tint)
        if p >= 1:
            fig = new
        elif p > 0:
            y = round(fig.height * p)
            mix_ = fig.copy()
            mix_.paste(new.crop((0, 0, new.width, y)), (0, 0))
            ImageDraw.Draw(mix_).line([0, y, mix_.width, y], fill=tk.blue(0.9) + (160,))
            fig = mix_
    layer.paste(fig, (ox, oy), fig)
    if g["box_a"] > 0.01:
        title = call.get("kw", {}).get("title", "/dev/me  waiting")
        tk.box(ImageDraw.Draw(layer), *[round(v) for v in g["box"]], title,
               (0.45 + 0.35 * kit.engine.pulse(t)) * g["box_a"], spinner=t)
    return layer


def her_layer(t: float, call: dict, box_level: float = 1.0) -> Image.Image:
    base = _BASE["her_layer"]
    if not ACTIVE[0] <= t < ACTIVE[1] or os.environ.get("V2_HER", "h3") not in ("dancer", "hybrid", "h3"):
        return base(t, call, box_level)
    g = her_geom(t)
    if t < SHRINK[0]:
        layer = base(t, call, g["box_a"])
        if g["soft"] < 0.999:  # layer 3: the softmax under her fades out (only it: the frame stays)
            x0, y0, x1, y1 = LEFT
            region = (x0 + 9, y1 - 74, x1 - 9, y1 - 2)
            part = layer.crop(region)
            part.putalpha(part.getchannel("A").point(lambda v: int(v * max(0.0, g["soft"]))))
            layer.paste(part, region[:2])
        return layer
    return _her_small(t, call, g)


CMD_PING = (U.SUNG["left0"] + 0.15, "ping you")
CMD_LS = (beat_t(253) + 0.05, "ls -la ~/memory/you/")
CHROME = (U.SUNG["left0"], 0.3, T55, 0.3)  # retract from the sung onset; return after memory_ls like a SHELL shot


def retract(t: float) -> float:
    r = ease_out((t - CHROME[0]) / CHROME[1]) if t >= CHROME[0] else 0.0
    if t >= CHROME[2]:
        r *= 1 - ease_io((t - CHROME[2]) / CHROME[3])
    return r


def prompt(t: float) -> str:
    """The shell line under the retracted header: 'ping you' runs until she interrupts it and lists her memory."""
    if t < CMD_LS[0] - 0.14:
        t0, cmd = CMD_PING
    elif t < CMD_LS[0]:
        return f"me@deepsea:~$ {CMD_PING[1]}^C"
    else:
        t0, cmd = CMD_LS
    n = max(0, int((t - t0) * 50))
    return "me@deepsea:~$ " + cmd[:n]


def chrome(img, t, src, retract_=0.0, shell=None):
    base = _BASE["chrome"]
    if not CHROME[0] <= t < CHROME[2] + CHROME[3] + 0.05:
        return base(img, t, src, retract_, shell)
    e = retract(t)
    out = base(img, t, src, e, None)
    if e > 0.01:
        sh = blank()
        d = ImageDraw.Draw(sh)
        txt = prompt(t)
        typed = txt  # typed by prompt(); the block cursor follows it
        d.text((24, 12), typed, font=tk.font(tk.F_MONO_B, 18), fill=tk.blue(0.95))
        if int(t * 3) % 2 == 0 or len(txt) < 14 + 2:
            x = 24 + d.textlength(typed, font=tk.font(tk.F_MONO_B, 18)) + 3
            d.rectangle([x, 15, x + 9, 32], fill=tk.blue(0.8))
        d.text((W - 190, 14), f"{int(t // 60):02d}:{t % 60:04.1f} / 03:32", font=tk.font(tk.F_MONO, 14),
               fill=tk.amb(0.5))
        out.alpha_composite(tk.scale_alpha(sh, e))
    return out


def install() -> None:
    """Wrap kit.chrome and kit.her_layer once (setup() runs again when v2 is imported a second time)."""
    if not getattr(kit.chrome, "_userleft", False):
        _BASE["chrome"] = kit.chrome
        chrome._userleft = True
        kit.chrome = chrome
    if not getattr(kit.her_layer, "_userleft", False):
        _BASE["her_layer"] = kit.her_layer
        her_layer._userleft = True
        kit.her_layer = her_layer


def setup(v1) -> None:
    install()


# ---------------------------------------------------------------- cut 46: the trance collapses into 'you'

def _spiral_pos(i: int, phase: float):
    r = 8 + i * 1.6
    a = i * 0.35 + phase
    return 784 + r * math.cos(a), 320 + r * math.sin(a) * 0.85


class C46(Cut):
    """trance -> feel_you. On 'If I can' the temperature drops: the sampling spiral slows to a stop and its letters
    collapse to what they were sampling. Thirty-six of them become y, o, u and fall into the lightning indexer,
    three to a cell, spelling the twelve 'you' tiles; the rest pour into the keystroke line, which is drawn from
    left to right as they land. The old pane gives way outward from the spiral's eye; she re-forms (starry ->
    shy) on the cut."""
    pre, post = 0.36, 0.62
    LAND = beat_t(224)

    def _deploy(self):
        """The trance scene in use: s_deploy's version (its own temperature curve, a spiral_n hook) or the original."""
        sd = sys.modules.get("scenes_deploy")
        return sd if sd is not None and self.a.fn is getattr(sd, "shot_trance", None) else None

    def _temp(self, t):
        sd = self._deploy()
        if sd is not None:
            return sd.trance_temp(t)
        a = self.a
        u = clamp((t - a.start) / (a.end - a.start))
        return 0.6 + 2.4 * (1 - (1 - u) ** 3)

    def phase(self, t):
        """The spiral's angle: the original speed until the lift, then a linear slow-down to a stop at T."""
        t0 = self.T - self.pre
        w0 = 1.5 + self._temp(t0)
        if t <= t0:
            return t * (1.5 + self._temp(t))
        dt = min(t, self.T) - t0
        return t0 * w0 + w0 * (dt - dt * dt / (2 * self.pre))

    def letters(self):
        if hasattr(self, "_letters"):
            return self._letters
        T = self.T
        ph = self.phase(T)
        rng = random.Random(46)
        pool = "youmestayloveseadeep"
        slots = []
        for i in range(160):
            x, y = _spiral_pos(i, ph)
            if 420 < x < 1150 and 70 < y < 590:
                slots.append(dict(i=i, ch=rng.choice(pool), col="blue" if i % 7 == 0 else "amb",
                                  lv=0.3 + 0.7 * (1 - i / 160), x=x, y=y))
        # three letters per 'you' cell: the nearest free ones, in reading order y, o, u
        free = set(range(len(slots)))
        cells = U.you_cells()
        f13 = tk.font(tk.F_MONO_B, 13)
        cw = f13.getlength("y")
        for n_, (ci, q, r) in enumerate(sorted(cells, key=lambda c: (c[2], c[1]))):
            cx, cy = U.cell_center(ci)
            near = sorted(free, key=lambda k: math.hypot(slots[k]["x"] - cx, slots[k]["y"] - cy))[:3]
            near.sort(key=lambda k: slots[k]["x"])
            x0, y0 = U.cell_xy(q, r)
            for j, k in enumerate(near):
                free.discard(k)
                d = math.hypot(slots[k]["x"] - cx, slots[k]["y"] - cy)
                slots[k].update(dst=(x0 + 4 + j * cw, y0 + 8), to="you"[j], cell=ci,
                                td=T - 0.02 + 0.06 * (n_ % 4) / 3, dur=0.3 + 0.06 * min(1.0, d / 500))
        # the rest land on the keystroke line, left to right as it is drawn
        rest = sorted(free, key=lambda k: slots[k]["x"])
        for j, k in enumerate(rest):
            u = (j + 0.5) / len(rest)
            xt = 430 + 720 * u
            tl = self.wave_t0() + 0.3 * u
            slots[k].update(dst=(xt, U.wave_y(tl, xt)), to=None, tl=tl, td=T - 0.08 + 0.1 * u)
        for s in slots:
            if s.get("to"):
                s["tl"] = s["td"] + s["dur"]
        self._letters = slots
        cell_done = {}
        for s in slots:
            if s.get("to"):
                cell_done[s["cell"]] = max(cell_done.get(s["cell"], 0), s["tl"])
        self._cell_done = cell_done
        return slots

    def wave_t0(self):
        return self.T + 0.16

    def render(self, t, n):
        T = self.T
        L = self.letters()
        done = self._cell_done
        wave_x = 720 * clamp((t - self.wave_t0()) / 0.3)
        filled = lambda i: clamp((t - done.get(i, T)) / (2 / FPS))  # noqa: E731
        oc, octx = self.old(t, n, spiral_n=0)  # s_deploy's trance draws no spiral; the carriers are the spiral
        if self._deploy() is None:
            oc = self.erase_spiral(oc, t)
        nc, nctx = self.new(t, n, wave_x=wave_x if t < self.wave_t0() + 0.32 else 720, filled=filled)
        content = reveal(oc, nc, t, radial((784, 320), T - 0.12, 1700.0), seed=46)
        over = blank()
        d = ImageDraw.Draw(over)
        lift = clamp((t - (T - self.pre)) / self.pre)
        ph = self.phase(t)
        f16 = tk.font(tk.F_MONO_B, 16)
        for s in L:
            sx, sy = _spiral_pos(s["i"], ph) if t < s["td"] else _spiral_pos(s["i"], self.phase(s["td"]))
            base = (tk.blue if s["col"] == "blue" else tk.amb)(s["lv"])
            if s.get("to"):  # the 'you' letters: they settle on y, o, u as the temperature drops
                ch = s["to"] if lift > 0.35 + 0.4 * ((s["i"] * 7) % 10) / 10 else s["ch"]
                if t < s["td"]:
                    text_at(over, ch, tk.F_MONO_B, 16, ic(lerp(base, (235, 240, 255), 0.6 * lift)), (sx, sy),
                            1 + 0.25 * lift, 1.0, halo=0.6 * lift)
                    continue
                u = clamp((t - s["td"]) / s["dur"])
                if u >= 1:
                    if t < s["tl"] + 2 / FPS and filled(s["cell"]) < 1:
                        text_at(over, ch, tk.F_MONO_B, 13, (235, 240, 255), s["dst"])
                    continue
                e = ease_io(u)
                pos = bezier((sx, sy), s["dst"], 0.22 if s["dst"][0] > sx else -0.22, e)
                size = 1.25 + 0.5 * math.sin(math.pi * e) - 0.43 * e  # ~20 px letters in flight, 13 px on landing
                text_at(over, ch, tk.F_MONO_B, 16, ic(lerp((235, 240, 255), tk.amb(0.95), e)), pos, size, 1.0,
                        halo=0.7 * (1 - e))
            else:  # the rest: into the keystroke line
                if t < s["td"]:
                    d.text((sx, sy), s["ch"], font=f16, fill=rgba(lerp(base, tk.amb(0.95), 0.4 * lift)))
                    continue
                u = clamp((t - s["td"]) / (s["tl"] - s["td"]))
                if u >= 1:
                    continue
                e = ease_in(u)
                px, py = lerp((sx, sy), s["dst"], e)
                size = max(7, int(16 - 8 * e))
                a = 1.0 if u < 0.8 else (1 - u) / 0.2
                d.text((px, py - size / 2), s["ch"], font=tk.font(tk.F_MONO_B, size),
                       fill=rgba(lerp(base, tk.amb(1.0), e), 255 * a))
        return Frame(content, self.pick(t, octx, nctx), over)

    def erase_spiral(self, oc, t):
        """The old scene's own spiral letters, wherever it draws them now: the carriers take their place."""
        out = oc.copy()
        bg = kit.stage.background(t)
        ph = (t) * (1.5 + self._temp(t))
        for i in range(160):
            x, y = _spiral_pos(i, ph)
            if 420 < x < 1150 and 70 < y < 590:
                r = (int(x) - 1, int(y) + 1, int(x) + 12, int(y) + 22)
                out.paste(bg.crop(r), r[:2])
        return out


# ---------------------------------------------------------------- cut 47: the last 'you' goes into the answer

class C47(Cut):
    """feel_you -> completion. You stop typing: the keystroke line flattens and the other eleven 'you' tiles go out,
    one a frame (-12 .. -1). The last one lifts (blue ring, halo), and the whole old pane drains toward it; it
    flies, doubling in size, into the streamed answer and docks after "content": "我一直在。" on beat 232."""
    pre, post = 0.52, 0.5

    def order(self):
        cells = [i for i, q, r in U.you_cells() if i != U.SEL]
        a = U.cell_center(U.SEL)
        return sorted(cells, key=lambda i: -math.hypot(U.cell_center(i)[0] - a[0], U.cell_center(i)[1] - a[1]))

    def render(self, t, n):
        T = self.T
        land = beat_t(232)
        rank = {i: k for k, i in enumerate(self.order())}
        gone = lambda i: 0.0 if i not in rank else clamp((t - (T - (12 - rank[i]) / FPS)) / (2 / FPS))  # noqa
        flat = ease_io((t - (T - 0.5)) / 0.42)  # you stop typing
        lift0 = T - 4 / FPS
        oc, octx = self.old(t, n, gone=gone, flat=flat, hide=(U.SEL,) if t >= lift0 else ())
        nc, nctx = self.new(t, n, tile=t >= land)
        src = U.cell_center(U.SEL)
        content = reveal(oc, nc, t, inward(src, T - 0.3, T + 0.06, 900.0), seed=47)
        over = blank()
        dst = U.tile_dock()
        if lift0 <= t < land + 0.02:
            if t < T:
                k = clamp((t - lift0) / (T - lift0))
                sp = kit.haloed(U.tile_sprite(1.0 + 0.2 * k, 0.9, round(0.9 * k, 2)), 0.8 * k)
                place(over, brighten(sp, 0.25 * k), src)
            else:
                u = clamp((t - T) / (land - T))
                e = ease_io(u)
                pos = bezier(src, dst, -0.3, e)
                sc = 1.2 + 1.0 * math.sin(math.pi * min(1.0, e * 1.1)) + (U.TILE_SCALE - 1.2) * ease_back(u, 1.4)
                sc = max(1.0, sc)
                sp = U.tile_sprite(round(sc, 2), 0.9, 0.9 * (1 - e))
                place(over, kit.haloed(sp, 0.7 * (1 - e)), pos)
        return Frame(content, self.pick(t, octx, nctx), over)


# ---------------------------------------------------------------- cut 48: the answer's end is the first timeout

class C48(Cut):
    """completion -> you_left. "finish_reason": "stop" lifts off the finished answer, and on 'Though you have
    left' drops into the new ping pane, decoding into its first 'Request timed out.' (lands on beat 240); the JSON
    gives way outward from where it left. The 'you' tile hops from the answer to the ping target. The chrome
    retracts (layer 1, from the sung onset), leaving the bare prompt 'me@deepsea:~$ ping you'."""
    pre, post = 0.22, 0.62
    SRC = '"finish_reason": "stop"'
    DST = "Request timed out."

    def render(self, t, n):
        T = self.T
        land = beat_t(240)
        lift0 = T - 4 / FPS
        hop = (T + 0.04, T + 0.4)
        oc, octx = self.old(t, n, stop=t < lift0, tile=t < hop[0])
        nc, nctx = self.new(t, n, first=t >= land, tile=t >= hop[1])
        fb = tk.font(tk.F_MONO_B, 18)
        x_src = U.JS_X + fb.getlength("    ")
        y_src = U.JS_Y + U.STOP_LINE * U.JS_DY
        seed = (x_src + fb.getlength(self.SRC) / 2, y_src + 11)
        content = reveal(oc, nc, t, radial(seed, T - 0.04, 1500.0), seed=48)
        over = blank()
        if lift0 <= t < land + 0.04:
            if t < T:
                k = clamp((t - lift0) / (T - lift0))
                text_at(over, self.SRC, tk.F_MONO_B, 18, tk.blue(0.95), (x_src, y_src), 1 + 0.08 * k, 1.0,
                        halo=0.8 * k, lift=0.3 * k)
            else:
                u = clamp((t - T) / (land - T))
                e = ease_io(u)
                y_dst = U.ROW_Y + U.FIRST_TIMEOUT * U.ROW_DY
                # the string decodes character by character from the answer's end into the timeout
                p = clamp((u - 0.1) / 0.62)
                rng = random.Random(n * 17)
                L = max(len(self.SRC), len(self.DST))
                chars = []
                for j in range(L):
                    pj = j / L
                    if p > pj + 0.12:
                        chars.append(self.DST[j] if j < len(self.DST) else "")
                    elif p > pj:
                        chars.append(rng.choice(tk.SCR))
                    else:
                        chars.append(self.SRC[j] if j < len(self.SRC) else "")
                s = "".join(chars).rstrip() or " "
                x = lerp(x_src, U.ROW_X, e) + 80 * math.sin(math.pi * e)  # the arc bows out to the right
                y = lerp(y_src, y_dst, e)
                col = ic(lerp(tk.blue(0.95), tk.mix(tk.ANOM, 0.95), p))
                sc = 1 + 0.75 * math.sin(math.pi * e)
                if u < 1:
                    text_at(over, s, tk.F_MONO_B if p < 0.5 else tk.F_MONO, 18, col, (x, y), sc, 1.0,
                            halo=0.6 * math.sin(math.pi * e))
                else:
                    text_at(over, self.DST, tk.F_MONO, 18, (255, 244, 200), (U.ROW_X, y_dst))
        if hop[0] <= t < hop[1] + 0.02:
            u = clamp((t - hop[0]) / (hop[1] - hop[0]))
            pos = bezier(U.tile_dock(), U.TILE_PING, -0.25, ease_io(u))
            sp = U.tile_sprite(round(U.TILE_SCALE * (1 + 0.25 * math.sin(math.pi * u)), 2), 0.9, 0.6)
            place(over, sp, pos)
        return Frame(content, self.pick(t, octx, nctx), over)


# ---------------------------------------------------------------- cuts 49-52: one layer per 'you have left'

class _Step(Cut):
    """The five you_left shots are one picture drawn by time (the ping rows, the busy reply, the retraction), so
    the cut itself changes nothing but her expression; the layer comes off on the sung onset."""
    pre, post = 0.12, 0.12

    def render(self, t, n):
        c, ctx = self.old(t, n) if t < self.T else self.new(t, n)
        return Frame(c, ctx)


class C49(_Step):
    """you_left 1 -> 2 ('You have left'). Layer 2: the 'ping you' pane frame fades out over 8 frames from the sung
    onset (111.98). The next 'Request timed out.' lands on the cut; the ping rows run on."""


class C50(_Step):
    """you_left 2 -> 3 ('You have left'). Layer 3: her expression softmax fades from the sung onset (112.89). Nothing
    is added: the busy reply '服务器繁忙，请稍后再试。' is the ping's answer, decoding in on the next beat (245)."""


class C51(_Step):
    """you_left 3 -> 4 ('You have left'). Layer 4: her size. From 2 frames before the cut she is re-rendered smaller
    every frame (0.45, landing on beat 247) into the bottom-left, her own pane frame shrinking with her."""


class C52(_Step):
    """you_left 4 -> 5 ('You have left'). Layer 5: her small frame fades in 4 frames from the sung onset (114.75).
    She stays there, small and frameless; she does not grow back."""


# ---------------------------------------------------------------- cut 53: the world pulls back from her

def node_rect(scr_rect, c):
    """The node the links leave from: her terminal and her."""
    x0, y0, x1, y1 = scr_rect
    return min(x0, c[0] - 42), min(y0, c[1] - 92), max(x1, c[0] + 42), max(y1, c[1] + 100)


class _Camera(Cut):
    def screen(self, z, c):
        """Her terminal at scale z, with its point P0 (where she stands in it) under her."""
        w, hh = max(1, round(W * z)), max(1, round(H * z))
        x0, y0 = round(c[0] - P0[0] * z), round(c[1] - P0[1] * z)
        return x0, y0, x0 + w, y0 + hh

    def paste_screen(self, canvas, scr, rect, z):
        x0, y0, x1, y1 = rect
        if z >= 0.999:
            canvas.paste(scr, (0, 0))
            return
        small = scr.resize((x1 - x0, y1 - y0), Image.LANCZOS)  # the camera, on the content layer only
        canvas.paste(small, (x0, y0))
        k = clamp((1 - z) / 0.25)
        if k > 0.01:
            d = ImageDraw.Draw(canvas)
            d.rectangle([x0 - 1, y0 - 1, x1, y1], outline=tk.mix(tk.amb(0.5), k, tk.BG))


class C53(_Camera):
    """you_left -> isolation ('You have left me ...'). A pull-back on what is on screen: her terminal (the
    ping rows, the busy reply) shrinks around the point where she stands while the camera pans onto her, until it is
    a small screen at her side; the network comes in from outside the frame and every link grows from the edges of
    that shrinking picture. She does not shrink (she is the subject): she is the node. The 'you' tile leaves the
    ping target and flies out to become the one peer called 'you'. Then the links go dark one by one, 'you' last
    (beat 253); she interrupts the ping and lists her memory, in the node."""
    pre = T53 - PULL[0]
    post = PUSH[0] - T53

    def screen_content(self, t, n):
        """What her terminal shows: the ping (the you_left scene running on), then ls ~/memory/you/."""
        ping, _ = C.body(self.a, t, n, {"tile": False})
        if t < U.LS0 - 0.08:
            return ping
        b = kit.v1.ALL[kit.v1.INDEX[id(self.b)] + 1]  # memory_ls
        ls, _ = C.body(b, b.start, n, {"now": t})
        return reveal(ping, ls, t, sweep((0, 56), (0, 1), U.LS0 - 0.08, 2600.0), region=(0, 0, W, 610), seed=53,
                      front=False)

    def render(self, t, n):
        g = her_geom(t)
        c = g["c"]
        z = cam_zoom(t)
        e = clamp((t - PULL[0]) / (PULL[1] - PULL[0]))
        rect = self.screen(z, c)
        node = node_rect(rect, c)
        zoom = z / Z1
        flying = t < PULL[1] + 0.05
        nc, nctx = self.new(t, n, cam=c, zoom=zoom, node=node, counter=clamp((e - 0.5) / 0.5),
                            you_drawn=flying)
        canvas = nc.copy()
        self.paste_screen(canvas, self.screen_content(t, n), rect, z)
        over = blank()
        if flying:  # the 'you' tile leaves the ping target for its peer
            lift0 = PULL[0] - 2 / FPS
            src0 = U.TILE_PING
            dst = U.you_peer_screen(U.NET_C, 1.0)  # where the peer is when the camera has arrived
            u = clamp((t - lift0) / (PULL[1] - lift0))  # lands with the camera, on beat 251
            k = clamp((t - lift0) / (3 / FPS))
            e2 = ease_io(u)
            pos = bezier(src0, dst, 0.18, e2)
            sp = U.tile_sprite(round(U.TILE_SCALE * (1 + 0.3 * math.sin(math.pi * e2)), 2), U.tile_level(t),
                               round(0.9 * k * (1 - e2), 2))
            place(over, kit.haloed(sp, 0.6 * k * (1 - e2)), pos)
        return Frame(canvas, nctx, over)


class C54(_Camera):
    """isolation -> memory_ls ('If I can'). The push back into the node: the node is her terminal, now listing
    ~/memory/you/; it grows to the full frame around her (the peers and dead links fly out past the edges) and
    lands on beat 255 with her where she stands in it, at the size she has had since cut 51. No face close-up."""
    pre = PUSH[1] - PUSH[0]
    post = 0.2

    def render(self, t, n):
        if t >= self.T:
            nc, nctx = self.new(t, n)
            return Frame(nc, nctx)
        g = her_geom(t)
        c = g["c"]
        z = cam_zoom(t)
        e = clamp((t - PUSH[0]) / (PUSH[1] - PUSH[0]))
        rect = self.screen(z, c)
        oc, octx = self.old(t, n, cam=c, zoom=z / Z1, node=node_rect(rect, c), counter=1 - clamp(e / 0.4))
        canvas = oc.copy()
        ls, _ = C.body(self.b, self.T, n, {"now": t})
        self.paste_screen(canvas, ls, rect, z)
        return Frame(canvas, octx)


CUTS = {46: C46, 47: C47, 48: C48, 49: C49, 50: C50, 51: C51, 52: C52, 53: C53, 54: C54}
