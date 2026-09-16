from fastapi.testclient import TestClient

from app.webhook_main import app


def test_webhook_ingress_exposes_only_github_webhook() -> None:
    assert str(app.url_path_for("receive_github_webhook")) == "/webhooks/github"

    with TestClient(app) as client:
        assert client.get("/webhooks/github").status_code == 405
        assert client.get("/health").status_code == 404
        assert client.get("/db-health").status_code == 404
        assert client.get("/organizations").status_code == 404
        assert client.get("/docs").status_code == 404
        assert client.get("/redoc").status_code == 404
        assert client.get("/openapi.json").status_code == 404
