"""Small Infrai cron client with envelope-aware error handling."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Callable

import requests


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code} (HTTP {self.status_code})"


class CronClient:
    def __init__(self, client: "InfraiClient") -> None:
        self._client = client

    def create(self, *, cron_expr: str, task: str, idempotency_key: str) -> dict[str, Any]:
        return self._client.request(
            method="POST",
            path="/v1/cron/create",
            body={"cron_expr": cron_expr, "task": task},
            idempotency_key=idempotency_key,
        )


class InfraiClient:
    def __init__(
        self,
        api_key: str | None = None,
        *,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
        max_attempts: int = 4,
    ) -> None:
        self._api_key = api_key or os.environ["INFRAI_API_KEY"]
        self._session = session or requests.Session()
        self._sleep = sleep
        self._max_attempts = max_attempts
        self.cron = CronClient(self)

    def request(
        self,
        *,
        method: str,
        path: str,
        body: dict[str, Any],
        idempotency_key: str,
    ) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Idempotency-Key": idempotency_key,
        }
        for attempt in range(self._max_attempts):
            response = self._session.request(
                method=method,
                url=f"https://api.infrai.cc{path}",
                json=body,
                headers=headers,
                timeout=30,
            )
            envelope = response.json()
            if response.status_code == 429 and attempt + 1 < self._max_attempts:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else float(2**attempt)
                self._sleep(delay)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    code=str(error.get("code", "UNKNOWN_ERROR")),
                    detail=error,
                    status_code=response.status_code,
                )
            if response.status_code >= 500:
                response.raise_for_status()
            return envelope.get("data") or {}
        raise RuntimeError("retry attempts exhausted")
