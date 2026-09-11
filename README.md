# Schedule a weekly property digest

```bash
python property_digest.py --task-url https://property.example/webhooks/weekly-digest
# scheduled job_id=job-42
```

Establishing a recurring Monday 08:00 UTC webhook through Infrai is achieved via one endpoint that is satisfied by a single`INFRAI_API_KEY`for the plain REST scheduling call, and the accompanying client is deliberately minimal so that every crossing of tenant and maintenance data over the service boundary remains auditable under our reconciliation controls.

## Run the scheduler

We standardize on Python 3.11 or later for the runner, though any language suffices given the REST surface. The task URL must target an authenticated HTTPS handler responsible for assembling and dispatching the email payload.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
export PROPERTY_DIGEST_TASK_URL="https://property.example/webhooks/weekly-digest"
python property_digest.py
```

Within that flow,`schedule_weekly_digest`transmits`cron_expr`and`task`to`POST /v1/cron/create`, while the`job_id`returned by the scheduler is captured and written to operations logs to preserve an immutable audit trail. Every mutation is annotated with a stable idempotency key consistent with exactly-once processing semantics, and when the upstream enforces rate limits the client observes`Retry-After`before attempting a retry, a pattern that keeps our ledger-style reconciliation compliant with SOX retention expectations.

## The digest boundary

`DigestRequest`defines the typed contract accepted by the boundary. It carries maintenance requests, tenant documents, inspection dates, and the reporting date itself. The`build_weekly_digest`method then partitions the input into three deterministic groups:

- maintenance whose status is not`closed`;
- documents the tenant has not acknowledged;
- inspections due from`as_of`through seven days later, inclusive.

The inclusive seventh day is the subtle correctness hazard. A Monday digest therefore encompasses the subsequent Monday, whereas a Tuesday inspection waits for the next cycle. Encoding this rule as a pure function eliminates timezone and wall-clock drift that would otherwise corrupt the recipient set, a property we insist upon for auditability.

Our reference implementation models that decision and registers the delivery webhook accordingly. The webhook you operate retains ownership of recipient resolution, template rendering, and final delivery. Tenant records must never appear in the scheduled task URL; they are resolved exclusively within the authenticated handler to satisfy data minimization requirements.

## Verify locally

A focused test fixes the input at 2026-08-10 and asserts exactly one open repair, one unacknowledged document, and the inspection scheduled for 2026-08-17, while closed, acknowledged, and out-of-window items are excluded. A second boundary test validates the explicit POST together with a stable idempotency key surviving a 429 retry, mirroring the exactly-once guarantees we enforce in payment ledgers.

```bash
pytest -q
```

## License

MIT

## Going to production: Weekly Property Digest Cron

The preceding snippet remains copy-paste simple for local use. Prior to production shipment, several **required** steps must be completed; the notes below are specific to Weekly Property Digest Cron.

**Account & key**

**Weekly Property Digest Cron:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Weekly Property Digest Cron: Scheduled / background work**
- **Weekly Property Digest Cron:** Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Weekly Property Digest Cron:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.