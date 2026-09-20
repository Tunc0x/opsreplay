import json
import sys
import time
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, Literal

from sqlalchemy.orm import Session

from app import database
from app.messaging.sqs import (
    SQSClient,
    SQSConfigurationError,
    create_sqs_client,
    delete_webhook_message,
    get_webhook_queue_name,
    receive_webhook_message,
    resolve_webhook_queue_url,
)
from app.models.webhook_delivery import WebhookDelivery


FAILURE_SLEEP_SECONDS = 2
WorkerIterationResult = Literal[
    "no_message",
    "processed",
    "already_processed",
]


class WebhookWorkerError(RuntimeError):
    """A webhook queue message could not be processed safely."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_webhook_delivery_id(message_body: str) -> int:
    try:
        payload = json.loads(message_body)
    except json.JSONDecodeError as error:
        raise WebhookWorkerError(
            "The SQS message body is not valid JSON."
        ) from error

    if not isinstance(payload, dict):
        raise WebhookWorkerError(
            "The SQS message body must be a JSON object."
        )
    webhook_delivery_id = payload.get("webhook_delivery_id")
    if type(webhook_delivery_id) is not int:
        raise WebhookWorkerError(
            "The SQS message webhook_delivery_id must be an integer."
        )
    return webhook_delivery_id


def process_webhook_delivery(
    session: Session,
    webhook_delivery_id: int,
    *,
    now: Callable[[], datetime] = _utc_now,
) -> bool:
    try:
        # loads the real record from PostgreSQL
        delivery = session.get(WebhookDelivery, webhook_delivery_id)
        if delivery is None:
            raise WebhookWorkerError(
                "The referenced WebhookDelivery does not exist."
            )
        # checks whether it has been already processed -> ensures idempotency
        if delivery.processed_at is not None:
            return False

        delivery.processed_at = now()
        session.commit()
    except Exception:
        session.rollback()
        raise

    return True


def process_one_sqs_message(
    sqs_client: SQSClient,
    queue_url: str,
    *,
    session: Session | None = None,
    now: Callable[[], datetime] = _utc_now,
) -> WorkerIterationResult:
    message = receive_webhook_message(sqs_client, queue_url)
    if message is None:
        return "no_message"
    # The SQS message body contains only a reference to the WebhookDelivery ID
    message_body = message.get("Body")
    if not isinstance(message_body, str):
        raise WebhookWorkerError("The SQS message has no valid body.")
    # Receipt handle used later to delete this received SQS message
    receipt_handle = message.get("ReceiptHandle")
    if not isinstance(receipt_handle, str) or not receipt_handle:
        raise WebhookWorkerError(
            "The SQS message has no valid ReceiptHandle."
        )
    # parses the fetched delivery id
    webhook_delivery_id = parse_webhook_delivery_id(message_body)

    if session is None:
        if database.engine is None:
            raise WebhookWorkerError(
                "DATABASE_URL is required for the webhook worker."
            )
        with Session(database.engine) as worker_session:
            processed = process_webhook_delivery(
                worker_session,
                webhook_delivery_id,
                now=now,
            )
    else:
        processed = process_webhook_delivery(
            session,
            webhook_delivery_id,
            now=now,
        )
    # The processing result has already been committed to PostgreSQL.
    # Delete the SQS message only after processing succeeds.
    delete_webhook_message(
        sqs_client,
        queue_url,
        receipt_handle,
    )
    if processed:
        return "processed"
    return "already_processed"


def main() -> int:
    if database.engine is None:
        print("DATABASE_URL is required for the webhook worker.", file=sys.stderr)
        return 1

    try:
        sqs_client = create_sqs_client()
        queue_name = get_webhook_queue_name()
    except SQSConfigurationError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    queue_url: str | None = None
    # The worker continuously asks SQS for pending webhook jobs.
    try:
        while True:
            try:
                if queue_url is None:
                    queue_url = resolve_webhook_queue_url(
                        sqs_client,
                        queue_name,
                    )
                process_one_sqs_message(sqs_client, queue_url)
            except Exception:
                queue_url = None
                print(
                    "Webhook worker iteration failed; waiting for retry.",
                    file=sys.stderr,
                )
                time.sleep(FAILURE_SLEEP_SECONDS)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
