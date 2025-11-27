"""API request and response models."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    """Request model for /ask endpoint."""

    question: str = Field(..., description="User question about events", examples=["Que faire ce week-end ?", "Concerts de jazz gratuits"])
    from_date: Optional[str] = Field(None, description="Start date filter (ISO format)", examples=["2025-12-01T00:00:00"])
    to_date: Optional[str] = Field(None, description="End date filter (ISO format)", examples=["2025-12-31T23:59:59"])
    category: Optional[str] = Field(None, description="Category filter", examples=["concert", "exposition"])
    price: Optional[str] = Field(None, description="Price constraint (free, cheap)", examples=["free"])
    arrondissement: Optional[int] = Field(
        None, ge=1, le=20, description="Paris arrondissement (1-20)", examples=[11]
    )
    language: Optional[str] = Field(None, description="Response language (fr, en)", examples=["fr"])


class Event(BaseModel):
    """Event information in response."""

    title: Optional[str] = Field(None, examples=["Jazz à la Villette"])
    start_datetime: Optional[str] = Field(None, examples=["2025-09-04T20:00:00"])
    venue_name: Optional[str] = Field(None, examples=["Philharmonie de Paris"])
    city: Optional[str] = Field(None, examples=["Paris"])
    arrondissement: Optional[str] = Field(None, examples=["19e"])
    price: Optional[str] = Field(None, examples=["30€"])
    url: Optional[str] = Field(None, examples=["https://openagenda.com/event/123"])
    categories: List[str] = Field(default_factory=list, examples=[["Concert", "Jazz"]])


class AskResponse(BaseModel):
    """Response model for /ask endpoint."""

    answer: str = Field(..., description="Generated answer text")
    events: List[Event] = Field(default_factory=list, description="List of relevant events")
    sources: List[str] = Field(default_factory=list, description="Source URLs")
    filters_applied: Dict = Field(default_factory=dict, description="Applied filters")
    latency_ms: int = Field(..., description="Total latency in milliseconds")
    retrieval_ms: Optional[int] = Field(None, description="Retrieval latency in milliseconds")
    generation_ms: Optional[int] = Field(None, description="Generation latency in milliseconds")
    trace_id: Optional[str] = Field(None, description="Trace ID for debugging")


class RebuildRequest(BaseModel):
    """Request model for /rebuild endpoint."""

    mode: str = Field(default="full", description="Rebuild mode: full or incremental")
    since: Optional[str] = Field(None, description="ISO timestamp for incremental update")


class RebuildResponse(BaseModel):
    """Response model for /rebuild endpoint."""

    status: str = Field(..., description="Rebuild status")
    events_fetched: int = Field(..., description="Number of events fetched")
    events_indexed: int = Field(..., description="Number of events indexed")
    duration_seconds: float = Field(..., description="Rebuild duration in seconds")
    manifest_hash: Optional[str] = Field(None, description="Index manifest hash")


class HealthResponse(BaseModel):
    """Response model for /health endpoint."""

    status: str = Field(..., description="Service status")
    index_loaded: bool = Field(..., description="Whether index is loaded")
    index_size: Optional[int] = Field(None, description="Number of documents in index")
    timestamp: str = Field(..., description="Current timestamp")
