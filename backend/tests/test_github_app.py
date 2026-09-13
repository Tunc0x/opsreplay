import pytest
from sqlalchemy.orm import Session

from app.integrations.github_app import (
    GitHubAppError,
    create_github_app_jwt,
    link_github_repository,
)
from app.models.organization import Organization
from app.models.repository import Repository


def test_github_app_jwt_uses_client_id_and_rs256(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixed_time = 1_800_000_000
    encoded: dict[str, object] = {}

    def fake_encode(
        payload: dict[str, object],
        key: bytes,
        algorithm: str,
    ) -> str:
        encoded.update(payload=payload, key=key, algorithm=algorithm)
        return "test-jwt"

    monkeypatch.setattr("app.integrations.github_app.jwt.encode", fake_encode)

    result = create_github_app_jwt(
        "Iv1.test-client-id",
        b"not-a-real-private-key",
        now=fixed_time,
    )

    payload = encoded["payload"]
    assert isinstance(payload, dict)
    assert result == "test-jwt"
    assert payload["iss"] == "Iv1.test-client-id"
    assert payload["iat"] == fixed_time - 60
    assert fixed_time < payload["exp"] <= fixed_time + 600
    assert encoded["algorithm"] == "RS256"


def test_link_github_repository_uses_verified_accessible_id(
    db_session: Session,
) -> None:
    organization = Organization(name="Test Engineering")
    db_session.add(organization)
    db_session.commit()
    db_session.refresh(organization)
    repository = Repository(
        organization_id=organization.id,
        name="local-payments-service",
    )
    db_session.add(repository)
    db_session.commit()
    db_session.refresh(repository)

    linked_repository = link_github_repository(
        db_session,
        repository.id,
        1_296_269,
        [
            {
                "id": 1_296_269,
                "name": "renamed-payments-api",
                "full_name": "some-owner/renamed-payments-api",
            }
        ],
    )

    assert linked_repository.github_repository_id == 1_296_269
    assert repository.name == "local-payments-service"


def test_link_github_repository_rejects_inaccessible_id(
    db_session: Session,
) -> None:
    organization = Organization(name="Test Engineering")
    db_session.add(organization)
    db_session.commit()
    db_session.refresh(organization)
    repository = Repository(
        organization_id=organization.id,
        name="payments-api",
    )
    db_session.add(repository)
    db_session.commit()
    db_session.refresh(repository)

    with pytest.raises(GitHubAppError, match="not accessible"):
        link_github_repository(
            db_session,
            repository.id,
            9_999_999,
            [
                {
                    "id": 1_296_269,
                    "name": "different-repository",
                    "full_name": "some-owner/different-repository",
                }
            ],
        )

    assert repository.github_repository_id is None
