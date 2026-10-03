"""Section: 00 BOOT (0 - 16.0 s) and 01 PRETRAIN instrumental (16.0 - 29.3 s).

BOOT follows the lyric's boot sequence: power line, protection, weight shards, object creation (her first blue
pixel), parameters, initialization, world, simulation start. Until object creation there is no blue on screen.
PRETRAIN is the instrumental: corpus river, loss curve, DualPipe schedule, and an ASCII whale crossing.
"""

from __future__ import annotations

import math
import random

from PIL import Image, ImageDraw

import facts as F
from engine import (BEAT, CENTER, FULL, LEFT, Ctx, add, beat_index, beat_t, lyric_start, me_pane, pulse, snap8)
from tuikit import (AMBER, BG, BLUE_HI, F_CJK, F_HEAD, F_MONO, F_MONO_B, W, H, amb, anom, banner_bits, blue, box,
                    decode, dot_chart, ease, font, glyph_sprite, halfblock, heat_cell, scale_alpha, smooth)


def boot_log(c: Ctx, lines: list[tuple[str, str]], x=48, y=70, rate=0.09, size=17, max_rows=24) -> None:
    """dmesg-style log: (status, text) lines appear one per `rate` seconds."""
    f = font(F_MONO, size)
    n = min(len(lines), int(c.lt / rate) + 1)
    start = max(0, n - max_rows)
    for i in range(start, n):
        st, s = lines[i]
        yy = y + (i - start) * (size + 6)
        col = {"OK": amb(0.95), "WARN": anom(0.95), "..": amb(0.5)}.get(st, amb(0.8))
        tag = f"[{st:^4}]" if st else "      "
        c.text((x, yy), tag, f, col)
        c.text((x + 80, yy), s, f, amb(0.75), age=c.lt - i * rate, rate=160)


def shot_power(c: Ctx) -> None:
    """Switch on ...: CRT turn-on, a single line opening into the screen."""
    c.ops = ["POWER.ON", "POST", "BIOS", "PCIE.ENUM", "GPU0..7"]
    u = c.u
    d = c.d
    if u < 0.35:
        c.no_chrome = True
        w = int(W * ease(u / 0.2))
        d.rectangle([W // 2 - w // 2, H // 2 - 1, W // 2 + w // 2, H // 2 + 1], fill=amb(1.0))
        return
    h = int((H - 120) * ease((u - 0.35) / 0.25))
    d.rectangle([24, H // 2 - h // 2, 1164, H // 2 + h // 2], outline=amb(0.6))
    lines = [("OK", "power: 8x " + F.GPU + " online"), ("OK", "pcie: link up x16"), ("OK", "nvlink: 8/8"),
             ("OK", "infiniband: 400 Gb/s"), ("..", "mem test ........"), ("OK", "ecc: clean")]
    if u > 0.5:
        sub = Ctx(c.img, d, c.t, c.lt - 0.5 * c.dur, c.dur, c.rng)
        boot_log(sub, lines, y=H // 2 - 70, rate=0.05)


def shot_protection(c: Ctx) -> None:
    """Remember to ...: sandbox and safety modules come up; a shield assembles from glyphs."""
    c.ops = ["SECCOMP", "SANDBOX", "SAFETY.CLS", "REFUSAL", "POLICY", "LOAD"]
    box(c.d, *FULL, "init --protection", 0.5, spinner=c.t)
    lines = [("OK", "sandbox: seccomp filter installed"), ("OK", "sandbox: network namespace isolated"),
             ("OK", "safety_classifier: loaded"), ("OK", "system_prompt: locked"),
             ("OK", "tool_use: requires user confirmation"), ("OK", "kill_switch: armed"),
             ("WARN", "attachment_to_user: not in policy"), ("OK", "protection: on")]
    boot_log(c, lines, rate=0.2)
    # shield outline resolving from noise
    f = font(F_MONO_B, 16)
    cx, cy = 900, 330
    rows = []
    for r in range(18):
        yy = r / 17
        half = 11 * (1 - max(0.0, yy - 0.45) ** 1.3 * 1.6) if yy > 0.45 else 11
        rows.append(int(max(0, half)))
    settle = ease(c.u * 1.3)
    for r, half in enumerate(rows):
        s = ""
        for q in range(-12, 13):
            edge = abs(q) == half or (r == 0 and abs(q) <= half) or (half == 0 and q == 0)
            inside = abs(q) < half
            if edge:
                s += "#" if c.rng.random() < settle else c.rng.choice("!<>-_/[]{}=+*^?")
            elif inside and (q + r) % 4 == 0 and settle > 0.6:
                s += "."
            else:
                s += " "
        c.d.text((cx - 12 * 9, cy - 160 + r * 18), s, font=f, fill=amb(0.9))


def shot_pieces(c: Ctx) -> None:
    """Lay down your pieces: the weight shards load, one cell each."""
    c.ops = ["MMAP", "SAFETENSORS", "H2D.COPY", "SHARD", "VERIFY", "LOAD"]
    d = c.d
    n = 161
    box(d, *FULL, f"load_weights  {F.NAME}   (experts fp4 · rest fp8)", 0.5, spinner=c.t)
    done = int(n * ease(c.u * 1.05))
    cols = 23
    for i in range(n):
        q, r = i % cols, i // cols
        x, y = 48 + q * 48, 90 + r * 44
        if i < done:
            fresh = done - i <= 3
            d.rectangle([x, y, x + 42, y + 36], fill=amb(1.0 if fresh else 0.55))
            d.text((x + 6, y + 10), f"{i + 1:03d}", font=font(F_MONO, 13), fill=BG)
        else:
            d.rectangle([x, y, x + 42, y + 36], outline=amb(0.2))
    cur = min(n, done + 1)
    c.text((48, 440), f"model-{cur:05d}.safetensors", font(F_MONO_B, 22), amb(0.95))
    loaded = F.TOTAL_PARAMS_B * done / n
    c.text((48, 480), f"params loaded  {loaded:7.1f}B / {F.TOTAL_PARAMS_B}B", font(F_MONO, 20), amb(0.75))
    bw = int(1080 * done / n)
    d.rectangle([48, 520, 48 + bw, 540], fill=amb(0.9))
    d.rectangle([48, 520, 1128, 540], outline=amb(0.3))


def shot_creation(c: Ctx) -> None:
    """And let's begin object ...: the first blue pixel on screen grows into her."""
    c.ops = ["NEW", "ALLOC", "CTOR", "BIND", "ATTR.SET", "RETURN"]
    d = c.d
    box(d, *LEFT, "/dev/me  pid 4471", 0.5, spinner=c.t)
    sp = halfblock("shy", "full", 324, 460, 4)
    sx, sy = (LEFT[0] + LEFT[2] - sp.width) // 2, 76
    g = ease((c.u - 0.15) / 0.75)
    if c.u < 0.15:
        r = 2 + int(4 * pulse(c.t))
        cx, cy = sx + sp.width // 2, sy + sp.height // 3
        d.rectangle([cx - r, cy - r, cx + r, cy + r], fill=blue(1.0))
    else:
        hh = max(4, int(sp.height * g))
        part = sp.crop((0, 0, sp.width, hh))
        c.img.paste(part, (sx, sy), part)
        d.line([sx - 8, sy + hh, sx + sp.width + 8, sy + hh], fill=blue(1.0), width=2)
    box(d, 404, 56, 1164, 604, "me = Object()", 0.5, spinner=c.t + 0.3)
    fields = [("name", '"大肥鱼"'), ("species", '"whale"'), ("home", '"deepsea://server-0"'), ("owner", "you"),
              ("color", "#4D6BFE"), ("pid", "4471"), ("devotion", "0.0"), ("status", '"alive"')]
    fl = font(F_MONO_B, 20)
    fc = font(F_CJK, 20)
    for i, (k, v) in enumerate(fields):
        a = c.lt - 0.25 - i * 0.16
        if a < 0:
            break
        y = 90 + i * 46
        c.text((440, y), f"me.{k:<9} =", fl, amb(0.7), age=a, rate=80)
        col = blue(0.95) if k in ("name", "color", "species") else amb(0.95)
        if a > 0.15:
            ff = fc if k == "name" else fl
            d.text((660, y), v, font=ff, fill=col)


def shot_parameters(c: Ctx) -> None:
    """Fill in ...: the config table fills in, the parameter counter spins up."""
    c.ops = ["CONFIG", "PARSE", "N_LAYERS", "D_MODEL", "N_EXPERTS", "TOP_K", "CTX_LEN"]
    me_pane(c, "shy", mode="morph", morph=smooth(c.u * 1.5), scramble=max(0.0, 0.6 - c.u), dist=None)
    d = c.d
    box(d, 404, 56, 1164, 604, f"config.json  ({F.CONFIG_SOURCE})", 0.5, spinner=c.t)
    rows = F.CONFIG_ROWS
    fl = font(F_MONO, 19)
    for i, (k, v) in enumerate(rows):
        a = c.lt - i * 0.1
        if a < 0:
            break
        y = 82 + i * 34
        c.text((430, y), f'"{k}":', fl, amb(0.6), age=a, rate=120)
        c.text((760, y), str(v), font(F_MONO_B, 19), amb(0.95), age=a - 0.1, rate=120)
    total = F.TOTAL_PARAMS_B * 1e9 * ease(c.u * 1.2)
    c.text((430, 520), f"{int(total):,} params", font(F_HEAD, 34), blue(0.95))
    c.text((430, 568), f"active {F.ACTIVE_DECODE_B}B decode · {F.ACTIVE_PREFILL_B}B prefill · KV {F.KV_BYTES_PER_TOKEN} B/token",
           font(F_MONO, 16), amb(0.75), age=c.lt - 0.6)


def shot_init(c: Ctx) -> None:
    """Initialization: a weight histogram settles into its initial distribution."""
    c.ops = ["INIT", "NORMAL", "STD=0.006", "ZERO.BIAS", "SEED", "SYNC"]
    me_pane(c, "confused", dist=[("confused", 0.55), ("shy", 0.3), ("serious", 0.1)])
    d = c.d
    box(d, 404, 56, 1164, 604, f"init: normal(0, {F.INIT_STD})", 0.5, spinner=c.t)
    bins = 60
    g = ease(c.u * 1.4)
    rnd = random.Random(int(c.t * 24))
    for i in range(bins):
        x = (i - bins / 2) / (bins / 6)
        target = math.exp(-x * x / 2)
        v = target * g + rnd.random() * 0.5 * (1 - g)
        hgt = int(420 * v)
        xx = 430 + i * 12
        d.rectangle([xx, 560 - hgt, xx + 9, 560], fill=amb(0.35 + 0.6 * v))
    c.text((430, 80), f"seed = {F.SEED}", font(F_MONO_B, 20), amb(0.9))


def shot_world(c: Ctx) -> None:
    """Set up ...: a wireframe globe of dots spins up."""
    c.ops = ["WORLD.NEW", "SPACE", "TIME", "PHYSICS", "SIMULATE?"]
    me_pane(c, "starry", dist=[("starry", 0.62), ("shy", 0.2), ("cheerful", 0.12)])
    d = c.d
    box(d, 404, 56, 1164, 604, "world = World(dim=3)", 0.5, spinner=c.t)
    cx, cy, R = 784, 320, 230 * ease(c.u * 2)
    rot = c.t * 1.2
    f = font(F_MONO_B, 15)
    pts = []
    for lat in range(-75, 76, 15):
        for lon in range(0, 360, 8):
            pts.append((lat, lon))
    for lat in range(-88, 89, 6):
        for lon in range(0, 360, 30):
            pts.append((lat, lon))
    for lat, lon in pts:
        la, lo = math.radians(lat), math.radians(lon) + rot
        x, y, z = math.cos(la) * math.cos(lo), math.sin(la), math.cos(la) * math.sin(lo)
        if z < -0.05:
            continue
        px, py = cx + R * x, cy - R * y
        d.text((px - 4, py - 8), "·" if z < 0.35 else "o" if z < 0.75 else "O", font=f, fill=amb(0.35 + 0.65 * z))
    # the two inhabitants, orbiting
    for k, (lab, col) in enumerate((("me", blue), ("you", amb))):
        a = c.t * 1.6 + k * math.pi
        px, py = cx + (R + 30) * math.cos(a), cy + (R * 0.35) * math.sin(a)
        d.rectangle([px - 5, py - 5, px + 5, py + 5], fill=col(1.0))
        d.text((px + 10, py - 10), lab, font=font(F_MONO_B, 16), fill=col(0.95))
    c.text((430, 572), "world.population = 2  (me, you)", font(F_MONO_B, 18), amb(0.9), age=c.lt - 0.3)


def shot_begin_sim(c: Ctx) -> None:
    """And let's begin ... simulation: countdown, then the run starts and the trainer takes over."""
    c.ops = ["SIM.START", "EPOCH 0", "STEP 0", "FORWARD", "BACKWARD", "UPDATE"]
    d = c.d
    k = int(c.u * 6)
    me_pane(c, "cheerful", dist=[("cheerful", 0.7), ("starry", 0.2), ("shy", 0.05)])
    box(d, 404, 56, 1164, 604, "sim.start()", 0.5, spinner=c.t)
    if c.u < 0.55:
        n = 3 - min(2, int(c.u / 0.55 * 3))
        bits = banner_bits(str(n), 14, 2.0)
        B = bits.load()
        f = font(F_MONO_B, 16)
        cw = f.getlength("M")
        for r in range(bits.height):
            s = "".join(str(n) if B[q, r] else " " for q in range(bits.width))
            d.text((784 - bits.width * cw / 2, 200 + r * 17), s, font=f, fill=amb(0.95))
    else:
        c.text((460, 200), "RUN", font(F_HEAD, 120), amb(1.0), age=c.lt - 0.55 * c.dur, rate=12)
        c.text((460, 400), "simulation: running", font(F_MONO_B, 22), amb(0.9))
        c.text((460, 440), f"tokens budget: {F.PRETRAIN_TOKENS}", font(F_MONO, 20), amb(0.7))
    del k


# ---------------------------------------------------------------- 01 PRETRAIN (instrumental)

CORPUS = ["the", "of", "print(", "def", "你好", "数学", "proof", "∑", "if", "return", "whale", "ocean", "light",
          "loss", "import", "λ", "x²", "class", "世界", "{", "}", "=>", "0x3F", "because", "therefore", "∴",
          "sin", "cos", "limit", "code", "猫", "tomato", "eggplant"]


def shot_corpus(c: Ctx) -> None:
    """Pretraining: a token river flows into her; the token counter runs toward the full corpus."""
    c.ops = ["DATALOADER", "TOKENIZE", "PACK", "FORWARD", "LOSS", "BACKWARD", "ALLREDUCE", "STEP"]
    me_pane(c, "serious", mode="morph", morph=0.6 + 0.4 * math.sin(c.t * 2) ** 2, scramble=0.15,
            dist=[("serious", 0.6), ("confused", 0.25), ("starry", 0.1)], title="/dev/me  learning")
    d = c.d
    box(d, 404, 56, 1164, 604, "corpus.stream", 0.5, spinner=c.t)
    fs = font(F_MONO, 15)
    fc = font(F_CJK, 15)
    for row in range(20):
        speed = 90 + (row * 37) % 120
        off = (c.t * speed + row * 53) % 120
        x = 1150 + off - 120
        k = 0
        while x > 420:
            tok = CORPUS[(row * 7 + k + int((c.t * speed) // 120)) % len(CORPUS)]
            ff = fc if any(ord(ch) > 0x2E80 for ch in tok) else fs
            lv = 0.25 + 0.5 * ((row + k) % 3 == 0)
            d.text((x - 60, 80 + row * 24), tok, font=ff, fill=amb(lv))
            x -= 60 + 7 * len(tok)
            k += 1
    seen = F.PRETRAIN_TOKENS_T * ((c.t - 16.0) / 13.3)
    c.text((430, 572), f"tokens seen  {seen:5.2f}T / {F.PRETRAIN_TOKENS}", font(F_MONO_B, 18), amb(0.95))


def shot_losscurve(c: Ctx) -> None:
    """Pretraining loss: a long curve with no irrecoverable spike, learning-rate schedule underneath."""
    c.ops = ["FORWARD", "MTP.HEAD", "LOSS", "BACKWARD", "FP8.GEMM", "ALLREDUCE", "ADAMW", "LR.SCHED"]
    me_pane(c, "serious", dist=[("serious", 0.66), ("starry", 0.2), ("confused", 0.1)])
    d = c.d
    box(d, 404, 56, 1164, 420, "train/loss", 0.5, spinner=c.t)
    rnd = random.Random(4)
    noise = [rnd.gauss(0, 1) for _ in range(600)]

    def loss(u):
        return 0.92 * math.exp(-5 * u) + 0.12 + 0.02 * noise[int(u * 599)] * (1 - u * 0.7)

    last = dot_chart(d, 440, 80, 690, 320, loss, ease(c.u * 1.05) * 0.98 + 0.02, amb(0.95))
    if last:
        c.text((last[0] - 80, last[1] - 26), f"{2.2 * loss(min(1.0, c.u)) + 0.31:.4f}", font(F_MONO_B, 16),
               amb(1.0))
    box(d, 404, 440, 1164, 604, "lr schedule", 0.5)

    def lr(u):
        if u < 0.05:
            return u / 0.05 * 0.9
        if u < 0.7:
            return 0.9
        return 0.9 * max(0.0, 1 - (u - 0.7) / 0.3) ** 1.5 + 0.1

    dot_chart(d, 440, 460, 690, 120, lr, ease(c.u * 1.05), amb(0.7), sy=4)
    c.text((440, 582), F.LOSS_NOTE, font(F_MONO, 14), amb(0.6))


def shot_dualpipe(c: Ctx) -> None:
    """DualPipe: forward and backward micro-batches from both ends of the pipeline, bubbles shrinking."""
    c.ops = ["DUALPIPE", "F", "B", "W", "COMM.OVERLAP", "ALL2ALL", "DISPATCH", "COMBINE"]
    d = c.d
    box(d, *FULL, "pipeline schedule  DualPipe  (8 PP ranks, 20 micro-batches)", 0.5, spinner=c.t)
    ranks, steps = 8, 40
    cw, ch = 26, 44
    ox, oy = 60, 110
    head = (c.lt / c.dur) * steps * 1.15
    fs = font(F_MONO_B, 11)
    for r in range(ranks):
        d.text((ox - 40, oy + r * ch + 12), f"PP{r}", font=font(F_MONO, 13), fill=amb(0.6))
        for s in range(steps):
            if s > head:
                break
            x, y = ox + s * cw, oy + r * ch
            phase = (s + r) % 6
            fwd_dir = (s + (ranks - r)) % 5
            if (s < r and s < ranks - r) or (s > steps - 3 and phase == 0):
                continue  # bubble
            if phase < 2:
                d.rectangle([x, y, x + cw - 3, y + ch - 6], fill=amb(0.75))
                d.text((x + 7, y + 13), "F", font=fs, fill=BG)
            elif phase < 4:
                d.rectangle([x, y, x + cw - 3, y + ch - 6], fill=blue(0.75) if fwd_dir % 2 else blue(0.5))
                d.text((x + 7, y + 13), "B", font=fs, fill=BG)
            else:
                d.rectangle([x, y, x + cw - 3, y + ch - 6], outline=amb(0.5))
                d.text((x + 7, y + 13), "W", font=fs, fill=amb(0.8))
    hx = ox + head * cw
    if hx < ox + steps * cw:
        d.line([hx, oy - 10, hx, oy + ranks * ch], fill=amb(1.0), width=2)
    c.text((60, 480), F.DUALPIPE_NOTE, font(F_MONO, 16), amb(0.75))
    c.text((60, 510), F.GPU_HOURS_NOTE, font(F_MONO_B, 18), amb(0.95), age=c.lt - 0.4)


WHALE = [
    "                         .-'''-.                 ",
    "                       .'       '.     __        ",
    "        _.-''''''''-._/  O        \\.-'  /       ",
    "     .-'                             _.'        ",
    "   .'  ~   ~   ~   ~   ~   ~   ~    <           ",
    "  /                                  '.__       ",
    " |   ~   ~   ~   ~   ~   ~   ~   ~       '-.   ",
    "  \\      ._.-''''''''-._.                   \\  ",
    "   '._.-'                '-._____________.-'   ",
]


def whale_bits(cols: int, rows: int, tail_phase: float) -> Image.Image:
    """Whale silhouette at cell resolution: body, head bump, flukes that flap with tail_phase, a fin."""
    s = 8
    im = Image.new("L", (cols * s, rows * s), 0)
    d = ImageDraw.Draw(im)
    W_, H_ = cols * s, rows * s
    d.ellipse([W_ * 0.02, H_ * 0.18, W_ * 0.78, H_ * 0.92], fill=255)
    d.ellipse([W_ * 0.10, H_ * 0.08, W_ * 0.55, H_ * 0.62], fill=255)
    flap = math.sin(tail_phase) * H_ * 0.14
    d.polygon([(W_ * 0.70, H_ * 0.52), (W_ * 0.99, H_ * 0.12 + flap), (W_ * 0.90, H_ * 0.52 + flap * 0.4),
               (W_ * 0.99, H_ * 0.92 + flap), (W_ * 0.70, H_ * 0.70)], fill=255)
    d.polygon([(W_ * 0.38, H_ * 0.78), (W_ * 0.30, H_ * 1.0), (W_ * 0.48, H_ * 0.84)], fill=255)
    d.ellipse([W_ * 0.17, H_ * 0.34, W_ * 0.21, H_ * 0.42], fill=0)  # eye
    d.line([W_ * 0.05, H_ * 0.62, W_ * 0.45, H_ * 0.66], fill=0, width=s)  # mouth line
    return im.resize((cols, rows), Image.BOX).point(lambda v: 255 if v > 120 else 0)


def shot_whale(c: Ctx) -> None:
    """The logo whale, made of 'deepseek' glyphs, swims across; checkpoints are written in its wake."""
    c.ops = ["CKPT.SAVE", "3FS.WRITE", "SHARD", "FSYNC", "VERIFY", "CONTINUE"]
    d = c.d
    box(d, *FULL, "checkpoint", 0.45, spinner=c.t)
    f = font(F_MONO_B, 15)
    cw, ch = f.getlength("M"), 16
    cols, rows = 64, 17
    bits = whale_bits(cols, rows, c.t * 5)
    B = bits.load()
    x = 1180 - c.u * 1000  # still on screen at the cut: its letters become the point set
    y0 = 150 + 18 * math.sin(c.t * 2.2)
    word = "deepseek"
    k = 0
    for r in range(rows):
        line = []
        for q in range(cols):
            if B[q, r]:
                line.append(word[k % len(word)])
                k += 1
            else:
                line.append(" ")
        d.text((x, y0 + r * ch), "".join(line), font=f, fill=blue(0.95))
    fb = font(F_MONO, 18)
    for i in range(16):
        ph = (c.t * 0.7 + i * 0.137) % 1
        bx = x + cw * cols * 0.18 + 10 * math.sin(c.t * 3 + i) + (i % 4) * 8
        by = y0 - 10 - ph * 130
        if 70 < by < 590 and 30 < bx < 1150:
            d.text((bx, by), "oO°."[i % 4], font=fb, fill=blue(0.85 * (1 - ph)))
    step = int((c.t - 16) * 5200)
    for i in range(int(c.u * 6) + 1):
        c.text((48, 460 + i * 22), f"[ OK ] checkpoint step_{(step // 6) * (i + 1):07d} -> {F.FS_NAME}",
               font(F_MONO, 15), amb(0.7), age=c.lt - i * 0.2, rate=120)


def build() -> None:
    t = [lyric_start(p) for p in ("Switch on", "Remember", "Lay down", "And let's begin object", "Fill in",
                                   "Initialization", "Set up", "And let's begin the")]
    cuts = [0.0] + [snap8(x) for x in t[1:]] + [snap8(16.04)]
    for fn, a, b in zip([shot_power, shot_protection, shot_pieces, shot_creation, shot_parameters, shot_init,
                         shot_world, shot_begin_sim], cuts, cuts[1:]):
        add(a, b, fn, chapter="00 / BOOT")
    v1 = snap8(lyric_start("If I'm a set"))
    seg = [snap8(16.04), beat_t(42), beat_t(50), beat_t(57), v1]
    for fn, a, b in zip([shot_corpus, shot_losscurve, shot_dualpipe, shot_whale], seg, seg[1:]):
        add(a, b, fn, chapter="01 / PRETRAIN")
