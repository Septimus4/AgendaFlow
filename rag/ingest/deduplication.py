"""Event deduplication."""

from typing import List
import logging
from difflib import SequenceMatcher

from .schema import Event

logger = logging.getLogger(__name__)


def compute_similarity(str1: str, str2: str) -> float:
    """Compute similarity between two strings using Levenshtein-like ratio.

    Args:
        str1: First string
        str2: Second string

    Returns:
        Similarity score between 0 and 1
    """
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()


def deduplicate_events(events: List[Event], similarity_threshold: float = 0.85) -> List[Event]:
    """Deduplicate events based on title, date, and venue.

    Args:
        events: List of events
        similarity_threshold: Minimum similarity for title matching

    Returns:
        Deduplicated list of events
    """
    if not events:
        return []

    # Sort by event_id for deterministic results
    events = sorted(events, key=lambda e: e.event_id)

    seen_keys = set()
    deduplicated = []

    for event in events:
        # Create a key based on normalized title, start date, and venue
        date_key = event.start_datetime.date().isoformat()
        venue_key = event.venue_name.lower().strip()
        title_normalized = event.get_normalized_title()

        # Check for exact matches first
        exact_key = (title_normalized, date_key, venue_key)
        if exact_key in seen_keys:
            logger.debug(f"Skipping duplicate event: {event.title}")
            continue

        # Check for similar titles (fuzzy matching)
        is_duplicate = False
        for existing_event in deduplicated:
            if (
                existing_event.start_datetime.date() == event.start_datetime.date()
                and existing_event.venue_name.lower().strip() == venue_key
            ):
                similarity = compute_similarity(
                    existing_event.get_normalized_title(), title_normalized
                )
                if similarity >= similarity_threshold:
                    logger.debug(
                        f"Skipping similar event (similarity={similarity:.2f}): "
                        f"{event.title} vs {existing_event.title}"
                    )
                    is_duplicate = True
                    break

        if not is_duplicate:
            seen_keys.add(exact_key)
            deduplicated.append(event)

    logger.info(
        f"Deduplicated {len(events)} events to {len(deduplicated)} "
        f"({len(events) - len(deduplicated)} duplicates removed)"
    )

    return deduplicated
