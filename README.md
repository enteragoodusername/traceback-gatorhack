# Traceback — find similar videos online

Drop **one video file** into Traceback. It describes sampled scenes on your computer, searches **YouTube and Internet Archive live**, and uses **Qwen3-VL-Embedding-2B** to compare the returned thumbnails with your clip. Watch candidates, compare them beside your upload, and save or export a shortlist of links.

**The application has no prerecorded examples or preloaded search results.** No source library setup, query text, account, or paid API key is required for the primary workflow.

## Run the working app

```bash
./setup.sh   # first-time dependency installation and interface build
./start.sh
```

Open **http://127.0.0.1:8000**, then drop a video. Clips up to 60 seconds start searching automatically. Longer videos open a clip selector: move the 60-second window, preview it, then choose **Search this clip**. Start/end fields also let you select a shorter section.

Requirements: Linux, Python 3.11+, Node.js 22+, FFmpeg, internet access, and enough RAM for the local models (16 GB recommended; tested on a 38 GB CPU machine). The first search downloads the pinned BLIP caption model (~1 GB) and Qwen embedding model (~4.4 GB) if they are not cached. Subsequent runs reuse those weights, not previous search answers. CPU searches can take a few minutes.

Input: MP4, MOV, WebM, MKV or M4V; at least 2 seconds; up to 1 GB and 4K. Choose a 2–60 second section of longer recordings directly in the app. If your browser cannot preview the format, start/end controls still work.

The [hosted interface](https://enteragoodusername.github.io/traceback-gatorhack/) explains how to open the local app. GitHub Pages and the private Sites copy host static files; they do not run the Python models. They show no substitute demo when the engine is unavailable.

## What you can do

- Upload or drop one video. Short clips search automatically; longer videos open an in-app clip selector.
- Preview your upload and jump to its sampled moments.
- Filter actual search candidates by provider.
- Compare your clip with an embedded candidate, or open its original video page.
- Save candidates in this browser, copy their links, and export a plain-text shortlist.
- Optionally correct the generated description and search again without uploading again.
- Reopen your most recent actual search after a page refresh or server restart.

## How search works

1. FFmpeg/OpenCV validate the upload. For longer videos, FFmpeg extracts only the user-selected interval into a browser-compatible MP4 before any scene sampling, captions or search. Three moments are sampled from the resulting clip.
2. Local BLIP captions the frames. Up to two distinct scene descriptions become search queries.
3. The server reads YouTube's public search results and Internet Archive's live video search API. It interleaves multi-scene results, deduplicates links, and limits candidates to eight YouTube videos and four Archive items.
4. It downloads bounded thumbnails from service-controlled image hosts. Local Qwen embeddings compare these images with the sampled query frames.
5. The UI shows the actual search text, provider status, watch links, and optional comparison details.

A ranked thumbnail is a **similar-video lead**, not proof of the same footage, original publication, ownership, or permission to reuse. A low-quality or misleading thumbnail can affect relevance. BLIP can misdescribe scenes; optional refinement lets you correct its words. We do not download or geometrically verify complete candidate videos in this workflow.

YouTube search is a public-page adapter, not an official YouTube API integration; page changes, consent gates, or rate limits can make it unavailable. Internet Archive is a separate live source. Failures and missing visual scores are shown explicitly. No captcha bypass, account cookies, fabricated results, or saved-answer fallback is used.

## Privacy and storage

The uploaded video and sampled frames stay in `data/uploads/` on this computer. Generated scene descriptions (or your optional refined description) are sent to search services. Candidate thumbnails are downloaded for comparison. Opening a video or its embedded player connects your browser to that provider.

Uploads, unfinished clip selections and completed user searches persist locally so they can be reopened. Long-video searches retain the original file plus the extracted clip; refining a description reuses that extracted section. They are not added to an indexed source library automatically. Saved links are stored in browser local storage. To remove local video data, stop the app and delete the relevant job directories in `data/uploads/`; the app's displayed job ID is available in its `/api/jobs/…` request. Keep any files you want to retain before deleting local data.

The server binds to localhost. It rejects mutations from unrelated browser origins, validates file size/duration, caps active jobs at two, and restricts image fetches to service-controlled hosts with byte and redirect limits.

## Development and verification

```bash
npm test
npm run build
.venv/bin/python -m pytest -q
python3 scripts/check_internet_build.py dist
```

For frontend development, `npm run dev` proxies `/api` to the local server on port 8000. Build before restarting the production-style local app after interface changes.

- UI: `src/App.tsx`, `src/TrimClip.tsx`, `src/internet.ts`, `src/styles.css`.
- Local segment extraction: `server/clips.py`.
- Live search: `server/internet.py`.
- Upload queue, recovery and API: `server/app.py`.
- Models: pinned BLIP revision `82a37760796d32b1411fe092ab5d4e227313294b`; pinned Qwen revision in `server/embedding.py`.
- Only `web-assets/` is copied into the production build. The build audit rejects bundled videos, reports, demo ZIPs and prerecorded-answer paths.

The previous v0.1 local-provenance experiment, media fixtures, verification engine and measurement artifacts remain in Git history and research/test files. They are not search inputs or displayed results in this application. Historical accuracy claims describe that earlier verifier, not internet-video discovery. The old PDF, pitch video and v0.1 release bundles are historical artifacts.

MIT licensed application. See `NOTICE.md` and `web-assets/THIRD_PARTY_LICENSES.txt` and the bundled font notices for dependency/model/media licensing.
