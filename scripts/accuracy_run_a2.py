"""A2 accuracy test: send the test-set tickets through POST /tickets, one at a time.

Usage: python scripts/accuracy_run_a2.py --url http://localhost:8000 [--set test|tuning]

The configuration under test is whatever the service is running; it is read from
GET /health, so the folder and meta can't disagree with what actually answered.
Switch configuration in .env, then `docker compose up -d service`.

Sequential, one request at a time: this is an accuracy test, not a load test.
Writes results/a2/accuracy/<config>__<set>__<timestamp>/responses.csv + meta.json,
which scripts/accuracy_report_a2.py scores against golden/limits_a2.md.
"""
import argparse
import json
import time
from datetime import datetime

import pandas as pd
import requests

from common import ROOT, slug

# Warm-up only. Not golden-set tickets, not scored, logged under a separate run id.
# The second one is phrased so the small model should answer "Bank account or service",
# which both settings escalate, so the large model is warmed too (docs/escalation_rule.md).
WARMUPS = [
    "I was charged a late fee twice on my credit card after paying on time.",
    "My checking account was closed without notice and the bank kept charging overdraft fees on it.",
]

ap = argparse.ArgumentParser()
ap.add_argument("--url", default="http://localhost:8000")
ap.add_argument("--set", choices=["test", "tuning"], default="test")
ap.add_argument("--no-reset", action="store_true", help="keep whatever is already stored")
args = ap.parse_args()

health = requests.get(f"{args.url}/health", timeout=10).json()
cfg = health.get("config", {})
label = health.get("model") or cfg.get("config_label") or "unknown"
mode = cfg.get("mode", "single")
if mode == "cascade" and not cfg.get("cascade_setting"):
    raise SystemExit("service is in cascade mode but CASCADE_SETTING is not set")

stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
run_id = f"a2__acc__{slug(label)}__{args.set}__{stamp}"
outdir = ROOT / "results" / "a2" / "accuracy" / f"{slug(label)}__{args.set}__{stamp}"
outdir.mkdir(parents=True)

split = pd.read_csv(ROOT / "golden" / "split_a2.csv")
rows = split[split["set"] == args.set]
team = pd.read_csv(ROOT / "data" / "team_rows.csv").set_index("row")
print(f"config: {json.dumps(cfg)}\n{len(rows)} {args.set}-set tickets, run_id={run_id}")

if not args.no_reset:
    requests.delete(f"{args.url}/tickets", headers={"X-Run-Id": run_id + "__reset"}, timeout=30)
for i, w in enumerate(WARMUPS, 1):
    requests.post(f"{args.url}/tickets", json={"narrative": w},
                  headers={"X-Run-Id": run_id + "__warmup"}, timeout=900)
    print(f"warm-up {i}/{len(WARMUPS)} done")

out = []
t0 = time.perf_counter()
for i, r in enumerate(rows.itertuples(), 1):
    start = time.perf_counter()
    resp = requests.post(f"{args.url}/tickets",
                         json={"narrative": team.loc[r.row, "narrative"], "source_row": int(r.row)},
                         headers={"X-Run-Id": run_id, "X-Request-Id": f"{run_id}__{r.row}"}, timeout=900)
    ms = (time.perf_counter() - start) * 1000
    pred = resp.json().get("category") if resp.ok else None
    out.append({"row": r.row, "gold_label": r.gold_label, "predicted": pred,
                "status": resp.status_code, "client_ms": round(ms, 1)})
    print(f"[{i}/{len(rows)}] row {r.row}: {pred!s:28} gold={r.gold_label:28} {ms:7.0f} ms")

pd.DataFrame(out).to_csv(outdir / "responses.csv", index=False)
meta = {
    "run_id": run_id, "set": args.set, "url": args.url, "started": stamp,
    "n": len(out), "config": label, "mode": mode, "cascade": mode == "cascade",
    "model": cfg.get("model") or label, "config_detail": cfg,
}
if mode == "cascade":
    meta.update(setting=f"Setting {cfg['cascade_setting']}",
                small_model=cfg.get("small_model"), large_model=cfg.get("large_model"),
                escalate_on=cfg.get("escalate_on"))
(outdir / "meta.json").write_text(json.dumps(meta, indent=2))
print(f"\ndone in {(time.perf_counter() - t0) / 60:.1f} min -> {outdir}")
print("next: python scripts/accuracy_report_a2.py")
