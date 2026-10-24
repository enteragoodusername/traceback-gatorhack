# Verification record

Build date: October 24, 2026. Hardware: Intel Core i7-1165G7 CPU, no GPU.

## Frozen-engine controlled evaluation

Suite: `heldout-refined-v4`, seed `92617`. The four core engine files remained
unchanged during this run. Every case records the same engine fingerprint:
`328f842cbcff435236c57e1760716de6caae3728d2e9499e2dee5371e5a65614`.

| Measurement | Observed result |
| --- | --- |
| Edited source recovery | 32 / 32 |
| Negative abstentions | 8 / 8 |
| Cases containing a false source match | 0 |
| Correct source ranked first by Qwen | 32 / 32 positive queries |
| Median start-time error | 0.046 seconds |
| Largest start-time error | 0.322 seconds |
| Median absolute speed error | 0.000× after rounding to three decimals |
| Largest absolute speed error | 0.078× |
| Median runtime | 65.2 seconds, with concurrent local work |

The source library contains four 40-second excerpts from Tears of Steel.
Eight edit families cover re-encoding, vertical crops, grayscale and captions,
horizontal reflection with slow playback, zoom with faster playback, rotation,
letterboxing, and low-quality compression. Positive offsets were independently
sampled for this suite. The same source works were used in development; “held
out” refers to new edit instances, not unseen films. Negative construction and
source offsets are in `scripts/benchmark.py`.

The complete public record is `public/evaluation.json`, including query hashes
and every outcome. The plot in `docs/media/evaluation-timing.png` includes all
recovered positive cases. These are controlled measurements, not a production
accuracy estimate. Consistency intervals are not calibrated confidence bounds.

## Development history

The initial 24-case development suite recovered the expected sources but
revealed coarse timing weaknesses. An intermediate larger run was stopped after
additional timing errors appeared. Neither is presented as the final held-out
result. The multi-candidate 4 fps refinement was then developed, and a fresh
seed was used for the complete frozen-engine suite above.

## New-source HTTP workflow

A separate Sintel trailer excerpt was uploaded through `/api/sources`, indexed
with the actual local model, searched through `/api/search`, and recovered from
a cropped, reflected, 1.2× query through `/api/analyze`. The correct new source
ranked first, ten frames supported it, no other source matched, and all twelve
returned evidence image hashes verified. The observed offset error was 0.145s
and speed error was 0.0052×. The temporary source was removed after the check;
its local test artifacts were preserved. See `public/validation/live-ingestion.json`.

## Diagnostic stress cases

`public/validation/stress-cases.json` reports eight deliberately difficult or
unsupported edits separately from the accuracy-style evaluation. These include
reverse playback, severe blur and occlusion, a frozen frame, featureless inputs,
a nonlinear speed change, and a small inset. They are diagnostic observations,
not eight additional “passes.”

## Automated checks

- 33 Python tests cover geometric false matches and transformed positives,
  temporal degeneracies, API validation and queue handling, provider failure
  behavior with mocked transports, and ZIP integrity.
- 32 interface tests cover recorded and live API paths, multi-source selection,
  semantic search, source attribution, export checksums, keyboard behavior,
  and accessible DOM structure.
- Strict TypeScript compilation and the Vite production build pass.
- `scripts/audit_release.py` checks the four sources, five recorded runs, sixty
  inspected evidence images, four semantic queries, and all forty evaluation
  cases against the shipped core fingerprint and media checksums.
- `scripts/check_static_build.py` verifies HTML/CSS references for the GitHub
  Pages subdirectory build.
- The actual CLI evidence export passes the independent packet verifier.
- The production npm dependency audit reported zero known vulnerabilities at
  build time. This is a point-in-time package check, not a security guarantee.

## Verification limits

No browser automation surface was available in this environment, including an
attempt to open the in-app browser. DOM accessibility tests do not validate
visual layout or color contrast. The generated video frames and scientific plot
were visually inspected, but they are evidence visualizations rather than app
screenshots. HTTP workflows and static asset checks were exercised directly.

Gemini and Twinly transports are tested with explicit mocks. No live paid API
success or sponsor eligibility is claimed without credentials and a genuine run.

## Published artifacts

The public GitHub Pages root, manifest, full evaluation, montage report, stress
record, MP4, captions, and sample ZIP returned HTTP 200. The downloaded data and
media matched local SHA-256 hashes. GitHub Actions completed successfully for
the initial release. The owner-private Sites deployment also completed through
the native publishing service.

## Fresh checkout installation

A separate shallow clone of the public repository installed the hash-pinned
Python dependencies into a new virtual environment, installed the npm lockfile,
built the application, and regenerated all four source indexes. This reused the
already downloaded Hugging Face model cache; it did not reuse the project's
virtual environment, node_modules, or source indexes. The CPU index resolver
configuration was corrected before this successful check.

The fresh checkout then ran the cropped query with `HF_HUB_OFFLINE=1`. Query
metadata, retrieval values, complete geometric/temporal results, engine
fingerprint, and every evidence image hash were identical to the shipped
recorded run. Its independently exported ZIP also verified. The published
record is `public/validation/reproducibility.json`. Runtime was profiled and is
not compared as a latency benchmark.

## Packet viewer and restart recovery

The browser verifier passed the actual published packet and rejected modified
reports, modified images, missing inventory entries, unexpected paths, excessive
expanded sizes, and malformed measurements. A consistently rewritten report
with its updated checksum passes, as expected: this is integrity checking, not
authentication. The viewer sends no upload and clearly labels that analysis was
not rerun.

After restarting the actual local server, the earlier completed HTTP job was
restored from disk. Its served original query bytes matched the SHA-256 in the
report. Interface checks cover reopening that original query, clearing stale
job IDs, and discarding delayed explanations after the selected clip changes.

## Additional-film verification

The unchanged engine verified 7 of 8 transformed Big Buck Bunny clips after two
new excerpts were indexed in an isolated six-source library. It rejected both
unindexed same-film negatives and produced no false source matches. The one
abstention was a re-encoding that Qwen ranked first, but whose geometric
candidates did not yield a temporal fit. Every case and its report hash are
published in `public/validation/cross-work.json`. These ten cases are separate
from the four-source 40-case evaluation.
