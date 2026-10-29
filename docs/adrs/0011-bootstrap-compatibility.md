# ADR 0011: Bootstrap compatibility and development boundaries

Status: accepted during M0 implementation.

Python 3.13.14, Node 24.18.1, uv 0.12.1 and pnpm 11.20.0 were available.
The resolver selected SQLAlchemy 2.1.6 and Celery 5.6.3 without downgrading the specification.
SQLAlchemy 2.1 requires the explicit `asyncio` extra for greenlet; the initial migration exposed this and the dependency was corrected.
Redis client 6.4.0 is selected by Celery's compatible dependency range; the Redis server is 8.0.2.
All exact Python and JavaScript transitive resolutions are in their lockfiles.

Login admission conservatively counts all attempts, including successful attempts, against the five-per-minute account/IP limit. This bounds password hashing work as well as failed authentication. Revisit if legitimate rapid relogin is needed.

The local HTTP profile uses `sd_staff` / `sd_visitor`; secure mode uses `__Host-` names. Production configuration rejects HTTP origins and development secrets.
The `/public/demo` operation creates both scoped audiences in an isolated expiring workspace. No public visitor is granted access to seeded staff accounts.

Development Compose uses an isolated project and loopback ports. Its database owner is for local development/migrations only. A restricted production database role is still required by M5.

The host exposes an empty read-only `.git` mount. Lockfiles can be written but cannot be committed here; contract drift checks compare hashes and do not depend on Git availability.
