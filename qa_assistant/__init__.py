"""Citation-aware retrieval and grounded answering for QA documentation."""

from qa_assistant.assistant import QAAssistant
from qa_assistant.benchmarking import (
    BenchmarkReport,
    benchmark_report_data,
    write_benchmark_report,
)
from qa_assistant.evaluation import (
    evaluate_case,
    grounding_evaluation_cases,
    summarize_results,
)
from qa_assistant.openai_generator import OpenAIResponsesGenerator
from qa_assistant.reporting import (
    EvaluationReport,
    evaluation_report_data,
    write_evaluation_report,
)
from qa_assistant.service import QAKnowledgeBase

__all__ = [
    "OpenAIResponsesGenerator",
    "QAAssistant",
    "QAKnowledgeBase",
    "BenchmarkReport",
    "EvaluationReport",
    "evaluate_case",
    "benchmark_report_data",
    "evaluation_report_data",
    "grounding_evaluation_cases",
    "summarize_results",
    "write_evaluation_report",
    "write_benchmark_report",
]
