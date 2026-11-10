# Prediction record (Assignment 2)

**Status: DRAFT.** Owner: Zhi Ming. To be committed with `docs/escalation_rule.md` before any Assignment 2 benchmark run (gate: Tue 17 Nov). After that commit it is not changed.

**Basis.** Every figure below comes from the **tuning set** (87 tickets, odd positions in `golden/split_a2.csv`), via `docs/a2_cascade_simulation.md` and `scripts/a2_tuning_breakdown.py`. The only test-derived inputs used are the client's limits in `golden/limits_a2.md` (overall at least 74.9%; each category at least qwen's test score minus 15 points), because they define "qualifying". No test-set score was used to choose or predict anything else. The test set is 86 tickets.

**Setup.** Same laptop as Assignment 1 (AMD Ryzen 7 7745HX, 15.46 GiB to Docker, CPU only), Ollama 0.35.0, the same four digests. One deliberate change: `OLLAMA_MAX_LOADED_MODELS` 1 to 2 (`docs/a2_memory_check.md`).

## 1. The fastest qualifying configuration

The assignment asks us to check every Assignment 1 model alone, not assume. Reading each configuration against the tuning set (qwen's tuning accuracy, 75.9%, stands in for the reference here; the real limits come from qwen's test-set score in `golden/limits_a2.md`):

| Configuration | Tuning accuracy | Predicted to qualify? |
|---|---|---|
| qwen2.5:7b alone | 66/87 (75.9%) | Yes: it is the reference |
| phi4-mini alone | 68/87 (78.2%) | Overall limit yes. **Per-category limit no:** on Money transfer it scores 2/11 (18.2%) against qwen's 4/11 (36.4%), 18.2 points lower, beyond the 15-point tolerance |
| llama3.2:3b alone | 52/87 (59.8%) | No: 16.1 points below qwen overall, beyond 10 |
| llama3.2:1b alone | 39/87 (44.8%) | No: 31.1 points below qwen overall |
| Setting 1 | 69/87 (79.3%) | Yes |
| Setting 2 | 69/87 (79.3%) | Yes, if Setting 1 does |

Single-model test-set scores were computed in `golden/limits_a2.md` (reusing the Assignment 1 records, as Step 4 allows) before this record was written. They are results, not predictions; the table above is read from the tuning set only.

**Prediction: Setting 1** (phi4-mini, escalating to qwen2.5:7b when phi4-mini predicts Bank account or service). Among all configurations predicted to qualify, it is predicted to be the fastest. phi4-mini alone would be faster (estimated p50 2.42 s) if it qualified, but is predicted not to. The reasons for Setting 1:
- It escalates the fewest tickets (24%), so it has the lowest estimated p50: 2.82 s, against 3.27 s for Setting 2 and 4.18 s for qwen alone.
- Its tuning accuracy (79.3%) is above the 74.9% overall limit, with a margin of about 4 points.
- On the weakest category it matches qwen: Money transfer scores 4/11 in the cascade and in qwen alone, so it does not widen that gap.

**Predicted order of median latency, from fastest to slowest: Setting 1, then Setting 2, then qwen alone.**

**If Setting 1 breaks a per-category limit, Setting 2 is predicted not to fix it.** On the tuning set the two settings give identical per-category results, so qwen alone would then be the fastest qualifying configuration.

## 2. Per-setting predictions

| | Setting 1 | Setting 2 | qwen alone (reference) |
|---|---|---|---|
| Escalation fraction | **24%** (21/87) | **37%** (32/87) | 0% |
| Overall accuracy | **79%** (69/87) | **79%** (69/87) | 76% (66/87) |
| Accuracy, answers accepted from phi4-mini | 85% (56/66) | 87% (48/55) | n/a |
| Accuracy, escalated tickets (qwen's answer) | 62% (13/21) | 66% (21/32) | n/a |
| Median latency | **about 2.8 s** | **about 3.3 s** | about 4.2 s |
| Mean latency (for reference) | about 3.7 s | about 4.1 s | about 4.3 s |

- **Predicted speed gain against qwen alone:** Setting 1, p50 down 33%; Setting 2, p50 down 22%.
- **Predicted accuracy cost against qwen alone:** none overall. The tuning set puts both settings 3 tickets above qwen (69 against 66). The tuning set also puts phi4-mini alone at 68/87, so the cascade is predicted to be about equal to phi4-mini alone, not clearly above it.
- **Sampling uncertainty.** At 86 test tickets, an accuracy near 79% has a 95% sampling interval of about ±9 points. The escalation fraction has a standard deviation of about 5 points on the test set, and about 8 points on a roughly 30-ticket speed workload.
- **Direction of error for latency.** The simulation uses Assignment 1 sequential, unloaded timings, so measured medians under load are expected to come out **higher** than the table, not lower.

## 3. Categories predicted to lose the most accuracy when the small model's answer is accepted

Against qwen alone on the tuning set, **Credit card** and **Consumer loan** are the only categories where the cascade is below qwen, each by one ticket:

| Category | Cascade (both settings) | qwen alone | Difference |
|---|---|---|---|
| Credit card | 6/8 | 7/8 | -12.5 points |
| Consumer loan | 8/9 | 9/9 | -11.1 points |

Predictions:
1. **Credit card loses the most** in both settings. phi4-mini's Credit-card answers are 75% precise and are accepted in both.
2. **Consumer loan is second.** Its answers are 73% precise and are accepted in Setting 1. In Setting 2 they are escalated, but the tuning set shows no gain from that.
3. **Credit reporting (86% precise) and Debt collection are not predicted to lose accuracy;** on the tuning set the cascade is above qwen alone on both.
4. **Money transfer remains the weakest category in absolute terms** (4/11 on the tuning set), but it is not predicted to lose accuracy relative to qwen.

**Credit card is the category most likely to breach its limit.** The test set has 9 Credit card tickets, so one ticket is 11.1 points. With the limit at 73.9% (`golden/limits_a2.md`), the cascade needs at least 7 of 9 correct, and losing 2 tickets against qwen would breach it. Debt collection (8 tickets) and Mortgage (9) are also decided by single tickets.

## 4. Known risks to these predictions

1. **Mean and median disagree for Setting 2.** Its estimated mean is 4.13 s, only 5% below qwen alone (4.33 s), while its estimated median is 22% below (3.27 s). If speed is judged by the mean or by the tail, Setting 2 looks much less attractive than by the median. Setting 1 shows the same pattern more mildly (mean 15% lower, median 33% lower).
2. **Two resident models may compete for CPU under load.** The simulation assumes the second model costs nothing while idle. It was not measured under load.
3. **The estimates are optimistic.** They come from Assignment 1 unloaded timings.
4. **The cascade's accuracy benefit over phi4-mini alone is one ticket on the tuning set.** Of the 9 phi4-mini errors Setting 1 routes to qwen, all with golden label Money transfer, qwen answers 2 correctly, and it breaks 1 answer phi4-mini had right.
5. **Small samples.** 87 tuning and 86 test tickets, with 8 to 23 per category.

## 5. What would show these predictions wrong

- Setting 2 measured faster than Setting 1 at the median, or qwen alone measured faster than either setting.
- Setting 1 failing the overall limit, or Money transfer falling more than 15 points below qwen's score.
- A category other than Credit card or Consumer loan showing the largest loss against qwen alone.
- Setting 2 qualifying when Setting 1 does not.
- The measured escalation fraction on the test set outside about 15% to 33% for Setting 1, or outside about 27% to 47% for Setting 2 (roughly two standard deviations either side).
