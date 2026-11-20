# LoudNorm fleet audio

StreamTV can apply a one-pass FFmpeg `loudnorm` + peak limiter profile across channels
so Plex/Live TV levels stay consistent and true-peak spikes are reduced.

Related: [FFmpeg profiles](FFMPEG_PROFILES.md).

## What it does

- Software FFmpeg profile uses one-pass `loudnorm` (typical targets **I=-16**, **TP=-2.0**, linear) plus `alimiter` (~−1 dBFS).
- Channels can be assigned an `ffmpeg_profile_id` (tier **all**).
- Continuous playout binds the profile at **channel start** (not only on-demand).
- Optional auto-rollback demotes **all → music (1985 / 1986 / 1987 / 1991) → off** on sustained FFmpeg CPU / host load, then restarts `com.streamtv`.

## In-tree tooling

| Path | Role |
|------|------|
| FFmpeg software profile + channel `ffmpeg_profile_id` | Product setting (Settings → FFmpeg Profiles) |
| `scripts/loudnorm_policy.py` | Read/write demotion policy (`data/loudnorm_policy.json`) |
| `scripts/monitor_loudnorm_cpu.py` / `.sh` | Sample FFmpeg CPU / load; trigger demotion |
| `scripts/install-loudnorm-monitor-launchagent.sh` | Install CPU monitor LaunchAgent |
| `scripts/monitor_remote_plex_tunes.py` | Optional LAN vs remote HDHomeRun client logging |
| `data/loudnorm_policy.json` | Operator policy state (gitignored / machine-local) |

## Operator workflow

1. Confirm an FFmpeg software profile with loudnorm exists (Settings → FFmpeg Profiles).
2. Assign channels to the profile (fleet **all**, or music-only if CPU is too high).
3. Install the LoudNorm monitor LaunchAgent if you want automatic demotion on spikes.
4. If CPU/load spikes without the monitor, demote assignments manually (music channels only, then off) or soften profile targets.

## Rollback

- Remove or change channel `ffmpeg_profile_id` / soft-disable the LoudNorm profile in Settings.
- Unload the LoudNorm monitor LaunchAgent if installed.
- Policy file may live at `data/loudnorm_policy.json` on the operator Mac.

## Safety notes

- LoudNorm is CPU-heavy; expect higher FFmpeg usage on multi-channel fleets.
- Do not regenerate FFmpeg golden tests to “pass” a profile change — Archive/PBS/YouTube goldens remain frozen.
- Demotion is **rule-based** process metrics, not ML.
