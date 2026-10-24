# Third-party notices and provenance

Traceback's original application code is licensed under MIT. That license does
not change the licenses or ownership of the following third-party materials.

## Qwen model and inference wrapper

- Model: [Qwen/Qwen3-VL-Embedding-2B](https://huggingface.co/Qwen/Qwen3-VL-Embedding-2B), Apache 2.0.
- Pinned model revision: `9f2f7e710d6d81056aa5c0a4f04764fec6bb7bda`.
- `vendor/qwen3_vl_embedding.py` is the upstream inference wrapper from
  [QwenLM/Qwen3-VL-Embedding](https://github.com/QwenLM/Qwen3-VL-Embedding/blob/main/src/models/qwen3_vl_embedding.py).
- Its Apache license is included as `vendor/QWEN-LICENSE`.
- Model weights are downloaded separately to the user's Hugging Face cache,
  never bundled in the application or repository.
- The model repository was first created January 7, 2026; the technical report
  was published in January 2026. This is the **embedding model**, not a claim
  that the older Qwen3-VL base model was released in 2026.

## Demo footage

**Tears of Steel (2012): (CC) Blender Foundation | mango.blender.org.**

Licensed under [Creative Commons Attribution 3.0](https://creativecommons.org/licenses/by/3.0/).
[Original licensing statement](https://mango.blender.org/sharing/).
Original download: https://download.blender.org/demo/movies/ToS/tears_of_steel_720p.mov

`public/media/bridge.mp4`, `laboratory.mp4`, `observatory.mp4`, and
`machines.mp4` are shortened, resized, muted excerpts. The corresponding
thumbnails, evidence frames, and semantic retrieval frames are derived from
those excerpts. Edited queries additionally use cropping, color changes,
compression, text overlays, reflection, and playback speed changes.
The exact source offsets and transformations are recorded in
`public/manifest.json` and `scripts/prepare_media.py`.

**Sintel trailer (2010): (CC) Blender Foundation | durian.blender.org.**

Licensed under [Creative Commons Attribution 3.0](https://creativecommons.org/licenses/by/3.0/).
[Original licensing statement](https://durian.blender.org/sharing/).
Original download: https://download.blender.org/durian/trailer/sintel_trailer-480p.mp4

`public/media/query-unrelated.mp4` is a shortened, muted, re-encoded excerpt
used as an unrelated negative example. Benchmark-only derivatives are not
included in the public application.

No Blender logos or sponsor trademarks are used as Traceback branding. Source
film frames may depict their original creative content. Inclusion does not
imply endorsement by Blender, Qwen, Google, Twinly, Vobile, or the hackathon.

## Dependencies and fonts

React, Vite, TypeScript, Lucide, FastAPI, OpenCV, PyTorch, Transformers, and other
dependencies retain their respective licenses. Package lockfiles record the
actual dependency versions. DM Sans and Manrope are distributed through Google
Fonts under the SIL Open Font License. They are bundled locally in `public/fonts/`
with their license files; system sans-serif fallbacks are provided.

## AI-assisted development

This project was developed with Codex during the Gator Hack V hacking period.
The model wrapper, frameworks, and media above are pre-existing permitted
dependencies; the Traceback application code was created for this project.
Team members should accurately disclose their own contributions in the final
submission and confirm any additional organizer guidance on AI assistance.
