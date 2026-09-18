import os
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db_session
from app.models.repository import Repository
from app.models.webhook_delivery import WebhookDelivery
from app.models.webhook_delivery_outbox import WebhookDeliveryOutbox
from app.webhooks.github import (
    extract_github_repository_id,
    verify_github_signature,
)


router = APIRouter()

DELIVERY_ID_UNIQUE_CONSTRAINT = "uq_webhook_deliveries_delivery_id"


@router.post("/webhooks/github", status_code=202)
async def receive_github_webhook(
    request: Request,
    response: Response,
    github_event: Annotated[str, Header(alias="X-GitHub-Event")],
    github_delivery: Annotated[str, Header(alias="X-GitHub-Delivery")],
    session: Session = Depends(get_db_session),
) -> dict[str, str]:
    secret = os.getenv("GITHUB_WEBHOOK_SECRET")
    if not secret:
        raise HTTPException(
            status_code=503,
            detail="GitHub webhook secret is not configured",
        )

    payload_body = await request.body()
    signature_header = request.headers.get("X-Hub-Signature-256")

    if not verify_github_signature(
        payload_body,
        secret,
        signature_header,
    ):
        raise HTTPException(
            status_code=403,
            detail="Invalid GitHub webhook signature",
        )

    github_repository_id = extract_github_repository_id(payload_body)
    repository_id = None

    if github_repository_id is not None:
        statement = select(Repository).where(
            Repository.github_repository_id == github_repository_id
        )
        repository = session.scalar(statement)
        if repository is not None:
            repository_id = repository.id

    delivery = WebhookDelivery(
        delivery_id=github_delivery,
        event=github_event,
        repository_id=repository_id,
        payload_body=payload_body,
    )
    session.add(delivery)
    # create an outbox row in the same database transaction for every new webhook
    try:
        session.flush() # send to PostgreSQL so SQLAlchemy gets delivery.id
        session.add(
            WebhookDeliveryOutbox(webhook_delivery_id=delivery.id)
        )
        session.commit()
    except IntegrityError as error:
        session.rollback()
        constraint_name = getattr(
            getattr(error.orig, "diag", None),
            "constraint_name",
            None,
        )
        if constraint_name != DELIVERY_ID_UNIQUE_CONSTRAINT:
            raise
        response.status_code = 200
        return {
            "status": "duplicate",
            "event": github_event,
            "delivery_id": github_delivery,
        }

    return {
        "status": "accepted",
        "event": github_event,
        "delivery_id": github_delivery,
    }
