import type { TimelineEventPreview } from "@/types/timeline";

// Temporary frontend types; generate API types from FastAPI OpenAPI later.
export type GroundedStatement = {
  text: string;
  evidence_event_ids: number[];
};

export type PostmortemDraftContent = {
  summary: GroundedStatement[];
  timeline: GroundedStatement[];
  impact: GroundedStatement | null;
  root_cause: GroundedStatement | null;
  resolution: GroundedStatement | null;
  unknowns: string[];
};

export type PostmortemDraftPreview = {
  id: number;
  incident_id: number;
  version: number;
  model: string;
  draft: PostmortemDraftContent;
  evidence: TimelineEventPreview[];
  created_at: string;
  updated_at: string;
};
