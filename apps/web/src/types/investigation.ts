import type { TimelineEventPreview } from "@/types/timeline";

// Temporary frontend representation; generate API types from FastAPI OpenAPI later.
export type InvestigationContextPreview = {
  repository_id: number;
  trigger_event_id: number;
  window_start: string;
  window_end: string;
  events: TimelineEventPreview[];
};
