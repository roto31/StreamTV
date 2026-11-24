# SetupDone and factory reset

AppleSetupDone-style marker: `~/Library/Application Support/StreamTV/.StreamTVSetupDone`  
Repo/LaunchAgent also may write `.streamtv-setup-done` next to cwd.

```mermaid
flowchart TD
  Absent["Marker absent"] --> Onboard["First-run onboarding"]
  Onboard --> Gate{"Plex present and AAC missing?"}
  Gate -->|yes| Block["409 plex_codecs_missing<br/>Retry install"]
  Block --> Gate
  Gate -->|no| Write["Write SetupDone"]
  Write --> Present["Marker present"]
  Present --> Main["Main shell / dashboard"]
  Factory["Run Setup Again"] --> Clear["Delete marker"]
  Clear --> Absent
```

JSON contents: `completed_at`, `app_version`, `setup_schema_version`.

**Run Setup Again** (Settings): confirms, clears marker (optional config reseed), returns to first-run. Does not delete channel YAML by default.

Plex AAC gate details: [First-run setup](FIRST_RUN_SETUP.md) · [Plex Playback Error host](PLEX_PLAYBACK_ERROR_HOST.md).
