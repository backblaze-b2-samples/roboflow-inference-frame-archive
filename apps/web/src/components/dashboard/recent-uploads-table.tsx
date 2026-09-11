"use client";

import Link from "next/link";
import { ArrowRight, Boxes } from "lucide-react";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { useArchiveMetrics } from "@/lib/queries";

export function DetectionBreakdown() {
  const { data: metrics, isLoading, error, refetch } = useArchiveMetrics();
  const byClass = metrics?.detections_by_class ?? [];
  const perCamera = metrics?.per_camera ?? [];

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Detection Breakdown</CardTitle>
        <CardAction className="self-center">
          <Link
            href="/archive"
            className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            View archive
            <ArrowRight className="h-3 w-3" />
          </Link>
        </CardAction>
      </CardHeader>
      <CardContent className="p-0">
        {isLoading ? (
          <div className="space-y-3 p-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-8 w-full" />
            ))}
          </div>
        ) : error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : byClass.length === 0 ? (
          <EmptyState
            icon={Boxes}
            title="No detections yet"
            description="Run a detection pass on a camera to populate this breakdown."
          />
        ) : (
          <div className="divide-y divide-border">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/40 hover:bg-muted/40">
                  <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Class
                  </TableHead>
                  <TableHead className="w-24 text-right text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Detections
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {byClass.map((row) => (
                  <TableRow key={row.class_name} className="table-row-hover">
                    <TableCell className="font-medium">
                      <Badge variant="secondary">{row.class_name}</Badge>
                    </TableCell>
                    <TableCell className="text-right font-mono tabular-nums">
                      {row.count}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            {perCamera.length > 0 && (
              <div className="px-5 py-4">
                <div className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Frames by camera
                </div>
                <ul className="space-y-1.5 text-sm">
                  {perCamera.map((c) => (
                    <li key={c.camera_id} className="flex items-center justify-between">
                      <span className="truncate">{c.camera_name}</span>
                      <span className="font-mono tabular-nums text-muted-foreground">
                        {c.frames}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
