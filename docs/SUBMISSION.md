# Current project description — Traceback v0.2

**Tagline:** Upload one clip. Find similar videos online.

Traceback is a practical video discovery tool for people who have a visual reference but do not know what to search for. One uploaded clip starts the complete workflow: local scene descriptions, live YouTube and Internet Archive retrieval, and thumbnail reranking with Qwen3-VL-Embedding-2B. Users can compare candidate videos with their upload, watch them at the source, refine the search description, and export saved links.

The production interface ships no prerecorded examples, test videos, stored answers, or report dashboards. It requires the local Python engine; the static hosted interface explains how to start it. The original upload remains on the user's computer, while generated search descriptions go online.

Built with React, TypeScript, FastAPI, OpenCV/FFmpeg, local BLIP captioning, and pinned Qwen3-VL-Embedding-2B inference. No paid API key is required for the main workflow.

The system compares thumbnails rather than verifying full candidate videos. It does not establish copyright, original publication, or permission to reuse. Search relevance depends on scene descriptions, provider coverage, and thumbnails. Provider failures are explicit.

The previous v0.1 PDF, pitch video, and provenance benchmark numbers describe an earlier product and should not be submitted as if they describe this version. Team details, eligibility, attendance and the final video-host submission remain the entrant's responsibility.
