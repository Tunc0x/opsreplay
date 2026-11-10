"use server";

import { redirect } from "next/navigation";

import { parsePositiveId } from "@/lib/ids";
import type { PostmortemGenerationErrorCode } from "@/lib/incident-feedback";
import { generatePostmortemDraft, PostmortemApiError } from "@/lib/postmortem-api";

function readId(formData: FormData, name: string): number | null {
  const values = formData.getAll(name);
  return values.length === 1 ? parsePositiveId(values[0]) : null;
}

export async function generatePostmortemAction(formData: FormData): Promise<void> {
  if (!(formData instanceof FormData)) {
    redirect("/?postmortemError=invalid-selection");
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
    query.set("postmortemError", "invalid-selection");
  } else {
    try {
      await generatePostmortemDraft(organizationId, repositoryId, incidentId);
    } catch (error) {
      let code: PostmortemGenerationErrorCode = "uncertain";
      if (error instanceof PostmortemApiError) {
        switch (error.kind) {
          case "invalid-request": code = "invalid-selection"; break;
          case "not-found": code = "not-found"; break;
          case "not-resolved": code = "not-resolved"; break;
          case "not-configured": code = "not-configured"; break;
          case "generation-failed": code = "generation-failed"; break;
          case "unavailable": code = "unavailable"; break;
          case "http-error": code = "unexpected-response"; break;
        }
      }
      query.set("postmortemError", code);
    }
  }

  // Next.js redirects throw framework control flow, outside the request catch.
  redirect(`/?${query}`);
}
