# v0.2 live internet search verification

The current application accepts one video file and makes fresh online searches. It does not ship prerecorded answers or demo footage.

- Automated checks: 43 backend tests and 28 UI/utility tests passed. Coverage includes upload-triggered submission, drag/drop, invalid files, duplicate submission prevention, provider filtering, saved links, optional description refinement, result recovery, trusted embed URLs, keyboard dismissal, and DOM accessibility. Backend checks cover live-provider parsing, provider failures, thumbnail host restrictions, real-pixel ranking data flow, honest score failure, upload validation, queue limits, refinement and asset scoping.
- Production build: TypeScript/Vite build and `scripts/check_internet_build.py` confirm working asset references and no bundled videos, reports, demo ZIPs or stored-answer paths.
- Actual live smoke test, October 24, 2026: newly downloaded NASA TROPICS launch footage, submitted through the HTTP upload endpoint with no precomputed answers. An 8-second excerpt containing a NASA title card produced logo and aerial-scene queries and 12 live candidates in 131.2 seconds. A separate 8-second launch excerpt produced rocket-launch queries and 12 live candidates in 87.0 seconds, with successful responses from both YouTube and Internet Archive and visual scores from the local Qwen model. These observations demonstrate operation, not a relevance or retrieval-accuracy benchmark.
- The second run's highest-ranked candidates included actual rocket launch videos. Captions and thumbnails can still be wrong or incomplete; results are similar-video leads, not source verification.
- Native browser automation was unavailable in this session. DOM interaction and accessibility checks passed; actual responsive rendering, playback permissions and third-party embedded-player behavior were not browser-verified. No claim of a contrast audit is made.

The prior v0.1 measurements below describe a different, local source-verification workflow. They do not measure this internet-search version and are retained only as historical engineering evidence.

---

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
were visually inspected. A Sites-generated 1200×750 screenshot of the earlier
published landing view was also inspected; it showed the real application with
no visible clipping in that viewport. This does not validate interactions or
mobile layout. HTTP workflows and static asset checks were exercised directly.

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

## Larger-library retrieval

The pinned model ranked the correct target first for 30/32 existing positive
queries and in the top five for 32/32 across 57 sources and 305 actual frame
embeddings. The expanded library adds 24 disjoint same-film excerpts and 29
Big Buck Bunny excerpts. Both top-one misses ranked second. Every rank, top-five
list, source construction, and input hash is in
`public/validation/retrieval-scale.json`. Targets are 40 seconds and distractors
20 seconds; max pooling can favor longer references. These are reused queries
and semantic ranking results, not end-to-end accuracy or a latency benchmark.

## Offline distribution

The compiled demo was packaged with a standard-library Python localhost
launcher, unpacked separately, and served without the local inference backend.
Seven HTML, caption, PDF, packet, validation, and license resources returned
HTTP 200 with byte-identical content; captions and PDF used the expected MIME
types. The API endpoint correctly remained absent. This supplements static
reference checks and does not replace the unavailable visual browser review.

## Expanded-library full engine

The unchanged engine recovered all four selected positive sources and rejected
both unrelated Sintel negatives across the same 57-source library: **6/6 correct
decisions**. The plan, query hashes, report hashes, and individual runtimes
(106–284 seconds) are in `public/validation/verification-scale.json`. This is a
small smoke test with reused queries, not a new independent accuracy estimate.
The summary links the exact retrieval experiment by SHA-256.

## Downloaded-release acceptance

The published v0.1.0 offline ZIP was downloaded from GitHub, its release digest
verified, unpacked separately, and launched without the inference backend.
All 89 selected pages, source/query media, evidence reports, images, and handoff
resources returned bytes identical to the archive. The 29 checksummed files
inside the separately downloaded submission kit also verified. The v0.1.1
interface adjusts supporting-text contrast and explains nearest-neighbor search
limits; the matching engine and benchmark records are unchanged.

Static palette calculations improved page-introduction text from 3.09:1 to
4.65:1 against its declared background and the model chip from 3.63:1 to 5.18:1.
These targeted calculations do not establish overall WCAG conformance or
replace browser-based visual and contrast evaluation.

## Final operational and mixed-edit review

A live queue accepted two queries, rejected a third with HTTP 429, recovered
the laboratory for the first job, and returned no source for the unrelated
second job. Both original files and all twelve exported evidence-image hashes
verified independently. Both completed jobs were recovered from disk after
restarting into v0.1.1. Eighty health requests remained responsive while jobs
ran; these observations are not a controlled latency benchmark.

Six mixed-edit diagnostics and twelve qualitative semantic searches are
reported separately in [EXTENDED_VALIDATION.md](EXTENDED_VALIDATION.md).
The supplementary release archive preserves inputs, scripts, measured reports,
and all retrieved frames, including the Spanish query's relevance failure and
nearest candidates for absent concepts. These are not added to the headline
40-case evaluation.
