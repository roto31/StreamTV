# Tuner Visibility Resolution — StreamTV + Tunarr (2026-07-08)

Evidence from Phase 0 (`reports/Phase0_Diagnostic_Report_2026-07-08.md`)
and Plex Media Server logs.

## Verdict

**Tunarr is discovered by Plex SSDP but filtered as incompatible** because its
`discover.json` advertises a non-hex `DeviceID` (`"Tunarr"`) and may echo a
loopback `BaseURL` when fetched via `127.0.0.1`. Plex keys devices as
`device://tv.plex.grabbers.hdhomerun/<DeviceID>` and only proceeds to test
"compatible" devices (log: `discovered 1 compatible devices` after seeing
HDTC-2US twice).

StreamTV was visible with placeholder `FFFFFFFF`; hardening now persists a
stable 8-hex DeviceID and adds native UDP **65001** discovery.

## Hypotheses (tested)

| # | Hypothesis | Result |
|---|---|---|
| 1 | DeviceID collision/dedupe | **Confirmed root cause for Tunarr** — DeviceID=`Tunarr` (non-hex). StreamTV placeholder `FFFFFFFF` also risked silent dedupe; fixed by `streamtv/hdhomerun/device_id.py`. |
| 2 | Discovery contention on UDP 1900 | **Not blocking** — Tunarr, Plex, and StreamTV all bind 1900 via SO_REUSEPORT; Plex *does* see Tunarr SSDP. Mitigated further by StreamTV port-65001 discovery. |
| 3 | Reachability of :8000 | **OK** — `curl http://192.0.2.1:8000/discover.json` succeeds from the Plex host. |
| 4 | Guide / single-XMLTV conflict | **Addressed** — use merged guide `http://<streamtv>/tuners/guide.xml` when adding both tuners. |

## In-place fix (operator) — **implemented**

### Recommended: StreamTV Tunarr proxy (Plex GUI)

See **[Add Tunarr in Plex](guides/ADD_TUNARR_IN_PLEX.md)**.

1. Ensure `tuner_manager.enabled: true` and a `tunarr` entry in `config.yaml`.
2. Restart StreamTV.
3. Plex → Live TV & DVR → Add device → paste:
   `http://192.0.2.1:8410/tuners/proxy/tunarr`
4. Guide: `http://192.0.2.1:8410/tuners/guide.xml`

Inventory / paste URLs: `GET /tuners`.

### Alternatives

1. **Manual add of Tunarr `:8000`** — often still rejected (non-hex DeviceID).
2. **Upstream Tunarr** — request a hex DeviceID setting (not available today).

StreamTV side (done in remediation + proxy build):

- Stable DeviceID persisted at `data/hdhomerun_device_id`
- Native HDHR discovery on UDP 65001
- `/health` reports discovery bind state + DeviceID
- **Tuner manager proxy** — `streamtv/tuners/`, `streamtv/api/tuner_manager.py`

## Standalone tuner manager — **implemented**

Routes (no `/api` prefix; exempt from API key like IPTV):

| Method | Path | Behavior |
|--------|------|----------|
| GET | `/tuners` | Inventory + `plex_add_url` / `plex_guide_url` |
| GET | `/tuners/proxy/{name}/discover.json` | Hex DeviceID + proxy BaseURL |
| GET | `/tuners/proxy/{name}/lineup.json` | Stream hosts rewritten to Tunarr LAN |
| GET | `/tuners/proxy/{name}/lineup_status.json` | Passthrough / static |
| GET | `/tuners/proxy/{name}/device.xml` | Minimal UPnP desc |
| GET | `/tuners/guide.xml` | Merged StreamTV + Tunarr XMLTV |

Video is **not** proxied through StreamTV. SSDP is **not** advertised for the
proxy (GUI paste is enough).

### Config

```yaml
tuner_manager:
  enabled: true
  merged_guide: true
  tuners:
    - name: tunarr
      url: http://192.0.2.1:8000
      # force_device_id omitted → data/tuner_device_ids/tunarr
      force_base_url: null   # null → advertise proxy as BaseURL
      xmltv_url: http://192.0.2.1:8000/api/xmltv.xml
```

Env override: `STREAMTV_TUNER_MANAGER_ENABLED`.

### Risk profile

Low — read-only toward Plex; only standardizes what tuners advertise.
Stream URLs still hit Tunarr directly. Guide merge prefixes colliding channel
ids with `tunarr.`.

## Verification

```bash
curl -s http://127.0.0.1:8410/tuners | python3 -m json.tool
curl -s http://127.0.0.1:8410/tuners/proxy/tunarr/discover.json | python3 -m json.tool
# DeviceID = 8 hex; BaseURL = proxy LAN URL; no 127.0.0.1
curl -s http://127.0.0.1:8410/tuners/proxy/tunarr/lineup.json | head
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8410/tuners/guide.xml
```
