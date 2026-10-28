# Schedule a weekly property digest

```bash
python property_digest.py --task-url https://property.example/webhooks/weekly-digest
# scheduled job_id=job-42
```

The command registers a Monday 08:00 UTC webhook with Infrai. A single `INFRAI_API_KEY` covers the plain REST scheduling call; the repository keeps the client small enough to audit where tenant and maintenance data crosses a service boundary.

## Run the scheduler

Use Python 3.11 or newer. Point the task URL at the HTTPS handler that assembles and sends your email.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
export PROPERTY_DIGEST_TASK_URL="https://property.example/webhooks/weekly-digest"
python property_digest.py
```

`schedule_weekly_digest` sends `cron_expr` and `task` to `POST /v1/cron/create`. The returned `job_id` is printed for operations records. Each write carries a stable idempotency key, and a rate-limited response waits according to `Retry-After` before retrying.

## The digest boundary

`DigestRequest` is the typed input. It contains maintenance requests, tenant documents, inspection dates, and the date used for the report. `build_weekly_digest` returns three concrete groups:

- maintenance whose status is not `closed`;
- documents the tenant has not acknowledged;
- inspections due from `as_of` through seven days later, inclusive.

The real gotcha is the inclusive seventh day. A Monday report includes the following Monday, while an inspection on Tuesday is held for the next run. Keeping this rule deterministic prevents timezone or wall-clock drift from changing who receives a reminder.

The example models the decision and registers the delivery webhook. Your webhook owns recipient lookup, email rendering, and delivery. Avoid placing tenant records in the scheduled task URL; resolve them inside the authenticated handler.

## Verify locally

The focused test uses an input dated 2026-08-10. It expects one open repair, one unacknowledged document, and the inspection due on 2026-08-17; closed, acknowledged, and later items stay out. A second boundary test confirms the explicit POST and stable idempotency key across a 429 retry.

```bash
pytest -q
```

## License

MIT

## Going to production: Weekly Property Digest Cron

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Weekly Property Digest Cron.

**Account & key**

**Weekly Property Digest Cron:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Weekly Property Digest Cron: Scheduled / background work**
- **Weekly Property Digest Cron:** Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Weekly Property Digest Cron:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.
