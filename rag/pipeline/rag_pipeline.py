"""Main RAG pipeline orchestrator."""

import time
from typing import Dict, Optional
import logging

from ..index.faiss_index import FAISSIndexManager
from .query_processor import QueryProcessor
from .retriever import EventRetriever
from .generator import AnswerGenerator

logger = logging.getLogger(__name__)


class RAGPipeline:
    """Main RAG pipeline for event queries."""

    def __init__(
        self,
        index_manager: FAISSIndexManager,
        query_processor: QueryProcessor,
        retriever: EventRetriever,
        generator: AnswerGenerator,
    ):
        """Initialize pipeline.

        Args:
            index_manager: FAISS index manager
            query_processor: Query processor
            retriever: Document retriever
            generator: Answer generator
        """
        self.index_manager = index_manager
        self.query_processor = query_processor
        self.retriever = retriever
        self.generator = generator

    def query(
        self,
        question: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        category: Optional[str] = None,
        price: Optional[str] = None,
        arrondissement: Optional[int] = None,
        language: Optional[str] = None,
    ) -> Dict:
        """Process query and generate answer.

        Args:
            question: User question
            from_date: Optional start date override (ISO format)
            to_date: Optional end date override (ISO format)
            category: Optional category override
            price: Optional price constraint override
            arrondissement: Optional arrondissement override
            language: Optional language override

        Returns:
            Dictionary with answer, events, sources, and metadata
        """
        start_time = time.time()

        # Process query to extract constraints
        processed = self.query_processor.process_query(question)

        # Apply overrides
        if from_date:
            from datetime import datetime

            processed["start_date"] = datetime.fromisoformat(from_date)
        if to_date:
            from datetime import datetime

            processed["end_date"] = datetime.fromisoformat(to_date)
        if category:
            processed["category"] = category
        if price:
            processed["price_constraint"] = price
        if arrondissement:
            processed["arrondissement"] = arrondissement
        if language:
            processed["language"] = language

        retrieval_start = time.time()

        # Retrieve relevant documents
        documents = self.retriever.retrieve(
            query=question,
            city="Paris",
            start_date=processed.get("start_date"),
            end_date=processed.get("end_date"),
            category=processed.get("category"),
            price_constraint=processed.get("price_constraint"),
            arrondissement=processed.get("arrondissement"),
        )

        retrieval_time = time.time() - retrieval_start
        logger.info(f"Retrieval took {retrieval_time:.3f}s, found {len(documents)} documents")

        generation_start = time.time()

        # Generate answer
        constraints = {
            "start_date": processed.get("start_date"),
            "end_date": processed.get("end_date"),
            "category": processed.get("category"),
            "price_constraint": processed.get("price_constraint"),
            "arrondissement": processed.get("arrondissement"),
        }

        result = self.generator.generate(
            query=question,
            documents=documents,
            language=processed.get("language", "fr"),
            constraints=constraints,
        )

        generation_time = time.time() - generation_start
        logger.info(f"Generation took {generation_time:.3f}s")

        total_time = time.time() - start_time

        # Add timing metadata
        result["latency_ms"] = int(total_time * 1000)
        result["retrieval_ms"] = int(retrieval_time * 1000)
        result["generation_ms"] = int(generation_time * 1000)

        return result
