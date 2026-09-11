"use client";

import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import Link from "next/link";
import type { Camera, CameraInput } from "@roboflow-inference-frame-archive/shared";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { useFiles } from "@/lib/queries";

// Select values are strings; confidence maps back to a number on submit.
const CONFIDENCE_VALUES = ["0.25", "0.4", "0.5", "0.6", "0.75"] as const;

const schema = z
  .object({
    name: z.string().min(1, "Give the camera a name").max(120),
    site: z.string().min(1, "Where is this camera?").max(160),
    model_alias: z.enum(["yolov8n-640", "yolov8s-640", "yolov8n-seg-640"]),
    confidence_threshold: z.enum(CONFIDENCE_VALUES),
    source: z.enum(["demo", "upload"]),
    source_key: z.string().optional().nullable(),
  })
  .refine((v) => v.source !== "upload" || !!v.source_key, {
    message: "Pick an uploaded clip, or use the bundled demo clip",
    path: ["source_key"],
  });

type FormValues = z.infer<typeof schema>;

function toFormValues(camera?: Camera): FormValues {
  return {
    name: camera?.name ?? "",
    site: camera?.site ?? "",
    model_alias: camera?.model_alias ?? "yolov8n-640",
    confidence_threshold: (camera
      ? String(camera.confidence_threshold)
      : "0.4") as (typeof CONFIDENCE_VALUES)[number],
    source: camera?.source ?? "demo",
    source_key: camera?.source_key ?? null,
  };
}

export function CameraForm({
  camera,
  showHints,
  submitLabel,
  pending,
  onSubmit,
}: {
  camera?: Camera;
  /** Create form surfaces safe-default hints; edit form opens pre-filled. */
  showHints: boolean;
  submitLabel: string;
  pending: boolean;
  onSubmit: (input: CameraInput) => void;
}) {
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: toFormValues(camera),
  });
  const source = useWatch({ control: form.control, name: "source" });

  // Uploaded video clips available as an "upload" source (direct-to-B2 objects).
  const { data: files = [] } = useFiles("", 200, { enabled: source === "upload" });
  const clips = files.filter(
    (f) => f.content_type.startsWith("video/") || f.key.startsWith("uploads/")
  );

  const submit = (values: FormValues) => {
    onSubmit({
      name: values.name.trim(),
      site: values.site.trim(),
      model_alias: values.model_alias,
      confidence_threshold: Number(
        values.confidence_threshold
      ) as CameraInput["confidence_threshold"],
      source: values.source,
      source_key: values.source === "upload" ? values.source_key ?? null : null,
    });
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(submit)} className="space-y-6">
        <Card>
          <CardHeader className="border-b border-border py-4 px-5">
            <CardTitle className="card-title">Camera</CardTitle>
          </CardHeader>
          <CardContent className="p-5 space-y-5">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Name</FormLabel>
                  <FormControl>
                    <Input placeholder="Line 3 — QC Camera" {...field} />
                  </FormControl>
                  {showHints && (
                    <FormDescription>
                      A human label for this edge camera.
                    </FormDescription>
                  )}
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="site"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Site / location</FormLabel>
                  <FormControl>
                    <Input placeholder="Plant A / Entrance B" {...field} />
                  </FormControl>
                  {showHints && (
                    <FormDescription>Where the camera is installed.</FormDescription>
                  )}
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="model_alias"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Detection model</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger className="w-full sm:w-80">
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="yolov8n-640">
                        yolov8n-640 — fastest, CPU-friendly
                      </SelectItem>
                      <SelectItem value="yolov8s-640">
                        yolov8s-640 — small, more accurate
                      </SelectItem>
                      <SelectItem value="yolov8n-seg-640">
                        yolov8n-seg-640 — segmentation
                      </SelectItem>
                    </SelectContent>
                  </Select>
                  {showHints && (
                    <FormDescription>
                      Roboflow Inference COCO model. The default runs comfortably
                      on CPU.
                    </FormDescription>
                  )}
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="confidence_threshold"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Confidence threshold</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger className="w-40">
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {CONFIDENCE_VALUES.map((value) => (
                        <SelectItem key={value} value={value}>
                          {Number(value).toFixed(2)}
                          {value === "0.4" ? " (default)" : ""}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {showHints && (
                    <FormDescription>
                      A frame is archived when its top detection clears this score.
                    </FormDescription>
                  )}
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="source"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Source</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger className="w-full sm:w-80">
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="demo">Bundled demo clip (CC-BY)</SelectItem>
                      <SelectItem value="upload">Upload a video</SelectItem>
                    </SelectContent>
                  </Select>
                  {showHints && (
                    <FormDescription>
                      Runs a detection pass over a CC-BY open-movie clip so you can
                      see the archive fill with no footage of your own.
                    </FormDescription>
                  )}
                  <FormMessage />
                </FormItem>
              )}
            />
            {source === "upload" && (
              <FormField
                control={form.control}
                name="source_key"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Uploaded clip</FormLabel>
                    <Select
                      onValueChange={field.onChange}
                      value={field.value ?? undefined}
                    >
                      <FormControl>
                        <SelectTrigger className="w-full sm:w-96">
                          <SelectValue placeholder="Select an uploaded video…" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {clips.map((clip) => (
                          <SelectItem key={clip.key} value={clip.key}>
                            {clip.filename}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormDescription>
                      No clips yet?{" "}
                      <Link href="/upload" className="underline underline-offset-4">
                        Upload one
                      </Link>{" "}
                      first — it uploads directly to B2.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            )}
          </CardContent>
        </Card>

        <div className="flex items-center justify-end gap-2">
          <Button asChild type="button" variant="outline">
            <Link href="/cameras">Cancel</Link>
          </Button>
          <Button type="submit" disabled={pending}>
            {pending ? "Saving…" : submitLabel}
          </Button>
        </div>
      </form>
    </Form>
  );
}
