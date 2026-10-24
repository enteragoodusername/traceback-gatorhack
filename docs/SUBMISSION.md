# Devpost submission draft

## Title
Traceback — find the source behind an edited video

## Tagline
A local video provenance workbench that turns visual similarity into inspectable source evidence.

## Inspiration
A cropped, recolored, sped-up clip can look very different from its source. Filmmakers, newsroom researchers, and archive teams need more than a plausible AI answer: they need to inspect the exact frames and understand what a match does and does not establish. Traceback makes that investigation visible.

## What it does
Give Traceback an edited clip and an indexed library. It retrieves candidate sources, verifies shared imagery, estimates the source interval and playback change, and shows corresponding visual features. A downloadable evidence packet preserves the measured results, inspected frames, model revision, and content hashes. Natural-language search finds source moments from descriptions rather than filenames.

The local application accepts new query videos and new sources. The hosted demonstration transparently uses recorded outputs from real model runs, so judges can inspect evidence immediately without downloading a large model.

## How it was built
Qwen3-VL-Embedding-2B encodes source pixels, query pixels, and search text into a shared representation. It is a January 2026 release and is central to retrieval and semantic search. The model is pinned to an exact revision and runs on a CPU.

Retrieval alone does not establish a source match. Traceback verifies unique ORB feature correspondences using RANSAC homographies, checks spatial coverage and aligned appearance, then fits a consistent source-time mapping across multiple query frames. A denser sampling pass refines the timing. Ambiguous or weak speed estimates remain labeled as uncertain.

React and TypeScript provide the evidence workbench. FastAPI coordinates local jobs, FFmpeg prepares media, and OpenCV performs visual verification. Optional Gemini and Twinly clients explain or review measured facts; these require user-provided credentials and are not part of the demonstrated core result.

## What makes it fresh
The [released challenge](https://ufgatorhack.com/data/challenge.json) calls for a recent technology at the center of the project. [Qwen3-VL-Embedding](https://huggingface.co/Qwen/Qwen3-VL-Embedding-2B) was made public in January 2026, within the event's preceding 12 months. This is the dedicated embedding model described in the [January technical report](https://arxiv.org/abs/2601.04720), not the older Qwen3-VL base model. Source titles and captions are not embedded as a shortcut; the retrieval inputs are actual pixels.

## Challenges and lessons
Coarse frame sampling can recover the correct scene while producing a misleading playback estimate. Development tests exposed this failure. We added denser source sampling, multiple timing hypotheses, one vote per query frame, and explicit uncertainty. Shared visual elements also need more than a raw feature count: spatial coverage and aligned appearance help reject accidental matches.

A useful evidence tool must separate shared imagery from ownership. Traceback never infers infringement, intent, or first publication from a visual match.

## What works today
- Real local multimodal inference and free-text source search.
- New source ingestion and edited-query upload.
- Geometric evidence, temporal alignment, and uncertainty indicators.
- Downloadable evidence packets with independent CLI and in-browser checksum
  verification and frame-pair review.
- A published controlled evaluation with every case, including failures.
- A responsive hosted demonstration with explicit recorded-run labels.

Use the exact current figures in `public/evaluation.json` when presenting results. They describe controlled synthetic edits of four licensed source excerpts, not production or internet-wide accuracy.

## What's next
Evaluate on a larger, independently annotated corpus; add shot-aware alignment for nonlinear edits; measure retrieval recall as the source library grows; and compare alternative verification methods under severe occlusion. A newsroom or archive pilot would test whether the evidence view reduces investigation time. No pilot, customer adoption, or time savings is claimed today.

## Built with
Qwen3-VL-Embedding-2B, PyTorch, Transformers, OpenCV, FFmpeg, FastAPI, Python, React, TypeScript, Vite, fflate. Optional clients: Google Gemini API and Twinly API.

## Project links

- Public repository: https://github.com/enteragoodusername/traceback-gatorhack
- Interactive recorded demo: https://enteragoodusername.github.io/traceback-gatorhack/
- Captioned 2:15 walkthrough: https://enteragoodusername.github.io/traceback-gatorhack/demo/
- Direct MP4: https://enteragoodusername.github.io/traceback-gatorhack/demo/traceback-demo.mp4
- Sample evidence packet: https://enteragoodusername.github.io/traceback-gatorhack/downloads/traceback-evidence.zip

## Submission operator checklist
The project is prepared, but this file is not a submitted Devpost entry.

- Supply the real registered roster and actual contributions. Do not invent team members or affiliations.
- Confirm the team's in-person eligibility and required interdisciplinary composition against the [rules](https://gatorhack2026.devpost.com/rules).
- Attach the public GitHub repository. Upload `public/demo/traceback-demo.mp4`
  to YouTube or Vimeo with settings that let judges view it, then use that hosted
  URL in Devpost's video field. The supplied MP4 and walkthrough page are ready,
  but [Devpost requires a supported video host](https://help.devpost.com/article/85-uploading-a-demo-video);
  a direct GitHub Pages MP4 URL is not accepted in that field.
- Select overall, Vobile, and open-source consideration. Select API-specific categories only after a genuine successful integration demonstration and organizer eligibility confirmation.
- Submit through [Devpost](https://gatorhack2026.devpost.com/) by **Sunday, October 25, 2026, 5:00 PM Eastern**.
- Arrange an eligible teammate's presence at the **Monday, October 26, 10:15 AM Eastern finals at the Reitz Union**; attendance is necessary to win.

## Development disclosure
The application was created during the hacking window with substantial autonomous Codex assistance. Existing libraries, the upstream model wrapper, fonts, and licensed films are credited in `NOTICE.md`. The submitting students must describe their own contributions accurately and follow any additional organizer guidance.
