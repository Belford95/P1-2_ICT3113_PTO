# Assignment 2 accuracy limits (test set = even positions in the row-sorted golden set)

Golden set: 173 tickets -> tuning 87 (odd positions after sorting by row number), test 86 (even positions).
Top model: `qwen2.5:7b` (A1 full-golden-set accuracy 80.3%).
Source: A1 accuracy records `results/accuracy/*/responses.csv` (reused: same digest, prompt, Ollama 0.35.0 and machine), scored on test-set rows only.

**Overall limit: 84.9% (73/86) - 10 = 74.9%**

| Category | Test n | qwen2.5:7b | Limit (-15 pts) | Fair test? |
|---|---|---|---|---|
| Credit reporting | 18 | 83.3% (15/18) | 68.3% | yes |
| Debt collection | 8 | 87.5% (7/8) | 72.5% | no: 1 ticket = 12.5 pts |
| Mortgage | 9 | 100.0% (9/9) | 85.0% | no: 1 ticket = 11.1 pts |
| Credit card | 9 | 88.9% (8/9) | 73.9% | no: 1 ticket = 11.1 pts |
| Bank account or service | 14 | 92.9% (13/14) | 77.9% | yes |
| Consumer loan | 16 | 87.5% (14/16) | 72.5% | yes |
| Money transfer or service | 12 | 58.3% (7/12) | 43.3% | yes |

## Every A1 model on the test set

| Model | Overall | Credit reporting | Debt collection | Mortgage | Credit card | Bank account or service | Consumer loan | Money transfer or service | Passes? |
|---|---|---|---|---|---|---|---|---|---|
| llama3.2-1b | 45.3% (39/86) ✗ | 83% (15/18) | 75% (6/8) | 56% (5/9) ✗ | 22% (2/9) ✗ | 29% (4/14) ✗ | 38% (6/16) ✗ | 8% (1/12) ✗ | fail: overall; Mortgage, Credit card, Bank account or service, Consumer loan, Money transfer or service |
| llama3.2-3b | 66.3% (57/86) ✗ | 94% (17/18) | 62% (5/8) ✗ | 89% (8/9) | 56% (5/9) ✗ | 57% (8/14) ✗ | 69% (11/16) ✗ | 25% (3/12) ✗ | fail: overall; Debt collection, Credit card, Bank account or service, Consumer loan, Money transfer or service |
| phi4-mini | 79.1% (68/86) | 89% (16/18) | 75% (6/8) | 89% (8/9) | 56% (5/9) ✗ | 100% (14/14) | 81% (13/16) | 50% (6/12) | fail: Credit card |
| qwen2.5-7b | 84.9% (73/86) | 83% (15/18) | 88% (7/8) | 100% (9/9) | 89% (8/9) | 93% (13/14) | 88% (14/16) | 58% (7/12) | reference |
