from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.alert_delivery import AlertDelivery
from app.models.incident import Incident
from app.models.organization import Organization
from app.models.repository import Repository
from app.models.timeline_event import TimelineEvent
from app.models.webhook_delivery import WebhookDelivery


TRIGGER_TIME = datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc)


def create_organization(db_session: Session) -> Organization:
    organization = Organization(name="Incident test organization")
    db_session.add(organization)
    db_session.flush()
    return organization


def create_repository(
    db_session: Session,
    organization: Organization,
    name: str,
) -> Repository:
    repository = Repository(organization_id=organization.id, name=name)
    db_session.add(repository)
    db_session.flush()
    return repository


def add_alert_event(
    db_session: Session,
    repository: Repository,
    external_event_id: str,
    observed_at: datetime,
) -> tuple[TimelineEvent, AlertDelivery]:
    delivery = AlertDelivery(
        external_event_id=external_event_id,
        repository_id=repository.id,
        severity="critical",
        title="Elevated production 5xx rate",
        observed_at=observed_at,
        payload_body=f"private {external_event_id}".encode("utf-8"),
    )
    db_session.add(delivery)
    db_session.flush()
    event = TimelineEvent(
        repository_id=repository.id,
        alert_delivery_id=delivery.id,
        source="alert",
        event_type="alert",
        summary="CRITICAL: Elevated production 5xx rate",
        observed_at=observed_at,
    )
    db_session.add(event)
    db_session.flush()
    return event, delivery


def add_github_event(
    db_session: Session,
    repository: Repository,
    delivery_id: str,
    observed_at: datetime,
) -> tuple[TimelineEvent, WebhookDelivery]:
    delivery = WebhookDelivery(
        delivery_id=delivery_id,
        repository_id=repository.id,
        event="push",
        payload_body=f"private {delivery_id}".encode("utf-8"),
    )
    db_session.add(delivery)
    db_session.flush()
    event = TimelineEvent(
        repository_id=repository.id,
        webhook_delivery_id=delivery.id,
        source="github",
        event_type="push",
        summary="Push to refs/heads/main",
        observed_at=observed_at,
    )
    db_session.add(event)
    db_session.flush()
    return event, delivery


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def test_create_incident_from_alert_persists_window_and_context(
    client: TestClient,
    db_session: Session,
) -> None:
    organization = create_organization(db_session)
    repository = create_repository(db_session, organization, "payments-api")
    github_event, github_delivery = add_github_event(
        db_session,
        repository,
        "incident-github-before-001",
        TRIGGER_TIME - timedelta(minutes=10),
    )
    trigger, alert_delivery = add_alert_event(
        db_session,
        repository,
        "incident-alert-trigger-001",
        TRIGGER_TIME,
    )
    db_session.commit()

    response = client.post(
        f"/organizations/{organization.id}/repositories/{repository.id}/incidents",
        json={
            "trigger_timeline_event_id": trigger.id,
            "lookback_minutes": 30,
            "lookahead_minutes": 15,
        },
    )

    assert response.status_code == 201
    incidents = list(db_session.scalars(select(Incident)))
    assert len(incidents) == 1
    incident = incidents[0]
    assert incident.repository_id == repository.id
    assert incident.trigger_timeline_event_id == trigger.id
    assert incident.lookback_minutes == 30
    assert incident.lookahead_minutes == 15
    result = response.json()
    assert result["id"] == incident.id
    assert result["repository_id"] == repository.id
    assert result["trigger_timeline_event_id"] == trigger.id
    assert result["lookback_minutes"] == 30
    assert result["lookahead_minutes"] == 15
    assert result["context"]["trigger_event_id"] == trigger.id
    assert parse_time(result["context"]["window_start"]) == (
        TRIGGER_TIME - timedelta(minutes=30)
    )
    assert parse_time(result["context"]["window_end"]) == (
        TRIGGER_TIME + timedelta(minutes=15)
    )
    assert [event["id"] for event in result["context"]["events"]] == [
        github_event.id,
        trigger.id,
    ]
    assert [event["evidence"] for event in result["context"]["events"]] == [
        {
            "kind": "github_webhook",
            "webhook_delivery_id": github_delivery.id,
            "github_delivery_id": github_delivery.delivery_id,
        },
        {
            "kind": "alert_webhook",
            "alert_delivery_id": alert_delivery.id,
            "external_event_id": alert_delivery.external_event_id,
        },
    ]


def test_get_incident_uses_persisted_window_and_live_timeline(
    client: TestClient,
    db_session: Session,
) -> None:
    organization = create_organization(db_session)
    repository = create_repository(db_session, organization, "customer-api")
    trigger, _ = add_alert_event(
        db_session,
        repository,
        "incident-live-trigger-001",
        TRIGGER_TIME,
    )
    db_session.commit()
    create_response = client.post(
        f"/organizations/{organization.id}/repositories/{repository.id}/incidents",
        json={
            "trigger_timeline_event_id": trigger.id,
            "lookback_minutes": 30,
            "lookahead_minutes": 0,
        },
    )
    assert create_response.status_code == 201
    incident_id = create_response.json()["id"]

    later_arriving_event, _ = add_github_event(
        db_session,
        repository,
        "incident-live-github-001",
        TRIGGER_TIME - timedelta(minutes=20),
    )
    db_session.commit()

    response = client.get(
        f"/organizations/{organization.id}/repositories/{repository.id}/"
        f"incidents/{incident_id}"
    )

    assert response.status_code == 200
    result = response.json()
    assert result["lookback_minutes"] == 30
    assert result["lookahead_minutes"] == 0
    assert [event["id"] for event in result["context"]["events"]] == [
        later_arriving_event.id,
        trigger.id,
    ]


def test_create_incident_rejects_non_alert_trigger(
    client: TestClient,
    db_session: Session,
) -> None:
    organization = create_organization(db_session)
    repository = create_repository(db_session, organization, "push-api")
    push, _ = add_github_event(
        db_session,
        repository,
        "incident-non-alert-001",
        TRIGGER_TIME,
    )
    db_session.commit()

    response = client.post(
        f"/organizations/{organization.id}/repositories/{repository.id}/incidents",
        json={"trigger_timeline_event_id": push.id},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Timeline event is not an alert"}
    assert db_session.scalar(select(Incident)) is None


def test_duplicate_incident_for_same_alert_returns_conflict(
    client: TestClient,
    db_session: Session,
) -> None:
    organization = create_organization(db_session)
    repository = create_repository(db_session, organization, "duplicate-api")
    trigger, _ = add_alert_event(
        db_session,
        repository,
        "incident-duplicate-alert-001",
        TRIGGER_TIME,
    )
    db_session.commit()
    url = (
        f"/organizations/{organization.id}/repositories/{repository.id}/incidents"
    )
    request_body = {"trigger_timeline_event_id": trigger.id}

    first_response = client.post(url, json=request_body)
    second_response = client.post(url, json=request_body)

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json() == {
        "detail": "Incident already exists for this alert"
    }
    incidents = list(
        db_session.scalars(
            select(Incident).where(
                Incident.trigger_timeline_event_id == trigger.id
            )
        )
    )
    assert len(incidents) == 1


def test_incident_from_another_repository_returns_404(
    client: TestClient,
    db_session: Session,
) -> None:
    organization = create_organization(db_session)
    repository_a = create_repository(db_session, organization, "repository-a")
    repository_b = create_repository(db_session, organization, "repository-b")
    trigger, _ = add_alert_event(
        db_session,
        repository_a,
        "incident-other-repository-001",
        TRIGGER_TIME,
    )
    db_session.commit()
    create_response = client.post(
        f"/organizations/{organization.id}/repositories/{repository_a.id}/incidents",
        json={"trigger_timeline_event_id": trigger.id},
    )
    assert create_response.status_code == 201
    incident_id = create_response.json()["id"]

    response = client.get(
        f"/organizations/{organization.id}/repositories/{repository_b.id}/"
        f"incidents/{incident_id}"
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Incident not found"}


def test_new_incident_is_open_and_unresolved(
    client: TestClient,
    db_session: Session,
) -> None:
    organization = create_organization(db_session)
    repository = create_repository(db_session, organization, "new-incident-api")
    trigger, _ = add_alert_event(
        db_session,
        repository,
        "incident-new-open-alert-001",
        TRIGGER_TIME,
    )
    db_session.commit()

    response = client.post(
        f"/organizations/{organization.id}/repositories/{repository.id}/incidents",
        json={"trigger_timeline_event_id": trigger.id},
    )

    assert response.status_code == 201
    result = response.json()
    assert result["status"] == "open"
    assert result["resolved_at"] is None
    db_incident = db_session.scalar(
        select(Incident).where(
            Incident.trigger_timeline_event_id == trigger.id
        )
    )
    assert db_incident is not None
    assert db_incident.status == "open"
    assert db_incident.resolved_at is None


def test_resolve_incident_sets_status_and_resolution_timestamp(
    client: TestClient,
    db_session: Session,
) -> None:
    organization = create_organization(db_session)
    repository = create_repository(db_session, organization, "resolve-api")
    trigger, _ = add_alert_event(
        db_session,
        repository,
        "incident-resolve-alert-001",
        TRIGGER_TIME,
    )
    db_session.commit()
    create_response = client.post(
        f"/organizations/{organization.id}/repositories/{repository.id}/incidents",
        json={"trigger_timeline_event_id": trigger.id},
    )
    assert create_response.status_code == 201
    incident_id = create_response.json()["id"]

    response = client.post(
        f"/organizations/{organization.id}/repositories/{repository.id}/"
        f"incidents/{incident_id}/resolve"
    )

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "resolved"
    assert result["resolved_at"] is not None
    assert result["context"]["trigger_event_id"] == trigger.id
    db_incident = db_session.get(Incident, incident_id)
    assert db_incident is not None
    db_session.refresh(db_incident)
    assert db_incident.status == "resolved"
    assert db_incident.resolved_at is not None
    assert db_incident.resolved_at.utcoffset() is not None
    assert parse_time(result["resolved_at"]) == db_incident.resolved_at


def test_resolving_incident_again_is_idempotent(
    client: TestClient,
    db_session: Session,
) -> None:
    organization = create_organization(db_session)
    repository = create_repository(db_session, organization, "idempotent-api")
    trigger, _ = add_alert_event(
        db_session,
        repository,
        "incident-idempotent-alert-001",
        TRIGGER_TIME,
    )
    db_session.commit()
    create_response = client.post(
        f"/organizations/{organization.id}/repositories/{repository.id}/incidents",
        json={"trigger_timeline_event_id": trigger.id},
    )
    assert create_response.status_code == 201
    incident_id = create_response.json()["id"]
    resolve_url = (
        f"/organizations/{organization.id}/repositories/{repository.id}/"
        f"incidents/{incident_id}/resolve"
    )

    first_response = client.post(resolve_url)
    second_response = client.post(resolve_url)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    first_result = first_response.json()
    second_result = second_response.json()
    assert second_result["status"] == "resolved"
    assert second_result["resolved_at"] == first_result["resolved_at"]
    incidents = list(
        db_session.scalars(
            select(Incident).where(
                Incident.trigger_timeline_event_id == trigger.id
            )
        )
    )
    assert len(incidents) == 1


def test_resolve_incident_from_another_repository_returns_404(
    client: TestClient,
    db_session: Session,
) -> None:
    organization = create_organization(db_session)
    repository_a = create_repository(db_session, organization, "resolve-a")
    repository_b = create_repository(db_session, organization, "resolve-b")
    trigger, _ = add_alert_event(
        db_session,
        repository_a,
        "incident-wrong-repository-alert-001",
        TRIGGER_TIME,
    )
    db_session.commit()
    create_response = client.post(
        f"/organizations/{organization.id}/repositories/{repository_a.id}/incidents",
        json={"trigger_timeline_event_id": trigger.id},
    )
    assert create_response.status_code == 201
    incident_id = create_response.json()["id"]

    response = client.post(
        f"/organizations/{organization.id}/repositories/{repository_b.id}/"
        f"incidents/{incident_id}/resolve"
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Incident not found"}
    db_incident = db_session.get(Incident, incident_id)
    assert db_incident is not None
    db_session.refresh(db_incident)
    assert db_incident.status == "open"
    assert db_incident.resolved_at is None
