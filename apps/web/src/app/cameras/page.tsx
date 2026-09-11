import Link from "next/link";
import { Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { CamerasList } from "@/components/cameras/cameras-list";

export default function CamerasPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in flex flex-wrap items-start justify-between gap-4 border-b border-border pb-5">
        <div className="min-w-0">
          <h1 className="page-title">Cameras</h1>
          <p className="mt-1.5 max-w-prose text-sm text-muted-foreground">
            Configure edge cameras, run Roboflow Inference detection passes, and
            archive flagged frames to Backblaze B2.
          </p>
        </div>
        <Button asChild size="sm" className="h-8 shrink-0">
          <Link href="/cameras/new">
            <Plus className="h-3.5 w-3.5" />
            New camera
          </Link>
        </Button>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <CamerasList />
      </div>
    </div>
  );
}
