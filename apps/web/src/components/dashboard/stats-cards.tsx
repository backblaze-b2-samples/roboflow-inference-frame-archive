"use client";

import { Images, ScanSearch, HardDrive, Cctv } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { LoadingNotice } from "@/components/common/loading-notice";
import { useArchiveMetrics } from "@/lib/queries";

export function ArchiveStatsCards() {
  const { data: metrics, isLoading, error, refetch } = useArchiveMetrics();

  if (error) {
    return (
      <Card>
        <CardContent className="p-0">
          <ErrorState error={error} onRetry={() => refetch()} />
        </CardContent>
      </Card>
    );
  }

  const cards = [
    { title: "Frames Archived", value: metrics?.frames_archived ?? 0, icon: Images },
    { title: "Detections", value: metrics?.detections_total ?? 0, icon: ScanSearch },
    {
      title: "Ingest Volume",
      value: `${(metrics?.ingest_gigabytes ?? 0).toFixed(3)} GB`,
      icon: HardDrive,
    },
    { title: "Active Cameras", value: metrics?.active_cameras ?? 0, icon: Cctv },
  ];

  return (
    <>
      {isLoading && <LoadingNotice className="mb-3" subject="archive metrics" />}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map((card, i) => (
          <Card
            key={card.title}
            className={`card-hover animate-fade-in-up stagger-${i + 1}`}
          >
            <CardHeader className="flex flex-row items-center justify-between pt-4 pb-2 px-4 space-y-0">
              <CardTitle className="text-xs font-semibold text-muted-foreground">
                {card.title}
              </CardTitle>
              <div className="stat-icon-wrap">
                <card.icon className="h-4 w-4" />
              </div>
            </CardHeader>
            <CardContent className="pb-5 px-4">
              {isLoading ? (
                <Skeleton className="h-8 w-24" />
              ) : (
                <div className="stat-value">{card.value}</div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </>
  );
}
