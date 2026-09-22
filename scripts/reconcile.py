"""Check that every JMeter run reconciles with the service log.

Usage: python scripts/reconcile.py [--kind load]
For each run*.meta.json: compares the .jtl with logs/service.jsonl lines carrying the same run_id.
  - request counts per endpoint (JMeter vs service)
  - status codes / errors on both sides
  - median latency: JMeter elapsed vs service latency_ms (difference = network + client overhead)
  - requests JMeter timed out on that the service still completed (they show only in the log)
Writes results/<kind>/reconciliation.csv. Run this before putting any number on a slide.
"""
import argparse
import json

import pandas as pd

from common import ROOT, read_log

ap = argparse.ArgumentParser()
ap.add_argument("--kind", default="load")
args = ap.parse_args()

base = ROOT / "results" / args.kind
log = pd.DataFrame(list(read_log()))
out = []
for meta_p in sorted(base.glob("*/*/run*.meta.json")):
    meta = json.loads(meta_p.read_text(encoding="utf-8-sig"))
    jtl = pd.read_csv(meta_p.with_name(meta_p.name.replace(".meta.json", ".jtl")), low_memory=False)
    lg = log[log["run_id"] == meta["run_id"]] if len(log) else log
    for label, path in [("POST /tickets", "/tickets"), ("GET /search", "/search"), ("GET /stats", "/stats")]:
        j = jtl[jtl["label"] == label]
        s = lg[(lg["path"] == path) & (lg["method"] == label.split()[0])] if len(lg) else lg
        if j.empty and s.empty:
            continue
        j_ok = j[j["success"].astype(str).str.lower() == "true"]
        s_ok = s[s["status"] == 200] if len(s) else s
        out.append({
            "run_id": meta["run_id"], "endpoint": label,
            "jmeter_n": len(j), "service_n": len(s), "count_match": len(j) == len(s),
            "jmeter_ok": len(j_ok), "service_ok": len(s_ok),
            "jmeter_p50_ms": j_ok["elapsed"].median(), "service_p50_ms": s_ok["latency_ms"].median() if len(s_ok) else None,
            "overhead_p50_ms": (j_ok["elapsed"].median() - s_ok["latency_ms"].median()) if len(s_ok) else None,
            "client_timeouts_completed_by_service": max(0, len(s_ok) - len(j_ok)),
        })
r = pd.DataFrame(out)
r.to_csv(base / "reconciliation.csv", index=False)
print(r.to_string(index=False))
if len(r) and not r["count_match"].all():
    print("\nMISMATCH: some runs do not reconcile - investigate before reporting (lost requests? wrong log file?)")
