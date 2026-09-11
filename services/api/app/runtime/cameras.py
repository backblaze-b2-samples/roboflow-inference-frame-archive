import logging

# Sync `def` handlers: the B2-backed service calls are blocking boto3, so
# Starlette runs them in its threadpool (see runtime/files.py rationale).
from fastapi import APIRouter, HTTPException

from app.service.cameras import (
    CameraNotFoundError,
    CameraValidationError,
    create_camera,
    delete_camera,
    get_camera,
    list_cameras,
    update_camera,
)
from app.types import Camera, CameraCreate, CameraUpdate

logger = logging.getLogger(__name__)

router = APIRouter()

# SECURITY: these routes are intentionally UNAUTHENTICATED and single-tenant
# (see docs/SECURITY.md). A multi-tenant clone must add an auth dependency and
# scope cameras/archive prefixes to the caller.


@router.post("/cameras", response_model=Camera, status_code=201)
def create_camera_endpoint(payload: CameraCreate):
    try:
        return create_camera(payload)
    except CameraValidationError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Failed to store camera") from None


@router.get("/cameras", response_model=list[Camera])
def list_cameras_endpoint():
    try:
        return list_cameras()
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Failed to read cameras") from None


@router.get("/cameras/{camera_id}", response_model=Camera)
def get_camera_endpoint(camera_id: str):
    try:
        return get_camera(camera_id)
    except CameraNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None


@router.put("/cameras/{camera_id}", response_model=Camera)
def update_camera_endpoint(camera_id: str, payload: CameraUpdate):
    try:
        return update_camera(camera_id, payload)
    except CameraNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    except CameraValidationError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Failed to store camera") from None


@router.delete("/cameras/{camera_id}")
def delete_camera_endpoint(camera_id: str):
    try:
        delete_camera(camera_id)
    except CameraNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Failed to delete camera") from None
    logger.info("Camera deleted: id=%s", camera_id)
    return {"deleted": True, "id": camera_id}
