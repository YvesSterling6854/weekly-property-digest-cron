from infrai_client import InfraiClient


class FakeResponse:
    def __init__(self, status_code, body, headers=None):
        self.status_code = status_code
        self._body = body
        self.headers = headers or {}

    def json(self):
        return self._body

    def raise_for_status(self):
        raise AssertionError("unexpected transport failure")


class FakeSession:
    def __init__(self):
        self.responses = [
            FakeResponse(429, {"ok": False, "data": None, "error": {"code": "RATE_LIMITED"}, "metadata": {}}, {"Retry-After": "2"}),
            FakeResponse(200, {"ok": True, "data": {"job_id": "job-42"}, "error": None, "metadata": {}}),
        ]
        self.calls = []

    def request(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


def test_create_retries_with_the_same_idempotency_key() -> None:
    session = FakeSession()
    delays = []
    client = InfraiClient(api_key="test-key", session=session, sleep=delays.append)

    result = client.cron.create(
        cron_expr="0 8 * * 1",
        task="https://property.example/digest",
        idempotency_key="weekly-v1",
    )

    assert result == {"job_id": "job-42"}
    assert delays == [2.0]
    assert [call["method"] for call in session.calls] == ["POST", "POST"]
    assert {call["headers"]["Idempotency-Key"] for call in session.calls} == {"weekly-v1"}
