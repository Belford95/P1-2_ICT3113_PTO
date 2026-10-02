# Prediction Record

**Status: DRAFT**, owner: model/requirements owner. Written before any benchmark run, from reasoning and published/observed hardware behaviour only — no timing run has been taken on the benchmark host. Must be reviewed and signed off by the team, then committed together with the frozen golden set before the first benchmark run. Nothing here may change after that commit.

**Test host** (confirmed 2026-10-02): AMD Ryzen 7 7745HX, 8 cores / 16 threads @ 3.6 GHz, 15.5 GB RAM available to Docker, CPU-only confirmed (`ollama ps` showed 100% CPU despite an RTX 4060 being present), Ollama 0.35.0.

---

## 1. Bottleneck prediction

**Primary bottleneck: Ollama's inference queue.** `OLLAMA_NUM_PARALLEL=1` means Ollama processes exactly one request at a time; every concurrent request queues behind it (`docker-compose.yml`). As the ticket arrival rate approaches 1/S, where S is a model's per-request service time (section 2), queueing delay grows sharply (classic single-server-queue behaviour) — p95/p99 latency will diverge well before the error rate rises. This should show up first and worst for **`qwen2.5:7b`**, which has the longest predicted service time (~14 s) and therefore the lowest throughput ceiling (~257 tickets/hour in theory, 3600/14); it is the most likely candidate to breach the throughput requirement (R3, ≥120 tickets/hour) once real variance and overhead push its service time past ~30 s.

**Secondary bottleneck: `GET /search`.** It is an unindexed `LIKE '%q%'` full-table scan (`docs/service_design.md`). Its latency should grow with the number of stored tickets, independent of which model is active — so it may breach the mixed-load search requirement (R2) even on the fastest model, once the store holds a few thousand rows from sustained testing.

**Not expected to be a bottleneck:** SQLite writes (one row per ticket, trivial volume at this scale) and the FastAPI/uvicorn layer itself (1 worker is fine since the service spends almost all its time blocked waiting on Ollama, not on CPU work of its own).

---

## 2. Per-model predictions: accuracy and single-request latency

### Latency methodology (shown so the prediction can be checked, not just trusted)

CPU decoding is dominated by memory bandwidth: each generated token requires reading roughly the whole weight set from RAM, so tokens/second ≈ effective memory bandwidth ÷ model size. We assume **~50 GB/s effective bandwidth** for this host (dual-channel DDR5 laptop memory, assumed ~85-90 GB/s theoretical, ~55-60% practical efficiency for a memory-bound workload — this 50 GB/s figure is itself an assumption and the single biggest source of error in these predictions). Prompt processing (prefill) is compute-bound and parallelises across threads, so we assume it runs **~4x faster per token** than generation, a rough multiplier commonly observed in CPU llama.cpp-style inference.

Prompt size: ~70 tokens of fixed system prompt (`classifier.py`) + the ticket narrative. We use the **p99 narrative length from the workload model (~480 tokens)** as the prompt size, since the requirement (R1) is itself a p95/p99 claim — predicting from a typical-case prompt would understate tail latency. Total prompt ≈ **550 tokens**. Output is fixed-format JSON (observed in early smoke-test logs at 8 tokens for `{"category": "Credit card"}`); we use **10 tokens** as a safe round number.

| Model | Weights (GB) | Decode rate (tok/s) = 50/size | Prefill rate (tok/s) = 4x decode | Prefill time (550 tok) | Decode time (10 tok) | **Predicted p99 single-request latency** |
|---|---|---|---|---|---|---|
| `llama3.2:1b` | 1.32 | 37.9 | 151.6 | 3.6 s | 0.3 s | **~4 s** |
| `llama3.2:3b` | 2.02 | 24.8 | 99.2 | 5.5 s | 0.4 s | **~6 s** |
| `phi4-mini` | 2.49 | 20.1 | 80.4 | 6.8 s | 0.5 s | **~7 s** |
| `qwen2.5:7b` | 4.68 | 10.7 | 42.8 | 12.9 s | 0.9 s | **~14 s** |

This assumes the model is already loaded (`OLLAMA_KEEP_ALIVE: -1`), matching how `baseline_latency.py` and `accuracy_run.py` both warm up before timing. All four predictions are comfortably under the draft R1 requirement (p95 ≤ 60 s), so **latency alone should not eliminate any candidate** — the accuracy/throughput trade-off is expected to be the deciding factor, not raw single-request speed.

### Accuracy predictions

No candidate has seen the golden set or any category definitions beyond the 7 names (`docs/service_design.md`: zero-shot prompt, names only, no definitions, no examples). Predictions are based on general model capability at each size/family, scaled down for the fact this is genuinely zero-shot with no in-prompt category guidance:

| Model | Predicted overall accuracy | Reasoning |
|---|---|---|
| `llama3.2:1b` | **~55%** | Smallest model, 1.2B params; limited capacity to disambiguate close categories without definitions in-prompt. |
| `llama3.2:3b` | **~68%** | Same family/training as #1 at ~2.6x the parameters; expect a meaningful jump, not a proportional one (diminishing returns at this task size). |
| `phi4-mini` | **~72%** | Slightly larger than #2 and a different training recipe (Microsoft's small models are tuned for reasoning/instruction-following, which should help a classification task with no examples given). |
| `qwen2.5:7b` | **~78%** | Largest model and a third family; expected best overall, but not dramatically ahead of `phi4-mini` — diminishing returns on a 7-way classification task. |

**These numbers are deliberately specific so they can be shown wrong.** A result that places `phi4-mini` above `qwen2.5:7b`, or any model below ~50% / above ~85%, would be a meaningful miss worth explaining on Slide 11.

---

## 3. Hardest categories

The golden set is now frozen (173 tickets, `golden/agreement.md`): 95.0% inter-annotator agreement, Cohen's κ = 0.942. This gives **real evidence**, not just protocol speculation — the 9 actual disagreements between the two annotators (`golden/agreement.md` confusion matrix) are the strongest available signal for which categories are genuinely ambiguous, since even trained humans following a written protocol split on them. Using this real data (not a model benchmark, so using it here doesn't breach the freeze):

| Disagreement pair | Count | 
|---|---|
| Consumer loan vs. Mortgage | 2 |
| None/Unclear vs. Credit card | 2 |
| Credit reporting vs. Consumer loan | 1 |
| Debt collection vs. Credit reporting | 1 |
| Debt collection vs. Mortgage | 1 |
| Money transfer vs. Bank account | 1 |
| None/Unclear vs. Mortgage | 1 |

**Revised predictions** (superseding the protocol-only reasoning below, now that real reconciliation data exists):

1. **Mortgage vs. Consumer loan — predicted hardest pair for the models.** It is the single most frequent real human disagreement among the 7 named categories (2 of 9), and Mortgage is also the label most involved in disagreements overall (4 of 9, including the None/Unclear case). The HELOC edge case (protocol section 2.1) is the likely cause, and a zero-shot model has no way to know that rule. Predict both categories' per-category accuracy to land **at least 15 points below** that model's overall accuracy.
2. **Credit reporting involved in two different disagreements** (vs. Consumer loan, vs. Debt collection) despite being the largest category (41 of 173 tickets) — predict it pulls in a disproportionate share of wrong predictions from other categories in the confusion matrix, even if its own per-category accuracy stays reasonable (large categories are easier to get partially right by base rate). Predict **~10 points below** overall accuracy specifically where it's the *true* label being confused for something else, not where other tickets are wrongly predicted as it.
3. **Money transfer vs. Bank account** — only 1 real disagreement, but it matches the protocol's own flagged ambiguity (payment apps vs. deposit accounts in casual language); predict a smaller gap, **~5-8 points below** overall accuracy.

**Predicted easiest categories: Credit card and Bank account or service** — neither appears on either side of a real disagreement except one single None/Unclear boundary case for Credit card, suggesting both have fairly unambiguous vocabulary once a ticket clears the None/Unclear boundary.

<details>
<summary>Original protocol-only reasoning (kept for the record, now superseded by the real data above)</summary>

Before the golden set was frozen, the protocol's own disambiguation rules (`golden/labelling_protocol.md`, section 2.1) were the only available signal — the most rule-space was spent on Credit reporting vs. Debt collection, so that was predicted hardest. The real reconciliation data shows that pair occurred only once; Mortgage vs. Consumer loan was the actual most frequent disagreement, which the protocol also flagged but with less space devoted to it. This is itself worth keeping for Slide 11: protocol rule density was a weaker predictor of real difficulty than expected.

</details>

---

## 4. What would make these predictions wrong, and why that's useful

- If the 50 GB/s bandwidth assumption is badly off (e.g. real effective bandwidth is 30 GB/s, not 50), every latency prediction scales up proportionally — a clean, explicable miss.
- If `phi4-mini` underperforms `llama3.2:3b` despite being larger, that would suggest its training is weaker for this task than assumed.
- If per-category accuracy is roughly flat across categories (no pair standing out), that would suggest the protocol's hardest-case reasoning doesn't transfer to how models actually fail, which is itself a useful finding for Slide 11.
