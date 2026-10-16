from conftest import register


def test_session_refresh_cookie_and_logout(client):
    _, token = register(client, "rita@example.com")
    assert "finance_refresh" in client.cookies
    login = client.post(
        "/api/auth/login",
        json={"email": "rita@example.com", "password": "strong-test-password"},
    )
    assert "httponly" in login.headers["set-cookie"].lower()
    assert "samesite=strict" in login.headers["set-cookie"].lower()
    assert "refresh_token" not in login.json()
    refresh = client.post("/api/auth/refresh")
    assert refresh.status_code == 200
    client.headers["Authorization"] = "Bearer " + refresh.json()["access_token"]
    assert client.post("/api/auth/logout").status_code == 204
    assert "finance_refresh" not in client.cookies
    assert client.post("/api/auth/refresh").status_code == 401


def test_confirmation_does_not_issue_app_session(client):
    client.fake_auth.confirmation_required = True
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Rita",
            "email": "rita@example.com",
            "password": "strong-test-password",
            "family_name": "Família",
        },
    )
    assert response.status_code == 201
    assert response.json() == {"confirmation_required": True}
    assert not client.cookies.get("finance_refresh")


def test_recovery_and_password_update_use_supabase(client):
    register(client, "rita@example.com")
    assert (
        client.post("/api/auth/recover", json={"email": "rita@example.com"}).status_code
        == 200
    )
    assert (
        client.put(
            "/api/auth/password", json={"password": "new-strong-password"}
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/auth/login",
            json={"email": "rita@example.com", "password": "new-strong-password"},
        ).status_code
        == 200
    )
    assert any("/auth/v1/recover" in call[1] for call in client.fake_auth.calls)


def test_invitation_is_single_use_and_group_has_two_members(client, household):
    assert client.post("/api/members/invitations").status_code == 409
    result = client.post(
        "/api/auth/register",
        json={
            "name": "Terceira pessoa",
            "email": "third@example.com",
            "password": "strong-test-password",
            "invitation_code": "invalid",
        },
    )
    client.headers["Authorization"] = "Bearer " + result.json()["access_token"]
    assert client.get("/api/me").status_code == 409


def test_csrf_origin_rejected(client):
    assert (
        client.post(
            "/api/auth/refresh", headers={"Origin": "https://attacker.example"}
        ).status_code
        == 403
    )
