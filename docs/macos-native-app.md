# macOS native app

StreamTV ships a **native macOS SwiftUI application** (`StreamTVMac/`) that bundles the Python server and provides:

- First-launch onboarding (Python 3.10+ check, venv consent)
- Server lifecycle (start/stop, logs, config in Application Support)
- Native channel list and HLS player
- TV guide (EPG from XMLTV)
- Channel creation from URL
- Settings and About

## Architecture

| Component | Path |
|-----------|------|
| App target | `StreamTVMac/` |
| Shared client library | `StreamTVKit/` (SPM) |
| Python server (bundled) | `streamtv/` synced into app Resources |
| User venv | `~/Library/Application Support/StreamTV/venv` |
| Config & database | `~/Library/Application Support/StreamTV/config.yaml`, `streamtv.db` |

## First launch

1. Install **Python 3.10+** ([python.org](https://www.python.org/downloads/macos/) or Homebrew).
2. Open **StreamTV.app** and accept venv creation in Application Support.
3. Wait for `pip install` to complete (first run only).
4. Server starts on `http://localhost:8410`.

**FFmpeg** is recommended: `brew install ffmpeg`

## Local development

```bash
cd StreamTVMac
./sync-python-code.sh
open StreamTVMac.xcodeproj
```

Or release build (unsigned):

```bash
bash scripts/release_build_macos_app.sh --no-notarize --no-dmg
```

## Web UI

The FastAPI web UI remains at `http://localhost:8410` during the native UI transition.
