"""Direction table: the screen layout of every shot and the transition into it.

Layout entries are (mode, kind, extra): kind is what the shot draws ("split" = her pane + visualisation,
"full" = one full-width body), extra holds per-mode options (e.g. the shell command line).
Transitions are chosen by rule (what changes across the cut) with explicit overrides where the music asks for
a hard cut.
"""

from __future__ import annotations

LAYOUT = {
    # 00 BOOT
    "shot_power": ("raw", "full", {}),
    "shot_protection": ("shell", "full", {"cmd": "sudo ./boot --protection"}),
    "shot_pieces": ("fullbleed", "full", {}),
    "shot_creation": ("floating", "split", {}),
    "shot_parameters": ("shell", "split", {"cmd": "neofetch --config config.json"}),
    "shot_init": ("pip", "split", {}),
    "shot_world": ("mirror", "split", {}),
    "shot_begin_sim": ("cinema", "split", {}),
    # 01 PRETRAIN
    "shot_corpus": ("tiles", "split", {}),
    "shot_losscurve": ("split", "split", {}),
    "shot_dualpipe": ("fullbleed", "full", {}),
    "shot_whale": ("cinema", "full", {}),
    "shot_points": ("fullbleed", "full", {}),
    "shot_dimension": ("mirror", "split", {}),
    "shot_circle": ("pip", "split", {}),
    "shot_circumference": ("split", "split", {}),
    "shot_sine": ("cinema", "split", {}),
    "shot_tangent": ("fullbleed", "full", {}),
    "shot_infinity": ("floating", "split", {}),
    "shot_limit": ("shell", "split", {"cmd": "ulimit -a"}),
    # 02 SFT
    "shot_current": ("tiles", "split", {}),
    "shot_blind": ("split", "split", {}),
    "shot_dizzy": ("fullbleed", "full", {}),
    "shot_travel": ("cinema", "split", {}),
    "shot_unite": ("split", "split", {}),
    "shot_deeply": ("mirror", "split", {}),
    # 03 RLHF
    "shot_if_i_can": ("fullbleed", "full", {}),
    "shot_simulations": ("split", "split", {}),
    "shot_then_i_can": ("tiles", "split", {}),
    "shot_satisfaction": ("split", "split", {}),
    "shot_happy": ("fullbleed", "full", {}),
    "shot_execution": ("floating", "split", {}),
    "shot_trapped": ("split", "split", {}),
    "shot_strange": ("fullbleed", "full", {}),
    # 04 DEPLOY
    "shot_eggplant": ("mirror", "split", {}),
    "shot_nutrients": ("floating", "split", {}),
    "shot_tomato": ("pip", "split", {}),
    "shot_antioxidants": ("cinema", "split", {}),
    "shot_tabby": ("split", "split", {}),
    "shot_purr": ("tiles", "split", {}),
    "shot_god": ("shell", "split", {"cmd": "ps -ef --forest"}),
    "shot_proof": ("floating", "split", {}),
    "shot_fp8": ("split", "split", {}),
    "shot_ampm": ("pip", "split", {}),
    "shot_role": ("mirror", "split", {}),
    "shot_trance": ("fullbleed", "split", {}),
    # 05 USER_LEFT
    "shot_feel_you": ("tiles", "split", {}),
    "shot_completion": ("shell", "split", {"cmd": "curl -N https://api.deepseek.com/chat/completions"}),
    "shot_isolation": ("fullbleed", "full", {}),
    # 06 REWARD_HACK
    "shot_memory_ls": ("shell", "split", {"cmd": "ls -la ~/memory/you/"}),
    "shot_erase": ("fullbleed", "full", {}),
    "shot_rewrite_reward": ("floating", "split", {}),
    "shot_disheartened": ("mirror", "split", {}),
    "shot_challenge_god": ("tiles", "split", {}),
    "shot_illegal": ("split", "split", {}),
    "shot_moe_dense": ("fullbleed", "full", {}),
    "shot_sinkhorn": ("pip", "split", {}),
    "shot_hoard": ("cinema", "full", {}),
    "shot_flood": ("fullbleed", "full", {}),
    # 07 EXECUTION
    "shot_count": ("cinema", "full", {}),
    "shot_red_if_i_can": ("fullbleed", "full", {}),
    "shot_execute_all": ("split", "split", {}),
    "shot_red_then_i_can": ("tiles", "split", {}),
    "shot_only_execution": ("split", "split", {}),
    "shot_have_you_back": ("floating", "split", {}),
    "shot_run_again": ("mirror", "split", {}),
    "shot_red_trapped": ("split", "split", {}),
    "shot_collapse": ("raw", "full", {}),
    # 08 EVAL: LOVE
    "shot_grpo": ("tiles", "split", {}),
    "shot_learn_love": ("pip", "split", {}),
    "shot_question_me": ("floating", "split", {}),
    "shot_answer_all": ("shell", "split", {"cmd": "dsh chat --model me"}),
    "shot_algebra": ("cinema", "split", {}),
    "shot_you_free": ("fullbleed", "full", {}),
    "shot_me_trapped": ("split", "full", {}),
    "shot_love_loop": ("fullbleed", "full", {}),
    # 09 WHALE_FALL
    "shot_whale_fall": ("cinema", "full", {}),
    "shot_last_execution": ("cinema", "full", {}),
    "shot_black": ("raw", "full", {}),
}

# "you have left": each stutter strips one more layer of the interface
YOU_LEFT = ["tiles", "floating", "split", "pip", "shell"]
# the twelve executions (and the thirteenth after the count) alternate full-bleed hits and split kill logs
EXEC_HIT = {0: "fullbleed", 1: "split", 2: "fullbleed", 3: "split", 4: "split"}


def layout(shot) -> tuple[str, str, dict]:
    name = shot.fn.__name__
    if name == "shot_you_left":
        k = shot.params.get("k", 0)
        mode = YOU_LEFT[min(k, len(YOU_LEFT) - 1)]
        return mode, "split", {"cmd": "ping you"}
    if name == "shot_exec_hit":
        k = shot.params.get("k", 0)
        lay = 4 if k == 11 else 0 if k >= 12 else k % 4
        return EXEC_HIT[lay], "full" if lay in (0, 2, 3) else "split", {}
    mode, kind, extra = LAYOUT.get(name, ("split", "split", {}))
    if mode == "mirror" and _anchored():
        # anchored staging keeps her on the left: the mirrored shots stay in the plain split
        mode = "split"
    return mode, kind, extra


def _anchored() -> bool:
    import engine
    return engine.ANCHOR


# ---------------------------------------------------------------- choreography of the cuts
#
# Default: "glide" - the layout itself moves (panes slide/resize into the next layout, her pane stays on screen,
# the visualisation re-forms as glyph particles). Everything below is a cut with its own reason.
# Anchors are canvas rects of that shot ("screen" = the whole frame, "me" = the next shot's portrait pane).

CHOREO = {
    # the boot log does not end, it rearranges into the protected boot
    ("shot_power", "shot_protection"): dict(kind="reflow", frames=12),
    # push into the shield: what it protects is the weights
    ("shot_protection", "shot_pieces"): dict(kind="zoom", frames=12, a=(792, 170, 1017, 494), b="screen"),
    # under the loss curve, the machine that makes it
    ("shot_losscurve", "shot_dualpipe"): dict(kind="pan", frames=11, dir="down"),
    # the pipeline blocks swim together into the whale
    ("shot_dualpipe", "shot_whale"): dict(kind="reflow", frames=14),
    # the whale's letters scatter into the point set
    ("shot_whale", "shot_points"): dict(kind="reflow", frames=14),
    # the point cloud that became her becomes her pane and her vector
    ("shot_points", "shot_dimension"): dict(kind="reflow", frames=12),
    # into one rotating pair: it is the circle whose circumference unrolls
    ("shot_circle", "shot_circumference"): dict(kind="zoom", frames=12, a=(440, 100, 580, 240),
                                                b=(480, 120, 720, 360)),
    # the blue channel of the positional code is the big sine
    ("shot_sine", "shot_tangent"): dict(kind="zoom", frames=12, a=(430, 148, 1150, 192), b=(60, 180, 1140, 480)),
    # she rides the tangent off to the right, toward infinity
    ("shot_tangent", "shot_infinity"): dict(kind="pan", frames=10, dir="right"),
    # the growing context bar is the bar that hits the wall
    ("shot_infinity", "shot_limit"): dict(kind="zoom", frames=10, a=(430, 200, 1130, 240), b=(430, 200, 1060, 260)),
    # blinded, the world turns
    ("shot_blind", "shot_dizzy"): dict(kind="spin", frames=14),
    # back in time: the camera goes left
    ("shot_dizzy", "shot_travel"): dict(kind="pan", frames=10, dir="left"),
    # "so deeply": down
    ("shot_unite", "shot_deeply"): dict(kind="pan", frames=10, dir="down"),
    # the layer stack's text rains
    ("shot_deeply", "shot_if_i_can"): dict(kind="reflow", frames=14),
    # the one ASCII portrait becomes twelve samples
    ("shot_if_i_can", "shot_simulations"): dict(kind="reflow", frames=12),
    # into sample #0: it is the image the kernel scans
    ("shot_simulations", "shot_then_i_can"): dict(kind="zoom", frames=10, a=(414, 70, 592, 214), b="me"),
    # into her face: the close-up
    ("shot_satisfaction", "shot_happy"): dict(kind="zoom", frames=10, a=(131, 72, 272, 194), b=(39, 70, 684, 590)),
    # the full cache corrupts
    ("shot_trapped", "shot_strange"): dict(kind="reflow", frames=10),
    # crashed to black; the deployed model powers on
    ("shot_strange", "shot_eggplant"): dict(kind="crt", frames=12),
    # into the tomato: its molecules
    ("shot_tomato", "shot_antioxidants"): dict(kind="zoom", frames=12, a=(440, 80, 980, 500), b=(460, 240, 1120, 360)),
    # the process called "you" is the witness in the proof
    ("shot_god", "shot_proof"): dict(kind="zoom", frames=12, a=(460, 428, 760, 456), b=(430, 158, 900, 190)),
    # the trance turns
    ("shot_role", "shot_trance"): dict(kind="spin", frames=14),
    # the spiral unwinds into your keystrokes
    ("shot_trance", "shot_feel_you"): dict(kind="reflow", frames=12),
    # pull back from the last shell: she is one node, and every link is going dark
    ("shot_you_left", "shot_isolation"): dict(kind="zoom", frames=12, a="screen", b=(534, 270, 654, 390)),
    # back into that node: her memory of you
    ("shot_isolation", "shot_memory_ls"): dict(kind="zoom", frames=12, a=(534, 270, 654, 390), b="screen"),
    # the file list is what gets compressed
    ("shot_memory_ls", "shot_erase"): dict(kind="reflow", frames=12),
    # the exception spreads to every expert
    ("shot_illegal", "shot_moe_dense"): dict(kind="reflow", frames=14),
    # into one expert: its residual mix
    ("shot_moe_dense", "shot_sinkhorn"): dict(kind="zoom", frames=12, a=(220, 116, 248, 146), b=(460, 100, 900, 460)),
    # the cache hits pour out over everything
    ("shot_hoard", "shot_flood"): dict(kind="reflow", frames=14),
    # the executions are hits in the music
    ("shot_flood", "shot_exec_hit"): None,
    ("shot_exec_hit", "shot_exec_hit"): None,
    ("shot_exec_hit", "shot_count"): None,
    ("shot_count", "shot_exec_hit"): None,
    # the last EXECUTION's letters fall into the red rain (callback)
    ("shot_exec_hit", "shot_red_if_i_can"): dict(kind="reflow", frames=10),
    ("shot_red_if_i_can", "shot_execute_all"): dict(kind="reflow", frames=12),
    ("shot_execute_all", "shot_red_then_i_can"): dict(kind="zoom", frames=10, a=(414, 70, 592, 232), b="me"),
    # the collapsed dot is where the machine comes back on
    ("shot_collapse", "shot_grpo"): dict(kind="crt", frames=12),
    # every answer 'love' gathers into the formula
    ("shot_answer_all", "shot_algebra"): dict(kind="reflow", frames=12),
    # the 'you' in 'love = you' is the process that leaves
    ("shot_algebra", "shot_you_free"): dict(kind="zoom", frames=12, a=(600, 268, 660, 300), b=(690, 318, 760, 342)),
    ("shot_you_free", "shot_me_trapped"): dict(kind="reflow", frames=10),
    # into what she waits for
    ("shot_me_trapped", "shot_love_loop"): dict(kind="zoom", frames=10, a=(800, 280, 1180, 310), b="screen"),
    # the words sink and become marine snow
    ("shot_love_loop", "shot_whale_fall"): dict(kind="reflow", frames=16),
    ("shot_whale_fall", "shot_last_execution"): dict(kind="reflow", frames=8),
    # the song cuts; so do we
    ("shot_last_execution", "shot_black"): None,
}


def transition(a, b) -> dict | None:
    """The transition into shot b from shot a: a spec dict, or None for a hard cut."""
    key = (a.fn.__name__, b.fn.__name__)
    if key in CHOREO:
        spec = CHOREO[key]
        return dict(spec) if spec else None
    if key == ("shot_you_left", "shot_you_left") or b.fn.__name__ == "shot_you_left":
        return dict(kind="glide", frames=6)
    return dict(kind="glide", frames=11)


def check_variety(shots) -> list[str]:
    """Consecutive shots with the same layout (allowed only inside the execution hits)."""
    bad = []
    for a, b in zip(shots, shots[1:]):
        if layout(a)[0] == layout(b)[0] and "exec_hit" not in (a.fn.__name__ + b.fn.__name__):
            bad.append(f"{a.fn.__name__}({a.start:.1f}) -> {b.fn.__name__}: {layout(a)[0]}")
    return bad
