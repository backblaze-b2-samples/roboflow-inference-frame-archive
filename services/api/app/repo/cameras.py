"""Camera + run persistence in B2, plus the live run-status registry.

Camera configs (`cameras/<id>.json`) and run records
(`runs/<camera_id>/<run_id>.json`) are plain JSON objects in the bucket — B2 is
the datastore. A lock-guarded in-process registry holds the live status of runs
while their worker threads execute, mirroring the starter's list-cache
concurrency idiom; the record is persisted to B2 on completion.
"""

from __future__ import annotations

import io
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings
from app.repo import archive
from app.repo.b2_client import get_s3_client
from app.repo.list_cache import invalidate as _invalidate_list_cache
from app.types.cameras import Camera
from app.types.runs import RunRecord

logger = logging.getLogger(__name__)

CAMERAS_PREFIX = "cameras/"
RUNS_PREFIX = "runs/"

# Camera/run configs are one B2 GET per object with no batch-read API. A
# bounded thread pool keeps `list_cameras`/`list_runs` from serializing those
# reads one at a time — the same fix applied to the archive gallery/metrics
# reads in repo/service archive.py.
_READ_CONCURRENCY = 16

# Live run status keyed by run_id. Guarded by a lock because the worker thread
# writes while request handlers (on Starlette's threadpool) read.
_registry: dict[str, RunRecord] = {}
_registry_lock = Lock()


def _put_json(key: str, body: bytes, content_type: str = "application/json") -> None:
    client = get_s3_client()
    try:
        client.put_object(
            Bucket=settings.b2_bucket_name,
            Key=key,
            Body=io.BytesIO(body),
            ContentType=content_type,
        )
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"B2 put failed for '{key}': {e}") from e


def _get_json(key: str) -> dict | None:
    client = get_s3_client()
    try:
        response = client.get_object(Bucket=settings.b2_bucket_name, Key=key)
        return json.loads(response["Body"].read())
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey"):
            return None
        raise RuntimeError(f"B2 get failed for '{key}': {e}") from e


# --- cameras ---------------------------------------------------------------

def camera_key(camera_id: str) -> str:
    return f"{CAMERAS_PREFIX}{camera_id}.json"


def put_camera(camera: Camera) -> None:
    _put_json(camera_key(camera.id), camera.model_dump_json().encode("utf-8"))
    _invalidate_list_cache()


def get_camera(camera_id: str) -> Camera | None:
    data = _get_json(camera_key(camera_id))
    return Camera.model_validate(data) if data else None


def list_cameras() -> list[Camera]:
    keys = [k for k in archive.list_keys(CAMERAS_PREFIX) if k.endswith(".json")]
    with ThreadPoolExecutor(max_workers=_READ_CONCURRENCY) as pool:
        docs = pool.map(_get_json, keys)
    cameras = [Camera.model_validate(data) for data in docs if data]
    cameras.sort(key=lambda c: c.created_at, reverse=True)
    return cameras


def delete_camera(camera_id: str) -> None:
    """Delete a camera and every artifact scoped to it — prefix-scoped only."""
    for prefix in (
        f"{archive.FRAMES_PREFIX}{camera_id}/",
        f"{archive.PREDICTIONS_PREFIX}{camera_id}/",
        f"{archive.SUMMARIES_PREFIX}{camera_id}/",
        f"{RUNS_PREFIX}{camera_id}/",
    ):
        archive.delete_prefix(prefix)
    client = get_s3_client()
    try:
        client.delete_object(Bucket=settings.b2_bucket_name, Key=camera_key(camera_id))
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"B2 delete failed for camera '{camera_id}': {e}") from e
    _invalidate_list_cache()


# --- run records -----------------------------------------------------------

def run_key(camera_id: str, run_id: str) -> str:
    return f"{RUNS_PREFIX}{camera_id}/{run_id}.json"


def persist_run(run: RunRecord) -> None:
    _put_json(run_key(run.camera_id, run.id), run.model_dump_json().encode("utf-8"))
    _invalidate_list_cache()


def get_run(camera_id: str, run_id: str) -> RunRecord | None:
    with _registry_lock:
        live = _registry.get(run_id)
    if live is not None and live.camera_id == camera_id:
        return live
    data = _get_json(run_key(camera_id, run_id))
    return RunRecord.model_validate(data) if data else None


def list_runs(camera_id: str) -> list[RunRecord]:
    keys = [
        k for k in archive.list_keys(f"{RUNS_PREFIX}{camera_id}/") if k.endswith(".json")
    ]
    with ThreadPoolExecutor(max_workers=_READ_CONCURRENCY) as pool:
        docs = pool.map(_get_json, keys)
    runs: dict[str, RunRecord] = {}
    for data in docs:
        if data:
            record = RunRecord.model_validate(data)
            runs[record.id] = record
    # Live/registry state wins over a possibly-older persisted copy.
    with _registry_lock:
        for record in _registry.values():
            if record.camera_id == camera_id:
                runs[record.id] = record
    return sorted(runs.values(), key=lambda r: r.created_at, reverse=True)


# --- live registry ---------------------------------------------------------

def register_run(run: RunRecord) -> None:
    with _registry_lock:
        _registry[run.id] = run


def update_run(run: RunRecord) -> None:
    with _registry_lock:
        _registry[run.id] = run
