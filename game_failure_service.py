"""Typed service for failures in a game backend agent loop."""

from __future__ import annotations

from typing import Literal, Protocol

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from failure_client import InfraiError, InfraiTransportError, infrai


class PlayerAsset(BaseModel):
    asset_id: str = Field(min_length=1, max_length=80)
    creator_id: str = Field(min_length=1, max_length=80)
    kind: Literal["avatar", "map", "voice-line"]
    visibility: Literal["draft", "public"]


class LiveEvent(BaseModel):
    event_id: str = Field(min_length=1, max_length=80)
    is_live: bool


class AgentFailureRequest(BaseModel):
    run_id: str = Field(min_length=1, max_length=80)
    step: Literal["generate", "scan", "publish"]
    asset: PlayerAsset
    live_event: LiveEvent | None = None
    exception_type: str = Field(min_length=1, max_length=80)
    exception_message: str = Field(min_length=1, max_length=300)


class FailureDecision(BaseModel):
    run_id: str
    state: Literal["queued", "urgent_review"]
    queue: Literal["asset-moderation", "live-event-moderation"]


class ErrorCapture(Protocol):
    def capture(self, exception: dict[str, object], event_id: str) -> dict[str, object]:
        raise NotImplementedError


def record_failure(
    request: AgentFailureRequest, errors: ErrorCapture | None = None
) -> FailureDecision:
    """Make the moderation decision, then record the same logical failure once."""
    urgent = bool(request.asset.visibility == "public" and request.live_event and request.live_event.is_live)
    decision = FailureDecision(
        run_id=request.run_id,
        state="urgent_review" if urgent else "queued",
        queue="live-event-moderation" if urgent else "asset-moderation",
    )
    capture = errors.capture if errors is not None else infrai.errors.capture
    capture(
        exception={
            "type": request.exception_type,
            "message": request.exception_message,
            "agent": "game-asset-agent",
            "step": request.step,
            "run_id": request.run_id,
            "asset_id": request.asset.asset_id,
            "asset_kind": request.asset.kind,
            "creator_id": request.asset.creator_id,
            "moderation_state": decision.state,
            "moderation_queue": decision.queue,
            "live_event_id": request.live_event.event_id if request.live_event else None,
        },
        event_id=f"game-agent-failure:{request.run_id}:{request.step}",
    )
    return decision


service = FastAPI(title="Game Agent Failure Service")


@service.post("/agent-failures", response_model=FailureDecision)
def capture_agent_failure(request: AgentFailureRequest) -> FailureDecision:
    try:
        return record_failure(request)
    except InfraiError as exc:
        status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=status, detail=exc.error) from exc
    except InfraiTransportError as exc:
        raise HTTPException(status_code=502, detail="error capture transport failed") from exc
