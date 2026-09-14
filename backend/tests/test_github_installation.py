import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.integrations.github_app import (
    GitHubAppError,
    link_github_repository,
    register_github_installation,
)
from app.models.github_installation import GitHubInstallation
from app.models.organization import Organization
from app.models.repository import Repository


def test_register_github_installation_is_idempotent(
    db_session: Session,
) -> None:
    organization = Organization(name="Test Engineering")
    db_session.add(organization)
    db_session.commit()
    db_session.refresh(organization)
    github_installations = [
        {
            "id": 123_456,
            "account_login": "test-engineering",
            "account_type": "Organization",
        }
    ]

    first_registration = register_github_installation(
        db_session,
        organization.id,
        123_456,
        github_installations,
    )
    second_registration = register_github_installation(
        db_session,
        organization.id,
        123_456,
        github_installations,
    )

    assert isinstance(first_registration.id, int)
    assert first_registration.organization_id == organization.id
    assert first_registration.github_installation_id == 123_456
    assert first_registration.account_login == "test-engineering"
    assert first_registration.account_type == "Organization"
    assert first_registration.created_at is not None
    assert second_registration.id == first_registration.id
    registration_count = db_session.scalar(
        select(func.count())
        .select_from(GitHubInstallation)
        .where(GitHubInstallation.organization_id == organization.id)
    )
    assert registration_count == 1


def test_register_github_installation_rejects_unverified_installation(
    db_session: Session,
) -> None:
    organization = Organization(name="Test Engineering")
    db_session.add(organization)
    db_session.commit()
    db_session.refresh(organization)

    with pytest.raises(GitHubAppError, match="not returned by GitHub"):
        register_github_installation(
            db_session,
            organization.id,
            999_999,
            [
                {
                    "id": 123_456,
                    "account_login": "test-engineering",
                    "account_type": "Organization",
                }
            ],
        )

    registration = db_session.scalar(
        select(GitHubInstallation).where(
            GitHubInstallation.organization_id == organization.id
        )
    )
    assert registration is None


def test_github_installation_cannot_belong_to_two_organizations(
    db_session: Session,
) -> None:
    first_organization = Organization(name="First Engineering")
    second_organization = Organization(name="Second Engineering")
    db_session.add_all([first_organization, second_organization])
    db_session.commit()
    db_session.refresh(first_organization)
    db_session.refresh(second_organization)
    github_installations = [
        {
            "id": 123_456,
            "account_login": "shared-account",
            "account_type": "Organization",
        }
    ]
    first_registration = register_github_installation(
        db_session,
        first_organization.id,
        123_456,
        github_installations,
    )

    with pytest.raises(GitHubAppError, match="already registered"):
        register_github_installation(
            db_session,
            second_organization.id,
            123_456,
            github_installations,
        )

    preserved_registration = db_session.get(
        GitHubInstallation,
        first_registration.id,
    )
    assert preserved_registration is not None
    assert preserved_registration.organization_id == first_organization.id
    assert preserved_registration.github_installation_id == 123_456
    second_registration = db_session.scalar(
        select(GitHubInstallation).where(
            GitHubInstallation.organization_id == second_organization.id
        )
    )
    assert second_registration is None


def test_link_github_repository_rejects_repository_from_another_organization(
    db_session: Session,
) -> None:
    first_organization = Organization(name="First Engineering")
    second_organization = Organization(name="Second Engineering")
    db_session.add_all([first_organization, second_organization])
    db_session.commit()
    db_session.refresh(first_organization)
    db_session.refresh(second_organization)
    repository = Repository(
        organization_id=first_organization.id,
        name="payments-api",
    )
    db_session.add(repository)
    db_session.commit()
    db_session.refresh(repository)

    with pytest.raises(GitHubAppError, match="does not belong"):
        link_github_repository(
            db_session,
            second_organization.id,
            repository.id,
            1_296_269,
            [
                {
                    "id": 1_296_269,
                    "name": "payments-api",
                    "full_name": "some-owner/payments-api",
                }
            ],
        )

    assert repository.github_repository_id is None
