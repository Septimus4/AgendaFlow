"""Data loader and persistence."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
import logging

import pandas as pd
import pytz

from .openagenda_client import OpenAgendaClient
from .cleaning import clean_event
from .deduplication import deduplicate_events
from .schema import Event

logger = logging.getLogger(__name__)


class EventLoader:
    """Load and persist events."""

    def __init__(
        self,
        api_key: str,
        data_dir: Path = Path("data"),
        city: str = "Paris",
        days_past: int = 365,
        days_future: int = 180,
    ):
        """Initialize loader.

        Args:
            api_key: OpenAgenda API key
            data_dir: Data directory
            city: City to fetch events for
            days_past: Days in the past to fetch
            days_future: Days in the future to fetch
        """
        self.client = OpenAgendaClient(api_key)
        self.data_dir = Path(data_dir)
        self.city = city
        self.days_past = days_past
        self.days_future = days_future

        # Create directories
        self.raw_dir = self.data_dir / "raw"
        self.clean_dir = self.data_dir / "clean"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.clean_dir.mkdir(parents=True, exist_ok=True)

    def _get_time_range(self) -> tuple[str, str]:
        """Get time range for fetching events.

        Returns:
            Tuple of (start_iso, end_iso)
        """
        now = datetime.now(pytz.utc)
        start = now - timedelta(days=self.days_past)
        end = now + timedelta(days=self.days_future)
        return start.isoformat(), end.isoformat()

    def fetch_events(self, mode: str = "agenda", max_agendas: int = 50) -> List[Event]:
        """Fetch events from OpenAgenda.

        Args:
            mode: Fetch mode - 'agenda' or 'transverse'
            max_agendas: Maximum number of agendas to fetch from (agenda mode)

        Returns:
            List of cleaned events
        """
        timings_gte, timings_lte = self._get_time_range()

        raw_events = []

        if mode == "transverse":
            logger.info("Fetching events using transverse search")
            try:
                for event in self.client.fetch_events_transverse(
                    city=self.city,
                    timings_gte=timings_gte,
                    timings_lte=timings_lte,
                    relative=["current", "upcoming"],
                ):
                    raw_events.append(event)
            except Exception as e:
                logger.error(f"Transverse search failed: {e}")
                logger.info("Falling back to agenda mode")
                mode = "agenda"

        if mode == "agenda":
            logger.info("Fetching events using agenda mode")
            # Discover agendas
            agendas = self.client.discover_agendas(city=self.city, limit=max_agendas)

            if not agendas:
                logger.warning(f"No agendas found for {self.city}")
                return []

            logger.info(f"Found {len(agendas)} agendas")

            # Fetch from each agenda
            for agenda in agendas[:max_agendas]:
                agenda_uid = agenda.get("uid")
                if not agenda_uid:
                    continue

                title = agenda.get("title", str(agenda_uid))
                if isinstance(title, dict):
                    title = title.get("fr", str(agenda_uid))

                logger.info(f"Fetching from agenda: {title}")

                try:
                    for event in self.client.fetch_events_from_agenda(
                        agenda_uid=agenda_uid,
                        city=self.city,
                        timings_gte=timings_gte,
                        timings_lte=timings_lte,
                        relative=["current", "upcoming"],
                    ):
                        raw_events.append(event)
                except Exception as e:
                    logger.error(f"Error fetching from agenda {agenda_uid}: {e}")
                    continue

        logger.info(f"Fetched {len(raw_events)} raw events")

        # Save raw events
        self._save_raw_events(raw_events)

        # Clean events
        cleaned_events = []
        for raw_event in raw_events:
            event = clean_event(raw_event)
            if event:
                cleaned_events.append(event)

        logger.info(f"Cleaned {len(cleaned_events)} events")

        # Deduplicate
        deduplicated_events = deduplicate_events(cleaned_events)

        return deduplicated_events

    def _save_raw_events(self, events: List[dict]):
        """Save raw events to disk.

        Args:
            events: List of raw event dictionaries
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        date_dir = self.raw_dir / datetime.now().strftime("%Y%m%d")
        date_dir.mkdir(parents=True, exist_ok=True)

        output_file = date_dir / f"events_{timestamp}.json"

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(events, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved {len(events)} raw events to {output_file}")

    def save_events_parquet(self, events: List[Event], filename: Optional[str] = None):
        """Save events to Parquet.

        Args:
            events: List of Event objects
            filename: Output filename (default: events_YYYYMMDD.parquet)
        """
        if not events:
            logger.warning("No events to save")
            return

        if filename is None:
            filename = f"events_{datetime.now().strftime('%Y%m%d')}.parquet"

        output_file = self.clean_dir / filename

        # Convert to DataFrame
        df = pd.DataFrame([e.to_dict() for e in events])

        # Save as Parquet
        df.to_parquet(output_file, index=False, engine="pyarrow")

        logger.info(f"Saved {len(events)} events to {output_file}")

    def load_events_parquet(self, filename: str) -> List[Event]:
        """Load events from Parquet.

        Args:
            filename: Input filename

        Returns:
            List of Event objects
        """
        input_file = self.clean_dir / filename

        if not input_file.exists():
            logger.error(f"File not found: {input_file}")
            return []

        df = pd.read_parquet(input_file, engine="pyarrow")

        events = []
        for _, row in df.iterrows():
            try:
                event = Event(**row.to_dict())
                events.append(event)
            except Exception as e:
                logger.error(f"Error loading event: {e}")
                continue

        logger.info(f"Loaded {len(events)} events from {input_file}")

        return events
