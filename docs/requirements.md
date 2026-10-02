# Performance and Accuracy Requirements

**Status: DRAFT for team review.** Every requirement is a number, a percentile where relevant, and the load condition under which it must hold. Values marked *(team decision)* are proposals, not settled. Nothing here may change after the freeze.

Inputs: `docs/workload_model.md` (volumes, rates, ticket length) and `docs/service_design.md` (baseline behaviour).

## 1. Position on cost (Step 6 requires us to take one)

Today a human reads and routes every ticket, so an automated result that arrives within about a minute is not noticeable to the client or the customer. A **misrouted ticket**, in contrast, lands with the wrong team, needs a human to notice and re-route it, and can add hours to resolution. We therefore weight **accuracy above latency**: latency requirements are lenient, accuracy requirements are strict. *(team decision; workload analyst to confirm and supply the cost framing for Slide 11)*

## 2. Load levels the requirements refer to

From the workload model (assumed ~4,000 tickets/year; peak about 1.3 tickets/hour, non-peak about 0.18/hour; searches about 2 per ticket).

| Level | Ticket arrival rate | Derivation |
|---|---|---|
| **Peak average** | ~1.3 tickets/hour | Workload model section 4 |
| **Burst** | ~13 tickets/hour | 10x peak average, as suggested in the workload model caveat |
| **Backlog drain** | **~120 tickets/hour, sustained** | A backlog of ~100 tickets (about 1.3 weeks of average volume, e.g. intake down or a mailing) must clear within about an hour. Assumed, not cited. |

Note: the peak-average and burst rates alone are so low that any CPU model would meet any latency target with no queueing. The backlog-drain level is what actually tests capacity, which is why the throughput requirement is set there. *(team decision)*

## 3. Requirements

### R1 Response time: POST /tickets
- **R1a.** p95 latency <= **60 s** (p99 <= **120 s**) at the **peak average** and **burst** levels. Justification: a minute is imperceptible next to today's human routing; at these rates requests do not queue, so this is effectively the single-request service time.
- **R1b.** p95 latency <= **120 s** at the **backlog-drain** level. Justification: at sustained high load requests queue in Ollama (one inference at a time); a two-minute worst case is still acceptable for a backlog being cleared.

### R2 Response time: GET /search under mixed load
- p95 <= **2 s**, p99 <= **5 s**, measured while POST /tickets is arriving at the **backlog-drain** level and searches arrive at 2x the ticket rate, with the store holding **at least 1,000 tickets**. Justification: search is used interactively by agents; the baseline scans the whole table (`LIKE '%q%'`), so this checks that classification traffic does not starve it. *(team decision on 2 s)*

### R3 Throughput
- The service must sustain **>= 120 tickets/hour** (2/min) classified for **at least 30 minutes** at the **backlog-drain** arrival rate, with achieved throughput within 5% of the arrival rate (i.e. no unbounded queue growth) and error rate per R4. Justification: derived from the backlog-drain level above. Achieved throughput and error rate are read from the `.jtl` files.
- Implied ceiling: with `OLLAMA_NUM_PARALLEL=1`, capacity is about 3600 / S tickets/hour, where S is the median service time in seconds. Meeting R3 needs S <= about 30 s, which filters candidates quickly.

### R4 Error rate
- HTTP 5xx and timeouts <= **1%** of requests at every load level; responses returned as `Unclassified` <= **2%** of tickets.

### R5 Classification accuracy (golden set, unloaded)
Measured by sending every golden-set ticket through `POST /tickets` for each candidate, against the frozen golden labels.
- **R5a.** Overall accuracy >= **80%** *(team decision — checked against the golden set's agreement statistic: 95.0% agreement, Cohen's κ = 0.942 ("almost perfect"), so the human ceiling is high and 80% is not an unreasonably stretched target for a zero-shot model without category definitions in-prompt)*.
- **R5b.** Accuracy in **every one of the 7 categories** >= **60%**. *(Caution: the frozen golden set (173 tickets) is not evenly split across categories — Credit reporting has 41, Credit card only 17 and Debt collection 18. A single wrong prediction swings a small category's accuracy by ~5-6 points, so per-category numbers on the smallest classes will be noisier than this threshold implies; note this when interpreting Slide 10.)*
- **R5c.** Report a confusion matrix; no single confusion pair may account for more than **15% of the tickets of a category** *(optional, drop if the team finds it excessive)*.
- **R5d.** Tickets the golden set records as `None / Unclear` (labelling protocol v1.0, section 1.2 step 7 and section 2.2) are **excluded from accuracy scoring**, since a classifier limited to the 7 categories cannot be scored on them. Report their count and exclude them from R5a-c's denominators, do not silently drop them from the golden set itself.

## 4. Traceability

| Requirement | Evidence | Source of truth |
|---|---|---|
| R1, R3, R4 | `results/*.jtl` (3 runs per configuration), analysed by `scripts/analyze_jtl.py` | `.jtl` reconciled against `logs/service.jsonl` |
| R2 | mixed-load `.jtl` | same |
| R5 | accuracy run output, `scripts/accuracy_report.py` | golden set + `logs/service.jsonl` |

## 5. Open items

- [ ] Team to confirm the cost position (section 1) and the backlog-drain assumption (section 2).
- [ ] Workload analyst to review that the load levels match their model.
- [ ] Revisit R5 thresholds after the inter-annotator agreement is computed.
- [ ] Confirm with the test engineer that the levels (1.3, 13, 120 tickets/hour) can be generated with the open-loop JMeter setup; the stress test then pushes beyond 120/hour to find the limit.
- [x] CPU-only confirmed on the candidate service host (`ollama ps` shows 100% CPU despite an RTX 4060 being present) — client constraint satisfied.
- [x] Service host confirmed: AMD Ryzen 7 7745HX (8C/16T, 3.6 GHz), 15.5 GB available to Docker, Windows 11 Home. This is the machine latency predictions and Slide 7 should be based on.
- [ ] Labelling protocol v1.0 is in (`golden/labelling_protocol.md`); its category-pair rules (section 2.1, e.g. Credit reporting/Debt collection, Bank account/Money transfer) name the confusions most likely to show up in R5c once real predictions exist.
- [ ] Freeze with the rest of the gate.
