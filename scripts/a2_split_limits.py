"""A2 Step 1: golden split (odd position after sorting by row number = tuning, even = test), accuracy limits from the
top model's test-set accuracy, every A1 model scored on the test set, and a tuning-set
reliability table for rule design.
Reads golden/golden_set.csv and reuses the A1 accuracy records (results/accuracy/*/responses.csv).

Usage: python scripts/a2_split_limits.py
Writes golden/split_a2.csv, golden/limits_a2.md, docs/a2_tuning_reliability.md"""
import glob
import os
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1].as_posix()
CATS = ["Credit reporting", "Debt collection", "Mortgage", "Credit card",
        "Bank account or service", "Consumer loan", "Money transfer or service"]
TOP = "qwen2.5-7b"

# Brief: "Sort your golden-set tickets by row number. Odd rows are your tuning set.
# Even rows are your test set." Read as positions in the sorted list (1st, 3rd, ...),
# since the sort only matters for a positional split.
gold = pd.read_csv(f"{REPO}/golden/golden_set.csv").sort_values("row").reset_index(drop=True)
gold["position"] = gold.index + 1
gold["set"] = gold["position"].map(lambda p: "tuning" if p % 2 else "test")
gold[["position", "row", "gold_label", "set"]].to_csv(f"{REPO}/golden/split_a2.csv", index=False)

runs = {}
for d in sorted(glob.glob(f"{REPO}/results/accuracy/*__*")):
    name = os.path.basename(d).split("__")[0]
    r = pd.read_csv(f"{d}/responses.csv")[["row", "predicted", "status"]]
    m = gold.merge(r, on="row", how="left")
    assert m["predicted"].notna().all() and len(m) == len(gold), name
    m["correct"] = m["predicted"] == m["gold_label"]
    runs[name] = m


def score(m):
    t = m[m["set"] == "test"]
    out = {"overall": (int(t.correct.sum()), len(t))}
    for c in CATS:
        g = t[t.gold_label == c]
        out[c] = (int(g.correct.sum()), len(g))
    return out


scores = {k: score(v) for k, v in runs.items()}
top = scores[TOP]
pct = lambda k, n: 100 * k / n
lim_overall = pct(*top["overall"]) - 10
lim_cat = {c: pct(*top[c]) - 15 for c in CATS}

L = ["# Assignment 2 accuracy limits (test set = even positions in the row-sorted golden set)", ""]
n_tune = int((gold.set == "tuning").sum())
n_test = int((gold.set == "test").sum())
L += [f"Golden set: {len(gold)} tickets -> tuning {n_tune} (odd positions after sorting by row number), test {n_test} (even positions).",
      f"Top model: `qwen2.5:7b` (A1 full-golden-set accuracy 80.3%).",
      "Source: A1 accuracy records `results/accuracy/*/responses.csv` (reused: same digest, prompt, "
      "Ollama 0.35.0 and machine), scored on test-set rows only.", ""]
k, n = top["overall"]
L += [f"**Overall limit: {pct(k, n):.1f}% ({k}/{n}) - 10 = {lim_overall:.1f}%**", "",
      "| Category | Test n | qwen2.5:7b | Limit (-15 pts) | Fair test? |", "|---|---|---|---|---|"]
for c in CATS:
    k, n = top[c]
    fair = "no: 1 ticket = %.1f pts" % (100 / n) if n < 10 else "yes"
    L.append(f"| {c} | {n} | {pct(k, n):.1f}% ({k}/{n}) | {lim_cat[c]:.1f}% | {fair} |")

L += ["", "## Every A1 model on the test set", "",
      "| Model | Overall | " + " | ".join(CATS) + " | Passes? |",
      "|---|---|" + "---|" * len(CATS) + "---|"]
for name, s in scores.items():
    k, n = s["overall"]
    ok_o = pct(k, n) >= lim_overall - 1e-9
    cells, fails = [], []
    for c in CATS:
        ck, cn = s[c]
        ok = pct(ck, cn) >= lim_cat[c] - 1e-9
        if not ok:
            fails.append(c)
        cells.append(f"{pct(ck, cn):.0f}% ({ck}/{cn}){'' if ok else ' ✗'}")
    verdict = "reference" if name == TOP else ("PASS" if ok_o and not fails else
                                               "fail: " + ("overall; " if not ok_o else "") + ", ".join(fails))
    L.append(f"| {name} | {pct(k, n):.1f}% ({k}/{n}){'' if ok_o else ' ✗'} | " + " | ".join(cells) + f" | {verdict} |")
open(f"{REPO}/golden/limits_a2.md", "w", encoding="utf-8").write("\n".join(L) + "\n")

# Tuning-set view for rule design: per small model, precision by PREDICTED category.
T = ["# Tuning set (odd positions): small-model reliability by predicted category", "",
     "Precision = of the tuning tickets the model labelled X, how many really were X. "
     "A category-based rule can only see the predicted label.", ""]
for name, m in runs.items():
    if name == TOP:
        continue
    t = m[m["set"] == "tuning"]
    k = int(t.correct.sum())
    T += [f"## {name}: tuning accuracy {pct(k, len(t)):.1f}% ({k}/{len(t)})", "",
          "| Predicted as | n | Correct | Precision |", "|---|---|---|---|"]
    for c in CATS:
        p = t[t.predicted == c]
        if len(p):
            T.append(f"| {c} | {len(p)} | {int(p.correct.sum())} | {pct(p.correct.sum(), len(p)):.0f}% |")
    other = t[~t.predicted.isin(CATS)]
    if len(other):
        T.append(f"| (other/unclassified) | {len(other)} | {int(other.correct.sum())} | - |")
    T.append("")
open(f"{REPO}/docs/a2_tuning_reliability.md", "w", encoding="utf-8").write("\n".join(T))
print("\n".join(L))
