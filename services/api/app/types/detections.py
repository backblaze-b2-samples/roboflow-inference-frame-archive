"""Detection / archived-frame models (the three coupled artifact streams).

Every flagged frame produces a JPEG under `frames/` and a paired prediction JSON
under `predictions/`; a run also writes a Parquet roll-up under `summaries/`. The
prediction JSON carries pixel-space boxes plus the frame dimensions so the
`/archive` gallery can overlay boxes on the presigned frame image in the browser.
"""

from pydantic import BaseModel


class Prediction(BaseModel):
    """One detected object in pixel space (top-left origin, width/height)."""

    class_name: str
    confidence: float
    x: float
    y: float
    width: float
    height: float


class PredictionDocument(BaseModel):
    """The JSON stored under `predictions/…` alongside each flagged frame."""

    camera_id: str
    run_id: str
    frame_index: int
    timestamp_seconds: float
    frame_width: int
    frame_height: int
    model_alias: str
    frame_key: str
    predictions: list[Prediction]


class ArchivedFrame(BaseModel):
    """A gallery row for `/archive`: the presigned frame image plus its boxes."""

    frame_key: str
    prediction_key: str
    camera_id: str
    captured_at: str
    frame_url: str
    frame_width: int
    frame_height: int
    top_class: str | None
    top_confidence: float | None
    classes: list[str]
    predictions: list[Prediction]


class ClassCount(BaseModel):
    class_name: str
    count: int


class DailyIngest(BaseModel):
    date: str
    frames: int
    gigabytes: float


class CameraFrameCount(BaseModel):
    camera_id: str
    camera_name: str
    frames: int


class ArchiveMetrics(BaseModel):
    """Dashboard roll-up read from the `summaries/` Parquet files."""

    frames_archived: int
    predictions_written: int
    detections_total: int
    ingest_gigabytes: float
    active_cameras: int
    detections_by_class: list[ClassCount]
    per_camera: list[CameraFrameCount]
    ingest_activity: list[DailyIngest]
