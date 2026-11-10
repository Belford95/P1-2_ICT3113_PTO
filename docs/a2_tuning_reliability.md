# Tuning set (odd positions): small-model reliability by predicted category

Precision = of the tuning tickets the model labelled X, how many really were X. A category-based rule can only see the predicted label.

## llama3.2-1b: tuning accuracy 44.8% (39/87)

| Predicted as | n | Correct | Precision |
|---|---|---|---|
| Credit reporting | 46 | 16 | 35% |
| Debt collection | 15 | 7 | 47% |
| Mortgage | 10 | 9 | 90% |
| Credit card | 7 | 2 | 29% |
| Bank account or service | 5 | 3 | 60% |
| Consumer loan | 4 | 2 | 50% |

## llama3.2-3b: tuning accuracy 59.8% (52/87)

| Predicted as | n | Correct | Precision |
|---|---|---|---|
| Credit reporting | 44 | 20 | 45% |
| Debt collection | 3 | 2 | 67% |
| Mortgage | 12 | 11 | 92% |
| Credit card | 10 | 6 | 60% |
| Bank account or service | 7 | 4 | 57% |
| Consumer loan | 9 | 7 | 78% |
| Money transfer or service | 2 | 2 | 100% |

## phi4-mini: tuning accuracy 78.2% (68/87)

| Predicted as | n | Correct | Precision |
|---|---|---|---|
| Credit reporting | 21 | 18 | 86% |
| Debt collection | 11 | 10 | 91% |
| Mortgage | 13 | 12 | 92% |
| Credit card | 8 | 6 | 75% |
| Bank account or service | 21 | 12 | 57% |
| Consumer loan | 11 | 8 | 73% |
| Money transfer or service | 2 | 2 | 100% |
