"""Time-series view of a stress run: find the arrival rate at which the system stops keeping up.

Usage: python scripts/analyze_stress.py results/stress/<model>/<config>/run1.jtl [--bucket-sec 60]
       [--monitor results/monitor/<file>.csv]

Per time bucket: arrivals/min, completions/min, p50/p95 latency of requests started in the bucket,
errors, and JMeter active threads (= requests in flight, since open-model threads live for one request).
Latency that keeps rising while completions stay flat => arrivals exceed capacity (unbounded queue growth).
Writes <jtl>.timeline.csv and <jtl>.timeline.png (if matplotlib is installed).
"""
import argparse
from pathlib import Path

import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("jtl")
ap.add_argument("--bucket-sec", type=int, default=60)
ap.add_argument("--label", default="POST /tickets")
ap.add_argument("--monitor", help="CSV from monitor_docker.py, overlays Ollama CPU")
args = ap.parse_args()

df = pd.read_csv(args.jtl, low_memory=False)
df = df[df["label"] == args.label].copy()
t0 = df["timeStamp"].min()
b = args.bucket_sec * 1000
df["ok"] = df["success"].astype(str).str.lower() == "true"
df["start_bucket"] = (df["timeStamp"] - t0) // b
df["end_bucket"] = (df["timeStamp"] + df["elapsed"] - t0) // b
per_min = 60 / args.bucket_sec

tl = pd.DataFrame({
    "arrivals_per_min": df.groupby("start_bucket").size() * per_min,
    "completions_per_min": df[df.ok].groupby("end_bucket").size() * per_min,
    "errors": df[~df.ok].groupby("start_bucket").size(),
    "p50_ms": df[df.ok].groupby("start_bucket")["elapsed"].median(),
    "p95_ms": df[df.ok].groupby("start_bucket")["elapsed"].quantile(.95),
    "in_flight_max": df.groupby("start_bucket")["allThreads"].max(),
}).fillna({"errors": 0, "completions_per_min": 0})
tl.index = (tl.index * args.bucket_sec / 60).rename("minute")
out = Path(args.jtl).with_suffix(".timeline.csv")
tl.to_csv(out)
print(tl.round(1).to_string())
print(f"\npeak completions/min in any bucket: {tl['completions_per_min'].max():.2f}")

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax1.plot(tl.index, tl["arrivals_per_min"], label="arrivals/min", color="tab:gray", ls="--")
    ax1.plot(tl.index, tl["completions_per_min"], label="completions/min", color="tab:blue")
    ax1.set_xlabel("minute of test")
    ax1.set_ylabel("tickets per minute")
    ax2 = ax1.twinx()
    ax2.plot(tl.index, tl["p95_ms"] / 1000, label="p95 latency (s)", color="tab:red")
    ax2.plot(tl.index, tl["p50_ms"] / 1000, label="p50 latency (s)", color="tab:orange")
    ax2.set_ylabel("latency (s)")
    if args.monitor:
        m = pd.read_csv(args.monitor)
        m = m[m["container"] == "ollama"]
        m["minute"] = (m["epoch_ms"] - t0) / 60000
        ax1.plot(m["minute"], m["cpu_pct"] / 100, label="ollama CPU (cores)", color="tab:green", alpha=.5)
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(out.with_suffix(".png"), dpi=150)
except ImportError:
    pass
