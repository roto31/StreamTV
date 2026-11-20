# Foundation Models recovery (StreamTVMac)

Enable on-device Apple Foundation Models for StreamTV self-recovery **without** changing playout math. Full reference: [AUTO_HEALER.md](../AUTO_HEALER.md). Offline adapters: [FOUNDATION_MODELS_ADAPTER.md](../FOUNDATION_MODELS_ADAPTER.md).

## Requirements

- macOS **26+** with Apple Intelligence available
- StreamTVMac build that includes the recovery services (bridge on `127.0.0.1:11435`)
- Python StreamTV server on `:8410` (usual path)

On macOS **15 and lower**, pick **Ollama** or **No AI** at onboarding. Heal scripts still work without AI.

## Enable (recommended dry-run path)

1. Launch StreamTVMac and finish Python/FFmpeg setup if prompted.
2. On **AI Self-Recovery**, select **Apple Foundation Models** (or **No AI** / **Ollama**).
3. Confirm Settings → **AI Self-Recovery** shows the bridge running (port 11435).
4. Leave `config.yaml` with:

```yaml
auto_healer:
  enabled: false
  apply_fixes: false
  ai_backend: auto
```

5. Optional dry-run from the repo:

```bash
./venv/bin/python scripts/auto_heal.py --ai-backend foundation_models
```

6. Web check: open `http://localhost:8410/ollama` (AI Recovery) or `GET /api/ai/status`. (`/foundation-models` redirects here.)

## What the model may do

- Classify log/error symptoms
- Call **only** `heal_playout_lag.py` and `heal_stalled_ffmpeg.py` (both in tree; whitelist only)
- Store local journal / training JSONL under `~/Library/Application Support/StreamTV/recovery/`

It must **not** invent guide indexes, FFmpeg flags, or edit `streamtv/streaming/**` / `streamtv/scheduling/**`.

## Turn off

- Settings → AI Self-Recovery → **No AI (scripts only)**, or
- `auto_healer.enable_ai: false` / `ai_backend: none`

Background healing only runs when `auto_healer.enabled: true`.

## Related

- [FFmpeg stall / keepalive](FFMPEG_STALL_KEEPALIVE.md)
- [EPG sync / playout lag](EPG_SYNC_CLASSES.md)
- [Backup and restore](BACKUP_RESTORE.md)
