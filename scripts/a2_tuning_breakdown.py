"""Assignment 2: what the cascade does to each escalated tuning-set ticket. TUNING ROWS ONLY.

Usage: python scripts/a2_tuning_breakdown.py

Reads golden/split_a2.csv and the A1 accuracy records (results/accuracy/*/responses.csv), keeps only
rows whose `set` is `tuning` (87 tickets), and replays the cascade phi4-mini -> qwen2.5:7b for both
candidate settings. Test-set rows are dropped immediately and never scored.

The simulation in docs/a2_cascade_simulation.md counts a small-model error as "caught" when it is
routed to qwen. This script separates routed from corrected: how many of those errors qwen answered
correctly, and how many correct small-model answers qwen broke.
Latency is an estimate from A1 sequential, unloaded timings (client_ms): not an A2 measurement.
"""
import glob

import numpy as np
import pandas as pd

from common import ROOT

split = pd.read_csv(ROOT / "golden" / "split_a2.csv")
tuning = set(split.loc[split["set"] == "tuning", "row"])
assert len(tuning) == 87


def load(tag):
    d = pd.read_csv(glob.glob(str(ROOT / "results" / "accuracy" / f"{tag}__*" / "responses.csv"))[0])
    return d[d["row"].isin(tuning)].set_index("row").sort_index()   # tuning only, filtered at load


phi, qwen = load("phi4-mini"), load("qwen2.5-7b")
phi_ok, qwen_ok = phi.predicted == phi.gold_label, qwen.predicted == qwen.gold_label
print(f"tuning accuracy alone: phi4-mini {phi_ok.sum()}/87, qwen2.5:7b {qwen_ok.sum()}/87")
print(f"alone, est. p50 / mean s: phi4-mini {phi.client_ms.median()/1000:.2f} / {phi.client_ms.mean()/1000:.2f}, "
      f"qwen2.5:7b {qwen.client_ms.median()/1000:.2f} / {qwen.client_ms.mean()/1000:.2f}")

print("\nper-category tuning accuracy, each model alone (gap = phi4-mini minus qwen, in points):")
for c in sorted(phi.gold_label.unique()):
    m = phi.gold_label == c
    a, b = (phi[m].predicted == c).mean() * 100, (qwen[m].predicted == c).mean() * 100
    print(f"  {c:26} n={m.sum():2d}  phi4-mini {a:5.1f}%  qwen {b:5.1f}%  gap {a-b:+5.1f}")

for name, cats in (("Setting 1", ["Bank account or service"]),
                   ("Setting 2", ["Bank account or service", "Consumer loan"])):
    esc = phi.predicted.isin(cats)
    final_ok = np.where(esc, qwen_ok, phi_ok)
    t = phi.client_ms.values / 1000 + np.where(esc, qwen.client_ms.values / 1000, 0)
    print(f"\n{name}: escalate when phi4-mini predicts {' or '.join(cats)}")
    print(f"  escalated {esc.sum()}/87 ({esc.mean():.0%}); cascade accuracy {final_ok.sum()}/87 = {final_ok.mean():.1%}")
    print(f"  accepted (not escalated) accuracy {(~esc & phi_ok).sum()}/{(~esc).sum()}; escalated accuracy {(esc & qwen_ok).sum()}/{esc.sum()}")
    print(f"  small-model errors routed to qwen: {(esc & ~phi_ok).sum()}; of those qwen answered correctly: {(esc & ~phi_ok & qwen_ok).sum()}")
    print(f"  correct small-model answers qwen broke: {(esc & phi_ok & ~qwen_ok).sum()}; small-model errors accepted (slipped): {(~esc & ~phi_ok).sum()}")
    print(f"  est. mean {t.mean():.2f} s, est. p50 {np.median(t):.2f} s")
    e = pd.DataFrame({"gold": phi.gold_label[esc], "phi": phi.predicted[esc], "qwen": qwen.predicted[esc]})
    wrong = e[e.gold != e.phi]
    print("  gold labels of the routed small-model errors:", wrong.gold.value_counts().to_dict())
    acc = pd.DataFrame({"gold": phi.gold_label[~esc], "phi": phi.predicted[~esc]})
    slip = acc[acc.gold != acc.phi]
    print("  slip-through: small-model errors accepted, by the category phi4-mini PREDICTED:", slip.phi.value_counts().to_dict())
    safe = acc[acc.phi.isin(["Credit reporting", "Debt collection", "Mortgage", "Money transfer or service"])]
    print(f"  of the {len(safe)} accepted answers in labels with tuning precision >= 86%, {(safe.gold != safe.phi).sum()} were wrong")
