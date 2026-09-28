import hashlib
import hmac
import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.alert_delivery import AlertDelivery
from app.models.organization import Organization
from app.models.repository import Repository
from app.models.timeline_event import TimelineEvent
from app.models.webhook_delivery import WebhookDelivery


TEST_SECRET = "local alert signing secret"
OBSERVED_AT = datetime(2026, 9, 28, 10, 0, tzinfo=timezone.utc)


def create_repository(db_session: Session) -> Repository:
    organization = Organization(name="Alert test organization")
    db_session.add(organization)
    db_session.flush()
    repository = Repository(
        organization_id=organization.id,
        name="payments-api",
    )
    db_session.add(repository)
    db_session.commit()
    db_session.refresh(repository)
    return repository


def alert_body(repository_id: int) -> bytes:
    return json.dumps(
        {
            "repository_id": repository_id,
            "severity": "critical",
            "title": "Elevated production 5xx rate",
            "observed_at": OBSERVED_AT.isoformat(),
        }
    ).encode("utf-8")


def signed_headers(event_id: str, body: bytes) -> dict[str, str]:
    digest = hmac.new(
        TEST_SECRET.encode("utf-8"), body, hashlib.sha256
    ).hexdigest()
    return {
        "X-OpsReplay-Signature-256": f"sha256={digest}",
        "X-OpsReplay-Event-ID": event_id,
    }


def test_valid_alert_creates_raw_evidence_and_timeline_event(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ALERT_WEBHOOK_SECRET", TEST_SECRET)
    repository = create_repository(db_session)
    body = alert_body(repository.id)

    response = client.post(
        "/webhooks/alerts",
        content=body,
        headers=signed_headers("alert-test-001", body),
    )

    assert response.status_code == 202
    assert response.json() == {
        "status": "accepted",
        "event_id": "alert-test-001",
        "repository_id": repository.id,
    }
    deliveries = list(db_session.scalars(select(AlertDelivery)))
    assert len(deliveries) == 1
    delivery = deliveries[0]
    assert delivery.external_event_id == "alert-test-001"
    assert delivery.payload_body == body
    events = list(
        db_session.scalars(
            select(TimelineEvent).where(
                TimelineEvent.alert_delivery_id == delivery.id
            )
        )
    )
    assert len(events) == 1
    event = events[0]
    assert event.repository_id == repository.id
    assert event.source == "alert"
    assert event.event_type == "alert"
    assert event.summary == "CRITICAL: Elevated production 5xx rate"
    assert event.observed_at == OBSERVED_AT
    assert event.webhook_delivery_id is None


def test_duplicate_alert_is_stored_once(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ALERT_WEBHOOK_SECRET", TEST_SECRET)
    repository = create_repository(db_session)
    body = alert_body(repository.id)
    headers = signed_headers("alert-test-duplicate-001", body)

    first_response = client.post(
        "/webhooks/alerts", content=body, headers=headers
    )
    second_response = client.post(
        "/webhooks/alerts", content=body, headers=headers
    )

    assert first_response.status_code == 202
    assert first_response.json() == {
        "status": "accepted",
        "event_id": "alert-test-duplicate-001",
        "repository_id": repository.id,
    }
    assert second_response.status_code == 200
    assert second_response.json() == {
        "status": "duplicate",
        "event_id": "alert-test-duplicate-001",
        "repository_id": repository.id,
    }
    deliveries = list(db_session.scalars(select(AlertDelivery)))
    assert len(deliveries) == 1
    events = list(
        db_session.scalars(
            select(TimelineEvent).where(
                TimelineEvent.alert_delivery_id == deliveries[0].id
            )
        )
    )
    assert len(events) == 1


def test_alert_with_invalid_signature_is_rejected(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ALERT_WEBHOOK_SECRET", TEST_SECRET)
    repository = create_repository(db_session)

    response = client.post(
        "/webhooks/alerts",
        content=alert_body(repository.id),
        headers={
            "X-OpsReplay-Signature-256": "sha256=invalid",
            "X-OpsReplay-Event-ID": "alert-test-invalid-001",
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Invalid alert webhook signature"}
    assert db_session.scalar(select(AlertDelivery)) is None
    assert db_session.scalar(select(TimelineEvent)) is None


def test_repository_timeline_returns_github_and_alert_evidence(
    client: TestClient,
    db_session: Session,
) -> None:
    repository = create_repository(db_session)
    github_time = datetime(2026, 9, 28, 11, 0, tzinfo=timezone.utc)
    alert_time = datetime(2026, 9, 28, 9, 0, tzinfo=timezone.utc)
    github_delivery = WebhookDelivery(
        delivery_id="github-mixed-001",
        repository_id=repository.id,
        event="push",
        payload_body=b"private github payload",
    )
    alert_delivery = AlertDelivery(
        external_event_id="alert-mixed-001",
        repository_id=repository.id,
        severity="critical",
        title="Elevated production 5xx rate",
        observed_at=alert_time,
        payload_body=b"private alert payload",
    )
    db_session.add_all([github_delivery, alert_delivery])
    db_session.flush()
    db_session.add_all(
        [
            TimelineEvent(
                repository_id=repository.id,
                webhook_delivery_id=github_delivery.id,
                source="github",
                event_type="push",
                summary="Push to refs/heads/main",
                observed_at=github_time,
            ),
            TimelineEvent(
                repository_id=repository.id,
                alert_delivery_id=alert_delivery.id,
                source="alert",
                event_type="alert",
                summary="CRITICAL: Elevated production 5xx rate",
                observed_at=alert_time,
            ),
        ]
    )
    db_session.commit()

    response = client.get(
        f"/organizations/{repository.organization_id}/repositories/"
        f"{repository.id}/timeline"
    )

    assert response.status_code == 200
    events = response.json()
    assert len(events) == 2
    assert [event["source"] for event in events] == ["alert", "github"]
    assert events[0]["evidence"] == {
        "kind": "alert_webhook",
        "alert_delivery_id": alert_delivery.id,
        "external_event_id": alert_delivery.external_event_id,
    }
    assert events[1]["evidence"] == {
        "kind": "github_webhook",
        "webhook_delivery_id": github_delivery.id,
        "github_delivery_id": github_delivery.delivery_id,
    }
    assert "private alert payload" not in response.text
    assert "private github payload" not in response.text
    assert "payload_body" not in response.text


def test_alert_for_missing_repository_is_rejected(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ALERT_WEBHOOK_SECRET", TEST_SECRET)
    body = alert_body(999_999)

    response = client.post(
        "/webhooks/alerts",
        content=body,
        headers=signed_headers("alert-test-missing-repo-001", body),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Repository not found"}
    assert db_session.scalar(select(AlertDelivery)) is None
    assert db_session.scalar(select(TimelineEvent)) is None
