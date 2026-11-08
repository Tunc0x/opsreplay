import type { InvestigationContextPreview } from "@/types/investigation";

// Temporary frontend fields from IncidentRead; generate API types from OpenAPI later.
export type IncidentPreview = {
  id: number;
  repository_id: number;
  trigger_timeline_event_id: number;
  lookback_minutes: number;
  lookahead_minutes: number;
  status: "open" | "resolved";
  resolved_at: string | null;
  created_at: string;
  context: InvestigationContextPreview;
};
