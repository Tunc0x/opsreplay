from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.alert_delivery import AlertDelivery
from app.models.organization import Organization
from app.models.repository import Repository
from app.models.timeline_event import TimelineEvent
from app.models.webhook_delivery import WebhookDelivery


TRIGGER_TIME = datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc)


def create_organization(db_session: Session) -> Organization:
    organization = Organization(name="Investigation organization")
    db_session.add(organization)
    db_session.flush()
    return organization


def create_repository(
    db_session: Session, organization: Organization, name: str
) -> Repository:
    repository = Repository(organization_id=organization.id, name=name)
    db_session.add(repository)
    db_session.flush()
    return repository


def add_github_event(
    db_session: Session,
    repository: Repository,
    delivery_id: str,
    observed_at: datetime,
    event_type: str = "push",
) -> tuple[TimelineEvent, WebhookDelivery]:
    delivery = WebhookDelivery(
        delivery_id=delivery_id,
        repository_id=repository.id,
        event=event_type,
        payload_body=f"private payload {delivery_id}".encode("utf-8"),
    )
    db_session.add(delivery)
    db_session.flush()
    event = TimelineEvent(
        repository_id=repository.id,
        webhook_delivery_id=delivery.id,
        source="github",
        event_type=event_type,
        summary=f"GitHub {event_type}",
        observed_at=observed_at,
    )
    db_session.add(event)
    db_session.flush()
    return event, delivery


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
        title="Elevated 5xx rate",
        observed_at=observed_at,
        payload_body=f"private payload {external_event_id}".encode("utf-8"),
    )
    db_session.add(delivery)
    db_session.flush()
    event = TimelineEvent(
        repository_id=repository.id,
        alert_delivery_id=delivery.id,
        source="alert",
        event_type="alert",
        summary="CRITICAL: Elevated 5xx rate",
        observed_at=observed_at,
    )
    db_session.add(event)
    db_session.flush()
    return event, delivery


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def test_alert_context_returns_events_inside_window_in_chronological_order(
    client: TestClient,
    db_session: Session,
) -> None:
    organization = create_organization(db_session)
    repository = create_repository(db_session, organization, "payments-api")

    add_github_event(
        db_session,
        repository,
        "github-after-31",
        TRIGGER_TIME + timedelta(minutes=31),
    )
    after, after_delivery = add_alert_event(
        db_session,
        repository,
        "alert-after-10",
        TRIGGER_TIME + timedelta(minutes=10),
    )
    trigger, trigger_delivery = add_alert_event(
        db_session, repository, "alert-trigger", TRIGGER_TIME
    )
    deployment, deployment_delivery = add_github_event(
        db_session,
        repository,
        "github-before-5",
        TRIGGER_TIME - timedelta(minutes=5),
        event_type="deployment_status",
    )
    before, before_delivery = add_github_event(
        db_session,
        repository,
        "github-before-20",
        TRIGGER_TIME - timedelta(minutes=20),
    )
    add_github_event(
        db_session,
        repository,
        "github-before-31",
        TRIGGER_TIME - timedelta(minutes=31),
    )
    db_session.commit()

    response = client.get(
        f"/organizations/{organization.id}/repositories/{repository.id}/"
        f"timeline/{trigger.id}/context"
    )

    assert response.status_code == 200
    context = response.json()
    assert context["repository_id"] == repository.id
    assert context["trigger_event_id"] == trigger.id
    assert parse_time(context["window_start"]) == TRIGGER_TIME - timedelta(
        minutes=30
    )
    assert parse_time(context["window_end"]) == TRIGGER_TIME + timedelta(
        minutes=30
    )
    events = context["events"]
    assert [event["id"] for event in events] == [
        before.id,
        deployment.id,
        trigger.id,
        after.id,
    ]
    assert [parse_time(event["observed_at"]) for event in events] == [
        TRIGGER_TIME - timedelta(minutes=20),
        TRIGGER_TIME - timedelta(minutes=5),
        TRIGGER_TIME,
        TRIGGER_TIME + timedelta(minutes=10),
    ]
    assert [event["evidence"] for event in events] == [
        {
            "kind": "github_webhook",
            "webhook_delivery_id": before_delivery.id,
            "github_delivery_id": before_delivery.delivery_id,
        },
        {
            "kind": "github_webhook",
            "webhook_delivery_id": deployment_delivery.id,
            "github_delivery_id": deployment_delivery.delivery_id,
        },
        {
            "kind": "alert_webhook",
            "alert_delivery_id": trigger_delivery.id,
            "external_event_id": trigger_delivery.external_event_id,
        },
        {
            "kind": "alert_webhook",
            "alert_delivery_id": after_delivery.id,
            "external_event_id": after_delivery.external_event_id,
        },
    ]
    assert "payload_body" not in response.text
    assert "private payload" not in response.text


def test_alert_context_respects_custom_window(
    client: TestClient,
    db_session: Session,
) -> None:
    organization = create_organization(db_session)
    repository = create_repository(db_session, organization, "customer-api")
    earlier, _ = add_github_event(
        db_session,
        repository,
        "github-before-45",
        TRIGGER_TIME - timedelta(minutes=45),
    )
    trigger, _ = add_alert_event(
        db_session, repository, "alert-custom-trigger", TRIGGER_TIME
    )
    add_github_event(
        db_session,
        repository,
        "github-after-1",
        TRIGGER_TIME + timedelta(minutes=1),
    )
    db_session.commit()

    response = client.get(
        f"/organizations/{organization.id}/repositories/{repository.id}/"
        f"timeline/{trigger.id}/context",
        params={"lookback_minutes": 60, "lookahead_minutes": 0},
    )

    assert response.status_code == 200
    context = response.json()
    assert parse_time(context["window_start"]) == TRIGGER_TIME - timedelta(
        minutes=60
    )
    assert parse_time(context["window_end"]) == TRIGGER_TIME
    assert [event["id"] for event in context["events"]] == [
        earlier.id,
        trigger.id,
    ]


def test_alert_context_rejects_timeline_event_from_another_repository(
    client: TestClient,
    db_session: Session,
) -> None:
    organization = create_organization(db_session)
    repository_a = create_repository(db_session, organization, "repository-a")
    repository_b = create_repository(db_session, organization, "repository-b")
    trigger, _ = add_alert_event(
        db_session, repository_a, "alert-other-repository", TRIGGER_TIME
    )
    db_session.commit()

    response = client.get(
        f"/organizations/{organization.id}/repositories/{repository_b.id}/"
        f"timeline/{trigger.id}/context"
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Timeline event not found"}


def test_context_rejects_non_alert_trigger(
    client: TestClient,
    db_session: Session,
) -> None:
    organization = create_organization(db_session)
    repository = create_repository(db_session, organization, "repository-push")
    push, _ = add_github_event(
        db_session, repository, "github-non-alert", TRIGGER_TIME
    )
    db_session.commit()

    response = client.get(
        f"/organizations/{organization.id}/repositories/{repository.id}/"
        f"timeline/{push.id}/context"
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Timeline event is not an alert"}
