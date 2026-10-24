# Current handoff — live internet video search (v0.2)

The working application is at **http://127.0.0.1:8000** while `./start.sh` is running. Choose or drop one video: it automatically describes scenes, searches YouTube and Internet Archive, and ranks real thumbnails against the upload.

No recorded case selection or source library setup is part of this workflow. The hosted URL is a static interface with local-engine instructions, not a cloud inference service.

## Main interactions

Upload → live progress → similar-video cards. Use Compare to watch side by side, filter by provider, save candidates, copy links, and export the shortlist. Description refinement is optional; it reuses the existing upload. Reopening a search restores only a real user job, clearly timestamped.

## Operational notes

Run `./setup.sh` once and `./start.sh` afterward. FFmpeg and Python 3.11+/Node 22+ are required. The first run downloads missing pinned caption/ranking model weights (~5.4 GB together); CPU inference may take a few minutes. Models are already cached on this workspace machine.

Only descriptions go to online search services. The raw upload stays local. Opening a candidate player connects to the provider. Search availability and ranking limitations are shown in the interface. Internet search never falls back to a stored example.

`data/uploads/<job-id>/search-result.json` stores a completed internet search, and `web/` holds its sampled frames and downloaded thumbnails. Browser local storage holds the last actual search ID and saved video links. The old `traceback:last-analysis` key is not used by this interface.

The v0.1 PDF and video are out of date for this version. Refer to README and the current interface for the current product behavior. Previous benchmark numbers do not measure this internet search pipeline.
