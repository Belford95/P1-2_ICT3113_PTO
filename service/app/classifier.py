"""Calls the Ollama backend to classify one ticket narrative.

Baseline behaviour (Assignment 1): one blocking HTTP call per ticket,
no caching, no batching, no retries.
"""
import json
import os
import time

import requests

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
MODEL = os.getenv("MODEL", "")  # set in .env; candidates chosen by the Model/requirements owner (docs/models.md)
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

# Zero-shot prompt: category names only, no definitions or examples (no training involved).
SYSTEM_PROMPT = (
    "Classify the customer complaint into exactly one of these categories:\n"
    + "\n".join(f"- {c}" for c in CATEGORIES)
    + '\n\nRespond with JSON only: {"category": "<one of the categories above>"}'
)

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
    if not MODEL:
        raise ClassificationError("no model configured: set MODEL in .env")
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
