import hashlib
import hmac
import json


def verify_github_signature(
    payload_body: bytes,
    secret: str,
    signature_header: str | None,
) -> bool:
    if signature_header is None:
        return False

    digest = hmac.new(
        secret.encode("utf-8"),
        payload_body,
        hashlib.sha256,
    ).hexdigest()
    expected_signature = f"sha256={digest}"

    return hmac.compare_digest(expected_signature, signature_header)


def extract_github_repository_id(payload_body: bytes) -> int | None:
    try:
        payload = json.loads(payload_body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None

    if not isinstance(payload, dict):
        return None

    repository = payload.get("repository")
    if not isinstance(repository, dict):
        return None

    repository_id = repository.get("id")
    if type(repository_id) is not int:
        return None

    return repository_id
