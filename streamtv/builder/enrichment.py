"""Post-build / CLI channel metadata enrichment (TVDB / TVMaze / TMDB).

Playback-safe by default: writes ``meta_data.enrichment`` and optional
description/thumbnail columns; never changes ``MediaItem.duration``.
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import date
from typing import Any, Dict, List, Literal, Optional, Tuple

from streamtv.builder.models import LinkStatus
from streamtv.config import config
from streamtv.database.models import (
    Channel,
    Collection,
    CollectionItem,
    MediaItem,
    Playlist,
    PlaylistItem,
)
from streamtv.database.session import SessionLocal
from streamtv.utils.media_meta import append_conflict_log, has_enrichment, merge_enrichment
from streamtv.utils.metadata_providers import create_metadata_manager

logger = logging.getLogger(__name__)

EnrichType = Literal["series", "movie"]

_CHANNEL_NAME_NOISE = re.compile(
    r"""
    \s*[\(\[]?\s*
    (?:
        seasons?\s*\d+.*|
        complete\s+series|
        marathon|
        mp4\s+only|
        \(seasons?\s*[^)]*\)|
        \[\s*seasons?\s*[^\]]*\]
    )
    [\)\]]?\s*
    """,
    re.IGNORECASE | re.VERBOSE,
)

_SXXEXX_PREFIX = re.compile(
    r"^(?P<show>.+?)\s*[-–—]\s*[Ss](?P<season>\d{1,2})[Ee](?P<episode>\d{1,3})\b"
)
_NXX_PREFIX = re.compile(
    r"^(?P<show>.+?)\s*[-–—]\s*(?P<season>\d{1,2})x(?P<episode>\d{1,3})\b"
)
_YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")


def parse_episode_from_title(title: str) -> Tuple[Optional[int], Optional[int]]:
    """Extract season and episode from title."""
    patterns = [
        r"[sS](\d+)[eE](\d+)",
        r"(\d+)x(\d+)",
        r"[Ss]eason\s+(\d+).*?[Ee]pisode\s+(\d+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, title or "")
        if match:
            return int(match.group(1)), int(match.group(2))
    m = re.search(r"[Ee]pisode\s+(\d{1,4})\b", title or "")
    if m:
        return 0, int(m.group(1))
    return None, None


def parse_episode_from_url(url: str) -> Tuple[Optional[int], Optional[int]]:
    """Extract season/episode from Archive.org-style paths."""
    from urllib.parse import unquote

    text = unquote(url or "")
    match = re.search(r"[sS](\d{1,2})[eE](\d{1,3})", text)
    if match:
        return int(match.group(1)), int(match.group(2))
    match = re.search(r"(?<![0-9])(\d{1,2})x(\d{1,3})(?![0-9])", text, re.I)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None, None


def parse_movie_title_year(title: str) -> Tuple[str, Optional[int]]:
    """Strip year/noise from movie titles for TMDB search."""
    raw = (title or "").strip()
    year = None
    m = re.search(r"\((19\d{2}|20\d{2})\b", raw)
    if m:
        year = int(m.group(1))
        raw = re.sub(r"\([^)]*\)", " ", raw).strip()
    if year is None:
        m2 = re.search(r"\b(19\d{2}|20\d{2})\b", raw)
        if m2:
            year = int(m2.group(1))
            raw = (raw[: m2.start()] + raw[m2.end() :]).strip(" -_")
    raw = re.sub(
        r"\b(extended|director'?s?\s*cut|dubbed|remastered|unrated)\b",
        " ",
        raw,
        flags=re.I,
    )
    raw = re.sub(r"\s+", " ", raw).strip(" -_")
    if "emperor" in raw.lower() and "clothes" in raw.lower() and "emperor's" not in raw.lower():
        raw = raw.replace("Emperors", "Emperor's").replace("emperors", "emperor's")
    raw = re.sub(r"^\d+\s*-\s*", "", raw)
    raw = re.sub(r"\.ia$", "", raw, flags=re.I).strip()
    return raw or (title or "").strip(), year


def clean_channel_name_for_series(name: str) -> str:
    """Strip marathon / season-range noise from a Builder channel name."""
    cleaned = _CHANNEL_NAME_NOISE.sub(" ", name or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -–—")
    return cleaned


def detect_series_from_titles(titles: list[str]) -> Tuple[Optional[str], Optional[int]]:
    """Best-effort show name + year from stream titles."""
    show_votes: Dict[str, int] = {}
    year: Optional[int] = None
    for title in titles:
        if not title:
            continue
        if year is None:
            ym = _YEAR_RE.search(title)
            if ym:
                year = int(ym.group(1))
        m = _SXXEXX_PREFIX.match(title.strip()) or _NXX_PREFIX.match(title.strip())
        if m:
            show = clean_channel_name_for_series(m.group("show"))
            if show:
                show_votes[show] = show_votes.get(show, 0) + 1
    if not show_votes:
        return None, year
    best = max(show_votes.items(), key=lambda kv: kv[1])[0]
    return best, year


def resolve_enrichment_identity(draft: Any) -> Tuple[Optional[str], Optional[int], EnrichType]:
    """Resolve series/movie name and year from Channel Info + link titles.

    Returns ``(name, year, enrich_type)``. ``name`` may be None when nothing usable
    can be inferred (caller should skip enrichment).
    """
    channel = getattr(draft, "channel", None)
    if channel is None:
        return None, None, "series"

    enrich_type: EnrichType = getattr(channel, "enrichment_type", None) or "series"
    explicit_name = (getattr(channel, "enrichment_series_name", None) or "").strip()
    explicit_year = getattr(channel, "enrichment_year", None)
    if explicit_year is not None:
        try:
            explicit_year = int(explicit_year)
        except (TypeError, ValueError):
            explicit_year = None

    if explicit_name:
        return explicit_name, explicit_year, enrich_type

    channel_name = clean_channel_name_for_series(getattr(channel, "name", "") or "")
    titles: list[str] = []
    for link in getattr(draft, "links", None) or []:
        status = getattr(link, "status", None)
        if status != LinkStatus.OK and getattr(status, "value", status) != "ok":
            continue
        if getattr(link, "title", None):
            titles.append(str(link.title))

    sniffed_name, sniffed_year = detect_series_from_titles(titles)
    name = channel_name or sniffed_name
    year = explicit_year if explicit_year is not None else sniffed_year
    if not name and sniffed_name:
        name = sniffed_name
    return (name or None), year, enrich_type


def apply_enrichment(
    media_item: MediaItem,
    metadata: Dict[str, Any],
    *,
    meta_only: bool,
    update_columns: bool,
) -> None:
    """Write enrichment onto meta_data; optionally columns. Never duration."""
    payload = dict(metadata)
    thumb = payload.get("thumbnail") or payload.get("poster")
    if thumb:
        payload["thumbnail"] = thumb

    if update_columns and not meta_only:
        if payload.get("title"):
            ep_title = payload.get("title")
            series = payload.get("series_name")
            season = payload.get("season")
            episode = payload.get("episode")
            if series and season is not None and episode is not None:
                media_item.title = (
                    f"{series} - S{int(season):02d}E{int(episode):02d} - {ep_title}"
                )
            else:
                media_item.title = ep_title
        if payload.get("description"):
            media_item.description = payload["description"]
        if thumb:
            media_item.thumbnail = thumb
    elif update_columns and meta_only:
        if payload.get("description"):
            media_item.description = payload["description"]
        if thumb:
            media_item.thumbnail = thumb

    media_item.meta_data = merge_enrichment(media_item.meta_data, payload)

    if payload.get("unverified") or payload.get("conflicts"):
        append_conflict_log(
            {
                "date": date.today().isoformat(),
                "media_id": media_item.id,
                "title": media_item.title,
                "source": payload.get("source"),
                "unverified": payload.get("unverified"),
                "conflicts": payload.get("conflicts"),
            }
        )


def movie_query_from_item(media_item: MediaItem) -> Tuple[str, Optional[int]]:
    """Prefer archive episode_title / URL filename over overwritten MediaItem.title."""
    from urllib.parse import unquote

    from streamtv.utils.media_meta import get_archive, parse_meta_data

    archive = get_archive(parse_meta_data(media_item.meta_data))
    raw = (
        (archive.get("episode_title") or "").strip()
        or (media_item.title or "").strip()
    )
    year = None
    url = unquote(media_item.url or "")
    m = re.search(r"\((19\d{2}|20\d{2})\)", url)
    if m:
        year = int(m.group(1))
    title, parsed_year = parse_movie_title_year(raw)
    if year is None:
        year = parsed_year
    return title, year


def channel_playlist_media(db: Any, channel: Channel) -> List[MediaItem]:
    out: List[MediaItem] = []
    seen: set[int] = set()
    playlists = db.query(Playlist).filter(Playlist.channel_id == channel.id).all()
    for playlist in playlists:
        items = (
            db.query(PlaylistItem)
            .filter(PlaylistItem.playlist_id == playlist.id)
            .order_by(PlaylistItem.order)
            .all()
        )
        for item in items:
            if item.media_item_id in seen:
                continue
            media = db.get(MediaItem, item.media_item_id)
            if media:
                seen.add(media.id)
                out.append(media)
    return out


def channel_schedule_media(db: Any, channel: Channel) -> List[MediaItem]:
    from streamtv.scheduling.playout_timeline import load_channel_stream_schedule

    out: List[MediaItem] = []
    seen: set[int] = set()
    try:
        sched = load_channel_stream_schedule(channel, db)
    except Exception as exc:
        logger.warning("Schedule load failed for enrich: %s", exc)
        return out
    for it in sched:
        m = it.get("media_item")
        if not m or m.id in seen:
            continue
        seen.add(m.id)
        media = db.get(MediaItem, m.id)
        if media:
            out.append(media)
    return out


def resolve_season_episode(
    media_item: MediaItem,
    season_from_coll: Optional[int],
) -> Tuple[Optional[int], Optional[int]]:
    season, episode = parse_episode_from_title(media_item.title or "")
    if season is None or episode is None:
        u_season, u_episode = parse_episode_from_url(media_item.url or "")
        if season is None:
            season = u_season
        if episode is None:
            episode = u_episode
    if season_from_coll is not None and (season is None or season > 50 or season == 0):
        if season == 0 and episode is not None and season_from_coll is None:
            pass
        elif season is None or season > 50:
            season = season_from_coll
            if episode is None:
                _, episode = parse_episode_from_title(media_item.title or "")
            if episode is None:
                _, episode = parse_episode_from_url(media_item.url or "")
    return season, episode


SeriesProvider = Literal["tvmaze", "tvdb", "both"]


def series_provider_flags(
    provider: Optional[SeriesProvider] = None,
) -> Tuple[bool, bool]:
    """Map draft provider choice to (enable_tvdb, enable_tvmaze)."""
    choice = provider or "tvmaze"
    if choice == "tvmaze":
        return False, True
    if choice == "tvdb":
        return True, False
    return True, True


def providers_ready_for(
    enrich_type: EnrichType,
    *,
    enable_tvdb: Optional[bool] = None,
    enable_tvmaze: Optional[bool] = None,
) -> Tuple[bool, Optional[str]]:
    """Return (ok, skip_reason)."""
    if not config.metadata.enabled:
        return False, "Metadata enrichment is disabled in config (metadata.enabled)"
    if enrich_type == "series":
        use_tvdb = config.metadata.enable_tvdb if enable_tvdb is None else enable_tvdb
        use_tvmaze = config.metadata.enable_tvmaze if enable_tvmaze is None else enable_tvmaze
        has_tvdb_creds = bool(config.metadata.tvdb_read_token or config.metadata.tvdb_api_key)
        if use_tvdb and not has_tvdb_creds and not use_tvmaze:
            return False, "TVDB selected but no API key / read token configured"
        if use_tvdb and not has_tvdb_creds and use_tvmaze:
            # Both requested without key → TVMaze-only is still usable
            return True, None
        if not use_tvdb and not use_tvmaze:
            return False, "No series metadata provider selected"
        if use_tvmaze or has_tvdb_creds:
            return True, None
        return False, "No TVDB credentials and TVMaze disabled"
    if not config.metadata.enable_tmdb or not config.metadata.tmdb_api_key:
        return False, "TMDB is not configured (metadata.tmdb_api_key / enable_tmdb)"
    return True, None


async def enrich_series(
    *,
    channel_number: str,
    series_name: str,
    series_year: Optional[int],
    dry_run: bool = False,
    force: bool = False,
    from_schedule: bool = True,
    meta_only: bool = True,
    update_columns: bool = True,
    verbose: bool = True,
    enable_tvdb: Optional[bool] = None,
    enable_tvmaze: Optional[bool] = None,
) -> Dict[str, Any]:
    """Enrich series episodes for a channel. Returns summary dict."""
    use_tvdb = config.metadata.enable_tvdb if enable_tvdb is None else enable_tvdb
    use_tvmaze = config.metadata.enable_tvmaze if enable_tvmaze is None else enable_tvmaze
    # Both without credentials → degrade to TVMaze-only
    if use_tvdb and not (config.metadata.tvdb_api_key or config.metadata.tvdb_read_token):
        use_tvdb = False
        if not use_tvmaze:
            use_tvmaze = True
    summary: Dict[str, Any] = {
        "mode": "series",
        "series_name": series_name,
        "series_year": series_year,
        "total": 0,
        "updated": 0,
        "skipped": 0,
        "failed": 0,
        "channel_number": channel_number,
        "enable_tvdb": use_tvdb,
        "enable_tvmaze": use_tvmaze,
    }
    db = SessionLocal()
    try:
        channel = db.query(Channel).filter(Channel.number == channel_number).first()
        if not channel:
            summary["warning"] = f"Channel {channel_number} not found"
            return summary

        if verbose:
            print(f"Channel: {channel.name}")
            print(f"  Series: {series_name}")
            if series_year:
                print(f"  Year: {series_year}")
            print(
                f"  from_schedule={from_schedule} meta_only={meta_only} "
                f"update_columns={update_columns}"
            )
            print()

        metadata_manager = create_metadata_manager(
            tvdb_api_key=config.metadata.tvdb_api_key,
            tvdb_read_token=config.metadata.tvdb_read_token,
            tmdb_api_key=config.metadata.tmdb_api_key,
            enable_tvdb=use_tvdb,
            enable_tvmaze=use_tvmaze,
            enable_tmdb=config.metadata.enable_tmdb,
            tvmaze_username=config.metadata.tvmaze_username,
            tvmaze_api_key=config.metadata.tvmaze_api_key,
        )

        work_items: List[Tuple[MediaItem, Optional[int]]] = []
        if from_schedule:
            media_list = channel_schedule_media(db, channel)
            if verbose:
                print(f"Found {len(media_list)} schedule media items")
            for media_item in media_list:
                work_items.append((media_item, None))
        else:
            collections = (
                db.query(Collection)
                .filter(Collection.name.like(f"%{series_name}%"))
                .all()
            )
            if not collections:
                summary["warning"] = f"No collections found for '{series_name}'"
                if verbose:
                    print(summary["warning"])
                return summary
            if verbose:
                print(f"Found {len(collections)} collections")
            for collection in collections:
                season_match = re.search(r"Season\s+(\d+)", collection.name, re.I)
                season_from_coll = int(season_match.group(1)) if season_match else None
                items = (
                    db.query(CollectionItem)
                    .filter(CollectionItem.collection_id == collection.id)
                    .order_by(CollectionItem.order)
                    .all()
                )
                for item in items:
                    media_item = db.get(MediaItem, item.media_item_id)
                    if media_item:
                        work_items.append((media_item, season_from_coll))

        metadata_cache: Dict[str, Any] = {}
        for media_item, season_from_coll in work_items:
            summary["total"] += 1
            if not force and has_enrichment(media_item.meta_data):
                summary["skipped"] += 1
                continue

            season, episode = resolve_season_episode(media_item, season_from_coll)
            if season is None or episode is None:
                if verbose:
                    print(f"  Skip (no S/E): {(media_item.title or '')[:70]}")
                summary["failed"] += 1
                continue

            cache_key = f"S{season:02d}E{episode:02d}"
            if cache_key in metadata_cache:
                metadata = metadata_cache[cache_key]
            else:
                if verbose:
                    print(f"  Fetching {cache_key}...")
                metadata = await metadata_manager.get_tv_episode_metadata(
                    series_name=series_name,
                    season=season,
                    episode=episode,
                    year=series_year,
                )
                metadata_cache[cache_key] = metadata
                await asyncio.sleep(0.1)

            if not metadata:
                if verbose:
                    print(f"  No metadata for {cache_key}")
                summary["failed"] += 1
                continue

            if dry_run:
                if verbose:
                    print(
                        f"  [DRY RUN] {cache_key} -> {metadata.get('title')} "
                        f"({metadata.get('source')})"
                    )
                summary["updated"] += 1
            else:
                apply_enrichment(
                    media_item,
                    metadata,
                    meta_only=meta_only,
                    update_columns=update_columns,
                )
                if verbose:
                    print(
                        f"  Updated {cache_key}: {metadata.get('title')} "
                        f"[{metadata.get('source')}]"
                    )
                summary["updated"] += 1

        if not dry_run:
            db.commit()
            if verbose:
                print("\nChanges committed to database")

        if verbose:
            print("\n" + "=" * 60)
            print("Series enrichment summary")
            print(f"Total items: {summary['total']}")
            print(f"Updated: {summary['updated']}")
            print(f"Skipped: {summary['skipped']} (already enriched; use --force)")
            print(f"Failed: {summary['failed']}")
            print("=" * 60)
            if dry_run:
                print("\nDry run only — re-run without --dry-run to write the database.")
            else:
                print("\nDone. Reload Plex guide after XMLTV emit picks up enrichment.")
        return summary
    finally:
        db.close()


async def enrich_movies(
    *,
    channel_number: str,
    label: str,
    dry_run: bool = False,
    force: bool = False,
    from_schedule: bool = True,
    meta_only: bool = True,
    update_columns: bool = True,
    verbose: bool = True,
) -> Dict[str, Any]:
    summary: Dict[str, Any] = {
        "mode": "movie",
        "series_name": label,
        "total": 0,
        "updated": 0,
        "skipped": 0,
        "failed": 0,
        "channel_number": channel_number,
    }
    db = SessionLocal()
    try:
        channel = db.query(Channel).filter(Channel.number == channel_number).first()
        if not channel:
            summary["warning"] = f"Channel {channel_number} not found"
            return summary

        if verbose:
            print(f"Channel: {channel.name}")
            print(f"  Movie enrich label: {label}")
            print(f"  from_schedule={from_schedule} meta_only={meta_only}")
            print()

        metadata_manager = create_metadata_manager(
            tvdb_api_key=config.metadata.tvdb_api_key,
            tvdb_read_token=config.metadata.tvdb_read_token,
            tmdb_api_key=config.metadata.tmdb_api_key,
            enable_tvdb=config.metadata.enable_tvdb,
            enable_tvmaze=config.metadata.enable_tvmaze,
            enable_tmdb=config.metadata.enable_tmdb,
            tvmaze_username=config.metadata.tvmaze_username,
            tvmaze_api_key=config.metadata.tvmaze_api_key,
        )

        if from_schedule:
            media_items = channel_schedule_media(db, channel)
        else:
            media_items = channel_playlist_media(db, channel)
            if not media_items:
                collections = db.query(Collection).filter(
                    (Collection.name == channel.name)
                    | (Collection.name == channel_number)
                    | (Collection.name.like(f"%{label}%"))
                ).all()
                seen: set[int] = set()
                for collection in collections:
                    for item in (
                        db.query(CollectionItem)
                        .filter(CollectionItem.collection_id == collection.id)
                        .all()
                    ):
                        if item.media_item_id in seen:
                            continue
                        media = db.get(MediaItem, item.media_item_id)
                        if media:
                            seen.add(media.id)
                            media_items.append(media)

        if not media_items:
            summary["warning"] = "No playlist/collection/schedule media found for channel"
            if verbose:
                print(summary["warning"])
            return summary

        if verbose:
            print(f"Found {len(media_items)} media items")

        cache: Dict[str, Any] = {}
        for media_item in media_items:
            summary["total"] += 1
            if not force and has_enrichment(media_item.meta_data):
                summary["skipped"] += 1
                continue

            title, year = movie_query_from_item(media_item)
            if not title:
                summary["failed"] += 1
                continue

            cache_key = f"{title.lower()}|{year or ''}"
            if cache_key in cache:
                metadata = cache[cache_key]
            else:
                if verbose:
                    print(f"  Fetching movie: {title!r} year={year}")
                metadata = await metadata_manager.get_movie_metadata(title, year)
                cache[cache_key] = metadata
                await asyncio.sleep(0.15)

            if not metadata:
                if verbose:
                    print(f"  No TMDB match for {title!r}")
                summary["failed"] += 1
                append_conflict_log(
                    {
                        "date": date.today().isoformat(),
                        "media_id": media_item.id,
                        "title": media_item.title,
                        "query": title,
                        "year": year,
                        "failed": "no_tmdb_match",
                        "unverified": True,
                    }
                )
                continue

            if dry_run:
                if verbose:
                    print(
                        f"  [DRY RUN] {title} -> {metadata.get('title')} "
                        f"({metadata.get('source')})"
                    )
                summary["updated"] += 1
            else:
                apply_enrichment(
                    media_item,
                    metadata,
                    meta_only=meta_only,
                    update_columns=update_columns,
                )
                if verbose:
                    print(
                        f"  Updated: {metadata.get('title')} [{metadata.get('source')}]"
                    )
                summary["updated"] += 1

        if not dry_run:
            db.commit()
            if verbose:
                print("\nChanges committed to database")

        if verbose:
            print("\n" + "=" * 60)
            print("Movie enrichment summary")
            print(f"Total items: {summary['total']}")
            print(f"Updated: {summary['updated']}")
            print(f"Skipped: {summary['skipped']} (already enriched; use --force)")
            print(f"Failed: {summary['failed']}")
            print("=" * 60)
            if dry_run:
                print("\nDry run only — re-run without --dry-run to write the database.")
        return summary
    finally:
        db.close()


async def enrich_channel_media(
    channel_number: str,
    *,
    series_name: str,
    series_year: Optional[int] = None,
    enrich_type: EnrichType = "series",
    from_schedule: bool = True,
    meta_only: bool = True,
    update_columns: bool = True,
    force: bool = False,
    dry_run: bool = False,
    verbose: bool = False,
    enable_tvdb: Optional[bool] = None,
    enable_tvmaze: Optional[bool] = None,
    series_provider: Optional[SeriesProvider] = None,
) -> Dict[str, Any]:
    """Public entry used by Builder and CLI."""
    if series_provider is not None:
        enable_tvdb, enable_tvmaze = series_provider_flags(series_provider)
    ok, reason = providers_ready_for(
        enrich_type,
        enable_tvdb=enable_tvdb,
        enable_tvmaze=enable_tvmaze,
    )
    if not ok:
        return {
            "mode": enrich_type,
            "series_name": series_name,
            "series_year": series_year,
            "total": 0,
            "updated": 0,
            "skipped": 0,
            "failed": 0,
            "channel_number": channel_number,
            "skipped_enrichment": True,
            "warning": reason,
        }

    if enrich_type == "movie":
        return await enrich_movies(
            channel_number=channel_number,
            label=series_name,
            dry_run=dry_run,
            force=force,
            from_schedule=from_schedule,
            meta_only=meta_only,
            update_columns=update_columns,
            verbose=verbose,
        )
    return await enrich_series(
        channel_number=channel_number,
        series_name=series_name,
        series_year=series_year,
        dry_run=dry_run,
        force=force,
        from_schedule=from_schedule,
        meta_only=meta_only,
        update_columns=update_columns,
        verbose=verbose,
        enable_tvdb=enable_tvdb,
        enable_tvmaze=enable_tvmaze,
    )


async def enrich_built_draft(draft: Any) -> Dict[str, Any]:
    """Run post-build enrichment for a BuilderDraft. Soft-skips on missing identity."""
    channel = getattr(draft, "channel", None)
    if channel is None or not getattr(channel, "enrich_metadata", True):
        return {
            "skipped_enrichment": True,
            "warning": "Enrichment disabled on draft",
            "updated": 0,
            "failed": 0,
            "total": 0,
            "skipped": 0,
        }

    name, year, enrich_type = resolve_enrichment_identity(draft)
    number = str(getattr(channel, "number", "") or "").strip()
    if not number:
        return {
            "skipped_enrichment": True,
            "warning": "No channel number",
            "updated": 0,
            "failed": 0,
            "total": 0,
            "skipped": 0,
        }
    if not name:
        return {
            "skipped_enrichment": True,
            "warning": "Could not resolve series/show name for enrichment",
            "updated": 0,
            "failed": 0,
            "total": 0,
            "skipped": 0,
            "channel_number": number,
        }

    provider = getattr(channel, "enrichment_series_provider", None) or "tvmaze"
    if enrich_type == "series" and provider in ("tvmaze", "both"):
        # Free TVMaze path: ensure metadata section is enabled for this operator.
        if not config.metadata.enabled or not config.metadata.enable_tvmaze:
            config.update_section(
                "metadata",
                {
                    "enabled": True,
                    "enable_tvmaze": True,
                },
            )

    summary = await enrich_channel_media(
        number,
        series_name=name,
        series_year=year,
        enrich_type=enrich_type,
        from_schedule=True,
        meta_only=True,
        update_columns=True,
        force=False,
        dry_run=False,
        verbose=False,
        series_provider=provider if enrich_type == "series" else None,
    )
    summary["identity_source"] = (
        "explicit"
        if (getattr(channel, "enrichment_series_name", None) or "").strip()
        else "auto"
    )
    summary["series_provider"] = provider if enrich_type == "series" else None
    return summary
