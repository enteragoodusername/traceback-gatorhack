"""Qualitative multilingual search inspection via a running local Traceback API."""

import argparse, hashlib, json, pathlib, urllib.request

p = argparse.ArgumentParser()
p.add_argument("--out", type=pathlib.Path, required=True)
p.add_argument("--base", default="http://127.0.0.1:8000")
a = p.parse_args()
if a.out.exists() and any(a.out.iterdir()):
    p.error("Use an empty output directory to preserve earlier observations.")
a.out.mkdir(parents=True, exist_ok=True)
queries = [
    ("en", "A man and a woman talking on a bridge over a canal"),
    ("es", "Un hombre y una mujer hablan en un puente sobre un canal"),
    ("zh", "一名男子和一名女子在运河上的桥上交谈"),
    ("en", "Scientists surrounded by laboratory equipment"),
    ("es", "Científicos rodeados de equipos de laboratorio"),
    ("zh", "科学家被实验室设备包围"),
    ("en", "Giant robots walking through a city"),
    ("es", "Robots gigantes caminando por una ciudad"),
    ("zh", "巨型机器人走过城市"),
    ("en", "Dolphins swimming in the ocean"),
    ("en", "A chef baking a pizza in a restaurant"),
    ("en", "A basketball game in a stadium"),
]
plan = dict(
    scope="Qualitative free-text search inspection. Three scene descriptions in three languages, plus three absent-concept queries. No labeled relevance score or multilingual generalization claim. Search always returns nearest candidates; a similarity score is not proof that the requested concept is present.",
    queries=[dict(language=l, query=q) for l, q in queries],
)
(a.out / "plan.json").write_text(json.dumps(plan, indent=2, ensure_ascii=False))
rows = []
for i, (lang, q) in enumerate(queries):
    req = urllib.request.Request(
        a.base + "/api/search",
        data=json.dumps({"query": q}).encode(),
        headers={"Content-Type": "application/json"},
    )
    result = json.load(urllib.request.urlopen(req, timeout=180))
    hits = result["results"]
    top = hits[0]
    image = urllib.request.urlopen(
        a.base + f"/api/frames/{top['sourceId']}/{int(top['time'])}", timeout=30
    ).read()
    name = f"{i:02d}-{lang}.jpg"
    (a.out / name).write_bytes(image)
    row = dict(
        language=lang,
        query=q,
        engine=result["engine"],
        results=hits,
        topFrame=name,
        topFrameSha256=hashlib.sha256(image).hexdigest(),
    )
    rows.append(row)
    (a.out / "summary.json").write_text(
        json.dumps(
            {**plan, "complete": len(rows) == len(queries), "observations": rows},
            indent=2,
            ensure_ascii=False,
        )
    )
    print(json.dumps({"query": q, "top": top}, ensure_ascii=False), flush=True)
