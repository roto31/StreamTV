# In-app Updates

Settings → **Updates** (`/settings/updates`).

```mermaid
flowchart TD
  Check["GET /api/updates/status"] --> Agree["Agree checkbox"]
  Agree --> Backup["Pre-update backup"]
  Backup --> Apply["apply_public_update.sh"]
  Apply --> Restart["launchctl kickstart"]
  Restart --> Banner["Server back up banner"]
  Apply -->|fail| Rollback["Restore from update-backups"]
```

- **install_mode:** `app` (Application Support) vs `repo` (LaunchAgent)
- **Download DMG:** `/api/updates/dmg` → latest GitHub release `.dmg`
