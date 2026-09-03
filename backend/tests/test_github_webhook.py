import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_valid_github_webhook_is_accepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "GITHUB_WEBHOOK_SECRET",
        "It's a Secret to Everybody",
    )

    response = client.post(
        "/webhooks/github",
        content=b"Hello, World!",
        headers={
            "X-Hub-Signature-256": (
                "sha256=757107ea0eb2509fc211221cce984b8a37570b6d7586c22c46f4379c8b043e17"
            ),
            "X-GitHub-Event": "ping",
            "X-GitHub-Delivery": "test-delivery-001",
        },
    )

    assert response.status_code == 202
    assert response.json() == {
        "status": "accepted",
        "event": "ping",
        "delivery_id": "test-delivery-001",
    }


def test_github_webhook_with_invalid_signature_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "GITHUB_WEBHOOK_SECRET",
        "It's a Secret to Everybody",
    )

    response = client.post(
        "/webhooks/github",
        content=b"invalid signature payload",
        headers={
            "X-Hub-Signature-256": "sha256=invalid",
            "X-GitHub-Event": "push",
            "X-GitHub-Delivery": "test-delivery-002",
        },
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Invalid GitHub webhook signature"
    }


def test_github_webhook_without_signature_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "GITHUB_WEBHOOK_SECRET",
        "It's a Secret to Everybody",
    )

    response = client.post(
        "/webhooks/github",
        content=b"missing signature payload",
        headers={
            "X-GitHub-Event": "push",
            "X-GitHub-Delivery": "test-delivery-003",
        },
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Invalid GitHub webhook signature"
    }
