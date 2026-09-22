"""Send every golden-set ticket through POST /tickets for the model the service is running.

Usage: python scripts/accuracy_run.py --url http://<sut-ip>:8000
Switch model first: set MODEL in .env, then `docker compose up -d service` (on the SUT)

Sequential, one request at a time (this is an accuracy test, not a load test).
Writes results/accuracy/<model>__<timestamp>/responses.csv + meta.json.
The run_id header ties every response to its line in logs/service.jsonl.
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
ap.add_argument("--golden", default=str(ROOT / "golden" / "golden_set.csv"))
ap.add_argument("--no-reset", action="store_true", help="do not empty the store before the run")
args = ap.parse_args()

health = requests.get(f"{args.url}/health", timeout=10).json()
model = health["model"]
stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
run_id = f"acc__{slug(model)}__{stamp}"
outdir = ROOT / "results" / "accuracy" / f"{slug(model)}__{stamp}"
outdir.mkdir(parents=True)

gold = pd.read_csv(args.golden)
team = pd.read_csv(ROOT / "data" / "team_rows.csv").set_index("row")
if not args.no_reset:
    requests.delete(f"{args.url}/tickets", headers={"X-Run-Id": run_id + "__reset"}, timeout=30)

# Warm-up so model load time is not charged to the first golden ticket.
requests.post(f"{args.url}/tickets", json={"narrative": "My credit card was charged twice."},
              headers={"X-Run-Id": run_id + "__warmup"}, timeout=900)

rows = []
for i, r in enumerate(gold.itertuples(), 1):
    t0 = time.perf_counter()
    resp = requests.post(f"{args.url}/tickets",
                         json={"narrative": team.loc[r.row, "narrative"], "source_row": int(r.row)},
                         headers={"X-Run-Id": run_id, "X-Request-Id": f"{run_id}__{r.row}"}, timeout=900)
    ms = (time.perf_counter() - t0) * 1000
    pred = resp.json().get("category") if resp.ok else None
    rows.append({"row": r.row, "gold_label": r.gold_label, "predicted": pred,
                 "status": resp.status_code, "client_ms": round(ms, 1)})
    print(f"[{i}/{len(gold)}] row {r.row}: {pred!s:28} gold={r.gold_label:28} {ms:7.0f} ms")

pd.DataFrame(rows).to_csv(outdir / "responses.csv", index=False)
(outdir / "meta.json").write_text(json.dumps(
    {"run_id": run_id, "model": model, "url": args.url, "started": stamp, "n": len(rows)}, indent=2))
print("wrote", outdir)
