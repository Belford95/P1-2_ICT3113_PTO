# Predictions vs Actual: Accuracy

For Slide 11 (golden-set coordinator writes it up). Predictions are quoted from `predictions/prediction_record.md` (committed 2026-10-02, before any accuracy run). Actuals are from `results/accuracy/summary.csv` and each run's `confusion_matrix.csv` / `per_category.csv` (n = 173, runs of 2026-10-06, log reconciliation 173/173 with 0 mismatches for all four).

Latency and bottleneck predictions are **not** assessed here: they need the load-test `.jtl` results.

## 1. Overall accuracy

| Model | Predicted | Actual | 95% CI | Predicted value inside CI? | Gap |
|---|---|---|---|---|---|
| `llama3.2:1b` | ~55% | **45.1%** | 37.9–52.5% | **No** (above the whole interval) | -10 pts |
| `llama3.2:3b` | ~68% | **63.0%** | 55.6–69.8% | Yes | -5 pts |
| `phi4-mini` | ~72% | **78.6%** | 71.9–84.1% | Yes (just) | +7 pts |
| `qwen2.5:7b` | ~78% | **80.3%** | 73.8–85.6% | Yes | +2 pts |

- Ranking predicted: qwen > phi4-mini > 3b > 1b. Actual ranking is the same.
- The record said any model below ~50% would be a meaningful miss: `llama3.2:1b` is that miss (45.1%).
- phi4-mini vs qwen2.5:7b: predicted gap 6 pts, actual 1.7 pts, and their intervals overlap almost completely, so at n=173 they are not statistically separable on overall accuracy. 1b < 3b < {phi4-mini, qwen} is the only ordering the data supports.

## 2. Hardest categories

Per-category accuracy (recall) per model, with the gap to that model's overall accuracy in brackets:

| Category (n) | 1b (45.1%) | 3b (63.0%) | phi4-mini (78.6%) | qwen2.5:7b (80.3%) |
|---|---|---|---|---|
| Credit reporting (41) | 75.6% (+30.5) | 90.2% (+27.2) | 82.9% (+4.3) | 75.6% (-4.7) |
| Debt collection (18) | 72.2% (+27.1) | 38.9% (-24.1) | 88.9% (+10.3) | 77.8% (-2.5) |
| Mortgage (22) | 63.6% (+18.5) | 86.4% (+23.4) | 90.9% (+12.3) | 95.5% (+15.2) |
| Credit card (17) | 23.5% (-21.6) | 64.7% (+1.7) | 64.7% (-13.9) | 88.2% (+7.9) |
| Bank account or service (27) | 25.9% (-19.2) | 44.4% (-18.6) | 96.3% (+17.7) | 88.9% (+8.6) |
| Consumer loan (25) | 32.0% (-13.1) | 72.0% (+9.0) | 84.0% (+5.4) | 92.0% (+11.7) |
| Money transfer or service (23) | **4.3% (-40.8)** | **21.7% (-41.3)** | **34.8% (-43.8)** | **47.8% (-32.5)** |

| Prediction (frozen record) | What happened | Verdict |
|---|---|---|
| **Mortgage vs Consumer loan is the hardest pair**; both categories at least 15 pts below overall | Mortgage was **above** overall for all four models (+12 to +23 pts) and the best category for the two strongest. Consumer loan was below overall only for 1b (-13). Confusions between the two are tiny: 3, 4, 2 and 1 tickets (1b, 3b, phi4-mini, qwen). | **Wrong** |
| **Credit reporting about 10 pts below overall** when it is the true label, but it pulls in wrong predictions from other categories | Recall was above overall for 1b (+30), 3b (+27) and phi4-mini (+4), below only for qwen (-5): the "10 pts below" figure is wrong. The "pulls in wrong predictions" part is **right** for the small models: 1b predicted Credit reporting for 91 of 173 tickets (true count 41), 3b for 80. | **Half right** |
| **Money transfer vs Bank account: smaller gap, 5-8 pts below overall** | Money transfer is the worst category for every model, 32-44 pts below overall (4-6x the predicted gap). The direction was right and the size badly wrong. | **Right pair, wrong size** |
| **Easiest: Credit card and Bank account** | True for phi4-mini and qwen on Bank account (96%, 89%) and for qwen on Credit card (88%). For 1b and 3b they were among the worst (Credit card 24%, Bank account 26% / 44%). | **Only for the larger models** |

## 3. What the confusion matrices show

Counts are tickets out of the gold category's total.

- **Money transfer or service is almost never predicted**, but when it is, it is nearly always right (precision 100% / 100% / 100% / 92%). The models' failure is under-prediction. Where its tickets went:
  - 1b: 11 of 23 to Credit reporting, 4 to Credit card.
  - 3b: 10 to Credit reporting, 4 to Bank account.
  - phi4-mini: **13 to Bank account** (8 correct).
  - qwen2.5:7b: 8 to Bank account (11 correct).
  So the pair I predicted (Money transfer vs Bank account) is the main confusion for the two strongest models, and the small models send it to Credit reporting instead.
- **Small models dump tickets into Credit reporting.** 1b: 12 of 17 Credit card, 14 of 27 Bank account and 15 of 25 Consumer loan tickets were labelled Credit reporting. 3b: 11 of 18 Debt collection tickets (recall 38.9%). This inflates Credit reporting's recall and wrecks its precision (34% for 1b, 46% for 3b).
- **Credit reporting vs Debt collection** was my original (protocol-only) hardest pair, which I demoted after seeing the human disagreements. For the models it is real: 3b sends 11 of 18 Debt collection tickets to Credit reporting, 1b sends 7 of 41 the other way, qwen confuses them in both directions (4 and 3). The record's revision away from this pair was a mistake for model difficulty, even though it was reasonable for human difficulty.
- **Human disagreement did not predict model difficulty.** The 9 annotator disagreements were concentrated on Mortgage/Consumer loan; the models barely confuse those. The models fail where the protocol's rules supply knowledge the prompt does not (for example "payment apps and wallets are Money transfer").

## 4. Explanations that are hypotheses, not findings

None of these were tested; they are candidates for Slide 11 wording, flagged as such:

- The service prompt lists only the 7 category names, with no definitions (`docs/service_design.md`), so a model has no way to know the protocol's payment-app rule. This fits the Money transfer result but was not tested.
- "Credit reporting" is the first name in the prompt's category list. The small models' pull towards it could be a position effect. Testing this would need a re-run with the order changed, which is outside Assignment 1.

## 5. Single-request latency (from the sequential accuracy runs)

The record predicted single-request p99 latency per model. The accuracy runs send one ticket at a time, so they give a like-for-like check of that prediction (not of R1/R3, which need open-loop load tests). Computed from `client_ms` in each run's `responses.csv` (n = 173, 0 errors, model already warm):

| Model | Predicted p99 | Actual p50 | Actual p95 | Actual p99 | Predicted / actual p99 |
|---|---|---|---|---|---|
| `llama3.2:1b` | ~4 s | 0.98 s | 1.74 s | **1.98 s** | 2.0x too high |
| `llama3.2:3b` | ~6 s | 1.75 s | 3.14 s | **3.78 s** | 1.6x too high |
| `phi4-mini` | ~7 s | 2.21 s | 3.94 s | **4.49 s** | 1.6x too high |
| `qwen2.5:7b` | ~14 s | 3.82 s | 7.05 s | **8.22 s** | 1.7x too high |

- The ordering and rough scaling were right; every figure was 1.6-2.0x too pessimistic. The weakest assumption was the effective memory bandwidth (50 GB/s) and the prefill multiplier (4x decode).
- Latency tracks ticket length almost perfectly (correlation 0.97-0.98 between narrative characters and latency, all four models), so prompt processing dominates and output generation is negligible, as the prediction assumed.
- **Machine.** These runs used `localhost`, so they ran on the service host: Belford95's laptop, which hosts Docker and Ollama (team confirmation). This is the AMD Ryzen 7 7745HX host the prediction assumed (CPU-only confirmed, Ollama 0.35.0), so the comparison is like for like.

## 6. Caveats

- n = 173 and the categories are uneven (Credit card 17, Debt collection 18, Credit reporting 41). One ticket moves a small category by about 6 pts, so per-category figures for those are noisy.
- Per-category differences between phi4-mini and qwen2.5:7b (for example Money transfer 34.8% vs 47.8%, i.e. 8 vs 11 of 23) are within noise.
- Accuracy is deterministic here (temperature 0, fixed seed), so these are single runs of one fixed configuration, not repeated measurements.
