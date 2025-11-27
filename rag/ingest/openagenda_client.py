"""OpenAgenda API client."""

import time
from typing import Dict, Iterator, List, Optional
import logging

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class OpenAgendaClient:
    """Client for OpenAgenda API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openagenda.com/v2",
        rate_limit_per_minute: int = 60,
    ):
        """Initialize client.

        Args:
            api_key: OpenAgenda API key
            base_url: Base URL for API
            rate_limit_per_minute: Maximum requests per minute
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.rate_limit_per_minute = rate_limit_per_minute

        # Setup session with retries
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Rate limiting
        self.request_times: List[float] = []

    def _rate_limit(self):
        """Enforce rate limiting."""
        now = time.time()
        # Remove requests older than 1 minute
        self.request_times = [t for t in self.request_times if now - t < 60]

        if len(self.request_times) >= self.rate_limit_per_minute:
            sleep_time = 60 - (now - self.request_times[0])
            if sleep_time > 0:
                logger.info(f"Rate limit reached, sleeping for {sleep_time:.2f}s")
                time.sleep(sleep_time)
                self.request_times = []

        self.request_times.append(now)

    def _make_request(self, url: str, params: Dict) -> Dict:
        """Make API request with rate limiting and error handling.

        Args:
            url: Request URL
            params: Query parameters

        Returns:
            Response JSON

        Raises:
            requests.exceptions.RequestException: On API errors
        """
        self._rate_limit()

        params["key"] = self.api_key

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logger.warning("Rate limit hit, backing off...")
                time.sleep(5)
                return self._make_request(url, params)
            raise

    def fetch_events_from_agenda(
        self,
        agenda_uid: str,
        city: Optional[str] = "Paris",
        timings_gte: Optional[str] = None,
        timings_lte: Optional[str] = None,
        relative: Optional[List[str]] = None,
        monolingual: Optional[str] = "fr",
        size: int = 300,
    ) -> Iterator[Dict]:
        """Fetch events from a specific agenda.

        Args:
            agenda_uid: Agenda UID
            city: Filter by city
            timings_gte: Minimum timing (ISO format)
            timings_lte: Maximum timing (ISO format)
            relative: Relative timing filters (e.g., ['current', 'upcoming'])
            monolingual: Language preference
            size: Page size (max 300)

        Yields:
            Event data dictionaries
        """
        url = f"{self.base_url}/agendas/{agenda_uid}/events"

        params = {
            "size": min(size, 300),
            "detailed": 1,
        }

        if city:
            params["city"] = city
        if timings_gte:
            params["timings[gte]"] = timings_gte
        if timings_lte:
            params["timings[lte]"] = timings_lte
        if relative:
            for rel in relative:
                params["relative[]"] = rel
        if monolingual:
            params["monolingual"] = monolingual

        after = None
        page_count = 0

        while True:
            if after:
                params["after"] = after

            logger.info(f"Fetching page {page_count + 1} from agenda {agenda_uid}")

            try:
                data = self._make_request(url, params)
            except Exception as e:
                logger.error(f"Error fetching events: {e}")
                break

            events = data.get("events", [])
            if not events:
                break

            for event in events:
                yield event

            page_count += 1
            after = data.get("after")

            if not after:
                break

        logger.info(f"Fetched {page_count} pages from agenda {agenda_uid}")

    def fetch_events_transverse(
        self,
        city: Optional[str] = "Paris",
        timings_gte: Optional[str] = None,
        timings_lte: Optional[str] = None,
        relative: Optional[List[str]] = None,
        monolingual: Optional[str] = "fr",
        size: int = 300,
    ) -> Iterator[Dict]:
        """Fetch events using transverse search (experimental).

        Args:
            city: Filter by city
            timings_gte: Minimum timing (ISO format)
            timings_lte: Maximum timing (ISO format)
            relative: Relative timing filters
            monolingual: Language preference
            size: Page size (max 300)

        Yields:
            Event data dictionaries
        """
        url = f"{self.base_url}/events"

        params = {
            "size": min(size, 300),
            "detailed": 1,
        }

        if city:
            params["city"] = city
        if timings_gte:
            params["timings[gte]"] = timings_gte
        if timings_lte:
            params["timings[lte]"] = timings_lte
        if relative:
            for rel in relative:
                params["relative[]"] = rel
        if monolingual:
            params["monolingual"] = monolingual

        after = None
        page_count = 0

        while True:
            if after:
                params["after"] = after

            logger.info(f"Fetching transverse page {page_count + 1}")

            try:
                data = self._make_request(url, params)
            except Exception as e:
                logger.error(f"Error fetching transverse events: {e}")
                # Transverse search might not be enabled
                logger.warning("Transverse search may not be available")
                break

            events = data.get("events", [])
            if not events:
                break

            for event in events:
                yield event

            page_count += 1
            after = data.get("after")

            if not after:
                break

        logger.info(f"Fetched {page_count} transverse pages")

    def discover_agendas(self, city: Optional[str] = "Paris", limit: int = 100) -> List[Dict]:
        """Discover agendas for a city.

        Args:
            city: City to search
            limit: Maximum number of agendas

        Returns:
            List of agenda metadata
        """
        url = f"{self.base_url}/agendas"

        params = {"size": min(limit, 100)}
        if city:
            params["search"] = city

        try:
            data = self._make_request(url, params)
            agendas = data.get("agendas", [])
            logger.info(f"Discovered {len(agendas)} agendas for {city}")
            return agendas
        except Exception as e:
            logger.error(f"Error discovering agendas: {e}")
            return []
