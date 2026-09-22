"""Summarise JMeter .jtl files: p50/p95/p99, achieved throughput, error rate - per run and across runs.

Usage: python scripts/analyze_jtl.py [--kind load] [--label "POST /tickets"] [--warmup-sec 0]

Reads results/<kind>/<model>/<config>/run*.jtl. A configuration's three runs are
aggregated as mean and standard deviation (spread) of each metric.
Writes results/<kind>/runs.csv (one row per run) and results/<kind>/summary.csv + summary.md.

Definitions (state these on the slide):
  offered rate      = samples started / arrival window (first start .. last start)
  achieved tput     = successful responses / (first start .. last response end)   [per minute]
  error rate        = failed samples / all samples (non-2xx, timeouts, connection errors)
  latency           = JMeter 'elapsed' (request sent -> full response received), successes only
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from common import ROOT

ap = argparse.ArgumentParser()
ap.add_argument("--kind", default="load")
ap.add_argument("--label", default="POST /tickets")
ap.add_argument("--warmup-sec", type=float, default=0, help="drop samples started in the first N seconds")
args = ap.parse_args()

base = ROOT / "results" / args.kind
runs = []
for jtl in sorted(base.glob("*/*/run*.jtl")):
    df = pd.read_csv(jtl, low_memory=False)
    df = df[df["label"] == args.label]
    if df.empty:
        continue
    t0 = df["timeStamp"].min()
    df = df[df["timeStamp"] >= t0 + args.warmup_sec * 1000]
    ok = df[df["success"].astype(str).str.lower() == "true"]
    end = (df["timeStamp"] + df["elapsed"]).max()
    arrival_win = (df["timeStamp"].max() - df["timeStamp"].min()) / 60000
    total_win = (end - df["timeStamp"].min()) / 60000
    meta_p = jtl.with_suffix(".meta.json")
    meta = json.loads(meta_p.read_text(encoding="utf-8-sig")) if meta_p.exists() else {}
    q = ok["elapsed"].quantile([.5, .95, .99]) if len(ok) else pd.Series([np.nan] * 3, index=[.5, .95, .99])
    runs.append({
        "model": jtl.parts[-3], "config": jtl.parts[-2], "run": jtl.stem, "run_id": meta.get("run_id", ""),
        "samples": len(df), "ok": len(ok), "errors": len(df) - len(ok),
        "error_rate": (len(df) - len(ok)) / len(df),
        "offered_per_min": len(df) / arrival_win if arrival_win else np.nan,
        "achieved_per_min": len(ok) / total_win if total_win else np.nan,
        "p50_ms": q[.5], "p95_ms": q[.95], "p99_ms": q[.99], "max_ms": ok["elapsed"].max(),
        "max_concurrency": df["allThreads"].max() if "allThreads" in df else np.nan,
        "top_error": df.loc[df["success"].astype(str).str.lower() != "true", "responseCode"].astype(str).mode().iat[0]
                     if len(df) > len(ok) else "",
    })

if not runs:
    raise SystemExit(f"no .jtl files with label '{args.label}' under {base}")
r = pd.DataFrame(runs)
r.to_csv(base / "runs.csv", index=False)

metrics = ["offered_per_min", "achieved_per_min", "p50_ms", "p95_ms", "p99_ms", "error_rate", "max_concurrency"]
g = r.groupby(["model", "config"])
s = g[metrics].agg(["mean", "std"])
s.columns = [f"{m}_{a}" for m, a in s.columns]
s.insert(0, "runs", g.size())
s.to_csv(base / "summary.csv")

lines = ["| Model | Config | Runs | Offered/min | Achieved/min | p50 ms | p95 ms | p99 ms | Error rate |",
         "|---|---|---|---|---|---|---|---|---|"]
for (m, c), row in s.iterrows():
    f = lambda k, fmt="{:.0f}": f"{fmt.format(row[k + '_mean'])} ± {fmt.format(0 if np.isnan(row[k + '_std']) else row[k + '_std'])}"
    lines.append(f"| {m} | {c} | {int(row['runs'])} | {f('offered_per_min', '{:.2f}')} | {f('achieved_per_min', '{:.2f}')} | "
                 f"{f('p50_ms')} | {f('p95_ms')} | {f('p99_ms')} | {f('error_rate', '{:.1%}')} |")
(base / "summary.md").write_text("\n".join(lines) + "\n\n(mean ± standard deviation across runs)\n", encoding="utf-8")
print("\n".join(lines))
bad = s[s["runs"] < 3]
if len(bad):
    print("\nWARNING: configurations with fewer than 3 runs:", list(bad.index))
