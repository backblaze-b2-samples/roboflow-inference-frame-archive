<!-- last_verified: 2026-08-06 -->
# App Workflows

User journeys inside the application. The primary journey is
**camera → run → archive**.

## Configure a Camera

- User navigates to `/cameras` and clicks **New camera**
- The form uses selectors for the finite-value fields (model, confidence, source) and free text for name and site. On create it surfaces safe defaults as placeholder/description hints: model pre-selected `yolov8n-640` (fastest, CPU-friendly), confidence `0.40`, source "Bundled demo clip (CC-BY)"
- Choosing source "Upload a video" reveals a selector of clips already uploaded to B2 (via `/upload`), or a link to upload one first
- Submitting `POST /cameras` writes `cameras/<id>.json` to the bucket (there is no database) and routes to the camera detail page
- Editing at `/cameras/[id]/edit` opens the same form pre-filled with the camera's real values (no default hints)
- Deleting (from the list or detail, behind a confirm dialog) removes the camera and every frame/prediction/summary/run scoped to it — prefix-scoped, never a bucket-wide wipe
- See: [Cameras](features/cameras.md)

## Run a Detection Pass

- On a camera's card or its detail page, the user clicks **Run detection**
- `POST /cameras/{id}/runs` returns immediately (202) with a run id; the pass executes on a background worker thread
- The engine auto-detects the device (CUDA → CPU; CPU on Apple Silicon) and runs Roboflow Inference locally over sampled frames of the source clip
- Every frame whose top detection clears the camera's confidence threshold is written to B2 as a JPEG frame + a prediction JSON; the whole run also writes a Parquet summary
- The detail page polls the run (TanStack Query `refetchInterval`) and shows live counts — frames processed/flagged, detections, bytes archived, device — until it reaches `done` or `failed`
- If the engine or the demo clip is missing, the run is recorded as `failed` with an actionable message; the request never 500s
- See: [Detection run](features/detection-run.md)

## Browse Detections

- User navigates to `/archive` (Detections)
- A gallery of flagged frames renders, each served by a short-lived presigned GET with its bounding boxes and labels overlaid in the browser
- Filters scope the gallery by camera, detected class, and capture date; the same gallery appears scoped to one camera on its detail page
- This gallery is deliberately scoped to the app's own output prefixes — the whole bucket stays browsable under Files
- See: [Frame archive](features/frame-archive.md)

## Upload Files

- User navigates to `/upload`
- Drops or selects files in the dropzone
- Client validates file size (max 100MB) and type
- Files upload **directly from the browser to B2** (a presigned PUT). A determinate progress bar tracks the bytes leaving the browser; once they are all sent the row switches to "Verifying upload..." with an *indeterminate* sweeping bar while the API HEADs and magic-byte-sniffs the stored object. That phase has no percentage to report, and a bar parked at a full 100% read as finished-but-stuck
- On success: toast notification, green checkmark, and a "View in Files" link through to the browser
- On failure: red status icon with error message
- User can clear completed uploads
- The queue lives in an app-wide provider: navigating to another page keeps the upload running, shows an "Uploading N files" indicator in the header, and keeps the duplicate-upload guard armed
- Reloading or closing mid-upload asks for confirmation first; if the upload dies anyway, the next load says which file didn't finish
- See: [File Upload](features/file-upload.md)

## Browse and Manage Files

- User navigates to `/files`
- Page loads the 100 most recent objects from the API (sorted most recent first). While it loads, the page says so on screen and escalates the wording if the wait runs long — a full bucket listing measured 2.8s-21s cold
- If that limit was hit, a notice states how many objects the bucket actually holds — the page never claims to show everything
- Files displayed in tree view with folders and type-specific icons
- Folders auto-expand on load until the *majority* of the listed files are reachable without clicking, so the page's own "click a file" instruction is always actionable. Stopping at the first visible file was not enough: one stray top-level object left the other 99 sealed in collapsed folders while the page claimed to show 100
- Clicking a file row opens its preview; the per-row actions menu (preview / download / delete) is always visible, on every viewport
- Arriving at `/files?preview=<key>` expands that file's folders and opens its preview directly. This is how the ⌘K palette and the dashboard's recent-uploads rows hand off a *specific* file; the param is consumed on arrival so it doesn't re-fire later
- **Preview**: opens dialog with image/PDF preview + metadata panel, and the file's Download / Delete actions — the advertised "click a file" path offers everything the row menu does. The loading state holds until the media paints; a failure offers "Open in a new tab". The preview URL is signed with `Content-Disposition: inline` so PDFs render in place
- **Download**: shows a pending state on the row plus a toast while the presigned URL is fetched, then starts the download via an anchor click (which, unlike a popup, still works if the click's user activation expired during a slow presign). Failures are reported; the click can never silently do nothing
- **Delete**: the confirmation dialog stays open showing "Deleting..." until the request settles, then the row disappears with the toast (optimistic cache update) and the list reconciles with the server. The dialog is held deliberately — Radix closes on action click by default, which dismissed the only pending state and left the row looking untouched while the delete was still in flight
- Empty bucket shows "No files found" with upload prompt
- See: [File Browser](features/file-browser.md)

## View Dashboard

- User navigates to `/` (home)
- One `GET /archive/metrics` call reads every per-run Parquet summary and rolls it up (the aggregator → dashboard path)
- While metrics load, the page states it in words above the cards rather than showing silent skeletons
- Stat cards show: frames archived, detections, ingest volume (GB), active cameras
- The ingest chart shows frames archived per day with total GB in the corner
- The detection breakdown lists detections by class and frames by camera, with a link through to the archive
- Empty state: "No ingest yet" / "No detections yet" messages
- See: [Dashboard](features/dashboard.md)

## Change Preferences

- User navigates to `/settings`
- A banner at the top states that the page is mostly a demonstration: only Theme is wired up for real, the rest showcases what a settings page can look like when you adapt the kit
- **Theme** (real): editing it and saving applies it immediately and persists it (`next-themes`), and the header's theme toggle drives the same state
- **Profile and preference fields** (demo): Display name, Bio, Default file view (Tree/List/Grid), Email me on every upload, Warn me when approaching quota + threshold. Each is labelled "Demo field", persists to `localStorage` only, and drives no behaviour — there is no account system, mailer, quota banner, activity log, or List/Grid view behind them yet
- Saving reports honestly: a success toast that separates the real theme change from the locally-stored demo values, or a warning toast if the browser blocked storage (theme still changes). It never claims a save that did not happen — the original page toasted "Settings saved" for fields that changed nothing
- Danger Zone actions are a demo — no real delete runs
- See: [Settings](features/settings.md)
