#!/usr/bin/env python3
"""Script to build the FAISS index."""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.config import get_settings
from rag.index.embeddings import EmbeddingGenerator
from rag.index.faiss_index import FAISSIndexManager
from rag.ingest.loader import EventLoader

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Build index from OpenAgenda data."""
    logger.info("Starting index build...")

    # Load settings
    settings = get_settings()

    # Initialize loader
    logger.info("Initializing event loader...")
    loader = EventLoader(
        api_key=settings.openagenda_api_key,
        data_dir=Path("data"),
        city=settings.city,
    )

    # Fetch events
    logger.info(f"Fetching events for {settings.city} (mode={settings.openagenda_mode})...")
    events = loader.fetch_events(
        mode=settings.openagenda_mode,
        max_agendas=50,
    )

    if not events:
        logger.error("No events fetched!")
        sys.exit(1)

    logger.info(f"Fetched {len(events)} events")

    # Save to Parquet
    loader.save_events_parquet(events)

    # Initialize embedding generator
    logger.info("Initializing embedding generator...")
    embedding_generator = EmbeddingGenerator(
        model_name=settings.embedding_model,
        cache_dir=Path(settings.embedding_cache_dir),
        batch_size=32,
        normalize=True,
    )

    # Initialize index manager
    logger.info("Initializing index manager...")
    index_manager = FAISSIndexManager(
        embedding_generator=embedding_generator,
        index_path=Path(settings.index_path),
    )

    # Build index
    logger.info("Building FAISS index...")
    index_manager.build_index(events)

    # Save index
    logger.info("Saving index...")
    metadata = {
        "mode": settings.openagenda_mode,
        "city": settings.city,
        "events_count": len(events),
    }
    index_manager.save_index(metadata=metadata)

    logger.info("Index build completed successfully!")
    logger.info(f"Index saved to {settings.index_path}")


if __name__ == "__main__":
    main()
