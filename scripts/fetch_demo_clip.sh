#!/usr/bin/env bash
# Fetch the bundled CC-BY demo clip a "demo" camera runs detection over.
#
# Source: the Sintel trailer (Blender Foundation, durian project) — CC-BY 3.0,
# fully synthetic/CG footage (no real people). It is downloaded into a gitignored
# path and NEVER committed to the repo. Override the URL/target with DEMO_CLIP_URL
# / DEMO_CLIP_PATH if you prefer another verified-license clip.
#
# Usage: bash scripts/fetch_demo_clip.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

DEMO_CLIP_URL="${DEMO_CLIP_URL:-https://download.blender.org/durian/trailer/sintel_trailer-720p.mp4}"
DEMO_CLIP_PATH="${DEMO_CLIP_PATH:-$REPO_ROOT/.data/demo-clip.mp4}"

mkdir -p "$(dirname "$DEMO_CLIP_PATH")"

if [ -s "$DEMO_CLIP_PATH" ]; then
  echo "Demo clip already present: $DEMO_CLIP_PATH"
  exit 0
fi

echo "Downloading CC-BY demo clip (Sintel trailer, Blender Foundation)…"
if command -v curl >/dev/null 2>&1; then
  curl -fL --retry 3 -o "$DEMO_CLIP_PATH" "$DEMO_CLIP_URL"
elif command -v wget >/dev/null 2>&1; then
  wget -O "$DEMO_CLIP_PATH" "$DEMO_CLIP_URL"
else
  echo "Need curl or wget to download the demo clip." >&2
  exit 1
fi

if [ ! -s "$DEMO_CLIP_PATH" ]; then
  echo "Download produced an empty file: $DEMO_CLIP_PATH" >&2
  exit 1
fi

echo "Saved demo clip to $DEMO_CLIP_PATH (gitignored; do not commit)."
echo "License: Sintel © Blender Foundation, CC-BY 3.0 — https://durian.blender.org"
