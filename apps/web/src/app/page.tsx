import { EmptyState } from "@/components/empty-state";
import { RepositorySelector } from "@/components/repository-selector";
import { TimelineEventList } from "@/components/timeline-event-list";
import { exampleTimelineEvents } from "@/data/example-timeline";
import { fetchRepositories, RepositoriesApiError } from "@/lib/repositories-api";
import { fetchRepositoryTimeline, TimelineApiError } from "@/lib/timeline-api";
import type { RepositoryOption } from "@/types/repository";
import type { TimelineEventPreview } from "@/types/timeline";

// accept the value only if it is a positive, safe integer
function parsePositiveId(value: string | string[] | undefined): number | null {
  if (typeof value !== "string" || !/^\d+$/.test(value)) {
    return null;
  }

  const id = Number(value);
  return Number.isSafeInteger(id) && id > 0 ? id : null;
}
// searchParams contains the URL query parameters. e.g. /?organizationId=1&repositoryId=5
export default async function Home({ searchParams }: PageProps<"/">) {
  const params = await searchParams;
  const isExample =
    params.organizationId === undefined && params.repositoryId === undefined;
  const organizationId = parsePositiveId(params.organizationId);
  const repositoryId = parsePositiveId(params.repositoryId);
  const hasRepositoryId = params.repositoryId !== undefined;
  let repositories: RepositoryOption[] | null = null;
  let selectedRepository: RepositoryOption | undefined;
  let events: TimelineEventPreview[] = isExample ? exampleTimelineEvents : [];
  let errorState: { title: string; description: string } | null = null;

  if (!isExample) {
    if (organizationId === null || (hasRepositoryId && repositoryId === null)) {
      errorState = {
        title: "Invalid repository selection",
        description:
          "Provide organizationId before selecting a repository. Each supplied ID must appear once and be a positive whole number within JavaScript's safe integer range.",
      };
    } else {
      try {
        repositories = await fetchRepositories(organizationId);
      } catch (error) {
        if (error instanceof RepositoriesApiError && error.kind === "not-found") {
          errorState = {
            title: "Organization not found",
            description:
              "Check the organization ID and load its repositories again.",
          };
        } else if (
          error instanceof RepositoriesApiError &&
          error.kind === "invalid-response"
        ) {
          errorState = {
            title: "Invalid repository data",
            description:
              "The backend returned an unexpected repository list. Try again later.",
          };
        } else {
          errorState = {
            title: "Repositories are unavailable",
            description:
              "The repository list could not be loaded. Check that the backend is running and OPSREPLAY_API_BASE_URL is configured for the Next.js server, then try again.",
          };
        }
      }

      if (repositories !== null && hasRepositoryId) {
        selectedRepository = repositories.find(
          (repository) =>
            repository.id === repositoryId &&
            repository.organization_id === organizationId,
        );

        if (selectedRepository === undefined) {
          errorState = {
            title: "Repository not found",
            description:
              "The selected repository does not belong to this organization. Choose a repository from the list above.",
          };
        } else {
          try {
            events = await fetchRepositoryTimeline(
              organizationId,
              selectedRepository.id,
            );
          } catch (error) {
            if (error instanceof TimelineApiError && error.kind === "not-found") {
              errorState = {
                title: "Repository not found",
                description:
                  "This repository is no longer available under the selected organization. Load the repositories again.",
              };
            } else if (
              error instanceof TimelineApiError &&
              error.kind === "invalid-response"
            ) {
              errorState = {
                title: "Invalid timeline data",
                description:
                  "The backend returned an unexpected timeline response. Try again later.",
              };
            } else {
              errorState = {
                title: "Repository timeline is unavailable",
                description:
                  "The timeline could not be loaded. Check that the backend is running and OPSREPLAY_API_BASE_URL is configured for the Next.js server, then reload this page.",
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
        <h1 className="text-4xl font-medium tracking-tight sm:text-5xl">
          Investigations
        </h1>
        <p className="mt-4 max-w-2xl text-base leading-7 text-muted">
          Follow the events around a production incident, understand what changed,
          and keep every investigation grounded in evidence.
        </p>
      </div>

      <RepositorySelector
        organizationId={organizationId}
        repositories={repositories}
        selectedRepositoryId={selectedRepository?.id ?? null}
      />

      {errorState && (
        <EmptyState
          title={errorState.title}
          description={errorState.description}
        />
      )}

      {!errorState && (isExample || selectedRepository) && (
        <section aria-labelledby="timeline-heading">
          <div className="mb-6">
            <p className="mb-3 font-mono text-xs tracking-widest text-accent uppercase">
              {isExample ? "Fictional sample data · Not live" : "Repository events"}
            </p>
            <h2
              id="timeline-heading"
              className="text-2xl font-medium tracking-tight"
            >
              {isExample ? "Example investigation timeline" : "Repository timeline"}
            </h2>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-muted sm:text-base sm:leading-7">
              {isExample
                ? "These three fictional events illustrate how an investigation timeline could look. No real incident or backend data is shown. All times are displayed in UTC."
                : `Timeline events for ${selectedRepository?.name}. All times are displayed in UTC.`}
            </p>
          </div>
          <TimelineEventList events={events} />
        </section>
      )}

      {!errorState &&
        repositories !== null &&
        repositories.length > 0 &&
        !selectedRepository && (
          <EmptyState
            title="Select a repository"
            description="Choose a repository by name above, then select View timeline to load its events."
          />
        )}
    </main>
  );
}
