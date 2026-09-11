"""Roboflow Inference engine adapter (the sample's headline capability).

The `inference` package is the detection engine on the critical path — it is NOT
substituted with a bare YOLO/ultralytics call. It is confined to this repo module
and imported lazily so the API (and the credential-free test suite) boots without
the heavy ML closure installed; installing it is gated behind
`services/api/requirements-ml.txt`.

Device selection is runtime auto-detect: first available of CUDA -> CPU. `inference`
runs on onnxruntime, which has no first-class Apple-MPS execution provider, so on
Apple Silicon this runs on CPU (we never claim MPS and never hard-require a GPU).
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from app.types.detections import Prediction

logger = logging.getLogger(__name__)


class EngineUnavailableError(RuntimeError):
    """Raised when the `inference` engine (or a model) cannot be loaded.

    Callers turn this into a persisted `failed` run with an actionable message,
    so a missing ML stack never surfaces as a 500.
    """


def detect_device() -> str:
    """Return 'cuda' when an NVIDIA GPU execution provider is present, else 'cpu'.

    onnxruntime exposes the available providers; CUDA is picked when present.
    There is no Apple-MPS provider, so Apple Silicon resolves to 'cpu'.
    """
    try:
        import onnxruntime as ort

        if "CUDAExecutionProvider" in ort.get_available_providers():
            return "cuda"
    except Exception as e:
        logger.info("Device probe fell back to CPU: %s", e)
    return "cpu"


@lru_cache(maxsize=4)
def _load_model(model_alias: str, api_key: str | None) -> Any:
    """Load and cache a Roboflow Inference model. Lazy import keeps boot light."""
    try:
        from inference import get_model
    except ImportError as e:  # engine not installed on this interpreter
        raise EngineUnavailableError(
            "Roboflow Inference (`inference`) is not installed. Install "
            "services/api/requirements-ml.txt on a supported platform "
            "(CPU or CUDA; onnxruntime has no Apple-MPS path)."
        ) from e
    try:
        # api_key is OPTIONAL: only some builds fetch pretrained weights from the
        # Roboflow hub on first load. Pass it when present; None otherwise.
        return get_model(model_id=model_alias, api_key=api_key or None)
    except Exception as e:
        raise EngineUnavailableError(
            f"Could not load Roboflow Inference model '{model_alias}': {e}. "
            "If the installed build needs a free key to download weights, set "
            "ROBOFLOW_API_KEY (https://app.roboflow.com/settings/api)."
        ) from e


def warm_model(model_alias: str, api_key: str | None) -> None:
    """Load the model once up front so the first frame doesn't pay for it."""
    _load_model(model_alias, api_key)


def _coerce_predictions(result: Any) -> list[Any]:
    """Pull the per-object prediction list out of an `inference` response.

    Handles both the object response (`.predictions`) and the older list/dict
    shapes, so a minor `inference` version bump doesn't break parsing.
    """
    if isinstance(result, list):
        result = result[0] if result else None
    if result is None:
        return []
    preds = getattr(result, "predictions", None)
    if preds is None and isinstance(result, dict):
        preds = result.get("predictions")
    return list(preds or [])


def _read(pred: Any, *names: str) -> Any:
    for name in names:
        if isinstance(pred, dict):
            if name in pred:
                return pred[name]
        elif hasattr(pred, name):
            return getattr(pred, name)
    return None


def run_detection(
    frame_bgr: Any,
    model_alias: str,
    confidence: float,
    api_key: str | None = None,
) -> list[Prediction]:
    """Run detection on one decoded frame and return typed predictions.

    Roboflow returns center-based boxes; we convert to top-left origin so the
    stored prediction JSON overlays cleanly on the frame image in the browser.
    """
    model = _load_model(model_alias, api_key)
    try:
        result = model.infer(frame_bgr, confidence=confidence)
    except TypeError:
        # Some builds don't accept a confidence kwarg on infer(); filter below.
        result = model.infer(frame_bgr)

    predictions: list[Prediction] = []
    for pred in _coerce_predictions(result):
        conf = float(_read(pred, "confidence") or 0.0)
        if conf < confidence:
            continue
        cx = float(_read(pred, "x") or 0.0)
        cy = float(_read(pred, "y") or 0.0)
        w = float(_read(pred, "width") or 0.0)
        h = float(_read(pred, "height") or 0.0)
        class_name = _read(pred, "class_name", "class") or "object"
        predictions.append(
            Prediction(
                class_name=str(class_name),
                confidence=conf,
                x=max(cx - w / 2, 0.0),
                y=max(cy - h / 2, 0.0),
                width=w,
                height=h,
            )
        )
    return predictions
