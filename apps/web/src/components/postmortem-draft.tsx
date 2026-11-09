"use client";

import { useRef, useState } from "react";

import { formatUtcTimestamp } from "@/lib/format-time";
import type { GroundedStatement, PostmortemDraftPreview } from "@/types/postmortem";

const clockFormatter = new Intl.DateTimeFormat("en-GB", {
  hour: "2-digit", minute: "2-digit", second: "2-digit",
  hourCycle: "h23", timeZone: "UTC",
});
const dayFormatter = new Intl.DateTimeFormat("en-GB", {
  day: "2-digit", month: "short", year: "numeric", timeZone: "UTC",
});

function eventLabel(eventType: string): string {
  switch (eventType) {
    case "push": return "Push";
    case "deployment_status": return "Deployment status";
    case "alert": return "Alert";
    default: return eventType.replace(/_/g, " ") || "Unknown event";
  }
}

type EvidenceSelection = {
  draftId: number;
  eventId: number;
  statementId: string | null;
};

function Statement({ statement, statementId, panelId, selection, onSelect }: {
  statement: GroundedStatement;
  statementId: string;
  panelId: string;
  selection: EvidenceSelection | null;
  onSelect: (eventId: number, statementId: string | null) => void;
}) {
  const isActive = selection?.statementId === statementId;

  return (
    <div
      id={statementId}
      tabIndex={-1}
      className={`-mx-3 scroll-mt-6 rounded-md px-3 py-2 ${isActive ? "bg-accent/5 ring-1 ring-accent/20 ring-inset" : ""}`}
    >
      <p className="max-w-[65ch] text-sm leading-7 wrap-anywhere sm:text-base">
        <span className="whitespace-pre-wrap">{statement.text}</span>{" "}
        {statement.evidence_event_ids.map((eventId, index) => (
          <button
            key={`${eventId}-${index}`}
            type="button"
            aria-label={`Review evidence event #${eventId}`}
            aria-controls={panelId}
            aria-pressed={isActive && selection?.eventId === eventId}
            onClick={() => onSelect(eventId, statementId)}
            className={`my-0.5 mr-1 inline-flex cursor-pointer rounded border px-1.5 py-0.5 align-baseline font-mono text-xs text-accent hover:bg-accent/10 ${isActive && selection?.eventId === eventId ? "border-accent/40 bg-accent/10" : "border-line"}`}
          >
            #{eventId}
          </button>
        ))}
      </p>
    </div>
  );
}

export function PostmortemDraft({ postmortem }: { postmortem: PostmortemDraftPreview }) {
  const headingId = `postmortem-${postmortem.id}`;
  const panelId = `${headingId}-evidence`;
  const content = postmortem.draft;
  const evidence = [...postmortem.evidence].sort(
    (a, b) => Date.parse(a.observed_at) - Date.parse(b.observed_at) || a.id - b.id,
  );
  const panelRef = useRef<HTMLElement>(null);
  const [selection, setSelection] = useState<EvidenceSelection | null>(null);
  const activeSelection = selection?.draftId === postmortem.id ? selection : null;
  const selectedEvent = evidence.find((event) => event.id === activeSelection?.eventId) ?? evidence[0];

  function selectEvidence(eventId: number, statementId: string | null) {
    setSelection({ draftId: postmortem.id, eventId, statementId });
    panelRef.current?.scrollIntoView({ block: "nearest" });
  }

  function renderStatement(statement: GroundedStatement, statementId: string) {
    return (
      <Statement
        statement={statement}
        statementId={statementId}
        panelId={panelId}
        selection={activeSelection}
        onSelect={selectEvidence}
      />
    );
  }

  return (
    <section aria-labelledby={headingId} className="mt-10">
      <header>
        <div className="flex flex-wrap items-center gap-3">
          <h3 id={headingId} className="text-2xl font-medium tracking-tight">Postmortem draft</h3>
          <span className="rounded border border-line px-2 py-1 text-xs text-muted">Version {postmortem.version}</span>
        </div>
        <p className="mt-4 rounded-lg bg-amber-300/10 px-4 py-3 text-sm leading-6 text-amber-200">
          AI-generated · Human review required. Check statements against the saved evidence.
        </p>
      </header>

      <div className="mt-6 grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_18rem] xl:grid-cols-[minmax(0,1fr)_20rem]">
        <article aria-label="Saved postmortem document" className="min-w-0 divide-y divide-line rounded-xl border border-line bg-surface">
          <section aria-labelledby={`${headingId}-summary`} className="p-5 sm:p-6">
            <h4 id={`${headingId}-summary`} className="mb-5 text-lg font-medium">Summary</h4>
            <ul className="space-y-4">
              {content.summary.map((statement, index) => (
                <li key={index}>{renderStatement(statement, `${headingId}-summary-${index}`)}</li>
              ))}
            </ul>
          </section>

          <section aria-labelledby={`${headingId}-timeline`} className="p-5 sm:p-6">
            <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
              <h4 id={`${headingId}-timeline`} className="text-lg font-medium">Timeline</h4>
              <span className="text-xs text-muted">Cited event times · UTC</span>
            </div>
            <ol className="divide-y divide-line">
              {content.timeline.map((statement, index) => {
                const citedEvents = evidence.filter((event) => statement.evidence_event_ids.includes(event.id));
                const singleEvent = citedEvents.length === 1 ? citedEvents[0] : null;
                return (
                  <li key={index} className="grid gap-2 py-4 first:pt-0 last:pb-0 sm:grid-cols-[5.5rem_minmax(0,1fr)] sm:gap-4">
                    <div className="pt-2 font-mono text-xs leading-5 text-muted">
                      {singleEvent ? (
                        <time dateTime={singleEvent.observed_at} title={formatUtcTimestamp(singleEvent.observed_at)}>
                          {clockFormatter.format(new Date(singleEvent.observed_at))}
                          <span className="block text-[10px]">{dayFormatter.format(new Date(singleEvent.observed_at))}</span>
                        </time>
                      ) : "Multiple events"}
                    </div>
                    {renderStatement(statement, `${headingId}-timeline-${index}`)}
                  </li>
                );
              })}
            </ol>
          </section>

          <section aria-labelledby={`${headingId}-gaps`} className="p-5 sm:p-6">
            <h4 id={`${headingId}-gaps`} className="text-lg font-medium">Evidence gaps</h4>
            <p className="mt-2 text-sm leading-6 text-muted">
              Citations provide traceability; they do not automatically verify a claim.
            </p>
            <dl className="mt-4 divide-y divide-line border-t border-line">
              {([
                ["impact", "Impact", content.impact],
                ["root-cause", "Root cause", content.root_cause],
                ["resolution", "Resolution", content.resolution],
              ] as const).map(([key, title, statement]) => (
                <div key={key} className="grid gap-2 py-4 last:pb-0 sm:grid-cols-[6rem_minmax(0,1fr)] sm:gap-4">
                  <dt className="text-sm font-medium">{title}</dt>
                  <dd className="min-w-0">
                    {statement === null ? (
                      <>
                        <p className="text-sm font-medium">Not established</p>
                        <p className="mt-1 text-sm leading-6 text-muted">Not established by available evidence.</p>
                      </>
                    ) : renderStatement(statement, `${headingId}-${key}`)}
                  </dd>
                </div>
              ))}
            </dl>
          </section>

          <section aria-labelledby={`${headingId}-unknowns`} className="p-5 sm:p-6">
            <h4 id={`${headingId}-unknowns`} className="mb-3 text-lg font-medium">Unknowns</h4>
            {content.unknowns.length === 0 ? (
              <p className="text-sm leading-6 text-muted">The draft lists no unknowns.</p>
            ) : (
              <ul className="list-disc space-y-2 pl-5 text-sm leading-7 marker:text-muted">
                {content.unknowns.map((unknown, index) => (
                  <li key={index} className="whitespace-pre-wrap wrap-anywhere">{unknown}</li>
                ))}
              </ul>
            )}
          </section>

          <details className="p-5 sm:p-6">
            <summary className="cursor-pointer text-sm font-medium text-muted">Draft details</summary>
            <dl className="mt-5 grid gap-4 text-sm sm:grid-cols-2">
              <div className="min-w-0"><dt className="text-muted">Model</dt><dd className="mt-1 wrap-anywhere">{postmortem.model}</dd></div>
              <div><dt className="text-muted">Version</dt><dd className="mt-1">{postmortem.version}</dd></div>
              <div><dt className="text-muted">Created (UTC)</dt><dd className="mt-1 leading-6"><time dateTime={postmortem.created_at}>{formatUtcTimestamp(postmortem.created_at)}</time></dd></div>
              <div><dt className="text-muted">Updated (UTC)</dt><dd className="mt-1 leading-6"><time dateTime={postmortem.updated_at}>{formatUtcTimestamp(postmortem.updated_at)}</time></dd></div>
            </dl>
          </details>
        </article>

        <aside ref={panelRef} id={panelId} aria-labelledby={`${panelId}-heading`} className="min-w-0 scroll-mt-6 rounded-xl border border-line bg-surface lg:sticky lg:top-6">
          <header className="border-b border-line p-5">
            <h4 id={`${panelId}-heading`} className="text-lg font-medium">Supporting evidence</h4>
            <p className="mt-1 text-xs leading-5 text-muted">Version {postmortem.version} snapshot · {evidence.length} events</p>
          </header>

          <div aria-live="polite" aria-atomic="true" className="p-5">
            {selectedEvent && (
              <>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h5 className="font-mono text-sm text-accent">Event #{selectedEvent.id}</h5>
                  <span className="rounded border border-line px-2 py-1 text-xs text-muted">{eventLabel(selectedEvent.event_type)}</span>
                </div>
                <p className="mt-4 text-sm leading-7 whitespace-pre-wrap wrap-anywhere">{selectedEvent.summary}</p>
                <dl className="mt-4 grid grid-cols-[4rem_minmax(0,1fr)] gap-x-3 gap-y-3 text-xs leading-5">
                  <dt className="text-muted">Occurred</dt>
                  <dd><time dateTime={selectedEvent.observed_at}>{formatUtcTimestamp(selectedEvent.observed_at)}</time></dd>
                  <dt className="text-muted">Source</dt><dd className="wrap-anywhere">{selectedEvent.source}</dd>
                </dl>
                <p className="mt-4 rounded-md bg-accent/5 px-3 py-2 text-xs leading-5 text-muted">Saved evidence for this draft version.</p>
                {activeSelection?.statementId && (
                  <a href={`#${activeSelection.statementId}`} className="mt-4 inline-flex text-sm text-accent underline underline-offset-4 hover:text-foreground">
                    Return to statement
                  </a>
                )}
              </>
            )}
          </div>

          <div className="border-t border-line p-2">
            <p className="px-3 pt-3 pb-2 text-xs text-muted">All saved evidence · Chronological · UTC</p>
            <ol className="max-h-80 overflow-y-auto p-1">
              {evidence.map((event, index) => (
                <li key={event.id}>
                  {(index === 0 || dayFormatter.format(new Date(event.observed_at)) !== dayFormatter.format(new Date(evidence[index - 1].observed_at))) && (
                    <p className="px-2 pt-3 pb-2 text-[11px] text-muted">{dayFormatter.format(new Date(event.observed_at))}</p>
                  )}
                  <button
                    type="button"
                    aria-label={`Review event #${event.id}, ${eventLabel(event.event_type)}, ${formatUtcTimestamp(event.observed_at)}`}
                    aria-controls={panelId}
                    aria-pressed={selectedEvent?.id === event.id}
                    onClick={() => selectEvidence(event.id, null)}
                    className={`grid w-full cursor-pointer grid-cols-[4.5rem_minmax(0,1fr)_auto] items-center gap-2 rounded-md px-2 py-3 text-left text-xs hover:bg-accent/5 ${selectedEvent?.id === event.id ? "bg-accent/10 text-accent" : "text-muted"}`}
                  >
                    <time dateTime={event.observed_at} className="font-mono text-[11px]">{clockFormatter.format(new Date(event.observed_at))}</time>
                    <span className={`min-w-0 wrap-anywhere ${event.event_type === "alert" ? "text-amber-200" : ""}`}>{eventLabel(event.event_type)}</span>
                    <span className="font-mono text-[11px]">#{event.id}</span>
                  </button>
                </li>
              ))}
            </ol>
          </div>
        </aside>
      </div>
    </section>
  );
}
