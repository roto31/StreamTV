"""PBS Channel Builder defaults (parity with operator rebuild scripts)."""

from __future__ import annotations

from streamtv.builder.models import BuilderDraft, ChannelInfo
from streamtv.builder.pbs_episode_filter import DEFAULT_MIN_EPISODE_SECONDS


def apply_pbs_source_defaults(draft: BuilderDraft) -> BuilderDraft:
    """Apply recommended PBS long-form channel settings to a draft."""
    channel = draft.channel.model_copy(
        update={
            "playout_mode": draft.channel.playout_mode or "continuous",
            "epg_sync_class": draft.channel.epg_sync_class,
        }
    )
    draft.channel = channel
    draft.pbs_filter_full_episodes = True
    draft.pbs_min_episode_seconds = DEFAULT_MIN_EPISODE_SECONDS
    draft.pbs_exclude_passport_drm = True
    return draft
