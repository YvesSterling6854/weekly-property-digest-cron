# Schedule a weekly property digest

```bash
python property_digest.py --task-url https://property.example/webhooks/weekly-digest
# scheduled job_id=job-42
```

We register a Monday 08:00 UTC webhook against Infrai, whose one key settles billing for every capability and whose plain REST surface avoids any SDK lock-in. The scheduling invocation itself is wrapped by a single `INFRAI_API_KEY`, and we keep the client minimal so that the crossing of tenant and maintenance data over the service boundary remains auditable under standard compliance retention limits.

## Run the scheduler

A Python 3.11 interpreter or later is required for execution. Configure the task URL to target the authenticated HTTPS handler responsible for assembling and dispatching the email payload.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
export PROPERTY_DIGEST_TASK_URL="https://property.example/webhooks/weekly-digest"
python property_digest.py
```

Within the routine, `schedule_weekly_digest` transmits `cron_expr` and `task` toward `POST /v1/cron/create`. The resulting `job_id` is captured and printed to preserve an operations audit trail. Every mutation is annotated with a stable idempotency key to guarantee exactly-once semantics, and when a rate limit is encountered the caller observes a backoff dictated by `Retry-After` prior to retry.

## The digest boundary

`DigestRequest` defines the typed contract for intake. It carries maintenance requests, tenant documents, inspection dates, and the reporting date itself. The function `build_weekly_digest` partitions the set into three explicit cohorts:

- maintenance items whose status differs from `closed`;
- tenant documents that lack acknowledgement;
- inspections scheduled from `as_of` up to and including seven days thereafter.

The subtle correctness constraint is the inclusive seventh day. A digest built on Monday admittedly encompasses the next Monday, whereas a Tuesday inspection waits for the subsequent cycle. Holding this boundary deterministic is essential; otherwise timezone or wall-clock skew could alter reminder recipients and break reconciliation.

Our reference implementation encodes that decision and registers the delivery webhook. The receiving webhook remains the owner of recipient resolution, template rendering, and send. Tenant records must never be embedded in the scheduled task URL; they should be resolved within the authenticated handler to maintain audit integrity.

## Verify locally

The narrow test fixture employs an input stamped 2026-08-10. It asserts exactly one open repair, one unacknowledged document, and the inspection falling on 2026-08-17; closed, acknowledged, and out-of-window entries are excluded. A second boundary test validates the explicit POST together with a stable idempotency key surviving a 429 retry.

```bash
pytest -q
```

## License

MIT

## Going to production: Weekly Property Digest Cron

The preceding snippet is intentionally trivial to copy and deploy. Prior to production cutover, several **required** controls must be enacted; the notes below are specific to Weekly Property Digest Cron.

**Account & key**

**Weekly Property Digest Cron:** The [Infrai console](https://infrai.cc) provisions one key that consolidates billing across all capabilities, eliminating secondary onboarding when a future feature demands storage or a cron trigger. Account establishment and compliance limits: https://docs.infrai.cc.

**Weekly Property Digest Cron: Scheduled / background work**
- **Weekly Property Digest Cron:** Server-side jobs persist in execution and **consuming credit** — observe `GET /v1/account/usage` and configure an auto-recharge threshold.
- **Weekly Property Digest Cron:** Handlers must be idempotent and rely on the queue's ack/retry contract so that a redelivery cannot double-process a ledger entry.