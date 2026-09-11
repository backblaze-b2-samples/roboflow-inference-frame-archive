"""Camera domain models.

A Camera is the sample's primary entity: an edge detection endpoint whose config
is persisted as a JSON object in B2 (`cameras/<id>.json`) — B2 is the datastore,
there is no database. Finite-option fields (model, confidence, source) are
constrained here so both the API and the form selectors share one contract.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# Curated Roboflow Inference aliases offered in the camera form. Kept small and
# CPU-friendly; the default is the fastest. Segmentation alias included to show
# a second selectable model (still COCO-class output for the archive).
ModelAlias = Literal["yolov8n-640", "yolov8s-640", "yolov8n-seg-640"]

# Discrete confidence thresholds surfaced as a selector (never free text).
ConfidenceThreshold = Literal[0.25, 0.40, 0.50, 0.60, 0.75]

# "demo"  -> the bundled CC-BY open-movie clip (default, no footage of your own)
# "upload" -> a source clip the user brought via the /upload direct-to-B2 path
CameraSource = Literal["demo", "upload"]


class CameraCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    site: str = Field(min_length=1, max_length=160)
    model_alias: ModelAlias = "yolov8n-640"
    confidence_threshold: ConfidenceThreshold = 0.40
    source: CameraSource = "demo"
    # Set only when source == "upload": the uploads/<file> key the browser PUT
    # directly to B2. Ignored for the bundled demo clip.
    source_key: str | None = None


class CameraUpdate(CameraCreate):
    """Same shape as create — the edit form opens pre-filled with real values."""


class Camera(CameraCreate):
    id: str
    created_at: datetime
    updated_at: datetime
