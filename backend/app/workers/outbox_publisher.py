import sys
import time
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import database
from app.messaging.sqs import (
    SQSClient,
    SQSConfigurationError,
    create_sqs_client,
    get_webhook_queue_name,
    publish_webhook_delivery_reference,
    resolve_webhook_queue_url,
)
from app.models.webhook_delivery_outbox import WebhookDeliveryOutbox


IDLE_SLEEP_SECONDS = 2

# returns the oldest outbox row that hasn't been published yet.
def publish_one_pending_outbox(
    session: Session,
    sqs_client: SQSClient,
    queue_url: str,
) -> bool:
    statement = (
        select(WebhookDeliveryOutbox)
        .where(WebhookDeliveryOutbox.published_at.is_(None))
        .order_by(
            WebhookDeliveryOutbox.created_at.asc(),
            WebhookDeliveryOutbox.id.asc(),
        )
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    outbox = session.scalar(statement)
    if outbox is None:
        return False

    try:
        # It sends the database ID of the WebhookDelivery to SQS.
        publish_webhook_delivery_reference(
            sqs_client,
            queue_url,
            outbox.webhook_delivery_id,
        )
        # and only then mark published_at
        outbox.published_at = datetime.now(timezone.utc)
        session.commit()
    except Exception:
        session.rollback()
        raise

    return True


def main() -> int:
    if database.engine is None:
        print("DATABASE_URL is required for the outbox publisher.", file=sys.stderr)
        return 1

    try:
        sqs_client = create_sqs_client()
        queue_name = get_webhook_queue_name()
    except SQSConfigurationError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    queue_url: str | None = None
    # keeps running and tries to publish pending work
    while True:
        try:
            if queue_url is None:
                queue_url = resolve_webhook_queue_url(
                    sqs_client,
                    queue_name,
                )
            with Session(database.engine) as session:
                published = publish_one_pending_outbox(
                    session,
                    sqs_client,
                    queue_url,
                )
        except Exception:
            queue_url = None
            print("Outbox publishing failed; retrying.", file=sys.stderr)
            time.sleep(IDLE_SLEEP_SECONDS)
            continue

        if not published:
            time.sleep(IDLE_SLEEP_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
