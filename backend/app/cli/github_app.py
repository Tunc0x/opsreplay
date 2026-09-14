import argparse
import os
import sys
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import database
from app.integrations.github_app import (
    GitHubAppError,
    get_github_installation_for_organization,
    link_github_repository,
    list_github_app_installations,
    list_installation_repositories,
    register_github_installation,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Operate the OpsReplay GitHub App.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("installations", help="List GitHub App installations.")

    register_parser = subparsers.add_parser(
        "register-installation",
        help="Register an installation for an OpsReplay organization.",
    )
    register_parser.add_argument(
        "--opsreplay-organization-id",
        type=int,
        required=True,
    )
    register_parser.add_argument(
        "--github-installation-id",
        type=int,
        required=True,
    )

    repositories_parser = subparsers.add_parser(
        "repositories",
        help="List repositories accessible to an installation.",
    )
    repositories_parser.add_argument(
        "--opsreplay-organization-id",
        type=int,
        required=True,
    )

    link_parser = subparsers.add_parser(
        "link",
        help="Link an existing OpsReplay repository to GitHub.",
    )
    link_parser.add_argument(
        "--opsreplay-organization-id",
        type=int,
        required=True,
    )
    link_parser.add_argument("--opsreplay-repository-id", type=int, required=True)
    link_parser.add_argument("--github-repository-id", type=int, required=True)

    return parser


def _load_credentials() -> tuple[str, bytes]:
    client_id = os.getenv("GITHUB_APP_CLIENT_ID")
    if not client_id:
        raise GitHubAppError("GITHUB_APP_CLIENT_ID is required.")

    private_key_path = os.getenv("GITHUB_APP_PRIVATE_KEY_PATH")
    if not private_key_path:
        raise GitHubAppError("GITHUB_APP_PRIVATE_KEY_PATH is required.")
    try:
        private_key = Path(private_key_path).read_bytes()
    except OSError as error:
        raise GitHubAppError(
            f"Could not read the GitHub App private key at {private_key_path}."
        ) from error

    return client_id, private_key


def main() -> int:
    args = _build_parser().parse_args()
    try:
        client_id, private_key = _load_credentials()

        if args.command == "installations":
            installations = list_github_app_installations(client_id, private_key)
            for installation in installations:
                print(
                    f"Installation {installation['id']}: "
                    f"{installation['account_login']} "
                    f"({installation['account_type']})"
                )
            return 0

        if args.command == "register-installation":
            installations = list_github_app_installations(client_id, private_key)
            if database.engine is None:
                raise GitHubAppError("DATABASE_URL is required for this command.")
            with Session(database.engine) as session:
                installation = register_github_installation(
                    session,
                    args.opsreplay_organization_id,
                    args.github_installation_id,
                    installations,
                )
                installation_details = (
                    installation.organization_id,
                    installation.github_installation_id,
                    installation.account_login,
                    installation.account_type,
                )
            print(
                f"Registered OpsReplay organization {installation_details[0]} "
                f"with GitHub installation {installation_details[1]} "
                f"({installation_details[2]}, {installation_details[3]})."
            )
            return 0

        if database.engine is None:
            raise GitHubAppError("DATABASE_URL is required for this command.")
        with Session(database.engine) as session:
            installation = get_github_installation_for_organization(
                session,
                args.opsreplay_organization_id,
            )
            github_installation_id = installation.github_installation_id

        repositories = list_installation_repositories(
            client_id,
            private_key,
            github_installation_id,
        )
        if args.command == "repositories":
            for repository in repositories:
                print(f"Repository {repository['id']}: {repository['full_name']}")
            return 0

        with Session(database.engine) as session:
            linked_repository = link_github_repository(
                session,
                args.opsreplay_organization_id,
                args.opsreplay_repository_id,
                args.github_repository_id,
                repositories,
            )
        verified_repository = next(
            repository
            for repository in repositories
            if repository["id"] == args.github_repository_id
        )
        print(
            f"Linked OpsReplay repository {linked_repository.id} to GitHub repository "
            f"{args.github_repository_id} ({verified_repository['full_name']})."
        )
        return 0
    except GitHubAppError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except SQLAlchemyError:
        print("Error: the database operation failed.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
