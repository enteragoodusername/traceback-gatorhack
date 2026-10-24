# Traceback handoff

The project is built for the overall, Vobile, and open-source award paths.
It is a real local video-provenance application with a clearly labeled recorded
web demonstration. A Devpost entry has **not** been submitted.

## Open the project

- [Interactive demo](https://enteragoodusername.github.io/traceback-gatorhack/)
- [Public MIT repository](https://github.com/enteragoodusername/traceback-gatorhack)
- [Captioned 2:15 video](https://enteragoodusername.github.io/traceback-gatorhack/demo/)
- [One-page judge brief](https://enteragoodusername.github.io/traceback-gatorhack/downloads/traceback-brief.pdf)
- [Release assets](https://github.com/enteragoodusername/traceback-gatorhack/releases/latest)

The submission kit contains the MP4, captions, brief, evidence ZIP, matching
sample query, submission draft, pitch notes, notices, and validation records.
The supplementary diagnostics ZIP preserves mixed-edit, semantic-search, and
queue/restart observations, including failures.
The separate offline-demo ZIP contains the built interface and all recorded
examples. Extract it and run `python3 START_DEMO.py` (`python` on some Windows
installations), then open the printed localhost URL. It needs no model or Node
installation. New inference requires the full project.

## Run new analysis

In the project directory:

```bash
./start.sh
```

The working environment already has the dependencies, model cache, and source
index. A fresh machine should run `./setup.sh` first. Linux and Python 3.11 were
tested. The interface opens at `http://127.0.0.1:8000`.

Use **Source library** to index a new 2-60 second original, then **Trace a clip**
to analyze an edited query. The engine runs on the local CPU. Completed analyses
can be reopened after a refresh or server restart. Private local uploads and
indexes are ignored by Git.

## Present the strongest workflow

1. Trace **The cropped repost** and inspect two matching frame pairs.
2. Show **Two stories, one edit** for multiple source intervals.
3. Export a packet, then open **Verify a packet** and check it locally.
4. Compare the supplied sample query file with the packet's query hash.
5. Show the unrelated example and the published evaluation limits.

The hosted and offline demos use actual saved outputs, not live model calls.
Say this plainly. Start a local live run before speaking if you want to show
fresh inference during the presentation. Read [PITCH.md](PITCH.md) for the short
script and technical questions.

## Complete the event-specific submission

Use [SUBMISSION.md](SUBMISSION.md) as the draft. The remaining information is
personal and event-specific; it was not guessed or fabricated.

- Supply the actual registered 2-5 person team and real contributions. The
  [rules](https://gatorhack2026.devpost.com/rules) require an interdisciplinary
  team spanning at least two UF departments and in-person participation.
- The event accepts a demonstration video of at most three minutes or slides.
  For the prepared video, upload the MP4 to YouTube or Vimeo with judge-accessible
  settings and paste that URL into Devpost's video field. The direct MP4 URL is
  not accepted in that field. The PDF brief is available as a handout/attachment.
- Select the prize categories the team genuinely qualifies for. Gemini and
  Twinly clients are implemented, but no live sponsor API run was made without
  credentials. Their categories should not be claimed on the basis of mocks.
- Submit through [Devpost](https://gatorhack2026.devpost.com/) by **Sunday,
  October 25, 2026, 5:00 PM Eastern**.
- At least one eligible team member must attend the **Monday, October 26,
  10:15 AM Eastern finals at the Reitz Union** to remain eligible for an award.

The application was created with substantial autonomous Codex assistance during
the hacking window. Describe student contributions accurately.

## Verification and limits

33 Python tests and 32 interface tests pass, along with production compilation,
public-artifact checks, and the independent packet verifier. Actual local
inference, source ingestion, semantic search, and restart recovery were exercised.
A fresh checkout reproduced one full pipeline result and its frame hashes.

The four-source controlled evaluation recovered 32/32 positive edits and rejected
8/8 negatives. An additional-film test recovered 7/8 positives and rejected 2/2
negatives. In the 57-source retrieval test, 30/32 existing queries ranked first
and 32/32 were within the top five. A six-case full-engine check in the same
57-source library recovered four positives and rejected both negatives. These are small synthetic experiments,
not production accuracy estimates; the expanded test reuses queries and has
unequal reference lengths. Full records and limitations are in
[TEST_REPORT.md](TEST_REPORT.md).

No interactive browser automation surface was available. A native Sites
screenshot of the earlier desktop landing view was inspected; mobile layout and
interactive visual QA remain unverified. DOM accessibility, HTTP workflows, and
static references were checked; the PDF and technical figures were visually inspected. The project does not establish
ownership, infringement, first publication, or authenticated provenance.
