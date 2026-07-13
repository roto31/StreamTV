from streamtv.database.models import MediaItem
from streamtv.importers.channel_importer import ChannelImporter


def test_yaml_notes_are_not_used_as_media_description() -> None:
    importer = ChannelImporter(db_session=None)
    media_item = MediaItem(description=None)

    importer._apply_yaml_stream_fields(
        media_item,
        {
            "slot": "S02E08 - Wave Goodbye",
            "notes": "Higgens",
            "runtime": "PT49M18S",
        },
        channel_name="Magnum P.I.",
    )

    assert media_item.description is None


def test_yaml_description_replaces_legacy_notes_description() -> None:
    importer = ChannelImporter(db_session=None)
    media_item = MediaItem(description="Higgens")

    importer._apply_yaml_stream_fields(
        media_item,
        {
            "slot": "S02E08 - Wave Goodbye",
            "description": "Episode summary",
            "notes": "Higgens",
            "runtime": "PT49M18S",
        },
        channel_name="Magnum P.I.",
    )

    assert media_item.description == "Episode summary"
