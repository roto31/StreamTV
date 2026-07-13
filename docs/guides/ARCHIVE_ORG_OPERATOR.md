# Archive.org operator guide

## Authentication

- Preferred: Netscape `cookies.txt` via `/api/auth/archive-org` or Settings → Auth.
- Alternative: username/password in `config.yaml` under `archive_org:` (less reliable for streaming).

## Download paths

- **HTTP downloader** — default for cache-first playback.
- **CLI downloader** — legacy path when `archive_org` tools are installed.

Both may appear in logs; tune behavior is identical once a local cache file exists.

## Troubleshooting

1. Re-export cookies after login at archive.org.
2. Confirm `archive_org.cookies_file` path exists on the server.
3. Use MP4 items for playout (non-MP4 items are skipped per bedrock policy).
