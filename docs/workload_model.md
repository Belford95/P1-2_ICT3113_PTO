# Workload Model

Team 2, rows 2000-2999. This document estimates how busy the client's system
would realistically be, so that Step 4's requirements (response time,
throughput, accuracy) are derived from something concrete rather than picked
arbitrarily. Every figure below is marked as either **cited** (a public
source) or **assumed** (our own reasoned estimate, with the reasoning shown).

## 1. Ticket length distribution — cited (our own data)

Computed directly from `data/team_rows.csv` (n=1,000):

| Stat | Value (characters) |
|---|---|
| Mean | 856 |
| Std dev | 447 |
| Min | 200 |
| Median (p50) | 768 |
| p90 | 1,518 |
| p95 | 1,722 |
| p99 | 1,922 |
| Max | 1,999 |

The range is bounded to roughly 200-2,000 characters, which does not look
naturally occurring — the course dataset appears to have been deliberately
pre-filtered to this band. This is favourable for the service: at ~4
characters/token, the p99 narrative is ~480 tokens, comfortably inside the
service's 2,048-token context window (`docs/service_design.md`), so
truncation should not be a factor at any percentile we're likely to test.

## 2. Ticket volume estimate — assumed, anchored to a cited figure

**Cited anchor:** the CFPB's 2024 Consumer Response Annual Report reports
~2,829,400 complaints sent to ~3,600 companies in 2024 — an industry-wide
average of **~786 complaints/company/year**
([source](https://www.consumerfinance.gov/data-research/research-reports/2024-consumer-response-annual-report/)).

**Sizing assumption:** this average blends everything from tiny credit
unions to national megabanks, so it can't be used directly. The brief
describes the client as having a dedicated "customer relations desk," which
implies enough complaint volume to justify a centralized team and, by
extension, enough volume to justify automating triage — a company small
enough to sit at the raw 786/year average likely wouldn't have a strong ROI
case for this project. We therefore assume a mid-size regional financial
services company, at roughly **5x** the national per-company average:

- **~4,000 tickets/year** (assumed)

**Arithmetic (derived from the assumption above):**

| Period | Volume |
|---|---|
| Per year | ~4,000 |
| Per business day (÷ ~250 business days/year) | ~16 |
| Per business hour (÷ 8-hour day) | ~2/hour average |

These per-hour/per-day figures are what feed the throughput requirement in
Step 4 — see the peak adjustment below before that number is used directly.

## 3. Search rate estimate — assumed, no public source exists

There is no published data on how often support staff search a ticket
system, so this is a stated assumption rather than a citation. We assume
each incoming ticket prompts roughly **2 searches on average** (e.g.
checking for duplicate or related complaints against the same company or
account), based on typical support-desk workflows. Search terms used for
`GET /search` load testing are already scaffolded in
`jmeter/data/search_terms.csv` (credit report, late fee, wire transfer,
etc.) — this document only supplies the *rate*, not the terms.

- **~2 searches per ticket → ~8,000 searches/year → ~4/hour average**
  (using the ticket volume above)

## 4. Peak vs. non-peak — assumed, no timestamp data available

`data/team_rows.csv` has no date/time column (only `row`, `source_label`,
`narrative`), so this can't be derived from our own data — it's a reasoned
assumption. Financial complaints are typically filed during or shortly
after a business interaction (a call, a statement, a billing cycle), which
should cluster in weekday business hours.

**Assumption:** weekday business hours (Mon-Fri, 9am-5pm = 40 hrs/week)
account for ~70% of weekly volume; the remaining 30% spreads thinly across
the other 128 hours of the week.

**Arithmetic:**

| | Calculation | Result |
|---|---|---|
| Weekly ticket volume | 4,000 / 52 | ~77/week |
| Peak hourly rate | (0.70 x 77) / 40 hrs | **~1.3 tickets/hour** |
| Non-peak hourly rate | (0.30 x 77) / 128 hrs | **~0.18 tickets/hour** |
| Peak hourly search rate | 2x ticket rate (from §3) | **~2.6 searches/hour** |

## 5. Summary — numbers for the requirements owner

| Figure | Value | Basis |
|---|---|---|
| Narrative length (p95 / p99 / max) | 1,722 / 1,922 / 1,999 chars | Cited (own data) |
| Assumed annual ticket volume | ~4,000 | Assumed, anchored to CFPB |
| Peak ticket rate | ~1.3/hour | Assumed |
| Non-peak ticket rate | ~0.18/hour | Assumed |
| Peak search rate | ~2.6/hour | Assumed |

**Caveat:** these peak rates look low in absolute terms (~1.3 tickets/hour)
because they're a naive time-of-day average. A real system also has
burstiness within peak hours (e.g. a backlog dumped in after a mailing, or
several tickets arriving in the same minute) — the requirements owner
should consider testing at multiples of this average rate (e.g. 5x, 10x) in
addition to the raw average, to check the baseline's behaviour under
bursty, not just steady, peak load. This is flagged here rather than
decided here, since load levels to test are the requirements owner's call.

## Sources

- CFPB, [2024 Consumer Response Annual Report](https://www.consumerfinance.gov/data-research/research-reports/2024-consumer-response-annual-report/)
- All other figures in this document not marked "cited" are team assumptions,
  reasoned as shown above.
