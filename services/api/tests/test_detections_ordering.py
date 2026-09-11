"""Regression test for the unfiltered `/archive` gallery ordering bug.

`predictions/` keys are `predictions/<camera_id>/<YYYY-MM-DD>/<HH>/<frame>`.
`camera_id` is a random hex id that sits *before* the date, so sorting the
raw key strings orders by camera rather than by time once 2+ cameras are
unfiltered — silently pushing a newer camera's frames past the bounded
`limit`. The service must sort by the object's actual last-modified time
instead.
"""

from datetime import UTC, datetime

from app.repo import archive as archive_repo
from app.service import archive as archive_service
from app.types.detections import Prediction, PredictionDocument


def _doc(camera_id: str, run_id: str) -> dict:
    return PredictionDocument(
        camera_id=camera_id,
        run_id=run_id,
        frame_index=0,
        timestamp_seconds=0.0,
        frame_width=640,
        frame_height=480,
        model_alias="yolov8n-640",
        frame_key=f"frames/{camera_id}/2026-09-01/00/{run_id}_0.jpg",
        predictions=[
            Prediction(class_name="person", confidence=0.9, x=0, y=0, width=1, height=1)
        ],
    ).model_dump()


def test_unfiltered_listing_orders_by_last_modified_not_camera_id(monkeypatch):
    # "aaaaaaaaaaaa" sorts before "zzzzzzzzzzzz" lexically, but its frame is
    # the OLDER one — a naive `keys.sort(reverse=True)` over the full key
    # string would (wrongly) put it first.
    old_key = "predictions/aaaaaaaaaaaa/2026-09-01/00/run1_0.json"
    new_key = "predictions/zzzzzzzzzzzz/2026-09-01/01/run2_0.json"
    old_time = datetime(2026, 9, 1, 0, 0, 0, tzinfo=UTC)
    new_time = datetime(2026, 9, 1, 1, 0, 0, tzinfo=UTC)

    monkeypatch.setattr(
        archive_repo,
        "list_keys_with_modified",
        lambda prefix: [(old_key, old_time), (new_key, new_time)],
    )
    docs = {old_key: _doc("aaaaaaaaaaaa", "run1"), new_key: _doc("zzzzzzzzzzzz", "run2")}
    monkeypatch.setattr(archive_repo, "read_json", lambda key: docs[key])
    monkeypatch.setattr(archive_repo, "presign_frame", lambda key: f"https://example/{key}")

    frames = archive_service.get_detections()

    assert [f.camera_id for f in frames] == ["zzzzzzzzzzzz", "aaaaaaaaaaaa"]


def test_single_camera_listing_still_orders_newest_first(monkeypatch):
    prefix_key_early = "predictions/cam1/2026-09-01/00/run1_0.json"
    prefix_key_late = "predictions/cam1/2026-09-02/00/run2_0.json"
    early = datetime(2026, 9, 1, 0, 0, 0, tzinfo=UTC)
    late = datetime(2026, 9, 2, 0, 0, 0, tzinfo=UTC)

    monkeypatch.setattr(
        archive_repo,
        "list_keys_with_modified",
        lambda prefix: [(prefix_key_early, early), (prefix_key_late, late)],
    )
    docs = {
        prefix_key_early: _doc("cam1", "run1"),
        prefix_key_late: _doc("cam1", "run2"),
    }
    monkeypatch.setattr(archive_repo, "read_json", lambda key: docs[key])
    monkeypatch.setattr(archive_repo, "presign_frame", lambda key: f"https://example/{key}")

    frames = archive_service.get_detections(camera_id="cam1")

    assert [f.prediction_key for f in frames] == [prefix_key_late, prefix_key_early]
