import json


class GitHubPushProcessingError(ValueError):
    """A GitHub push payload cannot be normalized safely."""


def extract_github_push_ref(payload_body: bytes) -> str:
    try:
        payload = json.loads(payload_body)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise GitHubPushProcessingError(
            "The GitHub push payload is not valid JSON."
        ) from error

    if not isinstance(payload, dict):
        raise GitHubPushProcessingError(
            "The GitHub push payload must be a JSON object."
        )

    ref = payload.get("ref")
    if not isinstance(ref, str) or not ref:
        raise GitHubPushProcessingError(
            "The GitHub push payload requires a non-empty ref."
        )
    if not isinstance(payload.get("before"), str):
        raise GitHubPushProcessingError(
            "The GitHub push payload requires a string before value."
        )
    if not isinstance(payload.get("after"), str):
        raise GitHubPushProcessingError(
            "The GitHub push payload requires a string after value."
        )

    return ref


def extract_github_deployment_status(
    payload_body: bytes,
) -> tuple[str, str]:
    """Return the deployment status state and environment."""
    try:
        payload = json.loads(payload_body)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise GitHubPushProcessingError(
            "The GitHub deployment_status payload is not valid JSON."
        ) from error

    if not isinstance(payload, dict):
        raise GitHubPushProcessingError(
            "The GitHub deployment_status payload must be a JSON object."
        )
    if payload.get("action") != "created":
        raise GitHubPushProcessingError(
            "The GitHub deployment_status action must be created."
        )

    deployment = payload.get("deployment")
    if not isinstance(deployment, dict):
        raise GitHubPushProcessingError(
            "The GitHub deployment_status payload requires a deployment object."
        )
    if type(deployment.get("id")) is not int:
        raise GitHubPushProcessingError(
            "The GitHub deployment_status deployment.id must be an integer."
        )

    deployment_status = payload.get("deployment_status")
    if not isinstance(deployment_status, dict):
        raise GitHubPushProcessingError(
            "The GitHub deployment_status payload requires a deployment_status object."
        )
    state = deployment_status.get("state")
    if not isinstance(state, str) or not state:
        raise GitHubPushProcessingError(
            "The GitHub deployment_status state must be a non-empty string."
        )
    environment = deployment_status.get("environment")
    if not isinstance(environment, str) or not environment:
        raise GitHubPushProcessingError(
            "The GitHub deployment_status environment must be a non-empty string."
        )

    return state, environment
