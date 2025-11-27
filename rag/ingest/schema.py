"""Event schema definition."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class Event(BaseModel):
    """Canonical event schema."""

    # Core identifiers
    event_id: str = Field(..., description="OpenAgenda event UID")
    source_agenda_uid: Optional[str] = Field(None, description="Source agenda UID")

    # Content
    title: str = Field(..., description="Event title")
    summary: Optional[str] = Field(None, description="Short description")
    long_description: Optional[str] = Field(None, description="Full description")

    # Classification
    categories: List[str] = Field(default_factory=list, description="Event categories")
    tags: List[str] = Field(default_factory=list, description="Event tags")
    category_norm: Optional[str] = Field(None, description="Normalized category")

    # Timing
    start_datetime: datetime = Field(..., description="Event start time (UTC)")
    end_datetime: Optional[datetime] = Field(None, description="Event end time (UTC)")
    all_day: bool = Field(default=False, description="All-day event flag")
    timings: Optional[List] = Field(None, description="Raw timing data")
    time_bucket: Optional[str] = Field(None, description="Time bucket classification")

    # Location
    venue_name: str = Field(..., description="Venue name")
    address: Optional[str] = Field(None, description="Street address")
    city: str = Field(default="Paris", description="City")
    postal_code: Optional[str] = Field(None, description="Postal code")
    country: str = Field(default="France", description="Country")
    lat: Optional[float] = Field(None, description="Latitude")
    lon: Optional[float] = Field(None, description="Longitude")
    arrondissement: Optional[str] = Field(None, description="Paris arrondissement")

    # Additional metadata
    organizer: Optional[str] = Field(None, description="Event organizer")
    price: Optional[str] = Field(None, description="Price information")
    is_free: bool = Field(default=False, description="Free event flag")
    price_bucket: Optional[str] = Field(None, description="Price bucket")

    # Links and media
    language: List[str] = Field(default_factory=lambda: ["fr"], description="Event languages")
    url: Optional[str] = Field(None, description="Event URL")
    image_url: Optional[str] = Field(None, description="Event image URL")

    # System metadata
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    @field_validator("categories", "tags", mode="before")
    @classmethod
    def ensure_list(cls, v):
        """Ensure field is a list."""
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return v

    @field_validator("start_datetime", "end_datetime", "updated_at", mode="before")
    @classmethod
    def parse_datetime(cls, v):
        """Parse datetime from various formats."""
        if v is None:
            return None
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            # Handle ISO format with various variations
            from dateutil import parser

            return parser.parse(v)
        return v

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return self.model_dump()

    def get_normalized_title(self) -> str:
        """Get normalized title for deduplication."""
        return self.title.lower().strip()

    def get_document_text(self) -> str:
        """Get text representation for embedding."""
        parts = [self.title]

        if self.summary:
            parts.append(self.summary)

        if self.long_description:
            # Truncate long description to ~800 chars
            desc = self.long_description[:800]
            if len(self.long_description) > 800:
                desc += "..."
            parts.append(desc)

        # Add location
        location_parts = [self.venue_name, self.city]
        if self.arrondissement:
            location_parts.append(self.arrondissement)
        parts.append(", ".join(filter(None, location_parts)))

        # Add categories and tags
        if self.categories:
            parts.append(f"Categories: {', '.join(self.categories)}")
        if self.tags:
            parts.append(f"Tags: {', '.join(self.tags[:5])}")  # Limit tags

        # Add metadata string for better recall
        metadata_parts = []
        if self.category_norm:
            metadata_parts.append(f"category: {self.category_norm}")
        if self.is_free:
            metadata_parts.append("price: free")
        elif self.price_bucket:
            metadata_parts.append(f"price: {self.price_bucket}")
        metadata_parts.append(f"city: {self.city}")

        if metadata_parts:
            parts.append("; ".join(metadata_parts))

        return "\n".join(parts)

    def get_metadata(self) -> dict:
        """Get metadata for FAISS storage."""
        return {
            "event_id": self.event_id,
            "title": self.title,
            "start_datetime": self.start_datetime.isoformat(),
            "end_datetime": self.end_datetime.isoformat() if self.end_datetime else None,
            "venue_name": self.venue_name,
            "city": self.city,
            "categories": self.categories,
            "category_norm": self.category_norm,
            "is_free": self.is_free,
            "price_bucket": self.price_bucket,
            "url": self.url,
            "lat": self.lat,
            "lon": self.lon,
            "arrondissement": self.arrondissement,
        }
