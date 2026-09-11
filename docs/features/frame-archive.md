<!-- last_verified: 2026-09-11 -->
# Feature: Frame Archive

## Purpose
Browse the sample's own detection output — a gallery of flagged frames with bounding
boxes overlaid — scoped to this app's `frames/` and `predictions/` prefixes, distinct
from the full-bucket Files explorer.

## Used By
- UI: `/archive` (Detections), and the scoped gallery embedded in `/cameras/[id]`
- API: `GET /archive/detections`, `GET /archive/metrics`

## Core Functions
- `apps/web/src/components/archive/detections-gallery.tsx` — filters + grid
- `apps/web/src/components/archive/frame-overlay.tsx` — draws boxes over the presigned image
- `apps/web/src/lib/queries.ts` — `useDetections`, `useArchiveMetrics`
- `services/api/app/runtime/archive.py` — route handlers
- `services/api/app/service/archive.py` — gallery build + dashboard aggregation
- `services/api/app/repo/archive.py` — list/read predictions, presign frames

## Canonical Files
- Gallery: `apps/web/src/components/archive/detections-gallery.tsx`
- Read models: `services/api/app/service/archive.py`

## Inputs
- camera_id: string | null (query) — scope to one camera
- class_name: string | null (query) — filter by detected class
- date: string | null (query) — filter by capture date (YYYY-MM-DD)
- limit: int (query, 1–200, default 60)

## Outputs
- `GET /archive/detections` → `ArchivedFrame[]` — each carries a short-lived presigned frame URL, frame dimensions, and the prediction boxes so the browser overlays them
- `GET /archive/metrics` → `ArchiveMetrics` (see [Dashboard](dashboard.md))

## Flow
- Gallery lists prediction JSON keys (scoped to a camera prefix when given), reads a bounded page of them (newest partitions first), applies class/date filters
- For each, the frame is presigned (inline, 10-min expiry) and returned with its boxes
- `frame-overlay.tsx` positions boxes as percentages of the natural frame size, so they scale with the rendered image — no server-side redraw and no canvas

## Edge Cases
- No detections yet → empty state with a link to Cameras
- Bounded scan (`_MAX_SCAN`) caps prediction reads per request so a large archive never becomes thousands of GETs
- A presigned URL expires after 10 minutes; re-fetching the gallery re-signs
- The gallery is deliberately scoped to this sample's prefixes; the whole bucket stays browsable under Files

## UX States
- Empty: "No detections archived yet"
- Loading: skeleton tiles
- Error: inline `ErrorState` with Retry

## Verification
- Test files: covered indirectly by `services/api/tests/test_openapi_contract.py` (routes present) and the archive read models
- Required cases: routes present in the contract; gallery/metrics reachable
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Full local verify command: `pnpm verify:full` when E2E/live prerequisites apply
- Pass criteria: `pnpm verify` green; a populated gallery requires a completed detection run

## Related Docs
- [Detection run](detection-run.md)
- [Dashboard](dashboard.md)
- [File Browser](file-browser.md)
