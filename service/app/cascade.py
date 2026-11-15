"""Configuration of POST /tickets: a single model, or the A2 cascade.

The cascade implements `docs/escalation_rule.md` exactly:

    small = classify(narrative, SMALL_MODEL)
    if small is not a valid category or small is in the setting's escalation list:
        final = classify(narrative, LARGE_MODEL)   # qwen's answer is final
    else:
        final = small

Nothing else is consulted: no ticket length, no confidence, no second opinion.
Set by environment variables, so a configuration change needs no code change:

    MODE=single   MODEL=<tag>                                  (Assignment 1 behaviour)
    MODE=cascade  SMALL_MODEL=<tag> LARGE_MODEL=<tag> CASCADE_SETTING=1|2
"""
import os

from . import classifier
from .classifier import CATEGORIES, ClassificationError

MODE = os.getenv("MODE", "single").strip().lower()
SMALL_MODEL = os.getenv("SMALL_MODEL", "").strip()
LARGE_MODEL = os.getenv("LARGE_MODEL", "").strip()
CASCADE_SETTING = os.getenv("CASCADE_SETTING", "").strip()

# docs/escalation_rule.md section 2. Chosen from the tuning set only.
ESCALATE_ON = {
    "1": {"Bank account or service"},
    "2": {"Bank account or service", "Consumer loan"},
}

# The label returned to the caller. One fixed string for every ticket, so the caller
# cannot tell which model answered (assignment Step 2); the real model is logged only.
if MODE == "cascade":
    CONFIG_LABEL = os.getenv("CONFIG_LABEL") or f"cascade-setting-{CASCADE_SETTING}"
else:
    CONFIG_LABEL = os.getenv("CONFIG_LABEL") or classifier.MODEL


def describe() -> dict:
    """Configuration summary for GET /health, checked before every run."""
    d = {"mode": MODE, "config_label": CONFIG_LABEL, "num_ctx": classifier.NUM_CTX}
    if MODE == "cascade":
        d.update(small_model=SMALL_MODEL, large_model=LARGE_MODEL,
                 cascade_setting=CASCADE_SETTING,
                 escalate_on=sorted(ESCALATE_ON.get(CASCADE_SETTING, ())))
    else:
        d.update(model=classifier.MODEL)
    return d


def _check_config():
    if MODE not in ("single", "cascade"):
        raise ClassificationError(f"MODE must be 'single' or 'cascade', got {MODE!r}")
    if MODE == "cascade":
        if CASCADE_SETTING not in ESCALATE_ON:
            raise ClassificationError(
                f"CASCADE_SETTING must be one of {sorted(ESCALATE_ON)}, got {CASCADE_SETTING!r}")
        if not SMALL_MODEL or not LARGE_MODEL:
            raise ClassificationError("cascade needs both SMALL_MODEL and LARGE_MODEL")


def classify(narrative: str) -> dict:
    """Classify one ticket under the active configuration.

    Returns the final category plus the fields the service logs:
    final_model, escalated, cascade_setting, small_category, small_model_ms, large_model_ms.
    """
    _check_config()
    if MODE == "single":
        r = classifier.classify(narrative)
        return {"category": r["category"], "raw": r["raw"], "ollama": r["ollama"],
                "final_model": r["model"], "model_ms": round(r["model_ms"], 2),
                "escalated": False, "cascade_setting": None, "small_category": None,
                "small_model_ms": None, "large_model_ms": None}

    # --- cascade ---------------------------------------------------------------
    escalate_on = ESCALATE_ON[CASCADE_SETTING]
    small_ms = small_category = None
    try:
        small = classifier.classify(narrative, SMALL_MODEL)
        small_category = small["category"]
        small_ms = round(small["model_ms"], 2)
        # A valid category is one of the seven A1 names; anything else escalates
        # (docs/escalation_rule.md section 4).
        escalated = small_category not in CATEGORIES or small_category in escalate_on
    except ClassificationError as e:
        # The small model failing also escalates, so the rule is total.
        escalated = True
        small_category = f"ERROR: {e}"[:200]

    if not escalated:
        return {"category": small["category"], "raw": small["raw"], "ollama": small["ollama"],
                "final_model": SMALL_MODEL, "model_ms": small_ms,
                "escalated": False, "cascade_setting": CASCADE_SETTING,
                "small_category": small_category, "small_model_ms": small_ms, "large_model_ms": None}

    # Escalation: the large model's answer is final. If it fails, the request fails
    # (HTTP 502) rather than falling back, so failures stay visible in the error rate.
    large = classifier.classify(narrative, LARGE_MODEL)
    large_ms = round(large["model_ms"], 2)
    return {"category": large["category"], "raw": large["raw"], "ollama": large["ollama"],
            "final_model": LARGE_MODEL, "model_ms": (small_ms or 0) + large_ms,
            "escalated": True, "cascade_setting": CASCADE_SETTING,
            "small_category": small_category, "small_model_ms": small_ms, "large_model_ms": large_ms}
