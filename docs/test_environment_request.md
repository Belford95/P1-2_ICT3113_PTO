# CPU/GPU Check — Instructions for Service Builder

The client requires CPU-only inference (no GPU). Your machine has an NVIDIA RTX 4060, which Docker shouldn't be using — but this needs to be confirmed, not assumed.

## Steps

**0. Open a terminal inside the project folder** (where `docker-compose.yml` is) — steps 2–4 need this, since they read `.env`/`docker-compose.yml` there. Step 1 and 5 work from anywhere, but keep the same terminal open throughout for simplicity.

**1. Pull one model** (any of the four candidates works, this one's small and fast):
```bash
docker exec ollama ollama pull llama3.2:1b
```

**2. Set it in `.env`:**
```
MODEL=llama3.2:1b
```

**3. Restart the service to pick it up:**
```bash
docker compose up -d service
```

**4. Send a test ticket:**
```bash
curl -X POST localhost:8000/tickets -H "Content-Type: application/json" -d "{\"narrative\":\"I was charged a late fee on my credit card twice\"}"
```

**5. Immediately check which processor it used:**
```bash
docker exec ollama ollama ps
```

## What to look for

In the `ollama ps` output, check the `PROCESSOR` column:
- **`100% CPU`** → correct, send me this output.
- **Any GPU percentage** (e.g. `50%/50% CPU/GPU`, `100% GPU`) → the GPU is being used; let me know and don't run any benchmarks yet.
