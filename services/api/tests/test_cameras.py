"""Camera lifecycle + run-start API tests (hermetic: repo boundary mocked)."""

import pytest

from app.repo import cameras as camera_repo
from app.service import cameras as camera_service


@pytest.fixture
def memory_store(monkeypatch):
    """Back the camera/run repo with in-memory dicts and stub the run worker."""
    cams: dict = {}
    runs: dict = {}

    monkeypatch.setattr(camera_repo, "put_camera", lambda c: cams.__setitem__(c.id, c))
    monkeypatch.setattr(camera_repo, "get_camera", lambda cid: cams.get(cid))
    monkeypatch.setattr(
        camera_repo,
        "list_cameras",
        lambda: sorted(cams.values(), key=lambda c: c.created_at, reverse=True),
    )
    monkeypatch.setattr(camera_repo, "delete_camera", lambda cid: cams.pop(cid, None))
    monkeypatch.setattr(camera_repo, "register_run", lambda r: runs.__setitem__(r.id, r))
    monkeypatch.setattr(camera_repo, "update_run", lambda r: runs.__setitem__(r.id, r))
    monkeypatch.setattr(camera_repo, "persist_run", lambda r: runs.__setitem__(r.id, r))
    monkeypatch.setattr(camera_repo, "get_run", lambda cid, rid: runs.get(rid))
    monkeypatch.setattr(
        camera_repo, "list_runs", lambda cid: [r for r in runs.values() if r.camera_id == cid]
    )
    # Stub the background worker so run-start does no real decode/detection.
    monkeypatch.setattr(camera_service.capture, "execute_run", lambda run, camera: None)
    return cams, runs


BASE = {
    "name": "Line 3 — QC Camera",
    "site": "Plant A / Entrance B",
    "model_alias": "yolov8n-640",
    "confidence_threshold": 0.4,
    "source": "demo",
}


async def test_camera_crud_roundtrip(client, memory_store):
    created = await client.post("/cameras", json=BASE)
    assert created.status_code == 201
    camera_id = created.json()["id"]

    listed = await client.get("/cameras")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    fetched = await client.get(f"/cameras/{camera_id}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == BASE["name"]

    updated = await client.put(
        f"/cameras/{camera_id}", json={**BASE, "confidence_threshold": 0.6}
    )
    assert updated.status_code == 200
    assert updated.json()["confidence_threshold"] == 0.6

    deleted = await client.delete(f"/cameras/{camera_id}")
    assert deleted.status_code == 200
    assert deleted.json() == {"deleted": True, "id": camera_id}


async def test_unknown_camera_is_404(client, memory_store):
    missing = await client.get("/cameras/does-not-exist")
    assert missing.status_code == 404


async def test_upload_source_requires_a_clip(client, memory_store):
    bad = await client.post("/cameras", json={**BASE, "source": "upload"})
    assert bad.status_code == 400


async def test_invalid_model_alias_is_422(client, memory_store):
    bad = await client.post("/cameras", json={**BASE, "model_alias": "sslpuffnet"})
    assert bad.status_code == 422


async def test_run_start_is_accepted_and_pollable(client, memory_store):
    created = await client.post("/cameras", json=BASE)
    camera_id = created.json()["id"]

    started = await client.post(f"/cameras/{camera_id}/runs")
    assert started.status_code == 202
    body = started.json()
    assert body["camera_id"] == camera_id
    assert body["status"] in {"queued", "running", "done", "failed"}

    run = await client.get(f"/cameras/{camera_id}/runs/{body['run_id']}")
    assert run.status_code == 200
    assert run.json()["id"] == body["run_id"]


async def test_run_start_unknown_camera_is_404(client, memory_store):
    started = await client.post("/cameras/nope/runs")
    assert started.status_code == 404
