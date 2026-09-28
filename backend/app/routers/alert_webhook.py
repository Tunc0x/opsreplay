import os
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db_session
from app.models.alert_delivery import AlertDelivery
from app.models.repository import Repository
from app.models.timeline_event import TimelineEvent
from app.schemas.alert import AlertPayload
from app.webhooks.alerts import verify_alert_signature


router = APIRouter()
ALERT_EVENT_ID_UNIQUE_CONSTRAINT = "uq_alert_deliveries_external_event_id"


@router.post("/webhooks/alerts", status_code=202)
async def receive_alert_webhook(
    request: Request,
    response: Response,
    event_id: Annotated[str, Header(alias="X-OpsReplay-Event-ID")],
    signature: Annotated[
        str | None, Header(alias="X-OpsReplay-Signature-256")
    ] = None,
    session: Session = Depends(get_db_session),
) -> dict[str, str | int]:
    secret = os.getenv("ALERT_WEBHOOK_SECRET")
    if not secret:
        raise HTTPException(
            status_code=503,
            detail="Alert webhook secret is not configured",
        )

    payload_body = await request.body()
    if not verify_alert_signature(payload_body, secret, signature):
        raise HTTPException(
            status_code=403,
            detail="Invalid alert webhook signature",
        )

    try:
        payload = AlertPayload.model_validate_json(payload_body)
    except ValidationError as error:
        raise HTTPException(status_code=400, detail="Invalid alert payload") from error

    repository = session.get(Repository, payload.repository_id)
    if repository is None:
        raise HTTPException(status_code=404, detail="Repository not found")

    delivery = AlertDelivery(
        external_event_id=event_id,
        repository_id=repository.id,
        severity=payload.severity,
        title=payload.title,
        observed_at=payload.observed_at,
        payload_body=payload_body,
    )
    session.add(delivery)
    try:
        session.flush()
        session.add(
            TimelineEvent(
                repository_id=repository.id,
                webhook_delivery_id=None,
                alert_delivery_id=delivery.id,
                source="alert",
                event_type="alert",
                summary=f"{payload.severity.upper()}: {payload.title}",
                observed_at=payload.observed_at,
            )
        )
        session.commit()
    except IntegrityError as error:
        session.rollback()
        constraint_name = getattr(
            getattr(error.orig, "diag", None), "constraint_name", None
        )
        if constraint_name != ALERT_EVENT_ID_UNIQUE_CONSTRAINT:
            raise
        response.status_code = 200
        return {
            "status": "duplicate",
            "event_id": event_id,
            "repository_id": repository.id,
        }

    return {
        "status": "accepted",
        "event_id": event_id,
        "repository_id": repository.id,
    }
