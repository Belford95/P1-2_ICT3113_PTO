# A2 accuracy on the test set (86 tickets)

Reference: `qwen2.5:7b` alone, 73/86 = 84.9%. **Overall limit 74.9%**; per category: reference - 15 points.

| Configuration | Overall | Verdict | Credit reporting | Debt collection | Mortgage | Credit card | Bank account or service | Consumer loan | Money transfer or service |
|---|---|---|---|---|---|---|---|---|---|
| *limit* | *74.9%* | | *68.3%* | *72.5%* | *85.0%* | *73.9%* | *77.9%* | *72.5%* | *43.3%* |
| llama3.2:1b alone | 45.3% (39/86) ✗ | fail: Mortgage; Credit card; Bank account or service; Consumer loan; Money transfer or service | 83% (15/18) | 75% (6/8) | 56% (5/9) ✗ | 22% (2/9) ✗ | 29% (4/14) ✗ | 38% (6/16) ✗ | 8% (1/12) ✗ |
| llama3.2:3b alone | 66.3% (57/86) ✗ | fail: Debt collection; Credit card; Bank account or service; Consumer loan; Money transfer or service | 94% (17/18) | 62% (5/8) ✗ | 89% (8/9) | 56% (5/9) ✗ | 57% (8/14) ✗ | 69% (11/16) ✗ | 25% (3/12) ✗ |
| phi4-mini alone | 79.1% (68/86) | fail: Credit card | 89% (16/18) | 75% (6/8) | 89% (8/9) | 56% (5/9) ✗ | 100% (14/14) | 81% (13/16) | 50% (6/12) |
| qwen2.5:7b alone | 84.9% (73/86) | reference | 83% (15/18) | 88% (7/8) | 100% (9/9) | 89% (8/9) | 93% (13/14) | 88% (14/16) | 58% (7/12) |
| cascade-setting-1 [Setting 1] | 84.9% (73/86) | PASS | 89% (16/18) | 75% (6/8) | 100% (9/9) | 89% (8/9) | 93% (13/14) | 88% (14/16) | 58% (7/12) |
| cascade-setting-2 [Setting 2] | 83.7% (72/86) | PASS | 83% (15/18) | 88% (7/8) | 100% (9/9) | 89% (8/9) | 93% (13/14) | 81% (13/16) | 58% (7/12) |

Too small for the 15-point limit to be a fair test (one ticket decides it): Debt collection (8 tickets, 1 ticket = 12.5 pts); Mortgage (9 tickets, 1 ticket = 11.1 pts); Credit card (9 tickets, 1 ticket = 11.1 pts).

## Cascade escalation (from logs/service.jsonl)

| Configuration | Escalated | Accuracy escalated | Accuracy not escalated | Small-model errors caught / slipped | Log check |
|---|---|---|---|---|---|
| cascade-setting-1 [Setting 1] | 27.9% (24/86) | 18/24 | 55/62 | 10 / 7 | ok |
| cascade-setting-2 [Setting 2] | 45.4% (39/86) | 32/39 | 40/47 | 12 / 7 | ok |
