"""Detection-run worker: decode -> detect (Roboflow Inference) -> archive to B2.

Runs on a background thread started by `service.cameras.start_run`. It streams
sampled frames through the local engine and, for every frame whose detections
clear the camera's confidence threshold, writes the JPEG + prediction JSON, then
a Parquet summary for the whole run. Progress is pushed to the live registry as
it goes; the record is persisted to B2 in `finally`, whatever the outcome.
"""

from __future__ import annotations

import contextlib
import logging
import os
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.config import settings
from app.repo import archive
from app.repo import cameras as camera_repo
from app.repo.b2_object import get_object_bytes
from app.repo.inference_engine import (
    EngineUnavailableError,
    detect_device,
    run_detection,
    warm_model,
)
from app.repo.video import (
    VideoUnavailableError,
    encode_jpeg,
    frame_dimensions,
    iter_sampled_frames,
)
from app.types.cameras import Camera
from app.types.detections import PredictionDocument
from app.types.runs import RunRecord

logger = logging.getLogger(__name__)


def _repo_root() -> Path:
    # service/capture.py -> service -> app -> api -> services -> repo-root.
    parents = Path(__file__).resolve().parents
    return parents[4] if len(parents) > 4 else parents[2]


def _resolve_source(camera: Camera) -> tuple[str, str | None]:
    """Return (local_path, temp_path_to_clean).

    A "demo" camera reads the bundled CC-BY clip; an "upload" camera downloads
    its source object from B2 into a temp file. Raises VideoUnavailableError with
    an actionable message when the source is missing.
    """
    if camera.source == "upload":
        if not camera.source_key:
            raise VideoUnavailableError(
                "This camera's source is 'upload' but no source clip was set. "
                "Upload a video on /upload and pick it as the source."
            )
        data = get_object_bytes(camera.source_key)
        suffix = Path(camera.source_key).suffix or ".mp4"
        fd, tmp = tempfile.mkstemp(prefix="rffa-src-", suffix=suffix)
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        return tmp, tmp

    path = Path(settings.demo_clip_path)
    if not path.is_absolute():
        path = _repo_root() / path
    if not path.exists():
        raise VideoUnavailableError(
            f"Bundled demo clip not found at '{path}'. Run scripts/fetch_demo_clip.sh "
            "to download the CC-BY open-movie clip, then start the run again."
        )
    return str(path), None


def _summary_row(camera_id: str, run_id: str, frame_index: int, captured_at: datetime,
                 frame_bytes: int, classes: list[str]) -> dict:
    return {
        "camera_id": camera_id,
        "run_id": run_id,
        "frame_index": frame_index,
        "captured_at": captured_at.isoformat(),
        "date": f"{captured_at:%Y-%m-%d}",
        "frame_bytes": frame_bytes,
        "detections": len(classes),
        "classes": classes,
    }


def execute_run(run: RunRecord, camera: Camera) -> None:
    """Execute one detection pass. Never raises — failures are recorded."""
    api_key = settings.roboflow_api_key or None
    temp_path: str | None = None
    try:
        run.status = "running"
        run.started_at = datetime.now(UTC)
        camera_repo.update_run(run)

        source_path, temp_path = _resolve_source(camera)
        run.device = detect_device()
        camera_repo.update_run(run)
        warm_model(camera.model_alias, api_key)

        summary_rows: list[dict] = []
        for frame in iter_sampled_frames(
            source_path, settings.frame_sample_stride, settings.max_frames_per_run
        ):
            run.frames_processed += 1
            preds = run_detection(
                frame.image_bgr, camera.model_alias, camera.confidence_threshold, api_key
            )
            if not preds:
                camera_repo.update_run(run)
                continue

            width, height = frame_dimensions(frame.image_bgr)
            captured_at = run.created_at + timedelta(seconds=frame.timestamp_seconds)
            fkey = archive.frame_key(camera.id, run.id, frame.index, captured_at)
            jpeg = encode_jpeg(frame.image_bgr, settings.jpeg_quality)
            archive.put_frame(fkey, jpeg)

            pkey = archive.prediction_key_for(fkey)
            archive.put_prediction(
                pkey,
                PredictionDocument(
                    camera_id=camera.id,
                    run_id=run.id,
                    frame_index=frame.index,
                    timestamp_seconds=frame.timestamp_seconds,
                    frame_width=width,
                    frame_height=height,
                    model_alias=camera.model_alias,
                    frame_key=fkey,
                    predictions=preds,
                ),
            )

            run.frames_flagged += 1
            run.detections_written += len(preds)
            run.bytes_written += len(jpeg)
            summary_rows.append(
                _summary_row(
                    camera.id, run.id, frame.index, captured_at, len(jpeg),
                    [p.class_name for p in preds],
                )
            )
            camera_repo.update_run(run)

        run.summary_key = archive.write_summary(camera.id, run.id, summary_rows)
        run.status = "done"
        run.finished_at = datetime.now(UTC)
        logger.info(
            "Run %s done: %d flagged / %d processed, %d detections, %d bytes on %s",
            run.id, run.frames_flagged, run.frames_processed,
            run.detections_written, run.bytes_written, run.device,
        )
    except (EngineUnavailableError, VideoUnavailableError) as e:
        run.status = "failed"
        run.error = str(e)
        run.finished_at = datetime.now(UTC)
        logger.warning("Run %s failed (unavailable): %s", run.id, e)
    except Exception as e:
        run.status = "failed"
        run.error = f"Detection run failed: {e}"
        run.finished_at = datetime.now(UTC)
        logger.exception("Run %s crashed", run.id)
    finally:
        if temp_path:
            with contextlib.suppress(OSError):
                os.unlink(temp_path)
        camera_repo.update_run(run)
        try:
            camera_repo.persist_run(run)
        except RuntimeError as e:
            logger.error("Could not persist run %s to B2: %s", run.id, e)
