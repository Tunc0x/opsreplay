import json
from datetime import datetime, timezone
from typing import Any

import pytest
from sqlalchemy.orm import Session

from app.models.webhook_delivery import WebhookDelivery
from app.workers.webhook_worker import (
    WebhookWorkerError,
    process_one_sqs_message,
)


QUEUE_URL = "http://sqs:9324/000000000000/opsreplay-webhooks"


class FakeSQSClient:
    def __init__(self, message: dict[str, str]) -> None:
        self.message = message
        self.receive_calls: list[dict[str, Any]] = []
        self.delete_calls: list[dict[str, Any]] = []
        self.processed_at_during_delete: list[datetime | None] = []
        self.delivery: WebhookDelivery | None = None

    def receive_message(self, **kwargs: Any) -> dict[str, Any]:
        self.receive_calls.append(kwargs)
        return {"Messages": [self.message]}

    def delete_message(self, **kwargs: Any) -> dict[str, Any]:
        if self.delivery is not None:
            self.processed_at_during_delete.append(
                self.delivery.processed_at
            )
        self.delete_calls.append(kwargs)
        return {}


def test_worker_processes_delivery_then_deletes_sqs_message(
    db_session: Session,
) -> None:
    delivery = WebhookDelivery(
        delivery_id="worker-delivery-001",
        event="ping",
        payload_body=b"Hello, World!",
    )
    db_session.add(delivery)
    db_session.commit()
    db_session.refresh(delivery)
    receipt_handle = "receipt-handle-001"
    sqs_client = FakeSQSClient(
        {
            "Body": json.dumps({"webhook_delivery_id": delivery.id}),
            "ReceiptHandle": receipt_handle,
        }
    )
    sqs_client.delivery = delivery

    result = process_one_sqs_message(
        sqs_client,
        QUEUE_URL,
        session=db_session,
    )

    assert result == "processed"
    assert delivery.processed_at is not None
    assert sqs_client.processed_at_during_delete[0] is not None
    assert len(sqs_client.delete_calls) == 1
    assert sqs_client.delete_calls[0] == {
        "QueueUrl": QUEUE_URL,
        "ReceiptHandle": receipt_handle,
    }
    assert sqs_client.receive_calls[0]["MaxNumberOfMessages"] == 1
    assert sqs_client.receive_calls[0]["WaitTimeSeconds"] == 10


def test_duplicate_sqs_message_for_processed_delivery_is_safe(
    db_session: Session,
) -> None:
    original_processed_at = datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc)
    delivery = WebhookDelivery(
        delivery_id="worker-delivery-002",
        event="ping",
        payload_body=b"Hello, World!",
        processed_at=original_processed_at,
    )
    db_session.add(delivery)
    db_session.commit()
    db_session.refresh(delivery)
    sqs_client = FakeSQSClient(
        {
            "Body": json.dumps({"webhook_delivery_id": delivery.id}),
            "ReceiptHandle": "receipt-handle-002",
        }
    )

    result = process_one_sqs_message(
        sqs_client,
        QUEUE_URL,
        session=db_session,
    )

    assert result == "already_processed"
    assert delivery.processed_at == original_processed_at
    assert len(sqs_client.delete_calls) == 1


def test_worker_does_not_delete_message_when_processing_fails(
    db_session: Session,
) -> None:
    sqs_client = FakeSQSClient(
        {
            "Body": json.dumps({"webhook_delivery_id": 999_999}),
            "ReceiptHandle": "receipt-handle-003",
        }
    )

    with pytest.raises(WebhookWorkerError, match="does not exist"):
        process_one_sqs_message(
            sqs_client,
            QUEUE_URL,
            session=db_session,
        )

    assert sqs_client.delete_calls == []
