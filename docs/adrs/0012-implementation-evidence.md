# ADR 0012: Explicit fixture and evidence boundaries

Status: accepted during implementation.

The default assistant is a deterministic excerpt provider with explicit supported
fixture topics and failure scripts. Its UI identifies fixture mode. The configurable
live adapter remains opt-in and unverified until credentials and a budget are supplied.
No automatic fallback from a failed live request to fixture answers is permitted.

Unknown provider token usage stays charged at the reserved per-attempt allowance.
The full reservation covers three attempts. The generic compatible adapter bounds
input conservatively using UTF-8 bytes because provider-specific tokenizers differ.
This may hand off earlier than a provider-native tokenizer would require.

The first evaluation exposed poor missing-knowledge handoff from cosine thresholds
alone. Preserve the baseline and distinguish scripted fixture coverage from live-model
quality. The original cases were inspected, so a fresh blind evaluation remains needed.

Migration 0006 adds the cyclic active-version foreign key; migration 0007 adds the
assistant ledgers after model-discovery verification caught missing tables. Incremental
migrations were retained so an existing local installation can upgrade without data loss.

Manual job retry is restricted to ingestion. A failed/superseded AI run has already
handed off or lost its control epoch; restarting that same run would violate the
publication fence. An operator must explicitly return control to the assistant and a
new customer turn creates a new run/attempt budget. The generic job-retry route rejects
AI jobs instead of reviving an obsolete epoch.

The first full load run failed its targets. It exposed workspace-wide wake-up fanout,
a one-record/250ms dispatch bottleneck and nested connection acquisition for message
rate limiting. Notifications now wake only matching subscriptions, dispatch claims run
in batches and message quotas participate in the existing transaction. A short recheck
removed send errors; polling was then reduced to 250ms before the full rerun.

Retention removes 90-day messages/citations/audit rows, 30-day event/command records,
seven-day published outbox rows and unreferenced terminal ingestion jobs after 30 days.
Minimal AI job identity rows remain while retained runs reference them; deleting those
rows at 30 days would break the run's job foreign key. This is an explicit tombstone
retention exception, not a claim that all job metadata is purged at 30 days. Withdrawn
chunks are purged after 30 days, nullable historical chunk links are cleared, and source
version/locator tombstones remain without restoring withdrawn-source access.
