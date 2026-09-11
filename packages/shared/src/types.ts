export type FileStatus = "uploading" | "complete" | "error";

export interface FileMetadata {
  key: string;
  filename: string;
  folder: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
}

export interface FileMetadataDetail {
  filename: string;
  size_bytes: number;
  size_human: string;
  mime_type: string;
  extension: string;
  md5: string;
  sha256: string;
  uploaded_at: string;
  /** Set when a format-specific extractor was skipped or failed (e.g. an image
   *  above the decompression-bomb decode limit). Core fields stay exact. */
  metadata_warning: string | null;
  // Image-specific
  image_width: number | null;
  image_height: number | null;
  exif: Record<string, string> | null;
  // PDF-specific
  pdf_pages: number | null;
  pdf_author: string | null;
  pdf_title: string | null;
  // Audio/Video
  duration_seconds: number | null;
  codec: string | null;
  bitrate: number | null;
}

export interface FileUploadResponse {
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
  metadata: FileMetadataDetail | null;
}

/** A short-lived presigned PUT the browser uploads a file directly to B2 with.
 *  `headers` are signed into the URL, so the browser must send them verbatim. */
export interface PresignUploadResponse {
  key: string;
  url: string;
  method: string;
  content_type: string;
  headers: Record<string, string>;
  expires_in: number;
}

export interface DailyUploadCount {
  date: string;
  uploads: number;
}

export interface UploadStats {
  total_files: number;
  total_size_bytes: number;
  total_size_human: string;
  uploads_today: number;
  total_downloads: number;
}

// --- Roboflow Frame Archive domain -----------------------------------------

/** Curated Roboflow Inference COCO aliases offered in the camera form. */
export type ModelAlias = "yolov8n-640" | "yolov8s-640" | "yolov8n-seg-640";
/** Discrete confidence thresholds surfaced as a selector (never free text). */
export type ConfidenceThreshold = 0.25 | 0.4 | 0.5 | 0.6 | 0.75;
export type CameraSource = "demo" | "upload";

export interface Camera {
  id: string;
  name: string;
  site: string;
  model_alias: ModelAlias;
  confidence_threshold: ConfidenceThreshold;
  source: CameraSource;
  source_key: string | null;
  created_at: string;
  updated_at: string;
}

/** Create/edit payload — the edit form opens pre-filled with these values. */
export interface CameraInput {
  name: string;
  site: string;
  model_alias: ModelAlias;
  confidence_threshold: ConfidenceThreshold;
  source: CameraSource;
  source_key?: string | null;
}

export type RunStatus = "queued" | "running" | "done" | "failed";

export interface RunRecord {
  id: string;
  camera_id: string;
  status: RunStatus;
  frames_processed: number;
  frames_flagged: number;
  detections_written: number;
  bytes_written: number;
  device: string;
  model_alias: string;
  summary_key: string | null;
  error: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface RunStartResponse {
  run_id: string;
  camera_id: string;
  status: RunStatus;
}

/** One detected object in pixel space (top-left origin, width/height). */
export interface Prediction {
  class_name: string;
  confidence: number;
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface ArchivedFrame {
  frame_key: string;
  prediction_key: string;
  camera_id: string;
  captured_at: string;
  frame_url: string;
  frame_width: number;
  frame_height: number;
  top_class: string | null;
  top_confidence: number | null;
  classes: string[];
  predictions: Prediction[];
}

export interface ClassCount {
  class_name: string;
  count: number;
}

export interface DailyIngest {
  date: string;
  frames: number;
  gigabytes: number;
}

export interface CameraFrameCount {
  camera_id: string;
  camera_name: string;
  frames: number;
}

export interface ArchiveMetrics {
  frames_archived: number;
  predictions_written: number;
  detections_total: number;
  ingest_gigabytes: number;
  active_cameras: number;
  detections_by_class: ClassCount[];
  per_camera: CameraFrameCount[];
  ingest_activity: DailyIngest[];
}
