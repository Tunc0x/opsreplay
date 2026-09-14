from __future__ import annotations

import json
import time
from collections.abc import Sequence
from typing import TypedDict
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import jwt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.github_installation import (
    GitHubInstallation as GitHubInstallationModel,
)
from app.models.organization import Organization
from app.models.repository import Repository


GITHUB_API_URL = "https://api.github.com"
GITHUB_API_VERSION = "2026-03-10"


class GitHubAppError(RuntimeError):
    """An expected GitHub App setup error safe to show to an operator."""


class GitHubInstallation(TypedDict):
    id: int
    account_login: str
    account_type: str


class GitHubRepository(TypedDict):
    id: int
    name: str
    full_name: str


def create_github_app_jwt(
    client_id: str,
    private_key: bytes,
    *,
    now: int | None = None,
) -> str:
    """Create a short-lived JWT used to authenticate as the GitHub App."""
    current_time = int(time.time()) if now is None else now
    payload = {
        "iat": current_time - 60,
        "exp": current_time + 540,
        "iss": client_id,
    }

    try:
        encoded_jwt = jwt.encode(payload, private_key, algorithm="RS256")
    except (jwt.PyJWTError, TypeError, ValueError) as error:
        raise GitHubAppError("Could not create the GitHub App JWT.") from error

    if not isinstance(encoded_jwt, str):
        raise GitHubAppError("GitHub App JWT creation returned an invalid value.")
    return encoded_jwt


def list_github_app_installations(
    client_id: str,
    private_key: bytes,
) -> list[GitHubInstallation]:
    app_jwt = create_github_app_jwt(client_id, private_key)
    response = _request_json(
        "GET",
        "/app/installations?per_page=100",
        app_jwt,
        expected_status=200,
    )
    if not isinstance(response, list):
        raise GitHubAppError("GitHub returned a malformed installations response.")

    installations: list[GitHubInstallation] = []
    for item in response:
        if not isinstance(item, dict):
            raise GitHubAppError("GitHub returned a malformed installation record.")
        installation_id = item.get("id")
        account = item.get("account")
        if type(installation_id) is not int or not isinstance(account, dict):
            raise GitHubAppError("GitHub returned a malformed installation record.")
        account_login = account.get("login")
        account_type = account.get("type")
        if not isinstance(account_login, str) or not isinstance(account_type, str):
            raise GitHubAppError("GitHub returned a malformed installation record.")
        installations.append(
            {
                "id": installation_id,
                "account_login": account_login,
                "account_type": account_type,
            }
        )

    return installations


def create_installation_access_token(
    client_id: str,
    private_key: bytes,
    installation_id: int,
) -> str:
    app_jwt = create_github_app_jwt(client_id, private_key)
    response = _request_json(
        "POST",
        f"/app/installations/{installation_id}/access_tokens",
        app_jwt,
        expected_status=201,
        body={"permissions": {"metadata": "read"}},
    )
    if not isinstance(response, dict):
        raise GitHubAppError("GitHub returned a malformed access-token response.")
    token = response.get("token")
    if not isinstance(token, str) or not token:
        raise GitHubAppError("GitHub returned a malformed access-token response.")
    return token


def list_installation_repositories(
    client_id: str,
    private_key: bytes,
    installation_id: int,
) -> list[GitHubRepository]:
    installation_token = create_installation_access_token(
        client_id,
        private_key,
        installation_id,
    )
    response = _request_json(
        "GET",
        "/installation/repositories?per_page=100",
        installation_token,
        expected_status=200,
    )
    if not isinstance(response, dict) or not isinstance(
        response.get("repositories"), list
    ):
        raise GitHubAppError("GitHub returned a malformed repositories response.")

    repositories: list[GitHubRepository] = []
    for item in response["repositories"]:
        if not isinstance(item, dict):
            raise GitHubAppError("GitHub returned a malformed repository record.")
        repository_id = item.get("id")
        name = item.get("name")
        full_name = item.get("full_name")
        if (
            type(repository_id) is not int
            or not isinstance(name, str)
            or not isinstance(full_name, str)
        ):
            raise GitHubAppError("GitHub returned a malformed repository record.")
        repositories.append(
            {"id": repository_id, "name": name, "full_name": full_name}
        )

    return repositories


def register_github_installation(
    session: Session,
    opsreplay_organization_id: int,
    github_installation_id: int,
    github_installations: Sequence[GitHubInstallation],
) -> GitHubInstallationModel:
    organization = session.get(Organization, opsreplay_organization_id)
    if organization is None:
        raise GitHubAppError("The OpsReplay organization does not exist.")

    verified_installation = next(
        (
            installation
            for installation in github_installations
            if type(installation.get("id")) is int
            and installation["id"] == github_installation_id
        ),
        None,
    )
    if verified_installation is None:
        raise GitHubAppError(
            "The requested GitHub installation was not returned by GitHub."
        )

    existing_installation = organization.github_installation
    if existing_installation is not None:
        if (
            existing_installation.github_installation_id
            == github_installation_id
        ):
            return existing_installation
        raise GitHubAppError(
            "The OpsReplay organization is already linked to a different "
            "GitHub installation."
        )

    installation = GitHubInstallationModel(
        organization_id=organization.id,
        github_installation_id=github_installation_id,
        account_login=verified_installation["account_login"],
        account_type=verified_installation["account_type"],
    )
    session.add(installation)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise GitHubAppError(
            "The Organization or GitHub installation is already registered."
        ) from error

    session.refresh(installation)
    return installation


def get_github_installation_for_organization(
    session: Session,
    opsreplay_organization_id: int,
) -> GitHubInstallationModel:
    organization = session.get(Organization, opsreplay_organization_id)
    if organization is None:
        raise GitHubAppError("The OpsReplay organization does not exist.")

    installation = organization.github_installation
    if installation is None:
        raise GitHubAppError(
            "The OpsReplay organization has no registered GitHub installation."
        )
    return installation


# link_github_repository() safely connects an OpsReplay repository record to a real GitHub repository, 
# after verifying that the current GitHub App installation is actually allowed to access that GitHub repository.
def link_github_repository(
    session: Session,
    opsreplay_organization_id: int,
    opsreplay_repository_id: int,
    github_repository_id: int,
    installation_repositories: Sequence[GitHubRepository],
) -> Repository:
    repository = session.get(Repository, opsreplay_repository_id)
    if repository is None:
        raise GitHubAppError("The OpsReplay repository does not exist.")
    if repository.organization_id != opsreplay_organization_id:
        raise GitHubAppError(
            "The OpsReplay repository does not belong to the requested Organization."
        )

    accessible_repository = next(
        (
            repository
            for repository in installation_repositories
            if type(repository.get("id")) is int
            and repository["id"] == github_repository_id
        ),
        None,
    )
    if accessible_repository is None:
        raise GitHubAppError(
            "The requested GitHub repository is not accessible to this installation."
        )

    if (
        repository.github_repository_id is not None
        and repository.github_repository_id != github_repository_id
    ):
        raise GitHubAppError(
            "The OpsReplay repository is already linked to a different GitHub repository."
        )

    repository.github_repository_id = github_repository_id
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise GitHubAppError(
            "That GitHub repository is already linked to another OpsReplay repository."
        ) from error

    session.refresh(repository)
    return repository


def _request_json(
    method: str,
    path: str,
    token: str,
    *,
    expected_status: int,
    body: dict[str, object] | None = None,
) -> object:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
        "Authorization": f"Bearer {token}",
        "User-Agent": "OpsReplay",
    }
    request_body = None
    if body is not None:
        request_body = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(
        f"{GITHUB_API_URL}{path}",
        data=request_body,
        headers=headers,
        method=method,
    )
    try:
        with urlopen(request, timeout=10) as response:
            status = response.status
            response_body = response.read()
    except HTTPError as error:
        raise GitHubAppError(
            f"GitHub rejected the {method} {path} request (HTTP {error.code})."
        ) from error
    except (URLError, OSError) as error:
        raise GitHubAppError(
            f"Could not reach GitHub for the {method} {path} request."
        ) from error

    if status != expected_status:
        raise GitHubAppError(
            f"GitHub returned HTTP {status} for the {method} {path} request."
        )
    try:
        return json.loads(response_body)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise GitHubAppError("GitHub returned a malformed JSON response.") from error
