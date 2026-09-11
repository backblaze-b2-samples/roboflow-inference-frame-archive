"use client";

import { useState } from "react";
import Link from "next/link";
import { ScanSearch } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { FrameOverlay } from "@/components/archive/frame-overlay";
import {
  runIsActive,
  useArchiveMetrics,
  useCameras,
  useDetections,
  useRuns,
} from "@/lib/queries";

const ANY = "__any__";

export function DetectionsGallery({
  cameraId,
  showFilters = true,
}: {
  cameraId?: string;
  showFilters?: boolean;
}) {
  const [className, setClassName] = useState<string>(ANY);
  const [selectedCamera, setSelectedCamera] = useState<string>(ANY);
  const [date, setDate] = useState<string>("");

  const effectiveCamera = cameraId ?? (selectedCamera === ANY ? undefined : selectedCamera);
  const filters = {
    cameraId: effectiveCamera,
    className: className === ANY ? undefined : className,
    date: date || undefined,
    limit: 60,
  };

  // Same "is a run active" signal useRuns polls on, scoped to whichever
  // camera this gallery is currently showing (the `cameraId` prop on the
  // camera-detail page, or the camera filter on the global page). Shares
  // camera-detail's own useRuns query/cache when both are mounted, so this
  // costs no extra request there.
  const { data: cameraRuns = [] } = useRuns(effectiveCamera);
  const hasActiveRun = cameraRuns.some((run) => runIsActive(run.status));

  const { data: frames = [], isLoading, error, refetch } = useDetections(filters, {
    pollWhileActive: hasActiveRun,
  });
  const { data: cameras = [] } = useCameras();
  const { data: metrics } = useArchiveMetrics({ pollWhileActive: hasActiveRun });
  const cameraNames = new Map(cameras.map((c) => [c.id, c.name]));
  const classes = metrics?.detections_by_class.map((c) => c.class_name) ?? [];

  // The unfiltered global gallery truncates to `limit`. Reuse the total the
  // dashboard roll-up already carries (`frames_archived`) rather than adding
  // a new count to the API response — only meaningful with no filters
  // active, since that total isn't scoped by camera/class/date.
  const isUnfiltered = !effectiveCamera && className === ANY && !date;
  const isTruncated =
    isUnfiltered &&
    metrics !== undefined &&
    frames.length < metrics.frames_archived;

  return (
    <div className="space-y-5">
      {showFilters && (
        <div className="flex flex-wrap items-center gap-3">
          {!cameraId && (
            <Select value={selectedCamera} onValueChange={setSelectedCamera}>
              <SelectTrigger className="w-52">
                <SelectValue placeholder="All cameras" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ANY}>All cameras</SelectItem>
                {cameras.map((c) => (
                  <SelectItem key={c.id} value={c.id}>
                    {c.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          <Select value={className} onValueChange={setClassName}>
            <SelectTrigger className="w-44">
              <SelectValue placeholder="All classes" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ANY}>All classes</SelectItem>
              {classes.map((name) => (
                <SelectItem key={name} value={name}>
                  {name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="w-40"
          />
          {(className !== ANY || selectedCamera !== ANY || date) && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setClassName(ANY);
                setSelectedCamera(ANY);
                setDate("");
              }}
            >
              Clear
            </Button>
          )}
        </div>
      )}

      {error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="aspect-video w-full" />
          ))}
        </div>
      ) : frames.length === 0 ? (
        <EmptyState
          icon={ScanSearch}
          title="No detections archived yet"
          description="Run a detection pass on a camera to fill the archive with flagged frames."
          action={
            <Button asChild size="sm">
              <Link href="/cameras">Go to cameras</Link>
            </Button>
          }
        />
      ) : (
        <div className="space-y-3">
          {isTruncated && metrics && (
            <p className="text-xs text-muted-foreground">
              Showing {frames.length} of {metrics.frames_archived} detections,
              newest first.
            </p>
          )}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {frames.map((frame) => (
              <Card key={frame.frame_key} className="overflow-hidden">
                <FrameOverlay frame={frame} />
                <CardContent className="flex flex-wrap items-center gap-2 px-4 py-3 text-xs">
                  {frame.top_class && (
                    <Badge variant="secondary">
                      {frame.top_class}
                      {frame.top_confidence !== null
                        ? ` ${(frame.top_confidence * 100).toFixed(0)}%`
                        : ""}
                    </Badge>
                  )}
                  <span className="text-muted-foreground">
                    {frame.predictions.length} detection
                    {frame.predictions.length === 1 ? "" : "s"}
                  </span>
                  {!cameraId && (
                    <span className="ml-auto truncate text-muted-foreground">
                      {cameraNames.get(frame.camera_id) ?? frame.camera_id}
                    </span>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
