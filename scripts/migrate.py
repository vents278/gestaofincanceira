"""Apply immutable SQL migrations with checksum tracking, using an admin DSN."""

import hashlib
import os
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]


def migrate(dsn):
    if not dsn.startswith(("postgresql://", "postgresql+psycopg://")):
        raise RuntimeError("Migrações exigem PostgreSQL; não há fallback SQLite")
    with psycopg.connect(
        dsn.replace("postgresql+psycopg://", "postgresql://", 1)
    ) as conn:
        conn.execute("select pg_advisory_lock(71602412)")
        conn.execute("create schema if not exists private")
        conn.execute(
            "create table if not exists private.schema_migrations (name text primary key, checksum text not null, applied_at timestamptz default now())"
        )
        conn.commit()
        for path in sorted((ROOT / "supabase/migrations").glob("*.sql")):
            checksum = hashlib.sha256(path.read_bytes()).hexdigest()
            row = conn.execute(
                "select checksum from private.schema_migrations where name=%s",
                (path.name,),
            ).fetchone()
            if row:
                if row[0] != checksum:
                    raise RuntimeError(
                        "Migração já aplicada foi alterada: " + path.name
                    )
                conn.commit()
                continue
            with conn.transaction():
                conn.execute(path.read_text(), prepare=False)
                conn.execute(
                    "insert into private.schema_migrations(name,checksum) values(%s,%s)",
                    (path.name, checksum),
                )
            conn.commit()
            print("Aplicada:", path.name)
        conn.execute("select pg_advisory_unlock(71602412)")
        conn.commit()


def export_sql():
    """Identical migrations packaged for SQL Editor, with checksum bookkeeping."""
    chunks = [
        "create schema if not exists private;",
        "create table if not exists private.schema_migrations (name text primary key, checksum text not null, applied_at timestamptz default now());",
    ]
    for path in sorted((ROOT / "supabase/migrations").glob("*.sql")):
        checksum = hashlib.sha256(path.read_bytes()).hexdigest()
        chunks.append(f"""begin;
select pg_advisory_xact_lock(71602412);
DO $migration$
begin
 if exists(select 1 from private.schema_migrations where name='{path.name}' and checksum<>'{checksum}') then
  raise exception 'Checksum divergente: {path.name}';
 end if;
 if not exists(select 1 from private.schema_migrations where name='{path.name}') then
 {path.read_text()}
 insert into private.schema_migrations(name,checksum) values('{path.name}','{checksum}');
 end if;
end $migration$;
commit;""")
    return "\n".join(chunks)


if __name__ == "__main__":
    import sys

    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")

    if "--sql" in sys.argv:
        print(export_sql())
    else:
        migrate(os.environ["DATABASE_URL"])
