import "server-only";

import { isPositiveSafeInteger } from "@/lib/ids";
import { parseInvestigationContext } from "@/lib/investigation-api";
import type { IncidentPreview } from "@/types/incident";

export class IncidentApiError extends Error {
  constructor(
    public readonly kind:
      | "not-eligible"
      | "not-found"
      | "conflict"
      | "invalid-request"
      | "unavailable"
      | "invalid-response"
      | "http-error"
      | "uncertain",
  ) {
    super("The incident request could not be completed");
    this.name = "IncidentApiError";
  }
}

function isWindowMinutes(value: unknown): value is number {
  return (
    typeof value === "number" &&
    Number.isInteger(value) &&
    value >= 0 && value <= 1440
  );
}

function parseIncident(payload: unknown, repositoryId: number): IncidentPreview {
  if (
    typeof payload !== "object" ||
    payload === null ||
    !("id" in payload) ||
    !isPositiveSafeInteger(payload.id) ||
    !("repository_id" in payload) ||
    payload.repository_id !== repositoryId ||
    !("trigger_timeline_event_id" in payload) ||
    !isPositiveSafeInteger(payload.trigger_timeline_event_id) ||
    !("lookback_minutes" in payload) ||
    !isWindowMinutes(payload.lookback_minutes) ||
    !("lookahead_minutes" in payload) ||
    !isWindowMinutes(payload.lookahead_minutes) ||
    !("status" in payload) ||
    (payload.status !== "open" && payload.status !== "resolved") ||
    !("resolved_at" in payload) ||
    !(payload.resolved_at === null || (typeof payload.resolved_at === "string" && Number.isFinite(Date.parse(payload.resolved_at)))) ||
    (payload.status === "open" && payload.resolved_at !== null) ||
    (payload.status === "resolved" && payload.resolved_at === null) ||
    !("created_at" in payload) ||
    typeof payload.created_at !== "string" ||
    !Number.isFinite(Date.parse(payload.created_at)) ||
    !("context" in payload)
  ) {
    throw new IncidentApiError("invalid-response");
  }

  let context: IncidentPreview["context"];
  try {
    context = parseInvestigationContext(
      payload.context,
      repositoryId,
      payload.trigger_timeline_event_id,
    );
  } catch {
    throw new IncidentApiError("invalid-response");
  }

  return {
    id: payload.id,
    repository_id: payload.repository_id,
    trigger_timeline_event_id: payload.trigger_timeline_event_id,
    lookback_minutes: payload.lookback_minutes,
    lookahead_minutes: payload.lookahead_minutes,
    status: payload.status,
    resolved_at: payload.resolved_at,
    created_at: payload.created_at,
    context,
  };
}

export async function createIncident(
  organizationId: number,
  repositoryId: number,
  triggerEventId: number,
): Promise<IncidentPreview> {
  const apiBaseUrl = process.env.OPSREPLAY_API_BASE_URL?.trim();
  if (!apiBaseUrl) {
    throw new IncidentApiError("unavailable");
  }

  const url = `${apiBaseUrl.replace(/\/+$/, "")}/organizations/${organizationId}/repositories/${repositoryId}/incidents`;
  let response: Response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        trigger_timeline_event_id: triggerEventId,
        lookback_minutes: 30,
        lookahead_minutes: 30,
      }),
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.timeout(10_000),
    });
  } catch {
    // The write may have committed even if its response never reached us.
    throw new IncidentApiError("uncertain");
  }

  if (response.status === 400) throw new IncidentApiError("not-eligible");
  if (response.status === 404) throw new IncidentApiError("not-found");
  if (response.status === 409) throw new IncidentApiError("conflict");
  if (response.status === 422) throw new IncidentApiError("invalid-request");
  if (response.status !== 201) throw new IncidentApiError("uncertain");

  try {
    const payload: unknown = await response.json();
    const incident = parseIncident(payload, repositoryId);
    if (
      incident.trigger_timeline_event_id !== triggerEventId ||
      incident.lookback_minutes !== 30 ||
      incident.lookahead_minutes !== 30 ||
      incident.status !== "open" ||
      incident.resolved_at !== null
    ) {
      throw new IncidentApiError("invalid-response");
    }
    return incident;
  } catch {
    // A 201 with an unreadable or unexpected body does not undo the write.
    throw new IncidentApiError("uncertain");
  }
}

export async function fetchIncident(
  organizationId: number,
  repositoryId: number,
  incidentId: number,
): Promise<IncidentPreview> {
  const apiBaseUrl = process.env.OPSREPLAY_API_BASE_URL?.trim();
  if (!apiBaseUrl) throw new IncidentApiError("unavailable");

  const url = `${apiBaseUrl.replace(/\/+$/, "")}/organizations/${organizationId}/repositories/${repositoryId}/incidents/${incidentId}`;
  let response: Response;
  try {
    response = await fetch(url, {
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    });
  } catch {
    throw new IncidentApiError("unavailable");
  }
  if (response.status === 404) throw new IncidentApiError("not-found");
  if (!response.ok) throw new IncidentApiError("http-error");

  let payload: unknown;
  try {
    payload = await response.json();
  } catch (error) {
    throw new IncidentApiError(
      error instanceof SyntaxError ? "invalid-response" : "unavailable",
    );
  }
  const incident = parseIncident(payload, repositoryId);
  if (incident.id !== incidentId) throw new IncidentApiError("invalid-response");
  return incident;
}

export async function resolveIncident(
  organizationId: number,
  repositoryId: number,
  incidentId: number,
): Promise<IncidentPreview> {
  const apiBaseUrl = process.env.OPSREPLAY_API_BASE_URL?.trim();
  if (!apiBaseUrl) throw new IncidentApiError("unavailable");

  const url = `${apiBaseUrl.replace(/\/+$/, "")}/organizations/${organizationId}/repositories/${repositoryId}/incidents/${incidentId}/resolve`;
  let response: Response;
  try {
    response = await fetch(url, {
      method: "POST",
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.timeout(10_000),
    });
  } catch {
    // A lost response does not establish whether the update committed.
    throw new IncidentApiError("uncertain");
  }

  if (response.status === 404) throw new IncidentApiError("not-found");
  if (response.status !== 200) throw new IncidentApiError("http-error");

  let payload: unknown;
  try {
    payload = await response.json();
  } catch (error) {
    throw new IncidentApiError(
      error instanceof SyntaxError ? "invalid-response" : "uncertain",
    );
  }

  const incident = parseIncident(payload, repositoryId);
  if (incident.id !== incidentId || incident.status !== "resolved") {
    throw new IncidentApiError("invalid-response");
  }
  return incident;
}
