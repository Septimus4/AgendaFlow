"""Unit tests for query processor."""

import pytest

from rag.pipeline.query_processor import QueryProcessor


@pytest.fixture
def processor():
    """Create query processor."""
    return QueryProcessor(default_language="fr", timezone="Europe/Paris")


def test_detect_language_french(processor):
    """Test French language detection."""
    query = "Quels concerts de musique classique ce week-end à Paris ?"
    lang = processor.detect_language(query)
    assert lang == "fr"


def test_detect_language_english(processor):
    """Test English language detection."""
    query = "What concerts this weekend?"
    lang = processor.detect_language(query)
    assert lang == "en"


def test_parse_today(processor):
    """Test parsing 'today'."""
    query = "Events today"
    start, end = processor.parse_temporal_constraints(query)

    assert start is not None
    assert end is not None
    assert (end - start).days == 1


def test_parse_tomorrow(processor):
    """Test parsing 'tomorrow'."""
    query = "Events tomorrow"
    start, end = processor.parse_temporal_constraints(query)

    assert start is not None
    assert end is not None
    assert (end - start).days == 1


def test_parse_weekend(processor):
    """Test parsing 'weekend'."""
    query = "Events this weekend"
    start, end = processor.parse_temporal_constraints(query)

    assert start is not None
    assert end is not None
    # Weekend is Saturday + Sunday
    assert (end - start).days == 2


def test_extract_category_music(processor):
    """Test music category extraction."""
    query = "Jazz concerts this weekend"
    category = processor.extract_category(query)
    assert category == "music"


def test_extract_category_theater(processor):
    """Test theater category extraction."""
    query = "Théâtre dans le 11e"
    category = processor.extract_category(query)
    assert category == "theater"


def test_extract_category_exhibition(processor):
    """Test exhibition category extraction."""
    query = "Expositions d'art"
    category = processor.extract_category(query)
    assert category == "exhibition"


def test_extract_price_free(processor):
    """Test free price extraction."""
    query = "Free events today"
    price = processor.extract_price_constraint(query)
    assert price == "free"


def test_extract_price_free_french(processor):
    """Test free price extraction in French."""
    query = "Événements gratuits"
    price = processor.extract_price_constraint(query)
    assert price == "free"


def test_extract_arrondissement(processor):
    """Test arrondissement extraction."""
    query = "Events in the 11th arrondissement"
    arr = processor.extract_arrondissement(query)
    assert arr == 11


def test_extract_arrondissement_french(processor):
    """Test arrondissement extraction in French."""
    query = "Événements dans le 11e"
    arr = processor.extract_arrondissement(query)
    assert arr == 11


def test_process_query_comprehensive(processor):
    """Test comprehensive query processing."""
    query = "Free jazz concerts this weekend in the 11e"
    result = processor.process_query(query)

    assert result["original_query"] == query
    assert result["language"] == "en"
    assert result["category"] == "music"
    assert result["price_constraint"] == "free"
    assert result["arrondissement"] == 11
    assert result["start_date"] is not None
    assert result["end_date"] is not None
