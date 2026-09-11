from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- Backblaze B2 (S3-compatible API) ---
    # Standard B2_* names audited by /b2-doctor. The endpoint is derived from the
    # region (see `endpoint_url`) so no region literal is hardcoded in source;
    # set B2_ENDPOINT only to override the derived S3 endpoint for a custom host.
    b2_application_key_id: str = ""
    b2_application_key: str = ""
    b2_bucket_name: str = ""
    b2_region: str = ""
    b2_endpoint: str = ""
    b2_public_url_base: str = ""

    # --- Roboflow Inference (local detection engine) ---
    # OPTIONAL, free-tier. Some `inference` builds fetch pretrained weights from
    # the Roboflow hub on first load and want a free key for that download; the
    # inference itself runs fully on-device. B2 credentials remain the only
    # required keys. Sign up: https://app.roboflow.com/settings/api
    roboflow_api_key: str = ""
    # Default detection model alias (Roboflow Inference COCO detector). Curated
    # aliases are offered in the camera form; this is the create-form default.
    default_model_alias: str = "yolov8n-640"
    default_confidence: float = 0.40

    # Detection-run bounds so a CPU pass over the demo clip stays fast: sample
    # one frame every `frame_sample_stride` decoded frames, cap the whole run at
    # `max_frames_per_run` sampled frames, encode flagged frames at this quality.
    frame_sample_stride: int = 15
    max_frames_per_run: int = 150
    jpeg_quality: int = 85
    # Bundled CC-BY demo clip (fetched by scripts/fetch_demo_clip.sh into a
    # gitignored path; no binary is committed). Relative paths resolve against
    # the repo root. "Bundled demo clip" cameras read from here.
    demo_clip_path: str = ".data/demo-clip.mp4"

    api_port: int = 8000
    # Interactive API docs (/docs, /redoc, /openapi.json). On by default for
    # local dev and exploration; set false to hide the full API surface in
    # production.
    enable_docs: bool = True
    # Explicit allowlist by default — covers Next on :3000 and the fallback
    # :3001 it picks if 3000 is busy. Production deploys should override with the
    # exact frontend origin.
    api_cors_origins: str = "http://localhost:3000,http://localhost:3001"
    # Optional dev-only escape hatch: a regex that matches additional allowed
    # origins. Empty by default. NEVER ship this to production.
    api_cors_origin_regex: str = ""

    # Upload limits (bring-your-own source clip via the direct-to-B2 path).
    max_file_size: int = 512 * 1024 * 1024  # 512MB — source video clips are large
    # TTL for the presigned PUT the browser uploads directly to B2 with.
    presign_upload_expiry_seconds: int = 900  # 15 minutes
    # TTL for presigned GETs that serve archived frames/predictions to the UI.
    presign_get_expiry_seconds: int = 600  # 10 minutes

    # Optional confinement for key-addressed reads/deletes. Empty by default so
    # the by-key routes accept any key shape.
    allowed_key_prefix: str = ""

    # Full-bucket listing cache (repo/list_cache.py) shared by /files and the
    # dashboard. Entries older than the TTL are served immediately while a
    # background thread refreshes them (stale-while-revalidate). Uploads and
    # deletes invalidate the cache outright.
    list_cache_ttl_seconds: float = 300.0
    warm_list_cache_on_startup: bool = True

    # Rate limiting (per client IP, per 60s window). In-process per replica.
    rate_limit_per_minute: int = 120
    rate_limit_write_per_minute: int = 60

    # Small durable counters (downloads, etc). Relative paths resolve against the
    # repo root (see repo/counter.py). Kept OUTSIDE services/api/ so writes never
    # land in uvicorn --reload's watch tree.
    download_count_file: str = ".data/download_count.json"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def endpoint_url(self) -> str:
        """S3 endpoint for boto3.

        Derived from `b2_region` so no region literal lives in source. An
        explicit `B2_ENDPOINT` override wins (custom host / non-standard region).
        """
        if self.b2_endpoint:
            return self.b2_endpoint
        return f"https://s3.{self.b2_region}.backblazeb2.com"

    @property
    def cors_origins(self) -> list[str]:
        # Drop empties so a trailing comma or API_CORS_ORIGINS="" doesn't yield a
        # stray "" origin.
        return [o.strip() for o in self.api_cors_origins.split(",") if o.strip()]


settings = Settings()
