"""A2 Step 2: simulate candidate cascade rules on the TUNING set only.

For each small model -> qwen2.5:7b pairing, replays the A1 accuracy records
(results/accuracy/*/responses.csv): the small model's answer is accepted unless
the rule escalates, in which case qwen's answer is used. Latency per ticket is
estimated as small-model time + (qwen time if escalated), from the A1 sequential
client_ms. This is a design aid, not a measurement: queueing, routing overhead
and A2 load conditions are ignored.

Usage: python scripts/a2_cascade_sim.py
Writes docs/a2_cascade_simulation.md
"""
import glob
import os
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1].as_posix()
CATS = ["Credit reporting", "Debt collection", "Mortgage", "Credit card",
        "Bank account or service", "Consumer loan", "Money transfer or service"]
LARGE = "qwen2.5-7b"
SMALL = ["phi4-mini", "llama3.2-3b", "llama3.2-1b"]

split = pd.read_csv(f"{REPO}/golden/split_a2.csv")
tune = split[split["set"] == "tuning"][["row", "gold_label"]]
chars = pd.read_csv(f"{REPO}/data/team_rows.csv").assign(chars=lambda d: d.narrative.str.len())[["row", "chars"]]
tune = tune.merge(chars, on="row")

resp = {}
for d in glob.glob(f"{REPO}/results/accuracy/*__*"):
    name = os.path.basename(d).split("__")[0]
    r = pd.read_csv(f"{d}/responses.csv")[["row", "predicted", "client_ms"]]
    resp[name] = r.rename(columns={"predicted": f"pred_{name}", "client_ms": f"ms_{name}"})
for r in resp.values():
    tune = tune.merge(r, on="row", how="left")
assert tune.notna().all().all() and len(tune) == 87


def evaluate(small, escalate):
    """escalate: boolean Series over tune rows."""
    final = tune[f"pred_{small}"].where(~escalate, tune[f"pred_{LARGE}"])
    ok = final == tune.gold_label
    ms = tune[f"ms_{small}"] + escalate * tune[f"ms_{LARGE}"]
    small_ok = tune[f"pred_{small}"] == tune.gold_label
    acc_kept = small_ok[~escalate]
    per_cat = {c: (int(ok[tune.gold_label == c].sum()), int((tune.gold_label == c).sum())) for c in CATS}
    return {
        "esc": int(escalate.sum()), "n": len(tune), "correct": int(ok.sum()),
        "mean_s": ms.mean() / 1000, "p50_s": ms.median() / 1000,
        "kept_ok": int(acc_kept.sum()), "kept_n": int((~escalate).sum()),
        # wrong small answers that escalation caught vs let through
        "caught": int((~small_ok & escalate).sum()), "slipped": int((~small_ok & ~escalate).sum()),
        "per_cat": per_cat,
    }


def row(label, e):
    pc = " | ".join(f"{k}/{n}" for k, n in e["per_cat"].values())
    kept = f"{100 * e['kept_ok'] / e['kept_n']:.0f}% ({e['kept_ok']}/{e['kept_n']})" if e["kept_n"] else "-"
    return (f"| {label} | {100 * e['esc'] / e['n']:.0f}% ({e['esc']}) | "
            f"{100 * e['correct'] / e['n']:.1f}% ({e['correct']}/{e['n']}) | {kept} | "
            f"{e['caught']} / {e['slipped']} | {e['mean_s']:.2f} | {e['p50_s']:.2f} | {pc} |")


HEAD = ("| Rule | Escalated | Cascade accuracy | Accepted-answer accuracy | Small errors caught / slipped | "
        "Est. mean s | Est. p50 s | " + " | ".join(CATS) + " |\n|" + "---|" * (7 + len(CATS)))

L = ["# Cascade simulation on the tuning set (87 tickets)", "",
     "Replays A1 accuracy records; latency = small-model time + qwen time when escalated "
     "(A1 sequential, unloaded timings). Design aid only: not an A2 measurement. "
     "Per-category cells are correct/total on the tuning set.", ""]

none = pd.Series(False, index=tune.index)
everything = pd.Series(True, index=tune.index)
L += ["## Reference points", "", HEAD]
for s in [LARGE] + SMALL:
    if s == LARGE:
        e = evaluate(SMALL[0], everything)  # qwen answers everything; time counted as phi4+qwen, so recompute
        ok = tune[f"pred_{LARGE}"] == tune.gold_label
        e.update(correct=int(ok.sum()), mean_s=tune[f"ms_{LARGE}"].mean() / 1000,
                 p50_s=tune[f"ms_{LARGE}"].median() / 1000, esc=0, kept_ok=0, kept_n=0, caught=0, slipped=0,
                 per_cat={c: (int(ok[tune.gold_label == c].sum()), int((tune.gold_label == c).sum())) for c in CATS})
        L.append(row(f"{LARGE} alone", e))
    else:
        L.append(row(f"{s} alone", evaluate(s, none)))

for s in SMALL:
    pred = tune[f"pred_{s}"]
    prec = {c: ((pred == c) & (pred == tune.gold_label)).sum() / max((pred == c).sum(), 1) for c in CATS}
    order = sorted(CATS, key=lambda c: (prec[c], c))  # least reliable predicted category first
    L += ["", f"## {s} -> {LARGE}: category-based (escalate when {s} predicts a listed category)", "",
          "Categories are added in order of the small model's tuning-set precision for that predicted label, "
          "least reliable first: " + ", ".join(f"{c} {100 * prec[c]:.0f}% (n={(pred == c).sum()})" for c in order), "",
          HEAD]
    for k in range(1, 5):
        esc_set = order[:k]
        L.append(row("escalate " + " + ".join(esc_set), evaluate(s, pred.isin(esc_set))))
    L += ["", f"## {s} -> {LARGE}: length-based (escalate when narrative > cut-off characters)", "", HEAD]
    for cut in [600, 800, 1000, 1300]:
        L.append(row(f"> {cut} chars", evaluate(s, tune.chars > cut)))
    wrong = pred != tune.gold_label
    L += ["", f"Does length predict {s} errors on tuning? mean chars of wrong answers "
          f"{tune.chars[wrong].mean():.0f} vs right {tune.chars[~wrong].mean():.0f}.", ""]

open(f"{REPO}/docs/a2_cascade_simulation.md", "w", encoding="utf-8").write("\n".join(L) + "\n")
print("\n".join(L))
