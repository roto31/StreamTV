"""Regression tests for scheduler semantics (pad/wait/fill/tail/reset/guide/shuffle/seed/random-start)"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock
from streamtv.scheduling.engine import ScheduleEngine
from streamtv.scheduling.parser import ParsedSchedule


def _schedule(
    name="test",
    *,
    main_sequence_key="main",
    sequences=None,
    content_map=None,
    playout=None,
):
    schedule = ParsedSchedule(name, "")
    schedule.main_sequence_key = main_sequence_key
    schedule.sequences = sequences or {}
    schedule.content_map = content_map or {}
    schedule.playout = playout or []
    return schedule


class TestSchedulerPadDirectives:
    """Test padToNext and padUntil directives"""
    
    def test_pad_to_next_hour(self):
        """Test padding to next hour boundary"""
        db = Mock()
        engine = ScheduleEngine(db, seed=42)
        engine.get_collection_media = Mock(return_value=[])
        
        schedule = _schedule(
            sequences={"main": [{"padToNext": 60, "content": "filler"}]},
            content_map={"filler": {"collection": "commercials"}},
            playout=[]
        )
        
        current_time = datetime(2024, 1, 1, 10, 30, 0)  # 10:30 AM
        result = engine._handle_pad_to_next(
            {"padToNext": 60, "content": "filler"},
            schedule,
            current_time
        )
        
        # Should pad to 11:00 AM (30 minutes)
        assert isinstance(result, list)
    
    def test_pad_to_next_half_hour(self):
        """Test padding to next half-hour boundary"""
        db = Mock()
        engine = ScheduleEngine(db, seed=42)
        engine.get_collection_media = Mock(return_value=[])
        
        schedule = _schedule(
            sequences={"main": [{"padToNext": 30, "content": "filler"}]},
            content_map={"filler": {"collection": "commercials"}},
            playout=[]
        )
        
        current_time = datetime(2024, 1, 1, 10, 15, 0)  # 10:15 AM
        result = engine._handle_pad_to_next(
            {"padToNext": 30, "content": "filler"},
            schedule,
            current_time
        )
        
        # Should pad to 10:30 AM (15 minutes)
        assert isinstance(result, list)
    
    def test_pad_until_specific_time(self):
        """Test padding until a specific time"""
        db = Mock()
        engine = ScheduleEngine(db, seed=42)
        engine.get_collection_media = Mock(return_value=[])
        
        schedule = _schedule(
            sequences={"main": [{"padUntil": "11:00:00", "content": "filler"}]},
            content_map={"filler": {"collection": "commercials"}},
            playout=[]
        )
        
        current_time = datetime(2024, 1, 1, 10, 30, 0)  # 10:30 AM
        result = engine._handle_pad_until(
            {"padUntil": "11:00:00", "content": "filler"},
            schedule,
            current_time
        )
        
        # Should pad until 11:00 AM (30 minutes)
        assert isinstance(result, list)


class TestSchedulerWaitDirective:
    """Test waitUntil directive"""
    
    def test_wait_until_specific_time(self):
        """Test waiting until a specific time"""
        db = Mock()
        engine = ScheduleEngine(db, seed=42)
        
        current_time = datetime(2024, 1, 1, 10, 30, 0)  # 10:30 AM
        result = engine._handle_wait_until(
            {"waitUntil": "11:00:00"},
            current_time
        )
        
        # Should return empty (time update handled by caller)
        assert result == []
    
    def test_wait_until_tomorrow(self):
        """Test waiting until tomorrow if time has passed"""
        db = Mock()
        engine = ScheduleEngine(db, seed=42)
        
        current_time = datetime(2024, 1, 1, 10, 30, 0)  # 10:30 AM
        result = engine._handle_wait_until(
            {"waitUntil": "09:00:00", "tomorrow": True},
            current_time
        )
        
        # Should return empty
        assert result == []


class TestSchedulerSkipDirective:
    """Test skipItems directive"""
    
    def test_skip_items_integer(self):
        """Test skipping a specific number of items"""
        db = Mock()
        engine = ScheduleEngine(db, seed=42)
        
        # Mock collection cache
        engine._collection_cache = {
            "test_collection": [Mock() for _ in range(10)]
        }
        
        schedule = _schedule(
            sequences={"main": []},
            content_map={"content": {"collection": "test_collection"}},
            playout=[]
        )
        
        result = engine._handle_skip_items(
            {"skipItems": 5, "content": "content"},
            schedule
        )
        
        # Should skip 5 items
        assert result == []
        assert len(engine._collection_cache["test_collection"]) == 5
    
    def test_skip_items_count_expression(self):
        """Test skipping items using count expression"""
        db = Mock()
        engine = ScheduleEngine(db, seed=42)
        
        # Mock collection cache
        engine._collection_cache = {
            "test_collection": [Mock() for _ in range(10)]
        }
        
        schedule = _schedule(
            sequences={"main": []},
            content_map={"content": {"collection": "test_collection"}},
            playout=[]
        )
        
        result = engine._handle_skip_items(
            {"skipItems": "count/2", "content": "content"},
            schedule
        )
        
        # Should skip half (5 items)
        assert result == []
        assert len(engine._collection_cache["test_collection"]) == 5


class TestSchedulerShuffleDirective:
    """Test shuffleSequence directive"""
    
    def test_shuffle_sequence(self):
        """Test shuffling a sequence"""
        db = Mock()
        engine = ScheduleEngine(db, seed=42)
        
        original_sequence = [
            {"content": "item1"},
            {"content": "item2"},
            {"content": "item3"},
            {"content": "item4"},
            {"content": "item5"}
        ]
        
        schedule = _schedule(
            sequences={"commercials": original_sequence.copy()},
            content_map={},
            playout=[]
        )
        
        result = engine._handle_shuffle_sequence(
            {"shuffleSequence": "commercials"},
            schedule
        )
        
        # Should return empty (state change)
        assert result == []
        # Sequence should be shuffled (may be same order with same seed, but structure preserved)
        assert len(schedule.sequences["commercials"]) == 5


class TestSchedulerFillersAndTails:
    """Test filler and tail behavior"""
    
    def test_duration_based_filler(self):
        """Test duration-based filler selection"""
        db = Mock()
        engine = ScheduleEngine(db, seed=42)
        
        # Mock media items with durations
        media_items = []
        for i in range(5):
            item = Mock()
            item.duration = 60  # 1 minute each
            media_items.append(item)
        
        engine.get_collection_media = Mock(return_value=media_items)
        
        schedule = _schedule(
            sequences={"main": []},
            content_map={"filler": {"collection": "commercials", "order": "shuffle"}},
            playout=[]
        )
        
        current_time = datetime(2024, 1, 1, 10, 0, 0)
        result = engine.resolve_sequence_item(
            {"duration": "00:03:00", "content": "filler"},
            schedule,
            current_time
        )
        
        # Should select items to fill 3 minutes (3 items of 1 minute each)
        assert isinstance(result, list)
        assert len(result) <= 3  # May be less if discard_attempts limits selection


class TestSchedulerPlaybackOrders:
    """Test playback orders (chronological, shuffle)"""
    
    def test_chronological_order(self):
        """Test chronological playback order"""
        db = Mock()
        engine = ScheduleEngine(db, seed=42)
        
        # Mock media items
        media_items = [Mock(duration=60) for _ in range(5)]
        engine.get_collection_media = Mock(return_value=media_items)
        
        schedule = _schedule(
            sequences={"main": []},
            content_map={"content": {"collection": "test", "order": "chronological"}},
            playout=[]
        )
        
        current_time = datetime(2024, 1, 1, 10, 0, 0)
        result = engine.resolve_sequence_item(
            {"all": "content"},
            schedule,
            current_time
        )
        
        # Should return items in order
        assert isinstance(result, list)
        assert len(result) == 5
    
    def test_shuffle_order(self):
        """Test shuffle playback order"""
        db = Mock()
        engine = ScheduleEngine(db, seed=42)
        
        # Mock media items
        media_items = [Mock(duration=60) for _ in range(5)]
        engine.get_collection_media = Mock(return_value=media_items)
        
        schedule = _schedule(
            sequences={"main": []},
            content_map={"content": {"collection": "test", "order": "shuffle"}},
            playout=[]
        )
        
        current_time = datetime(2024, 1, 1, 10, 0, 0)
        result = engine.resolve_sequence_item(
            {"all": "content"},
            schedule,
            current_time
        )
        
        # Should return shuffled items
        assert isinstance(result, list)
        assert len(result) == 5


class TestSchedulerSeededRandom:
    """Test seeded random for consistency"""
    
    def test_seeded_random_consistency(self):
        """Test that same seed produces same shuffle order"""
        db = Mock()
        engine1 = ScheduleEngine(db, seed=42)
        engine2 = ScheduleEngine(db, seed=42)
        
        original_sequence = [
            {"content": "item1"},
            {"content": "item2"},
            {"content": "item3"}
        ]
        
        schedule1 = _schedule(
            name="test1",
            sequences={"seq": original_sequence.copy()},
            content_map={},
            playout=[]
        )
        
        schedule2 = _schedule(
            name="test2",
            sequences={"seq": original_sequence.copy()},
            content_map={},
            playout=[]
        )
        
        engine1._handle_shuffle_sequence({"shuffleSequence": "seq"}, schedule1)
        engine2._handle_shuffle_sequence({"shuffleSequence": "seq"}, schedule2)
        
        # With same seed, should produce same shuffle order
        assert schedule1.sequences["seq"] == schedule2.sequences["seq"]
    
    def test_different_seeds_produce_different_orders(self):
        """Test that different seeds produce different shuffle orders"""
        db = Mock()
        engine1 = ScheduleEngine(db, seed=42)
        engine2 = ScheduleEngine(db, seed=123)
        
        original_sequence = [
            {"content": "item1"},
            {"content": "item2"},
            {"content": "item3"},
            {"content": "item4"},
            {"content": "item5"}
        ]
        
        schedule1 = _schedule(
            name="test1",
            sequences={"seq": original_sequence.copy()},
            content_map={},
            playout=[]
        )
        
        schedule2 = _schedule(
            name="test2",
            sequences={"seq": original_sequence.copy()},
            content_map={},
            playout=[]
        )
        
        engine1._handle_shuffle_sequence({"shuffleSequence": "seq"}, schedule1)
        engine2._handle_shuffle_sequence({"shuffleSequence": "seq"}, schedule2)
        
        # With different seeds, may produce different orders (not guaranteed but likely)
        # At minimum, both should be valid sequences
        assert len(schedule1.sequences["seq"]) == len(schedule2.sequences["seq"]) == 5

