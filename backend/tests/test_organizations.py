from fastapi.testclient import TestClient


def test_create_and_get_organization(client: TestClient) -> None:
    create_response = client.post(
        "/organizations",
        json={"name": "Test Engineering"},
    )

    assert create_response.status_code == 201

    created_organization = create_response.json()
    assert created_organization["name"] == "Test Engineering"
    assert isinstance(created_organization["id"], int)
    assert created_organization["created_at"]

    get_response = client.get(
        f"/organizations/{created_organization['id']}"
    )

    assert get_response.status_code == 200
    assert get_response.json() == created_organization


def test_get_missing_organization_returns_404(
    client: TestClient,
) -> None:
    response = client.get("/organizations/999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Organization not found"}
