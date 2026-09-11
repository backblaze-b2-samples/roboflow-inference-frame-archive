"""Camera lifecycle and run orchestration.

CRUD over B2-persisted camera configs, plus `start_run`, which mints a run
record, registers it live, and hands the actual detection pass to a background
worker thread (`service.capture.execute_run`). The POST returns immediately with
the run id; the UI polls the run for status.
"""

from __future__ import annotations

import logging
import threading
import uuid
from datetime import UTC, datetime

from app.repo import cameras as camera_repo
from app.service import capture
from app.types.cameras import Camera, CameraCreate, CameraUpdate
from app.types.runs import RunRecord

logger = logging.getLogger(__name__)


class CameraNotFoundError(Exception):
    def __init__(self, detail: str = "Camera not found"):
        self.detail = detail
        super().__init__(detail)


class RunNotFoundError(Exception):
    def __init__(self, detail: str = "Run not found"):
        self.detail = detail
        super().__init__(detail)


class CameraValidationError(Exception):
    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _validate(payload: CameraCreate) -> None:
    if payload.source == "upload" and not payload.source_key:
        raise CameraValidationError(
            "A source clip is required when the source is 'upload'. Upload a "
            "video on /upload and pick it, or use the bundled demo clip."
        )


def create_camera(payload: CameraCreate) -> Camera:
    _validate(payload)
    now = datetime.now(UTC)
    camera = Camera(id=_new_id(), created_at=now, updated_at=now, **payload.model_dump())
    camera_repo.put_camera(camera)
    logger.info("Camera created: id=%s name=%s", camera.id, camera.name)
    return camera


def list_cameras() -> list[Camera]:
    return camera_repo.list_cameras()


def get_camera(camera_id: str) -> Camera:
    camera = camera_repo.get_camera(camera_id)
    if camera is None:
        raise CameraNotFoundError()
    return camera


def update_camera(camera_id: str, payload: CameraUpdate) -> Camera:
    _validate(payload)
    existing = get_camera(camera_id)
    updated = existing.model_copy(
        update={**payload.model_dump(), "updated_at": datetime.now(UTC)}
    )
    camera_repo.put_camera(updated)
    logger.info("Camera updated: id=%s", camera_id)
    return updated


def delete_camera(camera_id: str) -> None:
    get_camera(camera_id)  # 404 if missing
    camera_repo.delete_camera(camera_id)
    logger.info("Camera deleted (prefix-scoped): id=%s", camera_id)


def start_run(camera_id: str) -> RunRecord:
    camera = get_camera(camera_id)
    run = RunRecord(
        id=_new_id(),
        camera_id=camera_id,
        status="queued",
        model_alias=camera.model_alias,
        created_at=datetime.now(UTC),
    )
    camera_repo.register_run(run)
    threading.Thread(
        target=capture.execute_run, args=(run, camera), name=f"run:{run.id}", daemon=True
    ).start()
    logger.info("Run queued: id=%s camera=%s", run.id, camera_id)
    return run


def get_run(camera_id: str, run_id: str) -> RunRecord:
    run = camera_repo.get_run(camera_id, run_id)
    if run is None:
        raise RunNotFoundError()
    return run


def list_runs(camera_id: str) -> list[RunRecord]:
    get_camera(camera_id)  # 404 if missing
    return camera_repo.list_runs(camera_id)
