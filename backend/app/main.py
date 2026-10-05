from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db_session, is_database_healthy
from app.llm.postmortem import (
    PostmortemConfigurationError,
    PostmortemGenerationError,
    PostmortemGroundingError,
    generate_postmortem_draft,
    validate_postmortem_grounding,
)
from app.models.alert_delivery import AlertDelivery
from app.models.incident import Incident
from app.models.organization import Organization
from app.models.repository import Repository
from app.models.timeline_event import TimelineEvent
from app.models.webhook_delivery import WebhookDelivery
from app.routers.alert_webhook import router as alert_webhook_router
from app.routers.github_webhook import router as github_webhook_router
from app.schemas.incident import IncidentCreate, IncidentRead
from app.schemas.investigation import InvestigationContextRead
from app.schemas.organization import OrganizationCreate, OrganizationRead
from app.schemas.postmortem import PostmortemDraftRead
from app.schemas.repository import RepositoryCreate, RepositoryRead
from app.schemas.timeline_event import (
    AlertWebhookEvidenceRead,
    GitHubWebhookEvidenceRead,
    TimelineEventRead,
)


app = FastAPI(title="OpsReplay API")
app.include_router(alert_webhook_router)
app.include_router(github_webhook_router)

INCIDENT_TRIGGER_UNIQUE_CONSTRAINT = "uq_incidents_trigger_timeline_event_id"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/db-health")
def db_health() -> dict[str, str]:
    if not is_database_healthy():
        raise HTTPException(status_code=503, detail="Database unavailable")

    return {"status": "ok"}


@app.post(
    "/organizations",
    response_model=OrganizationRead,
    status_code=201,
)
def create_organization(
    organization: OrganizationCreate,
    session: Session = Depends(get_db_session),
) -> Organization:
    db_organization = Organization(name=organization.name)
    session.add(db_organization)
    session.commit()
    session.refresh(db_organization)
    return db_organization


@app.get(
    "/organizations/{organization_id}",
    response_model=OrganizationRead,
)
def get_organization(
    organization_id: int,
    session: Session = Depends(get_db_session),
) -> Organization:
    organization = session.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    return organization


@app.post(
    "/organizations/{organization_id}/repositories",
    response_model=RepositoryRead,
    status_code=201,
)
def create_repository(
    organization_id: int,
    repository: RepositoryCreate,
    session: Session = Depends(get_db_session),
) -> Repository:
    organization = session.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    db_repository = Repository(
        organization_id=organization.id,
        name=repository.name,
    )
    session.add(db_repository)
    session.commit()
    session.refresh(db_repository)
    return db_repository


@app.get(
    "/organizations/{organization_id}/repositories",
    response_model=list[RepositoryRead],
)
def list_repositories(
    organization_id: int,
    session: Session = Depends(get_db_session),
) -> list[Repository]:
    organization = session.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    statement = (
        select(Repository)
        .where(Repository.organization_id == organization.id)
        .order_by(Repository.id.asc())
    )
    return list(session.scalars(statement))


@app.get(
    "/organizations/{organization_id}/repositories/{repository_id}",
    response_model=RepositoryRead,
)
def get_repository_from_organization(
    organization_id: int,
    repository_id: int,
    session: Session = Depends(get_db_session),
) -> Repository:
    organization = session.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    statement = (
        select(Repository)
        .where(Repository.organization_id == organization.id, Repository.id == repository_id)
    )

    repository = session.scalar(statement)

    if repository is None:
         raise HTTPException(status_code=404, detail="Repository not found")


    return repository

# read timeline event from repository id and optionally set a timeframe
def _read_timeline_events(
    session: Session,
    repository_id: int,
    window_start: datetime | None = None,
    window_end: datetime | None = None,
) -> list[TimelineEventRead]:
    statement = (
        select(
            TimelineEvent,
            WebhookDelivery.delivery_id,
            AlertDelivery.external_event_id,
        )
        .outerjoin(
            WebhookDelivery,
            TimelineEvent.webhook_delivery_id == WebhookDelivery.id,
        )
        .outerjoin(
            AlertDelivery,
            TimelineEvent.alert_delivery_id == AlertDelivery.id,
        )
        # return timeline events belonging to this repository
        .where(TimelineEvent.repository_id == repository_id)
    )
    if window_start is not None:
        statement = statement.where(TimelineEvent.observed_at >= window_start)
    if window_end is not None:
        statement = statement.where(TimelineEvent.observed_at <= window_end)
    statement = statement.order_by(
        TimelineEvent.observed_at.asc(), TimelineEvent.id.asc()
    )

    timeline = []
    for event, github_delivery_id, external_event_id in session.execute(
        statement
    ):
        if (
            event.webhook_delivery_id is not None
            and event.alert_delivery_id is None
            and github_delivery_id is not None
        ):
            evidence = GitHubWebhookEvidenceRead(
                kind="github_webhook",
                webhook_delivery_id=event.webhook_delivery_id,
                github_delivery_id=github_delivery_id,
            )
        elif (
            event.webhook_delivery_id is None
            and event.alert_delivery_id is not None
            and external_event_id is not None
        ):
            evidence = AlertWebhookEvidenceRead(
                kind="alert_webhook",
                alert_delivery_id=event.alert_delivery_id,
                external_event_id=external_event_id,
            )
        else:
            raise RuntimeError(
                f"TimelineEvent {event.id} has invalid evidence provenance."
            )

        timeline.append(
            TimelineEventRead(
                id=event.id,
                repository_id=event.repository_id,
                source=event.source,
                event_type=event.event_type,
                summary=event.summary,
                observed_at=event.observed_at,
                created_at=event.created_at,
                evidence=evidence,
            )
        )
    return timeline


def _get_alert_trigger(
    session: Session,
    repository_id: int,
    timeline_event_id: int,
) -> TimelineEvent:
    trigger = session.scalar(
        select(TimelineEvent).where(
            TimelineEvent.id == timeline_event_id,
            TimelineEvent.repository_id == repository_id,
        )
    )
    if trigger is None:
        raise HTTPException(status_code=404, detail="Timeline event not found")
    if (
        trigger.source != "alert"
        or trigger.event_type != "alert"
        or trigger.alert_delivery_id is None
    ):
        raise HTTPException(status_code=400, detail="Timeline event is not an alert")
    return trigger


def _build_investigation_context(
    session: Session,
    repository_id: int,
    trigger: TimelineEvent,
    lookback_minutes: int,
    lookahead_minutes: int,
) -> InvestigationContextRead:
    window_start = trigger.observed_at - timedelta(minutes=lookback_minutes)
    window_end = trigger.observed_at + timedelta(minutes=lookahead_minutes)
    return InvestigationContextRead(
        repository_id=repository_id,
        trigger_event_id=trigger.id,
        window_start=window_start,
        window_end=window_end,
        events=_read_timeline_events(
            session,
            repository_id,
            window_start=window_start,
            window_end=window_end,
        ),
    )


def _build_incident_read(
    session: Session,
    incident: Incident,
) -> IncidentRead:
    trigger = _get_alert_trigger(
        session,
        incident.repository_id,
        incident.trigger_timeline_event_id,
    )
    context = _build_investigation_context(
        session,
        incident.repository_id,
        trigger,
        incident.lookback_minutes,
        incident.lookahead_minutes,
    )
    return IncidentRead(
        id=incident.id,
        repository_id=incident.repository_id,
        trigger_timeline_event_id=incident.trigger_timeline_event_id,
        lookback_minutes=incident.lookback_minutes,
        lookahead_minutes=incident.lookahead_minutes,
        status=incident.status,
        resolved_at=incident.resolved_at,
        created_at=incident.created_at,
        context=context,
    )

# returns the whole timeline for repository X
@app.get(
    "/organizations/{organization_id}/repositories/{repository_id}/timeline",
    response_model=list[TimelineEventRead],
)
def get_repository_timeline(
    organization_id: int,
    repository_id: int,
    session: Session = Depends(get_db_session),
) -> list[TimelineEventRead]:
    organization = session.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    repository = session.scalar(
        select(Repository).where(
            Repository.id == repository_id,
            Repository.organization_id == organization_id,
        )
    )
    if repository is None:
        raise HTTPException(status_code=404, detail="Repository not found")

    return _read_timeline_events(session, repository_id)

# Returns timeline events around an alert
@app.get(
    "/organizations/{organization_id}/repositories/{repository_id}/"
    "timeline/{timeline_event_id}/context",
    response_model=InvestigationContextRead,
)
def get_investigation_context(
    organization_id: int,
    repository_id: int,
    timeline_event_id: int,
    lookback_minutes: Annotated[int, Query(ge=0, le=1440)] = 30, # restrict values to between 0 and 1440 minutes
    lookahead_minutes: Annotated[int, Query(ge=0, le=1440)] = 30,
    session: Session = Depends(get_db_session),
) -> InvestigationContextRead:
    # check if organization exists
    organization = session.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    # check if repository actually belongs to organization
    repository = session.scalar(
        select(Repository).where(
            Repository.id == repository_id,
            Repository.organization_id == organization_id,
        )
    )
    if repository is None:
        raise HTTPException(status_code=404, detail="Repository not found")


    trigger = _get_alert_trigger(session, repository_id, timeline_event_id)
    return _build_investigation_context(
        session,
        repository_id,
        trigger,
        lookback_minutes,
        lookahead_minutes,
    )


@app.post(
    "/organizations/{organization_id}/repositories/{repository_id}/incidents",
    response_model=IncidentRead,
    status_code=201,
)
def create_incident(
    organization_id: int,
    repository_id: int,
    incident: IncidentCreate,
    session: Session = Depends(get_db_session),
) -> IncidentRead:
    organization = session.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    repository = session.scalar(
        select(Repository).where(
            Repository.id == repository_id,
            Repository.organization_id == organization_id,
        )
    )
    if repository is None:
        raise HTTPException(status_code=404, detail="Repository not found")

    trigger = _get_alert_trigger(
        session,
        repository_id,
        incident.trigger_timeline_event_id,
    )
    db_incident = Incident(
        repository_id=repository_id,
        trigger_timeline_event_id=trigger.id,
        lookback_minutes=incident.lookback_minutes,
        lookahead_minutes=incident.lookahead_minutes,
    )
    session.add(db_incident)
    try:
        session.commit()
        session.refresh(db_incident)
    except IntegrityError as error:
        session.rollback()
        constraint_name = getattr(
            getattr(error.orig, "diag", None),
            "constraint_name",
            None,
        )
        if constraint_name != INCIDENT_TRIGGER_UNIQUE_CONSTRAINT:
            raise
        raise HTTPException(
            status_code=409,
            detail="Incident already exists for this alert",
        ) from error

    return _build_incident_read(session, db_incident)


@app.get(
    "/organizations/{organization_id}/repositories/{repository_id}/"
    "incidents/{incident_id}",
    response_model=IncidentRead,
)
def get_incident(
    organization_id: int,
    repository_id: int,
    incident_id: int,
    session: Session = Depends(get_db_session),
) -> IncidentRead:
    organization = session.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    repository = session.scalar(
        select(Repository).where(
            Repository.id == repository_id,
            Repository.organization_id == organization_id,
        )
    )
    if repository is None:
        raise HTTPException(status_code=404, detail="Repository not found")

    incident = session.scalar(
        select(Incident).where(
            Incident.id == incident_id,
            Incident.repository_id == repository_id,
        )
    )
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    return _build_incident_read(session, incident)


@app.post(
    "/organizations/{organization_id}/repositories/{repository_id}/"
    "incidents/{incident_id}/resolve",
    response_model=IncidentRead,
)
def resolve_incident(
    organization_id: int,
    repository_id: int,
    incident_id: int,
    session: Session = Depends(get_db_session),
) -> IncidentRead:
    organization = session.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    repository = session.scalar(
        select(Repository).where(
            Repository.id == repository_id,
            Repository.organization_id == organization_id,
        )
    )
    if repository is None:
        raise HTTPException(status_code=404, detail="Repository not found")

    incident = session.scalar(
        select(Incident).where(
            Incident.id == incident_id,
            Incident.repository_id == repository_id,
        )
    )
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    if incident.status == "open":
        incident.status = "resolved"
        incident.resolved_at = datetime.now(timezone.utc)
        session.commit()
        session.refresh(incident)
    elif incident.status != "resolved":
        raise HTTPException(
            status_code=500,
            detail="Incident has unsupported status",
        )

    return _build_incident_read(session, incident)


@app.post(
    "/organizations/{organization_id}/repositories/{repository_id}/"
    "incidents/{incident_id}/postmortem-draft",
    response_model=PostmortemDraftRead,
)
def generate_incident_postmortem_draft(
    organization_id: int,
    repository_id: int,
    incident_id: int,
    session: Session = Depends(get_db_session),
) -> PostmortemDraftRead:
    organization = session.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    repository = session.scalar(
        select(Repository).where(
            Repository.id == repository_id,
            Repository.organization_id == organization_id,
        )
    )
    if repository is None:
        raise HTTPException(status_code=404, detail="Repository not found")

    incident = session.scalar(
        select(Incident).where(
            Incident.id == incident_id,
            Incident.repository_id == repository_id,
        )
    )
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    if incident.status != "resolved":
        raise HTTPException(
            status_code=409,
            detail=(
                "Incident must be resolved before generating a "
                "postmortem draft"
            ),
        )

    context = _build_incident_read(session, incident).context
    try:
        model, draft = generate_postmortem_draft(context.events)
        validate_postmortem_grounding(draft, context.events)
    except PostmortemConfigurationError as error:
        raise HTTPException(
            status_code=503,
            detail="Postmortem generation is not configured",
        ) from error
    except PostmortemGroundingError as error:
        raise HTTPException(
            status_code=502,
            detail=(
                "Postmortem generation returned invalid evidence "
                "references"
            ),
        ) from error
    except PostmortemGenerationError as error:
        raise HTTPException(
            status_code=502,
            detail="Postmortem generation failed",
        ) from error

    return PostmortemDraftRead(
        incident_id=incident.id,
        model=model,
        draft=draft,
        evidence=context.events,
    )
