"""Unloaded (single-request) latency: one ticket at a time, no concurrency.

Usage: python scripts/baseline_latency.py --url http://<sut-ip>:8000 --n 30
Uses team rows that are NOT in the golden set (so no model sees golden tickets outside the accuracy test).
The median service time S from this run gives capacity ~ 60000/S tickets per minute with
OLLAMA_NUM_PARALLEL=1, which is how you pick the arrival rates for the load tests.
"""
import argparse
import json
import time
from datetime import datetime

import pandas as pd
import requests

from common import ROOT, slug

ap = argparse.ArgumentParser()
ap.add_argument("--url", default="http://localhost:8000")
ap.add_argument("--n", type=int, default=30)
ap.add_argument("--seed", type=int, default=7)
args = ap.parse_args()

model = requests.get(f"{args.url}/health", timeout=10).json()["model"]
stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
run_id = f"single__{slug(model)}__{stamp}"
team = pd.read_csv(ROOT / "data" / "team_rows.csv")
golden = ROOT / "golden" / "golden_set.csv"
if golden.exists():
    team = team[~team["row"].isin(pd.read_csv(golden)["row"])]
sample = team.sample(args.n, random_state=args.seed)

requests.post(f"{args.url}/tickets", json={"narrative": "warm-up ticket about a credit card fee"},
              headers={"X-Run-Id": run_id + "__warmup"}, timeout=900)
rows = []
for r in sample.itertuples():
    t0 = time.perf_counter()
    resp = requests.post(f"{args.url}/tickets", json={"narrative": r.narrative, "source_row": int(r.row)},
                         headers={"X-Run-Id": run_id}, timeout=900)
    rows.append({"row": r.row, "chars": len(r.narrative), "status": resp.status_code,
                 "client_ms": (time.perf_counter() - t0) * 1000})
df = pd.DataFrame(rows)
outdir = ROOT / "results" / "single"
outdir.mkdir(parents=True, exist_ok=True)
df.to_csv(outdir / f"{slug(model)}__{stamp}.csv", index=False)
q = df["client_ms"].quantile([.5, .95, .99])
summary = {"run_id": run_id, "model": model, "n": len(df), "p50_ms": q[.5], "p95_ms": q[.95], "p99_ms": q[.99],
           "mean_ms": df["client_ms"].mean(), "capacity_per_min_est": 60000 / df["client_ms"].mean()}
(outdir / f"{slug(model)}__{stamp}.json").write_text(json.dumps(summary, indent=2))
print(json.dumps(summary, indent=2))
