"""Draw the golden-set sample and create blank, independent label sheets.

Usage: python scripts/make_golden_sample.py --n 180 --annotators A B [C ...] --seed 3113

Sampling is stratified by the (noisy) source label so every category is
represented; the source label is NOT shown on the label sheets to avoid anchoring.
Writes golden/sample_rows.csv and golden/label_sheets/labels_<annotator>.xlsx (or .csv).
"""
import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = ["Credit reporting", "Debt collection", "Mortgage", "Credit card",
              "Bank account or service", "Consumer loan", "Money transfer or service",
              "None / Unclear"]

ap = argparse.ArgumentParser()
ap.add_argument("--n", type=int, default=180)
ap.add_argument("--annotators", nargs="+", default=["A", "B"])
ap.add_argument("--seed", type=int, default=3113)
args = ap.parse_args()

team = pd.read_csv(ROOT / "data" / "team_rows.csv")
per = args.n // team["source_label"].nunique()
sample = (team.groupby("source_label", group_keys=False)
              .apply(lambda g: g.sample(min(per, len(g)), random_state=args.seed)))
if len(sample) < args.n:  # top up remainder at random
    rest = team.drop(sample.index).sample(args.n - len(sample), random_state=args.seed)
    sample = pd.concat([sample, rest])
sample = sample.sample(frac=1, random_state=args.seed).sort_values("row")  # sort by row, hide strata
sample[["row", "source_label"]].to_csv(ROOT / "golden" / "sample_rows.csv", index=False)

sheet = sample[["row", "narrative"]].copy()
sheet["label"] = ""
sheet["confidence_1to3"] = ""
sheet["notes"] = ""
outdir = ROOT / "golden" / "label_sheets"
outdir.mkdir(parents=True, exist_ok=True)
for a in args.annotators:
    try:
        from openpyxl.worksheet.datavalidation import DataValidation
        path = outdir / f"labels_{a}.xlsx"
        with pd.ExcelWriter(path, engine="openpyxl") as xw:
            sheet.to_excel(xw, index=False, sheet_name="labels")
            ws = xw.sheets["labels"]
            ws.column_dimensions["B"].width = 110
            ws.column_dimensions["C"].width = 28
            for row in ws.iter_rows(min_row=2, min_col=2, max_col=2):
                row[0].alignment = row[0].alignment.copy(wrap_text=True, vertical="top")
            dv = DataValidation(type="list", formula1='"' + ",".join(CATEGORIES) + '"', allow_blank=True)
            ws.add_data_validation(dv)
            dv.add(f"C2:C{len(sheet) + 1}")
    except ImportError:
        path = outdir / f"labels_{a}.csv"
        sheet.to_csv(path, index=False)
    print("wrote", path)
print(f"{len(sample)} tickets sampled; source-label mix:\n{sample['source_label'].value_counts().to_string()}")
