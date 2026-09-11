import Link from "next/link";
import { Cctv } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ArchiveStatsCards } from "@/components/dashboard/stats-cards";
import { DetectionBreakdown } from "@/components/dashboard/recent-uploads-table";
import { IngestChart } from "@/components/dashboard/upload-chart";

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-1.5">
            Edge inference archive on Backblaze B2 — frames, predictions, and
            summaries across all cameras.
          </p>
        </div>
        <Button asChild size="sm" className="h-8">
          <Link href="/cameras">
            <Cctv className="h-3.5 w-3.5" />
            Cameras
          </Link>
        </Button>
      </div>
      <ArchiveStatsCards />
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="animate-fade-in-up stagger-3">
          <IngestChart />
        </div>
        <div className="animate-fade-in-up stagger-4">
          <DetectionBreakdown />
        </div>
      </div>
    </div>
  );
}
