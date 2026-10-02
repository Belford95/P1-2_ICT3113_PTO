# Candidate Models

**Status: DRAFT.** Tags, sizes and licences below are proposals from general knowledge and must be verified on the Ollama library pages before the freeze. Digests are filled in by `scripts/pin_models.py` (it writes `results/model_pins.md`); nothing here is final until that is committed.

How the service uses them: it runs one candidate at a time. Set `MODEL=<tag>` in `.env`, then run `docker compose up -d service`.

## Selection criteria

The client's constraint is CPU-only commodity servers with no public API, so the question is which model gives acceptable accuracy at acceptable CPU latency.

1. **Size classes.** At least two required; we span three (about 1B, about 3-4B, about 7B) so the speed/accuracy trade-off is visible rather than avoided.
2. **Runs on the test machine.** Quantised weights plus the 2,048-token context must fit in RAM alongside Docker and the OS. See the RAM column; check against the test host's real RAM (`docker info`).
3. **Structured output.** The service uses Ollama's JSON-schema `format`, so every candidate must return valid category JSON. Confirm each model does so in a smoke test on made-up text (not on golden-set rows).
4. **Context.** Longest narrative is about 2,000 characters (about 480 tokens), so a 2,048-token window suffices for any candidate.
5. **Licence.** Must permit our use, and any required acknowledgement goes on Slide 12.
6. **Family diversity.** Avoid a set that is only one family scaled up, so results are not just "same model, different size".

## Proposed candidate set

| # | Ollama tag | Size class | Params (pulled) | Quant (pulled) | Weights (GB, pulled) | Family / vendor | Licence (verify) | Digest |
|---|---|---|---|---|---|---|---|---|
| 1 | `llama3.2:1b` | ~1B (small) | 1.2B | Q8_0 | 1.32 | Llama, Meta | Llama 3.2 Community Licence ✅ verified | `baf6a787fdff` ✅ |
| 2 | `llama3.2:3b` | ~3B (medium) | 3.2B | Q4_K_M | 2.02 | Llama, Meta | Llama 3.2 Community Licence ✅ verified | `a80c4f17acd5` ✅ |
| 3 | `phi4-mini:latest` | ~3.8B (medium) | 3.8B | Q4_K_M | 2.49 | Phi, Microsoft | MIT ✅ verified | `78fad5d182a7` ✅ |
| 4 | `qwen2.5:7b` | ~7B (large) | 7.6B | Q4_K_M | 4.68 | Qwen, Alibaba | Apache License 2.0 ✅ verified | `845dbda0ea48` ✅ |

All four confirmed pulled and pinned via `scripts/pin_models.py` on 2026-10-01 (Ollama server 0.35.0; full output in `results/model_pins.md` / `results/model_pins.json`). Note `llama3.2:1b` alone pulled at **Q8_0**, not Q4_K_M like the other three — Ollama's default tag isn't the same compression level across models, so don't assume uniform quantisation when predicting relative latency.

### Llama 3.2 Community Licence — what Slide 12 actually needs to do

One licence covers both `llama3.2:1b` and `llama3.2:3b` (full text fetched from `ollama.com/library/llama3.2:1b`, "Details" section). Two obligations apply to us (Section 1.b of the agreement):

1. **Display "Built with Llama"** prominently somewhere the product/report is presented — put this on **Slide 12** and in the repo `README.md`.
2. **Include this attribution notice verbatim**, in a Notice file or on Slide 12:
   > Llama 3.2 is licensed under the Llama 3.2 Community License, Copyright © Meta Platforms, Inc. All Rights Reserved.

Not applicable to us: the >700M monthly-active-users commercial clause (Section 2), and the "Llama" naming requirement (only applies if we fine-tune and redistribute a derivative model, which we don't).

### phi4-mini licence — MIT (verified)

Copyright (c) Microsoft Corporation. Full text confirmed via `ollama.com/library/phi4-mini`. Standard MIT: free use, copy, modify, merge, publish, distribute, sublicense and sell, on the single condition that **the copyright notice and permission text are included in all copies or substantial portions of the software**. No "as used in" branding obligation like Llama's. For Slide 12: cite "MIT License, Copyright (c) Microsoft Corporation" and keep the notice text available in the repo (e.g. alongside this file) to satisfy the inclusion condition.

### qwen2.5:7b licence — Apache License 2.0 (verified)

Copyright 2024 Alibaba Cloud. Full text confirmed via `ollama.com/library/qwen2.5:7b`. Standard Apache-2.0: free use, reproduction, modification and distribution, with conditions on redistribution only (Section 4) — give recipients a copy of the licence, mark any changed files, and retain existing copyright/attribution notices. No obligation triggers for us since we are not redistributing modified source, only running the published weights via Ollama. For Slide 12: cite "Apache License 2.0, Copyright 2024 Alibaba Cloud".

Reserve options if one fails the smoke test or does not fit in RAM: `llama3.1:8b` (Llama 3.1 Community Licence), `gemma3:4b` (Gemma terms), `qwen2.5:3b`.

## Justification of the set (for Slide 5)

The brief asks for candidates that "make the trade-off visible rather than avoid it" — smaller models faster but wrong more often, larger models slower and more accurate. The set is built to produce that ladder, not to find one "best" model:

1. **Spans at least two size classes (required); we use three.** ~1B, ~3-4B and ~7B gives three points on the curve instead of two, so the accuracy-vs-latency trend is visible rather than a single before/after comparison.

2. **The constraint is CPU-only, no GPU, no public API** (client compliance rule — ticket data cannot leave their infrastructure). On CPU, token-generation speed is dominated by memory bandwidth, so latency scales roughly with weight size: ~1.3 GB vs an expected ~2-2.5 GB vs ~4.5-5 GB at the quantisations we pull is itself the latency prediction's basis (see `predictions/prediction_record.md`). This is also why we stop at ~7B: anything larger (e.g. 13B+) would very likely breach any workable latency requirement on commodity CPU hardware and risks not fitting in RAM at all, so including it would not be a real candidate, just padding the set.

3. **Isolating size from family.** #1 and #2 are the same family (Llama 3.2) at two sizes, so the difference between them is attributable to size alone. #3 (Phi, Microsoft) sits at a similar size to #2 but a different family/training recipe, so comparing #2 vs #3 isolates the effect of *how* a model was built, not just how big it is. #4 (Qwen, Alibaba) is a third family entirely, at the top of the range. This stops the result from being "one family, scaled up", which would understate how much training recipe matters versus raw size.

4. **Fits the workload.** Per `docs/workload_model.md`, the p99 narrative is ~1,922 characters (~480 tokens), comfortably inside the 2,048-token context every candidate runs at (`docs/service_design.md`), so no candidate is handicapped by truncation — the accuracy comparison is about the model, not the context window.

5. **All four support structured output** (Ollama JSON-schema `format`), required because the service constrains every reply to the 7 category names — confirmed per-candidate by a smoke test on made-up text before pinning.

6. **Licences are compatible with coursework use.** Llama 3.2 (both #1 and #2) requires a "Built with Llama" notice and a verbatim attribution line, both to appear on Slide 12 (see above); Phi and Qwen's licences (MIT / Apache-2.0) impose no such obligation, but their exact licence text on the Ollama library page is still to be confirmed (see Open items).

## Pinning procedure

1. Start the stack: `docker compose up -d --build` (with the Ollama image tag pinned, see TODO in `docker-compose.yml`).
2. `python scripts/pin_models.py llama3.2:1b llama3.2:3b phi4-mini qwen2.5:7b`
3. Commit `results/model_pins.json` and `results/model_pins.md`, and copy the digests into the table above.
4. Record the Ollama server version (the script writes it) on Slide 7.

## Open items

- [x] Confirm each tag exists, pull it, and pin tag + digest — done 2026-10-01, all four confirmed.
- [x] Smoke-test each model on made-up text: loads, fits, returns valid category JSON — done, all four returned "Credit card" correctly for the same test sentence.
- [x] Llama 3.2 licence verified (full text fetched from the model page); attribution obligations written up above.
- [x] phi4-mini licence verified: MIT, Copyright (c) Microsoft Corporation.
- [x] qwen2.5:7b licence verified: Apache License 2.0, Copyright 2024 Alibaba Cloud.
- [ ] Confirm the test machine's RAM and CPU (drives the size ceiling and the latency predictions).
- [ ] Freeze with the rest of the gate.
