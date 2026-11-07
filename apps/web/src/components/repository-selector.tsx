import type { RepositoryOption } from "@/types/repository";

type RepositorySelectorProps = {
  organizationId: number | null;
  repositories: readonly RepositoryOption[] | null;
  selectedRepositoryId: number | null;
};

export function RepositorySelector({
  organizationId,
  repositories,
  selectedRepositoryId,
}: RepositorySelectorProps) {
  return (
    <section
      aria-labelledby="repository-selector-heading"
      className="mb-10 rounded-xl border border-line bg-surface p-6 sm:p-8"
    >
      <h2 id="repository-selector-heading" className="text-lg font-medium">
        Choose a repository
      </h2>
      <p id="organization-id-help" className="mt-2 text-sm leading-6 text-muted">
        Enter an organization ID to load its repositories, then choose one by name.
      </p>

      <form
        action="/"
        method="get"
        className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-end"
      >
        <div className="min-w-0 flex-1">
          <label
            htmlFor="organization-id"
            className="mb-2 block text-sm font-medium"
          >
            Organization ID
          </label>
          <input
            id="organization-id"
            name="organizationId"
            type="number"
            min={1}
            max={Number.MAX_SAFE_INTEGER}
            step={1}
            required
            defaultValue={organizationId ?? ""}
            aria-describedby="organization-id-help"
            className="min-h-11 w-full rounded-md border border-line bg-background px-3 py-2 text-base"
          />
        </div>
        <button
          type="submit"
          className="min-h-11 cursor-pointer rounded-md bg-accent px-4 py-2 text-sm font-medium text-background hover:bg-accent/90"
        >
          Load repositories
        </button>
      </form>

      {organizationId !== null && repositories !== null &&
        (repositories.length === 0 ? (
          <p className="mt-6 text-sm leading-6 text-muted">
            This organization has no repositories. Load another organization to
            continue.
          </p>
        ) : (
          <form
            action="/"
            method="get"
            className="mt-6 flex flex-col gap-3 border-t border-line pt-6 sm:flex-row sm:items-end"
          >
            <input type="hidden" name="organizationId" value={organizationId} />
            <div className="min-w-0 flex-1">
              <label
                htmlFor="repository-id"
                className="mb-2 block text-sm font-medium"
              >
                Repository
              </label>
              <select
                id="repository-id"
                name="repositoryId"
                required
                defaultValue={selectedRepositoryId ?? ""}
                className="min-h-11 w-full min-w-0 rounded-md border border-line bg-background px-3 py-2 text-base"
              >
                <option value="" disabled>
                  Choose a repository
                </option>
                {repositories.map((repository) => (
                  <option key={repository.id} value={repository.id}>
                    {repository.name}
                  </option>
                ))}
              </select>
            </div>
            <button
              type="submit"
              className="min-h-11 cursor-pointer rounded-md bg-accent px-4 py-2 text-sm font-medium text-background hover:bg-accent/90"
            >
              View timeline
            </button>
          </form>
        ))}
    </section>
  );
}
