import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.models.repository import Repository
from app.models.webhook_delivery import WebhookDelivery


TEST_WEBHOOK_SECRET = "It's a Secret to Everybody"


def build_signature(payload_body: bytes) -> str:
    digest = hmac.new(
        TEST_WEBHOOK_SECRET.encode("utf-8"),
        payload_body,
        hashlib.sha256,
    ).hexdigest()
    return f"sha256={digest}"


def test_valid_github_webhook_is_accepted(
    client: TestClient,
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
    client: TestClient,
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
    client: TestClient,
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


def test_duplicate_github_delivery_is_stored_once(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "GITHUB_WEBHOOK_SECRET",
        "It's a Secret to Everybody",
    )
    payload_body = b"Hello, World!"
    delivery_id = "duplicate-delivery-001"
    headers = {
        "X-Hub-Signature-256": (
            "sha256=757107ea0eb2509fc211221cce984b8a37570b6d7586c22c46f4379c8b043e17"
        ),
        "X-GitHub-Event": "ping",
        "X-GitHub-Delivery": delivery_id,
    }

    first_response = client.post(
        "/webhooks/github",
        content=payload_body,
        headers=headers,
    )
    second_response = client.post(
        "/webhooks/github",
        content=payload_body,
        headers=headers,
    )

    assert first_response.status_code == 202
    assert first_response.json() == {
        "status": "accepted",
        "event": "ping",
        "delivery_id": delivery_id,
    }
    assert second_response.status_code == 200
    assert second_response.json() == {
        "status": "duplicate",
        "event": "ping",
        "delivery_id": delivery_id,
    }

    statement = select(WebhookDelivery).where(
        WebhookDelivery.delivery_id == delivery_id
    )
    deliveries = list(db_session.scalars(statement))

    assert len(deliveries) == 1
    assert deliveries[0].event == "ping"
    assert deliveries[0].payload_body == payload_body


def test_github_webhook_is_associated_with_known_repository(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", TEST_WEBHOOK_SECRET)

    organization = Organization(name="Test Engineering")
    db_session.add(organization)
    db_session.commit()
    db_session.refresh(organization)

    repository = Repository(
        organization_id=organization.id,
        name="payments-api",
        github_repository_id=1296269,
    )
    db_session.add(repository)
    db_session.commit()
    db_session.refresh(repository)

    payload_body = json.dumps(
        {
            "repository": {
                "id": 1296269,
                "full_name": "some-owner/renamed-payments-api",
            }
        },
        separators=(",", ":"),
    ).encode("utf-8")
    delivery_id = "known-repository-delivery-001"

    response = client.post(
        "/webhooks/github",
        content=payload_body,
        headers={
            "X-Hub-Signature-256": build_signature(payload_body),
            "X-GitHub-Event": "push",
            "X-GitHub-Delivery": delivery_id,
        },
    )

    assert response.status_code == 202

    delivery = db_session.scalar(
        select(WebhookDelivery).where(
            WebhookDelivery.delivery_id == delivery_id
        )
    )
    assert delivery is not None
    assert delivery.repository_id == repository.id
    assert delivery.payload_body == payload_body


def test_github_webhook_for_unknown_repository_is_stored_unmatched(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", TEST_WEBHOOK_SECRET)

    payload_body = json.dumps(
        {"repository": {"id": 987654321}},
        separators=(",", ":"),
    ).encode("utf-8")
    delivery_id = "unknown-repository-delivery-001"

    response = client.post(
        "/webhooks/github",
        content=payload_body,
        headers={
            "X-Hub-Signature-256": build_signature(payload_body),
            "X-GitHub-Event": "push",
            "X-GitHub-Delivery": delivery_id,
        },
    )

    assert response.status_code == 202

    delivery = db_session.scalar(
        select(WebhookDelivery).where(
            WebhookDelivery.delivery_id == delivery_id
        )
    )
    assert delivery is not None
    assert delivery.repository_id is None
    assert delivery.payload_body == payload_body
