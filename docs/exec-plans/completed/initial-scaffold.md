# Build plan — `roboflow-inference-frame-archive`

Source of truth (starter kit, cloned fresh):
`.claude/scratch/vcsk-71ed9888-ba76-4adf-8d3e-08bf5afde493/`
Build target: `./roboflow-inference-frame-archive`

---

## 1. Purpose

`roboflow-inference-frame-archive` is a B2 sample for edge computer-vision teams —
manufacturing quality engineers and retail loss-prevention ops — who run detection
models at the edge and need a durable, searchable archive of what the cameras saw.
An edge "camera" runs **Roboflow Inference** (the OSS `inference` engine) locally on
each decoded frame; every frame whose top detection clears the camera's confidence
threshold is streamed to Backblaze **B2** as three coupled artifact streams — the JPEG
frame under `frames/…`, its structured prediction JSON under `predictions/…`, and an
hourly roll-up **Parquet** summary under `summaries/…`. The web app lets an operator
configure cameras, run a detection pass over a source clip, browse the resulting
flagged-frame archive with bounding boxes overlaid, and watch archive-wide metrics on a
dashboard. It demonstrates B2 as the single durable sink for a high-throughput,
multi-stream vision pipeline (frames + predictions + summaries), all over the
**S3-compatible API** with a custom user-agent and standard `B2_*` env vars, and the
detection engine running **100% locally** — B2 credentials are the only required keys.

**Headline capability = Roboflow Inference itself** (vendor's own engine, per the local
sampleapps convention). It is NOT substituted with bare ultralytics/YOLO; the `inference`
package is the detection engine on the critical path.

---

## 2. Architecture delta from vibe-coding-starter-kit

The starter kit is the ceiling. Keep its layered FastAPI + Next.js scaffolding, its UI
kit, and its three B2-backed screens; strip the demo framing; add the camera + archive
domain on top of the same `runtime → service → repo` layering. **B2 stays the sole data
store — camera configs and run records are JSON objects in the bucket, not a DB.**

### KEEP (as-is — starter contract, do not strip/rename/replace)
- `apps/web/src/components/ui/**` (shadcn primitives) and design tokens in
  `apps/web/src/app/globals.css`; the `/design` reference page.
- **Bucket explorer — NON-NEGOTIABLE KEEP.** `/files` route
  (`apps/web/src/app/files/`, `apps/web/src/components/files/**`) — full-bucket browse
  with preview/download/delete stays. The Files sidebar entry stays.
- **Upload.** `/upload` route + `apps/web/src/components/upload/**` (presigned direct-to-B2
  PUT). Reused as the "bring your own footage" path for a camera source. Sidebar entry stays.
- `/settings` + `apps/web/src/components/settings/settings-form.tsx` — kept, and reused
  as the **form-UX exemplar** for the camera forms (selectors + create-form default hints).
- Backend layering, middleware, health/metrics/rate-limit, list-cache stale-while-revalidate,
  OpenAPI contract machinery, all verify gates, `infra/` delivery contracts, agent-docs harness.

### TRIM (remove/replace the starter's demo-specific content)
- **Dashboard content** (route `/` KEPT, per AGENTS.md the dashboard is the screen designed
  to be rewritten): replace the illustrative widgets
  `apps/web/src/components/dashboard/{stats-cards,upload-chart,recent-uploads-table}.tsx`
  content with archive metrics (see §4). Same files, new content, same
  `runtime→service→repo` + TanStack Query wiring.
- **Starter narrative docs**: rewrite `README.md`, `PRODUCT.md`, and the "Core Features"
  section of `ARCHITECTURE.md` to this sample. Rewrite `docs/features/dashboard.md`;
  keep `docs/features/file-upload.md` / `file-browser.md` / `metadata-extraction.md` /
  `settings.md` (still accurate). Leave the starter's `docs/exec-plans/completed/*` history
  in place (doc-link-gate safe); our plan lands in `completed/` on PASS.
- `.env.example` starter B2 var names → standard names (see §6 rename table).

### ADD (new for this sample)
- **Primary entity — Camera** (see §4). Frontend `/cameras` (list), `/cameras/new`
  (create), `/cameras/[id]` (detail + run + its scoped frame archive),
  `/cameras/[id]/edit`. New sidebar entry "Cameras". Backend `runtime/cameras.py` +
  `runtime/runs.py`; `service/cameras.py`, `service/capture.py`, `service/archive.py`;
  repo adapters below.
- **Sample-specific asset explorer — `/archive` ("Detections") — MANDATORY ADD.** A
  gallery of flagged frames scoped to THIS sample's own output prefixes
  (`frames/` + `predictions/`), each thumbnail served by a presigned GET with its
  bounding boxes/labels overlaid, filterable by camera / class / date. This is the
  sample-scoped explorer that complements (never replaces) the full-bucket `/files`
  explorer. New sidebar entry "Detections".
- **Roboflow Inference engine adapter** (repo layer — external SDK confined here):
  `repo/inference_engine.py` wraps the `inference` package (`get_model`, run detection
  on a frame → typed predictions), with device autodetect **CUDA → CPU** (see §4 note).
- `repo/video.py` — decode a source clip to frames (opencv-python-headless), frame
  sampling/stride so a CPU pass over the demo clip is bounded (~cap 150 frames).
- `repo/archive.py` — write frame JPEG + prediction JSON + summary Parquet under the
  three prefixes; list/query archived frames; presigned GET to serve them. (boto3 stays
  confined to `repo/`.)
- `repo/cameras.py` — S3-backed CRUD for camera config JSON (`cameras/<id>.json`) and run
  records (`runs/<camera_id>/<run_id>.json`); in-process run-status registry guarded by a
  `threading.Lock`, mirroring the starter's list-cache concurrency idiom.
- `scripts/fetch_demo_clip.sh` — downloads a **verified-license CC-BY synthetic** open-movie
  clip (Blender open movie, e.g. Sintel/Tears of Steel) into a gitignored local path at
  setup. **No real people / real surveillance footage; no binary committed to the repo.**
- New feature docs: `docs/features/cameras.md`, `docs/features/detection-run.md`,
  `docs/features/frame-archive.md`. Update `ARCHITECTURE.md` (new layers/flows) and
  `docs/app-workflows.md` (camera → run → archive journey).

---

## 3. B2 surface (S3-compatible API only)

All via boto3 in `repo/` with the custom user agent. **No b2-native API anywhere** (repo
default). Operations exercised:

| Operation | Where | Purpose |
|-----------|-------|---------|
| `put_object` | archive/cameras repo | write frame JPEG, prediction JSON, summary Parquet, camera config JSON, run records |
| `list_objects_v2` | archive/cameras repo, list-cache | bucket explorer, `/archive` gallery, camera list, aggregate reads of `predictions/`/`summaries/` |
| `get_object` | archive repo | read prediction JSON + summary Parquet for dashboard/detail; read camera config |
| `head_object` | files repo (starter) | object metadata |
| `delete_object(s)` | cameras repo | delete a camera + its archived data — **scoped to that camera's prefixes only** (`frames/<id>/`, `predictions/<id>/`, `summaries/<id>/`, `cameras/<id>.json`, `runs/<id>/`); never a bucket-wide wipe |
| `generate_presigned_url` (GET) | archive/files repo | serve frames/predictions to the UI (10-min expiry) |
| `generate_presigned_url` (PUT) | upload repo (starter) | bring-your-own source clip, direct browser→B2 |

**B2 key layout in the bucket:**
```
cameras/<camera_id>.json                         # camera config (B2 is the datastore)
runs/<camera_id>/<run_id>.json                   # run record (status, counts)
frames/<camera_id>/YYYY-MM-DD/HH/<frame>.jpg     # flagged frame (JPEG)
predictions/<camera_id>/YYYY-MM-DD/HH/<frame>.json # paired prediction JSON
summaries/<camera_id>/<run_id>.parquet           # hourly/per-class roll-up (Parquet)
uploads/…                                        # starter upload path (BYO source clips)
```

No b2-native use → nothing to justify.

---

## 4. Key features

1. **Cameras (primary entity, full lifecycle).** Configure an edge camera (name, site,
   detection model, confidence threshold, source) and manage it end to end.
2. **Detection run (Roboflow Inference, local).** Run the camera's model over its source
   clip; write flagged frames + prediction JSON + a Parquet summary to B2; live status.
3. **Detections / frame archive (`/archive`).** Sample-scoped gallery of flagged frames
   with bounding boxes + labels overlaid, filter by camera/class/date, presigned serving.
4. **Bucket explorer (`/files`).** Full-bucket browse (kept from starter).
5. **Direct upload (`/upload`).** Bring-your-own source clip, presigned direct-to-B2 PUT.
6. **Archive dashboard (`/`).** Frames archived, predictions written, detections-by-class,
   ingest volume (GB) over time, active cameras, per-camera counts — all read from the
   `summaries/` roll-ups (the described "aggregator → dashboard" path), through
   `runtime→service→repo` + TanStack Query hooks in `apps/web/src/lib/queries.ts`.

### External API provider (per `api-provider-selection.md`)
Only one model is involved, and it IS the sample's point → **local, no remote provider.**

| Feature | Provider / model | `deployment` | Cost / full demo run | Key env var |
|---------|------------------|--------------|----------------------|-------------|
| Detection run | **Roboflow Inference** (`inference`) running a pretrained COCO detector, default alias `yolov8n-640` | **local** | **$0** (runs on-device; no paid API) | `ROBOFLOW_API_KEY` — **optional**, free-tier, weight-download only |

- Rule 1 of provider selection applies: a specific on-device engine (Roboflow Inference)
  is the sample's whole point → **LOCAL is the default**, not remote, not a substitute.
- **CPU-default / GPU-autodetect hard rule:** pick first available **CUDA → CPU** at
  runtime; never hard-require a GPU. **MPS caveat:** `inference` runs on onnxruntime, which
  has no first-class Apple-MPS path, so on Apple Silicon this sample runs on **CPU** (note
  this in the plan/docs; do not claim MPS). Contain any native-ML crash/macOS banner
  in-repo per the sampleapps convention; surface only if it BLOCKS the run.
- **`ROBOFLOW_API_KEY` is optional, never required.** Some `inference` builds fetch
  pretrained weights from the Roboflow hub on first load and want a free key for that
  download; the *inference itself is fully local*. Document it as an optional free-tier
  var in `.env.example` (commented, with the sign-up URL); **B2 credentials remain the only
  required keys**, honoring "no second API key" for the required set. If weight download
  needs the key in the installed build, note it in the README's "Optional" section.
- Deps to pin in `services/api/requirements*.txt`: `inference` (Roboflow),
  `onnxruntime` (CPU), `opencv-python-headless`, `pyarrow`, `pillow`. Keep authored Python
  files < 300 lines (split capture/inference/overlay helpers accordingly).

### Provider orchestration via Genblaze
**Not applicable** — the description's stack does not mention Genblaze/`genblaze-*`. Use the
standard `sample-builder` path (this is not a Genblaze sample).

### Primary-entity lifecycle (UI completeness — mandatory)
**Primary entity: Camera.** All five verbs are user-meaningful and are BUILT into the UI —
**`omitted_ui_verbs` is empty**:

| Verb | UI surface | Backend |
|------|-----------|---------|
| **create** | `/cameras/new` form | `POST /cameras` → `put_object cameras/<id>.json` |
| **read** | `/cameras` list + `/cameras/[id]` detail (shows the camera's scoped frame archive) | `GET /cameras`, `GET /cameras/{id}` |
| **edit** | `/cameras/[id]/edit` form | `PUT /cameras/{id}` |
| **delete** | delete button on list/detail (confirm dialog, reuse `danger-zone`/`alert-dialog`) | `DELETE /cameras/{id}` → prefix-scoped deletes |
| **run** | "Run detection" button on detail/list; live status + progress | `POST /cameras/{id}/runs`, `GET /cameras/{id}/runs/{run_id}` (TanStack Query poll while running) |

Run executes in a background worker thread; status (queued/running/done/failed, frames
processed, detections written, GB written) lives in a lock-guarded in-process registry and
is persisted to the run record in B2 on completion; the UI polls via TanStack Query
`refetchInterval` while running (no bare `useEffect+fetch`). Keep the demo clip short and
frame-sampled so a CPU run completes in a reasonable time.

### Form UX conventions (create/edit — exemplar: `settings-form.tsx`)
Finite-value fields use a **selector** (never free text), on BOTH create and edit forms:

| Field | Control | Values |
|-------|---------|--------|
| model | `Select` | curated Roboflow Inference aliases: `yolov8n-640` (default), `yolov8s-640`, `yolov8n-seg-640` (segmentation) |
| confidence threshold | `Select`/slider | discrete: 0.25, 0.40 (default), 0.50, 0.60, 0.75 |
| source | `Select` | "Bundled demo clip (CC-BY)" (default) · "Upload a video" (routes through `/upload`) |
| site / location | text input | open set — free text is correct |
| name | text input | open set — free text is correct |

**CREATE-form safe defaults surfaced as placeholder / `FormDescription` guidance only**
(never an autofill button): name placeholder e.g. `"Line 3 — QC Camera"`; site placeholder
`"Plant A / Entrance B"`; model pre-selected `yolov8n-640` (fastest, CPU-friendly);
confidence pre-selected `0.40`; source pre-selected "Bundled demo clip" with description
"Runs a detection pass over a CC-BY open-movie clip so you can see the archive fill with no
footage of your own." **EDIT form opens pre-filled** with the camera's real values (same
selectors, no default hints).

---

## 5. Doc transforms

- **Rewrite:** `README.md` (title, what/why-B2, quick start, the three-artifact-stream
  story, optional `ROBOFLOW_API_KEY`, local-CPU/CUDA note), `PRODUCT.md`,
  `ARCHITECTURE.md` (new repo adapters, capture flow, `frames/predictions/summaries`
  data flows, "Core Features"), `docs/features/dashboard.md`, `docs/app-workflows.md`.
- **New stubs → full docs:** `docs/features/cameras.md`, `docs/features/detection-run.md`,
  `docs/features/frame-archive.md`. Register per the AGENTS.md §9 doc-update mapping.
- **Keep:** `docs/features/{file-upload,file-browser,metadata-extraction,settings}.md`,
  `docs/{SECURITY,RELIABILITY,verification,dev-workflows,frontend-conventions}.md`,
  `AGENTS.md` + shims (update only where behavior changed; keep agent-docs gate green).
- **Delete:** none required (starter exec-plan history stays for link-gate safety).

---

## 6. Rename table (`vibe-coding-starter-kit` → `roboflow-inference-frame-archive`)

| Kind | From | To |
|------|------|----|
| repo / kebab slug | `vibe-coding-starter-kit` | `roboflow-inference-frame-archive` |
| display name `APP_NAME` (`apps/web/src/lib/app-config.ts`) | `Vibe Coding Starter Kit` | `Roboflow Frame Archive` |
| `APP_DESCRIPTION` | `File management dashboard template powered by Backblaze B2` | `Edge inference frame + prediction archive on Backblaze B2` |
| **B2 attribution token** — ONE slug across `user_agent_extra` (`repo/b2_client.py`) AND `utm_content` (`app-sidebar.tsx` link) | `b2ai-oss-start` | `b2ai-roboflow-inference-frame-archive` (`/b2-doctor` requires the token equal `b2ai-<package.json name>`, so it is the full repo slug, not an abbreviation) |
| root `package.json` `name` + workspace pkg names | `vibe-coding-starter-kit`* | `roboflow-inference-frame-archive`* |
| API title/description | (auto-derives from `APP_NAME` via branding gate — do **not** hardcode) | — |
| Railway/Vercel project slug, image tags, CI workflow slugs (if any) | `vibe-coding-starter-kit` | `roboflow-inference-frame-archive` |
| README title / badges / clone URL | starter | `roboflow-inference-frame-archive` |

**Env-var migration to the `/b2-doctor` standard (settings + `.env.example` + docs):**

| Starter | Standard (this sample) |
|---------|------------------------|
| `B2_KEY_ID` / `b2_key_id` | `B2_APPLICATION_KEY_ID` / `b2_application_key_id` |
| `B2_APPLICATION_KEY` | `B2_APPLICATION_KEY` (unchanged) |
| `B2_BUCKET_NAME` | `B2_BUCKET_NAME` (unchanged) |
| `B2_ENDPOINT` (required) | `B2_REGION` (required) + `B2_ENDPOINT` optional override; endpoint derived from region via an `endpoint_url` property |
| `B2_PUBLIC_URL` | `B2_PUBLIC_URL_BASE` |

Add optional, commented `ROBOFLOW_API_KEY` to `.env.example` with its sign-up URL. B2
credentials are the only REQUIRED keys.

---

## 7. Builder guardrails (must hold on PASS)

- Three B2 standards via `/b2-doctor`: S3 API default (no b2-native), custom user agent on
  every S3 client (`user_agent_extra="b2ai-roboflow-inference-frame-archive"`), standard `B2_*` names.
- boto3 + Roboflow Inference + cv2 confined to `repo/`; layering `types→config→repo→
  service→runtime` with no backward imports; authored Python files < 300 lines.
- Every new/changed route re-exports `docs/api/openapi.json` (`pnpm contract:export`),
  updates `lib/api-client.ts` `API_CLIENT_ROUTES`, `lib/queries.ts`, and the
  api-contract test (`SERVER_ONLY_OPERATIONS` for server-only routes).
- One attribution token across `user_agent_extra` + `utm_content`; `APP_NAME` is the only
  place the display name is defined.
- `pnpm verify` (agent-docs + api + web) green; new feature docs registered in
  `scripts/check-agent-docs.mjs` mapping.
- Demo footage is CC-BY synthetic, fetched by a script, gitignored, never committed, never
  real people. Deletes are always prefix-scoped.
