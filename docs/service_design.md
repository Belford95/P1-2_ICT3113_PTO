# Service Design (Assignment 1 baseline)

## Components
```
 Load generator (separate machine)        System Under Test (Docker, one machine)
 ┌──────────────────┐   HTTP :8000   ┌───────────────────────┐  HTTP /api/chat  ┌──────────────────┐
 │  Apache JMeter   │ ─────────────► │  Triage Service       │ ───────────────► │  Ollama (CPU)    │
 │                  │ ◄───────────── │  FastAPI, 1 worker    │ ◄─────────────── │  1 request at a  │
 └──────────────────┘    category    └───┬───────────┬───────┘     category     │  time            │
                                         ▼           ▼                          └──────────────────┘
                                  ┌──────────┐  ┌──────────────────┐
                                  │ SQLite   │  │ logs/service.jsonl│
                                  └──────────┘  └──────────────────┘
```

## Endpoints
| Endpoint | What it does |
|---|---|
| `POST /tickets` | Body `{"narrative": str, "source_row": int (optional)}`. Asks Ollama for a category, **waits** for the answer, stores the ticket, returns `{id, category, model}` |
| `GET /search?q=<text>&limit=20` | Returns stored tickets whose narrative contains the text, newest first |
| `GET /stats` | Returns ticket counts per category |
| `GET /health` | Helper: service status and the model in use |
| `DELETE /tickets` | Helper: empties the store, so every test run starts from an empty service |

## Design decisions
| Area | Decision | Reason |
|---|---|---|
| Framework | FastAPI + uvicorn, **1 worker process** | Simple, and auto-generates API docs at `/docs`. One worker keeps the baseline unoptimised |
| Storage | SQLite file in a Docker volume, new connection per request | The brief only needs "storage"; a database server adds nothing for the baseline |
| Search | Plain substring match (`LIKE '%q%'`); every search scans the whole table, with no index | Deliberately naive (brief: "do not pre-optimise"). A candidate for Assignment 2 |
| Classification | **Synchronous**: `POST /tickets` does not return until Ollama answers. No caching, no queue in the service, no batching, no retries | Required by the brief for the baseline |
| Ollama concurrency | `OLLAMA_NUM_PARALLEL=1`: Ollama runs one inference at a time; further requests wait in Ollama's own queue (max 512, then HTTP 503) | Predictable, explainable behaviour for the baseline |
| Prompt | Zero-shot: the prompt lists the 7 category names only. No definitions, no examples, no training | The models are pre-trained. The golden set is only used for scoring |
| Valid answers | Ollama structured output (a JSON schema listing the 7 categories), so the model can only answer with one of the 7 names | Gives every reply a scorable category |
| Model settings | temperature 0, seed 42, context window 2048 tokens, 600 s timeout to Ollama | The same ticket gets the same answer, and the longest narratives (~2,000 chars) fit |
| Model choice | One candidate at a time, set by `MODEL` in `.env` (see `models.md`) | Each candidate is measured in isolation |
| GPU | None passed into the container, so it's CPU only | Client constraint |

## Error behaviour
| Situation | Response |
|---|---|
| Ollama unreachable, errors, or times out | HTTP **502**, logged with the error message |
| Model reply cannot be matched to a category | Stored and returned as **`Unclassified`** (HTTP 200); counts as wrong in accuracy scoring |
| Missing/empty `narrative` | HTTP 422 (validation error) |

## Request logging
Every request, on every endpoint, is appended as **one JSON line** to `logs/service.jsonl` (mounted from the repo folder).

| Field | Meaning |
|---|---|
| `ts`, `start_epoch_ms` | when the request arrived |
| `run_id` | from the `X-Run-Id` request header, so log lines can be matched to a test run |
| `method`, `path`, `query`, `status` | the request and its outcome |
| `latency_ms` | total time inside the service |
| `model`, `category`, `raw_output` | what classified the ticket and what it answered (POST only) |
| `source_row`, `narrative_chars` | dataset row number and ticket length (POST only) |
| `model_ms` | time the service waited for Ollama |
| `ollama.*` | Ollama's own timing: model load, prompt processing (tokens and ms), answer generation (tokens and ms) |
| `error` | the failure reason, when the request failed |
