"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Cctv, Play, Trash2 } from "lucide-react";
import { toast } from "sonner";
import type { Camera } from "@roboflow-inference-frame-archive/shared";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
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
import { useCameras, useDeleteCamera, useStartRun } from "@/lib/queries";
import { formatDate } from "@/lib/utils";

function CameraCard({ camera }: { camera: Camera }) {
  const router = useRouter();
  const startRun = useStartRun(camera.id);
  const deleteCamera = useDeleteCamera();

  const runDetection = () => {
    startRun.mutate(undefined, {
      onSuccess: (run) => {
        toast.success("Detection run started", {
          description: "Watch progress on the camera page.",
        });
        router.push(`/cameras/${camera.id}?run=${run.run_id}`);
      },
      onError: (error) => toast.error("Could not start run", { description: error.message }),
    });
  };

  const remove = () => {
    deleteCamera.mutate(camera.id, {
      onSuccess: () =>
        toast.success("Camera deleted", {
          description: "Its frames, predictions, and summaries were removed from B2.",
        }),
      onError: (error) => toast.error("Delete failed", { description: error.message }),
    });
  };

  return (
    <Card className="card-hover">
      <CardHeader className="flex flex-row items-start justify-between gap-3 border-b border-border py-4 px-5">
        <div className="min-w-0">
          <Link
            href={`/cameras/${camera.id}`}
            className="font-semibold tracking-tight hover:underline underline-offset-4"
          >
            {camera.name}
          </Link>
          <p className="text-xs text-muted-foreground mt-0.5 truncate">{camera.site}</p>
        </div>
        <Badge variant={camera.source === "demo" ? "secondary" : "outline"}>
          {camera.source === "demo" ? "Demo clip" : "Uploaded clip"}
        </Badge>
      </CardHeader>
      <CardContent className="px-5 py-4 flex flex-wrap gap-2 text-xs">
        <Badge variant="outline" className="font-mono">{camera.model_alias}</Badge>
        <Badge variant="outline">conf ≥ {camera.confidence_threshold.toFixed(2)}</Badge>
        <span className="text-muted-foreground ml-auto self-center">
          Added {formatDate(camera.created_at)}
        </span>
      </CardContent>
      <CardFooter className="px-5 py-3 border-t border-border gap-2">
        <Button size="sm" className="h-8" onClick={runDetection} disabled={startRun.isPending}>
          <Play className="h-3.5 w-3.5" />
          {startRun.isPending ? "Starting…" : "Run detection"}
        </Button>
        <Button asChild size="sm" variant="outline" className="h-8">
          <Link href={`/cameras/${camera.id}`}>View</Link>
        </Button>
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button
              size="sm"
              variant="ghost"
              className="h-8 ml-auto text-destructive hover:text-destructive"
              disabled={deleteCamera.isPending}
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete “{camera.name}”?</AlertDialogTitle>
              <AlertDialogDescription>
                This removes the camera and every archived frame, prediction, and
                summary scoped to it from B2. This cannot be undone.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={remove}>Delete camera</AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </CardFooter>
    </Card>
  );
}

export function CamerasList() {
  const { data: cameras = [], isLoading, error, refetch } = useCameras();

  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;

  if (isLoading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-44 w-full" />
        ))}
      </div>
    );
  }

  if (cameras.length === 0) {
    return (
      <EmptyState
        icon={Cctv}
        title="No cameras yet"
        description="Create a camera to run a detection pass and start filling the archive."
        action={
          <Button asChild size="sm">
            <Link href="/cameras/new">New camera</Link>
          </Button>
        }
      />
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {cameras.map((camera) => (
        <CameraCard key={camera.id} camera={camera} />
      ))}
    </div>
  );
}
