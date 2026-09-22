# Ticket Triage Service: ICT3113 Assignment 1

A CPU-only complaint classifier: a FastAPI service backed by Ollama, running in Docker. This is the synchronous **baseline**: it has no caching, no queueing and no batching.

## Run it
```bash
cp .env.example .env            # choose MODEL
docker compose up -d --build
python scripts/pin_models.py <model tags>   # pulls + records digests
curl -X POST localhost:8000/tickets -H "Content-Type: application/json" -d '{"narrative":"I was charged a late fee on my credit card twice"}'
curl "localhost:8000/search?q=late%20fee"
curl localhost:8000/stats
```

| Endpoint | Behaviour |
|---|---|
| `POST /tickets` | body `{"narrative": str, "source_row": int?}`. Calls Ollama synchronously, stores the result, returns `{id, category, model}` |
| `GET /search?q=&limit=20` | tickets whose narrative contains `q` (SQLite `LIKE`, newest first) |
| `GET /stats` | counts of stored tickets by category |
| `GET /health` | status + model in use |
| `DELETE /tickets` | test-harness reset (every test run starts from an empty service) |

Every request is appended as one JSON line to `logs/service.jsonl`. Each line records the run id (`X-Run-Id` header), status, latency, category, and Ollama's timing breakdown.

## Repo map
| Path | What |
|---|---|
| `service/` | the System Under Test |
| `data/team_rows.csv` | our 1,000 rows (`scripts/extract_team_rows.py --team N`) |
| `golden/` | labelling protocol, independent label sheets, agreement, disagreements + resolutions, frozen `golden_set.csv` |
| `predictions/prediction_record.md` | committed before the first benchmark run |
| `jmeter/` | open-model test plan, properties, `run_load.ps1`, ticket feed |
| `results/` | `.jtl` files, accuracy runs, monitor CSVs, summaries (all kept) |
| `logs/` | service request logs (all kept) |
| `docs/service_design.md` | architecture, endpoints, design decisions, log format |
| `docs/models.md` | candidate models and why |
| `docs/playbook.md` | step-by-step test procedure |

Host tooling: `pip install -r scripts/requirements.txt`
