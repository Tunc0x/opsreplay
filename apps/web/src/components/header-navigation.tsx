"use client";

import { usePathname, useSearchParams } from "next/navigation";
import Link from "next/link";

import { parsePositiveId } from "@/lib/ids";

export function HeaderNavigation() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const organizationIds = searchParams.getAll("organizationId");
  const repositoryIds = searchParams.getAll("repositoryId");
  const organizationId = organizationIds.length === 1
    ? parsePositiveId(organizationIds[0]) : null;
  const repositoryId = repositoryIds.length === 1
    ? parsePositiveId(repositoryIds[0]) : null;
  const selection = new URLSearchParams();
  if (organizationId !== null) {
    selection.set("organizationId", String(organizationId));
    if (repositoryId !== null) selection.set("repositoryId", String(repositoryId));
  }
  const query = selection.size > 0 ? `?${selection}` : "";
  const isIncidents = pathname === "/incidents" ||
    (pathname === "/" && searchParams.has("incidentId"));

  return (
    <nav aria-label="Application navigation" className="flex gap-6 text-sm font-medium">
      <Link
        href={`/${query}`}
        prefetch={false}
        aria-current={!isIncidents ? "page" : undefined}
        className={`border-b-2 py-2 ${!isIncidents ? "border-accent text-accent" : "border-transparent text-muted hover:text-foreground"}`}
      >
        Investigations
      </Link>
      <Link
        href={`/incidents${query}`}
        prefetch={false}
        aria-current={isIncidents ? "page" : undefined}
        className={`border-b-2 py-2 ${isIncidents ? "border-accent text-accent" : "border-transparent text-muted hover:text-foreground"}`}
      >
        Incidents
      </Link>
    </nav>
  );
}
