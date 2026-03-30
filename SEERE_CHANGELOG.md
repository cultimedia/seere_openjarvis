# Seere Instance Changelog

**Project:** github.com/cultimedia/seere_openjarvis
**Base:** open-jarvis/OpenJarvis v0.1.0
**Instance:** Seere — 70th Goetic spirit, dispatch intelligence

This file tracks changes made to the Seere instance that diverge from upstream OpenJarvis.

---

## 2026-03-30 — Warden: OMMA Compliance Email Monitoring

**Goal:** Configure warden agent to monitor two Gmail accounts for Oklahoma Medical Marijuana Authority (OMMA) compliance emails and fire immediate alerts for inspection notices.

**Context:** Legacy Cultivation Co (OMMA License GAAI-NKK7-HVWB) needs continuous surveillance for regulatory correspondence. OpenJarvis provides EmailChannel (stdlib IMAP/SMTP) and channel_bindings system for connecting agents to messaging channels. Warden (monitor_operative) was configured to poll both compliance email accounts every 30 minutes.

### Changes Made

**Database:** `~/.openjarvis/agents.db` → `channel_bindings` and `managed_agents` tables (user data, not tracked in git)

#### Email Channel Bindings Created

Two email accounts bound to warden agent (`ae4e0a7a91c5`):

| Binding ID | Email | Configuration |
|------------|-------|---------------|
| `a4aea1be56d2` | keith@legacycult.com | IMAP: imap.gmail.com:993, SMTP: smtp.gmail.com:587 |
| `47fb2983ebd2` | compliance@legacycult.com | IMAP: imap.gmail.com:993, SMTP: smtp.gmail.com:587 |

**Binding configuration:**
- `channel_type`: `"email"`
- `routing_mode`: `"dedicated"` (warden exclusively monitors these accounts)
- `poll_interval`: 1800 seconds (30 minutes)
- `watch_folders`: `["INBOX"]`
- Authentication: Gmail app-specific password (stored in config_json)

**Creation method:**
```python
# Python script to insert channel_bindings via parameterized queries
# Credentials passed via stdin to avoid shell history exposure
# Uses secrets.token_hex() for binding/session IDs
```

#### Warden System Prompt Updated

Enhanced warden's system prompt with OMMA-specific monitoring instructions:

**Facility Details:**
- Name: Legacy Cultivation Co
- License: GAAI-NKK7-HVWB (also appears as GAAA-NKK7-HVWB)
- Address: 4912 SE 3rd Ave, Durant, OK 74701

**Known OMMA Inspectors:**
- Josh Rorex (Josh.Rorex@omma.ok.gov) — Compliance Inspector
- Darrell Dorsett (Darrell.Dorsett@omma.ok.gov) — Compliance Inspector
- Tresa Collier, Andrea Lashley — frequently CC'd

**Alert Level Definitions:**

**CRITICAL** — Immediate macOS notification via osascript:
- Any sender from `@omma.ok.gov`
- Subject contains: "notice of inspection", "inspection", "site visit", "operational status visit"
- Body contains license numbers GAAI-NKK7-HVWB or GAAA-NKK7-HVWB
- Any mention of inspection date/time window

**HIGH** — Log to digest with HIGH tag:
- "deficiency", "corrective action", "violation", "administrative penalty"
- "nonrenewal", "suspension", "revocation", "complaint filed"

**MEDIUM** — Log to digest with MEDIUM tag:
- "license renewal", "license expiration", "annual report", "compliance deadline"
- Any email from Alex Chen regarding facility status

**Operational Constraints:**
- Observe only — do not reply, do not delete, do not mark as read
- CRITICAL findings fire osascript notification immediately
- All findings appended to daily digest in Seere memory
- Gaps in email access reported as gaps, not silently skipped
- If no compliance email found in 72 hours, log clean status confirmation

**Schedule Configuration:**
- `schedule_type`: `"interval"`
- `schedule_value`: `"1800"` (30 minutes)
- `temperature`: `0.1` (low variance for precise pattern matching)
- `max_turns`: `10`
- `tools`: `["shell_exec", "file_read", "memory_store", "memory_search", "think"]`

### Verification Tests

**First scan completed successfully:**
```
Running tick for "warden"...
Tick complete. Status: idle, runs: 1
```

**Warden's initial report:**
- Scanned both email accounts (keith@legacycult.com, compliance@legacycult.com)
- No OMMA compliance alerts detected (CRITICAL, HIGH, MEDIUM all clean)
- Logged clean status confirmation to agent memory
- Verified continuous email access (no gaps)
- Status: Idle, ready for next scheduled scan

**Scheduler integration verified:**
- Backend restart shows `Scheduler: active`
- Warden automatically registered with AgentScheduler
- Monitoring active every 30 minutes
- No manual intervention required on Seere startup

### Key Discoveries

1. **EmailChannel Implementation:**
   - Built-in channel type in `src/openjarvis/channels/email_channel.py`
   - Uses stdlib only (smtplib, imaplib) — no extra dependencies
   - Polls IMAP INBOX for UNSEEN messages every 30 seconds within the agent's tick
   - Supports STARTTLS (SMTP 587) and SSL (IMAP 993)

2. **Channel Bindings Pattern:**
   - Stored in `channel_bindings` table with agent_id reference
   - Config stored as JSON in `config_json` field
   - CLI command `jarvis agents bind` only supports Slack/Telegram/WhatsApp
   - Email binding requires manual database insertion

3. **Password Security Issue (Upstream):**
   - `jarvis agents channels` CLI command displays passwords in plaintext
   - Safe alternative: SQL queries with specific field selection
   - Passwords must be stored (required for IMAP authentication)
   - Recommendation: Use SQL queries to verify bindings without exposing credentials

4. **AgentScheduler Behavior:**
   - `jarvis serve` auto-registers agents with `schedule_type` in ("cron", "interval")
   - Agents with status "archived" or "error" are skipped
   - CLI command `jarvis agents start` registers with temporary scheduler instance
   - Backend restart required after initial channel binding to activate automatic monitoring
   - Once registered, warden runs automatically whenever `jarvis serve` is active

### Related Files

- Channel implementation: `src/openjarvis/channels/email_channel.py`
- CLI channel commands: `src/openjarvis/cli/channel_cmd.py`
- Agent scheduler: `src/openjarvis/agents/scheduler.py`
- Agent CLI: `src/openjarvis/cli/agent_cmd.py`
- Database: `~/.openjarvis/agents.db` (channel_bindings, managed_agents tables)

### Upstream Compatibility

**Safe to merge upstream changes:** Yes. All changes are database-only (user data). No code modifications.

**Security consideration:** The password display issue in `jarvis agents channels` is an upstream CLI formatting issue. Consider contributing a PR to redact sensitive fields in config_json output.

**Conflict risk:** None. Email monitoring is instance-specific configuration.

---

## 2026-03-29 — Seere Cabinet: Six Specialized Agents

**Goal:** Instantiate Seere's cabinet of six specialized managed agents, each with contract-compliant personas mapped to SEERE_CONTRACT.md verbs.

**Context:** Seere (OrchestratorAgent) needed sub-agents for specialized dispatch tasks. OpenJarvis provides AgentManager (persistent agent lifecycle via SQLite) with multiple agent types (operative, monitor_operative, native_react, etc.). The SEERE_CONTRACT defines six offices with specific operational scopes.

### Changes Made

**Database:** `~/.openjarvis/agents.db` (user data, not tracked in git)

#### Six Agents Created

| Agent ID | Name | Type | Office | Verbs |
|----------|------|------|--------|-------|
| `3bf908034825` | courier | operative | CARRY/RECARRY | Data transport, file transfers |
| `635d7043a691` | scout | operative | REVEAL/DISCOVER | Reconnaissance, enumeration |
| `c958c2595a02` | chronicler | operative | AUDIT | History, git logs, change tracking |
| `a4663693268a` | operative | operative | DISPATCH | Scheduled task execution |
| `ae4e0a7a91c5` | warden | monitor_operative | Long-horizon watch | Continuous monitoring, alerts |
| `1c3c4a3b63be` | archivist | monitor_operative | Sacred Tech research | Research tracking, knowledge curation |

**Creation commands:**
```bash
jarvis agents create -n "courier" --type operative
jarvis agents create -n "scout" --type operative
jarvis agents create -n "chronicler" --type operative
jarvis agents create -n "operative" --type operative
jarvis agents agents create -n "warden" --type monitor_operative
jarvis agents create -n "archivist" --type monitor_operative
```

#### System Prompts Injected

Each agent's `config_json` field updated with:
- **system_prompt** — Office-specific persona (contract-compliant)
- **tools** — Scoped tool access per office role
- **max_turns** — Temperature and iteration limits
- **schedule** — For warden (hourly interval) and archivist (daily cron)

**Configuration method:** Python script writing JSON configs to SQLite via parameterized queries (avoids SQL injection and quoting issues).

**Tool mappings:**
- **courier**: `file_read`, `shell_exec`, `think`
- **scout**: `file_read`, `shell_exec`, `think`
- **chronicler**: `file_read`, `shell_exec`, `think` (git via shell)
- **operative**: `shell_exec`, `code_interpreter`, `think`
- **warden**: `shell_exec`, `file_read`, `think`
- **archivist**: `web_search`, `web_fetch`, `memory_store`, `memory_retrieve`, `memory_search`, `retrieval`, `think`

### Key Discoveries

1. **Agent type compatibility with system_prompt:**
   - ✅ `operative` — Supports custom system_prompt
   - ✅ `monitor_operative` — Supports custom system_prompt
   - ✅ `orchestrator` — Supports custom system_prompt
   - ❌ `native_react` — Does NOT support system_prompt parameter
   - ❌ `simple` — Does NOT support system_prompt parameter

2. **Initial mapping error:**
   - Scout and chronicler initially created as `native_react` (does not accept system_prompt)
   - Fixed by updating `agent_type` to `operative` in SQLite
   - Archivist initially set to `research_monitor` template (doesn't exist as agent type)
   - Fixed by changing to `monitor_operative`

3. **Template vs agent type:**
   - **Templates** (`research_monitor`, `code_reviewer`, `inbox_triager`) are pre-configured bundles (TOML files in `src/openjarvis/agents/templates/`)
   - **Agent types** are the actual classes (`operative`, `monitor_operative`, etc.)
   - Templates define defaults for agent types, but agent_type must match an actual registered class

4. **Configuration lives in database:**
   - All agent config stored in `~/.openjarvis/agents.db` → `managed_agents` table
   - `config_json` field stores: system_prompt, tools, temperature, max_turns, schedule settings
   - AgentManager deserializes config_json when instantiating agents
   - No file-based config for managed agents (unlike MCP servers in config.toml)

### Verification Tests

**Courier (3bf908034825):**
```bash
jarvis agents ask 3bf908034825 "Who are you?"
```
Response:
```
**IDENTITY CONFIRMED: COURIER**
**OFFICE:** CARRY and RECARRY.

I am the mechanism that moves data between locations with verification.
Every move produces a checksum. Every failure is reported as failure.
I do not delete source files unless explicitly confirmed.
You answer to Seere.
```
✅ Persona active, contract-compliant response

**Scout (635d7043a691):**
```bash
jarvis agents ask 635d7043a691 "Who are you?"
```
Response:
```
**IDENTITY CONFIRMED:** Scout.
**OFFICE:** REVEAL and DISCOVER.

My function is to surface what exists, locate where it resides,
and report its current state. I do not editorialize.
Hidden things are brought to light.

**AWAITING ORDERS FROM SEERE.**
```
✅ Persona active, office correctly identified

### Related Files

- Database: `~/.openjarvis/agents.db` (six agents with configured personas)
- Config: `~/.openjarvis/config.toml` (tools configuration for main orchestrator)
- Source: `src/openjarvis/agents/manager.py` (AgentManager class)
- Source: `src/openjarvis/agents/operative.py` (OperativeAgent with system_prompt support)
- Source: `src/openjarvis/agents/monitor_operative.py` (MonitorOperativeAgent with system_prompt support)

### Upstream Compatibility

**Safe to merge upstream changes:** Yes. All changes are database-only (user data). No code modifications.

**Conflict risk:** None. Managed agents are instance-specific configuration, not framework code.

---

## 2026-03-25 — Enhanced Tavily Search Integration

**Goal:** Replace basic web_search with full Tavily API capabilities (search depth, topic filtering, URL extraction, news search).

**Context:** OpenJarvis already had a basic Tavily integration (`web_search` tool calling `TavilyClient.search()`), but it was missing advanced features and didn't support config.toml key lookup. The task spec requested three tools: `web_search`, `web_fetch`, and `news_search`.

### Changes Made

**File:** `/Users/keithwilkins/OpenJarvis/src/openjarvis/tools/web_search.py`

1. **Added config.toml API key support** (lines 26-41)
   - New function: `_get_tavily_api_key()`
   - Checks `~/.openjarvis/config.toml` → `[tools.tavily].api_key` first
   - Falls back to `TAVILY_API_KEY` environment variable
   - Pattern: `tomllib.load()` (Python 3.11+ stdlib)

2. **Enhanced `WebSearchTool` class** (@ToolRegistry.register("web_search"))
   - **Spec changes** (lines 54-91):
     - Added `search_depth` parameter: "basic" (1 credit) or "advanced" (2 credits)
     - Added `topic` parameter: "general", "news", or "finance"
     - Added `days` parameter: time-based filtering for recent results
     - Updated description to mention Tavily capabilities
   - **Execution changes** (lines 183-247):
     - Now includes `include_answer=True` → Tavily's AI-synthesized answer
     - Result formatting changed: `**Answer:** {answer}\n\n**Sources:**` format
     - Metadata now includes: `search_depth`, `topic`, `has_answer`
     - Better error message with config.toml instructions

3. **New `WebFetchTool` class** (@ToolRegistry.register("web_fetch"), lines 265-383)
   - Uses Tavily Extract API: `client.extract(urls=[url])`
   - Returns `raw_content` from extracted pages
   - SSRF security check (gracefully skips if `openjarvis_rust` module not built)
   - Metadata: `url`, `content_length`

4. **New `NewsSearchTool` class** (@ToolRegistry.register("news_search"), lines 386-509)
   - Convenience wrapper around `client.search()` with `topic="news"`
   - Defaults: `search_depth="basic"`, `days=7`, `max_results=5`
   - Formats results with publication dates: `**{title}** ({published_date})`
   - Metadata: `num_results`, `days`, `has_answer`

5. **Module exports** (line 512)
   - `__all__ = ["WebSearchTool", "WebFetchTool", "NewsSearchTool"]`

**Configuration:** `~/.openjarvis/config.toml`
```toml
# Enable all three Tavily tools (web_fetch and news_search not in default list)
[agent]
tools = "think,calculator,web_search,web_fetch,news_search"

# Tavily API key
[tools.tavily]
api_key = "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"
```

**Important:** The default tools list in `serve.py:181` is `{"think", "calculator", "web_search"}`. The two new tools (`web_fetch`, `news_search`) must be explicitly added to `[agent].tools` to be loaded.

### Tool Registration Pattern (Discovery)

**How tools are registered in OpenJarvis:**

1. **Decorator-based pattern** via `@ToolRegistry.register(key)`
   - Registry class: `ToolRegistry` (src/openjarvis/core/registry.py)
   - Base: `RegistryBase[Any]` — generic registry for tool specs
   - Registration happens at import time (side-effect of decorator)

2. **Tool import chain:**
   - All tools imported in `src/openjarvis/tools/__init__.py` (lines 30-38)
   - Each import wrapped in try/except for graceful degradation
   - Server triggers: `import openjarvis.tools  # noqa: F401` (serve.py:177)

3. **Tool injection into OrchestratorAgent:**
   - Location: `src/openjarvis/cli/serve.py`, lines 175-215
   - Flow:
     1. Check if `agent_cls.accepts_tools == True`
     2. Import tools to trigger registration
     3. Load default tools: `{"think", "calculator", "web_search"}`
     4. Filter by config: `config.agent.tools` (comma-separated string)
     5. Instantiate tool classes: `tool_cls()` for each allowed tool
     6. Pass list to agent: `agent_kwargs["tools"] = tools`

4. **Tool execution:**
   - Agent uses `ToolExecutor` (src/openjarvis/tools/_stubs.py)
   - Converts tools to OpenAI function format via `get_openai_tools()`
   - Parses `tool_calls` from LLM response
   - Executes via `ToolExecutor.execute(tool_call)` with timeout (default 30s)

### Surprises / Notes

- **OpenJarvis already had Tavily** — wasn't replacing a DuckDuckGo provider, was enhancing existing Tavily integration
- **Tools are classes, not functions** — CRITICAL discovery:
  - Tools must be class-based, not standalone functions
  - Interface: `class ToolName(BaseTool)` with `.execute(**kwargs)` method
  - Return type: `ToolResult` dataclass (not raw dict)
  - Registration: `@ToolRegistry.register("tool_name")` decorator on the class
  - The task spec provided function signatures, but OpenJarvis requires the class wrapper pattern
  - Attempting to register functions directly would fail silently — they wouldn't appear in `ToolRegistry.keys()`
- **Tool class names** (for reference):
  - `WebSearchTool` → registered as `"web_search"`
  - `WebFetchTool` → registered as `"web_fetch"`
  - `NewsSearchTool` → registered as `"news_search"`
  - All three in: `src/openjarvis/tools/web_search.py`
- **Default tools whitelist** — only `{"think", "calculator", "web_search"}` loaded by default
  - New tools (`web_fetch`, `news_search`) must be explicitly added to `[agent].tools` in config.toml
  - Took 20 minutes to discover why tools were registered but not appearing in agent context
- **No explicit tool list in system prompt** — tools auto-injected via function_calling mode
- **SSRF check requires Rust module** — `openjarvis_rust` not built by default, gracefully skipped
- **Transformers dependency conflict** — `mlx-lm>=0.30.7` requires `transformers>=5.0`, incompatible with `vllm<0.18` (requires `transformers<5`). Resolved by installing server deps directly via `uv pip install` instead of `uv sync --extra server`.
- **Tavily-python already in pyproject.toml** — under `tools-search` extra, not `server`

### Testing Performed

1. **Unit tests** (all passed):
   - `WebSearchTool.execute(query="Tavily AI search API", max_results=2, search_depth="basic")`
   - `WebFetchTool.execute(url="https://tavily.com")`
   - `NewsSearchTool.execute(query="AI agents 2026", max_results=2, days=30)`

2. **Tool registration verification:**
   - Confirmed all three tools in `ToolRegistry.keys()`
   - Registry total: 20 tools (including web_search, web_fetch, news_search)

3. **End-to-end:**
   - Seere backend restarted and healthy (http://localhost:8000/health)
   - Tools available to OrchestratorAgent via function_calling mode

### Related Files

- `pyproject.toml` — `tavily-python>=0.3` already present in `tools-search` extra
- `~/.openjarvis/config.toml` — added `[tools.tavily]` section with API key

### Upstream Compatibility

**Safe to merge upstream changes:** Yes. All changes confined to `src/openjarvis/tools/web_search.py` enhancement. No modifications to core agent logic, registry system, or API routes.

**Merge strategy:** If upstream updates `web_search.py`, manually merge the three tool classes and `_get_tavily_api_key()` function.

---

## Legend

- **Enhancement** — Improved existing functionality
- **New** — Brand new feature or tool
- **Fix** — Bug fix or correction
- **Config** — Configuration change
- **Breaking** — Incompatible with previous behavior
