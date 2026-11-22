# Channel Creator MCP — host wiring

Connect StreamTV Channel Creator MCP to editors, local models, and remote
ChatGPT / Claude web.

**Also on this wiki:** [Platform overview](Channel-Creator-MCP) · [HTTP auth](Channel-Creator-MCP-Auth)

```mermaid
flowchart TD
  Start["Want NL channel create"] --> Where{"Where do you work?"}
  Where -->|IDE| LocalIDE["Cursor / VS Code / Continue / Cline"]
  Where -->|Desktop chat| Claude["Claude Desktop / Claude Code"]
  Where -->|Local GPU| LocalLLM["LM Studio / Goose / Ollama client"]
  Where -->|Browser loopback| OpenWebUI["Open WebUI"]
  Where -->|Phone / ChatGPT / Claude web| Remote["Cloudflare tunnel"]
  LocalIDE --> Stdio["stdio MCP · profile guided"]
  Claude --> Stdio
  LocalLLM --> Stdio
  OpenWebUI --> LoopHTTP["HTTP :8411 auth=none · loopback only"]
  Remote --> PubHTTP["HTTP :8411 · bearer / oauth / dual"]
  Stdio --> API["StreamTV :8410 loopback"]
  LoopHTTP --> API
  PubHTTP --> API
```

**GitHub one-liner** (clone public repo + interactive wire):

```bash
curl -fsSL https://raw.githubusercontent.com/roto31/StreamTV/main/scripts/install_channel_creator_mcp.sh | bash
```

**Interactive (existing checkout):**

```bash
bash scripts/setup_channel_creator_mcp.sh
```

**Generator:**

```bash
zsh scripts/channel_creator_mcp_hosts.zsh --host all --mode emit --profile guided
# Apply Cursor project config (backs up first):
zsh scripts/channel_creator_mcp_hosts.zsh --host cursor --mode apply --profile guided
```

```mermaid
flowchart TD
  OneLiner["curl install_channel_creator_mcp.sh"] --> Setup["setup_channel_creator_mcp.sh"]
  Setup --> Gen["channel_creator_mcp_hosts.zsh"]
  Gen --> Mode{"mode"}
  Mode -->|emit| Out["scripts/channel-creator-mcp/generated/*.json"]
  Mode -->|apply| Bak["Backup .bak.stamp"]
  Bak --> Merge["Merge live host config"]
  Mode -->|dry-run| Print["Print actions only"]
  Out --> Smoke["mcp_smoke.py stdio"]
  Merge --> Smoke
```

---

## 1. Shared prerequisites

| Requirement | Detail |
|-------------|--------|
| StreamTV API | `http://127.0.0.1:8410` — production LaunchAgent (repo cwd) |
| MCP package | `pip install -r requirements-mcp-streamtv.txt` |
| Default profile | `guided` (11 tools) |
| Default transport | **stdio** (local hosts) |
| Remote transport | Streamable HTTP `:8411` + `bearer` / `oauth` / `dual` |

```bash
export STREAMTV_BASE_URL=http://127.0.0.1:8410
export STREAMTV_MCP_PROFILE=guided
./venv/bin/python -m mcp_streamtv.main --profile guided --transport stdio
```

Smoke:

```bash
./venv/bin/python scripts/mcp_smoke.py --transport stdio --profile guided
```

Verify: tool count = 11 for `guided`; `channel_guide` returns intake text.

```mermaid
flowchart LR
  Host["AI host"] -->|"stdio or HTTP /mcp"| MCP["mcp_streamtv"]
  MCP -->|"STREAMTV_BASE_URL"| API[":8410 Builder API"]
  API --> Draft["draft → plan → newchannel-build"]
  Draft --> YAML["data/ + schedules/"]
  YAML --> Soft["soft playout-reset / stream-restart"]
```

---

## 2. Cursor

```bash
zsh scripts/channel_creator_mcp_hosts.zsh --host cursor --mode apply --profile guided
```

Writes `.cursor/mcp.json` (backup `.bak.<stamp>`). Enable the
`streamtv-channel-creator` skill. First message: ask for a Christmas / holiday
channel in plain language.

**Verify:** guided tools visible; `channel_guide` works.

```mermaid
sequenceDiagram
  participant U as Operator
  participant C as Cursor
  participant M as mcp_streamtv stdio
  participant S as StreamTV :8410
  U->>C: Create a Christmas channel
  C->>M: channel_guide / channel_start
  M->>S: /api/builder/...
  S-->>M: draft + candidates
  M-->>C: shortlist / plan_token
  U->>C: build
  C->>M: channel_build confirm=build
```

---

## 3. VS Code (Copilot agent / Continue / Cline)

```bash
zsh scripts/channel_creator_mcp_hosts.zsh --host vscode --mode emit --profile guided
zsh scripts/channel_creator_mcp_hosts.zsh --host continue --mode emit --profile guided
zsh scripts/channel_creator_mcp_hosts.zsh --host cline --mode emit --profile guided
```

VS Code uses `"servers"` + `"type": "stdio"`. Paste generated JSON into the host’s
MCP settings. Add intake as a system rule: resource `streamtv://prompts/channel-intake`.

**Verify:** `/streamtv.channel_intake` (or pasted intake) + tools work.

```mermaid
flowchart LR
  subgraph VSCode
    Copilot["Copilot agent"]
    Cont["Continue"]
    Cline["Cline"]
  end
  Copilot --> Stdio["mcp_streamtv stdio"]
  Cont --> Stdio
  Cline --> Stdio
  Stdio --> API[":8410"]
```

---

## 4. Claude Desktop

```bash
zsh scripts/channel_creator_mcp_hosts.zsh --host claude-desktop --mode emit --profile guided
```

Merge into `claude_desktop_config.json` `mcpServers`. Use prompt `channel_intake`.

**Verify:** prompt + tools work.

---

## 5. Claude Code

```bash
zsh scripts/channel_creator_mcp_hosts.zsh --host claude-code --mode emit --profile guided
```

Or: `claude mcp add streamtv-channel-creator -- ./venv/bin/python -m mcp_streamtv.main --profile guided`

**Verify:** `claude mcp list` shows the server; `channel_guide` runs.

---

## 6. LM Studio / Goose / local models

```bash
zsh scripts/channel_creator_mcp_hosts.zsh --host lmstudio --mode emit --profile guided
zsh scripts/channel_creator_mcp_hosts.zsh --host goose --mode emit --profile guided
```

Use **compact** intake (`channel_intake_compact` / resource) for small context.
Recommended local models: Qwen3 32B · Llama 3.3 70B · Qwen3 8B (tight RAM).

**Verify:** flow up to plan preview (`channel_plan`).

```mermaid
flowchart TD
  Model{"Local model"} -->|Qwen3 32B| Good["Full guided flow"]
  Model -->|Llama 3.3 70B| Good
  Model -->|Qwen3 8B| Compact["channel_intake_compact"]
  Compact --> Plan["Stop at channel_plan if context tight"]
  Good --> Build["channel_build after confirm"]
```

---

## 7. Open WebUI (loopback HTTP)

```bash
./venv/bin/python -m mcp_streamtv.main --transport http --host 127.0.0.1 --port 8411 \
  --auth none --profile guided
```

```bash
zsh scripts/channel_creator_mcp_hosts.zsh --host open-webui --mode emit --profile guided
```

**Verify:** `channel_guide` and `channel_list` over `http://127.0.0.1:8411/mcp`.

```mermaid
flowchart LR
  UI["Open WebUI"] -->|"HTTP /mcp auth=none"| MCP["127.0.0.1:8411"]
  MCP --> API["127.0.0.1:8410"]
```

---

## 8. ChatGPT Developer mode + Claude web (remote)

Never expose `:8410`. Tunnel only MCP `:8411`.

```bash
export STREAMTV_MCP_AUTH=dual
export STREAMTV_MCP_TOKEN="$(openssl rand -hex 32)"
export STREAMTV_MCP_ACCESS_TEAM=myteam
export STREAMTV_MCP_ACCESS_AUDIENCE="<AUD>"

./venv/bin/python -m mcp_streamtv.main --transport http --host 127.0.0.1 --port 8411 \
  --auth dual --profile guided

zsh scripts/channel_creator_mcp_remote.zsh
# optional: --public-url https://YOUR_HOST/mcp
```

| App | Values |
|-----|--------|
| ChatGPT | MCP URL `https://YOUR_HOST/mcp`; Bearer token (dual Lock 2) or OAuth Sign-in |
| Claude web | Settings → Connectors → custom connector → same URL + auth |

**Verify:** `channel_guide`, `channel_list`, plan preview; build only if profile is `guided` and plan allows write.

Auth details: [HTTP auth](Channel-Creator-MCP-Auth).

```mermaid
flowchart TD
  App["ChatGPT / Claude web"] -->|"HTTPS /mcp"| CF["Cloudflare Tunnel"]
  CF --> Access{"Access policy Lock 1"}
  Access -->|email / IdP OK| Edge["Cf-Access-Jwt-Assertion"]
  Edge --> MCP["Mac :8411 dual"]
  App -->|"Authorization Bearer MCP token Lock 2"| MCP
  MCP --> API[":8410 never tunneled"]
```

```mermaid
flowchart LR
  subgraph AuthModes
    B["bearer — shared secret"]
    O["oauth — Sign in with Auth0/Access"]
    D["dual — Access + secret"]
  end
  B --> Mac["JWKS / token check on Mac"]
  O --> Mac
  D --> Mac
```

---

## 9. Profiles quick reference

| Profile | Tools | Notes |
|---------|-------|-------|
| `guided` | 11 `channel_*` | Default; includes `channel_build` |
| `planner` | guided minus build | Read / plan only |
| `builder` | guided + detail | Power users |
| `full` | + legacy names | May hit Cursor ~40 tool cap |

```mermaid
flowchart LR
  guided["guided 11"] --> planner["planner − build"]
  guided --> builder["builder + detail"]
  builder --> full["full + legacy"]
```

---

## 10. E2E rehearsal (throwaway)

```bash
zsh scripts/channel_creator_e2e_rehearsal.zsh
```

Uses isolated `STREAMTV_REPO_ROOT`; does not write production `data/`.

```mermaid
flowchart TD
  E2E["e2e_rehearsal.zsh"] --> Tmp["Temp STREAMTV_REPO_ROOT"]
  Tmp --> Install["Install demo fixture only"]
  Install --> Build["Build throwaway channel from fixture inputs"]
  Build --> Gates["Number free + isolation gates"]
  Gates --> Isol["Assert production data/ untouched"]
```
