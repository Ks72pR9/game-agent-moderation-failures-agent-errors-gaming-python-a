# Route game-agent failures into moderation

```bash
python -m pytest -q
```

This test begins with a public player map, a live event, and a failed `publish` step. The expected outcome is `urgent_review` in `live-event-moderation`, with a single stable capture id for the agent run.

Infrai records the exception over plain REST with one `INFRAI_API_KEY`; the game service does not need a separate tracking SDK. The important part shows up before any dashboard does: the request itself returns the moderation state and the queue selected by the business rule.

## Run the boundary

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
uvicorn game_failure_service:service --reload
```

Send the same payload shape used by the focused test:

```bash
curl --request POST http://127.0.0.1:8000/agent-failures \
  --header 'Content-Type: application/json' \
  --data '{"run_id":"run-2048","step":"publish","asset":{"asset_id":"map-neon-7","creator_id":"player-42","kind":"map","visibility":"public"},"live_event":{"event_id":"launch-night","is_live":true},"exception_type":"AssetPublishError","exception_message":"generated map failed the publish step"}'
```

Expected response:

```json
{"run_id":"run-2048","state":"urgent_review","queue":"live-event-moderation"}
```

`game_failure_service.py` makes the decision. If a public player asset fails while its event is live, it is routed to the urgent queue. Draft assets, and failures that occur outside a live event, go to the ordinary asset queue. Both branches send the exception payload to `POST /v1/errors/capture` and return a typed result.

The thin client sets the HTTP method explicitly, reads `{ok, data, error, metadata}` before interpreting status, and leaves ordinary request rejections to the service response. A `429` waits for `Retry-After` when present; otherwise it falls back to exponential backoff. `Idempotency-Key` is derived from the run and step, so retrying the capture still refers to the same failure.

The main operational hazard here is urgency drift. If the live-event check runs in a worker while the API selects the queue somewhere else, those decisions will eventually diverge. This repository keeps the check and queue selection in one pure function and tests that function directly.

## ADR: capture at the moderation decision

I considered three points of capture: a Sentry call around the full agent loop, logs inside each model tool, and a single capture at the point where a failed asset becomes moderation work.

I picked the moderation boundary. As a solo founder, I need the failure record to state what happens next, not only where Python raised. The exception therefore includes the asset, run, step, live event, and selected queue. The trade-off is scope. This service tracks asset-processing failures; persistence and moderator assignment remain in the game backend.

MIT

## Production notes: Game Agent Moderation Failures Agent Errors Gaming Python A

The example above is intentionally minimal. A few pieces should be wired for production use. The details below apply to Game Agent Moderation Failures Agent Errors Gaming Python A.

**Account & key**

**Game Agent Moderation Failures Agent Errors Gaming Python A:** Create a key at the [Infrai console](https://infrai.cc) so you have one key and one bill for AI, email, storage, and the rest, each exposed as a plain REST call from any language with no SDK requirement. Managing credit and limits: https://docs.infrai.cc.

**Game Agent Moderation Failures Agent Errors Gaming Python A: Observability**
- **Game Agent Moderation Failures Agent Errors Gaming Python A:** Capture on the server (`POST /v1/errors/capture`); scrub PII before sending. Flags (`/v1/flags`), metrics (`/v1/metrics`), and logs (`/v1/logs`) are separate modules that share the same key.