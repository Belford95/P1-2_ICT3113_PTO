# A2 Memory Check: can two models stay resident?

**Date:** 2026-11-10 · **Run by:** Belford (service host, same laptop as Assignment 1)

Assignment 2 requires the cascade's small and large model to be loaded **at the same time**. If they
do not both fit, Ollama unloads one to load the other on every escalation, and the result measures
model loading rather than the cascade. This file is the evidence that they fit.

## 1. The machine and its limits (unchanged from Assignment 1)

| Item | Value | How checked |
|---|---|---|
| Host | AMD Ryzen 7 7745HX, 8C/16T, 31.7 GB RAM, Windows 11 | Assignment 1, Slide 7 |
| CPUs available to Docker | 16 | `docker info` |
| **RAM available to Docker** | **15.46 GiB** (16,605,859,840 bytes) | `docker info` |
| Ollama | 0.35.0 (image pinned `ollama/ollama:0.35.0`) | `docker exec ollama ollama --version` |
| GPU | RTX 4060 present, **not used**: every load below reports `100% CPU` | `ollama ps` |

The client is not providing more RAM or CPU, so this ceiling is fixed.

## 2. Ollama settings (set once, held constant for every A2 configuration)

| Variable | A1 | A2 | Why |
|---|---|---|---|
| `OLLAMA_MAX_LOADED_MODELS` | `1` | **`2`** | The cascade needs both models resident. Changed once, before any A2 run; applies to single-model configurations too |
| `OLLAMA_NUM_PARALLEL` | `1` | `1` | Unchanged: one inference at a time |
| `OLLAMA_KEEP_ALIVE` | `-1` | `-1` | Unchanged: models stay loaded, no reload between tickets |
| `NUM_CTX` (sent by the service) | 2048 | 2048 | Unchanged |

Verified in the running container with `docker exec ollama printenv`.

## 3. Model digests unchanged from Assignment 1

Checked 2026-11-10 with `docker exec ollama ollama list` after re-pulling. All four match
`results/model_pins.md`:

| Model | Digest | Disk size |
|---|---|---|
| `llama3.2:1b` | `baf6a787fdff` | 1.3 GB |
| `llama3.2:3b` | `a80c4f17acd5` | 2.0 GB |
| `phi4-mini:latest` | `78fad5d182a7` | 2.5 GB |
| `qwen2.5:7b` | `845dbda0ea48` | 4.7 GB |

## 4. Main result: the cascade pair at the service's real context size (2048)

Loaded **through `POST /tickets`** (run id `a2__memcheck`), which is how the models are loaded during
testing. Ollama was restarted first, so nothing was resident beforehand.

```
NAME                ID              SIZE      PROCESSOR    CONTEXT    UNTIL
phi4-mini:latest    78fad5d182a7    2.8 GB    100% CPU     2048       Forever
qwen2.5:7b          845dbda0ea48    4.9 GB    100% CPU     2048       Forever

CONTAINER ID   NAME      CPU %     MEM USAGE / LIMIT     MEM %
faf12f1c5fbe   ollama    0.01%     7.571GiB / 15.46GiB   48.95%
```

**Both models stay resident: 7.57 GiB of 15.46 GiB (49%), leaving ~7.9 GiB headroom.**
Both report `100% CPU`, and `UNTIL Forever` confirms `keep_alive = -1` took effect.

Each model answered normally while the other stayed loaded (ticket 1 → `Money transfer or service`
from `qwen2.5:7b`; ticket 2 → `Credit card` from `phi4-mini`), so neither evicted the other.

## 5. Supporting result: all three pairs at context 4096

Loaded directly through the Ollama API, which defaults to a 4096-token context: a **larger**
configuration than the service uses, so these figures are an upper bound.

| Pair | Reported sizes | Container memory | Both resident? |
|---|---|---|---|
| `qwen2.5:7b` + `phi4-mini` | 5.1 + 3.1 GB | 9.71 GiB / 15.46 (62.8%) | yes |
| `qwen2.5:7b` + `llama3.2:3b` | 5.1 + 2.6 GB | 7.58 GiB / 15.46 (49.0%) | yes |
| `qwen2.5:7b` + `llama3.2:1b` | 5.1 + 1.5 GB | 6.69 GiB / 15.46 (43.3%) | yes |

All three pairs fit even at 4096, every row showed `100% CPU` and `UNTIL Forever`.
**Any pair of our four candidates can be used in the cascade**, so memory does not constrain the
rule design. The largest pair at the real context size uses under half the available RAM.

## 6. Caveat found during the check: context size forces a reload

The first check loaded the models directly through `http://localhost:11434/api/generate`, which used
Ollama's default context of 4096 (visible in the table above). The service always sends
`num_ctx = 2048`. Ollama treats a different context size as a different load, so a model warmed at
4096 is unloaded and reloaded when the service then calls it at 2048, costing several seconds.

Consequences for the test procedure:

1. **Every warm-up, and the S measurement, goes through `POST /tickets`**, never directly to Ollama.
2. **Both calls in the cascade use the same `num_ctx` (2048).** If the small and large model were
   called with different context sizes they would reload repeatedly instead of coexisting.
3. Section 5's figures stay in this file as supporting evidence only; Section 4 is the operating
   configuration.

## 7. Outstanding: confirm no eviction under load

Sections 4 and 5 show both models resident at rest. After the first full cascade speed run, run
`docker exec ollama ollama ps` and `docker stats --no-stream ollama` again, before anything else,
and record the result here. Both models still listed with `UNTIL Forever` means nothing was evicted
mid-run.

| Check | Status |
|---|---|
| Both models resident at 2048 via the service | done, section 4 |
| All three pairs fit at 4096 | done, section 5 |
| Still both resident after a full cascade run | **pending first speed run** |
