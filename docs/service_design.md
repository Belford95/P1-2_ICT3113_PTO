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

---

# Assignment 2: cascade mode

`POST /tickets` can now run either a single model (Assignment 1 behaviour) or the cascade of
`docs/escalation_rule.md`. Everything else is unchanged: same endpoints, same prompt, same seven
categories, same storage, same logging, still synchronous with no caching, queueing or retries.

## Configuration (environment only, no code change between runs)

| Variable | Single mode | Cascade mode |
|---|---|---|
| `MODE` | `single` | `cascade` |
| `MODEL` | the candidate tag | unused |
| `SMALL_MODEL` | unused | classifies first (`phi4-mini`) |
| `LARGE_MODEL` | unused | answers escalated tickets, final (`qwen2.5:7b`) |
| `CASCADE_SETTING` | unused | `1` (escalate Bank account) or `2` (+ Consumer loan) |
| `CONFIG_LABEL` | defaults to `MODEL` | defaults to `cascade-setting-<n>` |

Set them in `.env`, then `docker compose up -d service`. `GET /health` returns the active
configuration (`mode`, models, setting, the escalation list and `num_ctx`); check it before every run.

## What the caller sees

The response is `{id, category, model}` as in Assignment 1, but **`model` is `CONFIG_LABEL`: one
fixed string for every ticket in a configuration**. The caller cannot tell which model answered, as
Step 2 of the brief requires. `GET /search` and `GET /stats` are unchanged.

## What the log records (one JSON line per request, as before)

| Field | Meaning |
|---|---|
| `config`, `mode` | the active configuration label and mode |
| `final_model` | the model whose answer was returned |
| `escalated` | true when the ticket went to the large model |
| `cascade_setting` | `1` or `2`; null in single mode |
| `small_category` | the small model's predicted category (or `ERROR: …` if its call failed) |
| `small_model_ms`, `large_model_ms` | time in each model call; `large_model_ms` is null when not escalated |
| `model_ms` | total model time (both calls when escalated) |
| `ollama` | Ollama's own timings for the **final** call |

The escalation fraction is derived from `escalated` in these log lines, never from the response.

## Failure behaviour

| Situation | Result |
|---|---|
| Small model fails or returns an invalid category | Escalate to the large model (rule section 4) |
| Large model fails after escalation | HTTP 502, no fallback, so the failure shows in the error rate |
| Single mode, model fails | HTTP 502, as in Assignment 1 |
