# Evidence format and interpretation

The report schema is version `1.1`. The JSON is deliberately inspectable without
the application. It is a record of measurements, not a signed attestation.

| Field | Meaning |
| --- | --- |
| `query.sha256` | SHA-256 of the exact query video analyzed |
| `results[].source.sha256` | SHA-256 of the indexed source video; user uploads are normalized before indexing |
| `results[].source.inputSha256` | For newly ingested user sources, SHA-256 of the uploaded bytes before normalization |
| `retrieval.engine`, `revision` | Actual embedding model identifier and pinned model revision, or `visual-only` |
| `retrieval.rankings` | Candidate ordering and uncalibrated cosine scores; not match probabilities |
| `alignment.queryStart`, `queryEnd` | Earliest and latest query timestamps participating in the fitted consensus |
| `alignment.sourceStart`, `sourceEnd` | Corresponding estimated source interval within the indexed excerpt |
| `alignment.speed`, `offset` | Fitted relation: source time = speed × query time + offset |
| `alignment.speedRange` | Deterministic consistency range under the algorithm's timestamp tolerance; not a confidence interval or guaranteed error bound |
| `alignment.speedReliable` | Heuristic indicating enough temporal support and a sufficiently constrained fit; not a calibrated reliability probability |
| `alignment.timingAmbiguous` | Another comparably supported timing explanation was found |
| `alignment.support` | Number of distinct query frames supporting the fit; duplicate candidates do not add votes |
| `coverage` | Supported query frames divided by sampled query frames; not percent of pixels copied |
| `evidence[].points` | Normalized query/source coordinates for up to 36 verified correspondences per frame pair; the full inlier count can be larger |
| `evidence[].quad` | Estimated query-image boundary projected into source coordinates |
| `evidence[].mirrored` | Whether verification used horizontal reflection of the query |
| `evidenceAssets` | Exact evidence filenames and SHA-256 hashes |
| `engineFingerprint` | SHA-256 of the concatenated bytes of `server/media.py`, `temporal.py`, `embedding.py`, and `engine.py`, in that order, captured when the engine imports |

The source's `originalOffset` identifies the excerpt's start within the bundled
original film. It is metadata used for attribution and explanation, not an input
to the matching algorithm. A reported source time is relative to the indexed
excerpt, not to the full original film.

The engine fingerprint identifies four core implementation files. It does not
hash the whole environment or authenticate the author. The repository commit,
lockfiles, vendored wrapper, model revision, media hashes, and report together
provide the reproduction context. CPU library versions and numerical behavior
can still affect exact correspondences.

## Exported ZIP

The export adds `exportedAt` and attribution, then hashes the exact serialized
`report.json` bytes into `report.sha256`. Every referenced inspected frame is
included under `frames/`; original source/query videos are not included. The
verifier rejects mismatched image hashes, missing referenced frames, unexpected
filenames, duplicate ZIP entries, and oversized packets without extracting files.

A person who alters both the report and its hashes can produce a different,
internally consistent packet. No signature, trusted timestamp, ownership
certificate, or legal conclusion is implied.

## Interpreting an abstention

“No verified match” means the configured method did not verify a source in this
specific indexed library. It does not mean the query is original, lawful,
synthetic, or absent from the wider internet. A partial match can establish shared
imagery for some sampled frames without explaining the entire edit.

## Browser packet review

The **Verify a packet** workspace checks ZIP structure and size limits, report
SHA-256, inventory completeness, and every included JPEG hash before presenting
reported measurements and frame pairs. It makes no analysis calls and sends no
upload. Altered files, missing images, duplicate entries, and unknown files stop
verification. A packet with data and checksums consistently replaced can still
pass; integrity is not authentication. Original source/query videos are not in
the packet and are not verified by this operation.
