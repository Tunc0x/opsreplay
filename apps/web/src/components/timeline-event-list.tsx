import { EmptyState } from "@/components/empty-state";
import { formatUtcTimestamp } from "@/lib/format-time";
import type { TimelineEventPreview } from "@/types/timeline";

type TimelineEventListProps = {
  events: readonly TimelineEventPreview[];
  triggerEventId?: number;
  repositoryContext?: {
    organizationId: number;
    repositoryId: number;
  };
};

export function TimelineEventList({
  events,
  triggerEventId,
  repositoryContext,
}: TimelineEventListProps) {
  if (events.length === 0) {
    return (
      <EmptyState
        title="No timeline events to display"
        description="The supplied timeline does not contain any events."
      />
    );
  }

  return (
    <ol className="divide-y divide-line rounded-xl border border-line bg-surface">
      {events.map((event) => {
        const isTrigger = event.id === triggerEventId &&
          event.source === "alert" && event.event_type === "alert";
        let eventLabel = event.event_type.replace(/_/g, " ") || "Unknown event";
        let badgeClasses = "border-line bg-background text-muted";

        switch (event.event_type) {
          case "push":
            eventLabel = "Push";
            badgeClasses = "border-line bg-background text-foreground";
            break;
          case "deployment_status":
            eventLabel = "Deployment status";
            badgeClasses = "border-accent/20 bg-accent/10 text-accent";
            break;
          case "alert":
            eventLabel = "Alert";
            badgeClasses = "border-amber-300/20 bg-amber-300/10 text-amber-200";
            break;
        }

        return (
          <li
            key={event.id}
            className={`flex flex-col gap-3 px-5 py-6 sm:grid sm:grid-cols-[13rem_1fr] sm:gap-6 sm:px-6 ${isTrigger ? "bg-amber-300/5 ring-1 ring-amber-300/20 ring-inset first:rounded-t-xl last:rounded-b-xl" : ""}`}
          >
            <time
              dateTime={event.observed_at}
              className="font-mono text-xs leading-6 text-muted"
            >
              {formatUtcTimestamp(event.observed_at)}
            </time>
            <div className="min-w-0">
              <div className="mb-3 flex flex-wrap items-center gap-3">
                <span
                  className={`rounded-md border px-2 py-1 text-xs font-medium ${badgeClasses}`}
                >
                  {isTrigger ? "Trigger alert" : eventLabel}
                </span>
                <span className="text-xs text-muted">Source: {event.source}</span>
              </div>
              <p className="text-sm leading-6 break-words sm:text-base">
                {event.summary}
              </p>
              {repositoryContext &&
                event.source === "alert" &&
                event.event_type === "alert" && (
                  <a
                    href={`/?${new URLSearchParams({
                      organizationId: String(repositoryContext.organizationId),
                      repositoryId: String(repositoryContext.repositoryId),
                      triggerEventId: String(event.id),
                    })}`}
                    className="mt-3 inline-flex text-sm font-medium text-accent underline underline-offset-4 hover:text-foreground"
                  >
                    Investigate alert
                    <span className="sr-only"> event {event.id}</span>
                  </a>
                )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
