import os

os.environ["JWT_SECRET"] = "test-only-secret-with-at-least-32-characters"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app


@pytest.fixture
def client(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path}/test.db", connect_args={"check_same_thread": False}
    )

    @event.listens_for(engine, "connect")
    def fk(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)

    def override():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture
def household(client):
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Rita",
            "email": "rita@example.com",
            "password": "strong-test-password",
            "family_name": "Rita & Jean",
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()
    headers = {"Authorization": "Bearer " + data["access_token"]}
    client.headers.update(headers)
    member = client.post(
        "/api/members",
        json={
            "name": "Jean",
            "email": "jean@example.com",
            "password": "another-test-password",
        },
    ).json()
    account = client.post(
        "/api/accounts", json={"name": "Conta conjunta", "initial_balance": "100.00"}
    ).json()
    categories = client.get("/api/categories").json()
    return {
        "headers": headers,
        "rita": data["user"]["id"],
        "jean": member["id"],
        "account": account["id"],
        "expense": next(c["id"] for c in categories if c["kind"] == "expense"),
        "income": next(c["id"] for c in categories if c["kind"] == "income"),
    }
