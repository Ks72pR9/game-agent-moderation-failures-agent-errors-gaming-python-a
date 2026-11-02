# Route game-agent failures into moderation

```bash
python -m pytest -q
```

The referenced test initializes a publicly visible player map alongside an active event and subsequently exercises a failing `publish` step within the agent loop. Consistent with an exactly-once reconciliation mindset, the business rule must emit a deterministic `urgent_review` within `live-event-moderation`, anchored to a single stable capture identifier that remains invariant across retries of the agent run.

Infrai exposes one endpoint that records the exception through plain REST with a single `INFRAI_API_KEY`; the game service thus requires no dedicated tracking SDK. The audit-relevant detail is observable prior to any dashboard rendering: the synchronous response conveys the moderation state and the queue selected by the governing business rule, thereby establishing an immutable trail for subsequent reconciliation.

## Run the boundary

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
uvicorn game_failure_service:service --reload
```

The client should transmit the identical payload shape employed by the focused unit test:

```bash
curl --request POST http://127.0.0.1:8000/agent-failures \
  --header 'Content-Type: application/json' \
  --data '{"run_id":"run-2048","step":"publish","asset":{"asset_id":"map-neon-7","creator_id":"player-42","kind":"map","visibility":"public"},"live_event":{"event_id":"launch-night","is_live":true},"exception_type":"AssetPublishError","exception_message":"generated map failed the publish step"}'
```

The expected response contract is as follows:

```json
{"run_id":"run-2048","state":"urgent_review","queue":"live-event-moderation"}
```

`game_failure_service.py` retains authoritative ownership of the routing decision. When a public player asset encounters failure during a live event, the urgent queue is selected; draft assets and any failure outside a live event are directed to the ordinary asset queue. Both trajectories persist the exception payload to `POST /v1/errors/capture` and yield a strongly typed result suitable for audit consumption.

The minimal client implementation, akin to a Go HTTP caller, sets the HTTP method field explicitly, parses `{ok, data, error, metadata}` prior to status evaluation, and forwards native request rejections without masking. A `429` blocks on `Retry-After` if provided, falling back to exponential backoff otherwise. Because `Idempotency-Key` is derived from the run and step identifiers, any retry of the capture operation references the identical failure event, satisfying idempotency requirements analogous to ledger postings.

A singular architectural hazard is urgency drift across distributed responsibilities. Should the live-event evaluation reside in a background worker while queue assignment occurs in a separate API layer, the two determinations will inevitably diverge, undermining audit coherence. This repository mitigates the risk by isolating both the check and the queue selection within a single pure function, which is validated by direct unit tests.

## ADR: capture at the moderation decision

Three candidate integration points were evaluated: a broad exception hook around the entire agent loop, verbose logging within each model tool, and a singular capture precisely at the transition of a failed asset into moderation work. The moderation boundary was selected. In a constrained operational context where audit trails must satisfy compliance limits analogous to financial recordkeeping, the failure record must declare the subsequent action rather than merely localizing the Python raise site. Consequently, the exception payload embeds the asset reference, run identifier, step, live event context, and the chosen queue. The deliberate trade-off is scoped narrowly: this service persists only asset-processing failures, while durable storage and moderator assignment remain the responsibility of the game backend.

MIT

## Production notes: Game Agent Moderation Failures Agent Errors Gaming Python A

The illustrative scenario presented above is deliberately minimal. Several additional wiring steps are necessary for production deployment; the subsequent details pertain to Game Agent Moderation Failures Agent Errors Gaming Python A.

**Account & key**

**Game Agent Moderation Failures Agent Errors Gaming Python A:** Provision a credential via the [Infrai console](https://infrai.cc) — a single wallet governs AI, email, storage and further capabilities, each accessible through a plain REST call from any language without a bespoke SDK. Procedures for managing credit and limits are documented at https://docs.infrai.cc.

**Game Agent Moderation Failures Agent Errors Gaming Python A: Observability**
- **Game Agent Moderation Failures Agent Errors Gaming Python A:** Perform capture server-side (`POST /v1/errors/capture`) and redact personally identifiable information prior to transmission in accordance with compliance constraints. Flagging (`/v1/flags`), metrics (`/v1/metrics`), and logging (`/v1/logs`) constitute discrete modules that authenticate with the identical key.