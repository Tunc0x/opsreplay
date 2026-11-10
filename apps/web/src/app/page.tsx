import { createIncidentAction } from "@/app/actions/create-incident";
import { generatePostmortemAction } from "@/app/actions/generate-postmortem";
import { resolveIncidentAction } from "@/app/actions/resolve-incident";
import { EmptyState } from "@/components/empty-state";
import { GeneratePostmortemButton } from "@/components/generate-postmortem-button";
import { PostmortemDraft } from "@/components/postmortem-draft";
import { RepositorySelector } from "@/components/repository-selector";
import { TimelineEventList } from "@/components/timeline-event-list";
import { exampleTimelineEvents } from "@/data/example-timeline";
import { formatUtcTimestamp, formatUtcWindow } from "@/lib/format-time";
import { parsePositiveId } from "@/lib/ids";
import {
  getIncidentCreationFeedback,
  getIncidentResolutionFeedback,
  getPostmortemGenerationFeedback,
} from "@/lib/incident-feedback";
import { fetchIncident, IncidentApiError } from "@/lib/incidents-api";
import { fetchPostmortemDraft, PostmortemApiError } from "@/lib/postmortem-api";
import {
  fetchInvestigationContext,
  InvestigationApiError,
} from "@/lib/investigation-api";
import { fetchRepositories, RepositoriesApiError } from "@/lib/repositories-api";
import { fetchRepositoryTimeline, TimelineApiError } from "@/lib/timeline-api";
import type { InvestigationContextPreview } from "@/types/investigation";
import type { IncidentPreview } from "@/types/incident";
import type { PostmortemDraftPreview } from "@/types/postmortem";
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
  const generationFeedback = getPostmortemGenerationFeedback(params.postmortemError);
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

  let postmortem: PostmortemDraftPreview | null = null;
  let postmortemMissing = false;
  let postmortemNotice: { title: string; description: string } | null = null;
  if (savedIncident?.status === "open") {
    postmortemNotice = {
      title: "Postmortem draft",
      description: "Postmortem generation requires a resolved incident. Saved drafts are displayed here after resolution.",
    };
  } else if (!errorState && savedIncident?.status === "resolved" && organizationId !== null && selectedRepository) {
    try {
      postmortem = await fetchPostmortemDraft(organizationId, selectedRepository.id, savedIncident.id);
    } catch (error) {
      if (error instanceof PostmortemApiError && error.kind === "not-found") {
        postmortemMissing = true;
        postmortemNotice = {
          title: "Postmortem draft",
          description: "No postmortem draft has been generated for this incident yet.",
        };
      } else if (error instanceof PostmortemApiError && error.kind === "invalid-response") {
        postmortemNotice = {
          title: "Invalid postmortem data",
          description: "The backend returned a draft with invalid content or evidence references. The draft cannot be displayed.",
        };
      } else if (error instanceof PostmortemApiError && error.kind === "http-error") {
        postmortemNotice = {
          title: "Postmortem request failed",
          description: "The backend could not return the saved draft. Try reloading this page later.",
        };
      } else {
        postmortemNotice = {
          title: "Postmortem draft unavailable",
          description: "The saved draft could not be loaded. Check the backend connection and reload this page.",
        };
      }
    }
  }

  const triggeringAlert = investigation?.events.find(
    (event) => event.id === investigation.trigger_event_id &&
      event.source === "alert" && event.event_type === "alert",
  );
  // Normalized alert summaries use "SEVERITY: title". Keep other formats intact.
  const alertSummary = triggeringAlert?.summary.match(/^([A-Z][A-Z0-9 _-]*): ([\s\S]+)$/);
  const alertTitle = alertSummary?.[2] ?? triggeringAlert?.summary;
  const alertSeverity = alertSummary
    ? alertSummary[1].charAt(0) + alertSummary[1].slice(1).toLowerCase()
    : null;
  const minutesBeforeAlert = investigation && triggeringAlert
    ? (Date.parse(triggeringAlert.observed_at) - Date.parse(investigation.window_start)) / 60_000
    : null;
  const minutesAfterAlert = investigation && triggeringAlert
    ? (Date.parse(investigation.window_end) - Date.parse(triggeringAlert.observed_at)) / 60_000
    : null;

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
          {hasIncidentId ? "Incidents" : "Investigations"}
        </h1>
        <p className="mt-4 max-w-2xl text-base leading-7 text-muted">
          {hasIncidentId
            ? "Review a saved incident and its evidence-backed investigation context."
            : "Follow the events around a production incident, understand what changed, and keep every investigation grounded in evidence."}
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

      {generationFeedback && !postmortem && (
        <section aria-labelledby="postmortem-feedback-heading" className="mb-6 rounded-xl border border-line bg-surface p-6">
          <h2 id="postmortem-feedback-heading" className="text-lg font-medium">{generationFeedback.title}</h2>
          <p className="mt-2 text-sm leading-6 text-muted">{generationFeedback.description}</p>
        </section>
      )}

      {hasTriggerEventId && organizationId !== null && selectedRepository && (
        <nav aria-label="Breadcrumb" className="mb-8">
          <ol className="flex flex-wrap items-center gap-3 text-sm">
            <li>
              <a
                href={`/?${new URLSearchParams({
                  organizationId: String(organizationId),
                  repositoryId: String(selectedRepository.id),
                })}`}
                aria-label="Investigations, back to repository timeline"
                className="font-medium text-accent underline-offset-4 hover:underline"
              >
                Investigations
              </a>
            </li>
            <li className="flex items-center gap-3 text-muted">
              <svg
                viewBox="0 0 24 24"
                className="size-4"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="m9 5 7 7-7 7" />
              </svg>
              <span aria-current="page">Alert #{investigation?.trigger_event_id ?? triggerEventId}</span>
            </li>
          </ol>
        </nav>
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
              Alert investigation
            </p>
            <h2
              id="investigation-heading"
              className="text-3xl font-semibold tracking-tight wrap-anywhere sm:text-4xl"
            >
              {alertTitle ?? "Alert investigation"}
            </h2>
            {triggeringAlert && (
              <div className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-2 text-sm text-muted">
                <span className="rounded-md bg-amber-300/10 px-3 py-1.5 text-xs font-medium text-amber-200">
                  {alertSeverity ? `${alertSeverity} alert` : "Alert"}
                </span>
                {selectedRepository && (
                  <>
                    <span className="wrap-anywhere">{selectedRepository.name}</span>
                    <span aria-hidden="true">·</span>
                  </>
                )}
                <time dateTime={triggeringAlert.observed_at}>
                  {formatUtcTimestamp(triggeringAlert.observed_at)}
                </time>
              </div>
            )}
          </div>

          {organizationId !== null && selectedRepository && (
            <form
              action={createIncidentAction}
              aria-labelledby="create-incident-heading"
              className="mt-6 mb-6 flex flex-col gap-6 rounded-xl border border-line bg-surface p-6 sm:flex-row sm:items-center sm:justify-between"
            >
              <div className="min-w-0">
                <h3 id="create-incident-heading" className="text-lg font-medium">
                  Keep this investigation for later
                </h3>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
                  Create an incident to keep this alert and its investigation window together for review.
                </p>
              </div>
              <input type="hidden" name="organizationId" value={organizationId} />
              <input type="hidden" name="repositoryId" value={selectedRepository.id} />
              <input type="hidden" name="triggerEventId" value={investigation.trigger_event_id} />
              <button
                type="submit"
                className="inline-flex min-h-14 shrink-0 cursor-pointer items-center justify-center gap-3 self-end rounded-lg bg-accent px-5 py-3 text-base font-medium text-background transition-colors hover:bg-accent/90 sm:self-auto"
              >
                Create incident
                <svg
                  viewBox="0 0 24 24"
                  className="size-5"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <path d="M5 12h14m-6-6 6 6-6 6" />
                </svg>
              </button>
            </form>
          )}

          <dl className="mb-6 flex flex-col gap-6 rounded-xl border border-line bg-surface p-6 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <dt className="text-sm text-muted">Investigation window</dt>
              <dd className="mt-2 text-base leading-6 tabular-nums">
                {formatUtcWindow(investigation.window_start, investigation.window_end)}
              </dd>
            </div>
            <div>
              <dt className="text-sm text-muted">Window around the alert</dt>
              <dd className="mt-2 text-base leading-6 tabular-nums">
                {minutesBeforeAlert !== null && minutesAfterAlert !== null
                  ? `${minutesBeforeAlert} min before · ${minutesAfterAlert} min after`
                  : "Alert timestamp unavailable"}
              </dd>
            </div>
          </dl>

          <TimelineEventList
            events={investigation.events}
            triggerEventId={investigation.trigger_event_id}
          />

         
        </section>
      )}

      {!errorState && savedIncident && organizationId !== null && selectedRepository && (
        <section aria-labelledby="saved-incident-heading">
          <h2 id="saved-incident-heading" className="text-2xl font-medium tracking-tight">
            Saved incident
          </h2>
        
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

          {postmortem ? (
            <PostmortemDraft postmortem={postmortem} />
          ) : postmortemNotice && (
            <section aria-labelledby="postmortem-notice-heading" className="mt-8 rounded-xl border border-line bg-surface p-6 sm:p-8">
              <h3 id="postmortem-notice-heading" className="text-lg font-medium">{postmortemNotice.title}</h3>
              <p className="mt-2 text-sm leading-6 text-muted">{postmortemNotice.description}</p>
              {savedIncident.status === "resolved" && postmortemMissing && (
                <form action={generatePostmortemAction} className="mt-5 border-t border-line pt-5">
                  <input type="hidden" name="organizationId" value={organizationId} />
                  <input type="hidden" name="repositoryId" value={selectedRepository.id} />
                  <input type="hidden" name="incidentId" value={savedIncident.id} />
                  <p id="postmortem-generation-help" className="max-w-2xl text-sm leading-6 text-muted">
                    Create an AI draft from this incident&apos;s recorded evidence. Generation may incur API charges. Use non-sensitive test data only during local development.
                  </p>
                  <GeneratePostmortemButton />
                </form>
              )}
            </section>
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
