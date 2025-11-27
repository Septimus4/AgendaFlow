"""Unit tests for deduplication."""

from datetime import datetime
import pytz

from rag.ingest.schema import Event
from rag.ingest.deduplication import compute_similarity, deduplicate_events


def test_compute_similarity_identical():
    """Test similarity of identical strings."""
    similarity = compute_similarity("hello world", "hello world")
    assert similarity == 1.0


def test_compute_similarity_different():
    """Test similarity of different strings."""
    similarity = compute_similarity("hello", "goodbye")
    assert similarity < 0.5


def test_compute_similarity_similar():
    """Test similarity of similar strings."""
    similarity = compute_similarity("Jazz Concert", "Jazz Concerts")
    assert similarity > 0.8


def test_deduplicate_exact_duplicates():
    """Test deduplication of exact duplicates."""
    events = [
        Event(
            event_id="1",
            title="Jazz Concert",
            start_datetime=datetime(2024, 1, 20, 20, 0, tzinfo=pytz.utc),
            venue_name="Le Sunset",
            city="Paris",
        ),
        Event(
            event_id="2",
            title="Jazz Concert",
            start_datetime=datetime(2024, 1, 20, 20, 0, tzinfo=pytz.utc),
            venue_name="Le Sunset",
            city="Paris",
        ),
    ]

    result = deduplicate_events(events)
    assert len(result) == 1


def test_deduplicate_similar_titles():
    """Test deduplication of similar titles."""
    events = [
        Event(
            event_id="1",
            title="Jazz Concert Night",
            start_datetime=datetime(2024, 1, 20, 20, 0, tzinfo=pytz.utc),
            venue_name="Le Sunset",
            city="Paris",
        ),
        Event(
            event_id="2",
            title="Jazz Concert Nights",
            start_datetime=datetime(2024, 1, 20, 20, 0, tzinfo=pytz.utc),
            venue_name="Le Sunset",
            city="Paris",
        ),
    ]

    result = deduplicate_events(events)
    assert len(result) == 1


def test_deduplicate_different_venues():
    """Test that different venues are not deduplicated."""
    events = [
        Event(
            event_id="1",
            title="Jazz Concert",
            start_datetime=datetime(2024, 1, 20, 20, 0, tzinfo=pytz.utc),
            venue_name="Le Sunset",
            city="Paris",
        ),
        Event(
            event_id="2",
            title="Jazz Concert",
            start_datetime=datetime(2024, 1, 20, 20, 0, tzinfo=pytz.utc),
            venue_name="Le Sunside",
            city="Paris",
        ),
    ]

    result = deduplicate_events(events)
    assert len(result) == 2


def test_deduplicate_different_dates():
    """Test that different dates are not deduplicated."""
    events = [
        Event(
            event_id="1",
            title="Jazz Concert",
            start_datetime=datetime(2024, 1, 20, 20, 0, tzinfo=pytz.utc),
            venue_name="Le Sunset",
            city="Paris",
        ),
        Event(
            event_id="2",
            title="Jazz Concert",
            start_datetime=datetime(2024, 1, 21, 20, 0, tzinfo=pytz.utc),
            venue_name="Le Sunset",
            city="Paris",
        ),
    ]

    result = deduplicate_events(events)
    assert len(result) == 2


def test_deduplicate_empty_list():
    """Test deduplication of empty list."""
    result = deduplicate_events([])
    assert result == []
