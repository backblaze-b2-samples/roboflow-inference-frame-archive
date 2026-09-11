"use client";

import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import type { CameraInput } from "@roboflow-inference-frame-archive/shared";

import { CameraForm } from "@/components/cameras/camera-form";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useCamera, useUpdateCamera } from "@/lib/queries";

export default function EditCameraPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const router = useRouter();
  const { data: camera, isLoading, error, refetch } = useCamera(id);
  const update = useUpdateCamera(id);

  const onSubmit = (input: CameraInput) => {
    update.mutate(input, {
      onSuccess: () => {
        toast.success("Camera updated");
        router.push(`/cameras/${id}`);
      },
      onError: (err) => toast.error("Could not update camera", { description: err.message }),
    });
  };

  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Edit camera</h1>
        <p className="mt-1.5 max-w-prose text-sm text-muted-foreground">
          The form opens pre-filled with this camera&apos;s current settings.
        </p>
      </div>
      <div className="max-w-2xl animate-fade-in-up stagger-2">
        {error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : isLoading || !camera ? (
          <Skeleton className="h-96 w-full" />
        ) : (
          <CameraForm
            camera={camera}
            showHints={false}
            submitLabel="Save changes"
            pending={update.isPending}
            onSubmit={onSubmit}
          />
        )}
      </div>
    </div>
  );
}
