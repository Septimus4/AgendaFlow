"""Data cleaning and normalization."""

import re
from datetime import datetime
from typing import Dict, List, Optional
import logging
from html import unescape
from dateutil import parser as date_parser
import pytz

from .schema import Event

logger = logging.getLogger(__name__)

# Paris timezone
PARIS_TZ = pytz.timezone("Europe/Paris")

# Category mapping to normalized taxonomy
CATEGORY_MAPPING = {
    # Music
    "concert": "music",
    "musique": "music",
    "jazz": "music",
    "rock": "music",
    "classique": "music",
    "electronic": "music",
    # Theater
    "théâtre": "theater",
    "theater": "theater",
    "théatre": "theater",
    "spectacle": "theater",
    # Exhibition
    "exposition": "exhibition",
    "exhibition": "exhibition",
    "expo": "exhibition",
    "art": "exhibition",
    "galerie": "exhibition",
    "musée": "exhibition",
    "museum": "exhibition",
    # Kids
    "enfants": "kids",
    "kids": "kids",
    "children": "kids",
    "famille": "kids",
    "family": "kids",
    "jeunesse": "kids",
    # Festival
    "festival": "festival",
    "fête": "festival",
    # Cinema
    "cinéma": "cinema",
    "cinema": "cinema",
    "film": "cinema",
    "projection": "cinema",
    # Dance
    "danse": "dance",
    "dance": "dance",
    "ballet": "dance",
    # Literature
    "littérature": "literature",
    "literature": "literature",
    "lecture": "literature",
    "livre": "literature",
    "book": "literature",
    "salon du livre": "literature",
    # Workshop
    "atelier": "workshop",
    "workshop": "workshop",
    "stage": "workshop",
}


def strip_html(text: str) -> str:
    """Strip HTML tags and decode entities.

    Args:
        text: HTML text

    Returns:
        Plain text
    """
    if not text:
        return ""

    # Decode HTML entities
    text = unescape(text)

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", text)

    # Clean up whitespace
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def normalize_category(categories: List[str], tags: List[str]) -> Optional[str]:
    """Normalize category to taxonomy.

    Args:
        categories: Event categories
        tags: Event tags

    Returns:
        Normalized category or None
    """
    all_terms = [c.lower() for c in categories] + [t.lower() for t in tags]

    for term in all_terms:
        for key, normalized in CATEGORY_MAPPING.items():
            if key in term:
                return normalized

    return None


def determine_price_bucket(price_info: Optional[str], is_free: bool) -> Optional[str]:
    """Determine price bucket.

    Args:
        price_info: Price information string
        is_free: Whether event is free

    Returns:
        Price bucket: free, low, medium, high
    """
    if is_free:
        return "free"

    if not price_info:
        return None

    price_lower = price_info.lower()

    # Extract numbers
    prices = re.findall(r"(\d+(?:[.,]\d+)?)\s*€", price_info)
    if prices:
        # Convert to float (handle both . and , as decimal separator)
        price_values = [float(p.replace(",", ".")) for p in prices]
        min_price = min(price_values)

        if min_price < 10:
            return "low"
        elif min_price < 30:
            return "medium"
        else:
            return "high"

    # Check for keywords
    if any(word in price_lower for word in ["gratuit", "free", "libre"]):
        return "free"

    return None


def extract_arrondissement(address: Optional[str], postal_code: Optional[str]) -> Optional[str]:
    """Extract Paris arrondissement.

    Args:
        address: Street address
        postal_code: Postal code

    Returns:
        Arrondissement (e.g., "11e") or None
    """
    # Try postal code first (750XX format)
    if postal_code:
        match = re.search(r"750(\d{2})", postal_code)
        if match:
            arr_num = int(match.group(1))
            if 1 <= arr_num <= 20:
                return f"{arr_num}e"

    # Try address
    if address:
        match = re.search(r"(\d{1,2})(?:e|ème|eme)\s+arrondissement", address, re.I)
        if match:
            return f"{match.group(1)}e"

    return None


def normalize_datetime(dt_str: str) -> datetime:
    """Normalize datetime to UTC.

    Args:
        dt_str: Datetime string

    Returns:
        UTC datetime
    """
    dt = date_parser.parse(dt_str)

    # If naive, assume Paris timezone
    if dt.tzinfo is None:
        dt = PARIS_TZ.localize(dt)

    # Convert to UTC
    return dt.astimezone(pytz.utc)


def clean_event(raw_event: Dict) -> Optional[Event]:
    """Clean and normalize raw event data.

    Args:
        raw_event: Raw event from API

    Returns:
        Cleaned Event object or None if invalid
    """
    try:
        # Extract core fields
        event_id = str(raw_event.get("uid"))
        if not event_id:
            logger.warning("Event missing UID, skipping")
            return None

        title = raw_event.get("title", {})
        if isinstance(title, dict):
            title = title.get("fr") or title.get("en") or ""
        title = strip_html(str(title))

        if not title:
            logger.warning(f"Event {event_id} missing title, skipping")
            return None

        # Description
        description = raw_event.get("description", {})
        if isinstance(description, dict):
            summary = description.get("fr") or description.get("en") or ""
        else:
            summary = str(description) if description else ""
        summary = strip_html(summary)

        long_desc = raw_event.get("longDescription", {})
        if isinstance(long_desc, dict):
            long_description = long_desc.get("fr") or long_desc.get("en") or ""
        else:
            long_description = str(long_desc) if long_desc else ""
        long_description = strip_html(long_description)

        # Timing
        timings = raw_event.get("timings", [])
        if not timings:
            logger.warning(f"Event {event_id} missing timings, skipping")
            return None

        first_timing = timings[0]
        start_str = first_timing.get("start") or first_timing.get("begin")
        if not start_str:
            logger.warning(f"Event {event_id} missing start time, skipping")
            return None

        start_datetime = normalize_datetime(start_str)
        end_str = first_timing.get("end")
        end_datetime = normalize_datetime(end_str) if end_str else None

        # Location
        location = raw_event.get("location", {})
        venue_name = location.get("name") or "Unknown Venue"
        if not venue_name or venue_name == "Unknown Venue":
            logger.warning(f"Event {event_id} missing venue, skipping")
            return None

        address = location.get("address")
        city = location.get("city", "Paris")
        postal_code = location.get("postalCode")
        country = location.get("countryCode", "FR")

        # Coordinates
        lat = location.get("latitude")
        lon = location.get("longitude")

        # Categories and tags
        categories = raw_event.get("categories", [])
        if isinstance(categories, dict):
            categories = list(categories.values())
        elif not isinstance(categories, list):
            categories = [str(categories)] if categories else []

        # Ensure all categories are strings
        categories = [str(c) for c in categories if c is not None]

        tags = raw_event.get("keywords", [])
        if isinstance(tags, dict):
            tags = list(tags.values())
        elif not isinstance(tags, list):
            tags = [str(tags)] if tags else []

        # Ensure all tags are strings
        tags = [str(t) for t in tags if t is not None]

        category_norm = normalize_category(categories, tags)

        # Price
        conditions = raw_event.get("conditions", {})
        if isinstance(conditions, dict):
            price_info = conditions.get("fr") or conditions.get("en")
        else:
            price_info = str(conditions) if conditions else None

        is_free = raw_event.get("free", False)
        if is_free is None:
            is_free = False

        if price_info and "gratuit" in str(price_info).lower():
            is_free = True

        price_bucket = determine_price_bucket(price_info, is_free)

        # Arrondissement
        arrondissement = extract_arrondissement(address, postal_code)

        # Organizer
        organizer = raw_event.get("organizer", {})
        if isinstance(organizer, dict):
            organizer = organizer.get("name")

        # URLs
        url = raw_event.get("canonicalUrl") or raw_event.get("url")
        image = raw_event.get("image", {})
        if isinstance(image, dict):
            image_url = image.get("base") or image.get("url")
        else:
            image_url = str(image) if image else None

        # Languages
        languages = raw_event.get("lang", ["fr"])
        if isinstance(languages, str):
            languages = [languages]

        # Updated at
        updated_at_str = raw_event.get("updatedAt")
        updated_at = normalize_datetime(updated_at_str) if updated_at_str else None

        # Source agenda
        source_agenda_uid = raw_event.get("agendaUid")
        if source_agenda_uid:
            source_agenda_uid = str(source_agenda_uid)

        # Create Event object
        event = Event(
            event_id=event_id,
            source_agenda_uid=source_agenda_uid,
            title=title,
            summary=summary[:500] if summary else None,
            long_description=long_description[:2000] if long_description else None,
            categories=categories if isinstance(categories, list) else [],
            tags=tags if isinstance(tags, list) else [],
            category_norm=category_norm,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            all_day=first_timing.get("allDay", False),
            timings=timings,
            venue_name=venue_name,
            address=address,
            city=city,
            postal_code=postal_code,
            country=country,
            lat=float(lat) if lat else None,
            lon=float(lon) if lon else None,
            arrondissement=arrondissement,
            organizer=organizer,
            price=price_info,
            is_free=is_free,
            price_bucket=price_bucket,
            language=languages,
            url=url,
            image_url=image_url,
            updated_at=updated_at,
        )

        return event

    except Exception as e:
        logger.error(f"Error cleaning event: {e}", exc_info=True)
        return None
