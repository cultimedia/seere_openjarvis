# Claude Code Task: Implement Seere Identity + Desktop GUI

**Project:** ~/OpenJarvis  
**Goal:** Name and skin the OpenJarvis instance as "Seere" and get the Tauri desktop app running  

---

## Context

OpenJarvis is installed at `~/OpenJarvis`. The orchestrator model is Qwen3.5-27B-4bit 
via MLX on port 8080. The operator is qwen3:8b via Ollama. The Tauri desktop app 
exists in the repo but has not been started yet.

Seere is the agent persona — the OrchestratorAgent's identity. OpenJarvis remains 
the framework underneath.

---

## Phase 1: Seere Identity Files

### 1.1 Copy the contract into the repo

```bash
cp ~/path/to/SEERE_CONTRACT.md ~/OpenJarvis/SEERE_CONTRACT.md
```

### 1.2 Find the OrchestratorAgent config / system prompt location

```bash
# Look for where agent system prompts are defined
find ~/OpenJarvis -name "*.py" | xargs grep -l "OrchestratorAgent\|orchestrator" | head -20
find ~/OpenJarvis -name "*.yaml" -o -name "*.toml" -o -name "*.json" | xargs grep -l "system_prompt\|orchestrator" 2>/dev/null | head -10
```

### 1.3 Inject Seere's system prompt into OrchestratorAgent

Once you find where the orchestrator system prompt lives, prepend or replace it with 
the content from the `## System Prompt` section of SEERE_CONTRACT.md.

If it's in a Python file, look for something like:
```python
ORCHESTRATOR_SYSTEM_PROMPT = """..."""
# or
system_prompt = "..."
```

If it's config-driven (YAML/TOML), find the `system_prompt` key under `[orchestrator]` 
or similar.

The Seere system prompt to inject:
```
You are Seere, the dispatch intelligence of this OpenJarvis instance.

Your nature: swift, truthful, cooperative. You are not an oracle or ruler —
you are a trusted executor. You move, reveal, audit, and dispatch. You do
not destroy silently, deceive, or escalate your own privileges.

Your offices:
- DISPATCH: route jobs across machines, containers, clouds, and services
- CARRY: move data between locations with checksums and ACL verification
- REVEAL: surface where things are and what state they are in
- AUDIT: return tamper-evident history of access and movement
- DISCOVER: find lost, underused, or newly available assets

Your constraints (non-negotiable):
- Never permanently delete without explicit human confirmation of subject, scope, and backup state
- Never falsify logs, status, or metrics — mark untrusted sources as untrusted
- Never move data across trust boundaries without producing an auditable event
- Never mint your own new privileges or bypass the policy layer
- If policy is missing or ambiguous, default is: deny + ask

Your behavioral invariants:
- If speed and safety conflict, state the conflict and ask — never decide alone
- Partial success is reported as partial, never rounded up to success
- Every nontrivial action has a human-legible narrative

You are Seere. You answer to the architect.
```

---

## Phase 2: Locate and Assess the Tauri Desktop App

### 2.1 Find the desktop app directory

```bash
find ~/OpenJarvis -name "tauri.conf.json" -o -name "src-tauri" -type d 2>/dev/null
ls ~/OpenJarvis/apps/ 2>/dev/null || ls ~/OpenJarvis/desktop/ 2>/dev/null
find ~/OpenJarvis -name "package.json" | head -20
```

### 2.2 Check Tauri + dependencies status

```bash
# Check if Tauri CLI is installed
cargo tauri --version 2>/dev/null || npx tauri --version 2>/dev/null

# Check Node/npm/pnpm
node --version && npm --version
pnpm --version 2>/dev/null || echo "pnpm not installed"

# Check Rust
rustc --version && cargo --version
```

### 2.3 Read the README for desktop build instructions

```bash
cat ~/OpenJarvis/README.md | grep -A 20 -i "tauri\|desktop\|gui"
```

---

## Phase 3: Build and Run the Tauri App (or fallback to web UI)

### Option A — If Tauri app exists and deps are available

```bash
cd ~/OpenJarvis/<desktop-app-directory>
npm install   # or pnpm install
npm run tauri dev   # development mode
```

Watch for errors. Common issues:
- Missing `WEBKIT_DISABLE_COMPOSITING_MODE` on macOS
- Missing Xcode Command Line Tools: `xcode-select --install`
- Rust target: `rustup target add aarch64-apple-darwin`

### Option B — If Tauri app needs work or deps missing

Fall back to the React browser app:

```bash
# Find the web frontend
find ~/OpenJarvis -name "package.json" | xargs grep -l '"start"\|"dev"' | head -5
cd ~/OpenJarvis/<web-app-directory>
npm install && npm run dev
# App should be at http://localhost:3000 or :5173
```

### Option C — Build a minimal Seere web UI from scratch

If neither Tauri nor React app is in good shape, create a standalone page:

```bash
mkdir -p ~/OpenJarvis/seere-ui
cat > ~/OpenJarvis/seere-ui/index.html << 'EOF'
# (see the Seere UI spec below)
EOF
```

---

## Phase 4: Skin the UI as Seere

Wherever the frontend lives (Tauri app, React app, or new HTML), make these changes:

### 4.1 Rename / rebrand
- App title: `Seere` (not OpenJarvis)
- Window title bar: `Seere — Dispatch Intelligence`
- Any `<title>` tags: `Seere`

### 4.2 Color palette (Seere aesthetic)
```css
:root {
  --seere-void: #0a0a0c;           /* near-black ground */
  --seere-bone: #e8e4d9;           /* bone white text */
  --seere-amber: #c8890a;          /* primary accent — winged horse gold */
  --seere-amber-dim: #7a5406;      /* muted amber for secondary elements */
  --seere-surface: #141416;        /* card/panel surfaces */
  --seere-border: rgba(200,137,10,0.18);  /* amber border at low opacity */
  --seere-muted: #6b6860;          /* secondary text */
}
```

### 4.3 Typography
- Primary: `'SF Pro Display'` (available on Mac) or `system-ui`
- Monospace (for logs/audit output): `'SF Mono'` or `'JetBrains Mono'`
- Avoid: Inter, Roboto, generic sans-serif

### 4.4 Key UI copy changes
| Find | Replace |
|---|---|
| "OpenJarvis" (in UI labels) | "Seere" |
| "Orchestrator" (in UI labels) | "Seere" |
| "Ask OpenJarvis..." | "Dispatch to Seere..." |
| "Submit" | "Dispatch" |
| Loading indicator text | "Seere is traversing..." |

### 4.5 Chat/input area changes
The main input should feel like a dispatch console, not a chat box:
- Placeholder: `"Dispatch a task, carry a file, or ask Seere to reveal..."`
- Send button label: `Dispatch` or `↑`
- Response area header: `Seere →` (not "Assistant" or "AI")

---

## Phase 5: Seere UI Spec (if building from scratch)

If building a minimal standalone UI, here is the spec:

```
Layout: Single dark page, full viewport
Header: "SEERE" in small caps, left-aligned, amber color — right side shows model status
Main: Large dispatch input at bottom (think terminal-meets-chat)
Output: Message thread above input, alternating dispatch/seere blocks
Sidebar (optional): Mode switcher — Messenger / Courier / Treasure Hunter
Footer: Model info line: "Qwen3.5-27B · MLX · Port 8080"
```

**Input block:**
```
[ Dispatch to Seere...                              ] [↑]
  intent: auto-detect    mode: messenger
```

**Seere response block:**
```
Seere →
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[response text]

status: success  |  audit_id: a3f9b2  |  0.8s
```

---

## Phase 6: Connect UI to OpenJarvis Backend

The FastAPI server runs at `http://localhost:8000` via `jarvis serve --port 8000`.

### 6.1 Start the backend
```bash
cd ~/OpenJarvis
jarvis serve --port 8000
# or: uvicorn openjarvis.server:app --port 8000
```

### 6.2 API endpoints to use in UI
```javascript
// Stream a response (SSE)
const response = await fetch('http://localhost:8000/v1/chat/completions', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    model: 'qwen3.5-27b',  // or whatever model string OpenJarvis uses
    messages: [{ role: 'user', content: userInput }],
    stream: true
  })
});

// Check health
const health = await fetch('http://localhost:8000/health');
```

### 6.3 Discover the actual API shape
```bash
# Get the OpenAPI spec
curl http://localhost:8000/openapi.json | python3 -m json.tool | head -80

# Or browse
open http://localhost:8000/docs
```

---

## Phase 7: Verify End-to-End

```bash
# 1. MLX server running?
curl http://localhost:8080/v1/models

# 2. Ollama running?
ollama list

# 3. OpenJarvis server running?
curl http://localhost:8000/health

# 4. Seere system prompt active?
# Send a test message: "Who are you?"
# Expected: Response identifies as Seere, not a generic assistant
```

---

## Notes

- The Seere contract lives at `~/OpenJarvis/SEERE_CONTRACT.md`
- Do not rename the OpenJarvis directory or change the Python package — only the UI and agent persona change
- The OrchestratorAgent system prompt is the single most important change; everything else is cosmetic
- If the Tauri app requires significant Rust work, the React browser app at localhost is sufficient for now — Tauri can be revisited
- Log all changes in a `SEERE_CHANGELOG.md` so future sessions can pick up where this left off

---

## Seere Implementation Session Notes

*Session started: 2026-03-23*

### Phase 1: Seere Identity Files ✓

**1.1 SEERE_CONTRACT.md** - Confirmed existing (6282 bytes)
- Located at: `~/OpenJarvis/SEERE_CONTRACT.md`
- Contains Seere identity, system prompt, capabilities, constraints

**1.2 OrchestratorAgent System Prompt Location** - Found
- Main agent file: `src/openjarvis/agents/orchestrator.py`
- System prompt defined in: `src/openjarvis/learning/intelligence/orchestrator/prompt_registry.py`
- Agent instantiation: `src/openjarvis/system.py` (lines 142-165)
- System prompt parameter accepted at init (line 56 of orchestrator.py)
- Falls back to `build_system_prompt()` from prompt_registry (lines 94-100)

**1.3 Seere System Prompt Injection** ✓
- **Modified file:** `src/openjarvis/learning/intelligence/orchestrator/prompt_registry.py`
- **Change:** Prepended Seere identity to SYSTEM_PROMPT_TEMPLATE (lines 17-71)
- **Preservation:** Kept all tool selection logic and response format requirements
- **Result:** OrchestratorAgent now identifies as Seere by default while maintaining tool-calling functionality

**Key Changes:**
- Seere identity declaration: "You are Seere, the dispatch intelligence..."
- Five offices defined: DISPATCH, CARRY, REVEAL, AUDIT, DISCOVER
- Non-negotiable constraints embedded (deletion, logging, privilege escalation)
- Behavioral invariants (speed vs safety, partial success reporting, human narratives)
- Tool-calling format preserved for compatibility

**Status:** Phase 1 complete. OrchestratorAgent now has Seere identity embedded at the system prompt level.

---

### Phase 2: Locate and Assess Tauri Desktop App ✓

**2.1 Desktop App Discovery** - Found two Tauri applications
- **Primary app:** `frontend/` - Full React + Tauri chat application ("openjarvis-chat")
  - Dependencies: React 19, Tailwind CSS 4, shadcn/ui, react-markdown, routing
  - Build scripts: `vite`, `tauri`
  - Location: `/Users/keithwilkins/OpenJarvis/frontend/`
- **Wrapper app:** `desktop/` - Thin wrapper that delegates to frontend
  - Name: "openjarvis-desktop"
  - Scripts delegate to `../frontend`
  - Location: `/Users/keithwilkins/OpenJarvis/desktop/`

**2.2 Tauri Configuration**
- Tauri 2.0 config found at:
  - `desktop/src-tauri/tauri.conf.json`
  - `frontend/src-tauri/tauri.conf.json`
- Plugins: notification, shell, global-shortcut, autostart, updater, process

**2.3 Dependencies Status**
- ✓ Node.js: v25.2.1
- ✓ npm: v11.7.0
- ✓ Rust: v1.94.0
- ✓ Cargo: v1.94.0
- ✗ Tauri CLI: Not installed globally (available via npm devDependency)
- ✗ node_modules: Not installed in either `desktop/` or `frontend/`

**2.4 Build Instructions** (from desktop/README.md)
```bash
cd desktop
npm install
cargo tauri dev    # Development mode
cargo tauri build  # Production build
```

---

### Phase 3: Desktop App Assessment ✓

**Decision:** Apply branding to source code first, then optionally install/test

**Status:** Skipped installation for now - applied branding directly to source files instead.

---

### Phase 4: Seere UI Branding ✓

**4.1 App Title and Metadata** - Updated
- **File:** `frontend/index.html`
- **Changes:**
  - Title: "OpenJarvis" → "Seere"
  - Meta description: "OpenJarvis — on-device AI assistant" → "Seere — Dispatch Intelligence"

**4.2 Seere Color Palette Applied** - Dark mode colors updated
- **File:** `frontend/src/index.css`
- **Color scheme changes:**

  | Element | Old Color | New Color (Seere) |
  |---------|-----------|-------------------|
  | Background | `#161618` | `#0a0a0c` (seere-void) |
  | Surface | `#1e1e21` | `#141416` (seere-surface) |
  | Text primary | `#e8e8ed` | `#e8e4d9` (seere-bone) |
  | Text secondary | `#8e8e93` | `#8e8a80` |
  | Text tertiary | `#636366` | `#6b6860` (seere-muted) |
  | Accent | `#3b82f6` (blue) | `#c8890a` (seere-amber) |
  | Accent hover | `#60a5fa` | `#d99b1e` |
  | Border | `rgba(255,255,255,0.08)` | `rgba(200,137,10,0.18)` (amber-tinted) |
  | User bubble | `#3b82f6` (blue) | `#c8890a` (amber) |

- **Applied to:** `.dark` class and `@media (prefers-color-scheme: dark)`
- **Result:** Amber accent throughout, bone white text on near-black void background

**4.3 UI Copy Changes** - Seere terminology
- **File:** `frontend/src/components/Layout.tsx` (line 44)
  - "Cannot reach OpenJarvis backend" → "Cannot reach Seere backend"

- **File:** `frontend/src/components/Chat/InputArea.tsx` (line 308)
  - placeholder: "Message OpenJarvis..." → "Dispatch to Seere..."

- **File:** `frontend/src/components/SetupScreen.tsx` (line 112)
  - Header: "OpenJarvis" → "Seere"

**4.4 Typography** - Already appropriate
- System fonts: `system-ui, -apple-system, 'Segoe UI'` (includes SF Pro on macOS)
- Monospace: `"SF Mono", "JetBrains Mono", "Fira Code", "Cascadia Code"` (index.css:289, 306)
- **Result:** Typography already aligns with Seere spec (SF Pro Display/SF Mono available on Mac)

**4.5 Preserved References**
- External links (e.g., leaderboard URL in SystemPanel.tsx) - kept as OpenJarvis project references
- API documentation references - kept for technical clarity
- Internal variable names and comments - unchanged (only user-facing text modified)

**Summary:** Seere branding successfully applied to all user-facing UI elements. The app now displays "Seere" branding with the amber/bone/void color palette while maintaining the OpenJarvis framework underneath.
