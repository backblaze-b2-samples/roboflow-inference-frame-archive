"""Archive read models: the `/archive` gallery and the dashboard roll-up.

The gallery lists prediction JSON objects (optionally scoped to one camera),
reads a bounded page of them, and returns each flagged frame with a presigned
image URL and its boxes so the browser can overlay them. The dashboard metrics
aggregate the `summaries/` Parquet roll-ups (the aggregator -> dashboard path).
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict

from app.repo import archive
from app.repo import cameras as camera_repo
from app.types.detections import (
    ArchivedFrame,
    ArchiveMetrics,
    CameraFrameCount,
    ClassCount,
    DailyIngest,
    PredictionDocument,
)

logger = logging.getLogger(__name__)

# Upper bound on prediction JSONs read per gallery request, so a large archive
# never turns one page into thousands of GETs. The demo archive is far smaller.
_MAX_SCAN = 400


def _captured_at_from_key(frame_key: str) -> str:
    # frames/<camera>/YYYY-MM-DD/HH/<run>_<idx>.jpg
    parts = frame_key.split("/")
    if len(parts) >= 5:
        return f"{parts[2]}T{parts[3]}:00:00"
    return ""


def get_detections(
    camera_id: str | None = None,
    class_name: str | None = None,
    date: str | None = None,
    limit: int = 60,
) -> list[ArchivedFrame]:
    prefix = archive.PREDICTIONS_PREFIX + (f"{camera_id}/" if camera_id else "")
    keys = [k for k in archive.list_keys(prefix) if k.endswith(".json")]
    keys.sort(reverse=True)  # date/hour in the key => newest partitions first

    frames: list[ArchivedFrame] = []
    for scanned, key in enumerate(keys):
        if len(frames) >= limit or scanned >= _MAX_SCAN:
            break
        try:
            doc = PredictionDocument.model_validate(archive.read_json(key))
        except (RuntimeError, ValueError) as e:
            logger.warning("Skipping unreadable prediction '%s': %s", key, e)
            continue
        classes = sorted({p.class_name for p in doc.predictions})
        if class_name and class_name not in classes:
            continue
        captured_at = _captured_at_from_key(doc.frame_key)
        if date and not captured_at.startswith(date):
            continue
        top = max(doc.predictions, key=lambda p: p.confidence, default=None)
        frames.append(
            ArchivedFrame(
                frame_key=doc.frame_key,
                prediction_key=key,
                camera_id=doc.camera_id,
                captured_at=captured_at,
                frame_url=archive.presign_frame(doc.frame_key),
                frame_width=doc.frame_width,
                frame_height=doc.frame_height,
                top_class=top.class_name if top else None,
                top_confidence=round(top.confidence, 4) if top else None,
                classes=classes,
                predictions=doc.predictions,
            )
        )
    return frames


def get_metrics() -> ArchiveMetrics:
    rows = archive.read_summaries()
    cameras = camera_repo.list_cameras()
    camera_names = {c.id: c.name for c in cameras}

    class_counts: Counter[str] = Counter()
    per_camera_counts: Counter[str] = Counter()
    daily: dict[str, list[int]] = defaultdict(lambda: [0, 0])  # date -> [frames, bytes]
    detections_total = 0
    ingest_bytes = 0

    for row in rows:
        classes = row.get("classes") or []
        for cls in classes:
            class_counts[cls] += 1
        detections_total += int(row.get("detections", len(classes)))
        camera = row.get("camera_id", "")
        per_camera_counts[camera] += 1
        frame_bytes = int(row.get("frame_bytes", 0))
        ingest_bytes += frame_bytes
        day = row.get("date", "")
        daily[day][0] += 1
        daily[day][1] += frame_bytes

    return ArchiveMetrics(
        frames_archived=len(rows),
        predictions_written=len(rows),
        detections_total=detections_total,
        ingest_gigabytes=round(ingest_bytes / 1e9, 4),
        active_cameras=len(cameras),
        detections_by_class=[
            ClassCount(class_name=name, count=count)
            for name, count in class_counts.most_common(12)
        ],
        per_camera=[
            CameraFrameCount(
                camera_id=cid, camera_name=camera_names.get(cid, cid), frames=count
            )
            for cid, count in per_camera_counts.most_common()
        ],
        ingest_activity=[
            DailyIngest(date=day, frames=vals[0], gigabytes=round(vals[1] / 1e9, 4))
            for day, vals in sorted(daily.items())
            if day
        ],
    )
