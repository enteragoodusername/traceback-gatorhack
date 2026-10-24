# Traceback pitch and judge demonstration

## Opening: 20 seconds
“This is the same footage: cropped vertically, recolored, captioned, and played faster. A filename search cannot reconnect it. A plausible AI answer is not enough. Traceback finds the indexed source and lets you inspect the evidence.”

Show the cropped query immediately. Keep the problem concrete: a filmmaker or researcher tracing a clip within an archive they control.

## Demonstration: 60 seconds
1. Select **The cropped repost**, then **Find the source**. In the hosted demo, explicitly say this is a saved result from an actual pipeline run. For a live demonstration, start the local analysis before the introduction so the CPU can work while you speak.
2. Show the recovered source. Select two frame pairs. Point to the corresponding green features and the projected crop region.
3. Show the estimated source interval and playback change. Explain that timing has sampling uncertainty; the displayed range is not a calibrated probability.
4. Export the packet. Its JSON, inspected images, media hashes, pinned model revision, and engine fingerprint let another person review what was measured.
5. Select the unrelated example. Show that a clip outside this small library does not receive a forced match.

## Technical explanation: 35 seconds
“The new component is Qwen3-VL-Embedding, released in January 2026. It embeds pixels and text into the same retrieval space. That powers description-based source search and candidate ordering. Then geometry checks whether the images actually share content, and temporal alignment tests whether those correspondences form a coherent source interval. We separate retrieval, visual verification, and interpretation.”

For a technical judge: explain unique feature matches, RANSAC homography, spatial coverage, aligned appearance, multi-hypothesis temporal fitting, and the 4 fps refinement. Avoid claiming Qwen alone proves provenance.

## Evidence and close: 25 seconds
Open **Under the hood** and cite the current complete evaluation, with its scope. All cases remain visible. State one failure mode plainly: repeated static imagery or nonlinear edits can leave timing ambiguous.

“Traceback answers a narrow, useful question: which indexed source shares this imagery, and what can we inspect to support that answer? It runs locally, accepts new inputs, and is open source. A visual match is evidence of shared content, not a verdict on ownership.”

## Answers to likely questions

**Why use a new multimodal model instead of only feature matching?**
It enables semantic search without hand-authored tags and prioritizes candidate sources from actual pixels. In this four-source prototype all sources are still geometrically checked, so we do not claim a measured large-library speedup or retrieval ablation result. Scaling retrieval is future work.

**Is this searching the internet?**
No. It searches the source library you index. The bundled library is four licensed 40-second excerpts. Users can add their own 2–60 second sources locally.

**Can it prove who created a video?**
No. Identical imagery can exist in multiple copies. Rights metadata is supplied information. A match cannot establish ownership, lawful reuse, or earliest publication.

**Is the hosted site running the model?**
No. It displays actual saved model outputs with clear labels. The local Python service runs new inference, source indexing, and arbitrary semantic searches. The recorded mode keeps the judging experience immediate and reproducible.

**How do you know the evidence wasn't changed?**
Packet checksums detect accidental modifications. They are not signatures and do not authenticate the author. The source and query hashes identify the analyzed media, which can be rerun with the pinned model and engine.

**Did you really use sponsor APIs?**
Clients are implemented and tested with mocked transports. No live Gemini or Twinly success is claimed without configured credentials and an actual run. The core Qwen model was run locally.

**What is the business case?**
The initial user hypothesis is small media archives and research teams that need a clear audit trail. A paid local or private archive workflow is a possible direction, not validated revenue. The next validation step is observing actual investigators and measuring review time and missed matches.

**What was built during the event?**
The Traceback pipeline, interface, API, evaluation tooling, and handoff materials. Libraries, model wrapper, fonts, and films are credited pre-existing dependencies. Be candid about autonomous Codex assistance and each student's actual work.

## Demo recovery
- If inference is still running, use the recorded example and say so. Do not relabel a saved result as live.
- If internet access fails, `./start.sh` serves the built application on localhost and the bundled examples remain available. Download the model and build the index before arriving.
- If optional APIs fail, show the measured evidence; no sponsor explanation is needed for the core workflow.
- Keep the demo video locally available as a final fallback.
