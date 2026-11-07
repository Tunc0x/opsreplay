type EmptyStateProps = {
  title: string;
  description: string;
};

export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <section className="flex min-h-80 flex-col items-center justify-center rounded-xl border border-line bg-surface px-6 py-12 text-center sm:min-h-96 sm:px-12">
      <div className="mb-6 flex size-12 items-center justify-center rounded-xl bg-accent/10 text-accent">
        <svg
          viewBox="0 0 24 24"
          className="size-6"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <rect x="5" y="3" width="14" height="18" rx="2" />
          <path d="M9 8h6M9 12h6M9 16h3" />
        </svg>
      </div>
      <h2 className="max-w-md text-lg font-medium text-balance sm:text-xl">
        {title}
      </h2>
      <p className="mt-3 max-w-md text-sm leading-6 text-muted sm:text-base sm:leading-7">
        {description}
      </p>
    </section>
  );
}
