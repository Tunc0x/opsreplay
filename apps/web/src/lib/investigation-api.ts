import "server-only";

import { isTimelineEventPreview } from "@/lib/timeline-api";
import type { InvestigationContextPreview } from "@/types/investigation";

export class InvestigationApiError extends Error {
  constructor(
    public readonly kind:
      | "not-eligible"
      | "not-found"
      | "unavailable"
      | "invalid-response"
      | "http-error",
  ) {
    super("Investigation context could not be loaded");
    this.name = "InvestigationApiError";
  }
}

export async function fetchInvestigationContext(
  organizationId: number,
  repositoryId: number,
  triggerEventId: number,
): Promise<InvestigationContextPreview> {
  const apiBaseUrl = process.env.OPSREPLAY_API_BASE_URL?.trim();
  if (!apiBaseUrl) {
    throw new InvestigationApiError("unavailable");
  }

  const url =
    `${apiBaseUrl.replace(/\/+$/, "")}/organizations/${organizationId}` +
    `/repositories/${repositoryId}/timeline/${triggerEventId}/context`;

  let response: Response;
  try {
    response = await fetch(url, {
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    });
  } catch {
    throw new InvestigationApiError("unavailable");
  }

  if (response.status === 400) {
    throw new InvestigationApiError("not-eligible");
  }
  if (response.status === 404) {
    throw new InvestigationApiError("not-found");
  }
  if (!response.ok) {
    throw new InvestigationApiError("http-error");
  }

  let payload: unknown;
  try {
    payload = await response.json();
  } catch (error) {
    throw new InvestigationApiError(
      error instanceof SyntaxError ? "invalid-response" : "unavailable",
    );
  }

  if (
    typeof payload !== "object" ||
    payload === null ||
    !("repository_id" in payload) ||
    payload.repository_id !== repositoryId ||
    !("trigger_event_id" in payload) ||
    payload.trigger_event_id !== triggerEventId ||
    !("window_start" in payload) ||
    typeof payload.window_start !== "string" ||
    !Number.isFinite(Date.parse(payload.window_start)) ||
    !("window_end" in payload) ||
    typeof payload.window_end !== "string" ||
    !Number.isFinite(Date.parse(payload.window_end)) ||
    Date.parse(payload.window_start) > Date.parse(payload.window_end) ||
    !("events" in payload) ||
    !Array.isArray(payload.events) ||
    !payload.events.every(isTimelineEventPreview)
  ) {
    throw new InvestigationApiError("invalid-response");
  }

  return {
    repository_id: payload.repository_id,
    trigger_event_id: payload.trigger_event_id,
    window_start: payload.window_start,
    window_end: payload.window_end,
    events: payload.events.map(
      ({ id, source, event_type, summary, observed_at }) => ({
        id,
        source,
        event_type,
        summary,
        observed_at,
      }),
    ),
  };
}
