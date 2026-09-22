"""Accuracy vs the golden set for every run in results/accuracy/.

Usage: python scripts/accuracy_report.py
Per run: overall accuracy (+95% Wilson CI), per-category recall/precision/F1,
confusion matrix (csv, and png if matplotlib is installed), and a reconciliation
check against logs/service.jsonl. Summary table: results/accuracy/summary.md
"""
import json

import pandas as pd

from common import CATEGORIES, ROOT, read_log, wilson

ACC = ROOT / "results" / "accuracy"
summary = []
for run in sorted(p for p in ACC.iterdir() if (p / "responses.csv").exists()):
    meta = json.loads((run / "meta.json").read_text())
    df = pd.read_csv(run / "responses.csv")
    df["predicted"] = df["predicted"].fillna("ERROR")
    n, k = len(df), int((df.predicted == df.gold_label).sum())
    lo, hi = wilson(k, n)

    labels_pred = CATEGORIES + sorted(set(df.predicted) - set(CATEGORIES))
    cm = pd.crosstab(pd.Categorical(df.gold_label, CATEGORIES),
                     pd.Categorical(df.predicted, labels_pred), dropna=False,
                     rownames=["gold"], colnames=["predicted"])
    cm.to_csv(run / "confusion_matrix.csv")

    per = []
    for c in CATEGORIES:
        tp = int(((df.gold_label == c) & (df.predicted == c)).sum())
        support = int((df.gold_label == c).sum())
        npred = int((df.predicted == c).sum())
        rec = tp / support if support else float("nan")
        prec = tp / npred if npred else float("nan")
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        per.append({"category": c, "support": support, "recall(acc)": rec, "precision": prec, "f1": f1})
    per = pd.DataFrame(per)
    per.to_csv(run / "per_category.csv", index=False)

    # Reconcile: every response must have a matching log line with the same category.
    log = {e.get("source_row"): e for e in read_log(meta["run_id"]) if e["path"] == "/tickets"}
    mismatches = sum(1 for r in df.itertuples() if log.get(r.row, {}).get("category") != r.predicted
                     and r.predicted != "ERROR")
    lat = pd.Series([e["latency_ms"] for e in log.values()])
    recon = f"log lines {len(log)}/{n}, category mismatches {mismatches}"

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(8, 6.5))
        ax.imshow(cm.values, cmap="Blues")
        ax.set_xticks(range(cm.shape[1]), cm.columns, rotation=40, ha="right", fontsize=8)
        ax.set_yticks(range(cm.shape[0]), cm.index, fontsize=8)
        for i in range(cm.shape[0]):
            for j in range(cm.shape[1]):
                v = cm.values[i, j]
                if v:
                    ax.text(j, i, v, ha="center", va="center", fontsize=8,
                            color="white" if v > cm.values.max() / 2 else "black")
        ax.set_xlabel("Predicted"); ax.set_ylabel("Golden label")
        ax.set_title(f"{meta['model']}  accuracy {k/n:.1%} (n={n})")
        fig.tight_layout(); fig.savefig(run / "confusion_matrix.png", dpi=160); plt.close(fig)
    except ImportError:
        pass

    summary.append({"model": meta["model"], "run": run.name, "n": n, "accuracy": k / n,
                    "ci95": f"{lo:.1%}-{hi:.1%}", "macro_f1": per["f1"].mean(),
                    "worst_category": per.sort_values("recall(acc)").iloc[0]["category"],
                    "p50_ms_seq": lat.median() if len(lat) else None, "reconcile": recon,
                    **{f"acc:{c}": v for c, v in zip(per.category, per["recall(acc)"])}})
    print(f"{meta['model']:22} acc {k/n:.1%} [{lo:.1%},{hi:.1%}]  {recon}")

s = pd.DataFrame(summary)
s.to_csv(ACC / "summary.csv", index=False)
(ACC / "summary.md").write_text(s.round(3).to_string(index=False), encoding="utf-8")
