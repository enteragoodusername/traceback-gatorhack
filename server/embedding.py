"""Pinned Qwen3-VL-Embedding inference with a lazy, serialized CPU model."""

from pathlib import Path
import os
import sys
import threading
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MODEL_ID = "Qwen/Qwen3-VL-Embedding-2B"
MODEL_REVISION = "9f2f7e710d6d81056aa5c0a4f04764fec6bb7bda"
_model = None
_lock = threading.Lock()


def available():
    return os.getenv("TRACEBACK_ENABLE_MODEL", "1") == "1"


def embed(items: list[dict]) -> np.ndarray:
    global _model
    if not available():
        raise RuntimeError("Local semantic model is disabled.")
    with _lock:
        import torch

        torch.set_num_threads(int(os.getenv("TRACEBACK_MODEL_THREADS", "4")))
        if _model is None:
            sys.path.insert(0, str(ROOT / "vendor"))
            from qwen3_vl_embedding import Qwen3VLEmbedder

            _model = Qwen3VLEmbedder(
                MODEL_ID,
                revision=MODEL_REVISION,
                max_pixels=256 * 256,
                max_length=1024,
                torch_dtype=torch.bfloat16,
                attn_implementation="sdpa",
            )
        chunks = []
        for item in items:
            if "image" in item and isinstance(item["image"], np.ndarray):
                item = {**item, "image": Image.fromarray(item["image"][:, :, ::-1])}
            with torch.inference_mode():
                v = _model.process([item]).float().cpu().numpy()
            if not np.isfinite(v).all():
                raise RuntimeError("Embedding contained invalid values.")
            chunks.append(v)
        return np.concatenate(chunks, axis=0)
