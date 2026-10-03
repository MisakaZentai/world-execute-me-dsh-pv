"""Lyric line 59's four stressed words (118.2-121.7 s): she digs up memories. Loaded by dsh_her.install() (install(D, v2),
D = dsh_her); everything is in memory and nothing acts outside 118.1-121.8 s.

From GONE (115.42 s) she is one blue cursor. On each stressed word of line 59 (w(59, 0/2/3/5)) the cursor jumps
(2 frames, landing on the sung word) to one file of the right side's `ls -la ~/memory/you/`: the row inverts in her
colour and the memory opens beside it as a real dsh message, each one larger and brighter than the last; the one
before fades as the next arrives.

  If   w(59,0) 118.24  first_hello.txt       your first bubble 你好 (A1, sent at 14.95 s)
  can  w(59,2) 118.98  your_cat.png          your cat photo with its caption (C, 81.85 s)
  if   w(59,3) 119.38  laugh_2026-03-14.wav  dsh's own file card for the wav, with a burst of its waveform
  can  w(59,5) 119.92  last_message.txt      your last bubble 你会一直在吗？ (D, 106.80 s)

The bubbles are screenshots of dsh's own markup and CSS (the classes of build_frame.user and batch_c.you_img, dsh's
Sixlwa_fileCard with its FileTypeIcon), deepsea palette, 2x, transparent: `python dsh_patch_mem.py page` writes
mem.html, `node mem_shot.mjs` saves them into mem_sprites/.

How it meets the right side (s_reward.C55, the carry into erase; nothing there is changed):
  - Rows 1-3: the bubble opens to the left of the row, right-aligned where the dsh chat used to be; the cursor
    stands between the bubble and the row. The inverted row drains with the listing (C55's own drain times).
  - The defrag pass that breaks her pane (C55.her) reaches her cell at TEAR (~119.59, row 3); the 20 cells it tears
    off her fly into the defrag grid as before, sampled from her layer at the cut, where she now stands. She is
    not gone: from TEAR the cursor is drawn by this patch's overlay.
  - can (119.92): last_message.txt is already flying (C55's carrier). The cursor jumps to it and your last bubble
    opens under the flying name and rides with it into the compression panel (it lands at 120.16).
  - Erase (120.21): the bubble breaks into defrag-sized tiles in reading order; the tiles fly into the defrag grid,
    land in its bottom rows in reading order and are removed there by the defrag pass (erase's own sweep), each
    with a flash. The cursor goes back to cursor_centre (the bottom-left) and blinks there until the forged window
    slides back (C56 overwrites that spot at ~121.65; the window returns at 121.77 unchanged).

Drawn in two places: kit.her_layer (the cursor until TEAR: C55 samples and breaks it there) and v2.OVERLAY for
shot_memory_ls / shot_erase (rows, bubbles, tiles, and the cursor from TEAR), so all of it goes through post and
under the chrome (lyric band) like the rest of the frame.
"""
from __future__ import annotations

import math
import random
import sys
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

HERE = Path(__file__).parent
SPRITES = HERE / "mem_sprites"
FPS = 24
DSF = 2                                   # mem_shot.mjs screenshots at 2x
TAG = "_mem"                              # marks every wrapper (install() may run more than once per process)

SPAN = (118.10, 121.80)
CARET_X = 388.0                           # the cursor between a bubble and its row (inside C55.REG: it is torn there)
BUB_R = 376                               # right edge of the row bubbles (the dsh chat column's side)
ROW_X = 430                               # scenes_userleft.shot_memory_ls: rows at (430, 84 + 40 i), consola 18
MOVE = 3                                  # frames from rest to landing: 2 in-between frames, landing on the word
POP = 4                                   # frames of the scale-in (overshoot, then hold)
FADE = 5                                  # frames of the previous bubble's fade
SOLID = 0.35                              # the cursor stays lit this long after it lands, then blinks as before
GAP = 10                                  # under the flying name: gap to the bubble
TILE = (18, 22)                           # the defrag grid's pitch (s_reward.C55.CELL)
FLY = 0.32                                # a tile's flight into the grid
BLUE = (77, 107, 254)                     # her cursor (dsh_her.her_layer)


def sprite_specs():
    from sung_words import w
    return [  # word, ls row, sprite, scale, halo, flash
        dict(word=w(59, 0), row=1, name="first_hello.txt", sprite="hello", scale=1.00, halo=0.30, flash=0.12),
        dict(word=w(59, 2), row=4, name="your_cat.png", sprite="cat", scale=1.15, halo=0.50, flash=0.20),
        dict(word=w(59, 3), row=3, name="laugh_2026-03-14.wav", sprite="wav", scale=1.25, halo=0.70, flash=0.28),
        dict(word=w(59, 5), row=7, name="last_message.txt", sprite="last", scale=1.65, halo=0.95, flash=0.35),
    ]


def frame_t(t):
    return round(t * FPS) / FPS


def clamp(u):
    return max(0.0, min(1.0, u))


# ---------------------------------------------------------------- the sprite page (dsh markup, dsh CSS)

def file_icon_svg():
    """dsh's FileTypeIcon for a .wav (kind 'other': the muted page), with the classes that colour it."""
    import re
    from icons import _bundle
    s = _bundle()
    body = re.search(r'[,; ]SC="(M[^"]+)"', s).group(1)
    fold = re.search(r'[,; ]Sc="(M[^"]+)"', s).group(1)
    m = re.search(r"wc=\{icon:(\w+),.*?other:(\w+)[,}]", s)
    cls = [re.search(r'[,; ]%s="([^"]+)"' % re.escape(v), s).group(1) for v in m.groups()]
    return (f'<svg width="28" height="28" class="{cls[0]} {cls[1]} Sixlwa_fileIcon" viewBox="0 0 28 28" fill="none" '
            f'xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="{body}" fill="currentColor"/>'
            f'<path d="{fold}" fill="var(--dsw-static-neutral-400)"/></svg>')


def file_size_text(n):
    """dsh's fileSizeText."""
    if n < 1024:
        return f"{n}B"
    k = n / 1024
    return f"{k:.1f}KB" if k < 10 else f"{round(k)}KB"


def page():
    """mem.html: the four memories as dsh renders your messages, one [data-sprite] element each."""
    from build_frame import esc, user
    from batch_c import you_img
    size = 1000 + (3 * 7919) % 90000          # the wav's size in the ls listing (shot_memory_ls)
    card = f"""
<div class="Sixlwa_userRow"><div class="Sixlwa_userStack">
 <div class="Sixlwa_attachmentRow" data-message-attachments="true">
  <span class="Sixlwa_fileCard" title="laugh_2026-03-14.wav" data-sprite="wav">{file_icon_svg()}<span class="Sixlwa_fileContent"><span class="Sixlwa_fileName">laugh_2026-03-14.wav</span><span class="Sixlwa_fileMeta">{esc("WAV " + file_size_text(size))}</span></span></span>
 </div>
</div></div>"""
    parts = [
        user("你好").replace('class="Sixlwa_bubble"', 'class="Sixlwa_bubble" data-sprite="hello"', 1),
        you_img("这是我家的猫～").replace('class="Sixlwa_userStack"', 'class="Sixlwa_userStack" data-sprite="cat"', 1),
        card,
        user("你会一直在吗？").replace('class="Sixlwa_bubble"', 'class="Sixlwa_bubble" data-sprite="last"', 1),
    ]
    head = (HERE / "seg.html").read_text(encoding="utf8").split("</head>")[0]
    style = ("<style>html,body{background:transparent!important}"
             " #app{display:block;height:auto;padding:8px 14px;--dsh-chat-content-width:354px}"
             " .spr{margin:0 0 24px}</style>")
    doc = (head + style + '</head>\n<body data-ds-dark-theme="true"><div id="app">\n'
           + "".join(f'<div class="spr">{p}</div>\n' for p in parts) + "</div></body></html>")
    (HERE / "mem.html").write_text(doc, encoding="utf8")
    print("mem.html")


# ---------------------------------------------------------------- the patch

def install(D, v2):
    import kit
    # install() runs once per render chunk, and a pool worker renders several chunks: dsh_her wraps kit.her_layer
    # again each time (its GONE..BACK branch does not call down), so the cursor wrapper goes on top again; the
    # overlays live in v2.OVERLAY, which persists, and are registered once
    if getattr(kit.her_layer, TAG, False):
        return
    missing = [s["sprite"] for s in sprite_specs() if not (SPRITES / f"{s['sprite']}.png").exists()]
    if missing:
        print("dsh_patch_mem: mem_sprites missing", missing, "(python dsh_patch_mem.py page && node mem_shot.mjs)")
        return

    import s_reward as SR
    import s_userleft as UL
    import scenes_reward as R
    import scenes_userleft as U
    tk = kit.tk

    c55 = next(c for c in v2.CUTS if isinstance(c, SR.C55))
    c56 = next(c for c in v2.CUTS if isinstance(c, SR.C56))
    erase_shot = next(s for s in v2.ALL if s.fn.__name__ == "shot_erase")
    T55 = c55.T
    NX, NY = c55.NAME_XY
    LAND = T55 + c55.LAND
    f18 = tk.font(tk.F_MONO, 18)

    MEMS = sprite_specs()
    from sung_words import w
    ERASE = frame_t(w(60, 0))                      # 120.208: the frame of "Erase"
    for m in MEMS:
        m["A"] = frame_t(m["word"])
        assert U.FILES[m["row"]] == m["name"], (m["row"], U.FILES[m["row"]])
        sp = Image.open(SPRITES / f"{m['sprite']}.png").convert("RGBA")
        m["sp"] = sp.resize((round(sp.width / DSF * m["scale"]), round(sp.height / DSF * m["scale"])),
                            Image.Resampling.LANCZOS)
    A = [m["A"] for m in MEMS]
    RET = ERASE + 6 / FPS                           # the cursor is back at cursor_centre (the tiles have lifted)

    # ---- geometry of the ls rows (shot_memory_ls draws them exactly like this)
    def row_geom(i):
        size = 1000 + (i * 7919) % 90000
        head = f"-rw-r--r--  me  me  {size:>6}  "
        y = 84 + i * 40
        l, tp, r, b = f18.getbbox(head + U.FILES[i])
        return head, y, (ROW_X + l - 4, y + tp - 4, ROW_X + r + 5, y + b + 4)

    ROWS = {m["row"]: row_geom(m["row"]) for m in MEMS[:3]}

    def row_cy(i):
        return (ROWS[i][2][1] + ROWS[i][2][3]) / 2

    # ---- the carrier (C55): where last_message.txt is drawn at t, and the bubble that hangs under it
    def label_at(t):
        """(x, y, size) of C55's flying name, as its render() draws it; after it lands, the message line."""
        if t >= LAND + SR.LOCK:
            return R.MSG_XY[0], R.MSG_XY[1], 20
        if t < T55:
            return NX, NY, 18
        u = clamp((t - T55) / (c55.LAND + 0.06))
        e = SR.settle(u, 0.04, 0.12)
        px, py = kit.bezier((NX, NY), R.MSG_XY, -0.25, e)
        size = round(kit.lerp(18, 20, u) * (1 + 0.5 * math.sin(math.pi * min(1.0, u * 1.3))))
        return px, py, size

    LAST = MEMS[3]

    def last_box(t):
        """Top-left of your last bubble (full size) under the flying name."""
        px, py, size = label_at(t)
        l, tp, r, b = tk.font(tk.F_MONO_B, size).getbbox(c55.NAME)
        return px + l, py + b + GAP

    def last_caret(t):
        x, y = last_box(t)
        sp = LAST["sp"]
        return x + sp.width + 6 + D.CURSOR[0] / 2, y + sp.height / 2

    # ---- the cursor's path: home -> row 1 -> row 4 -> row 3 -> the flying name -> home
    @lru_cache(maxsize=4096)
    def home(t):
        return D.cursor_centre(t, UL, kit.LEFT)

    def rest(k, t):
        if k == 0 or k == 5:
            return home(t)
        if k == 4:
            return last_caret(t)
        i = MEMS[k - 1]["row"]
        return CARET_X, row_cy(i)

    ARRIVE = A + [RET]                               # arrival of legs 1..5

    def pos(t):
        k = 0
        for j, a in enumerate(ARRIVE):
            if t >= a - MOVE / FPS:
                k = j + 1
        if k == 0:
            return home(t), False
        a = ARRIVE[k - 1]
        if t >= a:
            return rest(k, t), False
        u = (t - (a - MOVE / FPS)) / (MOVE / FPS)
        e = 1 - (1 - clamp(u)) ** 2
        # a straight jump from where she was to where the target will be on the word (the name is flying)
        p0, p1 = rest(k - 1, a - MOVE / FPS), rest(k, a)
        return (p0[0] + (p1[0] - p0[0]) * e, p0[1] + (p1[1] - p0[1]) * e), True

    def blink(t):
        for a in ARRIVE:
            if a - MOVE / FPS <= t < a + SOLID:
                return 1.0
        return 1.0 if int((t - D.GONE) / 0.53) % 2 == 0 else 0.45

    def cursor_layer(t):
        """Her cursor at t on its own layer, with a streak while it jumps, and her glow."""
        layer = kit.blank()
        d = ImageDraw.Draw(layer)
        (cx, cy), moving = pos(t)
        k = blink(t)
        cw, ch = D.CURSOR
        if moving or any(abs(t - a) < 0.5 / FPS for a in ARRIVE):
            (px, py), _ = pos(t - 1 / FPS)
            dist = math.hypot(cx - px, cy - py)
            n = int(dist / 5)
            for j in range(n):
                q = j / max(1, n)
                x, y = px + (cx - px) * q, py + (cy - py) * q
                a = 40 + 150 * q
                d.rectangle([round(x - cw / 2 + 1), round(y - ch / 2 + 2), round(x + cw / 2) - 2,
                             round(y + ch / 2) - 3], fill=BLUE + (round(a),))
        d.rectangle([round(cx - cw / 2), round(cy - ch / 2), round(cx + cw / 2) - 1, round(cy + ch / 2) - 1],
                    fill=BLUE + (round(255 * k),))
        return kit.her_glow(layer, 0.6 * k)

    # ---- the tear: C55's defrag pass reaches her cell (row 3's caret) and masks her layer from then on
    RX, RY = c55.REG
    q = int((CARET_X - RX) // TILE[0])
    r_top = int((row_cy(MEMS[2]["row"]) - D.CURSOR[1] / 2 - RY) // TILE[1])
    TEAR = c55.ts(q, r_top)

    def in_reg(p):
        return RX <= p[0] < RX + c55.COLS * TILE[0] and RY <= p[1] < RY + c55.ROWS * TILE[1]

    # ---- 1. her layer: the cursor until the tear (C55 samples her at its cut and breaks her cell)
    orig_layer = kit.her_layer

    def her_layer(t, call, box_level=1.0):
        if not (A[0] - MOVE / FPS <= t < T55 + 0.25):
            return orig_layer(t, call, box_level)
        p, _ = pos(t)
        if t >= TEAR and not in_reg(p):
            return kit.blank()        # torn: from here the overlay draws her (C55 would not mask her out there)
        return cursor_layer(t)

    setattr(her_layer, TAG, True)
    kit.her_layer = her_layer

    # ---- the listing drains into last_message.txt (C55: inward, per 8 x 16 cell of FULLR); the rows drain with it
    drain = kit.inward((NX, NY + 10), T55 - 0.25, T55 + 0.05, 600.0)
    FX0, FY0 = SR.FULLR[:2]

    def drained(layer, box, t):
        if t < T55 - 0.25:
            return layer
        x0, y0, x1, y1 = box
        mask = Image.new("L", layer.size, 0)
        md = ImageDraw.Draw(mask)
        for rr in range(int((y0 - FY0) // 16), int((y1 - FY0) // 16) + 1):
            for qq in range(int((x0 - FX0) // 8), int((x1 - FX0) // 8) + 1):
                a = 1 - clamp((t - drain(FX0 + qq * 8 + 4, FY0 + rr * 16 + 8)) / 0.09)
                if a > 0:
                    md.rectangle([FX0 + qq * 8, FY0 + rr * 16, FX0 + qq * 8 + 7, FY0 + rr * 16 + 15],
                                 fill=round(255 * a))
        out = layer.copy()
        out.putalpha(ImageChops.multiply(layer.getchannel("A"), mask))
        return out

    def row_layer(k, t):
        """Row k's inversion: her colour behind, the row redrawn in the background colour (C55 drains it)."""
        m = MEMS[k]
        a = 1 - clamp(leaving(k, t) * FADE / 3)
        if a <= 0.01:
            return None
        head, y, box = ROWS[m["row"]]
        layer = kit.blank()
        d = ImageDraw.Draw(layer)
        hot = clamp(1 - (t - m["A"]) / 0.2)       # lit brighter the moment she lands on it
        lvl = (0.78, 0.88, 0.98)[k]
        bar = tk.mix((235, 240, 255), hot * 0.6, tk.mix(tk.BLUE_TEXT, lvl))
        d.rectangle(box, fill=bar + (round(255 * a),))
        ink = tk.BG + (round(255 * a),)
        d.text((ROW_X, y), head, font=f18, fill=ink)
        d.text((ROW_X + f18.getlength(head), y), m["name"], font=f18, fill=ink)
        return drained(layer, box, t)

    # ---- the bubbles
    def styled(m, t, halo_k):
        sp = m["sp"]
        fl = m["flash"] * clamp(1 - (t - m["A"]) / 0.3)
        if fl > 0.01:
            sp = kit.brighten(sp, fl)
        return kit.haloed(sp, halo_k, tk.BLUE_TEXT, max(4, round(5 * m["scale"])))

    def pop_scale(m, t):
        """Scale and alpha of the scale-in: already most of its size on the word's frame, overshoot, hold."""
        u = clamp((t - m["A"] + 1 / FPS) / (POP / FPS))
        return 0.62 + 0.38 * kit.ease_back(u), clamp(0.55 + u * 1.8)

    def leaving(k, t):
        """0 -> 1 as the cursor leaves memory k for the next one (from its first in-between frame)."""
        if k + 1 >= len(MEMS):
            return 0.0
        return clamp((t - (A[k + 1] - 2 / FPS)) / (FADE / FPS))

    def paste(layer, sp, x, y, scale, alpha):
        """sp at (x, y) (its own top-left, halo pad included), scaled about the anchor ax, ay (fractions)."""
        if alpha <= 0.01 or scale <= 0.01:
            return
        if abs(scale - 1) > 0.01:
            sp = sp.resize((max(1, round(sp.width * scale)), max(1, round(sp.height * scale))),
                           Image.Resampling.LANCZOS)
        if alpha < 0.999:
            sp = tk.scale_alpha(sp, alpha)
        layer.alpha_composite(sp, (round(x), round(y)))

    def wave_burst(layer, box, t, a):
        """The wav's burst: its laugh (six ha's) as bars behind the card, shooting out on the word and settling."""
        m = MEMS[2]
        x0, y0, x1, y1 = box
        cy = (y0 + y1) / 2
        dt = t - m["A"]
        b = clamp(dt / (2 / FPS) + 0.5) * (0.18 + 0.82 * math.exp(-max(0.0, dt) / 0.4))
        rng = random.Random(round(t * FPS))
        d = ImageDraw.Draw(layer)
        n = int((x1 - x0 - 16) // 5)
        for j in range(n):
            f = j / max(1, n - 1)
            env = sum((1 - 0.11 * i) * math.exp(-((f - (i + 0.5) / 6) / 0.05) ** 2) for i in range(6))
            hh = (y1 - y0) / 2 + 3 + 46 * m["scale"] * b * env * (0.65 + 0.35 * rng.random())
            x = x0 + 8 + j * 5
            col = tk.mix(tk.BLUE_TEXT, 0.7 + 0.3 * env)
            d.rectangle([x, round(cy - hh), x + 2, round(cy + hh)], fill=col + (round(220 * a),))

    def bubble_row(layer, k, t):
        m = MEMS[k]
        if t < m["A"]:
            return
        scale, alpha = pop_scale(m, t)
        v = leaving(k, t)
        alpha *= 1 - kit.ease_io(v)
        scale *= 1 - 0.08 * v
        if alpha <= 0.01:
            return
        sp = styled(m, t, m["halo"] * (0.85 + 0.15 * kit.engine.pulse(t)))
        pad = (sp.width - m["sp"].width) / 2
        cy = row_cy(m["row"]) - 8 * (t - m["A"])           # drifts up while she holds it
        w_, h_ = sp.width * scale, sp.height * scale
        if m["sprite"] == "wav":
            bw, bh = m["sp"].width * scale, m["sp"].height * scale
            wave_burst(layer, (BUB_R - bw, cy - bh / 2, BUB_R, cy + bh / 2), t, alpha)
        paste(layer, sp, BUB_R + pad * scale - w_, cy - h_ / 2, scale, alpha)

    # ---- Erase: your last bubble breaks into tiles that fly into the defrag grid and are removed there
    S0, S1 = erase_shot.start, erase_shot.end

    def swept_at(i):
        """When erase's defrag pass (i / 660 < g) reaches grid cell i."""
        n = round(S0 * FPS)
        while R.erase_sweep((n / FPS - S0) / (S1 - S0)) <= i / 660 and n / FPS < S1 + 2:
            n += 1
        return n / FPS

    def build_tiles():
        sp = LAST["sp"]
        x0, y0 = last_box(ERASE)
        cw, ch = TILE
        cols, rows = math.ceil(sp.width / cw), math.ceil(sp.height / ch)
        cells = []
        for r in range(rows):
            for c in range(cols):
                crop = sp.crop((c * cw, r * ch, c * cw + cw, r * ch + ch))
                hist = crop.getchannel("A").histogram()
                inked = sum(v * n for v, n in enumerate(hist)) / (cw * ch)
                if inked > 10:
                    cells.append((r, c, crop))
        her = set(c55.landed())
        first_land = ERASE + FLY
        cand = [i for i in range(660) if not R.defrag_keep(i) and i not in her and swept_at(i) >= first_land + 0.12]
        step = max(1, len(cand) // max(1, len(cells)))
        rng = random.Random(59)
        out = []
        for k, (r, c, crop) in enumerate(cells):
            i = cand[min(len(cand) - 1, k * step)]
            gx, gy = R.defrag_cell(i)
            lift = ERASE + 0.18 * k / max(1, len(cells) - 1)
            out.append(dict(crop=crop, src=(x0 + c * cw + cw / 2, y0 + r * ch + ch / 2), dst=(gx + 7, gy + 9),
                            lift=lift, land=lift + FLY, gone=max(lift + FLY + 0.06, swept_at(i)),
                            bend=rng.uniform(0.12, 0.3) * (1 if k % 2 else -1)))
        return out

    TILES = build_tiles()

    def tile_sprite(crop, wpx, hpx, lift, edge=True):
        sp = crop if (round(wpx), round(hpx)) == crop.size else crop.resize(
            (max(1, round(wpx)), max(1, round(hpx))), Image.Resampling.LANCZOS)
        if edge:
            sp = sp.copy()
            ImageDraw.Draw(sp).rectangle([0, 0, sp.width - 1, sp.height - 1], outline=tk.BLUE_TEXT + (230,))
        if lift > 0.01:
            sp = kit.brighten(sp, lift, (255, 244, 200))
        return sp

    def halo_only(sp, k, radius):
        """kit.haloed's halo without the sprite (pad = 2 * radius)."""
        pad = radius * 2
        a = Image.new("L", (sp.width + 2 * pad, sp.height + 2 * pad), 0)
        a.paste(sp.getchannel("A"), (pad, pad))
        a = a.filter(ImageFilter.GaussianBlur(radius)).point(lambda v: min(255, int(v * 2.2 * k)))
        cut = Image.new("L", a.size, 0)
        cut.paste(sp.getchannel("A"), (pad, pad))
        a = ImageChops.subtract(a, cut)
        out = Image.new("RGBA", a.size, tk.BLUE_TEXT + (0,))
        out.putalpha(a)
        return out

    def bubble_last(layer, t):
        m = LAST
        if t < m["A"]:
            return
        x, y = last_box(t)
        if t < ERASE:
            scale, alpha = pop_scale(m, t)
            sp = styled(m, t, m["halo"] * (0.85 + 0.15 * kit.engine.pulse(t)))
            pad = (sp.width - m["sp"].width) / 2
            # scaled about its top-left corner under the name (it opens out of the name)
            paste(layer, sp, x - pad * scale, y - pad * scale, scale, alpha)
            return
        # the halo goes with the first tiles; each tile: 2 frames lit at its lift, the flight, the grid, the pass
        k = clamp(1 - (t - ERASE) / 0.15)
        if k > 0.01:
            layer.alpha_composite(halo_only(m["sp"], m["halo"] * k, 8), (round(x) - 16, round(y) - 16))
        cw, ch = TILE
        for tl in TILES:
            if t < tl["lift"]:
                sx, sy = tl["src"]
                layer.alpha_composite(tile_sprite(tl["crop"], cw, ch, 0.0, edge=False),
                                      (round(sx - cw / 2), round(sy - ch / 2)))
                continue
            if t >= tl["gone"] + 2 / FPS:
                continue
            if t < tl["land"]:
                u = clamp((t - tl["lift"]) / FLY)
                e = 1 - (1 - u) ** 2                              # off the bubble at once, settling into its cell
                cx, cy = kit.bezier(tl["src"], tl["dst"], tl["bend"], e)
                s = 1 + 0.35 * math.sin(math.pi * u)
                wpx, hpx = kit.lerp(cw, 14, e) * s, kit.lerp(ch, 18, e) * s
                lit = clamp(1 - (t - tl["lift"]) / (2 / FPS))
            else:
                cx, cy = tl["dst"]
                wpx, hpx = 14, 18
                lit = clamp(1 - (t - tl["land"]) / (2 / FPS)) * 0.5
                if t >= tl["gone"]:
                    lit = 1.0                                      # the pass: lit for 2 frames, then removed
            sp = tile_sprite(tl["crop"], wpx, hpx, lit)
            layer.alpha_composite(sp, (round(cx - sp.width / 2), round(cy - sp.height / 2)))

    # ---- the cursor from the tear on (her layer is masked by C55, and is not drawn at all in erase)
    def hidden_at():
        """When C56's reveal (her pane sliding back) overwrites the cell the cursor blinks in (C56.render's delay)."""
        hx, hy = home(RET + 1.0)
        cx = FX0 + int((hx - FX0) // 8) * 8 + 4
        cy = FY0 + int((hy - FY0) // 16) * 16 + 8
        push = c56.push(int(cx) // 8 * 8) - 0.1 if cx < 400 else 1e9
        return min(push, kit.radial((436, 230), c56.T - 0.06, 1700.0)(cx, cy))

    HIDE = [None]

    # ---- 2. the overlay: rows, bubbles, tiles, and the cursor from TEAR
    def overlay(t, n):
        if not SPAN[0] <= t < SPAN[1]:
            return None
        layer = kit.blank()
        for k in range(3):
            if MEMS[k]["A"] <= t:
                rl = row_layer(k, t)
                if rl is not None:
                    layer.alpha_composite(rl)
        for k in range(3):
            bubble_row(layer, k, t)
        bubble_last(layer, t)
        if t >= TEAR:
            if HIDE[0] is None:
                HIDE[0] = hidden_at()
            if t < HIDE[0]:
                layer.alpha_composite(cursor_layer(t))
        return layer

    for name in ("shot_memory_ls", "shot_erase"):
        idx = next(i for i, s in enumerate(v2.ALL) if s.fn.__name__ == name)
        key = idx if idx in v2.OVERLAY else name
        prev = v2.OVERLAY.get(key)
        if getattr(prev, TAG, False):
            continue

        def ov(t, n, prev=prev):
            base = prev(t, n) if prev is not None else None
            mine = overlay(t, n)
            if mine is None:
                return base
            if base is None:
                return mine
            base = base.copy()
            base.alpha_composite(mine)
            return base

        setattr(ov, TAG, True)
        v2.OVERLAY[key] = ov

    # exposed for checks
    install.info = dict(A=A, ERASE=ERASE, RET=RET, TEAR=TEAR, TILES=len(TILES),
                        land=(min(x["land"] for x in TILES), max(x["land"] for x in TILES)),
                        gone=(min(x["gone"] for x in TILES), max(x["gone"] for x in TILES)))


if __name__ == "__main__":
    if sys.argv[1:] == ["page"]:
        page()
