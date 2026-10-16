from datetime import date, timedelta
from decimal import Decimal

TODAY = date.today().isoformat()
MONTH = TODAY[:7]


def entry(h, **changes):
    data = {
        "description": "Supermercado",
        "amount": "100.00",
        "kind": "expense",
        "due_date": TODAY,
        "owner_id": h["rita"],
        "payer_id": h["rita"],
        "account_id": h["account"],
        "category_id": h["expense"],
    }
    data.update(changes)
    return data


def test_auth_and_group_creation(client):
    assert client.get("/api/accounts").status_code == 401
    payload = {
        "name": "Rita",
        "email": "rita@example.com",
        "password": "safe-password-123",
        "family_name": "Família",
    }
    assert client.post("/api/auth/register", json=payload).status_code == 201
    assert client.post("/api/auth/register", json=payload).status_code == 400
    assert (
        client.post(
            "/api/auth/login", json={"email": payload["email"], "password": "wrong"}
        ).status_code
        == 401
    )
    response = client.post(
        "/api/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert response.status_code == 200
    assert "password_hash" not in response.text


def test_pending_and_settled_balances(client, household):
    h = household
    expense = client.post("/api/entries", json=entry(h)).json()
    assert Decimal(client.get("/api/accounts").json()[0]["visible_balance"]) == 100
    income = entry(
        h,
        description="Salário",
        kind="income",
        category_id=h["income"],
        amount="1000.10",
        settled_date=TODAY,
    )
    assert client.post("/api/entries", json=income).status_code == 201
    updated = client.put(
        "/api/entries/" + str(expense["id"]), json=entry(h, settled_date=TODAY)
    )
    assert updated.status_code == 200
    assert Decimal(client.get("/api/accounts").json()[0]["visible_balance"]) == Decimal(
        "1000.10"
    )
    d = client.get("/api/dashboard", params={"month": MONTH}).json()
    assert Decimal(d["expense"]) == 100
    assert Decimal(d["savings"]) == Decimal("900.10")
    # A repeated update is idempotent, with no duplicate debit.
    client.put("/api/entries/" + str(expense["id"]), json=entry(h, settled_date=TODAY))
    assert Decimal(client.get("/api/accounts").json()[0]["visible_balance"]) == Decimal(
        "1000.10"
    )


def test_custom_split_and_cancel(client, household):
    h = household
    result = client.post(
        "/api/entries",
        json=entry(
            h,
            amount="1000.01",
            shared=True,
            split_mode="custom",
            share_percent="40",
            settled_date=TODAY,
        ),
    )
    assert result.status_code == 201
    d = client.get("/api/dashboard", params={"month": MONTH}).json()
    assert Decimal(d["expense"]) == Decimal("1000.01")
    assert {s["user_id"]: Decimal(s["net"]) for s in d["settlement"]} == {
        h["rita"]: Decimal("600.01"),
        h["jean"]: Decimal("-600.01"),
    }
    assert client.delete("/api/entries/" + str(result.json()["id"])).status_code == 204
    assert client.get("/api/entries").json() == []
    assert Decimal(client.get("/api/accounts").json()[0]["visible_balance"]) == 100
    assert client.delete("/api/entries/" + str(result.json()["id"])).status_code == 404


def test_proportional_split_snapshots_income_ratio(client, household):
    h = household
    for owner, amount in [(h["rita"], "2000"), (h["jean"], "3000")]:
        assert (
            client.post(
                "/api/entries",
                json=entry(
                    h,
                    owner_id=owner,
                    amount=amount,
                    kind="income",
                    category_id=h["income"],
                ),
            ).status_code
            == 201
        )
    result = client.post(
        "/api/entries", json=entry(h, shared=True, split_mode="proportional")
    )
    assert result.status_code == 201
    assert Decimal(result.json()["share_percent"]) == 40


def test_private_records_do_not_leak_into_aggregates(client, household):
    h = household
    result = client.post(
        "/api/entries", json=entry(h, private=True, settled_date=TODAY)
    )
    assert result.status_code == 201
    login = client.post(
        "/api/auth/login",
        json={"email": "jean@example.com", "password": "strong-test-password"},
    ).json()
    client.headers["Authorization"] = "Bearer " + login["access_token"]
    assert client.get("/api/entries").json() == []
    dashboard = client.get("/api/dashboard", params={"month": MONTH}).json()
    assert Decimal(dashboard["expense"]) == 0
    assert Decimal(dashboard["accounts"][0]["visible_balance"]) == 100
    assert (
        client.put(
            "/api/entries/" + str(result.json()["id"]), json=entry(h)
        ).status_code
        == 404
    )


def test_group_isolation_and_foreign_keys(client, household):
    h = household
    result = client.post("/api/entries", json=entry(h)).json()
    other = client.post(
        "/api/auth/register",
        json={
            "name": "Outra pessoa",
            "email": "other@example.com",
            "password": "another-password",
            "family_name": "Outro grupo",
        },
    ).json()
    client.headers["Authorization"] = "Bearer " + other["access_token"]
    assert client.get("/api/me").status_code == 200
    assert client.get("/api/entries").json() == []
    assert client.get("/api/accounts").json() == []
    assert client.delete("/api/entries/" + str(result["id"])).status_code == 404
    assert client.post("/api/entries", json=entry(h)).status_code == 404


def test_member_permissions(client, household):
    h = household
    result = client.post("/api/entries", json=entry(h)).json()
    login = client.post(
        "/api/auth/login",
        json={"email": "jean@example.com", "password": "strong-test-password"},
    ).json()
    client.headers["Authorization"] = "Bearer " + login["access_token"]
    assert client.post("/api/accounts", json={"name": "Inválida"}).status_code == 403
    assert (
        client.post(
            "/api/categories", json={"name": "Nova", "kind": "expense"}
        ).status_code
        == 403
    )
    assert client.post("/api/entries", json=entry(h)).status_code == 403
    assert client.delete("/api/entries/" + str(result["id"])).status_code == 403
    assert (
        client.post("/api/entries", json=entry(h, owner_id=h["jean"])).status_code
        == 201
    )


def test_validation_and_category_history(client, household):
    h = household
    for changes in [
        {"amount": "-1"},
        {"amount": "0.001"},
        {"shared": True, "private": True},
        {"settled_date": (date.today() + timedelta(days=1)).isoformat()},
    ]:
        assert client.post("/api/entries", json=entry(h, **changes)).status_code == 422
    assert (
        client.post("/api/entries", json=entry(h, category_id=h["income"])).status_code
        == 422
    )
    assert (
        client.post(
            "/api/entries", json=entry(h, shared=True, split_mode="proportional")
        ).status_code
        == 422
    )
    assert client.post("/api/entries", json=entry(h)).status_code == 201
    assert client.delete("/api/categories/" + str(h["expense"])).status_code == 409
    assert client.get("/api/entries?month=2026-99").status_code == 422


def test_invalid_token(client):
    assert (
        client.get(
            "/api/me", headers={"Authorization": "Bearer forged-or-expired"}
        ).status_code
        == 401
    )


def test_static_application(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Rita & Jean Finance" in response.text
    assert response.headers["X-Frame-Options"] == "DENY"
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/vendor/chart.umd.js").status_code == 200
