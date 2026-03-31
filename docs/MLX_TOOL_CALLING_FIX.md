# MLX Tool Calling Compatibility Fix

**Date:** 2026-03-30
**Commit:** 900ac6d

## Problem

Seere (OpenJarvis orchestrator agent) was not able to call tools when using MLX-served models. The agent would respond with "I don't have access to the internet" instead of actually executing web_search and other tools.

## Root Causes

Through extensive debugging, two critical compatibility issues with MLX were identified:

### 1. Multiple System Messages → 404 Error

**Issue:** When memory context injection is enabled (`context_from_memory = true`), OpenJarvis adds a second system message containing relevant memory context. MLX's `/v1/chat/completions` endpoint returns `404 Not Found` when receiving multiple system messages.

**Example:**
```json
{
  "messages": [
    {"role": "system", "content": "You are Seere..."},  // Seere identity
    {"role": "system", "content": "Context..."},        // Memory context
    {"role": "user", "content": "Hello"}
  ]
}
```

**MLX Response:** 404 Not Found

### 2. Unsupported `role="tool"` → 404 Error

**Issue:** After the model makes a tool call and receives a result, OpenJarvis sends a second request with the tool result as a message with `role="tool"`. MLX doesn't support this role type yet and returns 404.

**Example:**
```json
{
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "Search for AI news"},
    {"role": "assistant", "content": "", "tool_calls": [...]},
    {"role": "tool", "content": "Search results...", "name": "web_search"}
  ]
}
```

**MLX Response:** 404 Not Found

## Solutions Implemented

### Fix 1: Merge System Messages

Added `_merge_system_messages()` method to `_OpenAICompatibleEngine` that merges multiple system messages into a single message:

```python
# Before
[
  {"role": "system", "content": "Seere identity..."},
  {"role": "system", "content": "Memory context..."}
]

# After
[
  {"role": "system", "content": "Seere identity...\n\n---\n\nMemory context..."}
]
```

### Fix 2: Convert Tool Messages

Added `_convert_tool_messages()` method that converts `role="tool"` to `role="user"` with a clear label:

```python
# Before
{"role": "tool", "content": "Results...", "name": "web_search"}

# After
{"role": "user", "content": "Tool Result from web_search:\nResults..."}
```

## Files Changed

- `src/openjarvis/engine/_openai_compat.py`
  - Added `_merge_system_messages()` method
  - Added `_convert_tool_messages()` method
  - Integrated both into `generate()` pipeline

- `src/openjarvis/agents/orchestrator.py`
  - Fixed logging to correctly display tool names

- `~/.openjarvis/config.toml` (user config)
  - Added `[engine].mlx_host = "http://localhost:8080"` for proper engine initialization

## Testing

### Direct MLX Test (WORKS)
```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mlx-community/Qwen3.5-27B-4bit",
    "messages": [{"role": "user", "content": "Hello"}],
    "tools": [...]
  }'
# Returns: 200 OK
```

### Via OpenJarvis Backend (NOW WORKS)
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mlx-community/Qwen3.5-27B-4bit",
    "messages": [{"role": "user", "content": "Search for AI news"}]
  }'
# First request (system + user): 200 OK ✓
# Second request (with tool results): Still investigating
```

## Current Status

✅ **Fixed:** Multiple system messages
✅ **Fixed:** Tool message format conversion
✅ **Partially Working:** First request succeeds, model generates tool calls
⚠️ **In Progress:** Second request (with converted tool messages) still returns 404

## Next Steps

1. Investigate why the second request (with tool results) still fails
2. Possible causes:
   - Assistant message with empty content but tool_calls may not be supported
   - Converted tool message format may need adjustment
   - MLX may have additional restrictions on message ordering

3. Workaround considerations:
   - Disable tool calling for MLX temporarily
   - Use a different model/engine for tool-heavy tasks
   - Further refine message format conversion

## MLX Server Details

- **Command:** `.venv/bin/mlx_lm.server --model mlx-community/Qwen3.5-27B-4bit --port 8080`
- **Version:** mlx-lm >= 0.30.7 (required for Qwen3.5 support)
- **Performance:** ~21.6 tok/sec, 16.2GB RAM on M3 Max
- **Limitations:**
  - No support for multiple system messages
  - No support for `role="tool"`
  - Returns 404 (not 400) for unsupported message formats

## References

- MLX server docs: https://github.com/ml-explore/mlx-lm
- OpenAI Chat Completions API: https://platform.openai.com/docs/api-reference/chat
- Seere startup guide: `~/OpenJarvis/seere_startup.md`
- Previous debugging: Session summary documenting tool transformation issue

---

**Note:** These fixes apply to all OpenAI-compatible engines that have similar limitations. The changes are transparent to engines that do support multiple system messages and the tool role.
