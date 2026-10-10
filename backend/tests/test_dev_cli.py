from pathlib import Path

from pytest import MonkeyPatch

from app.cli import dev
from app.cli.dev import (
    _build_deployment_status_payload,
    _build_incident_payload,
    _build_push_payload,
    _json_body,
    _sign_body,
)

def test_sign_body_uses_hmac_sha256() -> None:
    body = b'{"hello":"world"}'

    signature = _sign_body(
        "test-secret",
        body,
    )

    assert signature == (
        "sha256="
        "84cc33df716ed0b0598f07437c94069a"
        "ce3730358778a592bd6bbd1423d111f3"
    )

def test_json_body_is_compact_utf8_json() -> None:
    body = _json_body(
        {
            "ref": "refs/heads/main",
        }
    )

    assert body == b'{"ref":"refs/heads/main"}'


def test_build_push_payload() -> None:
    payload = _build_push_payload(
        12345,
        "refs/heads/main",
        "1" * 40,
        "2" * 40,
    )

    assert payload == {
        "ref": "refs/heads/main",
        "before": "1" * 40,
        "after": "2" * 40,
        "repository": {
            "id": 12345,
        },
    }

def test_build_deployment_status_payload() -> None:
    payload = _build_deployment_status_payload(
        12345,
        999,
        "success",
        "production",
    )

    assert payload == {
        "action": "created",
        "deployment": {
            "id": 999,
        },
        "deployment_status": {
            "state": "success",
            "environment": "production",
        },
        "repository": {
            "id": 12345,
        },
    }

def test_build_incident_payload() -> None:
    payload = _build_incident_payload(
        36,
        30,
        45,
    )

    assert payload == {
        "trigger_timeline_event_id": 36,
        "lookback_minutes": 30,
        "lookahead_minutes": 45,
    }


def test_incident_resolve_posts_to_resolve_endpoint(
    monkeypatch: MonkeyPatch,
) -> None:
    request_calls: list[tuple[str, str]] = []
    printed_results: list[object] = []
    response = {
        "id": 23,
        "status": "resolved",
    }

    def fake_request_json(method: str, url: str) -> object:
        request_calls.append((method, url))
        return response

    monkeypatch.setattr(dev, "_request_json", fake_request_json)
    monkeypatch.setattr(dev, "_print_result", printed_results.append)
    args = dev._build_parser().parse_args(
        [
            "--base-url",
            "http://opsreplay.test:8000",
            "incident-resolve",
            "--organization-id",
            "4",
            "--repository-id",
            "12",
            "--incident-id",
            "23",
        ]
    )

    assert args.handler is dev._command_incident_resolve
    args.handler(args)

    assert request_calls == [
        (
            "POST",
            "http://opsreplay.test:8000/organizations/4/repositories/12/"
            "incidents/23/resolve",
        )
    ]
    assert printed_results == [response]


def test_incident_postmortem_draft_posts_to_generation_endpoint(
    monkeypatch: MonkeyPatch,
) -> None:
    request_calls: list[tuple[str, str, float]] = []
    printed_results: list[object] = []
    response = {
        "incident_id": 23,
        "model": "gpt-6-luna",
        "draft": {},
        "evidence": [],
    }

    def fake_request_json(method: str, url: str, *, timeout: float = 10,) -> object:
        request_calls.append((method, url, timeout))
        return response

    monkeypatch.setattr(dev, "_request_json", fake_request_json)
    monkeypatch.setattr(dev, "_print_result", printed_results.append)
    args = dev._build_parser().parse_args(
        [
            "--base-url",
            "http://opsreplay.test:8000",
            "incident-postmortem-draft",
            "--organization-id",
            "4",
            "--repository-id",
            "12",
            "--incident-id",
            "23",
        ]
    )

    assert args.handler is dev._command_incident_postmortem_draft
    args.handler(args)

    assert request_calls == [
        (
            "POST",
            "http://opsreplay.test:8000/organizations/4/repositories/12/"
            "incidents/23/postmortem-draft",
            60
        )
    ]
    assert printed_results == [response]


def test_incident_postmortem_draft_get_reads_persisted_draft(
    monkeypatch: MonkeyPatch,
) -> None:
    request_calls: list[tuple[str, str]] = []
    printed_results: list[object] = []
    response = {
        "id": 31,
        "incident_id": 23,
        "model": "gpt-6-luna",
        "draft": {},
        "evidence": [],
    }

    def fake_request_json(method: str, url: str) -> object:
        request_calls.append((method, url))
        return response

    monkeypatch.setattr(dev, "_request_json", fake_request_json)
    monkeypatch.setattr(dev, "_print_result", printed_results.append)
    args = dev._build_parser().parse_args(
        [
            "--base-url",
            "http://opsreplay.test:8000",
            "incident-postmortem-draft-get",
            "--organization-id",
            "4",
            "--repository-id",
            "12",
            "--incident-id",
            "23",
        ]
    )

    assert args.handler is dev._command_incident_postmortem_draft_get
    args.handler(args)

    assert request_calls == [
        (
            "GET",
            "http://opsreplay.test:8000/organizations/4/repositories/12/"
            "incidents/23/postmortem-draft",
        )
    ]
    assert printed_results == [response]


def test_incident_postmortem_draft_put_replaces_persisted_draft(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    request_calls: list[dict[str, object]] = []
    printed_results: list[object] = []
    draft = {
        "summary": [
            {
                "text": "The production alert was investigated.",
                "evidence_event_ids": [10],
            }
        ],
        "timeline": [
            {
                "text": "The alert was observed.",
                "evidence_event_ids": [10],
            }
        ],
        "impact": None,
        "root_cause": None,
        "resolution": None,
        "unknowns": ["The root cause is not established."],
    }
    draft_file = tmp_path / "postmortem-draft.json"
    draft_file.write_bytes(_json_body(draft))
    response = {
        "id": 31,
        "incident_id": 23,
        "model": "gpt-6-luna",
        "draft": draft,
        "evidence": [],
    }

    def fake_request_json(
        method: str,
        url: str,
        *,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> object:
        request_calls.append(
            {
                "method": method,
                "url": url,
                "body": body,
                "headers": headers,
            }
        )
        return response

    monkeypatch.setattr(dev, "_request_json", fake_request_json)
    monkeypatch.setattr(dev, "_print_result", printed_results.append)
    args = dev._build_parser().parse_args(
        [
            "--base-url",
            "http://opsreplay.test:8000",
            "incident-postmortem-draft-put",
            "--organization-id",
            "4",
            "--repository-id",
            "12",
            "--incident-id",
            "23",
            "--draft-file",
            str(draft_file),
        ]
    )

    assert args.handler is dev._command_incident_postmortem_draft_put
    args.handler(args)

    assert request_calls == [
        {
            "method": "PUT",
            "url": (
                "http://opsreplay.test:8000/organizations/4/repositories/12/"
                "incidents/23/postmortem-draft"
            ),
            "body": _json_body({"draft": draft}),
            "headers": {
                "Content-Type": "application/json",
            },
        }
    ]
    assert printed_results == [response]
