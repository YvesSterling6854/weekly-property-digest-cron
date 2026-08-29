from datetime import date
from unittest.mock import Mock

from property_digest import (
    DigestRequest,
    InspectionReminder,
    MaintenanceRequest,
    TenantDocument,
    build_weekly_digest,
    schedule_weekly_digest,
)


def test_digest_keeps_only_actionable_items_in_the_weekly_window() -> None:
    request = DigestRequest(
        as_of=date(2026, 8, 10),
        maintenance=(
            MaintenanceRequest("mr-1", "Boiler pressure", "open"),
            MaintenanceRequest("mr-2", "Replace hallway lamp", "closed"),
        ),
        documents=(
            TenantDocument("doc-1", "Access consent", False),
            TenantDocument("doc-2", "Move-in inventory", True),
        ),
        inspections=(
            InspectionReminder("Cedar House", date(2026, 8, 17)),
            InspectionReminder("Lake Court", date(2026, 8, 18)),
        ),
    )

    digest = build_weekly_digest(request)

    assert [item.request_id for item in digest.open_maintenance] == ["mr-1"]
    assert [item.document_id for item in digest.pending_documents] == ["doc-1"]
    assert [item.property_name for item in digest.upcoming_inspections] == ["Cedar House"]


def test_schedule_uses_payload_specific_idempotency_keys() -> None:
    client = Mock()
    client.cron.create.return_value = {"job_id": "job-42"}

    schedule_weekly_digest("https://property.example/digest-a", client=client)
    schedule_weekly_digest("https://property.example/digest-b", client=client)
    schedule_weekly_digest("https://property.example/digest-a", client=client)

    keys = [call.kwargs["idempotency_key"] for call in client.cron.create.call_args_list]
    assert keys[0] != keys[1]
    assert keys[0] == keys[2]
