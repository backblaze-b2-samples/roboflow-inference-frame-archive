<!-- last_verified: 2026-08-06 -->
# Architecture

## Components

- **apps/web/** — Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  - Cameras: list / create / detail / edit (`/cameras…`) — the primary entity
  - Detection runs with live status polling on the camera detail page
  - Detections gallery (`/archive`) — flagged frames with boxes overlaid
  - Archive dashboard (`/`) read from the Parquet roll-ups
  - Full-bucket file browser and direct-to-B2 upload (bring-your-own footage)
  - Dark mode via `next-themes`
- **services/api/** — FastAPI backend (layered architecture)
  - REST API for cameras, runs, archive reads, and the file explorer/upload
  - Roboflow Inference detection engine (`repo/inference_engine.py`) — local, device autodetect
  - opencv frame decode/encode (`repo/video.py`) and Parquet summaries (`repo/archive.py`)
  - B2 S3 integration via boto3, confined to `repo/`
  - Background worker thread per run; lock-guarded live run registry
  - Health check, structured JSON logging, Prometheus-format metrics
- **packages/shared/** — TypeScript type definitions
  - Mirrors Pydantic models from the API (cameras, runs, detections, archive metrics)
  - Consumed by `apps/web/` as workspace dependency

## Backend Layering

The API follows a strict layered architecture:

```
types/     Pydantic models — no logic, no imports from other layers
  |
config/    Settings (pydantic-settings) — depends only on types
  |
repo/      Data access (boto3 B2 client) — no business logic
  |
service/   Business logic — calls repo, returns types
  |
runtime/   FastAPI routes — calls service, never repo directly
```

### Layering Rules

1. Dependencies flow downward only: `types` -> `config` -> `repo` -> `service` -> `runtime`
2. No backward imports (e.g., service must not import from runtime)
3. `boto3` only allowed in `repo/` layer
4. All boundary data uses Pydantic models (no raw dicts across layers)
5. Authored Python files under `services/api/app/` stay under 300 lines

### Directory Structure

```
services/api/
  main.py                  App entrypoint, middleware, router registration
  app/
    types/                 Pydantic models (cameras, runs, detections, files, …)
    config/                Settings loaded from environment
    repo/                  Data access — boto3 B2 client, archive/cameras stores,
                           inference_engine (Roboflow Inference), video (opencv)
    service/               Business logic (cameras, capture worker, archive, files)
    runtime/               FastAPI route handlers (cameras, runs, archive, files, …)
  requirements.txt/.lock   Base deps (installed by setup/verify/CI)
  requirements-ml.txt      Gated engine deps (inference, onnxruntime, opencv, pyarrow)
  tests/                   pytest tests (structural + integration)
```

The detection engine, opencv, and pyarrow are **lazy-imported** inside their repo
modules and live in the gated `requirements-ml.txt`, so the app and the
credential-free test suite boot without the heavy ML closure. A missing engine
surfaces as a persisted `failed` run with an actionable message, never a 500.

## Boundary Invariants

- **No external SDK leakage**: `boto3` is only imported in `app/repo/`. All other layers interact with B2 through the repo interface.
- **No raw dicts at boundaries**: All data crossing layer boundaries uses typed Pydantic models.
- **No cross-layer mutable state**: Configuration is read-only after init, and no mutable state is shared *between* layers. Intra-layer caches/counters (the listing cache in `repo/list_cache.py`, the B2 connectivity cache in `repo/b2_client.py`, the download counter in `repo/counter.py`, the live run registry in `repo/cameras.py`, the rate-limit and metrics state in `runtime/`) are module-local and guarded by a `threading.Lock`. Two kinds of background thread exist, both daemon: the listing cache's stale-while-revalidate re-scan (`main.lifespan` warms it once at startup so no user pays for the cold full-bucket scan), and one worker per detection run (`service/capture.py`) that streams frames to B2 and updates the lock-guarded run registry.
- **Validated inputs**: All HTTP inputs validated by FastAPI/Pydantic. File keys reject empty and path-traversal patterns; optional prefix confinement via `ALLOWED_KEY_PREFIX` (off by default).

## Deployment

- **Local dev** — `pnpm dev` runs both services via `concurrently`
  - Web: `localhost:3000`
  - API: `localhost:8000`
- **Railway** — two services from the same repository: `web` builds from the
  repository root because it consumes `packages/shared`; `api` builds from
  `services/api`. Each service's versioned config sits at its own root —
  `railway.json` and `services/api/railway.json` — the default path Railway
  discovers, so a one-click template deploy inherits the same build, start, and
  health behavior with nothing to configure by hand. The human-approved
  staging/production contract lives in [infra/railway/README.md](infra/railway/README.md).
- **Vercel** — one project using [Vercel Services](https://vercel.com/docs/services):
  the `web` (Next.js) and `api` (FastAPI) services build from the same repo and
  share one origin — the web app at `/`, the API under `/api`. The repo-root
  `vercel.json` declares both services and routes `/api/*` to the API service;
  the Vercel-only `services/api/index.py` strips the `/api` prefix so FastAPI
  keeps its native paths (`/health`, `/files`, …). Uploads go directly from the
  browser to B2 via a presigned PUT (see
  [File Upload](docs/features/file-upload.md)), so they bypass the Function's
  4.5 MB payload ceiling entirely — the bucket must allow the deploy origin in
  its CORS. A two-separate-Projects alternative and the full delivery contract
  live in [infra/vercel/README.md](infra/vercel/README.md).

External provisioning and deployment remain explicit user-approved actions.

## Data Stores

- **Backblaze B2** — object storage (S3-compatible API), the sole data store
  - Camera configs (`cameras/<id>.json`) and run records (`runs/<camera>/<run>.json`) are JSON objects — no application database
  - Flagged frames (`frames/…jpg`), predictions (`predictions/…json`), and per-run Parquet roll-ups (`summaries/…parquet`) under their own prefixes
  - Bring-your-own source clips under `uploads/`
  - Access via S3 `put_object` / `get_object` / `list_objects_v2` / `head_object` / `delete_objects` / `generate_presigned_url`

## External Services

- **Backblaze B2 S3 API** — file storage, retrieval, deletion, presigned URLs

## Trust Boundaries

See [docs/SECURITY.md](docs/SECURITY.md) for full security documentation.

- **Frontend -> API** — CORS-restricted to configured origins. `CORSMiddleware` is registered LAST in `main.py` (outermost) so it wraps **every** response, including uncaught-exception 500s — otherwise the browser would block error responses and the UI would only see an opaque "network error". See [docs/RELIABILITY.md](docs/RELIABILITY.md#error-handling). A per-IP rate-limit middleware sits inner to CORS; see [docs/SECURITY.md](docs/SECURITY.md#rate-limiting).
- **API -> B2** — authenticated via application keys, signature v4
- **Client -> B2** — presigned URLs for download (10-min expiry, forced attachment)

## Data Flows

- **Camera CRUD**: Browser -> `/cameras…` -> service -> repo `put/get/list/delete` on `cameras/<id>.json` (delete also removes the camera's `frames/`,`predictions/`,`summaries/`,`runs/` prefixes)
- **Detection run**: `POST /cameras/{id}/runs` -> worker thread: opencv decodes sampled frames -> Roboflow Inference detects (CUDA→CPU) -> flagged frames write JPEG + prediction JSON + a Parquet summary to B2; live status in the run registry, polled by the UI; run record persisted on completion
- **Archive read**: `GET /archive/detections` -> service lists `predictions/`, presigns frames, returns boxes for the browser overlay; `GET /archive/metrics` -> service reads every `summaries/*.parquet` and rolls it up
- **Upload**: Browser -> `POST /upload/presign` -> Browser PUTs bytes **directly to B2** -> `POST /upload/verify` (API HEADs + Range-sniffs the stored object)
- **File explorer**: `GET /files` / `/files/{key}/download` / `DELETE /files/{key}` over the full bucket

## Observability

- Structured JSON logging on all requests with `request_id`
- Request timing middleware (logs duration per request; also the catch-all that converts uncaught exceptions to a typed JSON 500)
- `/metrics` endpoint (Prometheus format: request count, latency, upload count)
- `/health` endpoint (B2 connectivity check)

## API Contract

- Checked-in OpenAPI artifact: `docs/api/openapi.json`
- Export/check command: `pnpm contract:export` / `pnpm contract:check`
- FastAPI freshness test: `services/api/tests/test_openapi_contract.py`
- Frontend route drift test: `apps/web/src/lib/api-contract.test.ts`

The frontend client keeps a small `API_CLIENT_ROUTES` registry in
`apps/web/src/lib/api-client.ts`. Tests compare that registry to the checked-in
OpenAPI artifact so route changes fail loudly before the hand-written client can
silently drift from FastAPI. `GET /metrics` is intentionally server-only.

## Canonical Files

- Layered API handler: `services/api/app/runtime/cameras.py`
- Service orchestration: `services/api/app/service/cameras.py`, `service/capture.py` (run worker)
- Detection engine adapter (repo): `services/api/app/repo/inference_engine.py`
- Archive store (repo): `services/api/app/repo/archive.py`; camera/run store: `repo/cameras.py`
- B2 S3 client (repo): `services/api/app/repo/b2_client.py`
- Pydantic models: `services/api/app/types/` (`cameras.py`, `runs.py`, `detections.py`, `files.py`, …)
- Config (pydantic-settings): `services/api/app/config/settings.py`
- Structural tests: `services/api/tests/test_structure.py`
- OpenAPI contract: `docs/api/openapi.json`; exporter: `services/api/scripts/export_openapi.py`
- Frontend API client: `apps/web/src/lib/api-client.ts`
- Shared TypeScript types: `packages/shared/src/types.ts`

## Core Features

- [Cameras](docs/features/cameras.md)
- [Detection run](docs/features/detection-run.md)
- [Frame archive](docs/features/frame-archive.md)
- [Dashboard](docs/features/dashboard.md)
- [File Upload](docs/features/file-upload.md)
- [File Browser](docs/features/file-browser.md)
- [Metadata Extraction](docs/features/metadata-extraction.md)

## References

- [docs/SECURITY.md](docs/SECURITY.md) — security principles and implementation
- [docs/RELIABILITY.md](docs/RELIABILITY.md) — reliability expectations
- [AGENTS.md](AGENTS.md) — architectural invariants and agent instructions
