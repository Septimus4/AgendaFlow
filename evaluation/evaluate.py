#!/usr/bin/env python3
"""Evaluation script using custom metrics and RAG pipeline."""

import sys
import json
import logging
from pathlib import Path
from typing import List, Dict
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.config import get_settings
from rag.pipeline.rag_pipeline import RAGPipeline
from rag.index.faiss_index import FAISSIndexManager
from rag.index.embeddings import EmbeddingGenerator
from rag.pipeline.query_processor import QueryProcessor
from rag.pipeline.retriever import EventRetriever
from rag.pipeline.generator import AnswerGenerator

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_qa_dataset(path: str = "evaluation/qa.jsonl"):
    """Load Q&A dataset.

    Args:
        path: Path to JSONL file

    Returns:
        List of Q&A pairs
    """
    qa_pairs = []
    with open(path, "r") as f:
        for line in f:
            qa_pairs.append(json.loads(line))
    return qa_pairs


def initialize_pipeline():
    """Initialize the RAG pipeline."""
    settings = get_settings()

    # Initialize embedding generator
    embedding_generator = EmbeddingGenerator(
        model_name=settings.embedding_model,
        cache_dir=Path(settings.embedding_cache_dir),
        api_key=settings.mistral_api_key,
    )

    # Initialize index manager
    index_manager = FAISSIndexManager(
        embedding_generator=embedding_generator,
        index_path=Path(settings.index_path),
    )

    # Load index
    if not index_manager.load_index():
        logger.error("Could not load index. Please run scripts/build_index.py first.")
        sys.exit(1)

    # Initialize components
    query_processor = QueryProcessor()
    retriever = EventRetriever(
        index_manager=index_manager,
        k_initial=settings.k_initial,
        k_final=settings.k_final,
        mmr_diversity=settings.mmr_diversity,
    )
    generator = AnswerGenerator(
        api_key=settings.mistral_api_key,
        model_name=settings.rag_model_name,
    )

    return RAGPipeline(
        index_manager=index_manager,
        query_processor=query_processor,
        retriever=retriever,
        generator=generator,
    )


def compute_metrics(
    results: List[Dict], ground_truths: List[str], embedding_generator: EmbeddingGenerator
):
    """Compute evaluation metrics.

    Args:
        results: List of pipeline results
        ground_truths: List of ground truth answers
        embedding_generator: Initialized embedding generator
    """
    logger.info("Computing metrics...")

    generated_answers = [r["answer"] for r in results]

    # 1. Semantic Similarity
    # Use the existing embedding generator
    gen_embeddings = embedding_generator.embed_texts(generated_answers)
    gt_embeddings = embedding_generator.embed_texts(ground_truths)

    similarities = []
    for i in range(len(generated_answers)):
        sim = cosine_similarity([gen_embeddings[i]], [gt_embeddings[i]])[0][0]
        similarities.append(float(sim))

    avg_similarity = np.mean(similarities)

    # 2. Response Coverage Rate
    # Check if events were found and answer is not the "not found" template
    coverage_count = 0
    for r in results:
        if r.get("events") and "couldn't find any events" not in r["answer"]:
            coverage_count += 1
    coverage_rate = coverage_count / len(results)

    # 3. Satisfaction Score (Subjective/Heuristic)
    # Heuristic: Combination of similarity, coverage, and latency
    satisfaction_scores = []
    for i, r in enumerate(results):
        sim = similarities[i]
        has_events = 1.0 if r.get("events") else 0.0
        # Penalize very long latency (>5s)
        latency_factor = max(0, 1 - (r.get("latency_ms", 0) / 5000))

        score = (sim * 0.5) + (has_events * 0.3) + (latency_factor * 0.2)
        satisfaction_scores.append(score)

    avg_satisfaction = np.mean(satisfaction_scores)

    return {
        "semantic_similarity": avg_similarity,
        "response_coverage_rate": coverage_rate,
        "satisfaction_score": avg_satisfaction,
        "details": {"similarities": similarities, "satisfaction_scores": satisfaction_scores},
    }


def evaluate_rag_system():
    """Evaluate RAG system."""
    logger.info("Starting evaluation...")

    # Load test set
    qa_pairs = load_qa_dataset()
    logger.info(f"Loaded {len(qa_pairs)} Q&A pairs")

    # Initialize pipeline
    pipeline = initialize_pipeline()

    results = []
    ground_truths = []

    # Run queries
    for i, item in enumerate(qa_pairs):
        logger.info(f"Processing question {i + 1}/{len(qa_pairs)}: {item['question']}")
        try:
            result = pipeline.query(item["question"])
            results.append(result)
            ground_truths.append(item["ground_truth"])
        except Exception as e:
            logger.error(f"Error processing question: {e}")
            results.append({"answer": "Error", "events": []})
            ground_truths.append(item["ground_truth"])

    # Compute metrics
    metrics = compute_metrics(results, ground_truths, pipeline.index_manager.embedding_generator)

    evaluation_results = {
        "total_questions": len(qa_pairs),
        "metrics": {
            "semantic_similarity": metrics["semantic_similarity"],
            "response_coverage_rate": metrics["response_coverage_rate"],
            "satisfaction_score": metrics["satisfaction_score"],
        },
        "results": [
            {
                "question": qa["question"],
                "ground_truth": qa["ground_truth"],
                "generated_answer": res["answer"],
                "similarity": sim,
                "satisfaction": sat,
            }
            for qa, res, sim, sat in zip(
                qa_pairs,
                results,
                metrics["details"]["similarities"],
                metrics["details"]["satisfaction_scores"],
            )
        ],
    }

    logger.info("Evaluation completed")
    logger.info(f"Metrics: {json.dumps(evaluation_results['metrics'], indent=2)}")

    # Save results
    output_path = "evaluation/results.json"
    with open(output_path, "w") as f:
        json.dump(evaluation_results, f, indent=2)
    logger.info(f"Results saved to {output_path}")

    return evaluation_results


if __name__ == "__main__":
    evaluate_rag_system()
