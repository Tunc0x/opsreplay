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

const resolutionFeedback = {
  "invalid-selection": {
    title: "Invalid incident resolution selection",
    description:
      "Submit exactly one positive, safe integer for the organization, repository and incident. Open the saved incident and try again.",
  },
  "not-found": {
    title: "Incident to resolve was not found",
    description:
      "The organization, repository or incident is not available at this saved incident URL. Check the selected resource.",
  },
  unavailable: {
    title: "Incident resolution is unavailable",
    description:
      "No resolution request was sent. Check OPSREPLAY_API_BASE_URL in the Next.js server environment, then reload the saved incident.",
  },
  "unexpected-response": {
    title: "Unexpected incident resolution response",
    description:
      "The backend returned an unexpected HTTP response, so resolution was not confirmed. Check the saved incident's current status before submitting again.",
  },
  "invalid-response": {
    title: "Incident resolution response could not be validated",
    description:
      "The response contained invalid or unexpected incident data. The update may have committed. Check the saved incident's current status before submitting again.",
  },
  uncertain: {
    title: "Incident resolution could not be confirmed",
    description:
      "The incident may already be resolved. Reload the saved incident to check its current status before submitting again. No automatic retry was made.",
  },
};

export type IncidentResolutionErrorCode = keyof typeof resolutionFeedback;

export function getIncidentResolutionFeedback(value: unknown) {
  if (typeof value !== "string" || !Object.hasOwn(resolutionFeedback, value)) {
    return null;
  }

  return resolutionFeedback[value as IncidentResolutionErrorCode];
}
