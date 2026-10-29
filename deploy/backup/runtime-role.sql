-- Run as migration owner after migrations. Set the password using a secret manager.
-- Replace the placeholder with a deployment-specific role, never a superuser.
CREATE ROLE supportdesk_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
GRANT CONNECT ON DATABASE supportdesk TO supportdesk_runtime;
GRANT USAGE ON SCHEMA public TO supportdesk_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO supportdesk_runtime;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO supportdesk_runtime;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO supportdesk_runtime;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO supportdesk_runtime;
REVOKE INSERT, UPDATE, DELETE ON alembic_version FROM supportdesk_runtime;
