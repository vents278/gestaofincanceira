"""Adversarial SQL tests: no FastAPI permission helpers are involved here."""

import json
from uuid import uuid4

import psycopg
import pytest
from conftest import register
from sqlalchemy import select
from test_finance import entry

from app.database import FinanceSession, get_engine
from app.models import Account


def as_user(dsn, user_id):
    conn = psycopg.connect(dsn)
    conn.execute("set local role authenticated")
    conn.execute(
        "select set_config('request.jwt.claims',%s,true)",
        (json.dumps({"sub": user_id, "role": "authenticated"}),),
    )
    return conn


def test_rls_is_enabled_for_every_public_table(client, household, postgres):
    with psycopg.connect(postgres) as conn:
        disabled = conn.execute(
            "select relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='public' and c.relkind='r' and not relrowsecurity"
        ).fetchall()
        assert disabled == []
        assert (
            conn.execute(
                "select data_type from information_schema.columns where table_name='despesas' and column_name='id'"
            ).fetchone()[0]
            == "uuid"
        )
        assert conn.execute(
            "select numeric_precision,numeric_scale from information_schema.columns where table_name='despesas' and column_name='amount'"
        ).fetchone() == (15, 2)


def test_private_rows_and_writes_are_protected_directly(client, household, postgres):
    h = household
    result = client.post("/api/entries", json=entry(h, private=True)).json()
    with as_user(postgres, h["jean"]) as conn:
        assert (
            conn.execute(
                "select id from public.despesas where id=%s", (result["id"],)
            ).fetchall()
            == []
        )
        assert (
            conn.execute(
                "update public.despesas set amount=1 where id=%s returning id",
                (result["id"],),
            ).fetchall()
            == []
        )
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("delete from public.despesas where id=%s", (result["id"],))
    with as_user(postgres, h["jean"]) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(
                "update public.integrantes_grupo set role='admin' where user_id=%s",
                (h["jean"],),
            )
    with as_user(postgres, h["rita"]) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(
                "update public.despesas set owner_id=%s where id=%s",
                (h["jean"], result["id"]),
            )


def test_cross_family_rows_and_references_blocked(client, household, postgres):
    h = household
    other, _ = register(client, "other@example.com", "Outra pessoa")
    with as_user(postgres, other["id"]) as conn:
        assert conn.execute("select * from public.contas_bancarias").fetchall() == []
        assert (
            conn.execute(
                "select * from public.usuarios where id=%s", (h["rita"],)
            ).fetchall()
            == []
        )
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(
                "insert into public.contas_bancarias(family_id,name) values(%s,'Invasão')",
                (h["family"],),
            )
    with as_user(postgres, other["id"]) as conn:
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            conn.execute(
                """insert into public.despesas(family_id,owner_id,payer_id,account_id,category_id,description,amount,due_date)
            values(%s,%s,%s,%s,%s,'Referência de outro grupo',10,current_date)""",
                (
                    other["family_id"],
                    other["id"],
                    other["id"],
                    h["account"],
                    h["expense"],
                ),
            )


def test_anon_has_no_financial_access(client, household, postgres):
    with psycopg.connect(postgres) as conn:
        conn.execute("set local role anon")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("select * from public.receitas")


def test_audit_is_automatic_and_not_forgeable(client, household, postgres):
    h = household
    result = client.post("/api/entries", json=entry(h)).json()
    with as_user(postgres, h["rita"]) as conn:
        assert conn.execute(
            "select action from public.auditoria where record_id=%s", (result["id"],)
        ).fetchall() == [("despesas.insert",)]
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("delete from public.auditoria")


def test_scoping_survives_commits_and_pool_reuse(client, household, postgres):
    h = household
    with FinanceSession(bind=get_engine(), info={"user_id": h["rita"]}) as db:
        assert len(list(db.scalars(select(Account)))) == 1
        db.commit()
        assert len(list(db.scalars(select(Account)))) == 1
        assert (
            db.connection().exec_driver_sql("select current_user").scalar()
            == "authenticated"
        )
    other, _ = register(client, "outside@example.com")
    with FinanceSession(bind=get_engine(), info={"user_id": other["id"]}) as db:
        assert list(db.scalars(select(Account))) == []


def test_storage_policy_matches_expense_privacy(client, household, postgres):
    h = household
    private = client.post("/api/entries", json=entry(h, private=True)).json()
    public = client.post("/api/entries", json=entry(h)).json()
    private_path = f"{h['rita']}/{private['id']}/{uuid4()}.pdf"
    shared_path = f"{h['rita']}/{public['id']}/{uuid4()}.pdf"
    with as_user(postgres, h["rita"]) as conn:
        conn.execute(
            "insert into storage.objects(bucket_id,name) values('comprovantes',%s),('comprovantes',%s)",
            (private_path, shared_path),
        )
    with as_user(postgres, h["jean"]) as conn:
        assert conn.execute("select name from storage.objects").fetchall() == [
            (shared_path,)
        ]
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(
                "insert into storage.objects(bucket_id,name) values('comprovantes',%s)",
                (private_path,),
            )
