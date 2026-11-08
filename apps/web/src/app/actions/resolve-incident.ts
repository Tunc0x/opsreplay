"use server";

import { redirect } from "next/navigation";
import { parsePositiveId } from "@/lib/ids";
import { resolveIncident, IncidentApiError } from "@/lib/incidents-api";
import type { IncidentResolutionErrorCode } from "@/lib/incident-feedback";

function readId(formData: FormData, name: string): number | null {
  const values = formData.getAll(name);
  return values.length === 1 ? parsePositiveId(values[0]) : null;
}

export async function resolveIncidentAction(formData: FormData): Promise<void> {
  if (!(formData instanceof FormData)) {
    redirect("/?resolutionError=invalid-selection");
  }

  const organizationId = readId(formData, "organizationId");
  const repositoryId = readId(formData, "repositoryId");
  const incidentId = readId(formData, "incidentId");
  const query = new URLSearchParams();
  if (organizationId !== null) {
    query.set("organizationId", String(organizationId));
    if (repositoryId !== null) {
      query.set("repositoryId", String(repositoryId));
      if (incidentId !== null) query.set("incidentId", String(incidentId));
    }
  }

  if (organizationId === null || repositoryId === null || incidentId === null) {
    query.set("resolutionError", "invalid-selection");
  } else {
    try {
      await resolveIncident(organizationId, repositoryId, incidentId);
    } catch (error) {
      let code: IncidentResolutionErrorCode = "uncertain";
      if (error instanceof IncidentApiError) {
        switch (error.kind) {
          case "not-found":
            code = "not-found";
            break;
          case "unavailable":
            code = "unavailable";
            break;
          case "http-error":
            code = "unexpected-response";
            break;
          case "invalid-response":
            code = "invalid-response";
            break;
        }
      }
      query.set("resolutionError", code);
    }
  }

  // Next.js redirect throws control flow; keep it outside the try/catch.
  redirect(`/?${query}`);
}
