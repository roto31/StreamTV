# Python 3.14 / 3.15 Migration Guide

StreamTV's floor stays **Python 3.10+**. This guide covers moving a host to
**3.14** or **3.15**: the dependency changes, the gate evidence (2026-11-26),
and the cutover steps.

## Support matrix

| Python | Status | Evidence |
|--------|--------|----------|
| 3.10–3.11 | Supported floor (not re-gated in this pass) | `setup.py`, `requirements.txt` header |
| 3.12 | CI gate (`ci.yml` `test` job) | Full suite passes |
| 3.13 | Studio production today | Full suite passes |
| 3.14 | Candidate (`ci.yml` `python-compat`) | Full suite passes; runtime soak clean |
| 3.15 | Candidate (`ci.yml` `python-compat`) | Full suite passes; 3.15.2 runtime soak clean |

"Supported" means the version is in the CI matrix and has been soaked on a host.
Homebrew or python.org having a version installed doesn't make it supported.

## Dependency changes required for 3.15

Three pins had no `cp315` wheels. Each bump also installs from wheels on 3.12–3.14:

| Package | Old | New | Reason |
|---------|-----|-----|--------|
| `pydantic` | 2.12.5 | 2.14.4 | 2.12.x hard-pins `pydantic-core` 2.41.5 (no cp315); 2.14.4 → core 2.50.5 (cp310–cp315) |
| `lxml` | 6.1.1 | 6.1.3 | first patch with cp315 wheels (keeps CVE-2026-41066 fix) |
| `pyyaml` | 6.0.3 | 6.0.4 | first patch with cp315 wheels |

`pytz` was removed. Nothing imports it, and the EPG uses stdlib `zoneinfo`.

Gate command: `pip install --only-binary=:all: -r requirements.txt -r requirements-mcp-streamtv.txt`.

## Gate results (development host, 2026-11-26)

- Import `streamtv.main`, `scripts/check_core_dependency_freshness.py`: PASS on 3.14.6 and 3.15.2.
- `pip-audit`: same findings on every version, so none is interpreter-specific. They come from existing pins:
  `certifi` 2025.11.12, `urllib3` 2.7.0, `python-jose` 3.5.0, `ecdsa` 0.19.2.
- Isolated runtime soak (own port, DB copy, cache and HOME; SSDP off):
  `/health` 200, `/lineup.json`, HDHomeRun `/auto/v101` H.264 + AAC MPEG-TS,
  11-minute continuous tune, 180 s cold A/B 3.14 vs 3.15 with 0 decode errors and 0 log ERRORs.
- YouTube resolve (Issue 73 clients): OK on 3.14 and 3.15, ~43 s each, the same on both versions.
- XMLTV generation (2.95 MB guide, median of 5): 3.13 9.1 s, 3.14 5.7 s, 3.15 5.3 s.

## Cutover steps (Studio only when the owner asks)

1. Install the interpreter (python.org framework build, matching how the current venv was created).
2. Create a **new** venv beside the old one. Never upgrade in place:
   `python3.15 -m venv venv-py315 && venv-py315/bin/pip install --only-binary=:all: -r requirements.txt`.
3. Run `venv-py315/bin/python -m pytest -q tests/` from a scratch copy of the repo,
   because tests call `init_db()` on `./streamtv.db`.
4. Swap `venv` → new venv (keep the old one as `venv.backup`), then
   `launchctl kickstart -k gui/$(id -u)/com.streamtv`.
   **Soft deploy does not change the interpreter.**
5. Re-run operator smoke and the `verify-hdhomerun-streaming` skill. Slice logs from the kickstart timestamp (Issue 53).

## Still blocked on owner approval (frozen bedrock)

These still emit deprecation warnings on 3.12+. None breaks on 3.15:

- `datetime.utcnow()`: 40 calls in `streaming/channel_manager.py`, `streaming/youtube_adapter.py`,
  `cache/{cache_manager,download_queue,download_scheduler}.py`, `scheduling/{playout_timeline,engine}.py`, `api/iptv.py`.
  Replace with `streamtv.utils.clock.utc_now_naive()`, which keeps the naive-UTC contract.
- `asyncio.get_event_loop()`: 7 calls in `streaming/channel_manager.py`, `streaming/youtube_adapter.py`,
  `cache/youtube_downloader.py`. Use `asyncio.get_running_loop()` inside coroutines.
- Text `open()` calls without `encoding=`: `scheduling/parser.py`, `streaming/pbs_adapter.py`, `streaming/archive_org_adapter.py`.
- Performance: `scheduling/parser.py` parses schedule YAML with pure-Python `yaml.safe_load` on every guide
  request (libyaml `CSafeLoader` is available), and `scheduling/engine.py:resolve_sequence_item` issues
  ~36k SQLite queries per XMLTV build (an N+1 pattern).

## Watch list for 3.16 (~2027-10)

- `slowapi` 0.1.9 calls `asyncio.iscoroutinefunction`, which is **removed in 3.16**. Needs an upstream fix or a replacement.
- The asyncio policy system is removed in 3.16. Nothing in StreamTV uses it directly; check uvicorn's loop setup.
- uvicorn 0.40 uses `websockets.legacy` (deprecated).
- Pydantic V3 drops class-based `Config`. StreamTV and the MCP servers now use `model_config` throughout.
