<!-- last_verified: 2026-09-11 -->
# Roboflow Frame Archive

A B2 sample for edge computer-vision teams. An edge "camera" runs **[Roboflow
Inference](https://github.com/roboflow/inference)** — the OSS `inference` engine —
**100% locally** on each decoded frame, and every frame whose top detection clears
the camera's confidence threshold is streamed to **[Backblaze
B2](https://www.backblaze.com/cloud-storage?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-roboflow-inference-frame-archive)**
as three coupled artifact streams: the JPEG frame, its structured prediction JSON,
and an hourly **Parquet** roll-up. It demonstrates B2 as the single durable sink
for a high-throughput, multi-stream vision pipeline — all over the S3-compatible
API, with the detection engine on-device and **B2 credentials the only required keys**.

**What you get out of the box:**
- Configure edge **cameras** (model, confidence threshold, source) — full create / read / edit / delete / run lifecycle.
- Run a **Roboflow Inference** detection pass over a source clip, on-device (CUDA → CPU auto-detect); live run status.
- A sample-scoped **Detections** gallery of flagged frames with bounding boxes overlaid, filterable by camera / class / date.
- An **archive dashboard**: frames archived, detections by class, ingest volume, active cameras — read from the Parquet roll-ups.
- The reusable B2 scaffolding: full-bucket **Files** explorer and direct-to-B2 **Upload** (bring your own footage).

## What it looks like

**Dashboard** — archive metrics (frames archived, detections, ingest volume, active cameras), a per-day ingest chart, and a detections-by-class breakdown read from the Parquet roll-ups.

![Dashboard with frames archived, detections, ingest volume, active cameras, an ingest chart, and a detection breakdown by class](docs/images/dashboard.png)

**Cameras** — the edge-camera fleet, each card showing its detection model, confidence threshold, and source clip alongside run, edit, and delete controls.

![Cameras grid of edge cameras, each card showing model, confidence threshold, source, and run/edit/delete controls](docs/images/cameras.png)

**Camera detail** — one camera's latest run stats (frames processed, flagged, detections, bytes archived) and its inline archive of flagged frames with bounding boxes overlaid.

![Camera detail view with latest-run stats and an inline gallery of flagged frames with detection boxes](docs/images/camera-detail.png)

**Detections** — the sample-scoped gallery of every flagged frame with detection boxes drawn on-device, filterable by camera, class, and date.

![Detections gallery of flagged frames with bounding boxes, each labeled with class, confidence, and source camera](docs/images/detections.png)

## Quick Start

You need: Node.js >= 20, pnpm >= 9, Python >= 3.12, and a free **[Backblaze B2
account](https://www.backblaze.com/sign-up/ai-cloud-storage?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-roboflow-inference-frame-archive)**.
No Roboflow account is required.

```bash
git clone https://github.com/backblaze-b2-samples/roboflow-inference-frame-archive.git
cd roboflow-inference-frame-archive
pnpm run setup
```

`pnpm run setup` copies `.env.example` to `.env` (only if missing), installs
workspace dependencies, creates `services/api/.venv`, and installs the API's
committed Python 3.12 resolution from `services/api/requirements.lock`. It is safe
to rerun.

> Use the `pnpm run` form: `setup` (like `doctor`) is a built-in pnpm command
> before pnpm 11, so bare `pnpm setup` runs pnpm's own command instead of this script.

**1. Add your B2 credentials.** Open `.env` and fill in the four required keys from
the [Backblaze B2 dashboard](https://secure.backblaze.com/b2_buckets.htm) — create a
bucket (`B2_BUCKET_NAME`, and its region → `B2_REGION`) and an application key with
Read and Write (`B2_APPLICATION_KEY_ID`, `B2_APPLICATION_KEY`). The S3 endpoint is
derived from the region, so there is no endpoint to paste.

**2. Install the detection engine (for real detection passes).** The engine is
gated so the app and its tests boot without the heavy ML closure:

```bash
services/api/.venv/bin/pip install -r services/api/requirements-ml.txt
bash scripts/fetch_demo_clip.sh   # downloads a CC-BY synthetic demo clip (gitignored)
```

**3. Run it.**

```bash
pnpm dev
```

Frontend at `localhost:3000`, API at `localhost:8000` (Swagger UI at `/docs`).
Create a camera with the bundled demo-clip source, click **Run detection**, and
watch the archive fill.

### Detection runs locally — device selection

Detection runs on-device. The engine auto-detects the first available of
**CUDA → CPU** at runtime and never hard-requires a GPU. Roboflow Inference runs on
onnxruntime, which has **no Apple-MPS execution provider**, so on Apple Silicon this
sample runs on **CPU** (we do not claim MPS). Runs are frame-sampled and capped so a
CPU pass over the demo clip completes quickly.

### Optional: `ROBOFLOW_API_KEY`

Detection is fully local and needs **no key**. Some `inference` builds fetch
pretrained weights from the Roboflow hub on first load and want a free-tier key for
that download only — set `ROBOFLOW_API_KEY` in `.env` if your build asks for it
([free sign-up](https://app.roboflow.com/settings/api)). B2 credentials remain the
only required keys.

## When to use

Use this repository when you want a working reference for archiving edge computer-
vision output — frames, predictions, and summaries — to durable object storage over
the S3-compatible API, and a UI to configure cameras, run detection passes, and
browse the resulting archive. It is a dependable scaffold with strict architecture,
contract checks, and tests, not a blank prototype.

## When not to use

Do not choose this expecting a complete hosted product, a managed camera fleet, or a
production surveillance system. It ships no managed hosting, user accounts,
authentication, tenant isolation, or on-call operations. It is single-tenant and
unauthenticated by default. You own the product-specific security, operations,
capacity, and compliance decisions for anything you adapt.

## Why Backblaze B2?

[Backblaze B2](https://www.backblaze.com/cloud-storage?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-roboflow-inference-frame-archive)
is the object storage this sample is built around — the single durable sink for the
whole pipeline:

- **S3-compatible API.** B2 speaks the S3 API, so the `boto3` calls you already use for AWS S3 work unchanged — point them at B2's endpoint. All storage access is isolated in `services/api/app/repo/`, nothing locked to a proprietary client.
- **Built for data-heavy vision workloads.** Frames, predictions, and Parquet summaries accumulate fast; B2 storage runs at a fraction of hyperscaler pricing with generous free egress.
- **Free to start.** A [free B2 account](https://www.backblaze.com/sign-up/ai-cloud-storage?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-roboflow-inference-frame-archive) runs everything here.

### How the three artifact streams are laid out in the bucket

```
cameras/<camera_id>.json                            # camera config (B2 is the datastore)
runs/<camera_id>/<run_id>.json                      # run record (status, counts)
frames/<camera_id>/YYYY-MM-DD/HH/<frame>.jpg        # flagged frame (JPEG)
predictions/<camera_id>/YYYY-MM-DD/HH/<frame>.json  # paired prediction JSON
summaries/<camera_id>/<run_id>.parquet              # per-run roll-up (Parquet)
uploads/…                                           # bring-your-own source clips
```

There is no database — camera configs and run records are JSON objects in the bucket.

## Core Features

- [Cameras](docs/features/cameras.md) — configure and manage edge cameras (the primary entity)
- [Detection run](docs/features/detection-run.md) — a local Roboflow Inference pass that archives frames, predictions, and a Parquet summary
- [Frame archive](docs/features/frame-archive.md) — the sample-scoped `/archive` gallery with boxes overlaid
- [Dashboard](docs/features/dashboard.md) — archive metrics read from the Parquet roll-ups
- [File Upload](docs/features/file-upload.md) — direct-to-B2 upload for bring-your-own footage
- [File Browser](docs/features/file-browser.md) — full-bucket explorer (list, preview, download, delete)
- [Metadata Extraction](docs/features/metadata-extraction.md) — image/PDF fields and checksums
- [Design System](docs/design-system.md) — tokens, primitives, error/empty states. Live at `/design`.

## Tech Stack

- TypeScript, Next.js 16, React 19, Tailwind v4, shadcn/ui, Recharts, TanStack Query
- Python 3.12+, FastAPI, boto3, Pydantic v2
- Roboflow Inference (`inference`) + onnxruntime, opencv-python-headless, pyarrow (gated ML deps)
- Backblaze B2 (S3-compatible object storage)
- pnpm workspaces (monorepo)

## Commands

| Command | What it does |
|---------|-------------|
| `pnpm run setup` | One-time cold start: copy `.env.example` → `.env` (only if missing), install deps, create the backend venv, install locked API deps |
| `pnpm dev` | Start frontend + backend (runs the `pnpm run doctor` preflight first) |
| `pnpm wait-ready` | Block until the running web + API answer, print one line, exit 0/1 |
| `pnpm verify` | Credential-free pre-PR suite — runs `pnpm check:agent-docs`, `pnpm verify:api`, then `pnpm verify:web` |
| `pnpm verify:api` | Backend half — lint, tests, structural boundaries |
| `pnpm verify:web` | Frontend half — lint, unit tests, typecheck + build |
| `pnpm verify:full` | `pnpm verify` plus Playwright E2E; needs a live local stack, real `.env`, and Chromium |
| `pnpm test:verify` | Run throwaway verification specs from `apps/web/e2e/verify/` |
| `pnpm contract:export` / `pnpm contract:check` | Export / verify the FastAPI OpenAPI contract in `docs/api/openapi.json` |

`pnpm verify` is the gate to run before a PR. It needs `services/api/.venv` from
`pnpm run setup` but no B2 credentials, no ML engine, and no browser. For the full
command reference see [docs/dev-workflows.md](docs/dev-workflows.md#commands); for
worktree/port-fallback and slow-run recovery see
[docs/verification.md](docs/verification.md).

## Deploying to Vercel

Deploys as **one Vercel project** — the Next.js web app and FastAPI API build from
the same repo and share one origin (web at `/`, API under `/api`), so there is **no
CORS and no second URL to wire up**. Note that a serverless Vercel deploy runs the
CRUD/archive/dashboard surface; long CPU detection passes are best run on a host with
the ML engine installed.

[![Deploy to Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fbackblaze-b2-samples%2Froboflow-inference-frame-archive&project-name=roboflow-inference-frame-archive&repository-name=roboflow-inference-frame-archive&demo-title=Roboflow%20Frame%20Archive&demo-description=Edge%20Roboflow%20Inference%20frame%20%2B%20prediction%20archive%20on%20Backblaze%20B2.&env=B2_APPLICATION_KEY_ID,B2_APPLICATION_KEY,B2_REGION,B2_BUCKET_NAME&envDescription=B2%20credentials%2C%20region%2C%20and%20bucket&envLink=https%3A%2F%2Fgithub.com%2Fbackblaze-b2-samples%2Froboflow-inference-frame-archive%2Fblob%2Fmain%2Finfra%2Fvercel%2FREADME.md)

Two things to know before a real deploy: your bucket's CORS must allow the deploy
origin, and the deployed API is unauthenticated and bucket-wide — use a dedicated
bucket/key for any preview. Full setup is in the
[Vercel delivery contract](infra/vercel/README.md).

## Documentation Map

| Doc | Purpose |
|-----|---------|
| [AGENTS.md](AGENTS.md) | Agent table of contents — start here |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System layout, layering, data flows |
| [docs/features/](docs/features/) | Feature docs (cameras, detection run, frame archive, dashboard, upload, browser) |
| [docs/app-workflows.md](docs/app-workflows.md) | User journeys (camera → run → archive) |
| [docs/dev-workflows.md](docs/dev-workflows.md) | Engineering workflows, command index, releases |
| [docs/verification.md](docs/verification.md) | What each gate checks, and failure recovery |
| [docs/frontend-conventions.md](docs/frontend-conventions.md) | Frontend conventions, screens, data fetching |
| [docs/SECURITY.md](docs/SECURITY.md) | Security principles |
| [docs/RELIABILITY.md](docs/RELIABILITY.md) | Reliability expectations |
| [docs/api/openapi.json](docs/api/openapi.json) | Checked contract for the local FastAPI API |
| [infra/vercel/README.md](infra/vercel/README.md) | Vercel deployment contract |

## FAQ

**What is Roboflow Frame Archive?**
A full-stack sample (Next.js 16 + FastAPI) that runs Roboflow Inference on-device
over a source clip and archives every flagged frame — the JPEG, its prediction JSON,
and a per-run Parquet summary — to Backblaze B2 over the S3-compatible API.

**Does detection run in the cloud?**
No. The `inference` engine runs 100% locally, auto-detecting CUDA → CPU. B2
credentials are the only required keys.

**Do I need a Roboflow API key?**
No. It is optional and free-tier — only some `inference` builds use it to download
pretrained weights on first load. Set `ROBOFLOW_API_KEY` only if your build asks.

**Does it run on Apple Silicon?**
Yes, on CPU. onnxruntime has no Apple-MPS execution provider, so this sample uses CPU
on Apple Silicon (never MPS) and never requires a GPU.

**Is there a database?**
No. Camera configs and run records are JSON objects in the B2 bucket; frames,
predictions, and summaries live under their own prefixes.

**What's the demo footage?**
A CC-BY synthetic open-movie clip (Sintel trailer, Blender Foundation), fetched by
`scripts/fetch_demo_clip.sh` into a gitignored path — never committed, never real
people.

**Can I use it in production?**
It's a sample Backblaze maintains to help developers build on B2. Production use is
possible with caution and your own validation; see [When not to use](#when-not-to-use).

## Maintenance and support

Backblaze maintains this open-source sample to help developers build on B2.
Production use is possible with caution and requires your own validation. Report
repository defects through
[GitHub Issues](https://github.com/backblaze-b2-samples/roboflow-inference-frame-archive/issues);
for B2 account, billing, or API help use [Backblaze Support](https://www.backblaze.com/help).
This sample is not covered by the Backblaze service level agreement.

## Contributing

Start with [AGENTS.md](AGENTS.md) — it's the map. For local commit hooks, follow
[the pre-commit workflow](docs/verification.md#pre-commit).

## License

MIT License — see [LICENSE](LICENSE) for details.
