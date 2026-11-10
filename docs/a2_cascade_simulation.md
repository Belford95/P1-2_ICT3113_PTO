# Cascade simulation on the tuning set (87 tickets)

Replays A1 accuracy records; latency = small-model time + qwen time when escalated (A1 sequential, unloaded timings). Design aid only: not an A2 measurement. Per-category cells are correct/total on the tuning set.

## Reference points

| Rule | Escalated | Cascade accuracy | Accepted-answer accuracy | Small errors caught / slipped | Est. mean s | Est. p50 s | Credit reporting | Debt collection | Mortgage | Credit card | Bank account or service | Consumer loan | Money transfer or service |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen2.5-7b alone | 0% (0) | 75.9% (66/87) | - | 0 / 0 | 4.33 | 4.18 | 16/23 | 7/10 | 12/13 | 7/8 | 11/13 | 9/9 | 4/11 |
| phi4-mini alone | 0% (0) | 78.2% (68/87) | 78% (68/87) | 0 / 19 | 2.50 | 2.42 | 18/23 | 10/10 | 12/13 | 6/8 | 12/13 | 8/9 | 2/11 |
| llama3.2-3b alone | 0% (0) | 59.8% (52/87) | 60% (52/87) | 0 / 35 | 1.97 | 1.97 | 20/23 | 2/10 | 11/13 | 6/8 | 4/13 | 7/9 | 2/11 |
| llama3.2-1b alone | 0% (0) | 44.8% (39/87) | 45% (39/87) | 0 / 48 | 1.09 | 1.05 | 16/23 | 7/10 | 9/13 | 2/8 | 3/13 | 2/9 | 0/11 |

## phi4-mini -> qwen2.5-7b: category-based (escalate when phi4-mini predicts a listed category)

Categories are added in order of the small model's tuning-set precision for that predicted label, least reliable first: Bank account or service 57% (n=21), Consumer loan 73% (n=11), Credit card 75% (n=8), Credit reporting 86% (n=21), Debt collection 91% (n=11), Mortgage 92% (n=13), Money transfer or service 100% (n=2)

| Rule | Escalated | Cascade accuracy | Accepted-answer accuracy | Small errors caught / slipped | Est. mean s | Est. p50 s | Credit reporting | Debt collection | Mortgage | Credit card | Bank account or service | Consumer loan | Money transfer or service |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| escalate Bank account or service | 24% (21) | 79.3% (69/87) | 85% (56/66) | 9 / 10 | 3.67 | 2.82 | 18/23 | 10/10 | 12/13 | 6/8 | 11/13 | 8/9 | 4/11 |
| escalate Bank account or service + Consumer loan | 37% (32) | 79.3% (69/87) | 87% (48/55) | 12 / 7 | 4.13 | 3.27 | 18/23 | 10/10 | 12/13 | 6/8 | 11/13 | 8/9 | 4/11 |
| escalate Bank account or service + Consumer loan + Credit card | 46% (40) | 79.3% (69/87) | 89% (42/47) | 14 / 5 | 4.54 | 3.51 | 19/23 | 10/10 | 12/13 | 5/8 | 11/13 | 8/9 | 4/11 |
| escalate Bank account or service + Consumer loan + Credit card + Credit reporting | 70% (61) | 79.3% (69/87) | 92% (24/26) | 17 / 2 | 5.54 | 5.07 | 16/23 | 10/10 | 12/13 | 7/8 | 11/13 | 9/9 | 4/11 |

## phi4-mini -> qwen2.5-7b: length-based (escalate when narrative > cut-off characters)

| Rule | Escalated | Cascade accuracy | Accepted-answer accuracy | Small errors caught / slipped | Est. mean s | Est. p50 s | Credit reporting | Debt collection | Mortgage | Credit card | Bank account or service | Consumer loan | Money transfer or service |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| > 600 chars | 68% (59) | 78.2% (68/87) | 86% (24/28) | 15 / 4 | 6.04 | 6.53 | 17/23 | 8/10 | 12/13 | 7/8 | 12/13 | 9/9 | 3/11 |
| > 800 chars | 54% (47) | 78.2% (68/87) | 78% (31/40) | 10 / 9 | 5.56 | 6.46 | 17/23 | 8/10 | 12/13 | 7/8 | 12/13 | 9/9 | 3/11 |
| > 1000 chars | 43% (37) | 77.0% (67/87) | 78% (39/50) | 8 / 11 | 5.07 | 2.42 | 17/23 | 8/10 | 12/13 | 6/8 | 12/13 | 9/9 | 3/11 |
| > 1300 chars | 31% (27) | 77.0% (67/87) | 78% (47/60) | 6 / 13 | 4.48 | 2.42 | 17/23 | 8/10 | 12/13 | 6/8 | 12/13 | 9/9 | 3/11 |

Does length predict phi4-mini errors on tuning? mean chars of wrong answers 969 vs right 939.


## llama3.2-3b -> qwen2.5-7b: category-based (escalate when llama3.2-3b predicts a listed category)

Categories are added in order of the small model's tuning-set precision for that predicted label, least reliable first: Credit reporting 45% (n=44), Bank account or service 57% (n=7), Credit card 60% (n=10), Debt collection 67% (n=3), Consumer loan 78% (n=9), Mortgage 92% (n=12), Money transfer or service 100% (n=2)

| Rule | Escalated | Cascade accuracy | Accepted-answer accuracy | Small errors caught / slipped | Est. mean s | Est. p50 s | Credit reporting | Debt collection | Mortgage | Credit card | Bank account or service | Consumer loan | Money transfer or service |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| escalate Credit reporting | 51% (44) | 73.6% (64/87) | 74% (32/43) | 24 / 11 | 4.11 | 3.04 | 15/23 | 7/10 | 11/13 | 8/8 | 10/13 | 9/9 | 4/11 |
| escalate Credit reporting + Bank account or service | 59% (51) | 74.7% (65/87) | 78% (28/36) | 27 / 8 | 4.52 | 3.58 | 15/23 | 7/10 | 11/13 | 8/8 | 10/13 | 9/9 | 5/11 |
| escalate Credit reporting + Bank account or service + Credit card | 70% (61) | 75.9% (66/87) | 85% (22/26) | 31 / 4 | 5.14 | 4.58 | 16/23 | 7/10 | 11/13 | 7/8 | 11/13 | 9/9 | 5/11 |
| escalate Credit reporting + Bank account or service + Credit card + Debt collection | 74% (64) | 75.9% (66/87) | 87% (20/23) | 32 / 3 | 5.28 | 4.81 | 16/23 | 7/10 | 11/13 | 7/8 | 11/13 | 9/9 | 5/11 |

## llama3.2-3b -> qwen2.5-7b: length-based (escalate when narrative > cut-off characters)

| Rule | Escalated | Cascade accuracy | Accepted-answer accuracy | Small errors caught / slipped | Est. mean s | Est. p50 s | Credit reporting | Debt collection | Mortgage | Credit card | Bank account or service | Consumer loan | Money transfer or service |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| > 600 chars | 68% (59) | 71.3% (62/87) | 64% (18/28) | 25 / 10 | 5.51 | 6.14 | 17/23 | 4/10 | 12/13 | 6/8 | 10/13 | 9/9 | 4/11 |
| > 800 chars | 54% (47) | 72.4% (63/87) | 65% (26/40) | 21 / 14 | 5.03 | 5.90 | 18/23 | 3/10 | 12/13 | 7/8 | 10/13 | 9/9 | 4/11 |
| > 1000 chars | 43% (37) | 69.0% (60/87) | 64% (32/50) | 17 / 18 | 4.54 | 1.97 | 18/23 | 3/10 | 12/13 | 6/8 | 8/13 | 9/9 | 4/11 |
| > 1300 chars | 31% (27) | 67.8% (59/87) | 65% (39/60) | 14 / 21 | 3.95 | 1.97 | 18/23 | 3/10 | 12/13 | 6/8 | 8/13 | 9/9 | 3/11 |

Does length predict llama3.2-3b errors on tuning? mean chars of wrong answers 1034 vs right 886.


## llama3.2-1b -> qwen2.5-7b: category-based (escalate when llama3.2-1b predicts a listed category)

Categories are added in order of the small model's tuning-set precision for that predicted label, least reliable first: Money transfer or service 0% (n=0), Credit card 29% (n=7), Credit reporting 35% (n=46), Debt collection 47% (n=15), Consumer loan 50% (n=4), Bank account or service 60% (n=5), Mortgage 90% (n=10)

| Rule | Escalated | Cascade accuracy | Accepted-answer accuracy | Small errors caught / slipped | Est. mean s | Est. p50 s | Credit reporting | Debt collection | Mortgage | Credit card | Bank account or service | Consumer loan | Money transfer or service |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| escalate Money transfer or service | 0% (0) | 44.8% (39/87) | 45% (39/87) | 0 / 48 | 1.09 | 1.05 | 16/23 | 7/10 | 9/13 | 2/8 | 3/13 | 2/9 | 0/11 |
| escalate Money transfer or service + Credit card | 8% (7) | 48.3% (42/87) | 46% (37/80) | 5 / 43 | 1.45 | 1.14 | 16/23 | 7/10 | 9/13 | 2/8 | 5/13 | 2/9 | 1/11 |
| escalate Money transfer or service + Credit card + Credit reporting | 61% (53) | 72.4% (63/87) | 62% (21/34) | 35 / 13 | 3.82 | 3.04 | 14/23 | 8/10 | 11/13 | 6/8 | 12/13 | 8/9 | 4/11 |
| escalate Money transfer or service + Credit card + Credit reporting + Debt collection | 78% (68) | 77.0% (67/87) | 74% (14/19) | 43 / 5 | 4.54 | 4.21 | 16/23 | 7/10 | 12/13 | 7/8 | 12/13 | 9/9 | 4/11 |

## llama3.2-1b -> qwen2.5-7b: length-based (escalate when narrative > cut-off characters)

| Rule | Escalated | Cascade accuracy | Accepted-answer accuracy | Small errors caught / slipped | Est. mean s | Est. p50 s | Credit reporting | Debt collection | Mortgage | Credit card | Bank account or service | Consumer loan | Money transfer or service |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| > 600 chars | 68% (59) | 65.5% (57/87) | 46% (13/28) | 33 / 15 | 4.63 | 5.26 | 16/23 | 6/10 | 11/13 | 5/8 | 11/13 | 5/9 | 3/11 |
| > 800 chars | 54% (47) | 63.2% (55/87) | 45% (18/40) | 26 / 22 | 4.16 | 5.03 | 16/23 | 6/10 | 11/13 | 4/8 | 11/13 | 5/9 | 2/11 |
| > 1000 chars | 43% (37) | 58.6% (51/87) | 46% (23/50) | 21 / 27 | 3.67 | 1.05 | 14/23 | 6/10 | 11/13 | 3/8 | 10/13 | 5/9 | 2/11 |
| > 1300 chars | 31% (27) | 55.2% (48/87) | 47% (28/60) | 16 / 32 | 3.07 | 1.05 | 14/23 | 6/10 | 11/13 | 3/8 | 9/13 | 4/9 | 1/11 |

Does length predict llama3.2-1b errors on tuning? mean chars of wrong answers 948 vs right 942.

