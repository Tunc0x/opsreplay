"use client";

import { useFormStatus } from "react-dom";

export function GeneratePostmortemButton() {
  const { pending } = useFormStatus();

  return (
    <>
      <button
        type="submit"
        disabled={pending}
        aria-busy={pending}
        aria-describedby="postmortem-generation-help"
        className="mt-4 min-h-11 cursor-pointer rounded-md bg-accent px-4 py-2 text-sm font-medium text-background hover:bg-accent/90 disabled:cursor-wait disabled:opacity-60"
      >
        {pending ? "Generating..." : "Generate postmortem draft"}
      </button>
      <span role="status" className="sr-only">{pending ? "Generating a postmortem draft." : ""}</span>
    </>
  );
}
