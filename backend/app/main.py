from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db_session, is_database_healthy
from app.models.organization import Organization
from app.schemas.organization import OrganizationCreate, OrganizationRead


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
