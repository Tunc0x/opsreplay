// Temporary display-only fields selected from TimelineEventRead.
// Future API response types should be generated from FastAPI OpenAPI.
export type TimelineEventPreview = {
  id: number;
  source: string;
  event_type: string;
  summary: string;
  observed_at: string;
};
