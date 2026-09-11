"use client";

import { useParams } from "next/navigation";

import { CameraDetail } from "@/components/cameras/camera-detail";

export default function CameraDetailPage() {
  const params = useParams<{ id: string }>();
  return <CameraDetail id={params.id} />;
}
