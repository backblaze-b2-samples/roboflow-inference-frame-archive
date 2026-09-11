"use client";

import type { ArchivedFrame } from "@roboflow-inference-frame-archive/shared";

/**
 * An archived frame image with its bounding boxes/labels overlaid.
 *
 * Predictions are in the frame's pixel space, so boxes are positioned as
 * percentages of the natural dimensions — they scale with the rendered image at
 * any size without a canvas or a server-side redraw. The frame itself is served
 * by a short-lived presigned GET (`frame.frame_url`).
 */
export function FrameOverlay({
  frame,
  className,
}: {
  frame: ArchivedFrame;
  className?: string;
}) {
  const { frame_width: w, frame_height: h } = frame;
  return (
    <div className={`relative overflow-hidden rounded-md bg-muted ${className ?? ""}`}>
      {/* eslint-disable-next-line @next/next/no-img-element -- presigned B2 URL, not a static asset */}
      <img
        src={frame.frame_url}
        alt={`Frame from camera ${frame.camera_id}`}
        className="block h-auto w-full"
        loading="lazy"
      />
      {frame.predictions.map((p, i) => (
        <div
          key={i}
          className="absolute border-2 border-[var(--brand-b2,#e21e29)]"
          style={{
            left: `${(p.x / w) * 100}%`,
            top: `${(p.y / h) * 100}%`,
            width: `${(p.width / w) * 100}%`,
            height: `${(p.height / h) * 100}%`,
          }}
        >
          <span className="absolute left-0 top-0 -translate-y-full whitespace-nowrap bg-[var(--brand-b2,#e21e29)] px-1 py-0.5 text-[10px] font-medium leading-none text-white">
            {p.class_name} {(p.confidence * 100).toFixed(0)}%
          </span>
        </div>
      ))}
    </div>
  );
}
