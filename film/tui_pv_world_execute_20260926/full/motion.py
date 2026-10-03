"""The shared vocabulary between the choreography (choreo.py), the rig that deforms her (rig.py) and the glyph
renderer (dancer.py). All angles in degrees, all offsets as fractions of her figure height unless noted."""

from __future__ import annotations

from dataclasses import dataclass

# the pose library: one full-body sprite each, all drawn on the same canvas at the same scale
POSES = {
    "cheerful": "hand waving at face height, wink",
    "shy": "hand on chest",
    "serious": "index finger raised, explaining",
    "confused": "hand to chin, thinking",
    "angry": "hands on hips",
    "frightened": "both hands up, surprised",
    "exasperated": "arms crossed",
    "starry": "arm raised high, excited",
    "skirt": "holding up the skirt hem, other hand waving low (curtsy)",
}


@dataclass
class Motion:
    sway: float = 0.0        # lean of the whole body around the feet, degrees (+ = top moves right)
    bend: float = 0.0        # extra lean of the upper body only (curved spine), degrees
    squash: float = 0.0      # 0..1: height squashed / width widened, anchored at the feet (landing, beat hit)
    hop: float = 0.0         # lift off the ground, fraction of figure height (0.03 = a small jump)
    shift: float = 0.0       # sideways step, fraction of figure height (+ = right)
    head: float = 0.0        # head tilt around the neck, degrees
    hair: float = 0.0        # -1..1 long hair swing (follow-through, lags the body)
    hem: float = 0.0         # -1..1 skirt hem swing
    tail: float = 0.0        # -1..1 tail wag
    turn: float = 0.0        # 0..1 progress of a turn: width scales |cos(pi*turn)|, image mirrors past 0.5


@dataclass
class Step:
    pose: str                # current pose (key of POSES)
    flip: bool = False       # mirrored pose
    prev: str | None = None  # pose we are morphing from, if a pose change is in progress
    prev_flip: bool = False
    morph: float = 1.0       # 0..1 progress of the change from prev to pose (1 = done)
    motion: Motion | None = None
    flow: float = 1.0        # speed of the text streaming through her body, 0 = still, 1 = normal, 3 = racing
    scramble: float = 0.0    # 0..1 glyph scramble (glitch, execution)
    move: str = "idle"       # name of the move, for debugging and the on-screen tag
