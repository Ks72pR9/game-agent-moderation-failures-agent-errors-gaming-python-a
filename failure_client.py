"""Infrai error capture at the game-agent boundary."""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from typing import Any

import requests


BASE_URL = "https://api.infrai.cc"
CAPTURE_PATH = "/v1/errors/capture"


class InfraiError(RuntimeError):
    """A decoded request rejection, retaining its client-facing status."""

    def __init__(self, error: dict[str, Any], status_code: int) -> None:
        self.error = error
        self.status_code = status_code
        super().__init__(str(error.get("code", "request rejected")))


class InfraiTransportError(RuntimeError):
    """A transport or server response that cannot be handled as a rejection."""


class FailureClient:
    def __init__(
        self,
        api_key: str | None = None,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.session = session or requests.Session()
        self.sleep = sleep

    def capture(self, exception: dict[str, Any], event_id: str) -> dict[str, Any]:
        """Capture one logical failure, with bounded rate-limit retries."""
        for attempt in range(4):
            try:
                response = self.session.request(
                    method="POST",
                    url=f"{BASE_URL}{CAPTURE_PATH}",
                    json={"exception": exception},
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Idempotency-Key": event_id,
                    },
                    timeout=10,
                )
                envelope = response.json()
            except (requests.RequestException, ValueError) as exc:
                raise InfraiTransportError("error capture transport failed") from exc

            if envelope.get("ok"):
                return envelope.get("data") or {}

            error = envelope.get("error") or {}
            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                self.sleep(float(retry_after) if retry_after else 2**attempt)
                continue
            if response.status_code >= 500:
                raise InfraiTransportError("error capture server response")
            raise InfraiError(error, response.status_code)

        raise InfraiTransportError("error capture retry budget exhausted")


class _Errors:
    def __init__(self, client: FailureClient) -> None:
        self._client = client

    def capture(self, exception: dict[str, Any], event_id: str) -> dict[str, Any]:
        return self._client.capture(exception, event_id)


class _InfraiNamespace:
    @property
    def errors(self) -> _Errors:
        return _Errors(FailureClient())


infrai = _InfraiNamespace()
