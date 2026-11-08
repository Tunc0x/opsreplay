import type { Metadata } from "next";
import Link from "next/link";

import { EmptyState } from "@/components/empty-state";
import { RepositorySelector } from "@/components/repository-selector";
import { formatUtcTimestamp } from "@/lib/format-time";
import { parsePositiveId } from "@/lib/ids";
import { fetchIncidents, IncidentApiError } from "@/lib/incidents-api";
import { fetchRepositories, RepositoriesApiError } from "@/lib/repositories-api";
import type { IncidentSummaryPreview } from "@/types/incident";
import type { RepositoryOption } from "@/types/repository";

export const metadata: Metadata = { title: "OpsReplay — Incidents" };

type IncidentsPageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function IncidentsPage({ searchParams }: IncidentsPageProps) {
  const params = await searchParams;
  const organizationId = parsePositiveId(params.organizationId);
  const repositoryId = parsePositiveId(params.repositoryId);
  const hasSelection = params.organizationId !== undefined || params.repositoryId !== undefined;
  const hasRepositoryId = params.repositoryId !== undefined;
  let repositories: RepositoryOption[] | null = null;
  let selectedRepository: RepositoryOption | undefined;
  let incidents: IncidentSummaryPreview[] | null = null;
  let errorState: { title: string; description: string } | null = null;

  if (hasSelection) {
    if (organizationId === null || (hasRepositoryId && repositoryId === null)) {
      errorState = {
        title: "Invalid repository selection",
        description: "Provide an organization ID first. Each ID must appear once and be a positive whole number within JavaScript's safe integer range.",
      };
    } else {
      try {
        repositories = await fetchRepositories(organizationId);
      } catch (error) {
        if (error instanceof RepositoriesApiError && error.kind === "not-found") {
          errorState = {
            title: "Organization not found",
            description: "Check the organization ID and load its repositories again.",
          };
        } else if (error instanceof RepositoriesApiError && error.kind === "invalid-response") {
          errorState = {
            title: "Invalid repository data",
            description: "The backend returned an unexpected repository list. Try again later.",
          };
        } else {
          errorState = {
            title: "Repositories are unavailable",
            description: "Check that the backend is running and OPSREPLAY_API_BASE_URL is configured for the Next.js server, then try again.",
          };
        }
      }

      if (repositories !== null && hasRepositoryId) {
        selectedRepository = repositories.find(
          (repository) => repository.id === repositoryId && repository.organization_id === organizationId,
        );
        if (selectedRepository === undefined) {
          errorState = {
            title: "Repository not found",
            description: "Choose a repository belonging to this organization from the list above.",
          };
        } else {
          try {
            incidents = await fetchIncidents(organizationId, selectedRepository.id);
          } catch (error) {
            if (error instanceof IncidentApiError && error.kind === "not-found") {
              errorState = {
                title: "Repository not found",
                description: "This repository or organization is no longer available. Load the repositories again.",
              };
            } else if (error instanceof IncidentApiError && error.kind === "invalid-response") {
              errorState = {
                title: "Invalid incident data",
                description: "The backend returned an unexpected incident list. Try again later.",
              };
            } else if (error instanceof IncidentApiError && error.kind === "http-error") {
              errorState = {
                title: "Incident request failed",
                description: "The backend could not return the saved incidents. Try again later.",
              };
            } else {
              errorState = {
                title: "Incidents are unavailable",
                description: "The saved incidents could not be loaded. Check the backend connection and reload this page.",
              };
            }
          }
        }
      }
    }
  }

  return (
    <main
      id="main-content"
      tabIndex={-1}
      className="mx-auto w-full max-w-6xl flex-1 px-6 py-12 sm:px-8 sm:py-16"
    >
      <div className="mb-10 sm:mb-12">
        <p className="mb-4 font-mono text-xs tracking-widest text-accent uppercase">
          Change. Context. Clarity.
        </p>
        <h1 className="text-4xl font-medium tracking-tight sm:text-5xl">Incidents</h1>
        <p className="mt-4 max-w-2xl text-base leading-7 text-muted">
          Revisit saved incidents for the selected repository. Open an incident to
          review its timeline and resolve it when ready.
        </p>
      </div>

      <RepositorySelector
        organizationId={organizationId}
        repositories={repositories}
        selectedRepositoryId={selectedRepository?.id ?? null}
        action="/incidents"
        submitLabel="View incidents"
      />

      {errorState ? (
        <EmptyState title={errorState.title} description={errorState.description} />
      ) : incidents !== null && selectedRepository ? (
        incidents.length === 0 ? (
          <EmptyState
            title="No saved incidents"
            description="This repository has no saved incidents. Investigate an alert in Investigations to create one."
          />
        ) : (
          <section aria-labelledby="saved-incidents-heading">
            <h2 id="saved-incidents-heading" className="mb-6 text-2xl font-medium tracking-tight">
              Saved incidents
            </h2>
            <div
              role="region"
              aria-labelledby="saved-incidents-heading"
              tabIndex={0}
              className="overflow-x-auto rounded-xl border border-line bg-surface"
            >
              <table className="w-full min-w-224 table-fixed text-left text-sm">
                <caption className="sr-only">
                  Saved incidents for {selectedRepository.name}. Select an incident to view its details.
                </caption>
                <thead className="bg-background/40 text-xs font-medium text-muted">
                  <tr>
                    <th scope="col" className="w-[34%] px-5 py-4 font-medium">Incident</th>
                    <th scope="col" className="w-[12%] px-4 py-4 font-medium">Status</th>
                    <th scope="col" className="w-[18%] px-4 py-4 font-medium">Repository</th>
                    <th scope="col" className="w-[18%] px-4 py-4 font-medium">Alert occurred (UTC)</th>
                    <th scope="col" className="w-[18%] px-4 py-4 font-medium">Incident created (UTC)</th>
                  </tr>
                </thead>
                <tbody>
                  {incidents.map((incident) => (
                    <tr
                      key={incident.id}
                      className="group relative border-t border-line transition-colors hover:bg-accent/5 focus-within:bg-accent/5"
                    >
                      <th scope="row" className="px-5 py-5 align-top font-normal">
                        <span className="mb-2 block font-mono text-xs text-muted">#{incident.id}</span>
                        {/* Extend the native link over the row without adding click handlers. */}
                        <Link
                          href={`/?organizationId=${organizationId}&repositoryId=${selectedRepository.id}&incidentId=${incident.id}`}
                          prefetch={false}
                          className="font-medium wrap-anywhere transition-colors after:absolute after:inset-0 after:z-10 after:content-[''] group-hover:text-accent focus-visible:text-accent focus-visible:outline-none focus-visible:after:ring-2 focus-visible:after:ring-accent focus-visible:after:ring-inset"
                        >
                          <span className="sr-only">View incident #{incident.id}: </span>
                          {incident.title}
                        </Link>
                      </th>
                      <td className="px-4 py-5 align-top">
                        <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${incident.status === "resolved" ? "bg-accent/10 text-accent" : "bg-amber-300/10 text-amber-200"}`}>
                          {incident.status === "resolved" ? "Resolved" : "Open"}
                        </span>
                      </td>
                      <td className="px-4 py-5 align-top wrap-anywhere text-muted">
                        {incident.repository_name}
                      </td>
                      <td className="px-4 py-5 align-top text-muted tabular-nums">
                        <time dateTime={incident.alert_observed_at}>{formatUtcTimestamp(incident.alert_observed_at)}</time>
                      </td>
                      <td className="px-4 py-5 align-top text-muted tabular-nums">
                        <time dateTime={incident.created_at}>{formatUtcTimestamp(incident.created_at)}</time>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )
      ) : (
        <EmptyState
          title={repositories?.length === 0 ? "No repositories available" : "Choose a repository"}
          description={repositories?.length === 0
            ? "This organization has no repositories to browse."
            : "Load an organization's repositories and select one to view its saved incidents."}
        />
      )}
    </main>
  );
}
