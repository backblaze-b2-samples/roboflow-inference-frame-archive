"""Detection-run models.

A Run is one detection pass of a camera's model over its source clip. Status is
live in an in-process registry while the background worker runs, then persisted
to B2 as `runs/<camera_id>/<run_id>.json` on completion.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

RunStatus = Literal["queued", "running", "done", "failed"]


class RunRecord(BaseModel):
    id: str
    camera_id: str
    status: RunStatus = "queued"
    # Live progress counters, updated by the worker thread as frames stream by.
    frames_processed: int = 0
    frames_flagged: int = 0
    detections_written: int = 0
    bytes_written: int = 0
    # Resolved at runtime: "cuda" when an NVIDIA GPU is present, else "cpu".
    # onnxruntime (which `inference` runs on) has no Apple-MPS path, so Apple
    # Silicon reports "cpu".
    device: str = "cpu"
    model_alias: str = "yolov8n-640"
    # The summaries/<camera>/<run>.parquet key written on success.
    summary_key: str | None = None
    error: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class RunStartResponse(BaseModel):
    """Returned immediately when a run is accepted (202); poll the run for status."""

    run_id: str
    camera_id: str
    status: RunStatus
