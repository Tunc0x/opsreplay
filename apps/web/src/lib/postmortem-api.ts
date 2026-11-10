import "server-only";

import { isPositiveSafeInteger } from "@/lib/ids";
import { isTimelineEventPreview } from "@/lib/timeline-api";
import type { GroundedStatement, PostmortemDraftPreview } from "@/types/postmortem";

export class PostmortemApiError extends Error {
  constructor(
    public readonly kind:
      | "not-found" | "http-error" | "unavailable" | "invalid-response"
      | "invalid-request" | "not-resolved" | "not-configured" | "generation-failed" | "uncertain",
  ) {
    super("The postmortem request could not be completed");
    this.name = "PostmortemApiError";
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNonemptyText(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function isTimestamp(value: unknown): value is string {
  return typeof value === "string" && Number.isFinite(Date.parse(value));
}

function parseStatement(value: unknown, allowedIds: ReadonlySet<number>): GroundedStatement {
  if (
    !isRecord(value) ||
    !isNonemptyText(value.text) ||
    !Array.isArray(value.evidence_event_ids) ||
    value.evidence_event_ids.length === 0 ||
    !value.evidence_event_ids.every(
      (id: unknown) => isPositiveSafeInteger(id) && allowedIds.has(id),
    )
  ) {
    throw new PostmortemApiError("invalid-response");
  }
  return { text: value.text, evidence_event_ids: [...value.evidence_event_ids] };
}

function parseStatements(value: unknown, allowedIds: ReadonlySet<number>): GroundedStatement[] {
  if (!Array.isArray(value) || value.length === 0) {
    throw new PostmortemApiError("invalid-response");
  }
  return value.map((statement: unknown) => parseStatement(statement, allowedIds));
}

function parsePostmortemDraft(payload: unknown, incidentId: number): PostmortemDraftPreview {
  if (
    !isRecord(payload) ||
    !isPositiveSafeInteger(payload.id) ||
    !isPositiveSafeInteger(payload.incident_id) ||
    payload.incident_id !== incidentId ||
    !isPositiveSafeInteger(payload.version) ||
    !isNonemptyText(payload.model) ||
    !isTimestamp(payload.created_at) ||
    !isTimestamp(payload.updated_at) ||
    !Array.isArray(payload.evidence) ||
    !payload.evidence.every(isTimelineEventPreview) ||
    !isRecord(payload.draft) ||
    !Array.isArray(payload.draft.unknowns) ||
    !payload.draft.unknowns.every(isNonemptyText)
  ) {
    throw new PostmortemApiError("invalid-response");
  }

  const evidence = payload.evidence.map(({ id, source, event_type, summary, observed_at }) => ({
    id, source, event_type, summary, observed_at,
  }));
  const allowedIds = new Set(evidence.map((event) => event.id));
  // Each evidence anchor must identify exactly one event.
  if (allowedIds.size !== evidence.length) throw new PostmortemApiError("invalid-response");

  const content = payload.draft;
  return {
    id: payload.id,
    incident_id: payload.incident_id,
    version: payload.version,
    model: payload.model,
    created_at: payload.created_at,
    updated_at: payload.updated_at,
    evidence,
    draft: {
      summary: parseStatements(content.summary, allowedIds),
      timeline: parseStatements(content.timeline, allowedIds),
      impact: content.impact === null ? null : parseStatement(content.impact, allowedIds),
      root_cause: content.root_cause === null ? null : parseStatement(content.root_cause, allowedIds),
      resolution: content.resolution === null ? null : parseStatement(content.resolution, allowedIds),
      unknowns: [...payload.draft.unknowns],
    },
  };
}

export async function fetchPostmortemDraft(
  organizationId: number,
  repositoryId: number,
  incidentId: number,
): Promise<PostmortemDraftPreview> {
  const apiBaseUrl = process.env.OPSREPLAY_API_BASE_URL?.trim();
  if (!apiBaseUrl) throw new PostmortemApiError("unavailable");

  const url = `${apiBaseUrl.replace(/\/+$/, "")}/organizations/${organizationId}/repositories/${repositoryId}/incidents/${incidentId}/postmortem-draft`;
  let response: Response;
  try {
    response = await fetch(url, {
      method: "GET",
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.timeout(10_000),
    });
  } catch {
    throw new PostmortemApiError("unavailable");
  }
  if (response.status === 404) throw new PostmortemApiError("not-found");
  if (response.status !== 200) throw new PostmortemApiError("http-error");

  let payload: unknown;
  try {
    payload = await response.json();
  } catch (error) {
    throw new PostmortemApiError(
      error instanceof SyntaxError ? "invalid-response" : "unavailable",
    );
  }
  return parsePostmortemDraft(payload, incidentId);
}

export async function generatePostmortemDraft(
  organizationId: number,
  repositoryId: number,
  incidentId: number,
): Promise<PostmortemDraftPreview> {
  if (![organizationId, repositoryId, incidentId].every(isPositiveSafeInteger)) {
    throw new PostmortemApiError("invalid-request");
  }
  const apiBaseUrl = process.env.OPSREPLAY_API_BASE_URL?.trim();
  if (!apiBaseUrl) throw new PostmortemApiError("unavailable");

  const url = `${apiBaseUrl.replace(/\/+$/, "")}/organizations/${organizationId}/repositories/${repositoryId}/incidents/${incidentId}/postmortem-draft`;
  let response: Response;
  try {
    response = await fetch(url, {
      method: "POST",
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.timeout(120_000),
    });
  } catch {
    // A timeout or lost response does not establish whether the draft was saved.
    throw new PostmortemApiError("uncertain");
  }
  if (response.status === 404) throw new PostmortemApiError("not-found");
  if (response.status === 409) throw new PostmortemApiError("not-resolved");
  if (response.status === 503) throw new PostmortemApiError("not-configured");
  if (response.status === 502) throw new PostmortemApiError("generation-failed");
  if (response.status !== 200) throw new PostmortemApiError("http-error");

  try {
    const payload: unknown = await response.json();
    return parsePostmortemDraft(payload, incidentId);
  } catch {
    // An unreadable 200 response cannot undo a possibly committed draft.
    throw new PostmortemApiError("uncertain");
  }
}
