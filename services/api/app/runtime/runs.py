import logging

from fastapi import APIRouter, HTTPException

from app.service.cameras import (
    CameraNotFoundError,
    RunNotFoundError,
    get_run,
    list_runs,
    start_run,
)
from app.types import RunRecord, RunStartResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/cameras/{camera_id}/runs", response_model=RunStartResponse, status_code=202
)
def start_run_endpoint(camera_id: str):
    """Queue a detection pass and return immediately; poll the run for status."""
    try:
        run = start_run(camera_id)
    except CameraNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    return RunStartResponse(run_id=run.id, camera_id=camera_id, status=run.status)


@router.get("/cameras/{camera_id}/runs", response_model=list[RunRecord])
def list_runs_endpoint(camera_id: str):
    try:
        return list_runs(camera_id)
    except CameraNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None


@router.get("/cameras/{camera_id}/runs/{run_id}", response_model=RunRecord)
def get_run_endpoint(camera_id: str, run_id: str):
    try:
        return get_run(camera_id, run_id)
    except RunNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
