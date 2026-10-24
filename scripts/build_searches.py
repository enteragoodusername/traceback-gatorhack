"""Publish real text-to-frame retrieval runs for the hosted demo."""

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server.engine import semantic_search, INDEX
from server.embedding import MODEL_ID, MODEL_REVISION

queries = [
    "Two people talking on a bridge",
    "A scientist with computer screens",
    "Giant robots in a city",
    "A man wearing glasses",
]
out = ROOT / "public/semantic-frames"
out.mkdir(exist_ok=True)
searches = []
for query in queries:
    results = semantic_search(query)
    searches.append(dict(query=query, results=results))
    for result in results:
        i = int(result["time"])
        shutil.copyfile(
            INDEX / result["sourceId"] / f"{i:03}.jpg",
            out / f"{result['sourceId']}-{i}.jpg",
        )
    print(query, results[:3], flush=True)
(ROOT / "public/semantic-searches.json").write_text(
    json.dumps(
        dict(
            engine=MODEL_ID,
            revision=MODEL_REVISION,
            recorded=True,
            inputs="Text queries and source frame pixels only; no titles or captions.",
            searches=searches,
        ),
        indent=2,
    )
)
