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
