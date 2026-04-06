"""RAGAS-style evaluation framework for FraudAI RAG pipeline.

Exports:
    RAGEvaluator       - Orchestrates evaluation runs against a benchmark dataset.
    BenchmarkQuestion   - Schema for a single benchmark question with ground truth.
    EvaluationResult    - Aggregated evaluation metrics and per-question breakdown.
    FRAUD_BENCHMARK     - 50-question benchmark dataset on Spanish financial regulation.
"""

from fraudai.evaluation.benchmark import FRAUD_BENCHMARK
from fraudai.evaluation.ragas_eval import (
    BenchmarkQuestion,
    EvaluationResult,
    RAGEvaluator,
)

__all__ = [
    "BenchmarkQuestion",
    "EvaluationResult",
    "FRAUD_BENCHMARK",
    "RAGEvaluator",
]
