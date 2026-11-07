// communicates with FastAPI and makes sure the returned data is valid.

import "server-only";

import type { TimelineEventPreview } from "@/types/timeline";

export class TimelineApiError extends Error {
  constructor(
    public readonly kind: "not-found" | "unavailable" | "invalid-response",
  ) {
    super(
      kind === "not-found"
        ? "Organization or repository not found"
        : kind === "invalid-response"
          ? "Invalid timeline data"
          : "Repository timeline is unavailable",
    );
    this.name = "TimelineApiError";
  }
}

// validate the backend's data
export function isTimelineEventPreview(
  value: unknown,
): value is TimelineEventPreview {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  return (
    "id" in value &&
    typeof value.id === "number" &&
    Number.isSafeInteger(value.id) &&
    value.id > 0 &&
    "source" in value &&
    typeof value.source === "string" &&
    "event_type" in value &&
    typeof value.event_type === "string" &&
    "summary" in value &&
    typeof value.summary === "string" &&
    "observed_at" in value &&
    typeof value.observed_at === "string" &&
    Number.isFinite(Date.parse(value.observed_at))
  );
}

// fetch the data from FastAPI
export async function fetchRepositoryTimeline(
  organizationId: number,
  repositoryId: number,
): Promise<TimelineEventPreview[]> {
  // retrieve backend address
  const apiBaseUrl = process.env.OPSREPLAY_API_BASE_URL?.trim();
  if (!apiBaseUrl) {
    throw new TimelineApiError("unavailable");
  }

  // build the endpoint e.g http://127.0.0.1:8000/organizations/1/repositories/5/timeline.
  const url =
    `${apiBaseUrl.replace(/\/+$/, "")}/organizations/${organizationId}` +
    `/repositories/${repositoryId}/timeline`;

  let response: Response;
  // request the current data from FastAPI. Stop if the request takes longer than 10 seconds
  try {
    response = await fetch(url, {
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    });
  } catch {
    throw new TimelineApiError("unavailable");
  }

  if (response.status === 404) {
    throw new TimelineApiError("not-found");
  }
  if (!response.ok) {
    throw new TimelineApiError("unavailable");
  }

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new TimelineApiError("invalid-response");
  }

  // every event must pass validation
  if (!Array.isArray(payload) || !payload.every(isTimelineEventPreview)) {
    throw new TimelineApiError("invalid-response");
  }

  // return a new array containing only those five fields
  return payload.map(({ id, source, event_type, summary, observed_at }) => ({
    id,
    source,
    event_type,
    summary,
    observed_at,
  }));
}
