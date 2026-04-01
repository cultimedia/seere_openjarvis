"""Shared base for OpenAI-compatible ``/v1/`` engines."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator, Sequence
from typing import Any, Dict, List

import httpx

from openjarvis.core.types import Message
from openjarvis.engine._base import (
    EngineConnectionError,
    InferenceEngine,
    messages_to_dicts,
)

logger = logging.getLogger(__name__)


class _OpenAICompatibleEngine(InferenceEngine):
    """Base for engines that serve the OpenAI ``/v1/chat/completions`` API."""

    engine_id: str = ""
    _default_host: str = "http://localhost:8000"
    _api_prefix: str = "/v1"

    def __init__(self, host: str | None = None, *, timeout: float = 600.0) -> None:
        self._host = (host or self._default_host).rstrip("/")
        self._client = httpx.Client(base_url=self._host, timeout=timeout)

    # -- InferenceEngine interface ------------------------------------------

    @staticmethod
    def _fix_tool_call_arguments(msg_dicts: list) -> list:
        """Ensure tool_call arguments are dicts, not JSON strings.

        OpenAI-compatible servers (vLLM, SGLang, llama.cpp, etc.) expect
        tool_call arguments as JSON objects.  ``messages_to_dicts`` may
        serialize them as strings, which causes 400 errors on multi-turn
        tool-calling conversations.
        """
        for md in msg_dicts:
            for tc in md.get("tool_calls", []):
                fn = tc.get("function", {})
                args = fn.get("arguments")
                if isinstance(args, str):
                    try:
                        fn["arguments"] = json.loads(args)
                    except (json.JSONDecodeError, TypeError):
                        pass
        return msg_dicts

    @staticmethod
    def _merge_system_messages(msg_dicts: list) -> list:
        """Merge multiple system messages into one.

        Some OpenAI-compatible servers (like MLX) don't accept multiple
        system messages and return 404. This merges them into a single
        system message at the beginning.
        """
        system_messages = []
        other_messages = []

        for msg in msg_dicts:
            if msg.get("role") == "system":
                system_messages.append(msg.get("content", ""))
            else:
                other_messages.append(msg)

        if len(system_messages) <= 1:
            return msg_dicts

        # Merge all system messages
        merged_content = "\n\n---\n\n".join(system_messages)
        merged_msg = {"role": "system", "content": merged_content}

        return [merged_msg] + other_messages

    @staticmethod
    def _convert_tool_messages(msg_dicts: list) -> list:
        """Convert tool role messages to user messages.

        Some OpenAI-compatible servers (like MLX) don't support role="tool"
        and return 404. This converts them to user messages with the tool
        result formatted as text.
        """
        converted = []
        for msg in msg_dicts:
            if msg.get("role") == "tool":
                # Convert tool message to user message
                tool_name = msg.get("name", "unknown_tool")
                content = msg.get("content", "")
                user_msg = {
                    "role": "user",
                    "content": f"Tool Result from {tool_name}:\n{content}"
                }
                converted.append(user_msg)
            else:
                converted.append(msg)
        return converted

    @staticmethod
    def _ensure_content_in_tool_calls(msg_dicts: list) -> list:
        """Ensure assistant messages with tool_calls have non-empty content.

        Some OpenAI-compatible servers (like MLX) return 404 when an assistant
        message has tool_calls but empty/null content. This ensures content is
        always present, using a placeholder if necessary.
        """
        for msg in msg_dicts:
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                content = msg.get("content")
                if not content or (isinstance(content, str) and not content.strip()):
                    logger.info("🔧 Fixing empty content in assistant message with tool_calls")
                    msg["content"] = "Calling tools..."
        return msg_dicts

    def generate(
        self,
        messages: Sequence[Message],
        *,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        msg_dicts = self._fix_tool_call_arguments(messages_to_dicts(messages))
        msg_dicts = self._merge_system_messages(msg_dicts)
        msg_dicts = self._convert_tool_messages(msg_dicts)
        msg_dicts = self._ensure_content_in_tool_calls(msg_dicts)

        # Debug logging for MLX issues
        if len(msg_dicts) > 2:
            roles = [m.get("role") for m in msg_dicts]
            logger.info(f"🔍 Sending {len(msg_dicts)} messages to {self.engine_id}: roles={roles}")
            for i, m in enumerate(msg_dicts):
                tc = m.get("tool_calls", [])
                logger.info(f"  [{i}] role={m.get('role')}, has_tool_calls={len(tc)>0}, content_len={len(str(m.get('content', '')))}")

        payload: Dict[str, Any] = {
            "model": model,
            "messages": msg_dicts,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
            "chat_template_kwargs": {"enable_thinking": False},
            **kwargs,
        }
        try:
            url = f"{self._api_prefix}/chat/completions"
            resp = self._client.post(url, json=payload)
            if resp.status_code == 400 and "tools" in payload:
                payload.pop("tools", None)
                payload.pop("tool_choice", None)
                resp = self._client.post(url, json=payload)
            resp.raise_for_status()
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise EngineConnectionError(
                f"{self.engine_id} engine not reachable at {self._host}"
            ) from exc
        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            return {
                "content": "",
                "usage": data.get("usage", {}),
                "model": data.get("model", model),
                "finish_reason": "error",
            }
        choice = choices[0]
        usage = data.get("usage", {})
        result: Dict[str, Any] = {
            "content": choice["message"].get("content") or "",
            "usage": {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
            "model": data.get("model", model),
            "finish_reason": choice.get("finish_reason", "stop"),
        }
        # Extract tool calls if present
        raw_tool_calls = choice["message"].get("tool_calls", [])
        if raw_tool_calls:
            result["tool_calls"] = [
                {
                    "id": tc.get("id", ""),
                    "name": tc.get("function", {}).get("name", ""),
                    "arguments": tc.get("function", {}).get("arguments", "{}"),
                }
                for tc in raw_tool_calls
            ]
        return result

    async def stream(
        self,
        messages: Sequence[Message],
        *,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        msg_dicts = self._fix_tool_call_arguments(messages_to_dicts(messages))
        payload: Dict[str, Any] = {
            "model": model,
            "messages": msg_dicts,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
            **kwargs,
        }
        try:
            url = f"{self._api_prefix}/chat/completions"
            with self._client.stream("POST", url, json=payload) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line.startswith("data:"):
                        continue
                    data_str = line[len("data:"):].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        yield content
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise EngineConnectionError(
                f"{self.engine_id} engine not reachable at {self._host}"
            ) from exc

    def list_models(self) -> List[str]:
        try:
            resp = self._client.get(f"{self._api_prefix}/models")
            resp.raise_for_status()
        except (
            httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError,
        ) as exc:
            logger.warning(
                "Failed to list models from %s at %s: %s",
                self.engine_id, self._host, exc,
            )
            return []
        data = resp.json()
        return [m["id"] for m in data.get("data", [])]

    def health(self) -> bool:
        try:
            resp = self._client.get(f"{self._api_prefix}/models", timeout=2.0)
            return resp.status_code == 200
        except Exception as exc:
            logger.debug(
                "%s health check failed at %s: %s",
                self.engine_id, self._host, exc,
            )
            return False

    def close(self) -> None:
        self._client.close()


__all__ = ["_OpenAICompatibleEngine"]
