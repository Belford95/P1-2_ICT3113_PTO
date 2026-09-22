"""Pull candidate models into the Ollama container and record their exact tag + digest.

Usage (on the SUT, stack running): python scripts/pin_models.py <model tag> [<model tag> ...]
Writes results/model_pins.json and results/model_pins.md (the table for Slide 5).
"""
import json
import subprocess
import sys

import requests

from common import ROOT

OLLAMA = "http://localhost:11434"
models = sys.argv[1:]
if not models:
    raise SystemExit("give the candidate model tags, e.g. python scripts/pin_models.py <tag1> <tag2> <tag3>")
for m in models:
    print("pulling", m)
    subprocess.run(["docker", "exec", "ollama", "ollama", "pull", m], check=True)

tags = {t["name"]: t for t in requests.get(f"{OLLAMA}/api/tags").json()["models"]}
version = requests.get(f"{OLLAMA}/api/version").json()["version"]
pins = []
for m in models:
    name = m if ":" in m else m + ":latest"
    t = tags[name]
    show = requests.post(f"{OLLAMA}/api/show", json={"model": name}).json()
    lic = [ln for ln in (show.get("license") or "").splitlines() if ln.strip()]
    pins.append({"tag": name, "digest": t["digest"], "size_gb": round(t["size"] / 1e9, 2),
                 "parameter_size": t["details"].get("parameter_size"),
                 "quantization": t["details"].get("quantization_level"),
                 "family": t["details"].get("family"), "license_first_line": lic[0].strip() if lic else ""})
(ROOT / "results").mkdir(exist_ok=True)
(ROOT / "results" / "model_pins.json").write_text(json.dumps({"ollama_version": version, "models": pins}, indent=2))
md = [f"Ollama server version: {version}\n",
      "| Tag | Digest | Params | Quant | Size (GB) | Licence |", "|---|---|---|---|---|---|"]
md += [f"| {p['tag']} | `{p['digest'][:12]}` | {p['parameter_size']} | {p['quantization']} | "
       f"{p['size_gb']} | {p['license_first_line'][:50]} |" for p in pins]
(ROOT / "results" / "model_pins.md").write_text("\n".join(md))
print("\n".join(md))
