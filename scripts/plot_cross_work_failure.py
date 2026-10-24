"""Plot a recorded failure diagnosis without changing or rerunning the engine."""

import json
from pathlib import Path
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
rows = json.loads((ROOT / "public/validation/cross-work-diagnosis.json").read_text())
points, fit = rows["candidates"], rows["fit"]
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.labelcolor": "#203c36",
        "text.color": "#203c36",
        "xtick.color": "#65746c",
        "ytick.color": "#65746c",
    }
)
fig, ax = plt.subplots(figsize=(9, 4.6), dpi=160)
fig.patch.set_facecolor("#f6f7f3")
ax.set_facecolor("#f6f7f3")
ax.scatter(
    [p["queryTime"] for p in points],
    [p["sourceTime"] for p in points],
    s=[max(20, min(100, p["inliers"]) * 0.8) for p in points],
    c="#244f42",
    alpha=0.62,
    linewidths=0.4,
    edgecolors="white",
    label="Retained coarse correspondences",
)
x = np.linspace(0, 7.5, 100)
ax.plot(
    x,
    x + 2.35,
    color="#377f9e",
    linestyle="--",
    linewidth=2,
    label="Known construction: 1.0x, +2.35s",
)
ax.plot(
    x,
    x * fit["selectedSpeed"] + fit["selectedOffset"],
    color="#a85b47",
    linewidth=2,
    label=f"Rejected refined fit: {fit['selectedSpeed']:.3f}x",
)
ax.set(
    xlabel="Query time (seconds)",
    ylabel="Candidate source time (seconds)",
    xlim=(-0.2, 8),
    ylim=(0, 13),
)
ax.grid(alpha=0.15)
ax.set_axisbelow(True)
ax.set_title(
    "Correct retrieval. No supported temporal result.",
    loc="left",
    fontweight="bold",
    fontsize=14,
    pad=46,
)
ax.legend(
    loc="lower left", bbox_to_anchor=(0, 1.01), ncol=3, frameon=False, fontsize=8.2
)
fig.text(
    0.08,
    0.035,
    "Diagnostic uses known synthetic timestamps only to inspect the failure; ground truth never enters the engine.",
    fontsize=8,
    color="#65746c",
)
fig.subplots_adjust(left=0.08, right=0.98, top=0.79, bottom=0.17)
fig.savefig(
    ROOT / "public/validation/cross-work-failure.svg", facecolor=fig.get_facecolor()
)
fig.savefig(ROOT / "docs/media/cross-work-failure.png", facecolor=fig.get_facecolor())
