"""Idempotent owner-only role provisioning; never prints credentials or URLs."""

import os
from urllib.parse import unquote, urlsplit

import psycopg
from psycopg import sql

from supportdesk.config import get_settings


def main() -> None:
    runtime = urlsplit(
        os.environ["RUNTIME_DATABASE_URL"].replace(
            "postgresql+psycopg://", "postgresql://"
        )
    )
    role, password = unquote(runtime.username or ""), unquote(runtime.password or "")
    if role != "supportdesk_runtime" or len(password) < 24:
        raise RuntimeError(
            "A dedicated runtime role and a strong password are required"
        )
    owner_url = get_settings().database_url.replace(
        "postgresql+psycopg://", "postgresql://"
    )
    with psycopg.connect(owner_url) as connection:
        if not connection.execute(
            "SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)
        ).fetchone():
            connection.execute(
                sql.SQL(
                    "CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT"
                ).format(sql.Identifier(role))
            )
        connection.execute(
            sql.SQL(
                "ALTER ROLE {} WITH LOGIN NOSUPERUSER NOCREATEDB "
                "NOCREATEROLE NOINHERIT PASSWORD {}"
            ).format(sql.Identifier(role), sql.Literal(password))
        )
        connection.execute(
            "REVOKE CREATE ON SCHEMA public FROM PUBLIC, supportdesk_runtime"
        )
        connection.execute(
            "GRANT CONNECT ON DATABASE supportdesk TO supportdesk_runtime"
        )
        connection.execute("GRANT USAGE ON SCHEMA public TO supportdesk_runtime")
        connection.execute(
            "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES "
            "IN SCHEMA public TO supportdesk_runtime"
        )
        connection.execute(
            "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public "
            "TO supportdesk_runtime"
        )
        connection.execute(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT "
            "SELECT, INSERT, UPDATE, DELETE ON TABLES TO supportdesk_runtime"
        )
        connection.execute(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT "
            "USAGE, SELECT ON SEQUENCES TO supportdesk_runtime"
        )
        connection.execute(
            "REVOKE INSERT, UPDATE, DELETE ON alembic_version FROM supportdesk_runtime"
        )
    print("Restricted runtime role provisioned")


if __name__ == "__main__":
    main()
