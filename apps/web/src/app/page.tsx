import { EmptyState } from "@/components/empty-state";
import { TimelineEventList } from "@/components/timeline-event-list";
import { exampleTimelineEvents } from "@/data/example-timeline";
import { fetchRepositoryTimeline, TimelineApiError } from "@/lib/timeline-api";
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
  let events: TimelineEventPreview[] = isExample ? exampleTimelineEvents : [];
  let errorState: { title: string; description: string } | null = null;

  if (!isExample) {
    const organizationId = parsePositiveId(params.organizationId);
    const repositoryId = parsePositiveId(params.repositoryId);

    if (organizationId === null || repositoryId === null) {
      errorState = {
        title: "Enter valid organization and repository IDs",
        description:
          "Provide both organizationId and repositoryId once in the URL. Each must be a positive whole number within JavaScript's safe integer range.",
      };
    } else {
      try {
        events = await fetchRepositoryTimeline(organizationId, repositoryId);
      } catch (error) {
        errorState =
          error instanceof TimelineApiError && error.kind === "not-found"
            ? {
                title: "Organization or repository not found",
                description:
                  "Check both IDs and make sure the repository belongs to the specified organization.",
              }
            : {
                title: "Repository timeline is unavailable",
                description:
                  "The timeline could not be loaded. Check that the backend is running and OPSREPLAY_API_BASE_URL is configured for the Next.js server, then reload this page.",
              };
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

      {isExample && (
        <EmptyState
          title="No repository selected"
          description="You are viewing a fictional example. No timeline data has been requested from the backend."
        />
      )}

      <section
        aria-labelledby="timeline-heading"
        className={isExample ? "mt-12 sm:mt-16" : undefined}
      >
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
              : "Timeline events for the organization and repository specified in the URL. All times are displayed in UTC."}
          </p>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-muted">
            To load real data, supply both IDs in the URL:{" "}
            <code className="text-foreground break-words">
              {"/?organizationId=<organization-id>&repositoryId=<repository-id>"}
            </code>
          </p>
        </div>

        {errorState ? (
          <EmptyState
            title={errorState.title}
            description={errorState.description}
          />
        ) : (
          <TimelineEventList events={events} />
        )}
      </section>
    </main>
  );
}
