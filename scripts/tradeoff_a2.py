"""A2 trade-off chart (slide 6): test-set accuracy vs p50 latency, one point per speed-tested
configuration and setting, with the overall accuracy limit drawn as a line.

Usage: python scripts/tradeoff_a2.py [--acc results/a2/accuracy/summary_test.csv]
                                     [--speed results/a2/speed/summary.csv]
                                     [--map SPEED_CONFIG=ACCURACY_CONFIGURATION ...]
                                     [--out results/a2/tradeoff]

Inputs are the outputs of accuracy_report_a2.py and analyze_a2.py, so every plotted value
traces back to the .jtl files and service logs. Speed configs are matched to accuracy rows
automatically (single model: "qwen2.5-7b" <-> "qwen2.5:7b alone"; cascade: the setting tag,
e.g. "cascade-s1" <-> "... [s1 ...]"); pass --map when that is ambiguous.

x = mean of the per-run p50s (whiskers: min-max across runs); y = test-set accuracy
(whiskers: 95% Wilson interval). Filled marker = passes both A2 limits; hollow = fails.
Configurations that were not speed-tested (single models failing accuracy) have no latency
and are listed under the chart, not plotted. Writes <out>.png and <out>.csv.
"""
import argparse
import re

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from common import ROOT  # noqa: E402

INK, INK_2, SERIES, SURFACE, GRID = "#0b0b0b", "#52514e", "#2a78d6", "#fcfcfb", "#e4e3df"

ap = argparse.ArgumentParser()
ap.add_argument("--acc", default=str(ROOT / "results" / "a2" / "accuracy" / "summary_test.csv"))
ap.add_argument("--speed", default=str(ROOT / "results" / "a2" / "speed" / "summary.csv"))
ap.add_argument("--map", nargs="*", default=[], help="speed_config=accuracy configuration")
ap.add_argument("--out", default=str(ROOT / "results" / "a2" / "tradeoff"))
args = ap.parse_args()

acc = pd.read_csv(args.acc)
speed = pd.read_csv(args.speed)
explicit = dict(m.split("=", 1) for m in args.map)


def match(cfg):
    if cfg in explicit:
        hits = acc[acc.configuration == explicit[cfg]]
    else:
        tag = re.search(r"\bs\d+\b", cfg.replace("-", " "))
        if cfg.lower().startswith("cascade") and tag:
            hits = acc[acc.configuration.str.contains(r"\[" + tag.group(0) + r"\b", regex=True)]
        else:
            hits = acc[acc.configuration.str.replace(":", "-").str.replace(" alone", "") == cfg]
    if len(hits) != 1:
        raise SystemExit(f"speed config '{cfg}' matched {len(hits)} accuracy rows; use --map {cfg}=<configuration>")
    return hits.iloc[0]


limit = None
pts = []
for s in speed.itertuples():
    a = match(s.config)
    lo, hi = (float(x.strip("%")) for x in a.ci95.split("-"))
    pts.append({"label": a.configuration, "speed_config": s.config,
                "p50_s": s.p50_mean_ms / 1000, "p50_min_s": s.p50_min_ms / 1000, "p50_max_s": s.p50_max_ms / 1000,
                "acc_pct": 100 * a.correct / a.n, "ci_lo": lo, "ci_hi": hi, "correct": a.correct, "n": a.n,
                "verdict": a.verdict, "failed_categories": a.failed_categories if isinstance(a.failed_categories, str) else ""})
p = pd.DataFrame(pts)
ref = acc[acc.verdict == "reference"].iloc[0]
limit = 100 * ref.correct / ref.n - 10
p.to_csv(args.out + ".csv", index=False)

fig, ax = plt.subplots(figsize=(8, 4.8), dpi=200, facecolor=SURFACE)
ax.set_facecolor(SURFACE)
ax.axhline(limit, color=INK_2, lw=1.2, ls=(0, (5, 4)), zorder=1)
ax.text(1.0, limit, f"  overall limit {limit:.1f}%", transform=ax.get_yaxis_transform(),
        va="center", ha="left", fontsize=8.5, color=INK_2, clip_on=False)
for r in p.itertuples():
    passes = r.verdict in ("PASS", "reference")
    ax.errorbar(r.p50_s, r.acc_pct,
                xerr=[[r.p50_s - r.p50_min_s], [r.p50_max_s - r.p50_s]],
                yerr=[[r.acc_pct - r.ci_lo], [r.ci_hi - r.acc_pct]],
                fmt="none", ecolor=SERIES, elinewidth=1, alpha=0.45, capsize=0, zorder=2)
    ax.plot(r.p50_s, r.acc_pct, marker="o", ms=9, mec=SURFACE, mew=2, zorder=4,
            mfc=SERIES if passes else SURFACE, color=SERIES)
    if not passes:  # hollow marker: ring in the series colour inside the surface gap
        ax.plot(r.p50_s, r.acc_pct, marker="o", ms=7, mfc=SURFACE, mec=SERIES, mew=2, zorder=5)
    status = {"reference": "reference", "PASS": "passes limits"}.get(r.verdict, "fails: " + (r.failed_categories or "overall"))
    setting = re.search(r"[Ss]etting[ -]?(\d+)", r.label)
    name = f"Cascade setting {setting.group(1)}" if setting and "alone" not in r.label else r.label
    # Points can sit close together: the leftmost label goes left of its point, the rest
    # alternate below / above to the right.
    rank = int(p.p50_s.rank(method="first")[r.Index]) - 1
    xy, ha, va = ((-12, 6), "right", "bottom") if rank == 0 else \
        (((10, -10), "left", "top") if rank % 2 else ((10, 8), "left", "bottom"))
    ax.annotate(f"{name}\n{r.acc_pct:.1f}% ({r.correct}/{r.n}), p50 {r.p50_s:.2f} s\n{status}",
                (r.p50_s, r.acc_pct), xytext=xy, textcoords="offset points",
                fontsize=8, color=INK, ha=ha, va=va)
ax.set_xlabel("p50 latency (s), mean of 3 runs; whiskers min–max across runs", fontsize=9, color=INK_2)
ax.set_ylabel("Test-set accuracy (%); whiskers 95% interval", fontsize=9, color=INK_2)
ax.set_title("Accuracy vs latency per configuration (filled = passes both A2 limits)",
             fontsize=10.5, color=INK, loc="left")
ax.grid(True, color=GRID, lw=0.8)
ax.set_axisbelow(True)
for side in ("top", "right"):
    ax.spines[side].set_visible(False)
for side in ("left", "bottom"):
    ax.spines[side].set_color(GRID)
ax.tick_params(colors=INK_2, labelsize=8.5)
ax.set_xlim(left=0, right=max(p.p50_max_s.max(), p.p50_s.max()) * 1.45)
ymin = min(p.ci_lo.min(), limit) - 5
ax.set_ylim(max(ymin, 0), min(max(p.ci_hi.max(), limit) + 6, 100))
not_tested = acc[~acc.configuration.isin(p.label)]
if len(not_tested):
    fig.text(0.01, 0.01, "Not speed-tested (fail accuracy limits): " + "; ".join(
        f"{c} {100 * k / n:.1f}% ({k}/{n})" for c, k, n in zip(not_tested.configuration, not_tested.correct, not_tested.n)),
        fontsize=7.5, color=INK_2)
fig.tight_layout(rect=(0, 0.04, 1, 1))
fig.savefig(args.out + ".png", facecolor=SURFACE)
print(p.round(3).to_string(index=False))
print("wrote", args.out + ".png")
