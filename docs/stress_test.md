# Stress Test Results

Stress test of the unmodified baseline using `phi4-mini`.

Raw result: `results/stress/phi4-mini/custom-20261007-1950/run1.jtl`  
Timeline: `results/stress/phi4-mini/custom-20261007-1950/run1.timeline.csv` / `results/stress/phi4-mini/custom-20261007-1950/run1.timeline.png`

## 1. Test configuration

Stepped open-loop arrival rate:

| Stage | Offered rate | Duration |
|---|---:|---:|
| 1 | 10/min | 5 min |
| 2 | 20/min | 5 min |
| 3 | 30/min | 5 min |
| 4 | 40/min | 5 min |
| Drain | 0/min | 5 min |

The JMeter load generator and SUT ran on separate machines and communicated over a ZeroTier virtual network across separate residential internet connections. Measured response times therefore include ZeroTier and residential internet overhead.

The test was intended to identify the arrival rate at which the service could no longer keep completions in line with arrivals and latency/backlog began growing.

## 2. Execution

Before the test, the active model was verified through `GET /health` to confirm that `phi4-mini` was running.

The stress test was executed from the JMeter load-generator machine using:

```powershell
.\jmeter\run_load.ps1 `
    -SutHost <SUT-IP> `
    -Kind stress `
    -Schedule "rate(10/min) random_arrivals(5 min) rate(10/min) rate(20/min) random_arrivals(5 min) rate(20/min) rate(30/min) random_arrivals(5 min) rate(30/min) rate(40/min) random_arrivals(5 min) rate(40/min) pause(5 min)" `
    -Runs 1 `
    -CooldownSec 0
```

The resulting JMeter file was analysed using:

```powershell
python scripts\analyze_stress.py "results\stress\phi4-mini\custom-20261007-1950\run1.jtl"
```

## 3. Result

- **10/min:** stable. Arrivals and completions remained approximately matched.
- **20/min:** stable. The service continued to keep up, with bounded in-flight requests.
- **30/min:** unstable. Completions began falling behind arrivals, in-flight requests grew rapidly, and p95 latency rose sharply.
- **40/min:** severely overloaded. p95 latency reached approximately 296 s and maximum in-flight requests reached 110.
- Peak observed completion throughput in a one-minute bucket was **26 tickets/min**.
- No request errors occurred; the limiting behaviour was queue buildup and latency growth rather than request failure.

Therefore the sustainable baseline arrival-rate limit for `phi4-mini` lies **between approximately 20 and 30 tickets/minute**.

## 4. Reconciliation

| JMeter requests | Service requests | Count match | JMeter OK | Service OK |
|---:|---:|---|---:|---:|
| 500 | 500 | Yes | 500 | 500 |

JMeter p50 was 36.70 s and service p50 was 36.66 s, with approximately 33 ms of client/network overhead.

The reconciliation was produced using:

```powershell
python scripts\reconcile.py --kind stress
```

## 5. Evidence

- `results/stress/phi4-mini/custom-20261007-1950/run1.jtl`
- `results/stress/phi4-mini/custom-20261007-1950/run1.jmeter.log`
- `results/stress/phi4-mini/custom-20261007-1950/run1.meta.json`
- `results/stress/phi4-mini/custom-20261007-1950/run1.timeline.csv`
- `results/stress/phi4-mini/custom-20261007-1950/run1.timeline.png`
- `results/stress/reconciliation.csv`