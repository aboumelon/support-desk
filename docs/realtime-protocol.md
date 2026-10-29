# Realtime protocol v1

Customer socket: `/api/v1/realtime/customer`. Staff socket:
`/api/v1/realtime/staff?workspace_id=<uuid>`. Cookies and exact Origin are required.
Send `{"protocol_version":1,"type":"subscribe","conversation_id":"<uuid>","after_seq":0}`.
Only subscriptions, ping/pong and throttled typing hints are accepted; durable writes use REST.

Generated frame schemas live under `contracts/` and `packages/api-client/src/generated/`.
PostgreSQL sequences order events. Redis notifications wake authorized DB replay; they
are never the durable event authority. Every 15 seconds the socket revalidates access
and checks committed watermarks, including when no later notification arrives.

A single sender serializes frames. Buffers are limited to 256 frames / 1 MiB; slow
consumers disconnect and resume by cursor. Gaps or retained-event loss require reset.
The client deduplicates sequence numbers, invalidates canonical queries, and reconnects
with bounded exponential jitter. REST polling remains available during socket outages.

`ai.delta` contains run ID, epoch, attempt and chunk index. It is provisional and never
replayed. A reconnect, gap, epoch change or terminal run discards the draft. Only a
committed message is final. Typing expires after five seconds. Presence uses per-connection
Redis TTLs; ownership changes require explicit versioned REST commands.
