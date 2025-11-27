# RAG System Evaluation

This directory contains the evaluation framework for the AgendaFlow RAG system. It includes the test dataset, the evaluation script, and the results of the latest run.

## Metrics Explanation

The system performance is measured using three key metrics:

### 1. Semantic Similarity
**Definition:** Measures how closely the meaning of the generated answer matches the ground truth answer.
**Calculation:**
1.  Generate vector embeddings for both the `generated_answer` and the `ground_truth` using the `intfloat/multilingual-e5-base` model.
2.  Compute the **Cosine Similarity** between the two vectors.
3.  The final metric is the **mean** of these similarity scores across all test questions.
**Range:** 0.0 to 1.0 (Higher is better)

### 2. Response Coverage Rate
**Definition:** The percentage of user queries for which the system successfully retrieved and presented relevant event information.
**Calculation:**
A query is considered "covered" if:
1.  The retrieval step returned at least one event (`r.get('events')` is not empty).
2.  The generated answer does **not** contain the fallback phrase "couldn't find any events".
**Formula:** `Coverage Rate = (Number of Covered Queries) / (Total Number of Queries)`
**Range:** 0.0 to 1.0 (Higher is better)

### 3. Satisfaction Score
**Definition:** A composite heuristic score designed to estimate overall user satisfaction by balancing accuracy, utility, and speed.
**Calculation:**
For each query, a score is calculated using the following weighted formula:
$$ \text{Score} = (0.5 \times \text{Similarity}) + (0.3 \times \text{HasEvents}) + (0.2 \times \text{LatencyFactor}) $$

Where:
*   **Similarity:** The Semantic Similarity score for that query.
*   **HasEvents:** 1.0 if events were retrieved, 0.0 otherwise.
*   **LatencyFactor:** A penalty for slow responses, calculated as $\max(0, 1 - (\text{latency\_ms} / 5000))$. This term becomes 0 if the request takes longer than 5 seconds.

The final metric is the **mean** of these scores.
**Range:** 0.0 to 1.0 (Higher is better)

## Files

*   `evaluate.py`: The main script that runs the evaluation pipeline.
*   `qa.jsonl`: The test dataset containing pairs of questions and ground truth answers.
*   `results.json`: The output file containing the calculated metrics and detailed results for each query.

## Running the Evaluation

To run the evaluation and generate new results:

```bash
python3 evaluation/evaluate.py
```
