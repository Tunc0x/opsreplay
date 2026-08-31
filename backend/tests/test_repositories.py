from fastapi.testclient import TestClient


def test_create_and_list_repositories_for_organization(
    client: TestClient,
) -> None:
    organization_response = client.post(
        "/organizations",
        json={"name": "Test Engineering"},
    )
    assert organization_response.status_code == 201
    organization_id = organization_response.json()["id"]

    payments_response = client.post(
        f"/organizations/{organization_id}/repositories",
        json={"name": "payments-api"},
    )
    frontend_response = client.post(
        f"/organizations/{organization_id}/repositories",
        json={"name": "customer-frontend"},
    )

    assert payments_response.status_code == 201
    assert frontend_response.status_code == 201
    assert payments_response.json()["organization_id"] == organization_id
    assert frontend_response.json()["organization_id"] == organization_id

    list_response = client.get(
        f"/organizations/{organization_id}/repositories"
    )

    assert list_response.status_code == 200
    repositories = list_response.json()
    assert len(repositories) == 2
    assert [repository["name"] for repository in repositories] == [
        "payments-api",
        "customer-frontend",
    ]


def test_create_repository_for_missing_organization_returns_404(
    client: TestClient,
) -> None:
    response = client.post(
        "/organizations/999999/repositories",
        json={"name": "ghost-repository"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Organization not found"}
