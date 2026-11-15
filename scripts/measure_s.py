"""Measure S, the top model's single-ticket service time, and derive the A2 test settings.

Usage (service in single mode on the top model, Ollama just restarted):
    python scripts/measure_s.py --url http://localhost:8000

Protocol (assignment Step 4, "How to set it"):
  * send the 3 committed warm-up tickets through POST /tickets and discard their timings;
  * send the 3 committed S tickets, one at a time, each a different ticket (a repeat would
    hit Ollama's prompt cache and come back faster than a new ticket);
  * S = the middle of the three times.

Everything goes through POST /tickets, never straight to Ollama, so the model is loaded at
the service's num_ctx (2048) and is not reloaded mid-measurement.

Derived and written to results/a2/speed/s_measurement.json:
    arrival rate  = one ticket every 2*S seconds   (leaves the top model ~50% idle)
    run length    = S minutes, minimum 5
    HTTP timeout  = 10*S seconds, minimum 300
    end pause     = timeout + 60 s, so a slow request is never cut off
"""
import argparse
import json
import math
import statistics
import time
from datetime import datetime

import pandas as pd
import requests

from common import ROOT

TOP_MODEL = "qwen2.5:7b"

ap = argparse.ArgumentParser()
ap.add_argument("--url", default="http://localhost:8000")
ap.add_argument("--top-model", default=TOP_MODEL)
args = ap.parse_args()

health = requests.get(f"{args.url}/health", timeout=10).json()
cfg = health.get("config", {})
if cfg.get("mode") != "single" or cfg.get("model") != args.top_model:
    raise SystemExit(f"S is measured on the top model alone; service is running: {cfg}")

rows = pd.read_csv(ROOT / "jmeter" / "data" / "a2_warmup_rows.csv")
team = pd.read_csv(ROOT / "data" / "team_rows.csv").set_index("row")
warm = rows[rows.role == "warmup"]["row"].tolist()
s_rows = rows[rows.role == "S"]["row"].tolist()
if len(set(s_rows)) != 3:
    raise SystemExit(f"need 3 distinct S rows, got {s_rows}")

stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
run_id = f"a2__S__{stamp}"
print(f"model {args.top_model} | warm-up rows {warm} | S rows {s_rows} | run_id {run_id}\n")


def post(row, tag):
    t0 = time.perf_counter()
    r = requests.post(f"{args.url}/tickets",
                      json={"narrative": team.loc[row, "narrative"], "source_row": int(row)},
                      headers={"X-Run-Id": tag}, timeout=900)
    ms = (time.perf_counter() - t0) * 1000
    r.raise_for_status()
    return ms, r.json()["category"]


for row in warm:
    ms, _ = post(row, run_id + "__warmup")
    print(f"warm-up row {row}: {ms / 1000:6.2f} s (discarded)")

timings = []
for row in s_rows:
    ms, cat = post(row, run_id)
    timings.append({"row": int(row), "chars": int(len(team.loc[row, "narrative"])),
                    "seconds": round(ms / 1000, 2), "category": cat})
    print(f"S ticket row {row}: {ms / 1000:6.2f} s  -> {cat}")

S = statistics.median(t["seconds"] for t in timings)
interval = 2 * S
rate_per_min = round(60 / interval, 2)
run_minutes = max(5, math.ceil(S))
timeout_s = max(300, math.ceil(10 * S))
pause_min = math.ceil((timeout_s + 60) / 60)

out = {
    "run_id": run_id, "measured": stamp, "top_model": args.top_model,
    "health": cfg, "timings": timings,
    "S_seconds": S,
    "arrival_interval_seconds": round(interval, 2),
    "arrival_rate_per_min": rate_per_min,
    "run_length_minutes": run_minutes,
    "expected_tickets_per_run": round(rate_per_min * run_minutes),
    "http_timeout_seconds": timeout_s,
    "end_pause_minutes": pause_min,
    "jmeter_schedule": f"rate({rate_per_min}/min) random_arrivals({run_minutes} min) pause({pause_min} min)",
}
outdir = ROOT / "results" / "a2" / "speed"
outdir.mkdir(parents=True, exist_ok=True)
(outdir / "s_measurement.json").write_text(json.dumps(out, indent=2))

print(f"\nS = {S} s (middle of {[t['seconds'] for t in timings]})")
print(f"arrival rate      : {rate_per_min}/min  (one ticket every {interval:.1f} s)")
print(f"run length        : {run_minutes} min  -> about {out['expected_tickets_per_run']} tickets per run")
print(f"HTTP timeout      : {timeout_s} s")
print(f"end pause         : {pause_min} min")
print(f"JMeter schedule   : {out['jmeter_schedule']}")
print(f"\nwritten to {outdir / 's_measurement.json'}")
