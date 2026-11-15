"""Ticket Triage Service - Assignment 1 baseline.

Synchronous by design: POST /tickets blocks until Ollama has classified the
ticket. No caching, no queue, no batching. Every request is logged as one
JSON line to $LOG_DIR/service.jsonl.
"""
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from . import cascade, classifier, db

LOG_DIR = os.getenv("LOG_DIR", "/logs")
os.makedirs(LOG_DIR, exist_ok=True)

req_log = logging.getLogger("requests")
req_log.setLevel(logging.INFO)
_fh = logging.FileHandler(os.path.join(LOG_DIR, "service.jsonl"), encoding="utf-8")
_fh.setFormatter(logging.Formatter("%(message)s"))
req_log.addHandler(_fh)
req_log.propagate = False

app = FastAPI(title="Ticket Triage Service", version="a1-baseline")


@app.on_event("startup")
def _startup():
    db.init()


def _now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


@app.middleware("http")
async def log_every_request(request: Request, call_next):
    request.state.extra = {}
    start_epoch_ms = int(time.time() * 1000)
    t0 = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        entry = {
            "ts": _now_iso(),
            "start_epoch_ms": start_epoch_ms,
            "request_id": request.headers.get("x-request-id") or uuid.uuid4().hex[:12],
            "run_id": request.headers.get("x-run-id", ""),
            "method": request.method,
            "path": request.url.path,
            "query": request.url.query,
            "status": status,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
            "client": request.client.host if request.client else None,
        }
        entry.update(request.state.extra)
        req_log.info(json.dumps(entry, ensure_ascii=False))


class TicketIn(BaseModel):
    narrative: str = Field(..., min_length=1)
    source_row: int | None = None  # dataset row number, for traceability only


@app.post("/tickets")
def create_ticket(ticket: TicketIn, request: Request):
    extra = request.state.extra
    extra.update(config=cascade.CONFIG_LABEL, mode=cascade.MODE, source_row=ticket.source_row,
                 narrative_chars=len(ticket.narrative))
    try:
        result = cascade.classify(ticket.narrative)
    except classifier.ClassificationError as e:
        extra["error"] = str(e)[:500]
        raise HTTPException(status_code=502, detail="classification failed")

    ticket_id = db.insert(_now_iso(), ticket.narrative, result["category"], result["final_model"],
                          ticket.source_row, request.headers.get("x-run-id", ""))
    # The log records which model actually answered and whether the ticket escalated;
    # the response (below) does not, so the caller cannot tell them apart.
    extra.update(ticket_id=ticket_id, category=result["category"], raw_output=result["raw"][:200],
                 model=result["final_model"], final_model=result["final_model"],
                 escalated=result["escalated"], cascade_setting=result["cascade_setting"],
                 small_category=result["small_category"], small_model_ms=result["small_model_ms"],
                 large_model_ms=result["large_model_ms"],
                 model_ms=result["model_ms"], ollama=result["ollama"])
    # `model` is one fixed label per configuration (docs/escalation_rule.md section 3).
    return {"id": ticket_id, "category": result["category"], "model": cascade.CONFIG_LABEL}


@app.get("/search")
def search(q: str, request: Request, limit: int = 20):
    results = db.search(q, limit)
    request.state.extra.update(results=len(results))
    return {"query": q, "count": len(results), "results": results}


@app.get("/stats")
def stats():
    counts = db.stats()
    return {"total": sum(counts.values()), "by_category": counts}


@app.get("/health")
def health():
    # `model` is kept for the Assignment 1 scripts; in cascade mode it is the config label.
    return {"status": "ok", "model": cascade.CONFIG_LABEL, "ollama_url": classifier.OLLAMA_URL,
            "config": cascade.describe()}


@app.delete("/tickets")
def reset():
    """Test-harness helper: empty the store so each run starts from an empty service."""
    return {"deleted": db.clear()}
