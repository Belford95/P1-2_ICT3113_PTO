"""Seed the store up to a target number of tickets, one at a time through POST /tickets.

Used to reach the store size a search requirement is stated at (e.g. R2: GET /search with
1,000 tickets stored). No bulk import: every ticket goes through the public endpoint,
exactly as the intake would send it.

Usage: python scripts/seed_store.py --url http://localhost:8000 --target 1000

Rows already in the store are skipped, so the script is safe to re-run. Rows are taken
from data/team_rows.csv in order, excluding the golden set by default (those were already
sent during the accuracy runs; --include-golden overrides).
Every request is tagged with a run_id so the seeding is traceable in logs/service.jsonl.
"""
import argparse
import time
from datetime import datetime

import pandas as pd
import requests

from common import ROOT, slug

ap = argparse.ArgumentParser()
ap.add_argument("--url", default="http://localhost:8000")
ap.add_argument("--target", type=int, default=1000, help="total tickets wanted in the store")
ap.add_argument("--include-golden", action="store_true")
args = ap.parse_args()

health = requests.get(f"{args.url}/health", timeout=10).json()
model = health.get("model") or ""
if not model:
    raise SystemExit("no model set on the service: set MODEL in .env and run: docker compose up -d service")

stats = requests.get(f"{args.url}/stats", timeout=30).json()
stored = stats["total"]
print(f"service model: {model} | tickets already stored: {stored} | target: {args.target}")
need = args.target - stored
if need <= 0:
    raise SystemExit("store already at or above the target; nothing to do")

# Which dataset rows are already in the store? (empty query matches every narrative)
existing = requests.get(f"{args.url}/search", params={"q": "", "limit": 1_000_000}, timeout=120).json()
have = {r["source_row"] for r in existing["results"] if r.get("source_row") is not None}
print(f"{len(have)} of those have a known source row")

team = pd.read_csv(ROOT / "data" / "team_rows.csv")
golden_path = ROOT / "golden" / "golden_set.csv"
if golden_path.exists() and not args.include_golden:
    team = team[~team["row"].isin(pd.read_csv(golden_path)["row"])]
todo = team[~team["row"].isin(have)].head(need)
if len(todo) < need:
    raise SystemExit(f"only {len(todo)} unused rows available, need {need}: use --include-golden or lower --target")

run_id = f"seed__{slug(model)}__{datetime.now():%Y%m%d-%H%M%S}"
print(f"posting {len(todo)} tickets, run_id={run_id}")
t0 = time.perf_counter()
failed = 0
for i, r in enumerate(todo.itertuples(), 1):
    try:
        resp = requests.post(f"{args.url}/tickets",
                             json={"narrative": r.narrative, "source_row": int(r.row)},
                             headers={"X-Run-Id": run_id}, timeout=900)
        if not resp.ok:
            failed += 1
    except requests.RequestException:
        failed += 1
    if i % 25 == 0 or i == len(todo):
        rate = i / (time.perf_counter() - t0)
        print(f"  {i}/{len(todo)} posted ({failed} failed) | {rate:.2f}/s | "
              f"~{(len(todo) - i) / rate / 60:.1f} min left")

final = requests.get(f"{args.url}/stats", timeout=30).json()
print(f"done in {(time.perf_counter() - t0) / 60:.1f} min | stored now: {final['total']} | failures: {failed}")
print("by category:", final["by_category"])
