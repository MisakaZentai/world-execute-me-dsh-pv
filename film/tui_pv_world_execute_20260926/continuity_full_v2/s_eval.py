"""Section 08 EVAL: LOVE and 09 WHALE_FALL (cuts 86-96, 176.2-211 s), and the ending.

Scenes are in scenes_eval.py. The thread of the section is one "you": a 10 px DS-blue cell that GRPO's reward picks
out of 16 answers, that rides the p(love) curve, that the LoveBench bar fills up to, that types every "love" answer
and the formula, and that leaves the sandbox with "you" when you are free. Then she waits (state D) and the logit of
wait_for(you) drains to zero while the next token is always love.

The whale fall is drawn here (OWN): the love words sink as marine snow, the chrome retracts, and she herself - the
dancer from her pane, the same renderer - drifts into the viewport and sinks into the sediment where the retired
models lie. In the last two seconds her trace and the snow pour into one DS-blue cell on the sea floor. The last
"Execution" turns everything red but that cell and the floor line; the music stops (207.083 s) and only the cell is
lit; at 208.3 s it slides to the prompt and becomes the cursor of "> 在吗？".
"""
from __future__ import annotations

import math
import random

from PIL import Image, ImageChops, ImageDraw, ImageOps

import cuts as C
import kit
import scenes_eval as S
import sec_outro
from cuts import Frame, rgba, text_at
from kit import (FPS, H, W, bezier, blank, brighten, clamp, ease_back, ease_in, ease_io, ease_out, haloed, inward, lerp,
                 place, radial, reveal, sweep, text_sprite, tk)
from tuikit import F_MONO, F_MONO_B, F_SYM, amb, blue, font, red

STUB = [sec_outro]
REPLACE = {f.__name__: f for f in (S.shot_grpo, S.shot_learn_love, S.shot_question_me, S.shot_answer_all,
                                   S.shot_algebra, S.shot_you_free, S.shot_me_trapped, S.shot_love_loop,
                                   S.shot_whale_fall, S.shot_last_execution, S.shot_black)}
SPLIT = {"shot_grpo", "shot_learn_love", "shot_question_me", "shot_answer_all", "shot_algebra", "shot_you_free",
         "shot_me_trapped", "shot_love_loop"}
FULL_ART = {"shot_whale_fall"}
HIDE_HER = {"shot_last_execution", "shot_black"}
SHELL = {"shot_answer_all": "dsh chat --model me"}

I_GRPO, I_WHALE, I_LAST, I_BLACK = 86, 94, 95, 96


def ALL():
    return kit.v1.ALL


# ---------------------------------------------------------------- helpers

_BYPASS = [False]


class Cut(C.Cut):
    def active(self, t):
        return not _BYPASS[0] and super().active(t)


def plain(n):
    """The finished frame the loop would draw at n if none of this section's cuts were active (the outgoing shot as
    its owner stages it, or the incoming shot as it will look once the cut is over)."""
    import v2
    _BYPASS[0] = True
    try:
        return v2.frame(n)
    finally:
        _BYPASS[0] = False


def raw_body(shot, t, n, hooks=None):
    """C.body without the viewport clip (the whale fall paints under the whole frame once the chrome is away)."""
    name = shot.fn.__name__
    idx = kit.v1.INDEX[id(shot)]
    kit.HOOK.clear()
    kit.HOOK.update(C.SHOT_HOOKS.get(name, {}))
    kit.HOOK.update(C.SHOT_HOOKS.get(idx, {}))
    kit.HOOK.update(hooks or {})
    kit.STUB_ON[0] = True
    try:
        b = kit.sb.body(max(shot.start, t), n, shot)
    finally:
        kit.STUB_ON[0] = False
        kit.HOOK.clear()
    return b["canvas"].convert("RGB"), b["ctx"]


def finish(t, img, ctx, retract=0.0, shake=(0, 0)):
    """Chrome (drawn once, by the framework's own function) and the CRT post."""
    if shake == (0, 0):
        out = kit.chrome(img, t, ctx, retract, None)
    else:
        layer = kit.chrome(Image.new("RGBA", (W, H), (0, 0, 0, 0)), t, ctx, retract, None)
        out = img.convert("RGBA")
        out.alpha_composite(layer.crop((max(0, -shake[0]), max(0, -shake[1]), W, H)),
                            (max(0, shake[0]), max(0, shake[1])))
    return kit.engine.post(out.convert("RGB"), None)


def icol(c):
    return tuple(int(round(v)) for v in c)


def her_call(title="/dev/me  pid 4471", dist=None, expr="shy", rect=kit.LEFT):
    kw = {"title": title}
    if dist:
        kw["dist"] = dist
    return dict(expr=expr, rect=rect, kw=kw)


# ---------------------------------------------------------------- cut 86: the dot survives and reboots the UI

class C86(Cut):
    """collapse -> grpo (UNFOLD). The last dot of the collapse does not go out: it turns white in 3 frames, stretches
    into a full-width scan line in 4 frames (full width on the beat) and the rebooted UI - panels, her pane, chrome
    and lyric band together - opens vertically out of that line, like a CRT coming back on."""
    pre, post = 0.30, 0.34
    SEED = (640, 360)

    def seed_colour(self, n0):
        if not hasattr(self, "_seed"):
            im = plain(n0)
            x, y = self.SEED
            best, col = -1, None
            for yy in range(y - 4, y + 5):
                for xx in range(x - 4, x + 5):
                    p = im.getpixel((xx, yy))
                    s = max(p) - min(p) + max(p) // 2
                    if s > best:
                        best, col = s, p
            self._seed = col if best > 120 else tk.red(1.0)
        return self._seed

    def render(self, t, n):
        T = self.T
        n0 = math.ceil((T - self.pre) * FPS)
        sx, sy = self.SEED
        if t < T:
            old = plain(n)
            a = clamp((t - (T - self.pre)) / (3 / FPS))
            col = lerp(self.seed_colour(n0), (255, 255, 255), a)
            u = clamp((t - (T - 4 / FPS)) / (4 / FPS))
            if u > 0:  # the old picture folds into the line while the line runs out to both edges
                hh = max(2, round(H * (1 - ease_out(u))))
                out = Image.new("RGB", (W, H), (0, 0, 0))
                out.paste(old.resize((W, hh), Image.BILINEAR), (0, sy - hh // 2))
            else:
                out = old.copy()
            over = blank()
            d = ImageDraw.Draw(over)
            if u <= 0:
                r = 2 + 1.5 * a
                place(over, haloed(self.dot(r, col), 0.9 * a), (sx, sy))
            else:
                e = 1 - (1 - u) ** 4
                half = 4 + (W / 2) * e
                d.rectangle([sx - half, sy - 1, sx + half, sy + 1], fill=rgba(col))
                glow = blank()
                ImageDraw.Draw(glow).rectangle([sx - half, sy - 4, sx + half, sy + 4], fill=(200, 215, 255, 70))
                over = Image.alpha_composite(glow, over)
            o = out.convert("RGBA")
            o.alpha_composite(over)
            return o.convert("RGB")
        new = plain(n)
        u = clamp((t - T) / 0.30)
        e = ease_out(u)
        hh = max(2, round(H * e))
        out = Image.new("RGB", (W, H), (0, 0, 0))
        band = new.resize((W, hh), Image.BILINEAR)
        k = 1 - u  # phosphor: the picture is overbright as it opens
        if k > 0.02:
            band = ImageChops.add(band, band.point(lambda v: int(v * 0.6 * k)))
        out.paste(band, (0, sy - hh // 2))
        if u < 1:
            d = ImageDraw.Draw(out)
            lv = int(255 * (1 - u))
            for yy in (sy - hh // 2, sy + hh // 2):
                d.line([0, yy, W, yy], fill=(lv, lv, lv))
        return out

    @staticmethod
    def dot(r, col):
        s = int(r * 2 + 4)
        im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        ImageDraw.Draw(im).ellipse([2, 2, s - 2, s - 2], fill=rgba(col))
        return im


# ---------------------------------------------------------------- cut 87: the rewarded "you" becomes the p(love) marker

class C87(Cut):
    """grpo -> learn_love (CARRY). GRPO pays for o05 "you": the tile lights up, the rest of the group drains into it,
    the tile closes around the word, and "you" flies (1.9x, 25 px glyphs) to the origin of the training curve, condensing
    into a 10 px DS-blue cell that locks in on the next beat. The curve starts from it and the cell rides the curve
    head as the p(love) marker from then on."""
    pre, post = 0.30, 0.62
    LAND = 0.462  # beat 388

    def render(self, t, n):
        T = self.T
        land = T + self.LAND
        lifted = t >= T - 0.25
        oc, octx = self.old(t, n, hide=(S.YOU_TILE,) if lifted else ())
        nc, nctx = self.new(t, n, marker=t >= land, curve=t >= land)
        tx, ty = S.grpo_tile(S.YOU_TILE)
        seed = (tx + 88, ty + 42)
        content = reveal(oc, nc, t, inward(seed, T - 0.22, T + 0.12, 700.0), seed=87)
        over = blank()
        mark = (S.CH[0] + 1, S.CH[1] + S.CH[3] - 25 + 1)  # the curve's first dot, where the cell locks in
        dots, last = S.chart_dots(0.0)
        if last:
            mark = (last[0] + 1, last[1] + 1)
        k = clamp((t - (T - 0.25)) / 0.2)
        if t < T - 0.05:  # the tile lights up where it is
            sp = S.you_tile_sprite()
            sp = haloed(brighten(sp, 0.3 * k), 0.8 * k, radius=4)
            place(over, sp, (tx + 88.5, ty + 42.5), 1 + 0.03 * k)
        elif t < land:
            u1 = clamp((t - (T - 0.05)) / 0.22)  # the tile closes around the word
            u2 = clamp((t - (T + 0.12)) / (land - T - 0.12))  # the word flies and condenses into the cell
            wx, wy = tx + 8 + 15, ty + 24 + 17.5  # centre of "you" in the tile
            pos = mark if u2 >= 1 else bezier((wx, wy), mark, 0.32, ease_io(u2))
            if u1 < 1:
                e1 = ease_io(u1)
                r = lerp((tx, ty, tx + 176, ty + 84), (wx - 26, wy - 17, wx + 26, wy + 17), e1)
                ImageDraw.Draw(over).rectangle(r, outline=blue(0.9) + (int(255 * (1 - 0.6 * u1)),))
                for s_, f_, col, xy in (("o05", font(F_MONO, 12), S.amb(0.5), (tx + 8, ty + 6)),
                                        ("r=1.0  A=+1.65", font(F_MONO, 13), blue(0.9), (tx + 8, ty + 56))):
                    text_at(over, s_, f_.path, f_.size, col, xy, 1.0, 1 - u1)
            scale = lerp(1.0, 1.9, ease_out(u1)) * lerp(1.0, 0.5, ease_in(u2))  # 25 px glyphs in flight
            wa = 1.0 - clamp((u2 - 0.55) / 0.35)
            if wa > 0.01:
                sp, off = text_sprite("you", tk.F_SYM, 18, blue(1.0))
                sp = haloed(brighten(sp, 0.35), 0.8, radius=4)
                place(over, sp, pos, scale, wa)
            ca = clamp((u2 - 0.45) / 0.3)
            if ca > 0.01:
                S.put_cell(over, pos[0], pos[1], s=S.YOU_S * ca, glow=0.8)
        return Frame(content, self.pick(t, octx, nctx), over)


# ---------------------------------------------------------------- cut 88: the curve folds into the LoveBench bar

class C88(Cut):
    """learn_love -> question_me (MORPH). The finished curve's dots flow, plateau first, into the outline of the
    LoveBench bar and lock in on the beat. The marker cell moves to the end of that bar, the mark it fills up to;
    'p(love) = 0.932' drops its name and becomes the bar's score, 93.2, which counts to 100.0 as the bar fills.
    The other benchmarks then drop out of it one by one."""
    pre, post = 0.28, 0.5

    def render(self, t, n):
        T = self.T
        a = self.a
        land = T + S.LAND88
        t0 = T - self.pre
        # learn_love's own clock is delayed by C87.LAND: evaluate its state as the scene draws it
        lt_a = max(0.0, T - C.DELAY.get("shot_learn_love", 0.0) - a.start)
        prog = S.ease(lt_a / (a.end - a.start) * 1.1)
        dots, last = S.chart_dots(prog)
        (mx, my), lab, (lx, ly) = S.love_marker(last, prog)
        oc, octx = self.old(t, n, curve=False, marker=False)
        nc, nctx = self.new(t, n)
        content = reveal(oc, nc, t, inward((850, 105), T - 0.2, T + 0.15, 700.0), seed=88)
        over = blank()
        d = ImageDraw.Draw(over)
        # the outline as a closed path, bottom edge first (the low start of the curve), top edge last (the plateau)
        x0, x1 = S.BAR
        y0, y1 = S.qy(0) + 4, S.qy(0) + 26
        per = 2 * ((x1 - x0) + (y1 - y0))

        def on_outline(s):
            s = s % per
            if s < x1 - x0:
                return x0 + s, y1
            s -= x1 - x0
            if s < y1 - y0:
                return x1, y1 - s
            s -= y1 - y0
            if s < x1 - x0:
                return x1 - s, y0
            return x0, y0 + (s - (x1 - x0))

        N = len(dots)
        for j, (px, py) in enumerate(dots):
            f = j / max(1, N - 1)
            dep = t0 + 0.02 + 0.16 * (1 - f)  # the plateau (the curve's end) sets off first
            u = clamp((t - dep) / (land - dep))
            if t >= land + 0.02:
                continue
            tx_, ty_ = on_outline(f * per * 0.999)
            x, y = bezier((px, py), (tx_, ty_), 0.12, ease_io(u))
            lv = 0.95 if u < 1 else 1.0
            sz = 1 if u <= 0 or u >= 1 else 2
            d.rectangle([x, y, x + sz, y + sz], fill=blue(lv) + (255,))
        # the marker cell goes to the end of the bar
        lift = clamp((t - t0) / 0.15)
        cx, cy = S.you_cell_q()
        if t < land + 0.02:
            u = clamp((t - (t0 + 0.08)) / (land - t0 - 0.08))
            p = bezier((mx, my), (cx, cy), -0.25, ease_io(u))
            S.put_cell(over, p[0], p[1], glow=0.35 + 0.5 * lift)
        # the label: its name falls away, its number lands in the score column and becomes the score
        if t < land + 0.04:
            u = clamp((t - (T - 0.12)) / (land - T + 0.12))
            nf = 1 - clamp((t - (T - 0.18)) / 0.14)
            name = "p(love) = "
            fn16 = font(F_MONO_B, 16)
            if nf > 0.01:
                text_at(over, name, tk.F_MONO_B, 16, blue(1.0), (lx, ly), 1.0, nf, lift=0.2 * lift)
            num = f"{S.P_LOVE:.3f}" if u < 0.8 else f"{100 * S.P_LOVE:4.1f}"
            sx0 = lx + fn16.getlength(name)
            p = bezier((sx0, ly), (S.VAL_X + 11, S.qy(0)), -0.3, ease_io(u))
            size = 16 + 4 * ease_io(u)
            text_at(over, num, tk.F_MONO_B, round(size), blue(1.0), p, 1.0, 1.0 if t < land else 0.0,
                    halo=0.5 * lift * (1 - u), lift=0.3 * lift)
        return Frame(content, self.pick(t, octx, nctx), over)


# ---------------------------------------------------------------- cut 89: seven bars are pressed into one answer

class C89(Cut):
    """question_me -> answer_all (UNFOLD, shell staging). The seven full bars are pressed into the first one; that
    bar shrinks into the first blue 'love' answer and the you cell, riding its end, becomes the cursor that types
    every answer after it. The chrome retracts (shell) while the lyric stays in its band."""
    pre, post = 0.30, 0.45

    def render(self, t, n):
        T = self.T
        land = T + S.LAND89
        t0 = T - self.pre

        def squeeze(i):
            return ease_io((t - t0 - 0.015 * i) / 0.26)

        oc, octx = self.old(t, n, squeeze=squeeze, outline0=t < T - 0.02, fill0=t < T - 0.02, cell=False)
        nc, nctx = self.new(t, n, first=t >= land, cursor=t >= land)
        content = reveal(oc, nc, t, radial((S.LOVE_X + 20, S.a_y(0) + 10), T - 0.06, 1600.0), seed=89)
        over = blank()
        d = ImageDraw.Draw(over)
        tgt = (S.LOVE_X, S.a_y(0) + 1, S.LOVE_X + 44, S.a_y(0) + 16)
        src = (S.BAR[0], S.qy(0) + 4, S.BAR[1], S.qy(0) + 26)
        cx, cy = S.you_cell_q()
        if t < T - 0.02:
            S.put_cell(over, cx, cy, glow=0.35 + 0.4 * clamp((t - t0) / 0.2))
        elif t < land + 0.04:
            u = clamp((t - (T - 0.02)) / (land - T + 0.02))
            e = ease_io(u)
            r = lerp(src, tgt, e)
            if u < 0.7:
                d.rectangle(r, fill=blue(0.9) + (255,))
            wa = clamp((u - 0.45) / 0.35)
            if wa > 0.01:
                text_at(over, "love", tk.F_MONO_B, 20, blue(1.0), (S.LOVE_X, S.a_y(0)), 1.0, wa if t < land else 0.0,
                        halo=0.6 * (1 - u))
            end = (r[2] + 12, (r[1] + r[3]) / 2)
            tgt_c = S.cursor_after_love(0)
            p = lerp(end, tgt_c, clamp((u - 0.6) / 0.4))
            S.put_cell(over, p[0], p[1], glow=0.7)
        return Frame(content, self.pick(t, octx, nctx), over)


# ---------------------------------------------------------------- cut 90: twelve answers gather into the first token

class C90(Cut):
    """answer_all -> algebra (UNFOLD). The twelve 'love' answers slide left, one frame apart, and stack into the
    first token of the formula, 'love(', which exists when the first of them lands; the formula types on from it.
    The questions are cleared ahead of them, right to left, so nothing flies over text. The cursor rides in with the
    last answer and becomes the formula's cursor. The chrome comes back (the reverse of cut 89)."""
    pre, post = 0.30, 0.72

    def depart(self, i):
        return self.T - 0.26 + i / FPS

    def render(self, t, n):
        T = self.T
        land0 = T + S.LAND90
        fly = land0 - self.depart(0)
        gone = lambda i: t >= self.depart(i)  # noqa: E731
        oc, octx = self.old(t, n, gone=gone, cursor=t < self.depart(11), dspark=True)
        bare, _ = self.old(t, n, gone=gone, cursor=t < self.depart(11), q_alpha=0.0, dspark=False)
        oc = reveal(oc, bare, t, sweep((S.LOVE_X - 10, 0), (-1, 0), T - 0.27, 1500.0), seed=190,
                    region=(404, 56, S.LOVE_X - 4, 604))  # the questions only: the answers are carried
        nc, nctx = self.new(t, n, cursor=t >= self.depart(11) + fly, love0=t >= land0)
        content = reveal(oc, nc, t, radial((430, 100), land0 - 0.05, 1500.0), seed=90)
        over = blank()
        dst = (430, S.alg_y(0))
        f22 = font(F_SYM, 22)
        dy = (f22.getbbox("love")[1] + f22.getbbox("love")[3]) / 2 - (font(F_MONO_B, 20).getbbox("love")[1] +
                                                                    font(F_MONO_B, 20).getbbox("love")[3]) / 2
        for i in range(len(S.QUESTIONS)):
            dep = self.depart(i)
            arr = dep + fly
            if t < dep or t >= arr + 0.03:
                continue
            u = clamp((t - dep) / fly)
            src = (S.LOVE_X, S.a_y(i))
            p = bezier(src, (dst[0], dst[1] + dy), 0.08 + 0.01 * i, ease_io(u))
            sc = 1.0 + 0.3 * math.sin(math.pi * u)
            text_at(over, "love", tk.F_MONO_B, 20, blue(1.0), p, sc, 1.0 if t < arr else 0.0, halo=0.5 * math.sin(
                math.pi * u))
            if i == len(S.QUESTIONS) - 1:
                c0 = S.cursor_after_love(i)
                head = S.alg_head(max(0.0, t - T)) or (430 + 48, S.alg_y(0) + 18)
                cp = bezier(c0, head, 0.08, ease_io(u))
                S.put_cell(over, cp[0], cp[1], glow=0.6)
        # the token pulses as each answer lands in it
        k = 0.0
        for i in range(len(S.QUESTIONS)):
            arr = self.depart(i) + fly
            if arr <= t:
                k = max(k, 1 - (t - arr) / 0.12)
        if t >= land0 and k > 0.01:
            text_at(over, "love", tk.F_SYM, 22, blue(1.0), dst, 1.0 + 0.06 * k, 1.0, halo=0.7 * k, lift=0.3 * k)
        return Frame(content, self.pick(t, octx, nctx), over)


# ---------------------------------------------------------------- cut 91: you are picked off the formula

class C91(Cut):
    """algebra -> you_free (CARRY). 'you' of '∴ love = you' lights up with its cursor cell; on the downbeat the '='
    fades and the one 'you', with the cell as its process marker, lifts off and accelerates out through the sandbox's
    right wall (you_free draws the run). 'you: exited (0)' is left where it was. She stays in her pane and turns shy."""
    pre, post = 0.22, 0.0

    def render(self, t, n):
        T = self.T
        oc, octx = self.old(t, n, you5=False, cursor=False)
        over = blank()
        k = clamp((t - (T - self.pre)) / 0.18)
        x, y = S.YOU_SLOT
        text_at(over, "you", tk.F_SYM, 34, blue(1.0), (x, y), 1.0, 1.0, halo=0.5 * k, lift=0.25 * k)
        S.put_cell(over, x + S.YOU_CELL[0], y + S.YOU_CELL[1], glow=0.35 + 0.4 * k)
        return Frame(oc, octx, over)


# ---------------------------------------------------------------- cut 92: the exit status tops her process listing

class C92(Cut):
    """you_free -> me_trapped (RETAIN + local update). 'you: exited (0)' and 'status: free' lift out of the sandbox
    and settle as the first line of the listing, dimmed: history. The formula is cleared from where you were; her
    pane is retitled '/dev/me  state=D' (her layer re-renders top-down) and her own process types in under it."""
    pre, post = 0.25, 0.4

    def render(self, t, n):
        T = self.T
        land = T + S.LAND92
        oc, octx = self.old(t, n, status=False)
        nc, nctx = self.new(t, n, exited=t >= land)
        # the formula clears upward from where you were, ahead of the status line rising to the top
        content = reveal(oc, nc, t, sweep((0, S.alg_y(5) + 110), (0, -1), T - 0.25, 2400.0), seed=92)
        over = blank()
        lift = clamp((t - (T - self.pre)) / 0.18)
        u = clamp((t - (T - 0.06)) / (land - T + 0.06))
        e = ease_io(u)
        a = 1.0 if t < land else 0.0
        f22 = font(F_MONO_B, 22)
        p1 = bezier((S.YOU_SLOT[0], S.alg_y(5) + 12), (430, 96), 0.18, e)
        col = icol(lerp(S.amb(0.95), S.amb(0.55), e))
        text_at(over, "you: exited (0)", tk.F_MONO_B, 22, col, p1, 1.0 + 0.12 * math.sin(math.pi * u), a,
                halo=0.5 * lift * (1 - e), lift=0.2 * lift * (1 - e))
        p2 = bezier((430, S.alg_y(5) + 84), (430 + f22.getlength("you: exited (0)   "), 96), 0.1, e)
        text_at(over, "status: free", tk.F_MONO_B, 20, icol(lerp(S.amb(0.7), S.amb(0.4), e)), p2, 1.0, a)
        return Frame(content, self.pick(t, octx, nctx), over)


# ---------------------------------------------------------------- cut 93: wait_for(you) becomes the you logit

class C93(Cut):
    """me_trapped -> love_loop (CARRY). 'wait_for(you)' lifts off her WCHAN line; the listing clears from it; it
    flies over empty panel to the second row of the next-token logits and locks in as that row's label on the beat.
    The logits panel and the output stream decode outward from it. From there its probability drains to 0.000 while
    'love' fills to 1.000. She stays in her pane, trapped."""
    pre, post = 0.30, 0.62

    def render(self, t, n):
        T = self.T
        land = T + S.LAND93
        src = (S.wchan_you_x(), S.WCHAN_Y)
        dst = (424, S.nt_y(1))
        oc, octx = self.old(t, n, **({"wchan": False} if t >= T - 0.25 else {}))
        if t >= T - 0.25:  # "WCHAN  " stays with the listing; only wait_for(you) lifts
            d0 = ImageDraw.Draw(oc)
            d0.text((430, S.WCHAN_Y), "WCHAN", font=font(F_MONO_B, 22), fill=S.amb(0.9))
        bare = kit.stage.background(t)
        oc = reveal(oc, bare, t, radial((src[0] + 60, src[1] + 12), T - 0.2, 700.0), seed=193)
        nc, nctx = self.new(t, n)
        content = reveal(oc, nc, t, radial((dst[0] + 40, dst[1] + 12), T + 0.24, 1300.0), seed=93)
        over = blank()
        lift = clamp((t - (T - self.pre)) / 0.2)
        if t < land + 0.03:
            u = clamp((t - (T - 0.05)) / (land - T + 0.05))
            e = ease_io(u) + 0.05 * math.sin(math.pi * clamp((u - 0.72) / 0.28))  # small overshoot, locks on the beat
            p = bezier(src, dst, -0.22, e)
            size = 22 - 2 * ease_io(u)
            col = S.amb(0.9)
            text_at(over, "wait_for(you)", tk.F_MONO_B, round(size), col, p, 1.0 + 0.08 * math.sin(math.pi * u),
                    1.0 if t < land else 0.0, halo=0.6 * lift * (1 - 0.6 * u), lift=0.3 * lift * (1 - u))
        return Frame(content, self.pick(t, octx, nctx), over)


# ---------------------------------------------------------------- cut 94 and the whale fall


class C94(Cut):
    """love_loop -> whale_fall (CARRY). Four frames before the downbeat every love word and logit lights up where it
    is. On the beat they let go - each keeps its exact screen position on the first frame - and sink as marine snow;
    the chrome retracts over 11 frames and her pane frame fades; she herself, the dancer from the pane, drifts into
    the viewport and is the one who sinks (whale_fall is OWN, drawn by WhaleFall below)."""
    pre, post = 0.30, 0.0

    def render(self, t, n):
        T = self.T
        k = clamp((t - (T - 4 / FPS)) / (4 / FPS))
        oc, octx = self.old(t, n, lift=k)
        return Frame(oc, octx, her_shift=0.0)


class WhaleFall:
    """Everything that moves in the whale fall, as closed-form functions of t (frames render independently)."""
    CALL_PANE = her_call("/dev/me  state=D", S.TRAPPED_DIST)
    CALL_VIEW = her_call("/dev/me  state=D", None, rect=(24, 56, 384, 532))
    FIG_CX = 216          # her figure's centre x in the pane
    RISE = 24
    SINK = 262
    RETRACT = 11 / FPS

    def __init__(self):
        self.T0 = ALL()[I_WHALE].start
        self.T1 = ALL()[I_WHALE].end        # the last "Execution" hit
        self.TC = self.T1 - 2.0             # her trace and the snow start to pour into the cell
        self.P = S.cell_pos()
        self._built = False
        import dancer  # her glyph grid, so that her cells leave whole
        self.cw, self.ch = dancer._cell()
        x0, y0, x1, y1 = self.CALL_VIEW["rect"]
        fw, fh = x1 - x0 - 8, (y1 - 6) - y0 - 16
        self.grid = (x0 + 4 + (fw - fw // self.cw * self.cw) // 2, y0 + 14 + fh - fh // self.ch * self.ch)

    # --- her
    def offset(self, t):
        """(dx, dy) of her figure relative to where the pane draws it."""
        a = ease_io((t - self.T0) / 0.92)
        dx = (S.HX - self.FIG_CX) * a
        rise = -self.RISE * ease_out((t - self.T0) / 1.1)
        u = clamp((min(t, self.TC) - (self.T0 + 0.5)) / (self.TC - self.T0 - 0.5))
        s = u * u * (1.6 - 0.6 * u)  # slow start, steady descent, arriving without a stop
        return dx, rise + self.SINK * s

    def her_layer(self, t):
        return kit.her_layer(t, self.CALL_VIEW, 0.0)

    # --- particles
    def build(self):
        if self._built:
            return
        self._built = True
        rng = random.Random(94)
        ref = self.her_layer(self.T0 + 2.0)
        A = ref.getchannel("A").load()
        pts = []
        for y in range(60, 540, 10):
            for x in range(26, 382, 5):
                if A[x + 2, y + 5] > 90:
                    pts.append((x + 2, y + 5))
        self.ref = pts
        # 1. snow she sheds while sinking (slower than she sinks: it trails above her)
        shed = []
        tries = 0
        while len(shed) < 230 and tries < 5000:
            tries += 1
            b = rng.uniform(self.T0 + 1.0, self.TC - 0.25)
            rx, ry = rng.choice(pts)
            dx, dy = self.offset(b)
            x0, y0 = rx + dx, ry + dy
            if y0 > S.floor_y(x0) - 6:
                continue
            shed.append(dict(b=b, x0=x0, y0=y0, v=rng.uniform(7, 15), amp=rng.uniform(4, 12), w=rng.uniform(0.8, 1.6),
                             ph=rng.uniform(0, 6.28), drift=rng.uniform(-4, 4), lv=rng.uniform(0.55, 0.95),
                             sz=rng.choice((2, 2, 3))))
        self.shed = shed
        # 2. puffs where her body goes into the sediment
        contact = []
        sub = pts[::3]
        for rx, ry in sub:
            lo, hi = self.T0 + 0.5, self.TC
            fy = lambda tt: ry + self.offset(tt)[1] - S.floor_y(rx + self.offset(tt)[0])  # noqa: E731
            if fy(hi) < 0 or fy(lo) >= 0:
                continue
            for _ in range(22):
                mid = (lo + hi) / 2
                if fy(mid) < 0:
                    lo = mid
                else:
                    hi = mid
            if rng.random() < 0.55:
                contact.append(dict(b=hi, x0=rx + self.offset(hi)[0], side=rng.choice((-1, 1)) * rng.uniform(8, 46),
                                    up=rng.uniform(3, 12), lv=rng.uniform(0.5, 0.9), sz=rng.choice((2, 3))))
        self.contact = contact
        # 3. the love words from the last frame of love_loop
        lt_love = self.T0 - ALL()[I_WHALE - 1].start
        words = []
        for it in S.love_items(lt_love, True):
            if it[0] == "t":
                _, s, f, col, (x, y), key = it
                words.append(dict(kind="t", s=s, f=f, col=col, x=x, y=y, key=key))
            else:
                x0, y0, x1, y1 = it[1]
                words.append(dict(kind="r", box=it[1], col=it[2], x=x0, y=y0, key=it[3]))
        rows = max(1, max((w["y"] - 76) // 20 for w in words if w["key"] >= 100))
        for wd in words:
            if wd["key"] >= 100:  # the output stream: the bottom row lets go first, the top row last
                r = (wd["y"] - 76) // 20
                wd["delay"] = 0.035 * (rows - r) + 0.006 * ((wd["x"] - 800) / 50) + rng.uniform(0, 0.03)
                wd["whole"] = 0.55
            else:  # the logits are in her way: they come apart at once
                wd["delay"] = rng.uniform(0.0, 0.08)
                wd["whole"] = 0.3
            wd["specks"] = [(rng.uniform(-4, 36), rng.uniform(-2, 12), rng.uniform(24, 42), rng.uniform(0, 6.28),
                             rng.uniform(0.5, 0.9)) for _ in range(3 if wd["kind"] == "t" else 5)]
        self.words = words
        # convergence: every particle and every cell of her gets its own departure
        for q in shed + contact:
            q["d"] = rng.uniform(0.0, 1.05)
        for wd in words:
            wd["d"] = [rng.uniform(0.0, 1.05) for _ in wd["specks"]]
        self.rng = rng

    def shed_pos(self, q, t):
        age = t - q["b"]
        x = q["x0"] + q["amp"] * math.sin(q["w"] * age + q["ph"]) + q["drift"] * age
        y = q["y0"] + q["v"] * age
        fy = S.floor_y(x) - 2
        lv = q["lv"] * (1 - 0.35 * clamp(age / 6))
        if y >= fy:
            # settled: find the landing point (fall is linear in y)
            ta = (fy - q["y0"]) / q["v"]
            x = q["x0"] + q["amp"] * math.sin(q["w"] * ta + q["ph"]) + q["drift"] * ta
            y = S.floor_y(x) - 2
            lv *= 0.8
        return x, y, lv

    def contact_pos(self, q, t):
        age = t - q["b"]
        e = ease_out(age / 1.4)
        x = q["x0"] + q["side"] * e
        y = S.floor_y(x) - 2 - q["up"] * math.sin(math.pi * clamp(age / 1.4))
        return x, y, q["lv"] * (1 - 0.3 * clamp(age / 4))

    def word_state(self, wd, t):
        """('whole', xy, alpha) while the word still holds together, then ('specks', [(x, y, lv)])."""
        a = max(0.0, t - self.T0 - wd["delay"])
        L = wd["whole"]
        if a < L:
            return ("whole", (wd["x"] + 2 * math.sin(a * 5 + wd["x"]), wd["y"] + 10 * a + 36 * a * a), 1 - 0.7 * a / L, a)
        out = []
        b = a - L
        y_l = 10 * L + 36 * L * L
        for ox, oy, v, ph, lv in wd["specks"]:
            x = wd["x"] + ox + 9 * math.sin(b * 1.1 + ph) + 3 * b
            y = wd["y"] + oy + y_l + v * b + 14 * min(b, 0.5)
            fy = S.floor_y(x) - 2
            if y >= fy:
                y = fy
                lv *= 0.8
            out.append((x, y, lv * (1 - 0.3 * clamp(b / 5))))
        return ("specks", out, 1.0, a)

    def converge(self, x, y, d, t):
        """Pull a particle into the cell over the last two seconds; None once it has been taken in."""
        if t < self.TC:
            return x, y, 1.0
        w = ease_in(clamp((t - self.TC - d) / 0.75))
        if w >= 1:
            return None
        px, py = self.P
        bx, by = bezier((x, y), (px, py), 0.18, w)
        return bx, by, 1 + 0.4 * w

    def absorbed(self, t):
        if t < self.TC:
            return 0.0
        k = [clamp((t - self.TC - q["d"]) / 0.75) >= 1 for q in self.shed + self.contact]
        return sum(k) / max(1, len(k))

    # --- the frame
    def render(self, t, n, raw=False):
        self.build()
        shot = ALL()[I_WHALE]
        canvas, ctx = raw_body(shot, t, n)
        if t < self.T0 + 1.3:  # the sea floor spreads out from where she will go down
            bare, _ = raw_body(shot, t, n, {"floor": 0.0})
            canvas = reveal(bare, canvas, t, radial((S.HX, S.FLOOR + 20), self.T0 + 0.12, 620.0),
                            region=(0, 440, W, 616), seed=94)
        img = canvas.convert("RGBA")
        snow = blank()
        d = ImageDraw.Draw(snow)

        def speck(x, y, sz, lv, d_=None):
            if d_ is not None:
                r = self.converge(x, y, d_, t)
                if r is None:
                    return
                x, y, g = r
                lv = min(1.0, lv * g)
            col = blue(lv)
            d.rectangle([x, y, x + sz - 1, y + sz - 1], fill=col + (255,))

        for q in self.shed:
            if t < q["b"]:
                continue
            x, y, lv = self.shed_pos(q, min(t, self.TC))
            speck(x, y, q["sz"], lv, q["d"])
        for q in self.contact:
            if t < q["b"]:
                continue
            x, y, lv = self.contact_pos(q, min(t, self.TC))
            speck(x, y, q["sz"], lv, q["d"])
        img.alpha_composite(snow)
        # her
        img.alpha_composite(self.her(t))
        # the cell she pours into
        if t >= self.TC:
            f = self.absorbed(t)
            hk = self.her_taken(t)
            k = clamp(0.35 * f + 0.65 * hk)
            if k > 0.01:
                S.put_cell(img, *self.P, s=3 + 7 * k ** 0.7, glow=k)
        # the love words sink (drawn over her: they are the old interface falling past)
        wl = blank()
        wd_ = ImageDraw.Draw(wl)
        for wd in self.words:
            kind, data, al, a = self.word_state(wd, t)
            if kind == "whole":
                if wd["kind"] == "t":
                    sp, off = text_sprite(wd["s"], wd["f"].path, wd["f"].size, wd["col"])
                    x, y = data
                    wl.alpha_composite(tk.scale_alpha(sp, al), (max(0, round(x + off[0])), max(0, round(y + off[1]))))
                else:
                    x0, y0, x1, y1 = wd["box"]
                    x, y = data
                    wd_.rectangle([x, y, x + (x1 - x0), y + (y1 - y0)], fill=rgba(wd["col"], 255 * al))
            else:
                for (x, y, lv), dd in zip(data, wd["d"]):
                    r = self.converge(x, y, dd, t)
                    if r is None:
                        continue
                    x, y, g = r
                    wd_.rectangle([x, y, x + 1, y + 1], fill=blue(min(1.0, lv * g)) + (255,))
        img.alpha_composite(wl)
        if raw:
            return img, ctx
        retract = ease_io((t - self.T0) / self.RETRACT)
        return finish(t, img, ctx, retract)

    def her_taken(self, t):
        if t < self.TC:
            return 0.0
        return clamp((t - self.TC - 0.2) / 1.55)

    def her(self, t):
        """Her layer in the viewport: the pane frame and softmax fade while she drifts out of the pane; below the sea
        floor she is gone into the sediment; in the last two seconds her cells leave, the farthest first, for the
        cell on the floor."""
        out = blank()
        e = ease_io((t - self.T0) / self.RETRACT)
        if e < 0.999:  # the pane she leaves: frame, title and softmax fade where they are
            pane = blank()
            c = kit.engine.Ctx(pane, ImageDraw.Draw(pane), t, 0.0, 1.0, random.Random(n_seed(t)))
            x0, y0, x1, y1 = kit.LEFT
            tk.box(c.d, x0, y0, x1, y1, "/dev/me  state=D", 0.45 + 0.35 * kit.engine.pulse(t), spinner=t)
            fnt = font(F_MONO, 13)
            dd = c.d
            dd.line([x0 + 12, y1 - 70, x1 - 12, y1 - 70], fill=amb(0.25))
            dd.text((x0 + 14, y1 - 66), "cls.expression  softmax", font=fnt, fill=amb(0.5))
            for i, (name, p) in enumerate(S.TRAPPED_DIST):
                p = max(0.0, min(1.0, p + 0.015 * math.sin(t * 7 + i * 2)))
                yy = y1 - 48 + i * 15
                dd.text((x0 + 14, yy), f"{name:<11}", font=fnt, fill=blue(0.95) if i == 0 else amb(0.6))
                dd.rectangle([x0 + 120, yy + 4, x0 + 120 + int(170 * p), yy + 11],
                             fill=blue(0.9) if i == 0 else amb(0.45))
                dd.text((x0 + 298, yy), f"{p:.2f}", font=fnt, fill=amb(0.7))
            out.alpha_composite(tk.scale_alpha(pane, 1 - e))
        fig = self.her_layer(t)
        dx, dy = self.offset(t)
        dx, dy = round(dx), round(dy)
        moved = blank()
        moved.alpha_composite(fig.crop((max(0, -dx), max(0, -dy), W - max(0, dx), H - max(0, dy))),
                              (max(0, dx), max(0, dy)))
        # the sediment takes her: nothing of her below the floor surface
        clip = Image.new("L", (W, H), 0)
        cd = ImageDraw.Draw(clip)
        for x in range(0, W, 5):
            cd.rectangle([x, 0, x + 4, S.floor_y(x) - 3], fill=255)
        if t >= self.TC:  # her cells leave for the cell on the floor, the farthest first
            px, py = self.P
            A = moved.getchannel("A")
            bb = A.getbbox()
            dots = blank()
            dd = ImageDraw.Draw(dots)
            if bb:
                reach = max(math.hypot(x_ - px, y_ - py) for x_ in (bb[0], bb[2]) for y_ in (bb[1], bb[3]))
                cw, ch = self.cw, self.ch
                gx, gy = self.grid[0] + dx, self.grid[1] + dy
                for cy_ in range(bb[1] - (bb[1] - gy) % ch, bb[3], ch):
                    for cx_ in range(bb[0] - (bb[0] - gx) % cw, bb[2], cw):
                        dist = math.hypot(cx_ + 2 - px, cy_ + 5 - py)
                        dep = self.TC + 0.1 + 1.2 * (1 - min(1.0, dist / reach))
                        if t < dep:
                            continue
                        cd.rectangle([cx_, cy_, cx_ + cw - 1, cy_ + ch - 1], fill=0)
                        u = clamp((t - dep) / 0.45)
                        if u >= 1 or cy_ + 5 > S.floor_y(cx_) - 3:
                            continue
                        if A.getpixel((min(W - 1, cx_ + 2), min(H - 1, cy_ + 5))) < 60:
                            continue
                        x, y = bezier((cx_ + 2, cy_ + 5), (px, py), 0.2, ease_in(u))
                        xp, yp = bezier((cx_ + 2, cy_ + 5), (px, py), 0.2, ease_in(max(0.0, u - 0.12)))
                        dd.line([xp, yp, x, y], fill=tk.BLUE_MID + (150,), width=1)
                        dd.rectangle([x - 1, y - 1, x + 1, y + 1], fill=tk.BLUE_HI + (255,))
        fade = 1 - 0.3 * S.smooth((t - self.T0 - 3.0) / (self.TC - self.T0 - 3.0))  # she thins to a trace
        if fade < 0.999:
            clip = clip.point(lambda v: int(v * fade))
        moved.putalpha(ImageChops.multiply(moved.getchannel("A"), clip))
        out.alpha_composite(moved)
        if t >= self.TC:
            out.alpha_composite(dots)
        return out


def n_seed(t):
    return int(t * FPS) * 7919


WF = [None]


def whale_fall(t, n):
    if WF[0] is None:
        WF[0] = WhaleFall()
    return WF[0].render(t, n)


# ---------------------------------------------------------------- cut 95: the last Execution

class C95(Cut):
    """whale_fall -> last_execution (HIT, hard cut on 'Execution'). Nothing crosses but her cell and the sea-floor
    line: the whole picture goes red for six frames around them, the chrome snaps back in its error state and shakes
    2 px, the red word decodes over the floor and stays until the music stops. (OWN; this class only documents it.)"""
    pre, post = 0.0, 0.0


def last_execution(t, n):
    if WF[0] is None:
        WF[0] = WhaleFall()
    wf = WF[0]
    wf.build()
    shot = ALL()[I_LAST]
    T = shot.start
    lt = t - T
    fr = int(round(lt * FPS))
    canvas, ctx = raw_body(shot, t, n)
    img = canvas.convert("RGBA")
    pulse = max(0.0, 1 - lt / 0.2) + 0.6 * max(0.0, 1 - abs(t - kit.engine.beat_t(446)) / 0.12)
    cell = dict(s=10 + 2 * min(1.0, pulse), glow=1.0)
    if fr >= 6:
        S.put_cell(img, *wf.P, **cell)
        return finish(t, img, ctx, 0.0)
    # the hit: everything that was there goes red, and away; only the floor line and her cell keep their colour
    if not hasattr(wf, "_red"):
        nn = math.ceil(T * FPS) - 1
        pic, _ = wf.render(nn / FPS, nn, raw=True)
        wf._red = ImageOps.colorize(pic.convert("L"), black=tk.BG, white=tk.RED, mid=(150, 30, 20)).convert("RGBA")
    k = [1.0, 1.0, 0.8, 0.55, 0.3, 0.12][fr]
    img.alpha_composite(tk.scale_alpha(wf._red, k))
    img.alpha_composite(Image.new("RGBA", (W, H), tk.RED + (int(60 * k * (1 if fr < 2 else 0.5)),)))
    shake = (2, 0) if fr == 0 else (-2, 1) if fr == 1 else (0, 0)  # the chrome snaps back and shakes
    layer = kit.chrome(Image.new("RGBA", (W, H), (0, 0, 0, 0)), t, ctx, 0.0, None)
    img.alpha_composite(layer.crop((max(0, -shake[0]), max(0, -shake[1]), W, H)), (max(0, shake[0]), max(0, shake[1])))
    if fr < 3:  # on the hit itself the chrome is red too
        rgb = img.convert("RGB")
        red_all = ImageOps.colorize(rgb.convert("L"), black=tk.BG, white=tk.RED, mid=(150, 30, 20))
        img = Image.blend(rgb, red_all, [0.9, 0.7, 0.4][fr]).convert("RGBA")
    S.draw_floor(ImageDraw.Draw(img), 0.6)
    S.put_cell(img, *wf.P, **cell)
    return kit.engine.post(img.convert("RGB"), None)


class C96(Cut):
    """last_execution -> black (HIT, the hard cut where the song stops dead, 207.083 s). 'execution' is on screen to
    the last frame; the black keeps only her cell, at the same place; at 208.31 s it slides (12 frames) to the prompt
    and becomes the cursor of '> 在吗？', typed like the lyric band, held to the end. (Scene shot_black.)"""
    pre, post = 0.0, 0.0


CUTS = {86: C86, 87: C87, 88: C88, 89: C89, 90: C90, 91: C91, 92: C92, 93: C93, 94: C94, 95: C95, 96: C96}
OWN = {I_WHALE: whale_fall, I_LAST: last_execution}


def setup(v1):
    C.DELAY["shot_learn_love"] = C87.LAND  # the curve starts from the cell that lands at its origin
    C.SHOT_HOOKS.setdefault("shot_learn_love", {})["pre_age"] = C87.LAND
