<!-- last_verified: 2026-09-11 -->
# Feature: Dashboard

## Purpose
Provide an at-a-glance overview of the detection archive: frames archived, detections
by class, ingest volume, and active cameras — read from the Parquet roll-ups.

## Used By
- UI: `/` page (dashboard home)
- API: `GET /archive/metrics`

## Core Functions
- `apps/web/src/components/dashboard/stats-cards.tsx` — `ArchiveStatsCards` (4 metric cards)
- `apps/web/src/components/dashboard/upload-chart.tsx` — `IngestChart` (frames archived per day, total GB)
- `apps/web/src/components/dashboard/recent-uploads-table.tsx` — `DetectionBreakdown` (detections by class + frames by camera)
- `apps/web/src/lib/queries.ts` — `useArchiveMetrics()`
- `services/api/app/runtime/archive.py` — `GET /archive/metrics` handler
- `services/api/app/service/archive.py` — `get_metrics()` aggregation
- `services/api/app/repo/archive.py` — `read_summaries()` reads every `summaries/*.parquet`

## Canonical Files
- Aggregation: `services/api/app/service/archive.py`
- Cards layout: `apps/web/src/components/dashboard/stats-cards.tsx`

## Inputs
- None (dashboard loads data automatically)

## Outputs
- `GET /archive/metrics` → `ArchiveMetrics`:
  - `frames_archived`, `predictions_written`, `detections_total`, `ingest_gigabytes`, `active_cameras`
  - `detections_by_class: ClassCount[]`, `per_camera: CameraFrameCount[]`, `ingest_activity: DailyIngest[]`

## Flow
- Page loads → one `GET /archive/metrics` call
- The service lists `summaries/`, reads each per-run Parquet (the aggregator → dashboard path), and rolls up counts by class, by camera, and by day
- Stat cards show frames archived, detections, ingest GB, active cameras
- The ingest chart plots frames archived per day with the total GB in the corner
- The breakdown table lists detections by class and frames by camera, with a link to the archive

## Edge Cases
- No runs yet → zeroed cards, empty chart/table states
- pyarrow not installed (base-only venv) and summaries exist → `read_summaries()` degrades to empty rather than erroring a dashboard read (a real run installs the ML deps)
- API unavailable → inline error states with Retry

## UX States
- Loading: an on-screen "Loading archive metrics…" notice + skeletons
- Empty: "No ingest yet" / "No detections yet"
- Loaded: populated cards, chart, breakdown

## Verification
- Test files: `services/api/tests/test_openapi_contract.py` (route present), `services/api/tests/test_cameras.py`
- Required cases: metrics route present; empty-archive zeros; populated roll-up after a run
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Full local verify command: `pnpm verify:full` when the E2E/live prerequisites in [Verification](../verification.md#non-live-verification) are available
- Pass criteria: focused tests and `pnpm verify` green

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [Frame archive](frame-archive.md)
- [App Workflows](../app-workflows.md)
