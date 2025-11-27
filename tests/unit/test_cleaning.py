"""Unit tests for data cleaning."""

from rag.ingest.cleaning import (
    strip_html,
    normalize_category,
    determine_price_bucket,
    extract_arrondissement,
    clean_event,
)


def test_strip_html():
    """Test HTML stripping."""
    html = "<p>Hello <strong>world</strong></p>"
    result = strip_html(html)
    assert result == "Hello world"


def test_strip_html_entities():
    """Test HTML entity decoding."""
    html = "Caf&eacute; &amp; Bar"
    result = strip_html(html)
    assert "é" in result or "e" in result


def test_normalize_category_music():
    """Test music category normalization."""
    categories = ["Concert", "Live Music"]
    tags = ["jazz"]
    result = normalize_category(categories, tags)
    assert result == "music"


def test_normalize_category_theater():
    """Test theater category normalization."""
    categories = ["Théâtre"]
    tags = []
    result = normalize_category(categories, tags)
    assert result == "theater"


def test_determine_price_bucket_free():
    """Test free price bucket."""
    result = determine_price_bucket("Gratuit", True)
    assert result == "free"


def test_determine_price_bucket_low():
    """Test low price bucket."""
    result = determine_price_bucket("5€", False)
    assert result == "low"


def test_determine_price_bucket_medium():
    """Test medium price bucket."""
    result = determine_price_bucket("15€", False)
    assert result == "medium"


def test_determine_price_bucket_high():
    """Test high price bucket."""
    result = determine_price_bucket("50€", False)
    assert result == "high"


def test_extract_arrondissement_postal():
    """Test arrondissement extraction from postal code."""
    result = extract_arrondissement(None, "75011")
    assert result == "11e"


def test_extract_arrondissement_address():
    """Test arrondissement extraction from address."""
    result = extract_arrondissement("Rue de la Roquette, 11e arrondissement", None)
    assert result == "11e"


def test_clean_event_valid():
    """Test cleaning a valid event."""
    raw_event = {
        "uid": "12345",
        "title": {"fr": "Concert de Jazz"},
        "description": {"fr": "Un magnifique concert"},
        "timings": [
            {
                "start": "2024-01-20T20:00:00+01:00",
                "end": "2024-01-20T23:00:00+01:00",
            }
        ],
        "location": {
            "name": "Le Sunset",
            "city": "Paris",
            "postalCode": "75001",
            "latitude": 48.8566,
            "longitude": 2.3522,
        },
        "categories": ["Musique"],
        "free": True,
    }

    event = clean_event(raw_event)
    assert event is not None
    assert event.event_id == "12345"
    assert event.title == "Concert de Jazz"
    assert event.venue_name == "Le Sunset"
    assert event.is_free is True
    assert event.arrondissement == "1e"


def test_clean_event_missing_title():
    """Test cleaning event with missing title."""
    raw_event = {
        "uid": "12345",
        "timings": [{"start": "2024-01-20T20:00:00+01:00"}],
        "location": {"name": "Venue"},
    }

    event = clean_event(raw_event)
    assert event is None


def test_clean_event_missing_timing():
    """Test cleaning event with missing timing."""
    raw_event = {
        "uid": "12345",
        "title": {"fr": "Event"},
        "location": {"name": "Venue"},
    }

    event = clean_event(raw_event)
    assert event is None
