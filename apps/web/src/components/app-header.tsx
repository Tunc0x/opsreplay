export function AppHeader() {
  return (
    <header className="border-b border-line">
      <div className="mx-auto flex w-full max-w-6xl items-center px-6 py-5 sm:px-8">
        <span className="inline-flex items-center gap-2 text-xl font-semibold tracking-tight">
          <svg
            viewBox="0 0 40 40"
            className="size-8 shrink-0 text-accent"
            aria-hidden="true"
          >
            <path
              d="M12 13a11 11 0 1 1-3 12M8 9v9h9"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <path d="m18 15 8 5-8 5Z" fill="currentColor" />
          </svg>
          OpsReplay
        </span>
      </div>
    </header>
  );
}
