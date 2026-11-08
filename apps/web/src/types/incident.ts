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

// Display fields from IncidentSummaryRead; generate API types from OpenAPI later.
export type IncidentSummaryPreview = Pick<
  IncidentPreview,
  "id" | "repository_id" | "trigger_timeline_event_id" | "status" | "created_at"
> & {
  title: string;
  repository_name: string;
  alert_observed_at: string;
};
