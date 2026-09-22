from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db_session, is_database_healthy
from app.models.organization import Organization
from app.models.repository import Repository
from app.models.timeline_event import TimelineEvent
from app.models.webhook_delivery import WebhookDelivery
from app.routers.github_webhook import router as github_webhook_router
from app.schemas.organization import OrganizationCreate, OrganizationRead
from app.schemas.repository import RepositoryCreate, RepositoryRead
from app.schemas.timeline_event import TimelineEvidenceRead, TimelineEventRead


app = FastAPI(title="OpsReplay API")
app.include_router(github_webhook_router)


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


@app.get(
    "/organizations/{organization_id}/repositories/{repository_id}/timeline",
    response_model=list[TimelineEventRead],
)
def get_repository_timeline(
    organization_id: int,
    repository_id: int,
    session: Session = Depends(get_db_session),
) -> list[TimelineEventRead]:
    # confirm organization
    organization = session.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    # proof provenance
    repository = session.scalar(
        select(Repository).where(
            Repository.id == repository_id,
            Repository.organization_id == organization_id,
        )
    )
    if repository is None:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Find TimelineEvents for the specific repository. Join each TimelineEvent to its WebhookDelivery
    # and then sort events chronologically
    
    statement = (
        select(TimelineEvent, WebhookDelivery.delivery_id)
        .join(
            WebhookDelivery,
            TimelineEvent.webhook_delivery_id == WebhookDelivery.id,
        )
        .where(TimelineEvent.repository_id == repository_id)
        .order_by(TimelineEvent.observed_at.asc(), TimelineEvent.id.asc())
    )
    return [
        TimelineEventRead(
            id=event.id,
            repository_id=event.repository_id,
            source=event.source,
            event_type=event.event_type,
            summary=event.summary,
            observed_at=event.observed_at,
            created_at=event.created_at,
            evidence=TimelineEvidenceRead(
                webhook_delivery_id=event.webhook_delivery_id,
                github_delivery_id=github_delivery_id,
            ),
        )
        # Convert each database result into TimelineEventRead
        for event, github_delivery_id in session.execute(statement)
    ]
