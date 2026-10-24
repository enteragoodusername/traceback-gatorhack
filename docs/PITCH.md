# Traceback — show a clip, find your next reference

Creators often remember how a video looks, but not the words that will find it. Traceback turns a short clip into a practical internet video search.

Drop one video. The app describes several moments locally, searches YouTube and Internet Archive live, and visually ranks the returned thumbnails with Qwen3-VL-Embedding-2B. Compare candidates beside your clip, watch their original pages, and save a shortlist of links.

The demonstration should use a fresh video chosen by the presenter or judge. Explain that CPU processing takes a few minutes. Show the generated search text and provider status, then compare two candidates and save one. If a scene is misdescribed, correct the optional description to demonstrate refinement without another upload.

The technical distinction is retrieval plus visual reranking: the system does not merely turn a filename into a query, and it does not display prepared answers. The January 2026 Qwen model compares uploaded-frame pixels with newly retrieved thumbnail pixels. BLIP provides local descriptions; internet services provide live candidates.

Be precise about scope: these are similar-video leads, not verified originals or ownership determinations. The raw upload stays local. YouTube's public-page adapter may become unavailable; the app reports that instead of inserting a saved result.
