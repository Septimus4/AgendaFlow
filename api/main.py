"""FastAPI application for AgendaFlow."""

import time
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Header, Depends, status
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from .config import Settings, get_settings
from .models import (
    AskRequest,
    AskResponse,
    RebuildRequest,
    RebuildResponse,
    HealthResponse,
    Event as EventModel,
)

from rag.index.embeddings import EmbeddingGenerator
from rag.index.faiss_index import FAISSIndexManager
from rag.pipeline.query_processor import QueryProcessor
from rag.pipeline.retriever import EventRetriever
from rag.pipeline.generator import AnswerGenerator
from rag.pipeline.rag_pipeline import RAGPipeline
from rag.ingest.loader import EventLoader

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Prometheus metrics
request_counter = Counter("agendaflow_requests_total", "Total requests", ["endpoint", "status"])
request_latency = Histogram("agendaflow_request_duration_seconds", "Request latency", ["endpoint"])
retrieval_latency = Histogram("agendaflow_retrieval_duration_seconds", "Retrieval latency")
generation_latency = Histogram("agendaflow_generation_duration_seconds", "Generation latency")

# Application
app = FastAPI(
    title="AgendaFlow",
    description="RAG service for Paris event queries",
    version="0.1.0",
)


# Global state
class AppState:
    """Application state."""

    def __init__(self):
        self.settings: Optional[Settings] = None
        self.pipeline: Optional[RAGPipeline] = None
        self.index_manager: Optional[FAISSIndexManager] = None
        self.embedding_generator: Optional[EmbeddingGenerator] = None


state = AppState()


def verify_rebuild_token(authorization: Optional[str] = Header(None)):
    """Verify rebuild token."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization header missing"
        )

    token = authorization.replace("Bearer ", "")
    if token != state.settings.rebuild_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("Starting AgendaFlow API...")

    # Load settings
    state.settings = get_settings()

    # Set HF_TOKEN if provided
    if state.settings.hf_token:
        import os

        os.environ["HF_TOKEN"] = state.settings.hf_token

    # Initialize embedding generator
    logger.info("Initializing embedding generator...")
    state.embedding_generator = EmbeddingGenerator(
        model_name=state.settings.embedding_model,
        cache_dir=Path(state.settings.embedding_cache_dir),
        batch_size=32,
        normalize=True,
        api_key=state.settings.mistral_api_key,
    )

    # Initialize index manager
    logger.info("Initializing index manager...")
    state.index_manager = FAISSIndexManager(
        embedding_generator=state.embedding_generator,
        index_path=Path(state.settings.index_path),
    )

    # Try to load existing index
    index_loaded = state.index_manager.load_index()

    if not index_loaded:
        logger.warning("No index found. Index must be built before serving queries.")
        logger.warning("Use POST /rebuild to build the index.")
    else:
        # Initialize pipeline components
        query_processor = QueryProcessor(
            default_language="fr",
            timezone="Europe/Paris",
        )

        retriever = EventRetriever(
            index_manager=state.index_manager,
            k_initial=state.settings.k_initial,
            k_final=state.settings.k_final,
            mmr_diversity=state.settings.mmr_diversity,
        )

        generator = AnswerGenerator(
            api_key=state.settings.mistral_api_key,
            model_name=state.settings.rag_model_name,
            temperature=0.2,
            max_tokens=1000,
            timeout=state.settings.generation_timeout,
        )

        state.pipeline = RAGPipeline(
            index_manager=state.index_manager,
            query_processor=query_processor,
            retriever=retriever,
            generator=generator,
        )

        logger.info("Pipeline initialized successfully")

    logger.info("AgendaFlow API started")


@app.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest) -> AskResponse:
    """Answer event-related questions.

    Args:
        request: Ask request

    Returns:
        Answer with events and metadata
    """
    trace_id = str(uuid.uuid4())
    start_time = time.time()

    try:
        if state.pipeline is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Index not loaded. Please build the index first using POST /rebuild.",
            )

        # Validate request
        if not request.question or len(request.question.strip()) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Question cannot be empty"
            )

        # Process query
        result = state.pipeline.query(
            question=request.question,
            from_date=request.from_date,
            to_date=request.to_date,
            category=request.category,
            price=request.price,
            arrondissement=request.arrondissement,
            language=request.language,
        )

        # Convert events to response model
        events = [EventModel(**event) for event in result.get("events", [])]

        # Record metrics
        request_counter.labels(endpoint="ask", status="success").inc()
        request_latency.labels(endpoint="ask").observe(time.time() - start_time)
        if result.get("retrieval_ms"):
            retrieval_latency.observe(result["retrieval_ms"] / 1000.0)
        if result.get("generation_ms"):
            generation_latency.observe(result["generation_ms"] / 1000.0)

        return AskResponse(
            answer=result["answer"],
            events=events,
            sources=result.get("sources", []),
            filters_applied=result.get("filters_applied", {}),
            latency_ms=result.get("latency_ms", 0),
            retrieval_ms=result.get("retrieval_ms"),
            generation_ms=result.get("generation_ms"),
            trace_id=trace_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        request_counter.labels(endpoint="ask", status="error").inc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@app.post("/rebuild", response_model=RebuildResponse, dependencies=[Depends(verify_rebuild_token)])
async def rebuild(request: RebuildRequest) -> RebuildResponse:
    """Rebuild the event index.

    Args:
        request: Rebuild request

    Returns:
        Rebuild statistics
    """
    start_time = time.time()

    try:
        logger.info(f"Starting index rebuild (mode={request.mode})")

        # Initialize loader
        loader = EventLoader(
            api_key=state.settings.openagenda_api_key,
            data_dir=Path("data"),
            city=state.settings.city,
        )

        # Fetch events
        events = loader.fetch_events(
            mode=state.settings.openagenda_mode,
            max_agendas=50,
        )

        if not events:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No events fetched"
            )

        # Save to Parquet
        loader.save_events_parquet(events)

        # Build index
        logger.info("Building index...")
        state.index_manager.build_index(events)

        # Save index
        metadata = {
            "mode": request.mode,
            "city": state.settings.city,
            "events_count": len(events),
        }
        state.index_manager.save_index(metadata=metadata)

        # Reinitialize pipeline
        query_processor = QueryProcessor(
            default_language="fr",
            timezone="Europe/Paris",
        )

        retriever = EventRetriever(
            index_manager=state.index_manager,
            k_initial=state.settings.k_initial,
            k_final=state.settings.k_final,
            mmr_diversity=state.settings.mmr_diversity,
        )

        generator = AnswerGenerator(
            api_key=state.settings.mistral_api_key,
            model_name=state.settings.rag_model_name,
            temperature=0.2,
            max_tokens=1000,
            timeout=state.settings.generation_timeout,
        )

        state.pipeline = RAGPipeline(
            index_manager=state.index_manager,
            query_processor=query_processor,
            retriever=retriever,
            generator=generator,
        )

        duration = time.time() - start_time

        logger.info(f"Index rebuild completed in {duration:.2f}s")

        return RebuildResponse(
            status="success",
            events_fetched=len(events),
            events_indexed=len(events),
            duration_seconds=duration,
            manifest_hash=None,
        )

    except Exception as e:
        logger.error(f"Error rebuilding index: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Rebuild failed: {str(e)}"
        )


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint.

    Returns:
        Service health status
    """
    index_loaded = state.index_manager is not None and state.index_manager.index is not None
    index_size = state.index_manager.index.ntotal if index_loaded else None

    return HealthResponse(
        status="healthy" if index_loaded else "degraded",
        index_loaded=index_loaded,
        index_size=index_size,
        timestamp=datetime.utcnow().isoformat(),
    )


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint.

    Returns:
        Prometheus metrics
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "AgendaFlow",
        "version": "0.1.0",
        "description": "RAG service for Paris event queries",
        "endpoints": {
            "POST /ask": "Ask event-related questions",
            "POST /rebuild": "Rebuild event index (requires auth)",
            "GET /health": "Health check",
            "GET /metrics": "Prometheus metrics",
        },
    }


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        workers=settings.api_workers,
        log_level="info",
    )
