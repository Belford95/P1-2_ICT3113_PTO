"""A2 accuracy report: every configuration scored on the test set against the A2 limits.

Usage: python scripts/accuracy_report_a2.py [--set test|tuning] [--a2-dir DIR] [--log FILE]

Configurations scored:
  * single models: the A1 accuracy records in results/accuracy/ (reused, as the brief
    allows: same digests, prompt, Ollama 0.35.0 and machine), restricted to the chosen set;
  * A2 runs: every results/a2/accuracy/<run>/ with responses.csv + meta.json
    (cascade settings, or any single model re-run under A2).

Limits come from qwen2.5:7b's A1 record on the same set: overall >= top - 10 points,
each category >= top's accuracy on that category - 15 points (golden/limits_a2.md).

For cascade runs, escalation is read from logs/service.jsonl (the brief requires the
escalation fraction to come from the logs), joined on run_id + source_row.

Only --set test decides pass/fail. --set tuning exists for comparison and self-tests.
Writes <a2-dir>/summary_<set>.md and .csv, and per run a confusion matrix csv/png.
"""
import argparse
import json
from pathlib import Path

import pandas as pd

from common import CATEGORIES, ROOT, read_log, wilson

TOP = "qwen2.5:7b"
# Service-log field names for the cascade (agreed with the service owner; change here only).
F_ESCALATED, F_FINAL, F_SMALL_CAT, F_SETTING = "escalated", "final_model", "small_category", "cascade_setting"

ap = argparse.ArgumentParser()
ap.add_argument("--set", choices=["test", "tuning"], default="test")
ap.add_argument("--a2-dir", default=str(ROOT / "results" / "a2" / "accuracy"))
ap.add_argument("--log", default=str(ROOT / "logs" / "service.jsonl"))
args = ap.parse_args()

A2 = Path(args.a2_dir)
split = pd.read_csv(ROOT / "golden" / "split_a2.csv")
rows = split.loc[split["set"] == args.set, ["row", "gold_label"]]


def load(run):
    """responses.csv restricted to the chosen set, with every set row present."""
    meta = json.loads((run / "meta.json").read_text())
    df = pd.read_csv(run / "responses.csv")[["row", "predicted", "status"]]
    df = rows.merge(df, on="row", how="left")
    missing = int(df["status"].isna().sum())
    df["predicted"] = df["predicted"].where(df["status"] == 200).fillna("ERROR")
    df["correct"] = df["predicted"] == df["gold_label"]
    return meta, df, missing


def counts(df):
    out = {"overall": (int(df.correct.sum()), len(df))}
    for c in CATEGORIES:
        g = df[df.gold_label == c]
        out[c] = (int(g.correct.sum()), len(g))
    return out


pct = lambda k, n: 100 * k / n if n else float("nan")

# --- configurations: reused A1 single models, then A2 runs ---------------------------
configs = []
for run in sorted(p for p in (ROOT / "results" / "accuracy").iterdir() if (p / "responses.csv").exists()):
    meta, df, missing = load(run)
    configs.append({"name": f"{meta['model']} alone", "source": f"A1 record reused ({run.name})",
                    "meta": meta, "df": df, "missing": missing, "cascade": False})
if A2.exists():
    for run in sorted(p for p in A2.iterdir() if (p / "responses.csv").exists()):
        meta, df, missing = load(run)
        name = meta.get("config") or f"{meta['model']} alone"
        if meta.get("setting"):
            name += f" [{meta['setting']}]"
        configs.append({"name": name, "source": f"A2 run ({run.name})", "meta": meta, "df": df,
                        "missing": missing, "cascade": bool(meta.get("cascade") or meta.get("setting")),
                        "dir": run})

ref = next(c for c in configs if c["meta"]["model"] == TOP and c["source"].startswith("A1"))
top = counts(ref["df"])
lim_overall = pct(*top["overall"]) - 10
lim_cat = {c: pct(*top[c]) - 15 for c in CATEGORIES}

# --- score -------------------------------------------------------------------------------
summary, sections = [], []
for cfg in configs:
    df, s = cfg["df"], counts(cfg["df"])
    k, n = s["overall"]
    lo, hi = wilson(k, n)
    ok_overall = pct(k, n) >= lim_overall - 1e-9
    fails = [c for c in CATEGORIES if pct(*s[c]) < lim_cat[c] - 1e-9]
    is_ref = cfg is ref
    rec = {"configuration": cfg["name"], "source": cfg["source"], "n": n, "correct": k,
           "accuracy": round(k / n, 4), "ci95": f"{lo:.1%}-{hi:.1%}",
           "passes_overall": ok_overall, "failed_categories": "; ".join(fails),
           "verdict": "reference" if is_ref else ("PASS" if ok_overall and not fails else "fail"),
           "missing_rows": cfg["missing"], "errors": int((df.predicted == "ERROR").sum())}
    for c in CATEGORIES:
        rec[f"{c} (k/n)"] = "%d/%d" % s[c]

    # Cascade: escalation from the service log, joined on run_id + source_row.
    if cfg["cascade"]:
        log = {e.get("source_row"): e for e in read_log(cfg["meta"]["run_id"], path=args.log)
               if e.get("path") == "/tickets" and e.get("method") == "POST"}
        df = df.assign(escalated=df.row.map(lambda r: log.get(r, {}).get(F_ESCALATED)),
                       final_model=df.row.map(lambda r: log.get(r, {}).get(F_FINAL)),
                       small_category=df.row.map(lambda r: log.get(r, {}).get(F_SMALL_CAT)),
                       log_category=df.row.map(lambda r: log.get(r, {}).get("category")))
        no_log = int(df.escalated.isna().sum())
        esc = df[df.escalated == True]  # noqa: E712  (values come from JSON)
        kept = df[df.escalated == False]  # noqa: E712
        small_wrong = df.small_category != df.gold_label
        mismatch = int(((df.log_category != df.predicted) & (df.predicted != "ERROR")).sum())
        rec.update({
            "escalated": len(esc), "escalation_fraction": round(len(esc) / n, 4),
            "acc_escalated": "%d/%d" % (esc.correct.sum(), len(esc)),
            "acc_not_escalated": "%d/%d" % (kept.correct.sum(), len(kept)),
            "small_errors_caught": int((small_wrong & (df.escalated == True)).sum()),  # noqa: E712
            "small_errors_slipped": int((small_wrong & (df.escalated == False)).sum()),  # noqa: E712
            "log_lines_missing": no_log, "log_category_mismatches": mismatch,
        })
        cfg["df"] = df

    # Confusion matrix for A2 runs (A1 runs already have theirs on the full golden set).
    if "dir" in cfg:
        labels_pred = CATEGORIES + sorted(set(df.predicted) - set(CATEGORIES))
        cm = pd.crosstab(pd.Categorical(df.gold_label, CATEGORIES), pd.Categorical(df.predicted, labels_pred),
                         dropna=False, rownames=["gold"], colnames=["predicted"])
        cm.to_csv(cfg["dir"] / f"confusion_matrix_{args.set}.csv")
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
                    if cm.values[i, j]:
                        ax.text(j, i, cm.values[i, j], ha="center", va="center", fontsize=8,
                                color="white" if cm.values[i, j] > cm.values.max() / 2 else "black")
            ax.set_xlabel("Predicted"); ax.set_ylabel("Golden label")
            ax.set_title(f"{cfg['name']}  {k}/{n} = {k / n:.1%} ({args.set} set)")
            fig.tight_layout(); fig.savefig(cfg["dir"] / f"confusion_matrix_{args.set}.png", dpi=160)
            plt.close(fig)
        except ImportError:
            pass
    summary.append(rec)

# --- write ---------------------------------------------------------------------------------
A2.mkdir(parents=True, exist_ok=True)
pd.DataFrame(summary).to_csv(A2 / f"summary_{args.set}.csv", index=False)

k, n = top["overall"]
L = [f"# A2 accuracy on the {args.set} set ({len(rows)} tickets)", "",
     f"Reference: `{TOP}` alone, {k}/{n} = {pct(k, n):.1f}%. "
     f"**Overall limit {lim_overall:.1f}%**; per category: reference - 15 points.", ""]
if args.set != "test":
    L += ["> Tuning set: for comparison only. Pass/fail is decided on the test set.", ""]
L += ["| Configuration | Overall | Verdict | " + " | ".join(CATEGORIES) + " |",
      "|---|---|---|" + "---|" * len(CATEGORIES)]
small = [f"{c} ({top[c][1]} tickets, 1 ticket = {100 / top[c][1]:.1f} pts)" for c in CATEGORIES if top[c][1] < 10]
L.append("| *limit* | " + f"*{lim_overall:.1f}%*" + " | | " +
         " | ".join(f"*{lim_cat[c]:.1f}%*" for c in CATEGORIES) + " |")
for rec in summary:
    cells = []
    for c in CATEGORIES:
        ck, cn = map(int, rec[f"{c} (k/n)"].split("/"))
        mark = " ✗" if c in rec["failed_categories"].split("; ") else ""
        cells.append(f"{pct(ck, cn):.0f}% ({ck}/{cn}){mark}")
    verdict = rec["verdict"] + (f": {rec['failed_categories']}" if rec["failed_categories"] and rec["verdict"] == "fail" else "")
    overall = f"{pct(rec['correct'], rec['n']):.1f}% ({rec['correct']}/{rec['n']}){'' if rec['passes_overall'] else ' ✗'}"
    L.append(f"| {rec['configuration']} | {overall} | {verdict} | " + " | ".join(cells) + " |")
if small:
    L += ["", "Too small for the 15-point limit to be a fair test (one ticket decides it): " + "; ".join(small) + "."]

casc = [r for r in summary if "escalated" in r]
if casc:
    L += ["", "## Cascade escalation (from logs/service.jsonl)", "",
          "| Configuration | Escalated | Accuracy escalated | Accuracy not escalated | "
          "Small-model errors caught / slipped | Log check |", "|---|---|---|---|---|---|"]
    for r in casc:
        chk = "ok" if not r["log_lines_missing"] and not r["log_category_mismatches"] else \
            f"{r['log_lines_missing']} missing, {r['log_category_mismatches']} mismatched"
        L.append(f"| {r['configuration']} | {100 * r['escalation_fraction']:.1f}% ({r['escalated']}/{r['n']}) | "
                 f"{r['acc_escalated']} | {r['acc_not_escalated']} | "
                 f"{r['small_errors_caught']} / {r['small_errors_slipped']} | {chk} |")
bad = [r for r in summary if r["missing_rows"] or r["errors"]]
if bad:
    L += ["", "Missing rows or HTTP errors (scored as wrong): " +
          "; ".join(f"{r['configuration']}: {r['missing_rows']} missing, {r['errors']} errors" for r in bad)]
(A2 / f"summary_{args.set}.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("\n".join(L))
