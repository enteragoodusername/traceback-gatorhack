# Traceback build plan

Started 2026-10-24 03:04 ET. Requested work window: four hours, through approximately 07:04 ET.

## Product

A provenance workbench for independent filmmakers, newsrooms, and media archivists. Given an edited clip, retrieve candidate source moments with Qwen3-VL-Embedding, verify them using geometric feature matching and temporal consistency, and export a reproducible evidence packet. Similarity is never presented as proof of ownership or infringement.

The demo uses attributed, openly licensed footage with deliberate crop, speed, color and overlay transformations. The application must work with new inputs, not just an animation of canned results. Prerecorded model outputs are marked and accompanied by their derivation.

## Competition evidence

- Official released challenge: https://ufgatorhack.com/data/challenge.json — technology, dataset, or discovery first public within the preceding 12 months, central to the project.
- Qwen3-VL-Embedding technical report: https://arxiv.org/abs/2601.04720 (January 2026). Model: https://huggingface.co/Qwen/Qwen3-VL-Embedding-2B. Distinct from the older Qwen3-VL base model.
- Gemini 3 release: https://blog.google/products-and-platforms/products/gemini/gemini-3/ (November 18, 2025). Optional evidence narration grounded in measured results.
- Rules: https://gatorhack2026.devpost.com/rules. Team of 2–5 registered students, at least two UF departments; in-person attendance; fresh event code; finalist representative on Monday October 26 at 10:15 ET.
- Submission: https://gatorhack2026.devpost.com/ — Sunday October 25, 17:00 ET. Public repository, at most 3-minute demo or slides, description, full roster, sponsor selections.
- Awards: https://ufgatorhack.com/prizes.html. Overall first place $2,000; Vobile amount unspecified; Gemini swag; open-source $25 gift card per member. Twinly's described awards are usage credit and subscriptions, despite Devpost's cash label; do not count as cash.

## Delivery sequence

1. Verify new model can run locally; build real media fixtures and license manifest.
2. Implement retrieval, visual verification, temporal alignment, benchmarks and API.
3. Build polished responsive workbench: source library, query upload, evidence comparison, timeline and export.
4. Add grounded Gemini explanation and a documented Twinly evidence-review integration if feasible. Do not claim live sponsor integration without a successful live run.
5. Test adversarial negatives, transformed positives, upload limits, and browser workflows. Record measured results.
6. Prepare reproducible installation, public-ready MIT source, demo script, pitch, and submission text. Deploy a clearly labeled interactive hosted demo through Sites.

## Success criteria

- Actual source localization from unseen transformed test clips.
- Honest rejection of unrelated clips and explicit uncertainty.
- Semantic retrieval uses genuine January 2026 model embeddings.
- No secrets or large model weights in source archives.
- No fabricated traction, accuracy, API calls, or award eligibility.
- Reliable judge demo with visible data provenance and downloadable evidence.
