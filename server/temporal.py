"""Deterministic multi-hypothesis alignment with one vote per query timestamp."""

import numpy as np


def fit_temporal(matches: list[dict], tolerance: float = 0.65) -> dict | None:
    if len(matches) < 3:
        return None
    q = np.array([m["queryTime"] for m in matches], dtype=float)
    s = np.array([m["sourceTime"] for m in matches], dtype=float)
    unique_q, groups = np.unique(q, return_inverse=True)
    if len(unique_q) < 3:
        return None
    weights = np.array(
        [
            min(m["inliers"], 100) * max(0.1, m.get("photometricCorrelation", 1))
            for m in matches
        ],
        dtype=float,
    )

    # Each query timestamp gets one vote, even if many source frames look alike.
    def select(speed, offset):
        residual = np.abs(s - (q * speed + offset))
        quality = np.where(
            residual <= tolerance, weights * (1 - 0.2 * residual / tolerance), 0
        )
        maxima = np.zeros(len(unique_q))
        np.maximum.at(maxima, groups, quality)
        support = int((maxima > 0).sum())
        return support * 1000 + float(maxima.sum()), support, residual, quality

    if len(matches) <= 55:
        pairs = [
            (i, j) for i in range(len(matches)) for j in range(i + 1, len(matches))
        ]
    else:
        rng = np.random.default_rng(0)
        pairs = rng.integers(0, len(matches), size=(2400, 2))
    hypotheses = []
    for i, j in pairs:
        if abs(q[j] - q[i]) < 1:
            continue
        speed = (s[j] - s[i]) / (q[j] - q[i])
        if not 0.35 <= speed <= 3:
            continue
        offset = s[i] - speed * q[i]
        score, support, _, _ = select(speed, offset)
        if support >= 3:
            hypotheses.append((score, support, float(speed), float(offset)))
    if not hypotheses:
        return None
    hypotheses.sort(reverse=True)
    _, _, speed, offset = hypotheses[0]
    selected_indices = []
    for _ in range(2):
        score, support, residual, quality = select(speed, offset)
        selected_indices = []
        for group in range(len(unique_q)):
            indices = np.where((groups == group) & (quality > 0))[0]
            if len(indices):
                selected_indices.append(int(indices[np.argmax(quality[indices])]))
        if len(selected_indices) < 3:
            return None
        keep = np.array(selected_indices)
        if np.ptp(q[keep]) < 1.5:
            return None
        design = np.vstack([q[keep], np.ones(len(keep))]).T
        speed, offset = np.linalg.lstsq(
            design * weights[keep, None] ** 0.5,
            s[keep] * weights[keep] ** 0.5,
            rcond=None,
        )[0]
        if not 0.35 <= speed <= 3:
            return None
    score, support, residual, quality = select(speed, offset)
    keep = np.array([i for i in selected_indices if residual[i] <= tolerance])
    if len(keep) < 3 or np.ptp(q[keep]) < 1.5:
        return None
    selected = [matches[i] for i in keep]
    lower, upper = 0.35, 3.0
    for i in range(len(selected)):
        for j in range(i + 1, len(selected)):
            dq = selected[j]["queryTime"] - selected[i]["queryTime"]
            if abs(dq) < 1e-6:
                continue
            ds = selected[j]["sourceTime"] - selected[i]["sourceTime"]
            bounds = sorted(((ds - 2 * tolerance) / dq, (ds + 2 * tolerance) / dq))
            lower = max(lower, bounds[0])
            upper = min(upper, bounds[1])
    qmin, qmax = float(q[keep].min()), float(q[keep].max())
    ambiguous = False
    for (
        candidate_score,
        candidate_support,
        candidate_speed,
        candidate_offset,
    ) in hypotheses[:150]:
        if candidate_support < len(keep) or candidate_score < score * 0.97:
            continue
        delta = max(
            abs((candidate_speed - speed) * qt + candidate_offset - offset)
            for qt in (qmin, qmax)
        )
        if delta > 1.0:
            ambiguous = True
            break
    reliable = (
        len(keep) >= 6 and qmax - qmin >= 3 and upper - lower <= 0.35 and not ambiguous
    )
    return dict(
        speed=round(float(speed), 4),
        speedRange=[round(lower, 4), round(upper, 4)],
        speedReliable=bool(reliable),
        timingAmbiguous=ambiguous,
        toleranceSeconds=tolerance,
        offset=round(float(offset), 4),
        queryStart=qmin,
        queryEnd=qmax,
        sourceStart=round(float(qmin * speed + offset), 3),
        sourceEnd=round(float(qmax * speed + offset), 3),
        support=len(selected),
        residual=round(float(np.median(residual[keep])), 4),
        matches=selected,
    )
