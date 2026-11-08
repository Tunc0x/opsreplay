import { createIncidentAction } from "@/app/actions/create-incident";
import { resolveIncidentAction } from "@/app/actions/resolve-incident";
import { EmptyState } from "@/components/empty-state";
import { RepositorySelector } from "@/components/repository-selector";
import { TimelineEventList } from "@/components/timeline-event-list";
import { exampleTimelineEvents } from "@/data/example-timeline";
import { formatUtcTimestamp } from "@/lib/format-time";
import { parsePositiveId } from "@/lib/ids";
import {
  getIncidentCreationFeedback,
  getIncidentResolutionFeedback,
} from "@/lib/incident-feedback";
import { fetchIncident, IncidentApiError } from "@/lib/incidents-api";
import {
  fetchInvestigationContext,
  InvestigationApiError,
} from "@/lib/investigation-api";
import { fetchRepositories, RepositoriesApiError } from "@/lib/repositories-api";
import { fetchRepositoryTimeline, TimelineApiError } from "@/lib/timeline-api";
import type { InvestigationContextPreview } from "@/types/investigation";
import type { IncidentPreview } from "@/types/incident";
import type { RepositoryOption } from "@/types/repository";
import type { TimelineEventPreview } from "@/types/timeline";

// searchParams contains the URL query parameters. e.g. /?organizationId=1&repositoryId=5
export default async function Home({ searchParams }: PageProps<"/">) {
  const params = await searchParams;
  const isExample =
    params.organizationId === undefined &&
    params.repositoryId === undefined &&
    params.triggerEventId === undefined &&
    params.incidentId === undefined;
  const organizationId = parsePositiveId(params.organizationId);
  const repositoryId = parsePositiveId(params.repositoryId);
  const hasRepositoryId = params.repositoryId !== undefined;
  const triggerEventId = parsePositiveId(params.triggerEventId);
  const hasTriggerEventId = params.triggerEventId !== undefined;
  const incidentId = parsePositiveId(params.incidentId);
  const hasIncidentId = params.incidentId !== undefined;
  const creationFeedback = getIncidentCreationFeedback(params.incidentError);
  const resolutionFeedback = getIncidentResolutionFeedback(params.resolutionError);
  let repositories: RepositoryOption[] | null = null;
  let selectedRepository: RepositoryOption | undefined;
  let events: TimelineEventPreview[] = isExample ? exampleTimelineEvents : [];
  let investigation: InvestigationContextPreview | null = null;
  let savedIncident: IncidentPreview | null = null;
  let errorState: { title: string; description: string } | null = null;

  if (!isExample) {
    if (
      hasIncidentId &&
      (hasTriggerEventId || incidentId === null || organizationId === null || repositoryId === null)
    ) {
      errorState = {
        title: "Invalid saved incident selection",
        description:
          "Provide one positive, safe integer each for organizationId, repositoryId and incidentId. Do not combine incidentId with triggerEventId.",
      };
    } else if (
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
            if (incidentId !== null) {
              savedIncident = await fetchIncident(
                organizationId,
                selectedRepository.id,
                incidentId,
              );
            } else if (triggerEventId !== null) {
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
            if (error instanceof IncidentApiError) {
              switch (error.kind) {
                case "not-found":
                  errorState = {
                    title: "Incident not found",
                    description: "The saved incident is not available under this organization and repository.",
                  };
                  break;
                case "invalid-response":
                  errorState = {
                    title: "Invalid incident data",
                    description: "The backend returned an unexpected saved incident response. Try again later.",
                  };
                  break;
                case "http-error":
                  errorState = {
                    title: "Incident request failed",
                    description: "The backend could not return this saved incident. Try again later.",
                  };
                  break;
                default:
                  errorState = {
                    title: "Saved incident is unavailable",
                    description: "Check that the backend is running and OPSREPLAY_API_BASE_URL is configured, then reload this page.",
                  };
              }
            } else if (error instanceof InvestigationApiError) {
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
                title: hasIncidentId
                  ? "Saved incident is unavailable"
                  : hasTriggerEventId
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

      {creationFeedback && (
        <section
          aria-labelledby="incident-feedback-heading"
          className="mb-6 rounded-xl border border-line bg-surface p-6"
        >
          <h2 id="incident-feedback-heading" className="text-lg font-medium">
            {creationFeedback.title}
          </h2>
          <p className="mt-2 text-sm leading-6 text-muted">
            {creationFeedback.description}
          </p>
        </section>
      )}

      {resolutionFeedback && (
        <section
          aria-labelledby="resolution-feedback-heading"
          className="mb-6 rounded-xl border border-line bg-surface p-6"
        >
          <h2 id="resolution-feedback-heading" className="text-lg font-medium">
            {resolutionFeedback.title}
          </h2>
          <p className="mt-2 text-sm leading-6 text-muted">
            {resolutionFeedback.description}
          </p>
        </section>
      )}

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
              Alert context
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

          {organizationId !== null && selectedRepository && (
            <form
              action={createIncidentAction}
              aria-labelledby="create-incident-heading"
              className="mt-6 rounded-xl border border-line bg-surface p-6 sm:p-8"
            >
              <h3 id="create-incident-heading" className="text-lg font-medium">
                Save this investigation as an incident
              </h3>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
                Submitting this form saves a real database record with a 30-minute
                lookback and lookahead. This workflow is for local development
                only; authentication and authorization are not implemented.
              </p>
              <input type="hidden" name="organizationId" value={organizationId} />
              <input type="hidden" name="repositoryId" value={selectedRepository.id} />
              <input type="hidden" name="triggerEventId" value={investigation.trigger_event_id} />
              <button
                type="submit"
                className="mt-5 min-h-11 cursor-pointer rounded-md bg-accent px-4 py-2 text-sm font-medium text-background hover:bg-accent/90"
              >
                Create incident
              </button>
            </form>
          )}
        </section>
      )}

      {!errorState && savedIncident && organizationId !== null && selectedRepository && (
        <section aria-labelledby="saved-incident-heading">
          <h2 id="saved-incident-heading" className="text-2xl font-medium tracking-tight">
            Saved incident
          </h2>
          <p className="mt-3 text-sm leading-6 text-muted">
            This record was retrieved from the backend. Its context reflects the
            current events inside its saved investigation window.
          </p>
          <dl className="my-6 grid gap-6 rounded-xl border border-line bg-surface p-6 sm:grid-cols-3 sm:p-8">
            <div>
              <dt className="text-sm text-muted">Incident ID</dt>
              <dd className="mt-2 font-mono text-sm">{savedIncident.id}</dd>
            </div>
            <div>
              <dt className="text-sm text-muted">Status</dt>
              <dd className="mt-2">
                <span
                  className={`inline-flex rounded-md border px-2 py-1 text-sm font-medium ${
                    savedIncident.status === "resolved"
                      ? "border-accent/20 bg-accent/10 text-accent"
                      : "border-amber-300/20 bg-amber-300/10 text-amber-200"
                  }`}
                >
                  {savedIncident.status === "resolved" ? "Resolved" : "Open"}
                </span>
              </dd>
            </div>
            <div>
              <dt className="text-sm text-muted">Trigger event ID</dt>
              <dd className="mt-2 font-mono text-sm">{savedIncident.trigger_timeline_event_id}</dd>
            </div>
            <div>
              <dt className="text-sm text-muted">Created (UTC)</dt>
              <dd className="mt-2 font-mono text-sm leading-6">
                <time dateTime={savedIncident.created_at}>
                  {formatUtcTimestamp(savedIncident.created_at)}
                </time>
              </dd>
            </div>
            <div>
              <dt className="text-sm text-muted">Investigation window</dt>
              <dd className="mt-2 text-sm leading-6">
                {savedIncident.lookback_minutes} minutes before / {savedIncident.lookahead_minutes} minutes after
              </dd>
            </div>
            <div>
              <dt className="text-sm text-muted">Resolution state</dt>
              <dd className="mt-2 text-sm leading-6">
                {savedIncident.resolved_at === null ? "Unresolved" : (
                  <time dateTime={savedIncident.resolved_at}>
                    Resolved {formatUtcTimestamp(savedIncident.resolved_at)}
                  </time>
                )}
              </dd>
            </div>
          </dl>
          <a
            href={`/?${new URLSearchParams({
              organizationId: String(organizationId),
              repositoryId: String(selectedRepository.id),
              triggerEventId: String(savedIncident.trigger_timeline_event_id),
            })}`}
            className="mb-6 inline-flex text-sm font-medium text-accent underline underline-offset-4 hover:text-foreground"
          >
            View triggering alert investigation
          </a>
          <TimelineEventList events={savedIncident.context.events} />

          {savedIncident.status === "open" ? (
            <form
              action={resolveIncidentAction}
              aria-labelledby="resolve-incident-heading"
              className="mt-6 rounded-xl border border-line bg-surface p-6 sm:p-8"
            >
              <h3 id="resolve-incident-heading" className="text-lg font-medium">
                Resolve this incident
              </h3>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
                Mark this incident as resolved and save a UTC resolution timestamp.
                This workflow is for local development only; authentication and
                authorization are not implemented.
              </p>
              <input type="hidden" name="organizationId" value={organizationId} />
              <input type="hidden" name="repositoryId" value={selectedRepository.id} />
              <input type="hidden" name="incidentId" value={savedIncident.id} />
              <button
                type="submit"
                className="mt-5 min-h-11 cursor-pointer rounded-md bg-accent px-4 py-2 text-sm font-medium text-background hover:bg-accent/90"
              >
                Resolve incident
              </button>
            </form>
          ) : (
            <p
              role="status"
              className="mt-6 rounded-xl border border-accent/20 bg-accent/5 p-6 text-sm leading-6 text-accent"
            >
              This incident has been resolved.
            </p>
          )}
        </section>
      )}

      {!errorState && !investigation && !savedIncident && (isExample || selectedRepository) && (
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
