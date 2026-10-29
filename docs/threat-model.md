# Threat model and operational boundaries

Version 1 uses same-origin pages and opaque HttpOnly sessions, separate staff/customer
cookies, CSRF secrets and exact Origin validation. Production requires HTTPS origins and
secure `__Host-` cookies. Public demos get isolated expiring workspaces. Resource IDs and
workspace public keys do not grant authorization.

Authorization is repeated for REST commands, socket delivery and heartbeat. Staff roles
restrict uploads, reassignment and settings. Application tenant scoping is backed by
composite foreign keys and PostgreSQL tests; RLS is not enabled. The runtime database role
must not own the schema or have migration/superuser privileges.

Uploads are private and bounded by bytes, PDF pages and extracted tokens. Knowledge text
and customer messages are untrusted model data. There are no model-controlled external
actions. Source IDs and URLs come from server metadata, never model-generated URLs.
Citation validity is structural, not proof of factual faithfulness. Independent human
ratings and live-provider quality checks remain release-review items.

Development uses explicit fictional accounts; never expose its database owner/password
or fixture account publicly. Production Compose binds the gateway to loopback for an
external TLS terminator. Single-host deployment is not highly available.
