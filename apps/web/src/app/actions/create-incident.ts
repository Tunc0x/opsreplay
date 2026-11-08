"use server";

import { redirect } from "next/navigation";
import { parsePositiveId } from "@/lib/ids";
import { createIncident, IncidentApiError } from "@/lib/incidents-api";
import type { IncidentCreationErrorCode } from "@/lib/incident-feedback";

function readId(formData: FormData, name: string): number | null {
  const values = formData.getAll(name);
  return values.length === 1 ? parsePositiveId(values[0]) : null;
}

export async function createIncidentAction(formData: FormData): Promise<void> {
  if (!(formData instanceof FormData)) {
    redirect("/?incidentError=invalid-selection");
  }

  const organizationId = readId(formData, "organizationId");
  const repositoryId = readId(formData, "repositoryId");
  const triggerEventId = readId(formData, "triggerEventId");
  const query = new URLSearchParams();
  if (organizationId !== null) {
    query.set("organizationId", String(organizationId));
    if (repositoryId !== null) {
      query.set("repositoryId", String(repositoryId));
      if (triggerEventId !== null) {
        query.set("triggerEventId", String(triggerEventId));
      }
    }
  }

  if (organizationId === null || repositoryId === null || triggerEventId === null) {
    query.set("incidentError", "invalid-selection");
  } else {
    try {
      const incident = await createIncident(
        organizationId,
        repositoryId,
        triggerEventId,
      );
      query.delete("triggerEventId");
      query.set("incidentId", String(incident.id));
    } catch (error) {
      let code: IncidentCreationErrorCode = "uncertain";
      if (error instanceof IncidentApiError) {
        switch (error.kind) {
          case "not-eligible":
            code = "not-eligible";
            break;
          case "not-found":
            code = "not-found";
            break;
          case "conflict":
            code = "already-exists";
            break;
          case "invalid-request":
            code = "invalid-request";
            break;
          case "unavailable":
            code = "unavailable";
            break;
        }
      }
      query.set("incidentError", code);
    }
  }

  // redirect throws framework control flow, so it must stay outside try/catch.
  redirect(`/?${query}`);
}
