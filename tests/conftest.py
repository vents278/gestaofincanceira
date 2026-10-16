"""Real PostgreSQL + Supabase-compatible Auth/Storage schema contracts.
Auth HTTP is mocked; these tests do not claim a hosted Supabase deployment.
"""

import os
from uuid import uuid4

import httpx
import pgserver
import psycopg
import pytest
from fastapi.testclient import TestClient

os.environ.update(
    SUPABASE_URL="https://test.supabase.co",
    SUPABASE_PUBLISHABLE_KEY="sb_publishable_test",
    APP_URL="http://testserver",
)

from app.config import settings
from app.database import get_engine
from app.main import app
from scripts.migrate import export_sql, migrate

BOOTSTRAP = """
create role anon nologin;
create role authenticated nologin;
create schema auth;
create table auth.users(id uuid primary key,email text not null,raw_user_meta_data jsonb not null default '{}');
create function auth.uid() returns uuid language sql stable as $$
 select (nullif(current_setting('request.jwt.claims',true),'')::jsonb->>'sub')::uuid
$$;
grant usage on schema public,auth to authenticated;
grant execute on function auth.uid() to authenticated;
create schema storage;
create table storage.buckets(id text primary key,name text,public boolean,file_size_limit bigint,allowed_mime_types text[]);
create table storage.objects(id uuid primary key default gen_random_uuid(),bucket_id text references storage.buckets(id),name text);
alter table storage.objects enable row level security;
grant usage on schema storage to authenticated;
grant select,insert,update,delete on storage.objects to authenticated;
"""


@pytest.fixture(scope="session")
def postgres(tmp_path_factory):
    data = tmp_path_factory.mktemp("postgres") / "data"
    server = pgserver.get_server(data, cleanup_mode="delete")
    dsn = server.get_uri()
    with psycopg.connect(dsn) as conn:
        conn.execute(BOOTSTRAP, prepare=False)
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(export_sql(), prepare=False)
    migrate(dsn)
    migrate(dsn)  # Must be repeatable without changing data/schema.
    yield dsn
    server.cleanup()


class FakeAuth:
    def __init__(self, dsn):
        self.dsn = dsn
        self.accounts = {}
        self.tokens = {}
        self.refreshes = {}
        self.calls = []
        self.confirmation_required = False

    def session(self, user):
        access = str(uuid4()) + str(uuid4())
        refresh = str(uuid4()) + str(uuid4())
        self.tokens[access] = user
        self.refreshes[refresh] = user
        return {
            "access_token": access,
            "refresh_token": refresh,
            "expires_in": 3600,
            "user": user,
        }

    def request(self, method, url, headers=None, json=None, **kwargs):
        self.calls.append((method, url, json))
        path = url.split("/auth/v1/")[-1]

        def respond(status, data):
            return httpx.Response(status, json=data)

        if path == "signup":
            if json["email"] in self.accounts:
                return respond(400, {})
            user = {
                "id": str(uuid4()),
                "email": json["email"],
                "user_metadata": json["data"],
            }
            with psycopg.connect(self.dsn) as conn:
                conn.execute(
                    "insert into auth.users(id,email,raw_user_meta_data) values(%s,%s,%s)",
                    (
                        user["id"],
                        user["email"],
                        __import__("json").dumps(user["user_metadata"]),
                    ),
                )
            self.accounts[user["email"]] = (json["password"], user)
            return respond(
                200,
                {"user": user} if self.confirmation_required else self.session(user),
            )
        if path == "token?grant_type=password":
            password, user = self.accounts.get(json["email"], (None, None))
            return (
                respond(200, self.session(user))
                if password == json["password"]
                else respond(400, {})
            )
        if path == "token?grant_type=refresh_token":
            user = self.refreshes.pop(json["refresh_token"], None)
            return respond(200, self.session(user)) if user else respond(400, {})
        raw = (headers or {}).get("Authorization", "").removeprefix("Bearer ")
        user = self.tokens.get(raw)
        if path == "user" and method == "GET":
            return respond(200, user) if user else respond(401, {})
        if path.startswith("logout"):
            if not user:
                return respond(401, {})
            self.tokens.pop(raw, None)
            self.refreshes = {
                k: v for k, v in self.refreshes.items() if v["id"] != user["id"]
            }
            return respond(200, {})
        if path == "user" and method == "PUT" and user:
            self.accounts[user["email"]] = (json["password"], user)
            return respond(200, user)
        if path.startswith("recover"):
            return respond(200, {})
        return respond(401, {})


@pytest.fixture
def client(postgres, monkeypatch):
    with psycopg.connect(postgres) as conn:
        tables = conn.execute(
            "select tablename from pg_tables where schemaname='public'"
        ).fetchall()
        names = ",".join('public."' + row[0] + '"' for row in tables)
        conn.execute(
            "truncate "
            + names
            + ", auth.users,private.convites,storage.objects cascade"
        )
    monkeypatch.setenv(
        "DATABASE_URL", postgres.replace("postgresql://", "postgresql+psycopg://", 1)
    )
    settings.cache_clear()
    if get_engine.cache_info().currsize:
        get_engine().dispose()
    get_engine.cache_clear()
    fake = FakeAuth(postgres)
    monkeypatch.setattr("app.auth.httpx.request", fake.request)
    with TestClient(app) as client:
        client.fake_auth = fake
        yield client
    get_engine().dispose()
    get_engine.cache_clear()
    settings.cache_clear()


def register(client, email, name="Rita", code=None):
    response = client.post(
        "/api/auth/register",
        json={
            "name": name,
            "email": email,
            "password": "strong-test-password",
            "family_name": "Rita & Jean",
            "invitation_code": code,
        },
    )
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    client.headers["Authorization"] = "Bearer " + token
    me = client.get("/api/me")
    assert me.status_code == 200, me.text
    return me.json(), token


@pytest.fixture
def household(client):
    rita, token = register(client, "rita@example.com")
    code = client.post("/api/members/invitations").json()["invitation_code"]
    jean, jean_token = register(client, "jean@example.com", "Jean", code)
    client.headers["Authorization"] = "Bearer " + token
    account = client.post(
        "/api/accounts", json={"name": "Conta conjunta", "initial_balance": "100.00"}
    ).json()
    categories = client.get("/api/categories").json()
    return {
        "rita": rita["id"],
        "jean": jean["id"],
        "token": token,
        "jean_token": jean_token,
        "family": rita["family_id"],
        "account": account["id"],
        "expense": next(c["id"] for c in categories if c["kind"] == "expense"),
        "income": next(c["id"] for c in categories if c["kind"] == "income"),
    }
