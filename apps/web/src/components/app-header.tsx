import { Suspense } from "react";
import Link from "next/link";

import { HeaderNavigation } from "@/components/header-navigation";

export function AppHeader() {
  return (
    <header className="border-b border-line">
      <div className="mx-auto flex w-full max-w-6xl flex-col items-start gap-4 px-6 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-8">
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
        <Suspense fallback={
          <nav aria-label="Application navigation" className="flex gap-6 py-2 text-sm font-medium text-muted">
            <Link href="/" prefetch={false}>Investigations</Link>
            <Link href="/incidents" prefetch={false}>Incidents</Link>
          </nav>
        }>
          <HeaderNavigation />
        </Suspense>
      </div>
    </header>
  );
}
