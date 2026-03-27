# Claude Code Task: Upgrade Seere's Search Tools with Tavily

**Project:** ~/OpenJarvis  
**Goal:** Replace or augment OpenJarvis's basic web_search tool with Tavily — a search API
designed specifically for AI agents that returns structured, citation-ready results with
full page content extraction in a single call.

---

## Context

Seere currently has a `web_search` tool that works but returns results in a normalized format
that hides provider metadata and offers no configuration (depth, topic, domain filtering, etc.).
The underlying provider is unknown and may be DuckDuckGo or a basic scraper.

Tavily is purpose-built for this use case:
- Returns full page content (not just URLs/snippets) — no separate scraping step needed
- Supports search depth (basic vs. advanced), topic filtering (general/news/finance), date ranges
- Provides source citations and an AI-synthesized answer alongside results
- Has a free tier: 1,000 credits/month, no credit card required
- Python SDK: `tavily-python`

**API key needed before starting:**
You (the architect) must get a free Tavily API key at https://app.tavily.com/
It will start with `tvly-`. You'll need to provide it to CC before Phase 3.

---

## Phase 1: Audit the Existing Search Tool

### 1.1 Find what web_search currently does
```bash
# Locate the search tool implementation
find ~/OpenJarvis/src -name "*.py" | xargs grep -l "web_search\|WebSearch\|search" | head -20

# Read the tool definition
find ~/OpenJarvis/src -path "*/tools/*search*"
cat ~/OpenJarvis/src/openjarvis/tools/web_search.py 2>/dev/null || \
  find ~/OpenJarvis/src -name "*.py" | xargs grep -l "def web_search\|class WebSearch" | head -5
```

### 1.2 Understand how tools are registered
```bash
# Find the tool registry / how tools are registered with agents
find ~/OpenJarvis/src -name "*.py" | xargs grep -l "register.*tool\|tool_registry\|TOOL_MAP\|available_tools" | head -10

# Check how tools get injected into the OrchestratorAgent
find ~/OpenJarvis/src -name "*.py" | xargs grep -l "OrchestratorAgent" | head -5
# Then read how tools are passed in
```

### 1.3 Document what you find
Note:
- The file path of the current web_search implementation
- How tools are registered (decorator, dict, explicit list?)
- Whether tools have a standard interface (function signature, return format)

---

## Phase 2: Install Tavily

```bash
cd ~/OpenJarvis

# Install Tavily Python SDK
uv pip install tavily-python

# Verify
.venv/bin/python -c "from tavily import TavilyClient; print('Tavily installed OK')"
```

### 2.1 Add to pyproject.toml (so it persists through uv sync)
Find the `[project.optional-dependencies]` section in pyproject.toml and add `tavily-python`
to an appropriate extra (probably `server` or a new `tools` extra):

```toml
[project.optional-dependencies]
# ... existing extras ...
server = [
  # ... existing deps ...
  "tavily-python",
]
```

---

## Phase 3: Implement Tavily Search Tools

Create `~/OpenJarvis/src/openjarvis/tools/tavily_search.py`:

```python
"""
Tavily search tools for Seere/OpenJarvis.

Tavily is a search API designed for AI agents — returns structured results
with full page content extraction in a single call. No separate scraping needed.

Requires TAVILY_API_KEY in ~/.openjarvis/config.toml:
  [tools.tavily]
  api_key = "tvly-your-key-here"
"""

import os
from typing import Optional
from tavily import TavilyClient

def _get_client() -> TavilyClient:
    """Get Tavily client, checking config.toml then env var."""
    # Try config.toml first (OpenJarvis convention)
    try:
        import tomllib
        config_path = os.path.expanduser("~/.openjarvis/config.toml")
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
        api_key = config.get("tools", {}).get("tavily", {}).get("api_key")
    except Exception:
        api_key = None

    # Fall back to env var
    if not api_key:
        api_key = os.environ.get("TAVILY_API_KEY")

    if not api_key:
        raise RuntimeError(
            "Tavily API key not found. Add to ~/.openjarvis/config.toml:\n"
            "  [tools.tavily]\n"
            "  api_key = 'tvly-your-key-here'\n"
            "Or set TAVILY_API_KEY environment variable."
        )

    return TavilyClient(api_key=api_key)


def web_search(
    query: str,
    max_results: int = 5,
    search_depth: str = "basic",
    topic: str = "general",
    include_answer: bool = True,
    include_domains: Optional[list] = None,
    exclude_domains: Optional[list] = None,
    days: Optional[int] = None,
) -> dict:
    """
    Search the web using Tavily. Returns structured results with full page content.

    Args:
        query: The search query
        max_results: Number of results to return (1-20, default 5)
        search_depth: "basic" (fast, 1 credit) or "advanced" (thorough, 2 credits)
        topic: "general", "news", or "finance"
        include_answer: Include Tavily's AI-synthesized answer (recommended: True)
        include_domains: Restrict results to these domains (e.g. ["arxiv.org", "github.com"])
        exclude_domains: Exclude these domains from results
        days: Limit results to the past N days (useful for news)

    Returns:
        dict with keys:
          - answer: AI-synthesized answer string (if include_answer=True)
          - results: list of {title, url, content, score, published_date}
          - query: the original query
          - response_time: seconds taken
    """
    client = _get_client()
    kwargs = dict(
        query=query,
        max_results=max_results,
        search_depth=search_depth,
        topic=topic,
        include_answer=include_answer,
    )
    if include_domains:
        kwargs["include_domains"] = include_domains
    if exclude_domains:
        kwargs["exclude_domains"] = exclude_domains
    if days:
        kwargs["days"] = days

    response = client.search(**kwargs)
    return response


def web_fetch(url: str) -> dict:
    """
    Fetch and extract clean content from a specific URL using Tavily Extract.

    Unlike web_search, this targets a known URL directly and returns the full
    cleaned text content — useful when Seere has a URL and needs to read the page.

    Args:
        url: The URL to fetch and extract content from

    Returns:
        dict with keys:
          - results: list of {url, raw_content}
          - failed_results: list of URLs that couldn't be extracted
    """
    client = _get_client()
    response = client.extract(urls=[url])
    return response


def news_search(query: str, max_results: int = 5, days: int = 7) -> dict:
    """
    Search specifically for recent news using Tavily.

    Convenience wrapper around web_search with topic="news".

    Args:
        query: The news search query
        max_results: Number of results (default 5)
        days: How many days back to search (default 7)

    Returns:
        Same format as web_search
    """
    return web_search(
        query=query,
        max_results=max_results,
        search_depth="basic",
        topic="news",
        include_answer=True,
        days=days,
    )
```

---

## Phase 4: Register the New Tools

### 4.1 Find and update tool registration

Based on what you found in Phase 1, register the three new tools
(`web_search`, `web_fetch`, `news_search`) from `tavily_search.py`.

**If tools are registered via a dict/map** (e.g. `TOOL_MAP = {...}`):
```python
from openjarvis.tools.tavily_search import web_search, web_fetch, news_search

TOOL_MAP = {
    # ... existing tools ...
    "web_search": web_search,       # replaces or augments existing
    "web_fetch": web_fetch,         # new
    "news_search": news_search,     # new
}
```

**If tools are registered via decorator** (e.g. `@tool`):
```python
from openjarvis.tools.tavily_search import web_search, web_fetch, news_search
# Register each:
tool(web_search)
tool(web_fetch)
tool(news_search)
```

**If there's a tool discovery pattern** (auto-imports from tools/):
The tools may register automatically once the file exists — verify by checking
if other tools in `src/openjarvis/tools/` are auto-discovered.

### 4.2 If the old web_search conflicts

If the existing `web_search` tool name conflicts, either:
- Replace the old implementation by modifying it to delegate to Tavily, or
- Rename the old one to `web_search_basic` and make Tavily the default `web_search`

Do not delete the old file without checking if it's imported elsewhere.

---

## Phase 5: Configure the API Key

Add the Tavily key to `~/.openjarvis/config.toml` (TOML only — no .env):

```toml
[tools.tavily]
api_key = "tvly-YOUR_KEY_HERE"
```

The architect will provide the actual key. Do not hardcode it anywhere.

**Verify it works:**
```bash
cd ~/OpenJarvis
.venv/bin/python -c "
from src.openjarvis.tools.tavily_search import web_search
result = web_search('OpenJarvis Stanford AI agent framework', max_results=2)
print('Answer:', result.get('answer', 'N/A')[:200])
print('Results:', len(result.get('results', [])))
print('First result:', result['results'][0]['title'] if result.get('results') else 'none')
"
```

---

## Phase 6: Update the Seere System Prompt (if needed)

Check `openjarvis/prompt_registry.py` — the Seere system prompt may need to reference
the new tools explicitly, or may auto-discover them. If Seere's tool list is hardcoded
in the prompt, add:

```
Your tools include:
- web_search(query, max_results, search_depth, topic, days): Search the web via Tavily.
  Use search_depth="advanced" for thorough research. Use topic="news" for recent events.
- web_fetch(url): Extract full content from a specific URL.
- news_search(query, days): Convenience wrapper for recent news.
```

---

## Phase 7: Verify End-to-End

With Seere running (all three terminals up), send these test dispatches:

**Test 1 — Basic search:**
```
"Seere, search for the latest OpenJarvis updates on GitHub"
```
Expected: Structured response with source URLs and summaries, not just "I found results"

**Test 2 — News search:**
```
"Seere, what's happening with Qwen models this week?"
```
Expected: Recent news results with dates

**Test 3 — Provider awareness:**
```
"Seere, what search tool are you using and what can it do?"
```
Expected: Seere should be able to describe Tavily, search depth options, etc.

**Test 4 — URL fetch:**
```
"Seere, fetch and summarize https://github.com/open-jarvis/OpenJarvis/blob/main/README.md"
```
Expected: Actual content from the page, not a generic response

---

## Notes

- Config key lives in `~/.openjarvis/config.toml` — TOML only, no .env
- The three tools are: `web_search` (general), `web_fetch` (URL targeting), `news_search` (convenience wrapper)
- Tavily free tier: 1,000 credits/month. Basic search = 1 credit. Advanced = 2 credits.
- Do not use `include_raw_content=True` by default — it massively inflates context size
- Log all changes in `SEERE_CHANGELOG.md`
- Update `CLAUDE.md` Tools section once complete — add Tavily to Key Conventions
