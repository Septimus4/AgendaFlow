#!/usr/bin/env python3
"""Generate Q&A dataset from events."""

import json
import logging
from pathlib import Path
import pandas as pd
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_dataset():
    """Generate Q&A dataset."""
    data_dir = Path("data/clean")
    parquet_files = list(data_dir.glob("*.parquet"))

    if not parquet_files:
        logger.error("No parquet files found in data/clean")
        return

    # Load latest file
    latest_file = sorted(parquet_files)[-1]
    logger.info(f"Loading events from {latest_file}")
    df = pd.read_parquet(latest_file)

    qa_pairs = []

    # Filter for valid events
    valid_events = df[
        df["title"].notna() & df["venue_name"].notna() & df["start_datetime"].notna()
    ].sample(n=min(10, len(df)), random_state=42)

    for _, event in valid_events.iterrows():
        title = event["title"]
        venue = event["venue_name"]
        start_dt = event["start_datetime"]
        try:
            if isinstance(start_dt, str):
                dt = datetime.fromisoformat(start_dt)
            else:
                # Assume it's a pandas Timestamp or datetime object
                dt = start_dt

            date_str = dt.strftime("%Y-%m-%d")
            time_str = dt.strftime("%H:%M")
        except (ValueError, TypeError, AttributeError):
            date_str = str(start_dt)
            time_str = ""

        # Question 1: Location
        qa_pairs.append(
            {
                "question": f"Where is the event '{title}' taking place?",
                "ground_truth": f"The event '{title}' is taking place at {venue}.",
                "context": f"Event: {title}, Venue: {venue}",
            }
        )

        # Question 2: Date
        qa_pairs.append(
            {
                "question": f"When is '{title}' scheduled?",
                "ground_truth": f"'{title}' is scheduled for {date_str} at {time_str}.",
                "context": f"Event: {title}, Date: {start_dt}",
            }
        )

        # Question 3: Price (if available)
        if "is_free" in event:
            price_status = "free" if event["is_free"] else "paid"
            qa_pairs.append(
                {
                    "question": f"Is the event '{title}' free?",
                    "ground_truth": f"The event is {price_status}.",
                    "context": f"Event: {title}, Free: {event['is_free']}",
                }
            )

    # Add some general questions
    qa_pairs.append(
        {
            "question": "What events are happening in Paris?",
            "ground_truth": "There are various events happening in Paris including concerts, exhibitions, and theater.",
            "context": "Paris events",
        }
    )

    # Save to JSONL
    output_path = Path("evaluation/qa.jsonl")
    output_path.parent.mkdir(exist_ok=True)

    with open(output_path, "w") as f:
        for pair in qa_pairs:
            f.write(json.dumps(pair) + "\n")

    logger.info(f"Generated {len(qa_pairs)} Q&A pairs in {output_path}")


if __name__ == "__main__":
    generate_dataset()
