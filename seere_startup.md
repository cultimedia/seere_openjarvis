# 🏇 SEERE — Startup Reference
*Dispatch Intelligence · OpenJarvis · Startup Reference*

---

## Three-Layer Stack

| Port | Layer | Role |
|------|-------|------|
| `8080` | MLX Server | Qwen3.5-27B-4bit orchestrator |
| `8000` | Seere Backend | OpenJarvis FastAPI server |
| `5173` | Frontend UI | Browser interface |

---

## Startup Sequence

> **Always start MLX first.** It takes the longest to load.

### Terminal 1 — MLX Orchestrator
```bash
cd ~/OpenJarvis
.venv/bin/mlx_lm.server --model mlx-community/Qwen3.5-27B-4bit --port 8080
```
⏳ Wait for: `Started server on http://0.0.0.0:8080`

### Terminal 2 — Seere Backend
```bash
cd ~/OpenJarvis
.venv/bin/jarvis serve --port 8000
```
**Note:** Use `.venv/bin/jarvis` directly — avoids dependency resolution on every run.

### Terminal 3 — Frontend
```bash
cd ~/OpenJarvis/frontend
npm run dev
```

---

## Access

| | URL |
|---|---|
| **Browser UI** | http://localhost:5173/ |
| **API Docs** | http://localhost:8000/docs |

**If servers are still running:** just reopen `localhost:5173` — Seere is ready immediately.

### Quick Health Check

Once all three terminals are running:

```bash
# Check MLX orchestrator
curl http://localhost:8080/health

# Check Seere backend
curl http://localhost:8000/health

# Check frontend
curl -s http://localhost:5173 | grep -q "<!doctype html" && echo "Frontend OK"
```

All three should respond successfully.

### Agent Scheduler Status

When Seere backend starts, look for this line in Terminal 2:
```
  Scheduler: active
```

This confirms **warden** (OMMA compliance monitoring) is automatically running:
- Polls keith@legacycult.com and compliance@legacycult.com every 30 minutes
- Fires macOS notifications for CRITICAL alerts (@omma.ok.gov senders)
- Logs all findings to Seere memory with severity tags
- No manual intervention required — runs automatically when backend is active

**Verify warden status:**
```bash
jarvis agents status | grep warden
# Should show: warden   idle   every 1800s   ...
```

---

## Persona Verification

Send: **"Who are you?"**

Expected response:
> *"I am Seere, the dispatch intelligence of this OpenJarvis instance. I answer to the architect."*

---

## First Time Setup

If you haven't installed dependencies yet:

```bash
cd ~/OpenJarvis

# Remove any existing lockfile that might have vLLM
rm -f uv.lock

# Install ONLY MLX backend (not vLLM — they conflict)
uv sync --extra inference-mlx --extra server --extra tools-search
```

**If you see a dependency conflict error**, the venv is likely fine already — just use `.venv/bin/jarvis serve` directly (see Terminal 2 above).

---

## Troubleshooting

### `uv sync` fails with MLX/vLLM conflict

**Symptom:**
```
mlx-lm[inference-mlx] and openjarvis[inference-vllm] are incompatible
```

**Cause:** MLX requires `transformers>=5.0`, vLLM requires `transformers<5.0`

**Fix:** Seere only needs MLX on Apple Silicon. Skip the sync — just use `.venv/bin/jarvis serve` directly.

### MLX server fails: `Model type qwen3_5 not supported`

**Cause:** `mlx-lm<0.30.7` (Qwen3.5 support added in 0.30.7)

**Fix:**
```bash
.venv/bin/pip install 'mlx-lm>=0.30.7'
```

### Port already in use

**Check what's running:**
```bash
lsof -i :8080  # MLX
lsof -i :8000  # Backend
lsof -i :5173  # Frontend
```

**Kill and restart:**
```bash
kill -9 <PID>
```

### Tools not executing (Seere narrates instead)

**Symptom:** Seere says "I would use the web_search tool..." but doesn't actually execute it.

**Cause:** Orchestrator mode mismatch in config.

**Fix:**
```bash
# Check your config
grep "mode" ~/.openjarvis/config.toml

# Should show:
# [orchestrator]
# mode = "function_calling"

# If it says "structured", change it to "function_calling"
# Then restart Terminal 2
```

---

## Memory Backend Setup (Optional)

If you want Seere to remember information across sessions and search a knowledge base:

### 1. Build Rust Extension

```bash
cd ~/OpenJarvis/rust/crates/openjarvis-python
../../../.venv/bin/maturin develop
```

### 2. Configure Memory

Add to `~/.openjarvis/config.toml`:
```toml
[agent]
context_from_memory = true

[memory]
default_backend = "sqlite"
db_path = "~/.openjarvis/memory.db"
```

Update tools list:
```toml
[agent]
tools = "think,calculator,web_search,web_fetch,news_search,memory_search,memory_retrieve"
```

### 3. Index Your Knowledge Base

```bash
# Create a folder for your KB documents
mkdir -p ~/OpenJarvis/seere_kb

# Add markdown files to the folder, then:
.venv/bin/jarvis memory index ~/OpenJarvis/seere_kb/
```

### 4. Restart Backend (Terminal 2)

```bash
pkill -f "jarvis serve"
.venv/bin/jarvis serve --port 8000 &
```

**Verify:** Backend logs should show "Memory: active"

### Test Memory

```bash
.venv/bin/jarvis memory search "your query"
```

Now Seere can automatically search your knowledge base when you ask questions!

---

## Notes

```
# Ollama runs automatically — no manual start needed
# MLX takes longest to load — always start it first
# Seere identity lives in: openjarvis/prompt_registry.py
# Contract spec: ~/OpenJarvis/SEERE_CONTRACT.md
```

---

## Repository

https://github.com/cultimedia/seere_openjarvis

---

*"Passes over the whole earth in the twinkling of an eye."*
