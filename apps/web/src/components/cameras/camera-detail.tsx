"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, Cpu, Pencil, Play, Trash2 } from "lucide-react";
import { toast } from "sonner";
import type { RunRecord } from "@roboflow-inference-frame-archive/shared";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { DetectionsGallery } from "@/components/archive/detections-gallery";
import { useCamera, useDeleteCamera, useRuns, useStartRun } from "@/lib/queries";
import { formatDate } from "@/lib/utils";

function humanBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  const units = ["KB", "MB", "GB"];
  let value = n / 1024;
  let i = 0;
  while (value >= 1024 && i < units.length - 1) {
    value /= 1024;
    i += 1;
  }
  return `${value.toFixed(1)} ${units[i]}`;
}

const STATUS_VARIANT: Record<RunRecord["status"], "default" | "secondary" | "destructive"> = {
  queued: "secondary",
  running: "default",
  done: "secondary",
  failed: "destructive",
};

function runProgress(run: RunRecord): number {
  if (run.status === "done") return 100;
  if (run.status === "failed") return 100;
  if (run.status === "queued") return 5;
  // Approximate against the default per-run frame cap (150).
  return Math.min(95, Math.round((run.frames_processed / 150) * 100));
}

function RunPanel({ run }: { run: RunRecord }) {
  const active = run.status === "running" || run.status === "queued";
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between border-b border-border py-4 px-5">
        <CardTitle className="card-title">Latest run</CardTitle>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="gap-1 font-mono text-[11px]">
            <Cpu className="h-3 w-3" />
            {run.device.toUpperCase()}
          </Badge>
          <Badge variant={STATUS_VARIANT[run.status]} className="capitalize">
            {run.status}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4 p-5">
        {active && <Progress value={runProgress(run)} />}
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Stat label="Frames processed" value={run.frames_processed} />
          <Stat label="Frames flagged" value={run.frames_flagged} />
          <Stat label="Detections" value={run.detections_written} />
          <Stat label="Archived" value={humanBytes(run.bytes_written)} />
        </div>
        {run.error && (
          <Alert variant="destructive">
            <AlertTitle>Run failed</AlertTitle>
            <AlertDescription>{run.error}</AlertDescription>
          </Alert>
        )}
        <p className="text-xs text-muted-foreground">
          Started {formatDate(run.created_at)} · model {run.model_alias}
        </p>
      </CardContent>
    </Card>
  );
}

function Stat({ label, value }: { label: string; value: number | string }) {
  return (
    <div>
      <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      <div className="stat-value text-xl">{value}</div>
    </div>
  );
}

export function CameraDetail({ id }: { id: string }) {
  const router = useRouter();
  const { data: camera, isLoading, error, refetch } = useCamera(id);
  const { data: runs = [] } = useRuns(id);
  const startRun = useStartRun(id);
  const deleteCamera = useDeleteCamera();

  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (isLoading || !camera) return <Skeleton className="h-96 w-full" />;

  const latest = runs[0];
  const history = runs.slice(1, 6);

  const run = () =>
    startRun.mutate(undefined, {
      onSuccess: () => toast.success("Detection run started"),
      onError: (e) => toast.error("Could not start run", { description: e.message }),
    });

  const remove = () =>
    deleteCamera.mutate(camera.id, {
      onSuccess: () => {
        toast.success("Camera deleted");
        router.push("/cameras");
      },
      onError: (e) => toast.error("Delete failed", { description: e.message }),
    });

  return (
    <div className="space-y-8">
      <div className="animate-fade-in space-y-4 border-b border-border pb-5">
        <Link
          href="/cameras"
          className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-3 w-3" /> Cameras
        </Link>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <h1 className="page-title">{camera.name}</h1>
            <p className="mt-1.5 text-sm text-muted-foreground">{camera.site}</p>
            <div className="mt-3 flex flex-wrap gap-2 text-xs">
              <Badge variant="outline" className="font-mono">{camera.model_alias}</Badge>
              <Badge variant="outline">conf ≥ {camera.confidence_threshold.toFixed(2)}</Badge>
              <Badge variant={camera.source === "demo" ? "secondary" : "outline"}>
                {camera.source === "demo" ? "Demo clip" : "Uploaded clip"}
              </Badge>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <Button size="sm" className="h-8" onClick={run} disabled={startRun.isPending}>
              <Play className="h-3.5 w-3.5" />
              {startRun.isPending ? "Starting…" : "Run detection"}
            </Button>
            <Button asChild size="sm" variant="outline" className="h-8">
              <Link href={`/cameras/${camera.id}/edit`}>
                <Pencil className="h-3.5 w-3.5" /> Edit
              </Link>
            </Button>
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button size="sm" variant="ghost" className="h-8 text-destructive hover:text-destructive">
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Delete “{camera.name}”?</AlertDialogTitle>
                  <AlertDialogDescription>
                    This removes the camera and every archived frame, prediction,
                    and summary scoped to it from B2. This cannot be undone.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction onClick={remove}>Delete camera</AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        </div>
      </div>

      {latest ? (
        <RunPanel run={latest} />
      ) : (
        <Card>
          <CardContent className="py-8 text-center text-sm text-muted-foreground">
            No runs yet. Click <strong>Run detection</strong> to start a pass over
            this camera&apos;s source clip.
          </CardContent>
        </Card>
      )}

      {history.length > 0 && (
        <Card>
          <CardHeader className="border-b border-border py-4 px-5">
            <CardTitle className="card-title">Earlier runs</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <ul className="divide-y divide-border text-sm">
              {history.map((r) => (
                <li key={r.id} className="flex items-center justify-between px-5 py-3">
                  <span className="flex items-center gap-2">
                    <Badge variant={STATUS_VARIANT[r.status]} className="capitalize">
                      {r.status}
                    </Badge>
                    <span className="text-muted-foreground">
                      {r.frames_flagged} flagged · {r.detections_written} detections
                    </span>
                  </span>
                  <span className="text-xs text-muted-foreground">{formatDate(r.created_at)}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      <div>
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
          Archived detections
        </h2>
        <DetectionsGallery cameraId={camera.id} />
      </div>
    </div>
  );
}
