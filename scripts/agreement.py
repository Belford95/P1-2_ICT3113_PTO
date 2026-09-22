"""Inter-annotator agreement on the independent label sheets.

Usage: python scripts/agreement.py            (reads golden/label_sheets/labels_*.xlsx|csv)

Writes
  golden/agreement.md        percent agreement, Cohen's kappa (each pair), Fleiss' kappa (>=3 annotators),
                             annotator-vs-annotator confusion table
  golden/disagreements.csv   every ticket where annotators differ, with empty
                             resolved_label / resolution_note / protocol_change columns to fill in
"""
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SHEETS = ROOT / "golden" / "label_sheets"


def load_sheets():
    labels = {}
    for p in sorted(SHEETS.glob("labels_*.*")):
        if p.name.startswith("~$"):
            continue
        name = p.stem.split("_", 1)[1]
        df = pd.read_excel(p) if p.suffix == ".xlsx" else pd.read_csv(p)
        df["label"] = df["label"].astype(str).str.strip()
        missing = df[df["label"].isin(["", "nan"])]
        if len(missing):
            raise SystemExit(f"{p.name}: {len(missing)} unlabelled rows, e.g. {missing['row'].head().tolist()}")
        labels[name] = df.set_index("row")["label"]
    if len(labels) < 2:
        raise SystemExit("need at least two completed label sheets")
    return pd.DataFrame(labels)


def cohen_kappa(a, b):
    cats = sorted(set(a) | set(b))
    po = np.mean(a.values == b.values)
    pe = sum((a == c).mean() * (b == c).mean() for c in cats)
    return po, (po - pe) / (1 - pe) if pe < 1 else 1.0


def fleiss_kappa(df):
    cats = sorted(set(df.values.ravel()))
    counts = np.array([[(row == c).sum() for c in cats] for row in df.values])
    n = df.shape[1]
    p_i = ((counts ** 2).sum(1) - n) / (n * (n - 1))
    p_j = counts.sum(0) / counts.sum()
    pe = (p_j ** 2).sum()
    return (p_i.mean() - pe) / (1 - pe)


def md(obj):
    """Markdown table without the optional 'tabulate' dependency."""
    df = obj.to_frame() if isinstance(obj, pd.Series) else obj
    head = "| " + " | ".join([str(df.index.name or "")] + [str(c) for c in df.columns]) + " |"
    sep = "|" + "---|" * (len(df.columns) + 1)
    body = ["| " + " | ".join([str(i)] + [str(v) for v in r]) + " |" for i, r in zip(df.index, df.values)]
    return "\n".join([head, sep] + body)


def interpret(k):
    # Landis & Koch (1977) bands
    for lim, word in [(0, "poor"), (.2, "slight"), (.4, "fair"), (.6, "moderate"), (.8, "substantial")]:
        if k <= lim:
            return word
    return "almost perfect"


def main():
    labels = load_sheets()
    names = list(labels.columns)
    lines = [f"# Inter-annotator agreement\n", f"Tickets: {len(labels)}  |  Annotators: {', '.join(names)}\n"]
    lines.append("| Pair | % agreement | Cohen's kappa | Interpretation (Landis & Koch) |\n|---|---|---|---|")
    for x, y in combinations(names, 2):
        po, k = cohen_kappa(labels[x], labels[y])
        lines.append(f"| {x} vs {y} | {po:.1%} | {k:.3f} | {interpret(k)} |")
    if len(names) >= 3:
        fk = fleiss_kappa(labels)
        lines.append(f"\nFleiss' kappa (all {len(names)} annotators): **{fk:.3f}** ({interpret(fk)})")

    x, y = names[0], names[1]
    lines.append(f"\n## Confusion between {x} (rows) and {y} (columns)\n")
    lines.append(md(pd.crosstab(labels[x], labels[y])))

    disagree = labels[labels.nunique(axis=1) > 1].copy()
    lines.append(f"\n## Disagreements: {len(disagree)} of {len(labels)} tickets\n")
    per_cat = pd.concat([labels[n] for n in names]).loc[lambda s: s.index.isin(disagree.index)].value_counts()
    lines.append("Labels involved in disagreements:\n\n" + md(per_cat))
    (ROOT / "golden" / "agreement.md").write_text("\n".join(lines), encoding="utf-8")

    team = pd.read_csv(ROOT / "data" / "team_rows.csv").set_index("row")
    out = disagree.add_prefix("label_")
    out.insert(0, "narrative", team.loc[out.index, "narrative"])
    out["resolved_label"] = ""
    out["resolution_note"] = ""
    out["protocol_change"] = ""
    dpath = ROOT / "golden" / "disagreements.csv"
    if dpath.exists():
        print(f"NOTE: {dpath.name} exists and was not overwritten (it may hold resolutions). Delete it to regenerate.")
    else:
        out.to_csv(dpath)
    print("\n".join(lines[:8]))


if __name__ == "__main__":
    main()
