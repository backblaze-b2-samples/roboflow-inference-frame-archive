<!-- last_verified: 2026-09-11 -->
# Feature: Cameras

## Purpose
Configure and manage edge cameras — the primary entity — end to end: each camera
names a detection model, a confidence threshold, and a source clip, and is the thing
you run detection passes against.

## Used By
- UI: `/cameras` (list), `/cameras/new` (create), `/cameras/[id]` (detail), `/cameras/[id]/edit` (edit)
- API: `POST /cameras`, `GET /cameras`, `GET /cameras/{camera_id}`, `PUT /cameras/{camera_id}`, `DELETE /cameras/{camera_id}`

## Core Functions
- `apps/web/src/components/cameras/camera-form.tsx` — create/edit form (selectors + create-form hints)
- `apps/web/src/components/cameras/cameras-list.tsx` — grid of cameras with per-card run/delete
- `apps/web/src/components/cameras/camera-detail.tsx` — detail, live run status, scoped archive
- `apps/web/src/lib/queries.ts` — `useCameras`, `useCamera`, `useCreateCamera`, `useUpdateCamera`, `useDeleteCamera`
- `services/api/app/runtime/cameras.py` — route handlers
- `services/api/app/service/cameras.py` — lifecycle + validation
- `services/api/app/repo/cameras.py` — B2-backed CRUD (`cameras/<id>.json`) + prefix-scoped delete

## Canonical Files
- Form-UX exemplar: `apps/web/src/components/settings/settings-form.tsx`
- Service logic: `services/api/app/service/cameras.py`

## Inputs
- name: string (text)
- site: string (text)
- model_alias: enum — `yolov8n-640` (default), `yolov8s-640`, `yolov8n-seg-640` (Select)
- confidence_threshold: enum — 0.25, 0.40 (default), 0.50, 0.60, 0.75 (Select)
- source: enum — `demo` (bundled CC-BY clip, default) or `upload` (a `/upload` object) (Select)
- source_key: string | null — required only when source is `upload`

## Outputs
- `Camera` JSON persisted to `cameras/<camera_id>.json` in B2 (no database)
- Side effect on delete: every object under `frames/<id>/`, `predictions/<id>/`, `summaries/<id>/`, and `runs/<id>/`, plus `cameras/<id>.json`, is removed — prefix-scoped, never a bucket-wide wipe

## Flow
- Create: `/cameras/new` form → `POST /cameras` mints an id and writes `cameras/<id>.json`
- Read: `/cameras` lists configs; `/cameras/[id]` shows one plus its scoped archive
- `list_cameras`/`list_runs` read each config with a bounded pool of concurrent B2 GETs rather than one at a time (one B2 GET per camera/run, no batch-read API) — with 10+ cameras this was slow enough on its own to look like the listing was stuck, independent of whether a detection run was active
- Edit: `/cameras/[id]/edit` opens pre-filled → `PUT /cameras/{id}` overwrites the config
- Delete: confirm dialog → `DELETE /cameras/{id}` removes the camera and its scoped artifacts

## Edge Cases
- source = `upload` with no clip selected → 400 (server) and a form error (client)
- Invalid model alias / confidence → 422 (Pydantic Literal validation)
- Unknown camera id → 404
- Finite-value fields use selectors on both create and edit, so an invalid free-text value can't be entered

## UX States
- Empty: "No cameras yet" with a New camera action
- Loading: skeleton cards
- Error: inline `ErrorState` with Retry

## Verification
- Test files: `services/api/tests/test_cameras.py`
- Required cases: CRUD round-trip, unknown-camera 404, upload-source-requires-clip 400, invalid alias 422
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Full local verify command: `pnpm verify:full` when E2E/live prerequisites apply
- Pass criteria: focused tests and `pnpm verify` green

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [Detection run](detection-run.md)
- [App Workflows](../app-workflows.md)
