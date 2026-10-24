"""Optional report figure: pip install matplotlib, then run after publishing evaluation."""

import json
from pathlib import Path
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
data = json.loads((ROOT / "public/evaluation.json").read_text())
rows = [r for r in data["cases"] if r.get("source") and "offsetError" in r]
groups = list(dict.fromkeys(r["transform"] for r in rows))
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.edgecolor": "#cbd6c2",
        "axes.labelcolor": "#244f42",
        "text.color": "#203c36",
        "xtick.color": "#657366",
        "ytick.color": "#657366",
        "figure.facecolor": "#f6f7f3",
        "axes.facecolor": "#f6f7f3",
        "svg.fonttype": "none",
    }
)
fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.3))
for ax, key, label in [
    (axes[0], "offsetError", "Absolute start-time error (seconds)"),
    (axes[1], "speedError", "Absolute playback-speed error (×)"),
]:
    for i, group in enumerate(groups):
        cases = [r for r in rows if r["transform"] == group]
        values = [r[key] for r in cases]
        positions = np.linspace(i - 0.18, i + 0.18, len(cases))
        ax.scatter(
            values,
            positions,
            s=48,
            c="#244f42",
            zorder=3,
            edgecolors="white",
            linewidths=0.8,
        )
        ax.plot(
            [float(np.median(values))] * 2,
            [i - 0.3, i + 0.3],
            color="#162f26",
            linewidth=2.1,
            zorder=4,
        )
    ax.set_yticks(range(len(groups)), [g.replace("-", " ") for g in groups])
    ax.invert_yaxis()
    ax.grid(axis="x", color="#e0e6d9", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_xlabel(label, labelpad=12)
    ax.set_xlim(left=-0.01 if key == "offsetError" else -0.002)
axes[0].set_title(
    "Where timing is accurate — and where it drifts",
    loc="left",
    fontweight="bold",
    pad=20,
)
axes[1].set_title(
    "Playback estimates are measurements, not guarantees",
    loc="left",
    fontweight="bold",
    pad=20,
)
fig.text(
    0.02,
    0.025,
    f"{data['suite']} · {len(rows)} recovered positive clips · Each dot is one case; dark ticks mark medians. Same four source excerpts.",
    fontsize=10,
    color="#657366",
)
fig.tight_layout(rect=(0, 0.07, 1, 1), w_pad=3)
fig.savefig(ROOT / "public/evaluation-timing.svg", bbox_inches="tight")
fig.savefig(ROOT / "docs/media/evaluation-timing.png", dpi=160, bbox_inches="tight")
svg = ROOT / "public/evaluation-timing.svg"
svg.write_text("\n".join(line.rstrip() for line in svg.read_text().splitlines()) + "\n")
print("Saved timing-error figure from every recovered positive case.")
