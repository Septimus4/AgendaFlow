"""Query pre-processing and understanding."""

import re
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import logging

import dateparser
from langdetect import detect, LangDetectException
import pytz

logger = logging.getLogger(__name__)

# Paris timezone
PARIS_TZ = pytz.timezone("Europe/Paris")

# Category keywords and synonyms
CATEGORY_KEYWORDS = {
    "music": [
        "music",
        "musique",
        "concert",
        "jazz",
        "rock",
        "pop",
        "classical",
        "classique",
        "electronic",
        "électronique",
        "rap",
        "hip-hop",
        "opera",
        "opéra",
    ],
    "theater": [
        "theater",
        "theatre",
        "théâtre",
        "théatre",
        "play",
        "pièce",
        "spectacle",
        "performance",
        "comédie",
        "comedy",
    ],
    "exhibition": [
        "exhibition",
        "expo",
        "exposition",
        "art",
        "galerie",
        "gallery",
        "museum",
        "musée",
        "painting",
        "peinture",
        "sculpture",
        "photography",
        "photo",
    ],
    "kids": [
        "kids",
        "enfants",
        "children",
        "family",
        "famille",
        "jeunesse",
        "youth",
        "bébé",
        "baby",
        "tout-petits",
    ],
    "festival": ["festival", "fête", "fest", "celebration", "célébration", "carnival", "carnaval"],
    "cinema": ["cinema", "cinéma", "film", "movie", "projection", "screening"],
    "dance": ["dance", "danse", "ballet", "contemporary", "contemporain", "hip-hop"],
    "literature": [
        "literature",
        "littérature",
        "book",
        "livre",
        "reading",
        "lecture",
        "poetry",
        "poésie",
        "author",
        "auteur",
        "salon du livre",
    ],
    "workshop": ["workshop", "atelier", "stage", "class", "cours", "training", "formation"],
}

# Price keywords
PRICE_KEYWORDS = {
    "free": ["free", "gratuit", "libre", "sans frais"],
    "cheap": ["cheap", "pas cher", "bon marché", "abordable", "affordable"],
}

# Arrondissement patterns
ARRONDISSEMENT_PATTERN = re.compile(
    r"\b(\d{1,2})(?:e|ème|eme|er|ère|th|st|nd|rd)?\s*(?:arr|arrondissement|arrdt)?\b", re.IGNORECASE
)


class QueryProcessor:
    """Process and understand user queries."""

    def __init__(self, default_language: str = "fr", timezone: str = "Europe/Paris"):
        """Initialize processor.

        Args:
            default_language: Default language for responses
            timezone: Timezone for date parsing
        """
        self.default_language = default_language
        self.timezone = pytz.timezone(timezone)

    def detect_language(self, query: str) -> str:
        """Detect query language.

        Args:
            query: Query text

        Returns:
            Language code (fr, en, etc.)
        """
        try:
            lang = detect(query)
            if lang in ["fr", "en"]:
                return lang
            return self.default_language
        except LangDetectException:
            return self.default_language

    def parse_temporal_constraints(
        self, query: str
    ) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Parse temporal constraints from query.

        Args:
            query: Query text

        Returns:
            Tuple of (start_datetime, end_datetime) in UTC, or (None, None)
        """
        query_lower = query.lower()
        now = datetime.now(self.timezone)

        # Common patterns
        if any(word in query_lower for word in ["today", "aujourd'hui", "ce soir"]):
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
            return start.astimezone(pytz.utc), end.astimezone(pytz.utc)

        if any(word in query_lower for word in ["tomorrow", "demain"]):
            start = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
            return start.astimezone(pytz.utc), end.astimezone(pytz.utc)

        if any(word in query_lower for word in ["this weekend", "ce week-end", "weekend"]):
            # Find next Saturday and Sunday
            days_until_saturday = (5 - now.weekday()) % 7
            if days_until_saturday == 0 and now.hour > 12:
                days_until_saturday = 7
            saturday = (now + timedelta(days=days_until_saturday)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            monday = saturday + timedelta(days=2)
            return saturday.astimezone(pytz.utc), monday.astimezone(pytz.utc)

        if any(word in query_lower for word in ["this week", "cette semaine"]):
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=7)
            return start.astimezone(pytz.utc), end.astimezone(pytz.utc)

        if any(
            word in query_lower
            for word in ["next week", "la semaine prochaine", "semaine prochaine"]
        ):
            # Next Monday
            days_until_monday = (7 - now.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 7
            monday = (now + timedelta(days=days_until_monday)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            next_monday = monday + timedelta(days=7)
            return monday.astimezone(pytz.utc), next_monday.astimezone(pytz.utc)

        if any(word in query_lower for word in ["this month", "ce mois", "mois"]):
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=30)
            return start.astimezone(pytz.utc), end.astimezone(pytz.utc)

        if any(word in query_lower for word in ["next month", "le mois prochain", "mois prochain"]):
            # First day of next month
            if now.month == 12:
                start = now.replace(
                    year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0
                )
            else:
                start = now.replace(
                    month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0
                )
            end = start + timedelta(days=30)
            return start.astimezone(pytz.utc), end.astimezone(pytz.utc)

        # Try dateparser for specific dates
        try:
            parsed_dates = dateparser.search.search_dates(
                query,
                languages=["en", "fr"],
                settings={"TIMEZONE": str(self.timezone), "RETURN_AS_TIMEZONE_AWARE": True},
            )
            if parsed_dates and len(parsed_dates) > 0:
                # Take first parsed date
                date_start = parsed_dates[0][1]
                date_end = date_start + timedelta(days=1)
                return date_start.astimezone(pytz.utc), date_end.astimezone(pytz.utc)
        except Exception as e:
            logger.debug(f"Error parsing dates: {e}")

        return None, None

    def extract_category(self, query: str) -> Optional[str]:
        """Extract category intent from query.

        Args:
            query: Query text

        Returns:
            Category name or None
        """
        query_lower = query.lower()

        for category, keywords in CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in query_lower:
                    return category

        return None

    def extract_price_constraint(self, query: str) -> Optional[str]:
        """Extract price constraint from query.

        Args:
            query: Query text

        Returns:
            Price constraint: 'free', 'cheap', or None
        """
        query_lower = query.lower()

        for constraint, keywords in PRICE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in query_lower:
                    return constraint

        return None

    def extract_arrondissement(self, query: str) -> Optional[int]:
        """Extract arrondissement from query.

        Args:
            query: Query text

        Returns:
            Arrondissement number (1-20) or None
        """
        matches = ARRONDISSEMENT_PATTERN.findall(query)

        for match in matches:
            arr_num = int(match)
            if 1 <= arr_num <= 20:
                return arr_num

        return None

    def process_query(self, query: str) -> Dict:
        """Process query and extract all constraints.

        Args:
            query: User query

        Returns:
            Dictionary with processed query information
        """
        language = self.detect_language(query)
        start_date, end_date = self.parse_temporal_constraints(query)
        category = self.extract_category(query)
        price = self.extract_price_constraint(query)
        arrondissement = self.extract_arrondissement(query)

        result = {
            "original_query": query,
            "language": language,
            "start_date": start_date,
            "end_date": end_date,
            "category": category,
            "price_constraint": price,
            "arrondissement": arrondissement,
        }

        logger.info(f"Processed query: {result}")

        return result
