"""Tests for YAML export helpers."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from streamtv.database import Base
from streamtv.database.models import Channel, MediaItem, Playlist, PlaylistItem, StreamSource
from streamtv.exporters.channel_yaml import build_channel_inventory_yaml
from streamtv.scheduling.yaml_export import build_schedule_yaml_from_db
from streamtv.database.models import (
    Collection,
    CollectionItem,
    CollectionType,
    CollectionTypeEnum,
    PlaybackOrder,
    PlayoutModeItem,
    Schedule,
    ScheduleItem,
    StartType,
)


def _session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_build_channel_inventory_yaml() -> None:
    db = _session()
    channel = Channel(number="100", name="Test Channel", enabled=True, group="Demo")
    db.add(channel)
    db.commit()
    db.refresh(channel)

    media = MediaItem(
        source=StreamSource.YOUTUBE,
        source_id="abc123",
        url="https://www.youtube.com/watch?v=abc123",
        title="Sample Video",
        duration=120,
    )
    db.add(media)
    db.commit()
    db.refresh(media)

    playlist = Playlist(name="Test Channel - Main Playlist", channel_id=channel.id)
    db.add(playlist)
    db.commit()
    db.refresh(playlist)
    db.add(PlaylistItem(playlist_id=playlist.id, media_item_id=media.id, order=0))
    db.commit()

    payload = build_channel_inventory_yaml(db, channel)
    assert payload["channels"][0]["number"] == "100"
    assert payload["channels"][0]["streams"][0]["source"] == "youtube"
    assert payload["channels"][0]["streams"][0]["url"].endswith("abc123")


def test_build_schedule_yaml_from_db() -> None:
    db = _session()
    channel = Channel(number="200", name="Schedule Channel", enabled=True)
    db.add(channel)
    db.commit()
    db.refresh(channel)

    collection = Collection(name="Main Collection", collection_type=CollectionTypeEnum.MANUAL)
    db.add(collection)
    db.commit()
    db.refresh(collection)

    schedule = Schedule(name="Evening", channel_id=channel.id)
    db.add(schedule)
    db.commit()
    db.refresh(schedule)

    db.add(
        ScheduleItem(
            schedule_id=schedule.id,
            index=0,
            start_type=StartType.DYNAMIC,
            collection_type=CollectionType.COLLECTION,
            collection_id=collection.id,
            playback_order=PlaybackOrder.CHRONOLOGICAL,
            playout_mode=PlayoutModeItem.ONE,
            custom_title="Prime Time",
        )
    )
    db.commit()

    payload = build_schedule_yaml_from_db(db, channel)
    assert payload["content"][0]["collection"] == "Main Collection"
    assert payload["sequence"][0]["items"][0]["custom_title"] == "Prime Time"
    assert payload["playout"][-1]["repeat"] is True


def test_export_channel_yaml_route() -> None:
    from fastapi.testclient import TestClient
    from streamtv.database import get_db
    from streamtv.main import app

    db = _session()
    channel = Channel(number="300", name="Export Route", enabled=True)
    db.add(channel)
    db.commit()
    db.refresh(channel)

    def _override_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_db
    try:
        client = TestClient(app)
        resp = client.get(f"/api/export/channels/{channel.id}/yaml")
        assert resp.status_code == 200
        assert "yaml" in resp.headers.get("content-type", "")
        assert "300" in resp.text
    finally:
        app.dependency_overrides.clear()
