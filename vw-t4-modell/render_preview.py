#!/usr/bin/env python3
"""Vorschaubilder einer binaeren STL per einfachem Z-Buffer (numpy + matplotlib).
Aufruf: python3 render_preview.py modell.stl vorschau.png"""
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

path, out = sys.argv[1], sys.argv[2]
raw = open(path, "rb").read()
n = int(np.frombuffer(raw[80:84], np.uint32)[0])
tri = np.frombuffer(raw[84:], dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")],
                    count=n)["v"].astype(np.float64)
nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
area = np.linalg.norm(nrm, axis=1) / 2
nrm /= np.maximum(2 * area[:, None], 1e-12)

RES = int(sys.argv[3]) if len(sys.argv) > 3 else 700
span = (tri.reshape(-1, 3).max(0) - tri.reshape(-1, 3).min(0)).max()
px = span * 1.15 / RES
# Punkte gleichmaessig auf den Dreiecken verteilen
cnt = np.maximum(1, np.ceil(area / (px * px * 0.15))).astype(int)
idx = np.repeat(np.arange(n), cnt)
r1, r2 = np.random.rand(len(idx)), np.random.rand(len(idx))
s = np.sqrt(r1)
a, b, c = 1 - s, s * (1 - r2), s * r2
t = tri[idx]
P = a[:, None] * t[:, 0] + b[:, None] * t[:, 1] + c[:, None] * t[:, 2]
N = nrm[idx]
center = (tri.reshape(-1, 3).max(0) + tri.reshape(-1, 3).min(0)) / 2
P -= center

views = [(12, -35, "Detail Front"), (6, -100, "Detail Seite")] if len(sys.argv) > 4 else [(18, -55, "vorne rechts"), (18, 125, "hinten links"), (0, -90, "Seite rechts"),
         (8, 0, "Front"), (8, 180, "Heck"), (55, -35, "oben")]
fig, axs = plt.subplots(*((1, 2) if len(views) == 2 else (2, 3)), figsize=(18, 11) if len(views) == 6 else (20, 10))
for ax, (el, az, title) in zip(axs.flat, views):
    e, z = np.radians(el), np.radians(az)
    cam = np.array([np.cos(e) * np.cos(z), np.cos(e) * np.sin(z), np.sin(e)])
    right = np.cross([0, 0, 1], cam); right /= np.linalg.norm(right)
    up = np.cross(cam, right)
    u = (P @ right / px + RES / 2).astype(int)
    v = (RES / 2 - P @ up / px).astype(int)
    depth = P @ cam
    ok = (u >= 0) & (u < RES) & (v >= 0) & (v < RES) & (N @ cam > -0.02)
    lin = v[ok] * RES + u[ok]
    zb = np.full(RES * RES, -np.inf)
    np.maximum.at(zb, lin, depth[ok])
    win = depth[ok] >= zb[lin] - 1e-9
    img = np.ones((RES * RES, 3))
    light = cam + 0.6 * up + 0.3 * right; light /= np.linalg.norm(light)
    sh = 0.18 + 0.82 * np.clip(N[ok][win] @ light, 0, 1)
    img[lin[win]] = np.column_stack([sh * 0.62, sh * 0.80, sh * 0.98])
    ax.imshow(img.reshape(RES, RES, 3), interpolation="bilinear")
    ax.set_title(title, fontsize=14)
    ax.axis("off")
plt.tight_layout()
plt.savefig(out, dpi=90)
