import hashlib
import hmac


def verify_alert_signature(
    payload_body: bytes,
    secret: str,
    signature_header: str | None,
) -> bool:
    if signature_header is None:
        return False

    digest = hmac.new(
        secret.encode("utf-8"), payload_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={digest}", signature_header)
