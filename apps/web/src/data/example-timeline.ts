import type { TimelineEventPreview } from "@/types/timeline";

// Fictional examples only; these events were not retrieved from the backend.
export const exampleTimelineEvents: TimelineEventPreview[] = [
  {
    id: 101,
    source: "github",
    event_type: "push",
    summary: "Push to refs/heads/main",
    observed_at: "2026-09-20T09:15:00Z",
  },
  {
    id: 102,
    source: "github",
    event_type: "deployment_status",
    summary: "Deployment to production: success",
    observed_at: "2026-09-20T09:24:00Z",
  },
  {
    id: 103,
    source: "alert",
    event_type: "alert",
    summary: "CRITICAL: Elevated error rate in payment service",
    observed_at: "2026-09-20T09:32:00Z",
  },
];
