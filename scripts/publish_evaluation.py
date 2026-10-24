"""Summarize every completed case, including failures, for the public method page."""

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("suite")
args = parser.parse_args()
summary = json.loads(
    (ROOT / "artifacts/benchmarks" / args.suite / "summary.json").read_text()
)
rows = summary["results"]
reports = [
    json.loads(
        (
            ROOT / "artifacts/benchmarks" / args.suite / row["id"] / "report.json"
        ).read_text()
    )
    for row in rows
]
fingerprints = {report.get("engineFingerprint") for report in reports}
for row, report in zip(rows, reports):
    row["querySha256"] = report["query"]["sha256"]
    row["engineFingerprint"] = report.get("engineFingerprint")

positive = [r for r in rows if r["source"] is not None]
negative = [r for r in rows if r["source"] is None]
groups = defaultdict(list)
for row in rows:
    groups[row["transform"]].append(row)
result = dict(
    suite=summary["suite"],
    seed=summary["seed"],
    engineFingerprint=next(iter(fingerprints)) if len(fingerprints) == 1 else None,
    singleEngineFingerprint=len(fingerprints) == 1 and None not in fingerprints,
    model=reports[0]["retrieval"]["engine"] if reports else None,
    modelRevision=reports[0]["retrieval"]["revision"] if reports else None,
    complete=summary["completed"] == summary["total"],
    generatedAt=datetime.now(timezone.utc).isoformat(),
    visualOnly=summary["visualOnly"],
    total=len(rows),
    positiveCount=len(positive),
    negativeCount=len(negative),
    recovered=sum(r["correct"] for r in positive),
    abstained=sum(not r["found"] for r in positive),
    rejected=sum(not r["found"] for r in negative),
    falseMatchCases=sum(bool(r["falseMatches"]) for r in rows),
    medianOffsetError=round(
        statistics.median(r["offsetError"] for r in positive if "offsetError" in r), 3
    )
    if any("offsetError" in r for r in positive)
    else None,
    medianSpeedError=round(
        statistics.median(r["speedError"] for r in positive if "speedError" in r), 3
    )
    if any("speedError" in r for r in positive)
    else None,
    medianLatency=round(statistics.median(r["elapsedSeconds"] for r in rows), 1),
    speedUncertain=sum(r.get("speedReliable") is False for r in positive),
    semanticTop1Correct=sum(r.get("semanticTop1") == r["source"] for r in positive),
    semanticTop1Total=sum(r.get("semanticTop1") is not None for r in positive),
    maxOffsetError=max(
        (r["offsetError"] for r in positive if "offsetError" in r), default=None
    ),
    maxSpeedError=max(
        (r["speedError"] for r in positive if "speedError" in r), default=None
    ),
    groups=[
        dict(
            name=name,
            total=len(group),
            passed=sum(r["correct"] and not r["falseMatches"] for r in group),
        )
        for name, group in groups.items()
    ],
    cases=rows,
    scope="Four indexed 40-second excerpts from Tears of Steel. Positive queries use independently chosen offsets and scripted edits. Negatives include Sintel and unindexed scenes from Tears of Steel.",
    limitations=[
        "Small, synthetic-edit evaluation; not a representative production benchmark.",
        "Development results informed thresholds. A separately seeded held-out suite is reported when complete.",
        "Source retrieval success does not imply accurate ownership attribution or legal conclusions.",
        "Timing errors are conditional on a recovered source; abstentions are reported separately.",
    ],
    hardware="Intel Core i7-1165G7 CPU, no GPU. Local concurrent tasks affect latency.",
)
(ROOT / "public/evaluation.json").write_text(json.dumps(result, indent=2))
print({k: v for k, v in result.items() if k not in ("cases", "groups", "limitations")})
