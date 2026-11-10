"""A2 speed-test analysis: one row per run, one summary row per configuration.

Usage: python scripts/analyze_a2.py [--base results/a2/speed] [--log logs/service.jsonl]
                                    [--label "POST /tickets"]

Reads <base>/<config>/run*.jtl with the matching run*.meta.json (run_id, and optionally
stats_before / stats_after: the GET /stats ticket totals taken before and after the run).
Writes <base>/runs.csv, <base>/summary.csv and <base>/summary.md.

Definitions, as the A2 brief asks (state these on slide 5):
  sent         samples JMeter recorded for the label (each started request writes one when it ends)
  completed    samples with success=true (HTTP 2xx)
  errored      samples that got an HTTP response that was not a success
  unfinished   samples with no HTTP response (client timeout, socket closed, killed at schedule end)
               plus requests the service logged for this run_id that the .jtl does not contain
  p50          median elapsed (ms) of completed requests in one run; reported per run, then
               mean and spread (sample SD, min-max) across the configuration's runs
  pooled p95   nearest-rank 95th percentile of the completed requests of all runs of the
               configuration together, with the number of requests it is based on (no p99:
               the sample is too small)
  throughput   completed requests per second, over first request start .. last response end
  error rate   (errored + unfinished) / sent
  escalation   for cascade runs: share of this run's POST /tickets service-log lines with
               escalated = true (the brief requires it from the logs, not from the client)
  service_completed  stats_after - stats_before when both are in the meta, else the count of
               status-200 POST /tickets log lines for the run_id
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from common import ROOT, read_log

# Service-log field names for the cascade (agreed with the service owner; change here only).
F_ESCALATED = "escalated"

ap = argparse.ArgumentParser()
ap.add_argument("--base", default=str(ROOT / "results" / "a2" / "speed"))
ap.add_argument("--log", default=str(ROOT / "logs" / "service.jsonl"))
ap.add_argument("--label", default="POST /tickets")
args = ap.parse_args()

base = Path(args.base)
log = pd.DataFrame(list(read_log(path=args.log)))


def nearest_rank(values, p):
    """Value p of the way up the sorted list (an observed value, no interpolation)."""
    v = np.sort(np.asarray(values))
    return float(v[max(math.ceil(p * len(v)), 1) - 1]) if len(v) else float("nan")


runs, pooled = [], {}
for jtl in sorted(base.glob("*/run*.jtl")):
    config = jtl.parent.name
    meta_p = jtl.with_name(jtl.name.replace(".jtl", ".meta.json"))
    meta = json.loads(meta_p.read_text(encoding="utf-8-sig")) if meta_p.exists() else {}
    run_id = meta.get("run_id", "")

    df = pd.read_csv(jtl, low_memory=False)
    df = df[df["label"] == args.label]
    if df.empty:
        continue
    success = df["success"].astype(str).str.lower() == "true"
    http = pd.to_numeric(df["responseCode"], errors="coerce").notna()  # "Non HTTP response code: ..." -> NaN
    ok = df[success]
    errored = int((~success & http).sum())
    no_response = int((~success & ~http).sum())

    lg = log[(log.get("run_id") == run_id) & (log["path"] == "/tickets") & (log["method"] == "POST")] \
        if run_id and len(log) else log.iloc[0:0]
    logged = len(lg)
    missing_from_jtl = max(0, logged - len(df))
    log_ok = int((lg["status"] == 200).sum()) if logged else 0
    if "stats_before" in meta and "stats_after" in meta:
        service_completed, svc_src = int(meta["stats_after"]) - int(meta["stats_before"]), "/stats"
    else:
        service_completed, svc_src = log_ok, "log"

    esc = None
    if logged and F_ESCALATED in lg.columns and lg[F_ESCALATED].notna().any():
        e = lg[F_ESCALATED].astype(str).str.lower()
        esc = {"escalated": int((e == "true").sum()), "logged": logged}

    window_s = ((df["timeStamp"] + df["elapsed"]).max() - df["timeStamp"].min()) / 1000
    runs.append({
        "config": config, "run": jtl.stem, "run_id": run_id,
        "sent": len(df), "completed": len(ok), "errored": errored,
        "unfinished": no_response + missing_from_jtl,
        "error_rate": (errored + no_response + missing_from_jtl) / (len(df) + missing_from_jtl),
        "service_completed": service_completed, "service_completed_source": svc_src,
        "log_lines": logged, "log_matches_jtl": logged == len(df),
        "p50_ms": float(ok["elapsed"].median()) if len(ok) else float("nan"),
        "max_ms": int(ok["elapsed"].max()) if len(ok) else None,
        "throughput_per_s": len(ok) / window_s if window_s else float("nan"),
        "escalated": esc["escalated"] if esc else None,
        "escalation_fraction": esc["escalated"] / esc["logged"] if esc else None,
    })
    pooled.setdefault(config, []).extend(ok["elapsed"].tolist())

if not runs:
    raise SystemExit(f"no .jtl files with label '{args.label}' under {base}/<config>/")
r = pd.DataFrame(runs)
r.to_csv(base / "runs.csv", index=False)

rows = []
for config, g in r.groupby("config", sort=False):
    p50 = g["p50_ms"]
    esc_n = g["escalated"].dropna()
    rows.append({
        "config": config, "runs": len(g),
        "p50_per_run_ms": " / ".join(f"{v:.0f}" for v in p50),
        "p50_mean_ms": p50.mean(), "p50_sd_ms": p50.std(ddof=1) if len(g) > 1 else float("nan"),
        "p50_min_ms": p50.min(), "p50_max_ms": p50.max(),
        "pooled_p95_ms": nearest_rank(pooled[config], 0.95), "pooled_p95_n": len(pooled[config]),
        "throughput_per_s_per_run": " / ".join(f"{v:.3f}" for v in g["throughput_per_s"]),
        "error_rate_per_run": " / ".join(f"{v:.1%}" for v in g["error_rate"]),
        "sent": int(g["sent"].sum()), "completed": int(g["completed"].sum()),
        "errored": int(g["errored"].sum()), "unfinished": int(g["unfinished"].sum()),
        "escalation_per_run": " / ".join(f"{e:.0%}" for e in g["escalation_fraction"].dropna()) if len(esc_n) else "",
        "escalation_pooled": esc_n.sum() / g.loc[g["escalated"].notna(), "log_lines"].sum() if len(esc_n) else None,
        "all_runs_reconcile": bool(g["log_matches_jtl"].all()),
    })
s = pd.DataFrame(rows)
s.to_csv(base / "summary.csv", index=False)

L = ["# A2 speed results", "",
     "| Configuration | Runs | p50 per run (ms) | p50 mean ± SD (min-max) | Pooled p95 (n) | "
     "Throughput /s per run | Error rate per run | Sent / completed / errored / unfinished | Escalation (logs) |",
     "|---|---|---|---|---|---|---|---|---|"]
for x in s.itertuples():
    sd = "-" if math.isnan(x.p50_sd_ms) else f"{x.p50_sd_ms:.0f}"
    esc = f"{x.escalation_per_run} (pooled {x.escalation_pooled:.0%})" if x.escalation_pooled is not None else "-"
    L.append(f"| {x.config} | {x.runs} | {x.p50_per_run_ms} | {x.p50_mean_ms:.0f} ± {sd} ({x.p50_min_ms:.0f}-{x.p50_max_ms:.0f}) | "
             f"{x.pooled_p95_ms:.0f} (n={x.pooled_p95_n}) | {x.throughput_per_s_per_run} | {x.error_rate_per_run} | "
             f"{x.sent} / {x.completed} / {x.errored} / {x.unfinished} | {esc} |")
L += ["", "p50 = median of completed requests per run; pooled p95 = nearest-rank over all runs' completed "
      "requests (n shown); throughput = completed requests per second; escalation from logs/service.jsonl."]
warn = [f"{c}: only {n} run(s)" for c, n in zip(s.config, s.runs) if n < 3]
warn += [f"{x.run_id or x.run}: .jtl {x.sent} vs log {x.log_lines}" for x in r.itertuples() if not x.log_matches_jtl]
warn += [f"{x.run_id or x.run}: {x.unfinished} unfinished" for x in r.itertuples() if x.unfinished]
if warn:
    L += ["", "**Check before reporting:** " + "; ".join(warn)]
(base / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("\n".join(L))
