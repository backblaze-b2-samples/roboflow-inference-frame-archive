<!-- last_verified: 2026-09-11 -->
# Feature: Detection Run

## Purpose
Run a camera's Roboflow Inference model over its source clip on-device, and stream
every flagged frame — JPEG + prediction JSON + a per-run Parquet summary — to B2.

## Used By
- UI: "Run detection" on `/cameras` and `/cameras/[id]`; live status on the detail page
- API: `POST /cameras/{camera_id}/runs`, `GET /cameras/{camera_id}/runs`, `GET /cameras/{camera_id}/runs/{run_id}`
- Job: background worker thread (`service/capture.execute_run`)

## Core Functions
- `services/api/app/service/capture.py` — the worker: decode → detect → archive
- `services/api/app/repo/inference_engine.py` — Roboflow Inference adapter (device autodetect, lazy import)
- `services/api/app/repo/video.py` — opencv decode + JPEG encode (lazy import)
- `services/api/app/repo/archive.py` — writes frames/predictions/summaries to B2
- `services/api/app/repo/cameras.py` — lock-guarded live run registry + persisted run records
- `apps/web/src/lib/queries.ts` — `useStartRun`, `useRuns`, `useRun` (poll while running)

## Canonical Files
- Engine adapter: `services/api/app/repo/inference_engine.py`
- Worker: `services/api/app/service/capture.py`

## Inputs
- camera_id: string (path) — the camera whose model/threshold/source drive the run
- source clip: the bundled CC-BY demo clip, or the camera's uploaded object (downloaded from B2)

## Outputs
- `frames/<camera>/<date>/<hour>/<run>_<idx>.jpg` — flagged frame JPEG
- `predictions/<camera>/<date>/<hour>/<run>_<idx>.json` — paired `PredictionDocument` (pixel-space boxes + frame dims)
- `summaries/<camera>/<run>.parquet` — per-frame roll-up (camera, run, class list, bytes, date)
- `runs/<camera>/<run>.json` — the run record (status, counts, device), persisted on completion
- Live side effect: an in-process registry updated as frames stream, polled by the UI

## Flow
- `POST /cameras/{id}/runs` mints a run, registers it (`queued`), spawns a worker thread, returns 202 immediately
- Worker sets `running`, resolves the source, auto-detects device (CUDA → CPU), warms the model
- For each sampled frame (stride + cap): run detection; if the top detection clears the camera's threshold, write the JPEG + prediction JSON and accumulate a summary row
- On completion: write the Parquet summary, set `done`, persist the run record to B2
- UI polls `GET …/runs/{run_id}` via TanStack Query `refetchInterval` while `queued`/`running`

## Edge Cases
- Engine not installed (base-only venv) → `EngineUnavailableError` → run persisted as `failed` with an actionable message; the POST never 500s
- Bundled demo clip missing → `failed` with "run scripts/fetch_demo_clip.sh"
- Upload source with no clip → `failed` with a pointer to `/upload`
- No detections clear the threshold → run completes `done` with zero flagged frames
- Apple Silicon → device resolves to `cpu` (onnxruntime has no MPS provider)

## UX States
- Queued/Running: status badge + approximate progress bar + live counts (frames processed/flagged, detections, bytes)
- Done: final counts and device
- Failed: destructive alert with the error message

## Verification
- Test files: `services/api/tests/test_cameras.py` (run start accepted + pollable, unknown camera 404)
- Required cases: run accepted (202), run pollable, unknown-camera 404
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Full local verify command: `pnpm verify:full` when E2E/live prerequisites apply
- Pass criteria: focused tests and `pnpm verify` green; a real end-to-end pass requires `services/api/requirements-ml.txt` and the demo clip

## Related Docs
- [Cameras](cameras.md)
- [Frame archive](frame-archive.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
