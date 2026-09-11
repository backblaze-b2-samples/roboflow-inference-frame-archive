"""Source-clip decoding and JPEG encoding (opencv-python-headless).

Confined to the repo layer and lazy-imported, so the API boots without the ML/CV
closure. A run samples one frame every `stride` decoded frames and stops after
`max_frames`, so a CPU detection pass over the demo clip stays bounded.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


class VideoUnavailableError(RuntimeError):
    """Raised when opencv is missing or the clip cannot be opened/decoded."""


@dataclass
class DecodedFrame:
    index: int
    timestamp_seconds: float
    image_bgr: Any  # numpy ndarray (H, W, 3), BGR — kept untyped to avoid a numpy import here


def _cv2() -> Any:
    try:
        import cv2
    except ImportError as e:
        raise VideoUnavailableError(
            "opencv-python-headless is not installed. Install "
            "services/api/requirements-ml.txt to run detection passes."
        ) from e
    return cv2


def iter_sampled_frames(
    path: str, stride: int, max_frames: int
) -> Iterator[DecodedFrame]:
    """Yield up to `max_frames` frames, one every `stride` decoded frames.

    Timestamps come from the source FPS so archived frames carry a real
    capture offset. Raises VideoUnavailableError if the clip can't be opened.
    """
    cv2 = _cv2()
    capture = cv2.VideoCapture(path)
    if not capture.isOpened():
        raise VideoUnavailableError(
            f"Could not open source clip at '{path}'. For a bundled-demo camera, "
            "run scripts/fetch_demo_clip.sh first."
        )
    fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
    stride = max(int(stride), 1)
    try:
        decoded = 0
        emitted = 0
        while emitted < max_frames:
            ok, frame = capture.read()
            if not ok:
                break
            if decoded % stride == 0:
                yield DecodedFrame(
                    index=decoded,
                    timestamp_seconds=round(decoded / fps, 3),
                    image_bgr=frame,
                )
                emitted += 1
            decoded += 1
    finally:
        capture.release()


def frame_dimensions(image_bgr: Any) -> tuple[int, int]:
    """Return (width, height) of a decoded BGR frame."""
    height, width = image_bgr.shape[:2]
    return int(width), int(height)


def encode_jpeg(image_bgr: Any, quality: int) -> bytes:
    """Encode a decoded BGR frame to JPEG bytes. Raises on encode failure."""
    cv2 = _cv2()
    ok, buffer = cv2.imencode(
        ".jpg", image_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), int(quality)]
    )
    if not ok:
        raise VideoUnavailableError("Failed to JPEG-encode a decoded frame.")
    return buffer.tobytes()
