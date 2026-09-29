"""Review 1 (the author's notes on film v1, 2026-09-28): fixes that need no design choice. Loaded by dsh_her.install
right after dsh_patch_fix, for the whole film; every wrap is guarded, so install() may run more than once.

  1  feature maps (1:03, 2:47)  the maps of the conv shots grow row by row with the scan, and until the scan reached
                                a row it was cut off: the first rows of the maxpool maps read as a squashed figure.
                                The rows still to come now stay as a dim ghost of the whole map.
  2  the twelve samples         upper-body crops sitting on the tile floor read as squat lumps, off centre. Every
     (0:55, 2:44, 2:46)         sample is her full body, centred in its tile (chorus 1's simulations, where they come
                                from, too). An executed sample flashes, turns red, tears, and dims to 40 %.
  3  god hand-off (1:25)        the props she hands the process tree lifted off her avatar and crossed the chat;
                                they now leave from the window's right edge, level with their rows.
  4  fp8 (1:28)                 the posterise was cut to her old figure box and re-tinted it blue, so the window went
                                half blue, half pink. The whole window now drops to the format's levels in its own
                                colours (the trance dissolve is unchanged).

Review 2 (the second review, 2026-09-28):

  5  lyric band                 a word types over up to 0.25 s from its onset and every letter then flickers for
                                0.08 s, but the line is swapped when the next one starts: completion, back, free and
                                nine more line ends never showed whole. Now every line's last word is whole and still
                                for HOLD (6 frames) before the swap: its typing is compressed so it lands in time (it
                                still starts on its sung onset); a word sung too close to the swap comes out whole
                                at its onset without the flicker, and the swap waits at most SWAP_WAIT (2 frames)
                                for it. Inside that last window the word is exempt from the section's glitch.
  6  pid of you                 the god tree gave 'you' pid 1000 + 7 * 7 = 1049, the executions 1000 + 11 * 7 = 1077;
                                the tree now says 1077 too.
"""
from __future__ import annotations

import copy
import math
import random
from functools import lru_cache

from PIL import Image

D = None                      # dsh_her, set by install
HOLD = 6 / 24                 # 5: a line's last word is whole and still this long before the line is swapped
SWAP_WAIT = 2 / 24            # 5: at most this much later than the next line's first sung word
YOU_PID = 1077                # 6
GHOST = 0.22                  # 1: the unscanned rows of a feature map
DIM = 0.40                    # 2: an executed sample, settled
FLASH, TEAR, FADE = 2 / 24, 0.30, 0.45


def centred(art: Image.Image, w: int, h: int) -> Image.Image:
    """Her figure (not the sprite canvas, where she stands off centre) in the middle of a w x h canvas."""
    box = art.getchannel("A").getbbox()
    if box:
        art = art.crop(box)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.alpha_composite(art, ((w - art.width) // 2, (h - art.height) // 2))
    return out


def scale_alpha(im: Image.Image, k: float) -> Image.Image:
    out = im.copy()
    out.putalpha(im.getchannel("A").point(lambda v: round(v * k)))
    return out


def install(D_, v2):
    global D
    D = D_
    import h3_full
    import kit
    import scenes_exec as X
    import s_deploy as SDp
    import tuikit as tk

    spaces = h3_full.namespaces()

    # 1. feature maps: the rows the scan has not reached are a ghost, not missing
    if not getattr(tk.tile_from_lum, "_r1", False):
        otl = tk.tile_from_lum

        def tile_from_lum(lum, px, tint="amber", reveal_rows=None):
            if reveal_rows is None:
                return otl(lum, px, tint)
            out = scale_alpha(otl(lum, px, tint), GHOST)
            out.alpha_composite(otl(lum, px, tint, reveal_rows=reveal_rows))
            return out

        tile_from_lum._r1 = True
        h3_full.replace_alias(otl, tile_from_lum, spaces)
        tk.tile_from_lum = tile_from_lum

    # 2a. chorus 1's simulations: diffusion_tile(expr, "upper", 166, 122, 3, s) pasted bottom-centred in a 178 x 152
    # cell (label on top) -> her full body in a canvas that fills the cell below the label, so it lands centred
    def sim_tile(orig):
        def diffusion_tile(expr, crop, w, h, px, s):
            if crop == "upper" and (w, h) == (166, 122):
                return centred(orig(expr, "full", w, h - 6, px, s), 178, 124)
            return orig(expr, crop, w, h, px, s)
        diffusion_tile._r1 = True
        return diffusion_tile

    for space in spaces + [X.SC.__dict__]:
        fn = space.get("diffusion_tile")
        if callable(fn) and getattr(fn, "__name__", "") == "diffusion_tile" and not getattr(fn, "_r1", False):
            space["diffusion_tile"] = sim_tile(fn)

    # 2b. the red chorus's samples: the same full body, centred under the tile's label (tile_art_xy and draw_tile
    # paste the art bottom-centred; a canvas of the tile's inner size puts it in the middle)
    if not getattr(X.tile_art, "_r1", False):
        def tile_art(i):
            art = X.SC.diffusion_tile(X.tile_expr(i), "full", X.TILE_W - 20, X.TILE_H - 36, 3, 1.0)
            return centred(art, X.TILE_W - 8, X.TILE_H - 28)

        new = h3_full.dynamic(tile_art)
        new._r1 = True
        h3_full.replace_alias(X.tile_art, new, spaces)
        X.tile_art = new

    exec_all = next(s for s in v2.ALL if getattr(s.fn, "__name__", "") == "shot_execute_all")

    def crossed_at(i):
        """execute_all crosses tile i when int(u * 14) passes i."""
        return exec_all.start + (exec_all.end - exec_all.start) * (i + 1) / 14

    def executed(art, age, i):
        if age < FLASH:                                           # the hit: one white frame
            white = Image.new("RGBA", art.size, (255, 236, 228, 255))
            white.putalpha(art.getchannel("A"))
            return white
        red = tk.tint_colorize(art.convert("L"), "red").convert("RGBA")
        red.putalpha(art.getchannel("A"))
        if age < TEAR:                                            # rows tear sideways, less and less
            rnd = random.Random(i * 7919 + round(age * 24))
            torn = Image.new("RGBA", red.size, (0, 0, 0, 0))
            k = 1 - age / TEAR
            for r in range(0, red.height, 6):
                off = round(rnd.choice((-1, 1)) * rnd.randint(0, 14) * k) if rnd.random() < 0.55 else 0
                torn.alpha_composite(red.crop((0, r, red.width, min(red.height, r + 6))), (max(0, off), r),
                                     (max(0, -off), 0))
            red = torn
        return scale_alpha(red, max(DIM, 1 - (1 - DIM) * (age - FLASH) / FADE))

    if not getattr(X.draw_tile, "_r1", False):
        def draw_tile(d, img, i, crossed, x=None, y=None):
            x0, y0 = X.tile_origin(i)
            x, y = (x0, y0) if x is None else (x, y)
            art = X.tile_art(i)
            pos = (x + (X.TILE_W - 8 - art.width) // 2, y + X.TILE_H - 10 - art.height)
            if crossed:
                t = D.CUR[0]
                age = t - crossed_at(i) if exec_all.start <= t < exec_all.end else 9.0
                art = executed(art, age, i)
            img.paste(art, pos, art)
            d.rectangle([x, y, x + X.TILE_W - 8, y + X.TILE_H - 8], outline=X.red(0.7))
            d.text((x + 6, y + 4), f"#{i:04d}", font=X.font(X.F_MONO, 12), fill=X.red(0.9))
            if crossed:
                d.line([x + 6, y + 6, x + X.TILE_W - 14, y + X.TILE_H - 14], fill=X.red(1.0), width=4)
                d.line([x + X.TILE_W - 14, y + 6, x + 6, y + X.TILE_H - 14], fill=X.red(1.0), width=4)

        draw_tile._r1 = True
        h3_full.replace_alias(X.draw_tile, draw_tile, spaces)
        X.draw_tile = draw_tile
        if hasattr(X.sample0_sprite, "cache_clear"):
            X.sample0_sprite.cache_clear()

    # 3. god: the props leave from the window's right edge, level with their rows (not off the avatar, over the chat)
    def ov_god(t, n):
        layer = SDp.blank()
        s = SDp.BY["shot_god"]
        for i, name in enumerate(SDp.SD.PROCS):
            if name not in SDp.SD.ICONS:
                continue
            td = s.start + SDp.SD.god_row_t(i)
            tl = td + SDp.SD.ICON_LAND
            if not td - 0.1 <= t < tl + 0.02:
                continue
            dst = SDp.SD.icon_xy(i)
            src = (kit.LEFT[2] + 16, dst[1])
            sp = SDp.SD.icon_sprite(SDp.SD.ICONS[name])
            if t < td:
                k = SDp.clamp((t - (td - 0.1)) / 0.1)
                SDp.place(layer, SDp.haloed(sp, 0.8 * k), src, 1.3, k)
                continue
            u = SDp.clamp((t - td) / SDp.SD.ICON_LAND)
            pos = SDp.bezier(src, dst, -0.25, SDp.ease_io(u))
            SDp.place(layer, SDp.haloed(sp, 0.7 * (1 - u)), pos, SDp.lerp(1.3, 1.0, SDp.ease_io(u)))
        return layer

    for table in (v2.OVERLAY, SDp.OVERLAY):
        old = table.get("shot_god")
        if old is not None and not getattr(old, "_r1", False):
            def god(t, n, old=old):
                return ov_god(t, n) if D.inside(t) else old(t, n)
            god._r1 = god._dsh = True
            table["shot_god"] = god

    # 4. fp8: the whole window, in its own colours
    if not getattr(SDp.her_filter, "_r1", False):
        def quantize(layer, levels):
            step = 255 / (levels - 1)
            lut = [round(round(v / step) * step) for v in range(256)]
            q = layer.convert("RGB").point(lut * 3).convert("RGBA")
            q.putalpha(layer.getchannel("A"))
            return q

        ohf = SDp.her_filter

        def her_filter(layer, t):
            if not D.inside(t):
                return ohf(layer, t)
            lv = SDp.levels_at(t)
            if lv < 256:
                layer = quantize(layer, max(2, lv))
            hv = SDp.heat_at(t)
            if hv > 0.01:
                layer = SDp.dissolve(layer, t, hv)
            return layer

        her_filter._r1 = True
        SDp.her_filter = her_filter

    # 5. the lyric band: every line's last word whole and still before the line is swapped
    import words as W
    if not getattr(W.lines, "_r1", False):
        orig_lines, orig_typed, orig_flicker = W.lines, W.typed, W.flicker

        @lru_cache(None)
        def lines():
            out = copy.deepcopy(orig_lines())
            for ln in out:
                end = ln["show_until"]
                if ln["fade_until"] == end:              # swapped by the next line, not faded before a break
                    wait = min(SWAP_WAIT, max(0.0, HOLD - (end - ln["words"][-1][2])))
                    ln["show_until"] = ln["fade_until"] = end = end + wait
                limit = end - HOLD - W.SETTLE              # the last letter must be out by here to settle in time
                late, ws = set(), []
                for j, (i0, i1, onset, td) in enumerate(ln["words"]):
                    if onset > limit:
                        late.add(j)
                        td = 0.0
                    elif onset + td > limit:
                        td = limit - onset
                    ws.append((i0, i1, onset, td))
                ln["words"], ln["late"], ln["calm"] = ws, late, end - HOLD
            return out

        def typed(ln, t):
            n_out, when = orig_typed(ln, t)
            if "late" not in ln:
                return n_out, when
            when, ws = list(when), ln["words"]
            for j, (i0, i1, onset, td) in enumerate(ws):
                if j in ln["late"] or (j == len(ws) - 1 and t >= ln["calm"]):
                    nxt = ws[j + 1][0] if j + 1 < len(ws) else len(ln["text"])
                    for q in range(i0, nxt):
                        if when[q] <= t:
                            when[q] = -math.inf          # age inf: shown clean (see flicker)
            return n_out, when

        def flicker(shown, ages, rng, corrupt=0.0):
            out = orig_flicker(shown, ages, rng, corrupt)
            return "".join(ch if a == math.inf else o for ch, o, a in zip(shown, out, ages))

        lines._r1 = True
        W.lines, W.typed, W.flicker = lines, typed, flicker

    # 6. one pid for 'you'
    import scenes_deploy as SDe
    if not getattr(SDe.god_row_text, "_r1", False):
        ogr = SDe.god_row_text

        def god_row_text(i):
            s = ogr(i)
            return s.replace(f"{1000 + i * 7:5d}", f"{YOU_PID:5d}") if SDe.PROCS[i] == "you" else s

        god_row_text._r1 = True
        h3_full.replace_alias(ogr, god_row_text, spaces)
        SDe.god_row_text = god_row_text
