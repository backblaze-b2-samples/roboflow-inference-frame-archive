"use client";

import { useRouter } from "next/navigation";
import { toast } from "sonner";
import type { CameraInput } from "@roboflow-inference-frame-archive/shared";

import { CameraForm } from "@/components/cameras/camera-form";
import { useCreateCamera } from "@/lib/queries";

export default function NewCameraPage() {
  const router = useRouter();
  const create = useCreateCamera();

  const onSubmit = (input: CameraInput) => {
    create.mutate(input, {
      onSuccess: (camera) => {
        toast.success("Camera created");
        router.push(`/cameras/${camera.id}`);
      },
      onError: (error) => toast.error("Could not create camera", { description: error.message }),
    });
  };

  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">New camera</h1>
        <p className="mt-1.5 max-w-prose text-sm text-muted-foreground">
          Defaults are tuned for a fast first run: the bundled CC-BY demo clip and
          a CPU-friendly model, so you can see the archive fill without footage of
          your own.
        </p>
      </div>
      <div className="max-w-2xl animate-fade-in-up stagger-2">
        <CameraForm
          showHints
          submitLabel="Create camera"
          pending={create.isPending}
          onSubmit={onSubmit}
        />
      </div>
    </div>
  );
}
