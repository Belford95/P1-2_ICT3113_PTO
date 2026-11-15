"""Pre-run warm-up: send the three fixed warm-up tickets through POST /tickets.

Usage (after restarting Ollama and setting the configuration in .env):
    python scripts/warmup.py --url http://localhost:8000

Timings are printed but discarded; the first ticket pays the model load. Everything goes
through the service, so models load at the service's num_ctx (2048) and are not reloaded.

In cascade mode the large model only warms up if a warm-up ticket escalates. If none did,
one extra ticket is sent whose predicted category is on the escalation list, so both models
are resident before the run starts. Run `ollama ps` afterwards to confirm.
"""
import argparse
import time

import pandas as pd
import requests

from common import ROOT

# Used only if the warm-up tickets did not escalate: the small model reliably reads this
# as "Bank account or service", which both settings escalate.
ESCALATING_TICKET = ("My checking account was closed without notice and the bank kept "
                     "charging overdraft fees on it.")

ap = argparse.ArgumentParser()
ap.add_argument("--url", default="http://localhost:8000")
ap.add_argument("--run-id", default="a2__warmup")
args = ap.parse_args()

started_ms = int(time.time() * 1000)  # so only this invocation's log lines count
health = requests.get(f"{args.url}/health", timeout=10).json()
cfg = health.get("config", {})
print(f"configuration: {cfg}\n")

rows = pd.read_csv(ROOT / "jmeter" / "data" / "a2_warmup_rows.csv")
warm = rows[rows.role == "warmup"]["row"].tolist()
team = pd.read_csv(ROOT / "data" / "team_rows.csv").set_index("row")


def post(narrative, row=None):
    body = {"narrative": narrative}
    if row is not None:
        body["source_row"] = int(row)
    t0 = time.perf_counter()
    r = requests.post(f"{args.url}/tickets", json=body,
                      headers={"X-Run-Id": args.run_id}, timeout=900)
    r.raise_for_status()
    return (time.perf_counter() - t0), r.json()


for row in warm:
    secs, resp = post(team.loc[row, "narrative"], row)
    print(f"warm-up row {row}: {secs:6.2f} s (discarded) -> {resp['category']}")

if cfg.get("mode") == "cascade":
    # Did any warm-up ticket reach the large model? The response deliberately hides this,
    # so read it from the service log instead.
    import json
    escalated = False
    with open(ROOT / "logs" / "service.jsonl", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            e = json.loads(line)
            if (e.get("run_id") == args.run_id and e.get("source_row") in warm
                    and e.get("start_epoch_ms", 0) >= started_ms):
                escalated = escalated or bool(e.get("escalated"))
    if escalated:
        print("\nat least one warm-up ticket escalated: both models are warm")
    else:
        secs, resp = post(ESCALATING_TICKET)
        print(f"\nno warm-up ticket escalated; sent one extra to warm {cfg.get('large_model')}: "
              f"{secs:6.2f} s -> {resp['category']}")

print("\nnow run:  docker exec ollama ollama ps")
print("expect CONTEXT 2048 and 100% CPU for every model this configuration uses "
      "(both models in cascade mode).")
