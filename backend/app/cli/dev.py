import argparse
import hashlib
import hmac
import json
import os
import sys
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

from sqlalchemy.orm import Session

from app import database
from app.models.repository import Repository


DEFAULT_BASE_URL = "http://127.0.0.1:8000"

DEFAULT_BEFORE_SHA = "1" * 40
DEFAULT_AFTER_SHA = "2" * 40


class DevCliError(RuntimeError):
    """A local OpsReplay development command failed."""

# creation of the json body returns in UTF-8 bytes because GitHub's HMAC signature is calculated over the exact body that gets sent.
def _json_body(payload: dict[str, object]) -> bytes:
    return json.dumps(
        payload,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

# read the secret
def _required_secret(environment_variable: str) -> str:
    secret = os.getenv(environment_variable)

    if not secret:
        raise DevCliError(
            f"{environment_variable} is not configured."
        )

    return secret

# calculate the HMAC
def _sign_body(secret: str, body: bytes) -> str:
    digest = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    return f"sha256={digest}"

# replaces  Invoke-RestMethod ` -Method Post ` -Uri ... ` -Headers ... ` -Body ...
def _request_json(
    method: str,
    url: str,
    *,
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 10,
) -> object:
    request = Request(
        url,
        data=body,
        headers=headers or {},
        method=method,
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            response_body = response.read()

    except HTTPError as error:
        error_body = error.read().decode(
            "utf-8",
            errors="replace",
        )
        raise DevCliError(
            f"{method} {url} returned HTTP "
            f"{error.code}: {error_body}"
        ) from error

    except URLError as error:
        raise DevCliError(
            f"Could not reach OpsReplay at {url}: "
            f"{error.reason}"
        ) from error

    if not response_body:
        return {}

    try:
        return json.loads(response_body)
    except json.JSONDecodeError:
        return response_body.decode(
            "utf-8",
            errors="replace",
        )

def _print_result(result: object) -> None:
    if isinstance(result, str):
        print(result)
        return

    print(json.dumps(result, indent=2))

# Let the CLI translate OpsReplay repository ID -> GitHub repository ID
def _github_repository_id(
    repository_id: int,
) -> int:
    if database.engine is None:
        raise DevCliError(
            "DATABASE_URL is required."
        )

    with Session(database.engine) as session:
        repository = session.get(
            Repository,
            repository_id,
        )

        if repository is None:
            raise DevCliError(
                f"Repository {repository_id} does not exist."
            )

        github_repository_id = (
            repository.github_repository_id
        )

    if github_repository_id is None:
        raise DevCliError(
            f"Repository {repository_id} is not linked "
            "to a GitHub repository."
        )

    return github_repository_id

# unique event-ID generator for example dev-push-a93f103d8b22, dev-alert-c9182ad3663
def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"

# replaces $body = '{"ref":"refs/heads/main", ... }'
def _build_push_payload(
    github_repository_id: int,
    ref: str,
    before: str,
    after: str,
) -> dict[str, object]:
    return {
        "ref": ref,
        "before": before,
        "after": after,
        "repository": {
            "id": github_repository_id,
        },
    }


def _send_github_webhook(
    *,
    base_url: str,
    event: str,
    payload: dict[str, object],
    delivery_id: str,
) -> object:
    body = _json_body(payload)

    secret = _required_secret(
        "GITHUB_WEBHOOK_SECRET"
    )

    signature = _sign_body(secret, body)

    return _request_json(
        "POST",
        f"{base_url}/webhooks/github",
        body=body,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": signature,
            "X-GitHub-Event": event,
            "X-GitHub-Delivery": delivery_id,
        },
    )

def _command_github_push(
    args: argparse.Namespace,
) -> None:
    github_repository_id = _github_repository_id(
        args.repository_id
    )

    payload = _build_push_payload(
        github_repository_id,
        args.ref,
        args.before,
        args.after,
    )

    delivery_id = (
        args.delivery_id
        or _new_id("dev-push")
    )

    result = _send_github_webhook(
        base_url=args.base_url,
        event="push",
        payload=payload,
        delivery_id=delivery_id,
    )

    _print_result(result)

def _build_deployment_status_payload(
    github_repository_id: int,
    deployment_id: int,
    state: str,
    environment: str,
) -> dict[str, object]:
    return {
        "action": "created",
        "deployment": {
            "id": deployment_id,
        },
        "deployment_status": {
            "state": state,
            "environment": environment,
        },
        "repository": {
            "id": github_repository_id,
        },
    }


def _command_deployment_status(
    args: argparse.Namespace,
) -> None:
    github_repository_id = _github_repository_id(
        args.repository_id
    )

    payload = _build_deployment_status_payload(
        github_repository_id,
        args.deployment_id,
        args.state,
        args.environment,
    )

    delivery_id = (
        args.delivery_id
        or _new_id("dev-deployment")
    )

    result = _send_github_webhook(
        base_url=args.base_url,
        event="deployment_status",
        payload=payload,
        delivery_id=delivery_id,
    )

    _print_result(result)



def _build_alert_payload(
    repository_id: int,
    severity: str,
    title: str,
    observed_at: str,
) -> dict[str, object]:
    return {
        "repository_id": repository_id,
        "severity": severity,
        "title": title,
        "observed_at": observed_at,
    }

def _build_incident_payload(
    trigger_timeline_event_id: int,
    lookback_minutes: int,
    lookahead_minutes: int
) -> dict[str, object]:
    return {
        "trigger_timeline_event_id": trigger_timeline_event_id,
        "lookback_minutes": lookback_minutes,
        "lookahead_minutes": lookahead_minutes,
       
    }


def _command_alert(
    args: argparse.Namespace,
) -> None:
    observed_at = args.observed_at

    if observed_at is None:
        observed_at = datetime.now(
            timezone.utc
        ).isoformat()

    payload = _build_alert_payload(
        args.repository_id,
        args.severity,
        args.title,
        observed_at,
    )

    body = _json_body(payload)

    secret = _required_secret(
        "ALERT_WEBHOOK_SECRET"
    )

    signature = _sign_body(
        secret,
        body,
    )

    event_id = (
        args.event_id
        or _new_id("dev-alert")
    )

    result = _request_json(
        "POST",
        f"{args.base_url}/webhooks/alerts",
        body=body,
        headers={
            "Content-Type": "application/json",
            "X-OpsReplay-Signature-256": signature,
            "X-OpsReplay-Event-ID": event_id,
        },
    )

    _print_result(result)



def _command_timeline(
    args: argparse.Namespace,
) -> None:
    url = (
        f"{args.base_url}"
        f"/organizations/{args.organization_id}"
        f"/repositories/{args.repository_id}"
        "/timeline"
    )

    result = _request_json(
        "GET",
        url,
    )

    _print_result(result)


def _command_context(
    args: argparse.Namespace,
) -> None:
    query = urlencode(
        {
            "lookback_minutes": args.lookback,
            "lookahead_minutes": args.lookahead,
        }
    )

    url = (
        f"{args.base_url}"
        f"/organizations/{args.organization_id}"
        f"/repositories/{args.repository_id}"
        f"/timeline/{args.event_id}/context"
        f"?{query}"
    )

    result = _request_json(
        "GET",
        url,
    )

    _print_result(result)

def _command_incident_create(
        args: argparse.Namespace

) -> None:
    
    payload = _build_incident_payload(
            args.trigger_event_id,
            args.lookback,
            args.lookahead,
            
        )
    
    body = _json_body(payload)
    
    result = _request_json(
        "POST",
        f"{args.base_url}/organizations/{args.organization_id}/repositories/{args.repository_id}/incidents",
        body=body,
        headers={
            "Content-Type": "application/json",     
        },)

    _print_result(result)
    

def _command_incident_get(
    args: argparse.Namespace,
) -> None:
    url = (
        f"{args.base_url}"
        f"/organizations/{args.organization_id}"
        f"/repositories/{args.repository_id}"
        f"/incidents/{args.incident_id}"
    )

    result = _request_json(
        "GET",
        url,
    )

    _print_result(result)


def _command_incident_resolve(
    args: argparse.Namespace,
) -> None:
    url = (
        f"{args.base_url}"
        f"/organizations/{args.organization_id}"
        f"/repositories/{args.repository_id}"
        f"/incidents/{args.incident_id}/resolve"
    )

    result = _request_json(
        "POST",
        url,
    )

    _print_result(result)


def _command_incident_postmortem_draft(
    args: argparse.Namespace,
) -> None:
    url = (
        f"{args.base_url}"
        f"/organizations/{args.organization_id}"
        f"/repositories/{args.repository_id}"
        f"/incidents/{args.incident_id}/postmortem-draft"
    )

    result = _request_json(
        "POST",
        url,
        timeout=60,
    )

    _print_result(result)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Local development helpers for OpsReplay."
        )
    )

    parser.add_argument(
        "--base-url",
        default=os.getenv(
            "OPSREPLAY_BASE_URL",
            DEFAULT_BASE_URL,
        ),
        help=(
            "OpsReplay API URL. "
            f"Default: {DEFAULT_BASE_URL}"
        ),
    )

    # push parser
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    push_parser = subparsers.add_parser(
        "github-push",
        help="Send a signed fake GitHub push webhook.",
    )

    push_parser.add_argument(
        "--repository-id",
        type=int,
        required=True,
    )

    push_parser.add_argument(
        "--ref",
        default="refs/heads/main",
    )

    push_parser.add_argument(
        "--before",
        default=DEFAULT_BEFORE_SHA,
    )

    push_parser.add_argument(
        "--after",
        default=DEFAULT_AFTER_SHA,
    )

    push_parser.add_argument(
        "--delivery-id",
    )

    push_parser.set_defaults(
        handler=_command_github_push
    )

    # deployment status
    deployment_parser = subparsers.add_parser(
        "deployment-status",
        help=(
            "Send a signed fake GitHub "
            "deployment_status webhook."
        ),
    )

    deployment_parser.add_argument(
        "--repository-id",
        type=int,
        required=True,
    )

    deployment_parser.add_argument(
        "--deployment-id",
        type=int,
        required=True,
    )

    deployment_parser.add_argument(
        "--state",
        required=True,
    )

    deployment_parser.add_argument(
        "--environment",
        default="production",
    )

    deployment_parser.add_argument(
        "--delivery-id",
    )

    deployment_parser.set_defaults(
        handler=_command_deployment_status
    )

    # alert parser
    alert_parser = subparsers.add_parser(
        "alert",
        help="Send a signed fake alert webhook.",
    )

    alert_parser.add_argument(
        "--repository-id",
        type=int,
        required=True,
    )

    alert_parser.add_argument(
        "--severity",
        required=True,
    )

    alert_parser.add_argument(
        "--title",
        required=True,
    )

    alert_parser.add_argument(
        "--observed-at",
    )

    alert_parser.add_argument(
        "--event-id",
    )

    alert_parser.set_defaults(
        handler=_command_alert
    )

    # timeline parser
    timeline_parser = subparsers.add_parser(
        "timeline",
        help="Read a repository timeline.",
    )

    timeline_parser.add_argument(
        "--organization-id",
        type=int,
        required=True,
    )

    timeline_parser.add_argument(
        "--repository-id",
        type=int,
        required=True,
    )

    timeline_parser.set_defaults(
        handler=_command_timeline
    )

    # context parser
    context_parser = subparsers.add_parser(
        "context",
        help="Read investigation context around an alert.",
    )

    context_parser.add_argument(
        "--organization-id",
        type=int,
        required=True,
    )

    context_parser.add_argument(
        "--repository-id",
        type=int,
        required=True,
    )

    context_parser.add_argument(
        "--event-id",
        type=int,
        required=True,
    )

    context_parser.add_argument(
        "--lookback",
        type=int,
        default=30,
    )

    context_parser.add_argument(
        "--lookahead",
        type=int,
        default=30,
    )

    context_parser.set_defaults(
        handler=_command_context
    )

    # incident create parser
    incident_create_parser = subparsers.add_parser(
        "incident",
        help="Send a fake incident",
    )
    
    incident_create_parser.add_argument(
        "--organization-id",
        type=int,
        required=True,
    )
    
    incident_create_parser.add_argument(
        "--repository-id",
        type=int,
        required=True,
    )
    
    incident_create_parser.add_argument(
        "--trigger-event-id",
        type=int,
        required=True,
    )
    
    incident_create_parser.add_argument(
        "--lookback",
        type=int,
        default=30,
    )
    
    incident_create_parser.add_argument(
        "--lookahead",
        type=int,
        default=30,
    )
    
    incident_create_parser.set_defaults(
        handler=_command_incident_create
    )

    # incident get parser
    incident_get_parser = subparsers.add_parser(
        "incident-get",
        help="Read an existing incident.",
    )
    
    incident_get_parser.add_argument(
        "--organization-id",
        type=int,
        required=True,
    )
    
    incident_get_parser.add_argument(
        "--repository-id",
        type=int,
        required=True,
    )
    
    incident_get_parser.add_argument(
        "--incident-id",
        type=int,
        required=True,
    )
    
    incident_get_parser.set_defaults(
        handler=_command_incident_get
    )

    incident_resolve_parser = subparsers.add_parser(
        "incident-resolve",
        help="Resolve an existing incident.",
    )

    incident_resolve_parser.add_argument(
        "--organization-id",
        type=int,
        required=True,
    )

    incident_resolve_parser.add_argument(
        "--repository-id",
        type=int,
        required=True,
    )

    incident_resolve_parser.add_argument(
        "--incident-id",
        type=int,
        required=True,
    )

    incident_resolve_parser.set_defaults(
        handler=_command_incident_resolve
    )

    incident_postmortem_parser = subparsers.add_parser(
        "incident-postmortem-draft",
        help="Generate a postmortem draft for a resolved incident.",
    )

    incident_postmortem_parser.add_argument(
        "--organization-id",
        type=int,
        required=True,
    )

    incident_postmortem_parser.add_argument(
        "--repository-id",
        type=int,
        required=True,
    )

    incident_postmortem_parser.add_argument(
        "--incident-id",
        type=int,
        required=True,
    )

    incident_postmortem_parser.set_defaults(
        handler=_command_incident_postmortem_draft
    )

    return parser



def main() -> int:
    args = _build_parser().parse_args()

    try:
        args.handler(args)
        return 0

    except DevCliError as error:
        print(
            f"Error: {error}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
