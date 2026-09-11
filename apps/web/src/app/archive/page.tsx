import { DetectionsGallery } from "@/components/archive/detections-gallery";

export default function ArchivePage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Detections</h1>
        <p className="mt-1.5 max-w-prose text-sm text-muted-foreground">
          Flagged frames archived from your cameras, with detection boxes
          overlaid. Filter by camera, class, or capture date. This gallery is
          scoped to this app&apos;s own output — browse the whole bucket under
          Files.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <DetectionsGallery />
      </div>
    </div>
  );
}
