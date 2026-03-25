# Seere Instance Changelog

**Project:** github.com/cultimedia/seere_openjarvis
**Base:** open-jarvis/OpenJarvis v0.1.0
**Instance:** Seere — 70th Goetic spirit, dispatch intelligence

This file tracks changes made to the Seere instance that diverge from upstream OpenJarvis.

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
