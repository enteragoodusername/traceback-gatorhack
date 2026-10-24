# Demo video provenance

The demo is a narrated pipeline walkthrough assembled from actual input videos,
retrieved source frames, measured correspondences, and report fields. It is
not a browser screen recording and does not simulate live inference.

`docs/DEMO_NARRATION.json` contains the spoken script. `scripts/build_narration.py`
uses the optional Piper TTS build tool and the generic `en_US-ljspeech-medium`
voice. The narration is synthetic; it is not a team member's voice. The voice's
[model card](https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/ljspeech/medium/MODEL_CARD)
identifies its training dataset as the public-domain LJ Speech dataset.
The [Piper runtime](https://github.com/OHF-Voice/piper1-gpl) is GPL-3.0 and is not
included in the application. The voice weights are downloaded separately and
excluded from the repository.

Film footage and derived evidence images retain their CC BY 3.0 attribution:
Tears of Steel — (CC) Blender Foundation | mango.blender.org;
Sintel trailer — (CC) Blender Foundation | durian.blender.org.
The video uses trimmed, muted, resized, and deliberately transformed excerpts.

The video is designed to remain under the competition's three-minute limit.
The interactive hosted demo and local application are the best places to inspect
individual evidence frames and export the full packet.

## Rebuild

```bash
uv pip install --python .venv/bin/python -r requirements-demo.txt
.venv/bin/python -m piper.download_voices --data-dir artifacts/narration en_US-ljspeech-medium
.venv/bin/python scripts/build_narration.py
.venv/bin/python scripts/build_video.py
```

The measured reports and evaluation must already exist. The output is
`artifacts/traceback-demo.mp4`, with SRT and WebVTT captions. Caption timing is
approximated at sentence level from the narration lengths. Film audio is muted;
only the synthetic narration is included. Opening and negative examples play
the actual query videos; evidence frames and semantic retrieval examples use
the exact measured images.
