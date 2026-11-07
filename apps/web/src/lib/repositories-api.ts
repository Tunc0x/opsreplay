import "server-only";

import type { RepositoryOption } from "@/types/repository";

export class RepositoriesApiError extends Error {
  constructor(
    public readonly kind: "not-found" | "unavailable" | "invalid-response",
  ) {
    super(
      kind === "not-found"
        ? "Organization not found"
        : kind === "invalid-response"
          ? "Invalid repository data"
          : "Repositories are unavailable",
    );
    this.name = "RepositoriesApiError";
  }
}

function isRepositoryOption(value: unknown): value is RepositoryOption {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  return (
    "id" in value &&
    typeof value.id === "number" &&
    Number.isSafeInteger(value.id) &&
    value.id > 0 &&
    "organization_id" in value &&
    typeof value.organization_id === "number" &&
    Number.isSafeInteger(value.organization_id) &&
    value.organization_id > 0 &&
    "name" in value &&
    typeof value.name === "string"
  );
}

export async function fetchRepositories(
  organizationId: number,
): Promise<RepositoryOption[]> {
  const apiBaseUrl = process.env.OPSREPLAY_API_BASE_URL?.trim();
  if (!apiBaseUrl) {
    throw new RepositoriesApiError("unavailable");
  }

  const url = `${apiBaseUrl.replace(/\/+$/, "")}/organizations/${organizationId}/repositories`;
  let response: Response;
  try {
    response = await fetch(url, {
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    });
  } catch {
    throw new RepositoriesApiError("unavailable");
  }

  if (response.status === 404) {
    throw new RepositoriesApiError("not-found");
  }
  if (!response.ok) {
    throw new RepositoriesApiError("unavailable");
  }

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new RepositoriesApiError("invalid-response");
  }

  if (
    !Array.isArray(payload) ||
    !payload.every(
      (value): value is RepositoryOption =>
        isRepositoryOption(value) && value.organization_id === organizationId,
    )
  ) {
    throw new RepositoriesApiError("invalid-response");
  }

  return payload.map(({ id, organization_id, name }) => ({
    id,
    organization_id,
    name,
  }));
}
