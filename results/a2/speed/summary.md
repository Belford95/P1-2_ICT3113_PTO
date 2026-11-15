# A2 speed results

| Configuration | Runs | p50 per run (ms) | p50 mean ± SD (min-max) | Pooled p95 (n) | Throughput /s per run | Error rate per run | Sent / completed / errored / unfinished | Escalation (logs) |
|---|---|---|---|---|---|---|---|---|
| cascade1 | 3 | 4416 / 4577 / 4192 | 4395 ± 193 (4192-4577) | 11894 (n=114) | 0.136 / 0.127 / 0.133 | 0.0% / 0.0% / 0.0% | 114 / 114 / 0 / 0 | 29% / 29% / 29% (pooled 29%) |
| cascade2 | 3 | 4404 / 4987 / 5014 | 4802 ± 345 (4404-5014) | 14412 (n=114) | 0.136 / 0.127 / 0.133 | 0.0% / 0.0% / 0.0% | 114 / 114 / 0 / 0 | 37% / 37% / 37% (pooled 37%) |
| qwen | 3 | 7400 / 7448 / 5994 | 6947 ± 826 (5994-7448) | 20945 (n=114) | 0.134 / 0.125 / 0.132 | 0.0% / 0.0% / 0.0% | 114 / 114 / 0 / 0 | 0% / 0% / 0% (pooled 0%) |

p50 = median of completed requests per run; pooled p95 = nearest-rank over all runs' completed requests (n shown); throughput = completed requests per second; escalation from logs/service.jsonl.
