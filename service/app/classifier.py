"""Calls the Ollama backend to classify one ticket narrative.

Baseline behaviour (Assignment 1): one blocking HTTP call per ticket,
no caching, no batching, no retries.
"""
import json
import os
import time

import requests

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
MODEL = os.getenv("MODEL", "llama3.2:3b")
NUM_CTX = int(os.getenv("NUM_CTX", "2048"))
OLLAMA_TIMEOUT_S = float(os.getenv("OLLAMA_TIMEOUT_S", "600"))

CATEGORIES = [
    "Credit reporting",
    "Debt collection",
    "Mortgage",
    "Credit card",
    "Bank account or service",
    "Consumer loan",
    "Money transfer or service",
]

SYSTEM_PROMPT = """You are a triage assistant at a financial services complaints desk.
Classify the customer complaint into exactly one of these categories:

- Credit reporting: errors or disputes about credit reports or credit scores, identity theft showing on a report, credit bureau investigations.
- Debt collection: attempts to collect a debt, collector communication or harassment, debts not owed, validation of debt.
- Mortgage: home loans, mortgage servicing, escrow, loan modification, foreclosure, home equity loans.
- Credit card: credit card accounts, card billing disputes, card fees and interest, card rewards, card applications.
- Bank account or service: checking or savings accounts, deposits and withdrawals, overdraft fees, account opening or closing, debit cards.
- Consumer loan: vehicle loans or leases, personal loans, installment loans, payday loans, student loans.
- Money transfer or service: wire transfers, remittances, money orders, peer-to-peer payment apps, virtual currency transfers.

Choose the category describing the product or service the complaint is mainly about.
Respond with JSON only: {"category": "<one of the categories above>"}"""

# Structured output: Ollama constrains decoding to this JSON schema.
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {"category": {"type": "string", "enum": CATEGORIES}},
    "required": ["category"],
}


class ClassificationError(Exception):
    pass


def classify(narrative: str) -> dict:
    """Returns {"category", "raw", "ollama": {...timings...}, "model_ms"}."""
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": narrative},
        ],
        "format": RESPONSE_SCHEMA,
        "stream": False,
        "keep_alive": -1,
        "options": {"temperature": 0, "seed": 42, "num_ctx": NUM_CTX},
    }
    t0 = time.perf_counter()
    try:
        r = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=OLLAMA_TIMEOUT_S)
    except requests.RequestException as e:
        raise ClassificationError(f"ollama request failed: {e}") from e
    model_ms = (time.perf_counter() - t0) * 1000
    if r.status_code != 200:
        raise ClassificationError(f"ollama HTTP {r.status_code}: {r.text[:300]}")

    body = r.json()
    raw = body.get("message", {}).get("content", "")
    category = _parse_category(raw)
    ns = 1e6  # Ollama reports durations in nanoseconds -> ms
    timings = {
        "total_ms": body.get("total_duration", 0) / ns,
        "load_ms": body.get("load_duration", 0) / ns,
        "prompt_eval_count": body.get("prompt_eval_count"),
        "prompt_eval_ms": body.get("prompt_eval_duration", 0) / ns,
        "eval_count": body.get("eval_count"),
        "eval_ms": body.get("eval_duration", 0) / ns,
    }
    return {"category": category, "raw": raw, "ollama": timings, "model_ms": model_ms}


def _parse_category(raw: str) -> str:
    try:
        cat = json.loads(raw).get("category", "")
    except (ValueError, AttributeError):
        cat = raw
    for c in CATEGORIES:
        if c.lower() == str(cat).strip().lower():
            return c
    # Fall back to substring match on free text; anything else is Unclassified.
    for c in CATEGORIES:
        if c.lower() in str(raw).lower():
            return c
    return "Unclassified"
