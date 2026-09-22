"""Extract this team's 1,000 rows from the course CSV.

Usage: python scripts/extract_team_rows.py --team 4 --csv ../ict3113_tickets.csv

Writes
  data/team_rows.csv       row, source_label, narrative  (the team's working set)
  jmeter/data/tickets.tsv  row <TAB> JSON-escaped narrative  (JMeter CSV Data Set input)
"""
import argparse
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

ap = argparse.ArgumentParser()
ap.add_argument("--team", type=int, required=True)
ap.add_argument("--csv", default=str(ROOT.parent / "ict3113_tickets.csv"))
args = ap.parse_args()

df = pd.read_csv(args.csv)
lo, hi = args.team * 1000, args.team * 1000 + 999
team = df[(df["row"] >= lo) & (df["row"] <= hi)].sort_values("row")
assert len(team) == 1000, f"expected 1000 rows in {lo}-{hi}, got {len(team)}"

(ROOT / "data").mkdir(exist_ok=True)
team.to_csv(ROOT / "data" / "team_rows.csv", index=False)

# One ticket per line; json.dumps escapes quotes, newlines and tabs, so a TAB delimiter is safe.
out = ROOT / "jmeter" / "data" / "tickets.tsv"
out.parent.mkdir(parents=True, exist_ok=True)
with open(out, "w", encoding="utf-8", newline="\n") as f:
    for r in team.itertuples():
        f.write(f"{r.row}\t{json.dumps(r.narrative, ensure_ascii=False)}\n")

(ROOT / "data" / "TEAM").write_text(str(args.team))
lengths = team["narrative"].str.len()
print(f"team {args.team}: rows {lo}-{hi}, {len(team)} tickets")
print("source label counts:\n", team["source_label"].value_counts().to_string())
print("narrative chars:", lengths.describe(percentiles=[.5, .9, .95, .99]).round(0).to_dict())
