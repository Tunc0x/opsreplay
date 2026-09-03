import os
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db_session, is_database_healthy
from app.models.organization import Organization
from app.models.repository import Repository
from app.schemas.organization import OrganizationCreate, OrganizationRead
from app.schemas.repository import RepositoryCreate, RepositoryRead
from app.webhooks.github import verify_github_signature


app = FastAPI(title="OpsReplay API")


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


@app.post("/webhooks/github", status_code=202)
async def receive_github_webhook(
    request: Request,
    github_event: Annotated[str, Header(alias="X-GitHub-Event")],
    github_delivery: Annotated[str, Header(alias="X-GitHub-Delivery")],
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

    return {
        "status": "accepted",
        "event": github_event,
        "delivery_id": github_delivery,
    }
