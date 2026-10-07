# Load Test Results

Open-loop JMeter load tests against `POST /tickets`.

Raw results are under `results/load/<model>/rate-2/`.
Summary statistics are from `results/load/summary.csv`.
All configurations used 3 runs.

## 1. Test configuration

- Arrival rate: 2 tickets/min (120/hour)
- Duration: 30 minutes/run
- Runs: 3 per model
- Traffic model: Open Model Thread Group
- Input: team ticket narratives via CSV Data Set Config
- Load generator and SUT ran on separate machines
- Network: The JMeter load generator and SUT communicated over a ZeroTier virtual network across separate residential internet connections.
- Network latency therefore includes ZeroTier and residential internet overhead, so absolute response times may differ from a co-located deployment.

Models:
- `llama3.2:1b`
- `llama3.2:3b`
- `phi4-mini`
- `qwen2.5:7b`

## 2. Execution

Before testing each candidate model, the active model was verified through `GET /health`.

Each model was tested using:

```powershell
.\jmeter\run_load.ps1 `
    -SutHost <SUT-IP> `
    -RatePerMin 2 `
    -Minutes 30 `
    -Runs 3 `
    -Kind load
```

The script executed three independent 30-minute runs for the active model and stored the raw results under `results/load/<model>/rate-2/`.

After all four models were tested, the JMeter results were analysed using:

```powershell
python scripts\analyze_jtl.py --kind load
```

## 3. Results

Values are reported as mean ± standard deviation across the three runs.

| Model | Achieved/min | p50 | p95 | p99 | Error rate |
|---|---:|---:|---:|---:|---:|
| `llama3.2:1b` | 2.06 ± 0.04 | 0.95 ± 0.19 s | 1.87 ± 0.38 s | 2.79 ± 0.85 s | 0% |
| `llama3.2:3b` | 2.06 ± 0.04 | 1.28 ± 0.56 s | 3.06 ± 1.31 s | 4.50 ± 1.80 s | 0% |
| `phi4-mini` | 2.06 ± 0.04 | 1.75 ± 0.95 s | 3.33 ± 1.33 s | 5.48 ± 2.96 s | 0% |
| `qwen2.5:7b` | 2.06 ± 0.04 | 2.26 ± 1.70 s | 5.36 ± 2.93 s | 8.60 ± 4.82 s | 0% |

- All four models sustained the offered rate with 0% errors.
- Latency increased across the candidate set, with `llama3.2:1b` fastest and `qwen2.5:7b` slowest.
- `qwen2.5:7b` also showed the greatest run-to-run latency variation.
- Achieved throughput closely matched offered throughput for every model.

## 4. Reconciliation

JMeter results were reconciled against `logs/service.jsonl` using:

`python scripts/reconcile.py --kind load`

The reconciliation output is stored in `results/load/reconciliation.csv`.

## 5. Evidence

- Raw `.jtl`: `results/load/<model>/rate-2/`
- Per-run metadata: `runN.meta.json`
- JMeter logs: `runN.jmeter.log`
- Summary: `results/load/summary.csv`
- Reconciliation: `results/load/reconciliation.csv`