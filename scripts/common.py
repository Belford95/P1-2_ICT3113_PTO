import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_FILE = ROOT / "logs" / "service.jsonl"
CATEGORIES = ["Credit reporting", "Debt collection", "Mortgage", "Credit card",
              "Bank account or service", "Consumer loan", "Money transfer or service"]


def slug(s):
    return re.sub(r"[^A-Za-z0-9.]+", "-", s).strip("-")


def read_log(run_id=None, path=LOG_FILE):
    """Yield service log entries, optionally only those tagged with run_id (or run_id prefix ending in '*')."""
    with open(path, encoding="utf-8-sig") as f:  # tolerate a BOM written by PowerShell
        for line in f:
            if not line.strip():
                continue
            e = json.loads(line)
            rid = e.get("run_id", "")
            if run_id is None or rid == run_id or (run_id.endswith("*") and rid.startswith(run_id[:-1])):
                yield e


def wilson(k, n, z=1.96):
    """95% Wilson score interval for a proportion."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (c - h, c + h)
