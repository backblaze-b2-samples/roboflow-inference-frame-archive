import logging

from fastapi import APIRouter, HTTPException

from app.service.archive import get_detections, get_metrics
from app.types import ArchivedFrame, ArchiveMetrics

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/archive/detections", response_model=list[ArchivedFrame])
def detections_endpoint(
    camera_id: str | None = None,
    class_name: str | None = None,
    date: str | None = None,
    limit: int = 60,
):
    """Sample-scoped gallery of flagged frames (frames/ + predictions/).

    Each item carries a presigned frame image URL and its boxes so the browser
    overlays them. Filterable by camera, class, and capture date.
    """
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 200")
    try:
        return get_detections(
            camera_id=camera_id, class_name=class_name, date=date, limit=limit
        )
    except RuntimeError:
        raise HTTPException(
            status_code=502, detail="Failed to read the detection archive"
        ) from None


@router.get("/archive/metrics", response_model=ArchiveMetrics)
def metrics_endpoint():
    """Archive-wide dashboard roll-up read from the summaries/ Parquet files."""
    try:
        return get_metrics()
    except RuntimeError:
        raise HTTPException(
            status_code=502, detail="Failed to read archive metrics"
        ) from None
