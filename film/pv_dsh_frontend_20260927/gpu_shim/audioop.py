"""Stand-in for the stdlib audioop (removed in Python 3.13): only rms(), which full/music.py uses."""
import numpy as np


def rms(fragment, width):
    dt = {1: np.int8, 2: np.int16, 4: np.int32}[width]
    a = np.frombuffer(fragment, dt).astype(np.float64)
    return int(np.sqrt((a * a).mean())) if len(a) else 0
