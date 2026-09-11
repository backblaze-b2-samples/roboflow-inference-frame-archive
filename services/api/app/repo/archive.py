"""Archive storage: the three coupled artifact streams in B2.

All boto3 access stays here. Every flagged frame writes a JPEG under `frames/`
and a paired prediction JSON under `predictions/`; each run writes a Parquet
roll-up under `summaries/`. Reads presign frames for the gallery and pull the
summary rows the dashboard aggregates. Deletes are always prefix-scoped.
"""

from __future__ import annotations

import io
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings
from app.repo.b2_client import get_presigned_url, get_s3_client
from app.repo.list_cache import invalidate as _invalidate_list_cache
from app.types.detections import PredictionDocument

logger = logging.getLogger(__name__)

FRAMES_PREFIX = "frames/"
PREDICTIONS_PREFIX = "predictions/"
SUMMARIES_PREFIX = "summaries/"

# One B2 GET per run summary — bounded so a bucket with many runs doesn't
# open unbounded concurrent connections.
_SUMMARY_READ_CONCURRENCY = 16


def _partition(captured_at: datetime) -> str:
    """YYYY-MM-DD/HH partition path segment for a capture time."""
    return f"{captured_at:%Y-%m-%d}/{captured_at:%H}"


def frame_key(camera_id: str, run_id: str, frame_index: int, captured_at: datetime) -> str:
    return f"{FRAMES_PREFIX}{camera_id}/{_partition(captured_at)}/{run_id}_{frame_index}.jpg"


def prediction_key_for(frame_key_value: str) -> str:
    """The prediction JSON key paired with a frame key."""
    return (
        PREDICTIONS_PREFIX
        + frame_key_value[len(FRAMES_PREFIX):].rsplit(".", 1)[0]
        + ".json"
    )


def put_frame(key: str, jpeg_bytes: bytes) -> None:
    client = get_s3_client()
    try:
        client.put_object(
            Bucket=settings.b2_bucket_name,
            Key=key,
            Body=io.BytesIO(jpeg_bytes),
            ContentType="image/jpeg",
        )
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"B2 put frame failed for '{key}': {e}") from e


def put_prediction(key: str, doc: PredictionDocument) -> None:
    client = get_s3_client()
    try:
        client.put_object(
            Bucket=settings.b2_bucket_name,
            Key=key,
            Body=doc.model_dump_json().encode("utf-8"),
            ContentType="application/json",
        )
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"B2 put prediction failed for '{key}': {e}") from e


def write_summary(camera_id: str, run_id: str, rows: list[dict]) -> str:
    """Write the per-run Parquet roll-up. Returns the summary key.

    pyarrow is imported lazily (it ships in requirements-ml.txt with the engine),
    so the API boots without it.
    """
    import pyarrow as pa
    import pyarrow.parquet as pq

    key = f"{SUMMARIES_PREFIX}{camera_id}/{run_id}.parquet"
    table = pa.Table.from_pylist(rows) if rows else pa.table({"camera_id": pa.array([], pa.string())})
    buffer = io.BytesIO()
    pq.write_table(table, buffer)
    client = get_s3_client()
    try:
        client.put_object(
            Bucket=settings.b2_bucket_name,
            Key=key,
            Body=buffer.getvalue(),
            ContentType="application/vnd.apache.parquet",
        )
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"B2 put summary failed for '{key}': {e}") from e
    _invalidate_list_cache()
    return key


def _list_objects(prefix: str) -> list[tuple[str, datetime]]:
    """Every (key, last_modified) pair under `prefix` (paginated)."""
    client = get_s3_client()
    objects: list[tuple[str, datetime]] = []
    kwargs: dict = {"Bucket": settings.b2_bucket_name, "Prefix": prefix, "MaxKeys": 1000}
    try:
        while True:
            response = client.list_objects_v2(**kwargs)
            objects.extend(
                (obj["Key"], obj["LastModified"]) for obj in response.get("Contents", [])
            )
            if not response.get("IsTruncated"):
                break
            kwargs["ContinuationToken"] = response["NextContinuationToken"]
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"B2 list failed for '{prefix}': {e}") from e
    return objects


def list_keys(prefix: str) -> list[str]:
    """Every object key under `prefix` (paginated)."""
    return [key for key, _ in _list_objects(prefix)]


def list_keys_with_modified(prefix: str) -> list[tuple[str, datetime]]:
    """Every (key, last_modified) pair under `prefix` (paginated).

    Used where order must reflect actual capture time rather than key layout
    — e.g. the unfiltered `/archive` gallery, whose keys are
    `predictions/<camera_id>/<date>/<hour>/...`. Sorting those keys lexically
    orders by the random `camera_id` ahead of the date, not by time.
    """
    return _list_objects(prefix)


def read_json(key: str) -> dict:
    client = get_s3_client()
    try:
        response = client.get_object(Bucket=settings.b2_bucket_name, Key=key)
        return json.loads(response["Body"].read())
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"B2 get failed for '{key}': {e}") from e


def _read_summary_rows(key: str) -> list[dict]:
    try:
        import pyarrow.parquet as pq

        client = get_s3_client()
        response = client.get_object(Bucket=settings.b2_bucket_name, Key=key)
        table = pq.read_table(io.BytesIO(response["Body"].read()))
    except (ClientError, BotoCoreError, OSError) as e:
        logger.warning("Skipping unreadable summary '%s': %s", key, e)
        return []
    return table.to_pylist()


def read_summaries() -> list[dict]:
    """All summary rows across every camera, for the dashboard aggregation.

    Degrades to an empty list if pyarrow is not installed (base-only venv with
    no runs yet) rather than raising on a dashboard read. Reads run
    concurrently — one B2 GET per run summary, and the dashboard aggregates
    every row order-independently (see `service.archive.get_metrics`), so a
    bounded thread pool cuts wall time from O(runs) sequential round trips to
    one.
    """
    keys = [k for k in list_keys(SUMMARIES_PREFIX) if k.endswith(".parquet")]
    if not keys:
        return []
    try:
        import pyarrow.parquet as pq  # noqa: F401
    except ImportError:
        logger.warning("pyarrow not installed; dashboard summaries unavailable")
        return []
    with ThreadPoolExecutor(max_workers=_SUMMARY_READ_CONCURRENCY) as pool:
        rows: list[dict] = []
        for batch in pool.map(_read_summary_rows, keys):
            rows.extend(batch)
    return rows


def presign_frame(key: str) -> str:
    """Presigned inline GET for serving an archived frame image to the UI."""
    return get_presigned_url(
        key, expires_in=settings.presign_get_expiry_seconds, disposition="inline"
    )


def delete_prefix(prefix: str) -> int:
    """Delete every object under `prefix` (batched). Returns the count removed.

    Scoped deletes only: callers pass a single camera's own prefixes, never a
    bucket-wide wipe.
    """
    keys = list_keys(prefix)
    if not keys:
        return 0
    client = get_s3_client()
    removed = 0
    for start in range(0, len(keys), 1000):
        batch = keys[start:start + 1000]
        try:
            client.delete_objects(
                Bucket=settings.b2_bucket_name,
                Delete={"Objects": [{"Key": k} for k in batch], "Quiet": True},
            )
        except (ClientError, BotoCoreError) as e:
            raise RuntimeError(f"B2 delete failed for '{prefix}': {e}") from e
        removed += len(batch)
    _invalidate_list_cache()
    return removed
