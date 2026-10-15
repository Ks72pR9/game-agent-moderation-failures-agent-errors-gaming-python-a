from game_failure_service import AgentFailureRequest, record_failure


class RecordingErrors:
    def __init__(self) -> None:
        self.exception: dict[str, object] | None = None
        self.event_id = ""

    def capture(self, exception: dict[str, object], event_id: str) -> dict[str, object]:
        self.exception = exception
        self.event_id = event_id
        return {"event_id": "captured-test-event"}


def test_public_asset_failure_during_live_event_gets_urgent_review() -> None:
    errors = RecordingErrors()
    request = AgentFailureRequest.model_validate(
        {
            "run_id": "run-2048",
            "step": "publish",
            "asset": {
                "asset_id": "map-neon-7",
                "creator_id": "player-42",
                "kind": "map",
                "visibility": "public",
            },
            "live_event": {"event_id": "launch-night", "is_live": True},
            "exception_type": "AssetPublishError",
            "exception_message": "generated map failed the publish step",
        }
    )

    result = record_failure(request, errors)

    assert result.model_dump() == {
        "run_id": "run-2048",
        "state": "urgent_review",
        "queue": "live-event-moderation",
    }
    assert errors.event_id == "game-agent-failure:run-2048:publish"
    assert errors.exception is not None
    assert errors.exception["moderation_queue"] == "live-event-moderation"
    assert errors.exception["asset_id"] == "map-neon-7"
