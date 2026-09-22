from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.models.repository import Repository
from app.models.timeline_event import TimelineEvent
from app.models.webhook_delivery import WebhookDelivery


def create_repository(db_session: Session, organization: Organization) -> Repository:
    repository = Repository(
        organization_id=organization.id,
        name="payments-api",
    )
    db_session.add(repository)
    db_session.flush()
    return repository


def test_repository_timeline_returns_events_in_chronological_order_with_evidence(
    client: TestClient,
    db_session: Session,
) -> None:
    organization = Organization(name="Test Engineering")
    db_session.add(organization)
    db_session.flush()
    repository = create_repository(db_session, organization)
    earlier_time = datetime(2026, 9, 20, 9, 0, tzinfo=timezone.utc)
    later_time = datetime(2026, 9, 20, 10, 0, tzinfo=timezone.utc)
    later_delivery = WebhookDelivery(
        delivery_id="github-delivery-later",
        event="push",
        repository_id=repository.id,
        payload_body=b"raw later payload",
    )
    earlier_delivery = WebhookDelivery(
        delivery_id="github-delivery-earlier",
        event="push",
        repository_id=repository.id,
        payload_body=b"raw earlier payload",
    )
    db_session.add_all([later_delivery, earlier_delivery])
    db_session.flush()

    later_event = TimelineEvent(
        repository_id=repository.id,
        webhook_delivery_id=later_delivery.id,
        source="github",
        event_type="push",
        summary="Push to refs/heads/release",
        observed_at=later_time,
    )
    db_session.add(later_event)
    db_session.flush()
    earlier_event = TimelineEvent(
        repository_id=repository.id,
        webhook_delivery_id=earlier_delivery.id,
        source="github",
        event_type="push",
        summary="Push to refs/heads/main",
        observed_at=earlier_time,
    )
    db_session.add(earlier_event)
    db_session.commit()

    response = client.get(
        f"/organizations/{organization.id}/repositories/{repository.id}/timeline"
    )

    assert response.status_code == 200
    events = response.json()
    assert len(events) == 2
    assert "payload_body" not in response.text
    assert "raw later payload" not in response.text
    assert "raw earlier payload" not in response.text
    for event, expected_event, expected_delivery, expected_summary in (
        (events[0], earlier_event, earlier_delivery, "Push to refs/heads/main"),
        (events[1], later_event, later_delivery, "Push to refs/heads/release"),
    ):
        assert set(event) == {
            "id",
            "repository_id",
            "source",
            "event_type",
            "summary",
            "observed_at",
            "created_at",
            "evidence",
        }
        assert event["id"] == expected_event.id
        assert event["repository_id"] == repository.id
        assert event["source"] == "github"
        assert event["event_type"] == "push"
        assert event["summary"] == expected_summary
        assert datetime.fromisoformat(
            event["observed_at"].replace("Z", "+00:00")
        ) == expected_event.observed_at
        assert event["created_at"] is not None
        assert event["evidence"] == {
            "webhook_delivery_id": expected_delivery.id,
            "github_delivery_id": expected_delivery.delivery_id,
        }


def test_repository_timeline_for_empty_repository_returns_empty_list(
    client: TestClient,
    db_session: Session,
) -> None:
    organization = Organization(name="Empty Engineering")
    db_session.add(organization)
    db_session.flush()
    repository = create_repository(db_session, organization)
    db_session.commit()

    response = client.get(
        f"/organizations/{organization.id}/repositories/{repository.id}/timeline"
    )

    assert response.status_code == 200
    assert response.json() == []


def test_repository_timeline_rejects_repository_from_another_organization(
    client: TestClient,
    db_session: Session,
) -> None:
    organization_a = Organization(name="Organization A")
    organization_b = Organization(name="Organization B")
    db_session.add_all([organization_a, organization_b])
    db_session.flush()
    repository = create_repository(db_session, organization_a)
    db_session.commit()

    response = client.get(
        f"/organizations/{organization_b.id}/repositories/{repository.id}/timeline"
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Repository not found"}
