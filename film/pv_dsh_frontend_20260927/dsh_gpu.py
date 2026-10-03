"""tuikit.post on the GPU (torch/CUDA): the bloom blur, the add, the trail and the scanlines of every frame.

Post is about 40 % of a frame on the CPU (PIL's 1280x720 Gaussian blur alone is ~30 ms); the rest of a frame is PIL
drawing and stays on the CPU. Enabled by DSH_GPU=1 (dsh_her.install calls install()); it needs a Python with torch,
for example a Python with torch (only its interpreter is used, ComfyUI itself is not touched), with
gpu_shim/ on PYTHONPATH for the stdlib audioop that Python 3.13 dropped:

    $env:DSH_GPU='1'; $env:PYTHONPATH='gpu_shim'
    <python with torch> dsh_her.py render 0 211 film.mp4 8

The output matches the CPU post to within a level or two (a true Gaussian of sigma 4 instead of PIL's box
approximation); `python dsh_gpu.py check 104.5` prints the difference on one frame.
"""
from __future__ import annotations

import sys

import numpy as np
from PIL import Image

_T = {}


def _torch():
    if not _T:
        import torch
        dev = torch.device("cuda")
        r = 12                                                    # 3 sigma, sigma = PIL's blur radius 4
        x = torch.arange(-r, r + 1, dtype=torch.float32, device=dev)
        k = torch.exp(-(x / 4.0) ** 2 / 2)
        _T.update(torch=torch, dev=dev, k=(k / k.sum()), r=r)
    return _T


def _blur(t, x):
    """Separable Gaussian on a (3, H, W) float tensor, edges replicated (as PIL does)."""
    torch = t["torch"]
    F = torch.nn.functional
    k, r = t["k"], t["r"]
    y = x.unsqueeze(1)                                           # (3, 1, H, W)
    y = F.pad(y, (r, r, 0, 0), mode="replicate")
    y = F.conv2d(y, k.view(1, 1, 1, -1))
    y = F.pad(y, (0, 0, r, r), mode="replicate")
    y = F.conv2d(y, k.view(1, 1, -1, 1))
    return y.squeeze(1)


def post(img, prev, trail=0.42, bloom=0.35, _vignette=None):
    t = _torch()
    torch = t["torch"]
    x = torch.from_numpy(np.asarray(img.convert("RGB"))).to(t["dev"]).permute(2, 0, 1).float()
    if prev is not None and trail > 0:
        p = torch.from_numpy(np.asarray(prev.convert("RGB"))).to(t["dev"]).permute(2, 0, 1).float()
        x = torch.maximum(x, torch.floor(p * trail))
    x = torch.clamp(x + torch.floor(_blur(t, x) * bloom), 0, 255)
    x[:, 0::3, :] = torch.floor(x[:, 0::3, :] * (200 / 255) + 0.5)   # scanlines: black at alpha 55 every 3rd row
    out = Image.fromarray(x.round().clamp(0, 255).byte().permute(1, 2, 0).contiguous().cpu().numpy(), "RGB")
    if _vignette is not None:                                     # only if the vignette is still on
        out = out.convert("RGBA")
        out.alpha_composite(_vignette())
        out = out.convert("RGB")
    return out


def install(tk):
    if getattr(tk.post, "_gpu", False):
        return
    orig = tk.post
    vig = None if getattr(tk.vignette, "_dsh", False) else (lambda: tk.vignette(tk.LYRIC_LIFT[0]))

    def gpu_post(img, prev, trail=0.42, bloom=0.35):
        return post(img, prev, trail, bloom, vig)

    gpu_post._gpu = True
    gpu_post._orig = orig
    for m in list(sys.modules.values()):                       # modules that did `from tuikit import post`
        if getattr(m, "post", None) is orig:
            try:
                m.post = gpu_post
            except Exception:
                pass
    tk.post = gpu_post


if __name__ == "__main__" and sys.argv[1:2] == ["check"]:
    import os
    os.environ.pop("DSH_GPU", None)
    import dsh_her as D
    v2, _ = D.install()
    import tuikit as tk
    t = float(sys.argv[2])
    n = round(t * 24)
    D.CUR[0] = t
    cpu = np.asarray(D.finish(v2.frame(n), t)).astype(int)
    install(tk)
    gpu = np.asarray(D.finish(v2.frame(n), t)).astype(int)
    d = np.abs(cpu - gpu)
    print(f"mean |diff| {d.mean():.3f}   p99 {np.percentile(d, 99):.0f}   max {d.max()}")
