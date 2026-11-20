# Auto-Healing System

StreamTV monitors logs, detects known error patterns, and can use AI to classify
issues and select **approved** heal scripts (playout lag, stalled FFmpeg). AI never
invents playout indexes or edits streaming bedrock / scheduling modules.

Quick enable (StreamTVMac): [Foundation Models recovery](guides/FOUNDATION_MODELS_RECOVERY.md).  
Offline LoRA adapters: [FOUNDATION_MODELS_ADAPTER.md](FOUNDATION_MODELS_ADAPTER.md).

## Architecture

```text
Logs / health  →  ErrorMonitor (regex)
                      │
                      ▼
                 AutoHealer  ──►  ErrorFixer (registered config fixes, dry-run by default)
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
  Foundation Models bridge    Ollama (optional)
  StreamTVMac :11435          localhost:11434
          │
          ▼
  Whitelisted scripts only (in tree):
    heal_playout_lag.py
    heal_stalled_ffmpeg.py
    (+ LoudNorm / TunarrRAM helpers)
```

**Production defaults:** `auto_healer.enabled: false`, `apply_fixes: false` (dry-run / advise only until an operator change window).

| Layer | Role |
|-------|------|
| StreamTVMac bridge | On-device `LanguageModelSession`, Instructions, transcript, Tools |
| Python `AutoHealer` | Orchestrates scan → AI classify → registered fixes / recover |
| Deterministic scripts | In-tree: `heal_playout_lag.py`, `heal_stalled_ffmpeg.py`, LoudNorm/TunarrRAM helpers |

Related operator guides: [FFmpeg stall / keepalive](guides/FFMPEG_STALL_KEEPALIVE.md), [EPG sync / playout lag](guides/EPG_SYNC_CLASSES.md).

## AI backends

| Host | Default | Options |
|------|---------|---------|
| **macOS 26+** (Apple Intelligence) | Apple Foundation Models via StreamTVMac bridge `:11435` | Optional Ollama |
| **macOS 15 and lower** | Scripts only unless user chooses Ollama | Ollama install / `install_codestral.sh` |
| FM unavailable on 26+ | Rule-based scripts | Optional Ollama |

StreamTVMac onboarding checks the macOS version and lets the user pick **Foundation Models**, **Ollama**, or **No AI**. Settings → **AI Self-Recovery** can change the choice later.

### Continuous learning (Foundation Models)

Per Apple docs ([generating content](https://developer.apple.com/documentation/foundationmodels/generating-content-and-performing-tasks-with-foundation-models),
[tool calling](https://developer.apple.com/documentation/foundationmodels/expanding-generation-with-tool-calling)):

- Trusted `Instructions` + few-shot heal journal under Application Support
- Multiturn `Transcript` (persisted/trimmed for context limits)
- Whitelisted Tools calling `heal_playout_lag.py` / `heal_stalled_ffmpeg.py` (both in tree)
- Structured decisions (no free-form bedrock patches; ErrorFixer refuses writes under frozen streaming paths)

Offline LoRA (macOS 26.x only): [FOUNDATION_MODELS_ADAPTER.md](FOUNDATION_MODELS_ADAPTER.md).

## Configuration (`config.yaml`)

```yaml
auto_healer:
  enabled: false              # Background loop from main.py when true
  enable_ai: true
  ai_backend: auto            # auto | foundation_models | ollama | none
  foundation_models_url: http://127.0.0.1:11435
  ollama_url: http://localhost:11434
  ollama_model: llama3.2:latest
  collect_training_samples: true
  check_interval: 30          # Minutes
  apply_fixes: false          # false = dry-run only
  max_fix_attempts: 3       # Cap applies per error_pattern per process lifetime
```

Defaults keep production safe: **healer off**, **apply off**. After
`max_fix_attempts` applies for the same `error_pattern`, further registry
applies for that pattern are skipped until process restart.

**Production posture (2026-09-20):** leave `enabled: false` so Phase 0
ErrorFixer / bedrock refuse / attempt caps stay off the hot path until an
operator explicitly enables dry-run (`enabled: true`, `apply_fixes: false`).
Do **not** set `apply_fixes: true` on the fleet without a change window.

## StreamTVMac UX

1. After Python/FFmpeg setup, **AI Self-Recovery** picker appears once.
2. Choosing Foundation Models starts the loopback bridge on port **11435**.
3. Settings → AI Self-Recovery shows backend, sample collection toggle, and bridge status.
4. UserDefaults keys: `streamtv.aiBackend`, `streamtv.aiBackendChoiceCompleted`, `streamtv.collectTrainingSamples`.

## Web UI and API

| Path | Purpose |
|------|---------|
| `GET /ollama` | **AI Recovery** unified web UI (FM + Ollama) |
| `GET /foundation-models` | 302 → `/ollama` |
| `GET /foundation-models/status` | Bridge JSON status |
| `POST /foundation-models/query` | Body: `{ "query": "..." }` |
| `POST /foundation-models/recover` | Body: `{ "prompt": "...", "apply_fixes": false }` (apply also gated by config) |
| `GET /api/ai/status` | Unified FM + Ollama availability |
| `POST /api/ai/query` | Body: `{ "query": "...", "backend": "auto\|foundation_models\|ollama" }` |
| `/ollama/*` install APIs | Optional Ollama install / models (retained) |

## CLI

```bash
python scripts/auto_heal.py
python scripts/auto_heal.py --apply
python scripts/auto_heal.py --ai-backend foundation_models
python scripts/auto_heal.py --ai-backend ollama
python scripts/auto_heal.py --foundation-models-url http://127.0.0.1:11435
python scripts/auto_heal.py --continuous --interval 30
python scripts/auto_heal.py --no-ai
python scripts/auto_heal.py --json
```

## Safe rollout

1. Leave `auto_healer.enabled: false` and `apply_fixes: false` (defaults).
2. Restart Python when deploying; streaming path unchanged with healer off.
3. On StreamTVMac update, complete the one-time AI picker (choose **No AI** to stay script-only).
4. Exercise dry-run: `python scripts/auto_heal.py --ai-backend foundation_models`.
5. Enable background loop only after dry-runs look correct; keep `apply_fixes: false` until you trust apply.

## Troubleshooting

| Symptom | Check |
|---------|--------|
| `503` on `/foundation-models/query` or `/api/ai/query` | StreamTVMac running with AI = Foundation Models; bridge `:11435`; `curl http://127.0.0.1:11435/v1/status` |
| FM not available | macOS 26+, Apple Intelligence on, eligible device/region |
| macOS 15 or lower | Use Ollama option or scripts only |
| Healer never runs | `auto_healer.enabled: true` and server restarted |
| Unwanted applies | Ensure `apply_fixes: false` |

## Safety

- Deterministic scripts remain the only mutators for lag/stall
- `apply_fixes: false` forces dry-run
- Streaming bedrock / scheduling modules are never AI-patched
- `ErrorFixer` refuses targets under `streamtv/streaming/**` (and related frozen
  trees); `ffmpeg_timeout` no longer rewrites `mpegts_streamer.py`
- Active-tuner channels are skipped by lag heal apply paths
