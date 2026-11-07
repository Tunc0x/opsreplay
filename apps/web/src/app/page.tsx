import { EmptyState } from "@/components/empty-state";
import { RepositorySelector } from "@/components/repository-selector";
import { TimelineEventList } from "@/components/timeline-event-list";
import { exampleTimelineEvents } from "@/data/example-timeline";
import { formatUtcTimestamp } from "@/lib/format-time";
import {
  fetchInvestigationContext,
  InvestigationApiError,
} from "@/lib/investigation-api";
import { fetchRepositories, RepositoriesApiError } from "@/lib/repositories-api";
import { fetchRepositoryTimeline, TimelineApiError } from "@/lib/timeline-api";
import type { InvestigationContextPreview } from "@/types/investigation";
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
    params.organizationId === undefined &&
    params.repositoryId === undefined &&
    params.triggerEventId === undefined;
  const organizationId = parsePositiveId(params.organizationId);
  const repositoryId = parsePositiveId(params.repositoryId);
  const hasRepositoryId = params.repositoryId !== undefined;
  const triggerEventId = parsePositiveId(params.triggerEventId);
  const hasTriggerEventId = params.triggerEventId !== undefined;
  let repositories: RepositoryOption[] | null = null;
  let selectedRepository: RepositoryOption | undefined;
  let events: TimelineEventPreview[] = isExample ? exampleTimelineEvents : [];
  let investigation: InvestigationContextPreview | null = null;
  let errorState: { title: string; description: string } | null = null;

  if (!isExample) {
    if (
      hasTriggerEventId &&
      (triggerEventId === null || organizationId === null || repositoryId === null)
    ) {
      errorState = {
        title: "Invalid alert investigation",
        description:
          "An investigation requires organizationId, repositoryId and triggerEventId. Each must appear once and be a positive whole number within JavaScript's safe integer range.",
      };
    } else if (
      organizationId === null ||
      (hasRepositoryId && repositoryId === null)
    ) {
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
            if (triggerEventId !== null) {
              investigation = await fetchInvestigationContext(
                organizationId,
                selectedRepository.id,
                triggerEventId,
              );
            } else {
              events = await fetchRepositoryTimeline(
                organizationId,
                selectedRepository.id,
              );
            }
          } catch (error) {
            if (error instanceof InvestigationApiError) {
              switch (error.kind) {
                case "not-eligible":
                  errorState = {
                    title: "This event cannot trigger an investigation",
                    description:
                      "Choose an alert event from the repository timeline.",
                  };
                  break;
                case "not-found":
                  errorState = {
                    title: "Investigation event not found",
                    description:
                      "The requested event, repository or organization could not be found. Return to the repository timeline and choose an alert.",
                  };
                  break;
                case "invalid-response":
                  errorState = {
                    title: "Invalid investigation data",
                    description:
                      "The backend returned an unexpected investigation response. Try again later.",
                  };
                  break;
                case "http-error":
                  errorState = {
                    title: "Investigation request failed",
                    description:
                      "The backend could not return the investigation context. Try again later.",
                  };
                  break;
                case "unavailable":
                  errorState = {
                    title: "Investigation context is unavailable",
                    description:
                      "Check that the backend is running and OPSREPLAY_API_BASE_URL is configured for the Next.js server, then reload this page.",
                  };
                  break;
              }
            } else if (
              error instanceof TimelineApiError && error.kind === "not-found"
            ) {
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
                title: hasTriggerEventId
                  ? "Investigation context is unavailable"
                  : "Repository timeline is unavailable",
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

      {hasTriggerEventId && organizationId !== null && selectedRepository && (
        <a
          href={`/?${new URLSearchParams({
            organizationId: String(organizationId),
            repositoryId: String(selectedRepository.id),
          })}`}
          className="mb-6 inline-flex text-sm font-medium text-accent underline underline-offset-4 hover:text-foreground"
        >
          Back to repository timeline
        </a>
      )}

      {errorState && (
        <EmptyState
          title={errorState.title}
          description={errorState.description}
        />
      )}

      {!errorState && investigation && (
        <section aria-labelledby="investigation-heading">
          <div className="mb-6">
            <p className="mb-3 font-mono text-xs tracking-widest text-accent uppercase">
              Read-only context
            </p>
            <h2
              id="investigation-heading"
              className="text-2xl font-medium tracking-tight"
            >
              Alert investigation
            </h2>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-muted sm:text-base sm:leading-7">
              This window covers 30 minutes before and 30 minutes after the
              triggering alert.
            </p>
          </div>

          <dl className="mb-6 grid gap-6 rounded-xl border border-line bg-surface p-6 sm:grid-cols-3 sm:p-8">
            <div>
              <dt className="text-sm text-muted">Trigger event ID</dt>
              <dd className="mt-2 font-mono text-sm">
                {investigation.trigger_event_id}
              </dd>
            </div>
            <div>
              <dt className="text-sm text-muted">Investigation start (UTC)</dt>
              <dd className="mt-2 font-mono text-sm leading-6">
                <time dateTime={investigation.window_start}>
                  {formatUtcTimestamp(investigation.window_start)}
                </time>
              </dd>
            </div>
            <div>
              <dt className="text-sm text-muted">Investigation end (UTC)</dt>
              <dd className="mt-2 font-mono text-sm leading-6">
                <time dateTime={investigation.window_end}>
                  {formatUtcTimestamp(investigation.window_end)}
                </time>
              </dd>
            </div>
          </dl>

          <TimelineEventList events={investigation.events} />
        </section>
      )}

      {!errorState && !investigation && (isExample || selectedRepository) && (
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
                ? "These three fictional events illustrate how an investigation timeline could look. No real incident or backend data is shown."
                : `Timeline events for ${selectedRepository?.name}.`}
            </p>
          </div>
          <TimelineEventList
            events={events}
            repositoryContext={
              organizationId !== null && selectedRepository
                ? { organizationId, repositoryId: selectedRepository.id }
                : undefined
            }
          />
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
