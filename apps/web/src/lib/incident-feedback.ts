const creationFeedback = {
  "invalid-selection": {
    title: "Invalid incident selection",
    description:
      "Submit exactly one positive, safe integer for the organization, repository and trigger event. Select an alert investigation and try again.",
  },
  "not-eligible": {
    title: "This event cannot create an incident",
    description: "Choose an eligible alert from the repository timeline.",
  },
  "not-found": {
    title: "Incident resource not found",
    description: "The organization, repository or triggering alert no longer exists.",
  },
  "already-exists": {
    title: "An incident already exists for this alert",
    description: "The backend rejected the duplicate creation request. The existing incident was not changed.",
  },
  "invalid-request": {
    title: "The incident request was rejected",
    description: "The backend did not accept the submitted incident fields. Check the selection before trying again.",
  },
  unavailable: {
    title: "Incident creation is unavailable",
    description: "No creation request was sent. Check OPSREPLAY_API_BASE_URL in the Next.js server environment.",
  },
  uncertain: {
    title: "Incident creation could not be confirmed",
    description: "The incident may already have been saved. Check the backend before submitting again. No automatic retry was made.",
  },
};

export type IncidentCreationErrorCode = keyof typeof creationFeedback;

export function getIncidentCreationFeedback(value: unknown) {
  if (typeof value !== "string" || !Object.hasOwn(creationFeedback, value)) {
    return null;
  }

  return creationFeedback[value as IncidentCreationErrorCode];
}
