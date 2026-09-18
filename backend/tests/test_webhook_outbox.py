import json
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.webhook_delivery import WebhookDelivery
from app.models.webhook_delivery_outbox import WebhookDeliveryOutbox
from app.workers.outbox_publisher import publish_one_pending_outbox


TEST_WEBHOOK_SECRET = "It's a Secret to Everybody"
TEST_PAYLOAD = b"Hello, World!"
TEST_SIGNATURE = (
    "sha256=757107ea0eb2509fc211221cce984b8a37570b6d7586c22c46f4379c8b043e17"
)


def webhook_headers(delivery_id: str) -> dict[str, str]:
    return {
        "X-Hub-Signature-256": TEST_SIGNATURE,
        "X-GitHub-Event": "ping",
        "X-GitHub-Delivery": delivery_id,
    }


def test_new_github_delivery_creates_outbox_row(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", TEST_WEBHOOK_SECRET)
    delivery_id = "outbox-delivery-001"

    response = client.post(
        "/webhooks/github",
        content=TEST_PAYLOAD,
        headers=webhook_headers(delivery_id),
    )

    assert response.status_code == 202
    delivery = db_session.scalar(
        select(WebhookDelivery).where(
            WebhookDelivery.delivery_id == delivery_id
        )
    )
    assert delivery is not None
    outboxes = list(
        db_session.scalars(
            select(WebhookDeliveryOutbox).where(
                WebhookDeliveryOutbox.webhook_delivery_id == delivery.id
            )
        )
    )
    assert len(outboxes) == 1
    assert outboxes[0].published_at is None


def test_duplicate_github_delivery_does_not_create_second_outbox_row(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", TEST_WEBHOOK_SECRET)
    delivery_id = "outbox-duplicate-delivery-001"
    headers = webhook_headers(delivery_id)

    first_response = client.post(
        "/webhooks/github",
        content=TEST_PAYLOAD,
        headers=headers,
    )
    second_response = client.post(
        "/webhooks/github",
        content=TEST_PAYLOAD,
        headers=headers,
    )

    assert first_response.status_code == 202
    assert second_response.status_code == 200
    deliveries = list(
        db_session.scalars(
            select(WebhookDelivery).where(
                WebhookDelivery.delivery_id == delivery_id
            )
        )
    )
    assert len(deliveries) == 1
    outboxes = list(
        db_session.scalars(
            select(WebhookDeliveryOutbox).where(
                WebhookDeliveryOutbox.webhook_delivery_id
                == deliveries[0].id
            )
        )
    )
    assert len(outboxes) == 1


def test_outbox_publish_marks_row_only_after_sqs_send(
    db_session: Session,
) -> None:
    delivery = WebhookDelivery(
        delivery_id="publisher-delivery-001",
        event="ping",
        payload_body=TEST_PAYLOAD,
    )
    db_session.add(delivery)
    db_session.flush()
    outbox = WebhookDeliveryOutbox(webhook_delivery_id=delivery.id)
    db_session.add(outbox)
    db_session.commit()
    db_session.refresh(outbox)
    send_calls: list[dict[str, Any]] = []
    published_at_during_send = []

    class FakeSQSClient:
        def send_message(self, **kwargs: Any) -> dict[str, str]:
            published_at_during_send.append(outbox.published_at)
            send_calls.append(kwargs)
            return {"MessageId": "test-message-id"}

    published = publish_one_pending_outbox(
        db_session,
        FakeSQSClient(),
        "http://sqs:9324/000000000000/opsreplay-webhooks",
    )

    assert published is True
    assert len(send_calls) == 1
    assert set(send_calls[0]) == {"QueueUrl", "MessageBody"}
    assert json.loads(send_calls[0]["MessageBody"]) == {
        "webhook_delivery_id": delivery.id
    }
    assert published_at_during_send == [None]
    assert outbox.published_at is not None
