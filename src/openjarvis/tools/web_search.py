"""Web search tools — Tavily API integration for Seere/OpenJarvis.

Provides three tools:
- web_search: General web search with configurable depth and topic filtering
- web_fetch: Direct URL content extraction
- news_search: Recent news search (convenience wrapper)

Requires TAVILY_API_KEY configured in ~/.openjarvis/config.toml:
  [tools.tavily]
  api_key = "tvly-your-key-here"

Or set TAVILY_API_KEY environment variable.
"""

from __future__ import annotations

import os
from typing import Any

from openjarvis.core.registry import ToolRegistry
from openjarvis.core.types import ToolResult
from openjarvis.security.ssrf import check_ssrf
from openjarvis.tools._stubs import BaseTool, ToolSpec


def _get_tavily_api_key() -> str | None:
    """Get Tavily API key from config.toml or environment variable."""
    # Try config.toml first (OpenJarvis convention)
    try:
        import tomllib
        config_path = os.path.expanduser("~/.openjarvis/config.toml")
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
        api_key = config.get("tools", {}).get("tavily", {}).get("api_key")
        if api_key:
            return api_key
    except Exception:
        pass

    # Fall back to environment variable
    return os.environ.get("TAVILY_API_KEY")


@ToolRegistry.register("web_search")
class WebSearchTool(BaseTool):
    """Search the web via Tavily API with configurable depth and topic filtering."""

    tool_id = "web_search"

    def __init__(self, api_key: str | None = None, max_results: int = 5):
        self._api_key = api_key or _get_tavily_api_key()
        self._max_results = max_results

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="web_search",
            description=(
                "Search the web for current information using Tavily. "
                "Returns structured results with full page content. "
                "Supports search depth (basic/advanced), topic filtering (general/news/finance), "
                "and time-based filtering (days parameter for recent results)."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query."},
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum results to return (1-20, default 5).",
                    },
                    "search_depth": {
                        "type": "string",
                        "description": "Search depth: 'basic' (fast) or 'advanced' (thorough). Default: basic.",
                        "enum": ["basic", "advanced"],
                    },
                    "topic": {
                        "type": "string",
                        "description": "Topic filter: 'general', 'news', or 'finance'. Default: general.",
                        "enum": ["general", "news", "finance"],
                    },
                    "days": {
                        "type": "integer",
                        "description": "Limit results to past N days (useful for news). Optional.",
                    },
                },
                "required": ["query"],
            },
            category="search",
            metadata={"requires_api_key": "TAVILY_API_KEY"},
        )

    @staticmethod
    def _is_url(text: str) -> bool:
        """Check if text is a URL."""
        stripped = text.strip()
        return stripped.startswith("http://") or stripped.startswith("https://")

    @staticmethod
    def _extract_url(text: str) -> str | None:
        """Extract the first URL from text, if any."""
        import re as _re

        match = _re.search(r"https?://[^\s,;\"'<>]+", text)
        return match.group(0).rstrip(".,;)") if match else None

    @staticmethod
    def _normalize_url(url: str) -> str:
        """Convert known PDF URLs to their HTML equivalents."""
        import re as _re

        # arxiv: /pdf/ID → /abs/ID (abstract page with full metadata)
        m = _re.match(r"(https?://arxiv\.org)/pdf/(.+?)(?:\.pdf)?$", url)
        if m:
            return f"{m.group(1)}/abs/{m.group(2)}"
        return url

    @staticmethod
    def _fetch_url(url: str, max_chars: int = 6000) -> str:
        """Fetch a URL and return extracted text content."""
        import re as _re

        import httpx

        url = WebSearchTool._normalize_url(url)
        ssrf_error = check_ssrf(url)
        if ssrf_error:
            raise ValueError(ssrf_error)
        resp = httpx.get(
            url.strip(),
            follow_redirects=True,
            timeout=30.0,
            headers={"User-Agent": "Mozilla/5.0 (compatible; OpenJarvis/1.0; +https://github.com/openjarvis)"},
        )
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        if "application/pdf" in content_type:
            return (
                "[This URL points to a PDF file which"
                f" cannot be read directly. URL: {url}]"
            )
        html = resp.text
        # Strip script/style tags and their contents
        html = _re.sub(
            r"<(script|style)[^>]*>.*?</\1>", "", html,
            flags=_re.DOTALL | _re.IGNORECASE,
        )
        # Strip HTML tags
        text = _re.sub(r"<[^>]+>", " ", html)
        # Collapse whitespace
        text = _re.sub(r"\s+", " ", text).strip()
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[Content truncated]"
        return text

    def execute(self, **params: Any) -> ToolResult:
        query = params.get("query", "")
        if not query:
            return ToolResult(
                tool_name="web_search",
                content="No query provided.",
                success=False,
            )

        # If the query contains a URL, fetch it directly instead of searching
        url = self._extract_url(query) if not self._is_url(query) else query.strip()
        if url:
            try:
                content = self._fetch_url(url)
                return ToolResult(
                    tool_name="web_search",
                    content=content or "No content found at URL.",
                    success=True,
                    metadata={"url": url, "mode": "fetch"},
                )
            except Exception as exc:
                return ToolResult(
                    tool_name="web_search",
                    content=f"Failed to fetch URL: {exc}",
                    success=False,
                )

        if not self._api_key:
            return ToolResult(
                tool_name="web_search",
                content=(
                    "No API key configured. Add to ~/.openjarvis/config.toml:\n"
                    "  [tools.tavily]\n"
                    "  api_key = 'tvly-your-key-here'\n"
                    "Or set TAVILY_API_KEY environment variable."
                ),
                success=False,
            )

        # Extract parameters with defaults
        max_results = params.get("max_results", self._max_results)
        search_depth = params.get("search_depth", "basic")
        topic = params.get("topic", "general")
        days = params.get("days")

        try:
            from tavily import TavilyClient

            client = TavilyClient(api_key=self._api_key)

            # Build search kwargs
            search_kwargs = {
                "query": query,
                "max_results": max_results,
                "search_depth": search_depth,
                "topic": topic,
                "include_answer": True,  # Include AI-synthesized answer
            }
            if days is not None:
                search_kwargs["days"] = days

            response = client.search(**search_kwargs)

            # Format response with answer and results
            answer = response.get("answer", "")
            results = response.get("results", [])

            parts = []
            if answer:
                parts.append(f"**Answer:** {answer}\n")

            if results:
                parts.append("**Sources:**")
                for r in results:
                    parts.append(
                        f"\n**{r.get('title', 'Untitled')}**\n"
                        f"{r.get('url', '')}\n{r.get('content', '')}"
                    )

            formatted = "\n".join(parts) if parts else "No results found."

            return ToolResult(
                tool_name="web_search",
                content=formatted,
                success=True,
                metadata={
                    "num_results": len(results),
                    "search_depth": search_depth,
                    "topic": topic,
                    "has_answer": bool(answer),
                },
            )
        except ImportError:
            return ToolResult(
                tool_name="web_search",
                content=(
                    "tavily-python not installed."
                    " Install with: pip install tavily-python"
                ),
                success=False,
            )
        except Exception as exc:
            return ToolResult(
                tool_name="web_search",
                content=f"Search error: {exc}",
                success=False,
            )


@ToolRegistry.register("web_fetch")
class WebFetchTool(BaseTool):
    """Fetch and extract content from a specific URL using Tavily Extract API."""

    tool_id = "web_fetch"

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or _get_tavily_api_key()

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="web_fetch",
            description=(
                "Fetch and extract clean content from a specific URL using Tavily Extract. "
                "Returns full cleaned text content from the page. "
                "Use this when you have a URL and need to read the page content."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to fetch and extract content from.",
                    },
                },
                "required": ["url"],
            },
            category="search",
            metadata={"requires_api_key": "TAVILY_API_KEY"},
        )

    def execute(self, **params: Any) -> ToolResult:
        url = params.get("url", "").strip()
        if not url:
            return ToolResult(
                tool_name="web_fetch",
                content="No URL provided.",
                success=False,
            )

        if not self._api_key:
            return ToolResult(
                tool_name="web_fetch",
                content=(
                    "No API key configured. Add to ~/.openjarvis/config.toml:\n"
                    "  [tools.tavily]\n"
                    "  api_key = 'tvly-your-key-here'\n"
                    "Or set TAVILY_API_KEY environment variable."
                ),
                success=False,
            )

        # SSRF check (skip if Rust module not available)
        try:
            ssrf_error = check_ssrf(url)
            if ssrf_error:
                return ToolResult(
                    tool_name="web_fetch",
                    content=f"Security error: {ssrf_error}",
                    success=False,
                )
        except (ImportError, ModuleNotFoundError):
            # Rust module not built - skip SSRF check
            pass

        try:
            from tavily import TavilyClient

            client = TavilyClient(api_key=self._api_key)
            response = client.extract(urls=[url])

            results = response.get("results", [])
            failed = response.get("failed_results", [])

            if failed:
                return ToolResult(
                    tool_name="web_fetch",
                    content=f"Failed to extract content from URL: {url}",
                    success=False,
                    metadata={"failed_urls": failed},
                )

            if not results:
                return ToolResult(
                    tool_name="web_fetch",
                    content="No content extracted.",
                    success=False,
                )

            # Get the first (and should be only) result
            result = results[0]
            content = result.get("raw_content", "")

            if not content:
                return ToolResult(
                    tool_name="web_fetch",
                    content="No content found at URL.",
                    success=False,
                )

            return ToolResult(
                tool_name="web_fetch",
                content=content,
                success=True,
                metadata={"url": url, "content_length": len(content)},
            )

        except ImportError:
            return ToolResult(
                tool_name="web_fetch",
                content=(
                    "tavily-python not installed."
                    " Install with: pip install tavily-python"
                ),
                success=False,
            )
        except Exception as exc:
            return ToolResult(
                tool_name="web_fetch",
                content=f"Fetch error: {exc}",
                success=False,
            )


@ToolRegistry.register("news_search")
class NewsSearchTool(BaseTool):
    """Search specifically for recent news using Tavily."""

    tool_id = "news_search"

    def __init__(self, api_key: str | None = None, max_results: int = 5, days: int = 7):
        self._api_key = api_key or _get_tavily_api_key()
        self._max_results = max_results
        self._days = days

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="news_search",
            description=(
                "Search specifically for recent news using Tavily. "
                "Convenience wrapper around web_search with topic='news'. "
                "Returns news articles from the past N days with dates."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The news search query.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Number of news results to return (default 5).",
                    },
                    "days": {
                        "type": "integer",
                        "description": "How many days back to search (default 7).",
                    },
                },
                "required": ["query"],
            },
            category="search",
            metadata={"requires_api_key": "TAVILY_API_KEY"},
        )

    def execute(self, **params: Any) -> ToolResult:
        query = params.get("query", "")
        if not query:
            return ToolResult(
                tool_name="news_search",
                content="No query provided.",
                success=False,
            )

        if not self._api_key:
            return ToolResult(
                tool_name="news_search",
                content=(
                    "No API key configured. Add to ~/.openjarvis/config.toml:\n"
                    "  [tools.tavily]\n"
                    "  api_key = 'tvly-your-key-here'\n"
                    "Or set TAVILY_API_KEY environment variable."
                ),
                success=False,
            )

        max_results = params.get("max_results", self._max_results)
        days = params.get("days", self._days)

        try:
            from tavily import TavilyClient

            client = TavilyClient(api_key=self._api_key)
            response = client.search(
                query=query,
                max_results=max_results,
                search_depth="basic",
                topic="news",
                include_answer=True,
                days=days,
            )

            answer = response.get("answer", "")
            results = response.get("results", [])

            parts = []
            if answer:
                parts.append(f"**News Summary:** {answer}\n")

            if results:
                parts.append("**Recent News:**")
                for r in results:
                    published = r.get("published_date", "")
                    date_str = f" ({published})" if published else ""
                    parts.append(
                        f"\n**{r.get('title', 'Untitled')}**{date_str}\n"
                        f"{r.get('url', '')}\n{r.get('content', '')}"
                    )

            formatted = "\n".join(parts) if parts else "No news found."

            return ToolResult(
                tool_name="news_search",
                content=formatted,
                success=True,
                metadata={
                    "num_results": len(results),
                    "days": days,
                    "has_answer": bool(answer),
                },
            )

        except ImportError:
            return ToolResult(
                tool_name="news_search",
                content=(
                    "tavily-python not installed."
                    " Install with: pip install tavily-python"
                ),
                success=False,
            )
        except Exception as exc:
            return ToolResult(
                tool_name="news_search",
                content=f"News search error: {exc}",
                success=False,
            )


__all__ = ["WebSearchTool", "WebFetchTool", "NewsSearchTool"]
