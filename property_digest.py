"""Select property events for a weekly digest and register its schedule."""

from __future__ import annotations

import argparse
import hashlib
import os
from dataclasses import dataclass
from datetime import date, timedelta

from infrai_client import InfraiClient


@dataclass(frozen=True)
class MaintenanceRequest:
    request_id: str
    summary: str
    status: str


@dataclass(frozen=True)
class TenantDocument:
    document_id: str
    title: str
    acknowledged: bool


@dataclass(frozen=True)
class InspectionReminder:
    property_name: str
    due_on: date


@dataclass(frozen=True)
class DigestRequest:
    as_of: date
    maintenance: tuple[MaintenanceRequest, ...]
    documents: tuple[TenantDocument, ...]
    inspections: tuple[InspectionReminder, ...]


@dataclass(frozen=True)
class WeeklyDigest:
    open_maintenance: tuple[MaintenanceRequest, ...]
    pending_documents: tuple[TenantDocument, ...]
    upcoming_inspections: tuple[InspectionReminder, ...]


def build_weekly_digest(request: DigestRequest) -> WeeklyDigest:
    window_end = request.as_of + timedelta(days=7)
    return WeeklyDigest(
        open_maintenance=tuple(item for item in request.maintenance if item.status != "closed"),
        pending_documents=tuple(item for item in request.documents if not item.acknowledged),
        upcoming_inspections=tuple(
            item for item in request.inspections if request.as_of <= item.due_on <= window_end
        ),
    )


def schedule_weekly_digest(task_url: str, *, client: InfraiClient | None = None) -> str:
    infrai = client or InfraiClient()
    cron_expr = "0 8 * * 1"
    payload_fingerprint = hashlib.sha256(f"{cron_expr}\0{task_url}".encode()).hexdigest()
    result = infrai.cron.create(
        cron_expr=cron_expr,
        task=task_url,
        idempotency_key=f"property-digest-{payload_fingerprint}",
    )
    return str(result["job_id"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Register the weekly property digest webhook")
    parser.add_argument("--task-url", default=os.environ.get("PROPERTY_DIGEST_TASK_URL"))
    args = parser.parse_args()
    if not args.task_url:
        parser.error("set PROPERTY_DIGEST_TASK_URL or pass --task-url")
    print(f"scheduled job_id={schedule_weekly_digest(args.task_url)}")


if __name__ == "__main__":
    main()
