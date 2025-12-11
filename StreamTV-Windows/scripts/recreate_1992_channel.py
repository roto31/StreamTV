#!/usr/bin/env python3
"""Recreate 1992 Albertville Winter Olympics Channel from scratch"""

import sys
import asyncio
import re
import json
from pathlib import Path
from urllib.parse import urlparse, unquote
from datetime import datetime, timezone
from typing import Dict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session  # type: ignore
from streamtv.database.session import SessionLocal, init_db  # type: ignore
from streamtv.database.models import (  # type: ignore
    Channel,
    MediaItem,
    Collection,
    CollectionItem,
    StreamSource,
    PlayoutMode,
)
from streamtv.streaming import StreamManager  # type: ignore
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ordered list of 63 Archive.org URLs covering every day/part
OLYMPICS_1992_URLS = [
    "https://archive.org/details/1992-winter-olympics-day-01-opening-ceremony-pt.-1/1992+Winter+Olympics+-+Day+01+-+Opening+Ceremony+Pt.+1.mp4",
    "https://archive.org/details/1992-winter-olympics-day-01-opening-ceremony-pt.-1/1992+Winter+Olympics+-+Day+01+-+Opening+Ceremony+Pt.+2.mp4",
    "https://archive.org/details/1992-winter-olympics-day-02-pt.-6/1992+Winter+Olympics+-+Day+02+Pt.+1.mp4",
    "https://archive.org/details/1992-winter-olympics-day-02-pt.-6/1992+Winter+Olympics+-+Day+02+Pt.+2.mp4",
    "https://archive.org/details/1992-winter-olympics-day-02-pt.-6/1992+Winter+Olympics+-+Day+02+Pt.+3.mp4",
    "https://archive.org/details/1992-winter-olympics-day-02-pt.-6/1992+Winter+Olympics+-+Day+02+Pt.+4.mp4",
    "https://archive.org/details/1992-winter-olympics-day-02-pt.-6/1992+Winter+Olympics+-+Day+02+Pt.+5.mp4",
    "https://archive.org/details/1992-winter-olympics-day-02-pt.-6/1992+Winter+Olympics+-+Day+02+Pt.+6.mp4",
    "https://archive.org/details/1992-winter-olympics-day-03-pt.-1/1992+Winter+Olympics+-+Day+03+Pt.+1.mp4",
    "https://archive.org/details/1992-winter-olympics-day-03-pt.-1/1992+Winter+Olympics+-+Day+03+Pt.+2.mp4",
    "https://archive.org/details/1992-winter-olympics-day-03-pt.-1/1992+Winter+Olympics+-+Day+03+Pt.+3.mp4",
    "https://archive.org/details/1992-winter-olympics-day-04-pt.-1/1992+Winter+Olympics+-+Day+04+Pt.+1.mp4",
    "https://archive.org/details/1992-winter-olympics-day-04-pt.-1/1992+Winter+Olympics+-+Day+04+Pt.+2.mp4",
    "https://archive.org/details/1992-winter-olympics-day-04-pt.-1/1992+Winter+Olympics+-+Day+04+Pt.+3.mp4",
    "https://archive.org/details/1992-winter-olympics-day-04-pt.-1/1992+Winter+Olympics+-+Day+04+Pt.+4.mp4",
    "https://archive.org/details/1992-winter-olympics-day-05-pt.-2/1992+Winter+Olympics+-+Day+05+Pt.+1.mp4",
    "https://archive.org/details/1992-winter-olympics-day-05-pt.-2/1992+Winter+Olympics+-+Day+05+Pt.+2.mp4",
    "https://archive.org/details/1992-winter-olympics-day-05-pt.-2/1992+Winter+Olympics+-+Day+05+Pt.+3.mp4",
    "https://archive.org/details/1992-winter-olympics-day-06-pt.-1/1992+Winter+Olympics+-+Day+06+Pt.+1.mp4",
    "https://archive.org/details/1992-winter-olympics-day-06-pt.-1/1992+Winter+Olympics+-+Day+06+Pt.+2.mp4",
    "https://archive.org/details/1992-winter-olympics-day-06-pt.-1/1992+Winter+Olympics+-+Day+06+Pt.+3.mp4",
    "https://archive.org/details/1992-winter-olympics-day-06-pt.-1/1992+Winter+Olympics+-+Day+06+Pt.+4.mp4",
    "https://archive.org/details/1992-winter-olympics-day-07-pt.-2/1992+Winter+Olympics+-+Day+07+Pt.+1.mp4",
    "https://archive.org/details/1992-winter-olympics-day-07-pt.-2/1992+Winter+Olympics+-+Day+07+Pt.+2.mp4",
    "https://archive.org/details/1992-winter-olympics-day-07-pt.-2/1992+Winter+Olympics+-+Day+07+Pt.+3.mp4",
    "https://archive.org/details/1992-winter-olympics-day-07-pt.-2/1992+Winter+Olympics+-+Day+07+Pt.+4.mp4",
    "https://archive.org/details/1992-winter-olympics-day-08-pt.-4/1992+Winter+Olympics+-+Day+08+Pt.+1.mp4",
    "https://archive.org/details/1992-winter-olympics-day-08-pt.-4/1992+Winter+Olympics+-+Day+08+Pt.+2.mp4",
    "https://archive.org/details/1992-winter-olympics-day-08-pt.-4/1992+Winter+Olympics+-+Day+08+Pt.+3.mp4",
    "https://archive.org/details/1992-winter-olympics-day-08-pt.-4/1992+Winter+Olympics+-+Day+08+Pt.+4.mp4",
    "https://archive.org/details/1992-winter-olympics-day-08-pt.-4/1992+Winter+Olympics+-+Day+08+Pt.+5.mp4",
    "https://archive.org/details/1992-winter-olympics-day-08-pt.-4/1992+Winter+Olympics+-+Day+08+Pt.+6.mp4",
    "https://archive.org/details/1992-winter-olympics-day-08-pt.-4/1992+Winter+Olympics+-+Day+08+Pt.+7.mp4",
    "https://archive.org/details/1992-winter-olympics-day-09-pt.-3/1992+Winter+Olympics+-+Day+09+Pt.+1.mp4",
    "https://archive.org/details/1992-winter-olympics-day-09-pt.-3/1992+Winter+Olympics+-+Day+09+Pt.+2.mp4",
    "https://archive.org/details/1992-winter-olympics-day-09-pt.-3/1992+Winter+Olympics+-+Day+09+Pt.+3.mp4",
    "https://archive.org/details/1992-winter-olympics-day-10-pt.-3/1992+Winter+Olympics+-+Day+10+Pt.+1.mp4",
    "https://archive.org/details/1992-winter-olympics-day-10-pt.-3/1992+Winter+Olympics+-+Day+10+Pt.+2.mp4",
    "https://archive.org/details/1992-winter-olympics-day-10-pt.-3/1992+Winter+Olympics+-+Day+10+Pt.+3.mp4",
    "https://archive.org/details/1992-winter-olympics-day-11-pt.-1/1992+Winter+Olympics+-+Day+11+Pt.+1.mp4",
    "https://archive.org/details/1992-winter-olympics-day-11-pt.-1/1992+Winter+Olympics+-+Day+11+Pt.+2.mp4",
    "https://archive.org/details/1992-winter-olympics-day-11-pt.-1/1992+Winter+Olympics+-+Day+11+Pt.+3.mp4",
    "https://archive.org/details/1992-winter-olympics-day-11-pt.-5_20250224/1992+Winter+Olympics+-+Day+11+Pt.+4.mp4",
    "https://archive.org/details/1992-winter-olympics-day-11-pt.-5_20250224/1992+Winter+Olympics+-+Day+11+Pt.+5.mp4",
    "https://archive.org/details/1992-winter-olympics-day-12-pt.-2/1992+Winter+Olympics+-+Day+12+Pt.+1.mp4",
    "https://archive.org/details/1992-winter-olympics-day-12-pt.-2/1992+Winter+Olympics+-+Day+12+Pt.+2.mp4",
    "https://archive.org/details/1992-winter-olympics-day-12-pt.-4/1992+Winter+Olympics+-+Day+12+Pt.+3.mp4",
    "https://archive.org/details/1992-winter-olympics-day-12-pt.-4/1992+Winter+Olympics+-+Day+12+Pt.+4.mp4",
    "https://archive.org/details/1992-winter-olympics-day-13-pt.-1/1992+Winter+Olympics+-+Day+13+Pt.+1.mp4",
    "https://archive.org/details/1992-winter-olympics-day-13-pt.-1/1992+Winter+Olympics+-+Day+13+Pt.+2.mp4",
    "https://archive.org/details/1992-winter-olympics-day-13-pt.-1/1992+Winter+Olympics+-+Day+13+Pt.+3.mp4",
    "https://archive.org/details/1992-winter-olympics-day-13-pt.-1/1992+Winter+Olympics+-+Day+13+Pt.+4.mp4",
    "https://archive.org/details/1992-winter-olympics-day-14-pt.-2/1992+Winter+Olympics+-+Day+14+Pt.+1.mp4",
    "https://archive.org/details/1992-winter-olympics-day-14-pt.-2/1992+Winter+Olympics+-+Day+14+Pt.+2.mp4",
    "https://archive.org/details/1992-winter-olympics-day-14-pt.-3/1992+Winter+Olympics+-+Day+14+Pt.+3.mp4",
    "https://archive.org/details/1992-winter-olympics-day-14-pt.-3/1992+Winter+Olympics+-+Day+14+Pt.+4.mp4",
    "https://archive.org/details/1992-winter-olympics-day-14-pt.-3/1992+Winter+Olympics+-+Day+14+Pt.+5.mp4",
    "https://archive.org/details/1992-winter-olympics-day-15-pt.-3/1992+Winter+Olympics+-+Day+15+Pt.+1.mp4",
    "https://archive.org/details/1992-winter-olympics-day-15-pt.-3/1992+Winter+Olympics+-+Day+15+Pt.+2.mp4",
    "https://archive.org/details/1992-winter-olympics-day-15-pt.-3/1992+Winter+Olympics+-+Day+15+Pt.+3.mp4",
    "https://archive.org/details/1992-winter-olympics-day-16-pt.-2/1992+Winter+Olympics+-+Day+16+Pt.+1.mp4",
    "https://archive.org/details/1992-winter-olympics-day-16-pt.-2/1992+Winter+Olympics+-+Day+16+Pt.+2.mp4",
    "https://archive.org/details/1992-winter-olympics-day-16-pt.-2/1992+Winter+Olympics+-+Day+16+Pt.+3.mp4",
]


def extract_day_from_url(url: str) -> tuple[int, int]:
    """Extract numeric day and part from the filename."""
    path = urlparse(url).path
    filename = path.split("/")[-1]
    decoded_filename = unquote(filename.replace("+", " "))
    decoded_lower = decoded_filename.lower()

    day_match = re.search(r"day\s*(\d+)", decoded_lower, re.IGNORECASE)
    if not day_match:
        return (0, 0)

    day_num = int(day_match.group(1))
    part_match = re.search(r"pt\.\s*(\d+)", decoded_lower, re.IGNORECASE)
    part_num = int(part_match.group(1)) if part_match else 1
    return (day_num, part_num)


def get_collection_name(day: int) -> str:
    """Return the collection name for a given day."""
    return f"1992 Winter Olympics - Day {day:02d}"


async def fetch_metadata_for_url(stream_manager: StreamManager, url: str) -> dict:
    """Fetch metadata from Archive.org for a given video URL."""
    try:
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split('/') if p]

        if "details" not in path_parts:
            raise ValueError(f"Invalid Archive.org URL: {url}")

        idx = path_parts.index("details")
        identifier = path_parts[idx + 1] if idx + 1 < len(path_parts) else None
        filename = path_parts[-1] if path_parts else None
        decoded_filename = unquote(filename.replace("+", " ")) if filename else None

        # Metadata from Archive.org item
        item_info = await stream_manager.archive_org_adapter.get_item_info(identifier)

        # Try to get duration via StreamManager (which resolves actual stream)
        duration = None
        try:
            media_info = await stream_manager.get_media_info(url)
            duration = media_info.get("duration")
        except Exception:
            pass

        metadata = {
            "title": decoded_filename.replace(".mp4", "").strip() if decoded_filename else "Untitled",
            "description": item_info.get("description", "") or "1992 Winter Olympics coverage from CBS",
            "duration": duration,
            "thumbnail": f"https://archive.org/download/{identifier}/__ia_thumb.jpg" if identifier else None,
            "uploader": item_info.get("creator", ""),
            "upload_date": item_info.get("date", ""),
            "url": url,
            "identifier": identifier,
        }
        return metadata
    except Exception as e:
        logger.warning(f"Error fetching metadata for {url}: {e}")
        parsed = urlparse(url)
        filename = parsed.path.split("/")[-1]
        decoded_filename = unquote(filename.replace("+", " "))
        return {
            "title": decoded_filename.replace(".mp4", "").strip(),
            "description": "1992 Winter Olympics coverage",
            "duration": None,
            "thumbnail": None,
            "uploader": None,
            "upload_date": None,
            "url": url,
            "identifier": None,
        }


async def recreate_channel(db: Session):
    """Recreate 1992 channel from scratch."""
    logger.info("=" * 80)
    logger.info("RECREATING 1992 Albertville Winter Olympics Channel")
    logger.info("=" * 80)

    stream_manager = StreamManager()

    # STEP 1: Create or update channel definition
    logger.info("\\n[STEP 1] Creating channel...")
    channel = db.query(Channel).filter(Channel.number == "1992").first()

    if not channel:
        now = datetime.now(timezone.utc)
        channel = Channel(
            number="1992",
            name="1992 Albertville Winter Olympics",
            group="Winter Olympics",
            enabled=True,
            playout_mode=PlayoutMode.ON_DEMAND,
            created_at=now,
            updated_at=now,
        )
        db.add(channel)
        db.commit()
        db.refresh(channel)
        logger.info(f"  ✓ Created channel: {channel.name}")
    else:
        channel.playout_mode = PlayoutMode.ON_DEMAND
        channel.enabled = True
        channel.name = "1992 Albertville Winter Olympics"
        channel.group = "Winter Olympics"
        now = datetime.now(timezone.utc)
        channel.created_at = now
        channel.updated_at = now
        db.commit()
        logger.info(f"  ✓ Updated channel: {channel.name}")

    # STEP 2: Delete existing collections/media for this channel
    logger.info("\\n[STEP 2] Deleting existing 1992 Olympics data...")
    collections = db.query(Collection).filter(
        Collection.name.like("1992 Winter Olympics%")
    ).all()

    deleted_collections = 0
    deleted_items = 0
    for collection in collections:
        items_count = (
            db.query(CollectionItem)
            .filter(CollectionItem.collection_id == collection.id)
            .count()
        )
        db.query(CollectionItem).filter(
            CollectionItem.collection_id == collection.id
        ).delete()
        db.delete(collection)
        deleted_collections += 1
        deleted_items += items_count

    media_items = db.query(MediaItem).filter(
        MediaItem.source == StreamSource.ARCHIVE_ORG,
        MediaItem.url.like("%1992%Winter%Olympics%"),
    ).all()

    deleted_media = 0
    for media_item in media_items:
        db.delete(media_item)
        deleted_media += 1

    db.commit()
    logger.info(
        f"  ✓ Deleted {deleted_collections} collections, {deleted_items} items, {deleted_media} media items"
    )

    # STEP 3: Organize URLs by day
    logger.info("\\n[STEP 3] Organizing URLs by day...")
    urls_by_day: Dict[int, list[tuple[int, str]]] = {}
    for url in OLYMPICS_1992_URLS:
        day, part = extract_day_from_url(url)
        if day == 0:
            logger.warning(f"  ⚠ Could not parse day from: {url}")
            continue
        urls_by_day.setdefault(day, []).append((part, url))

    for day in urls_by_day:
        urls_by_day[day].sort(key=lambda x: x[0])

    logger.info(
        f"  ✓ Organized {len(OLYMPICS_1992_URLS)} URLs into {len(urls_by_day)} days"
    )

    # STEP 4: Import metadata + create collections
    logger.info("\\n[STEP 4] Importing URLs with complete metadata...")
    imported_count = 0

    for day in sorted(urls_by_day.keys()):
        collection_name = get_collection_name(day)
        logger.info(f"\\n  📁 {collection_name}...")

        collection = Collection(
            name=collection_name,
            description=f"1992 Winter Olympics - Day {day:02d} coverage from CBS",
        )
        db.add(collection)
        db.commit()
        db.refresh(collection)

        order = 0
        for part, url in urls_by_day[day]:
            try:
                metadata = await fetch_metadata_for_url(stream_manager, url)
                parsed = urlparse(url)
                path_parts = [p for p in parsed.path.split('/') if p]
                idx = path_parts.index("details")
                identifier = path_parts[idx + 1]

                media_item = MediaItem(
                    source=StreamSource.ARCHIVE_ORG,
                    source_id=identifier,
                    url=url,
                    title=metadata["title"],
                    description=metadata["description"],
                    duration=metadata["duration"],
                    thumbnail=metadata["thumbnail"],
                    uploader=metadata.get("uploader"),
                    upload_date=str(metadata["upload_date"]) if metadata["upload_date"] else None,
                    view_count=None,
                    meta_data=json.dumps(metadata),
                )
                db.add(media_item)
                db.commit()
                db.refresh(media_item)

                collection_item = CollectionItem(
                    collection_id=collection.id,
                    media_item_id=media_item.id,
                    order=order,
                )
                db.add(collection_item)
                db.commit()

                logger.info(f"    ✓ [{order + 1}/{len(urls_by_day[day])}] {media_item.title[:60]}")
                imported_count += 1
                order += 1
                await asyncio.sleep(0.3)
            except Exception as e:
                logger.error(f"    ✗ Failed to import {url}: {e}")
                import traceback

                traceback.print_exc()
                continue

    logger.info(f"\\n  ✓ Imported {imported_count} media items total")
    logger.info("\\n" + "=" * 80)
    logger.info("✅ 1992 CHANNEL RECREATION COMPLETE!")
    logger.info("=" * 80)
    logger.info("  ✓ Channel created/updated: 1992 Albertville Winter Olympics")
    logger.info("  ✓ Channel set to ON_DEMAND mode")
    logger.info(f"  ✓ Imported {imported_count} media items")
    logger.info(f"  ✓ Created {len(urls_by_day)} collections")
    logger.info("\\n📋 NEXT STEPS:")
    logger.info("  1. Restart the server: ./stop_server.sh && ./start_server.sh")
    logger.info("  2. Channel 1992 now starts at Day 01 when accessed")
    logger.info("  3. Test the channel to confirm sequential playback")
    logger.info("=" * 80)


async def main():
    """Script entry point."""
    init_db()
    db = SessionLocal()
    try:
        await recreate_channel(db)
    except Exception as e:
        logger.error(f"❌ Error during recreation: {e}")
        import traceback

        traceback.print_exc()
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())


