from app.cli.dev import (
    _build_deployment_status_payload,
    _build_push_payload,
    _json_body,
    _sign_body,
)

def test_sign_body_uses_hmac_sha256() -> None:
    body = b'{"hello":"world"}'

    signature = _sign_body(
        "test-secret",
        body,
    )

    assert signature == (
        "sha256="
        "84cc33df716ed0b0598f07437c94069a"
        "ce3730358778a592bd6bbd1423d111f3"
    )

def test_json_body_is_compact_utf8_json() -> None:
    body = _json_body(
        {
            "ref": "refs/heads/main",
        }
    )

    assert body == b'{"ref":"refs/heads/main"}'


def test_build_push_payload() -> None:
    payload = _build_push_payload(
        12345,
        "refs/heads/main",
        "1" * 40,
        "2" * 40,
    )

    assert payload == {
        "ref": "refs/heads/main",
        "before": "1" * 40,
        "after": "2" * 40,
        "repository": {
            "id": 12345,
        },
    }

def test_build_deployment_status_payload() -> None:
    payload = _build_deployment_status_payload(
        12345,
        999,
        "success",
        "production",
    )

    assert payload == {
        "action": "created",
        "deployment": {
            "id": 999,
        },
        "deployment_status": {
            "state": "success",
            "environment": "production",
        },
        "repository": {
            "id": 12345,
        },
    }