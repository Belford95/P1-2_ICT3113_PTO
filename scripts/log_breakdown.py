"""Where does the time go? Break POST /tickets latency into Ollama phases, from the service log.

Usage: python scripts/log_breakdown.py [run_id or prefix*]     e.g.  "load__llama3.2-3b__rate-4__*"

  service latency_ms = total time inside the service
  ollama total_ms    = Ollama's own processing time (load + prompt eval + generation)
  wait_ms            = latency_ms - ollama total_ms  (mostly time queued inside Ollama behind other requests
                       when OLLAMA_NUM_PARALLEL=1, plus service/DB overhead)
If wait_ms dominates under load while prompt_eval_ms stays flat, the bottleneck is Ollama's single
inference slot on CPU, not the web service.
"""
import sys

import pandas as pd

from common import read_log

rid = sys.argv[1] if len(sys.argv) > 1 else None
rows = []
for e in read_log(rid):
    if e["path"] != "/tickets" or e["method"] != "POST" or e["status"] != 200:
        continue
    o = e.get("ollama", {})
    rows.append({"run_id": e["run_id"], "model": e.get("model"), "chars": e.get("narrative_chars"),
                 "latency_ms": e["latency_ms"], "ollama_total_ms": o.get("total_ms"),
                 "prompt_eval_ms": o.get("prompt_eval_ms"), "prompt_tokens": o.get("prompt_eval_count"),
                 "eval_ms": o.get("eval_ms"), "eval_tokens": o.get("eval_count"), "load_ms": o.get("load_ms")})
df = pd.DataFrame(rows)
if df.empty:
    raise SystemExit("no successful POST /tickets entries for that run_id")
df["wait_ms"] = df["latency_ms"] - df["ollama_total_ms"]
df["prefill_tok_per_s"] = df["prompt_tokens"] / (df["prompt_eval_ms"] / 1000)
cols = ["latency_ms", "ollama_total_ms", "prompt_eval_ms", "eval_ms", "load_ms", "wait_ms",
        "prompt_tokens", "prefill_tok_per_s"]
print("medians per run:")
print(df.groupby(["run_id", "model"])[cols].median().round(0).to_string())
print("\ncorrelation of latency with narrative length (chars):", round(df["latency_ms"].corr(df["chars"]), 3))
