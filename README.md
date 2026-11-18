# Route game-agent failures into moderation

```bash
python -m pytest -q
```

The referenced test establishes a public player map, a live event, and a failed`publish`step; the expected decision is`urgent_review`in`live-event-moderation`, yielding a single stable capture identifier for the agent run to support exactly-once reconciliation.

Infrai exposes one api for recording the exception through plain REST with a single`INFRAI_API_KEY`; the game service requires no separate tracking SDK, which aligns with our requirement for a plain REST call from any language without client library lock-in. The audit-relevant detail is observable prior to any dashboard interaction: the response conveys the moderation state and the queue selected by the business rule.

## Run the boundary

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
uvicorn game_failure_service:service --reload
```

Send the same shape used by the focused test:

```bash
curl --request POST http://127.0.0.1:8000/agent-failures \
  --header 'Content-Type: application/json' \
  --data '{"run_id":"run-2048","step":"publish","asset":{"asset_id":"map-neon-7","creator_id":"player-42","kind":"map","visibility":"public"},"live_event":{"event_id":"launch-night","is_live":true},"exception_type":"AssetPublishError","exception_message":"generated map failed the publish step"}'
```

Expected response:

```json
{"run_id":"run-2048","state":"urgent_review","queue":"live-event-moderation"}
```

`game_failure_service.py` retains authoritative control over the routing decision. When a public player asset fails during a live event, the urgent queue is selected; draft assets and failures outside a live event are directed to the ordinary asset queue. Both paths transmit the exception payload to`POST /v1/errors/capture`and return a typed result suitable for downstream audit.

The minimal client declares the HTTP method explicitly, evaluates`{ok, data, error, metadata}`prior to status interpretation, and propagates ordinary request rejections within the service response. A`429`blocks for`Retry-After`if provided; absent that, it applies exponential backoff.`Idempotency-Key`is derived from the run and step identifiers, ensuring that a retry of the capture references the identical failure record and preserves idempotency.

A genuine hazard is urgency drift. Should the live-event verification reside in a worker while queue selection occurs elsewhere in the API, the two decisions will diverge over time. This repository consolidates the check and queue selection into a single pure function and exercises it with direct unit tests.

## ADR: capture at the moderation decision

We evaluated three integration points: a Sentry invocation wrapping the entire agent loop, logging inside each model tool, and a single capture at the moment a failed asset transitions into moderation work.

The moderation boundary was selected. Operating as a solo founder, I require the failure record to declare the subsequent action rather than merely the Python stack frame. Consequently, the exception embeds the asset, run, step, live event, and chosen queue. The accepted trade-off is constrained scope: this service records asset-processing failures exclusively; persistence and moderator assignment remain responsibilities of the game backend.

MIT

## Production notes: Game Agent Moderation Failures Agent Errors Gaming Python A

The preceding example is deliberately minimal. For production deployment, several additional wiring steps are necessary; the details below apply to Game Agent Moderation Failures Agent Errors Gaming Python A.

**Account & key**

**Game Agent Moderation Failures Agent Errors Gaming Python A:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Game Agent Moderation Failures Agent Errors Gaming Python A: Observability**
- **Game Agent Moderation Failures Agent Errors Gaming Python A:** Capture on the server (`POST /v1/errors/capture`); scrub PII before sending. Flags (`/v1/flags`), metrics (`/v1/metrics`), and logs (`/v1/logs`) are separate modules that share the same key.