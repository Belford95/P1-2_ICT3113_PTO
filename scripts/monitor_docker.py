"""Sample container CPU/memory on the SUT while tests run (evidence for the bottleneck diagnosis).

Usage (on the SUT machine): python scripts/monitor_docker.py --tag load_llama3.2-3b_rate-4 [--interval 2]
Stop with Ctrl+C. Writes results/monitor/<timestamp>_<tag>.csv (epoch_ms, container, cpu_pct, mem_mib, mem_pct).
cpu_pct is docker's figure: 100% = one full core, so 1600% = all 16 logical CPUs.
"""
import argparse
import csv
import json
import subprocess
import time
from datetime import datetime

from common import ROOT

UNITS = {"GiB": 1024, "MiB": 1, "KiB": 1 / 1024, "B": 1 / 2**20}

ap = argparse.ArgumentParser()
ap.add_argument("--tag", default="")
ap.add_argument("--interval", type=float, default=2)
args = ap.parse_args()

out = ROOT / "results" / "monitor" / f"{datetime.now():%Y%m%d-%H%M%S}_{args.tag}.csv"
out.parent.mkdir(parents=True, exist_ok=True)


def mib(s):
    for unit, factor in UNITS.items():
        if s.endswith(unit):
            return float(s[: -len(unit)]) * factor
    return float("nan")


with open(out, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["epoch_ms", "container", "cpu_pct", "mem_mib", "mem_pct"])
    print("writing", out, "- Ctrl+C to stop")
    try:
        while True:
            ts = int(time.time() * 1000)
            res = subprocess.run(["docker", "stats", "--no-stream", "--format", "{{json .}}"],
                                 capture_output=True, text=True)
            for line in res.stdout.splitlines():
                s = json.loads(line)
                w.writerow([ts, s["Name"], s["CPUPerc"].rstrip("%"),
                            round(mib(s["MemUsage"].split(" / ")[0]), 1), s["MemPerc"].rstrip("%")])
            f.flush()
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("stopped")
