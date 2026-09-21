import json
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.models.repository import Repository
from app.models.timeline_event import TimelineEvent
from app.models.webhook_delivery import WebhookDelivery
from app.processing.github import GitHubPushProcessingError
from app.workers.webhook_worker import process_webhook_delivery


def create_repository(db_session: Session, name: str) -> Repository:
    organization = Organization(name=f"{name} organization")
    db_session.add(organization)
    db_session.flush()
    repository = Repository(
        organization_id=organization.id,
        name=name,
    )
    db_session.add(repository)
    db_session.flush()
    return repository


def create_push_delivery(
    db_session: Session,
    repository_id: int,
    delivery_id: str,
    received_at: datetime,
    payload: dict[str, str],
) -> WebhookDelivery:
    delivery = WebhookDelivery(
        delivery_id=delivery_id,
        event="push",
        repository_id=repository_id,
        payload_body=json.dumps(payload).encode("utf-8"),
        received_at=received_at,
    )
    db_session.add(delivery)
    db_session.commit()
    db_session.refresh(delivery)
    return delivery


def test_github_push_creates_timeline_event(db_session: Session) -> None:
    repository = create_repository(db_session, "payments-api")
    received_at = datetime(2026, 9, 20, 10, 0, tzinfo=timezone.utc)
    worker_time = datetime(2026, 9, 20, 10, 1, tzinfo=timezone.utc)
    delivery = create_push_delivery(
        db_session,
        repository.id,
        "timeline-push-001",
        received_at,
        {
            "ref": "refs/heads/main",
            "before": "1111111111111111111111111111111111111111",
            "after": "2222222222222222222222222222222222222222",
        },
    )

    processed = process_webhook_delivery(
        db_session,
        delivery.id,
        now=lambda: worker_time,
    )

    assert processed is True
    assert delivery.processed_at == worker_time
    timeline_events = list(
        db_session.scalars(
            select(TimelineEvent).where(
                TimelineEvent.webhook_delivery_id == delivery.id
            )
        )
    )
    assert len(timeline_events) == 1
    timeline_event = timeline_events[0]
    assert timeline_event.repository_id == repository.id
    assert timeline_event.webhook_delivery_id == delivery.id
    assert timeline_event.source == "github"
    assert timeline_event.event_type == "push"
    assert timeline_event.summary == "Push to refs/heads/main"
    assert timeline_event.observed_at == received_at


def test_processing_same_push_again_does_not_duplicate_timeline_event(
    db_session: Session,
) -> None:
    repository = create_repository(db_session, "customer-frontend")
    received_at = datetime(2026, 9, 20, 11, 0, tzinfo=timezone.utc)
    first_worker_time = datetime(2026, 9, 20, 11, 1, tzinfo=timezone.utc)
    delivery = create_push_delivery(
        db_session,
        repository.id,
        "timeline-push-002",
        received_at,
        {
            "ref": "refs/heads/main",
            "before": "3333333333333333333333333333333333333333",
            "after": "4444444444444444444444444444444444444444",
        },
    )
    process_webhook_delivery(
        db_session,
        delivery.id,
        now=lambda: first_worker_time,
    )

    processed_again = process_webhook_delivery(
        db_session,
        delivery.id,
        now=lambda: datetime(2026, 9, 20, 11, 2, tzinfo=timezone.utc),
    )

    assert processed_again is False
    assert delivery.processed_at == first_worker_time
    timeline_events = list(
        db_session.scalars(
            select(TimelineEvent).where(
                TimelineEvent.webhook_delivery_id == delivery.id
            )
        )
    )
    assert len(timeline_events) == 1


def test_non_push_delivery_is_processed_without_timeline_event(
    db_session: Session,
) -> None:
    delivery = WebhookDelivery(
        delivery_id="timeline-ping-001",
        event="ping",
        payload_body=b"Hello, World!",
    )
    db_session.add(delivery)
    db_session.commit()
    db_session.refresh(delivery)

    processed = process_webhook_delivery(db_session, delivery.id)

    assert processed is True
    assert delivery.processed_at is not None
    timeline_event = db_session.scalar(
        select(TimelineEvent).where(
            TimelineEvent.webhook_delivery_id == delivery.id
        )
    )
    assert timeline_event is None


def test_malformed_push_is_not_marked_processed(
    db_session: Session,
) -> None:
    repository = create_repository(db_session, "malformed-push")
    delivery = create_push_delivery(
        db_session,
        repository.id,
        "timeline-push-malformed-001",
        datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc),
        {
            "before": "5555555555555555555555555555555555555555",
            "after": "6666666666666666666666666666666666666666",
        },
    )

    with pytest.raises(GitHubPushProcessingError, match="ref"):
        process_webhook_delivery(db_session, delivery.id)

    assert delivery.processed_at is None
    timeline_event = db_session.scalar(
        select(TimelineEvent).where(
            TimelineEvent.webhook_delivery_id == delivery.id
        )
    )
    assert timeline_event is None
