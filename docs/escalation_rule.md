# Escalation rule (Assignment 2)

**Status: FINAL.** Owner: Zhi Ming. Committed in 06d309a on 10 Nov, before any Assignment 2 benchmark run. Not changed since that commit except this status line (wording only, no rule or number changed).

**Evidence base.** The rule and both settings were chosen from **tuning-set numbers only** (87 tickets, odd positions in `golden/split_a2.csv`): `docs/a2_tuning_reliability.md`, `docs/a2_cascade_simulation.md`, and `scripts/a2_tuning_breakdown.py` (which drops every test-set row at load). No test-set ticket or result was used to choose the rule or its settings.

## 1. The rule

Every ticket goes to `phi4-mini` first. If phi4-mini's predicted category is on the active setting's escalation list, or phi4-mini does not return a valid category, the same ticket is sent to `qwen2.5:7b` and **qwen's answer is the final answer**. Otherwise phi4-mini's answer is final. Nothing else is looked at: not ticket length, not any confidence score, and there is no second opinion or voting.

## 2. The two settings

| Setting | Escalate when phi4-mini predicts | Suggested switch |
|---|---|---|
| **1** | Bank account or service | `CASCADE_SETTING=1` |
| **2** | Bank account or service, **or** Consumer loan | `CASCADE_SETTING=2` |

The variable name is Belford's to choose. The setting must be switchable without a code change, and the active setting must be logged for every ticket.

## 3. Procedure (enough to implement from this file alone)

```
ESCALATE = { 1: {"Bank account or service"},
             2: {"Bank account or service", "Consumer loan"} }[setting]

POST /tickets(narrative):
    small = classify(narrative, model="phi4-mini")        # A1 prompt, unchanged
    if small is not a valid category  or  small in ESCALATE:
        final = classify(narrative, model="qwen2.5:7b")   # same prompt, unchanged
        escalated = True
    else:
        final = small
        escalated = False
    store ticket with category = final
    return {id, category, model: <the same fixed label for every ticket>}
```

A "valid category" is one of the seven Assignment 1 names: Credit reporting, Debt collection, Mortgage, Credit card, Bank account or service, Consumer loan, Money transfer or service.

- **The caller must not be able to tell which model answered** (assignment Step 2). Assignment 1 returned `model: <the model that classified>`; in the cascade that would reveal the model per ticket. The `model` field in the `POST /tickets` response must therefore be one constant label (for example the configuration name), identical for every ticket. Which model produced the final answer is recorded in the service log only (section 5). `GET /search` and `GET /stats` are unchanged and do not expose the model.
- Both models use the Assignment 1 prompt (zero-shot, seven category names, JSON schema), temperature 0, seed 42 and `NUM_CTX` 2048. The classification prompt is not changed and no second prompt is used.
- Both stay resident (`OLLAMA_MAX_LOADED_MODELS=2`, `KEEP_ALIVE=-1`, `NUM_PARALLEL=1`). No retries, no caching.

## 4. Behaviour outside a normal answer (design choices, stated so they are not left to the implementer)

- **phi4-mini returns `Unclassified` or its call fails: escalate.** This never happened on the tuning set (all 87 phi4-mini answers were valid categories), so it affects nothing measured; it only makes the rule total.
- **qwen fails after an escalation: return the same HTTP 502 as Assignment 1.** Do not fall back to phi4-mini's answer, so failures stay visible in the error rate.

## 5. What must be logged for every ticket

`final_model`, `escalated` (true/false) and the active setting (required), plus `small_category` (phi4-mini's predicted category), `small_model_ms`, and `large_model_ms` (empty when not escalated). The escalation fraction is computed from these fields, not from the response.

## 6. Why this rule (tuning set only)

**phi4-mini is the small model.** On the tuning set it scores 78.2% (68/87), against 59.8% for llama3.2:3b and 44.8% for llama3.2:1b, and its estimated p50 is 2.42 s against qwen's 4.18 s.

**phi4-mini's reliability depends on which category it predicts.** A category-based rule can only see the predicted label, so it targets the labels it gets wrong most often:

| phi4-mini predicted | n | Correct | Precision |
|---|---|---|---|
| Bank account or service | 21 | 12 | **57%** |
| Consumer loan | 11 | 8 | **73%** |
| Credit card | 8 | 6 | 75% |
| Credit reporting | 21 | 18 | 86% |
| Debt collection | 11 | 10 | 91% |
| Mortgage | 13 | 12 | 92% |
| Money transfer or service | 2 | 2 | 100% |

**Why Setting 1 escalates Bank account.** It is the least reliable label (57%). All nine of phi4-mini's errors among its Bank-account answers are tickets whose golden label is Money transfer or service. That is also the category where phi4-mini is furthest below qwen on the tuning set: 18.2% against 36.4%, 18.2 points, beyond the client's 15-point per-category tolerance when applied to this set. No other category is more than 12.5 points below qwen. Escalating Bank-account answers brings Money transfer to parity with qwen (4/11 against 4/11).

**Why Setting 2 adds Consumer loan.** It is the next least reliable label (73%, 8/11), and phi4-mini is 11.1 points below qwen on Consumer loan (8/9 against 9/9). Setting 2 escalates 11 more tickets, at an estimated +0.45 s p50.

**How often a wrong answer slips through a "safe" label** (the check the assignment asks for). In Setting 1, 66 tickets are accepted from phi4-mini and 10 of them are wrong. By the label phi4-mini predicted, those 10 are Credit reporting 3, Consumer loan 3, Credit card 2, Mortgage 1 and Debt collection 1. Among the 47 accepted answers in the labels with tuning precision of 86% or more (Credit reporting, Debt collection, Mortgage, Money transfer), 5 were wrong, about 1 in 9. A "safe" label is therefore not error-free, and the rule accepts that risk knowingly. In Setting 2 the slip-through is 7 (Consumer loan's 3 are now escalated).

**Why not add Credit card.** Escalating Credit card as well sends 46% of tickets to qwen (est. p50 3.51 s) with cascade accuracy unchanged at 79.3%, and the Credit card cell drops from 6/8 to 5/8 (`docs/a2_cascade_simulation.md`).

**Rejected: a length rule.** Length does not predict phi4-mini's errors on the tuning set (mean 969 characters when wrong, 939 when right). Length cut-offs from 600 to 1,300 characters give 77.0% to 78.2% accuracy, no better than phi4-mini alone, while escalating 31% to 68% of tickets.

**Rejected: a different small model.** To approach 77% the 1B must escalate 78% of tickets (est. p50 4.21 s, about qwen alone at 4.18 s). The 3B tops out at 75.9% with 70% to 74% escalated (est. p50 4.58 to 4.81 s), slower than qwen alone.

## 7. What the tuning data does not show

- **The accuracy benefit over phi4-mini alone is one ticket.** Both settings reach 69/87 (79.3%) against phi4-mini's 68/87. In Setting 1, nine phi4-mini errors are routed to qwen, qwen answers 2 correctly, and it breaks 1 answer phi4-mini had right. "Errors caught" in the simulation means routed to qwen, not corrected. The rule's value on this evidence is Money transfer parity with qwen, not overall accuracy.
- **Setting 2 gains nothing over Setting 1 on the tuning set.** Its 11 extra escalations correct no tickets. It lowers the count of accepted small-model errors from 10 to 7 and raises accepted-answer accuracy from 85% to 87%, but the three additional routed errors (two Credit reporting, one Mortgage) are tickets qwen also gets wrong. It is offered as the cautious setting, and only the test set can say whether it is worth its speed cost.
- **Money transfer stays weak:** 4/11 in the cascade and in qwen alone.
- **Small samples.** 87 tickets, with 8 to 23 per category. One ticket moves a category by 4 to 12.5 points.
- **Latency figures are estimates** from Assignment 1 sequential, unloaded timings, so they are optimistic. For Setting 2, the mean (4.13 s) is close to qwen alone (4.33 s) while the median (3.27 s) is not (4.18 s).
