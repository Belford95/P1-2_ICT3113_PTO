"""Merge agreed labels with recorded resolutions into the frozen golden set.

Usage: python scripts/finalize_golden.py
Requires every row of golden/disagreements.csv to have resolved_label and resolution_note.
resolved_label may be EXCLUDE (ticket fits no category); excluded rows are listed, not silently dropped.
Writes golden/golden_set.csv (row, gold_label, how).
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = {"Credit reporting", "Debt collection", "Mortgage", "Credit card",
              "Bank account or service", "Consumer loan", "Money transfer or service"}

import agreement  # noqa: E402  (reuses the sheet loader; also refreshes agreement.md)

labels = agreement.load_sheets()
res = pd.read_csv(ROOT / "golden" / "disagreements.csv").set_index("row")
res["resolved_label"] = res["resolved_label"].fillna("").astype(str).str.strip()
todo = res[(res["resolved_label"] == "") | res["resolution_note"].isna()]
if len(todo):
    raise SystemExit(f"{len(todo)} disagreements lack a resolution/note: {todo.index.tolist()[:10]}")
bad = set(res["resolved_label"]) - CATEGORIES - {"EXCLUDE"}
if bad:
    raise SystemExit(f"invalid resolved labels: {bad}")

agreed = labels[labels.nunique(axis=1) == 1].iloc[:, 0]
gold = pd.DataFrame({"gold_label": agreed, "how": "agreed"})
gold = pd.concat([gold, pd.DataFrame({"gold_label": res["resolved_label"], "how": "resolved"})])
excluded = gold[(gold["gold_label"] == "EXCLUDE") | ~gold["gold_label"].isin(CATEGORIES)]
gold = gold.drop(excluded.index).sort_index()
gold.index.name = "row"
gold.to_csv(ROOT / "golden" / "golden_set.csv")
if len(excluded):
    excluded.to_csv(ROOT / "golden" / "excluded_rows.csv", index_label="row")
print(f"golden set: {len(gold)} tickets ({(gold.how == 'resolved').sum()} resolved), excluded {len(excluded)}")
print(gold["gold_label"].value_counts().to_string())
