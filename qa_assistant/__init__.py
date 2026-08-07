"""Citation-aware retrieval and grounded answering for QA documentation."""

from qa_assistant.assistant import QAAssistant
from qa_assistant.evaluation import (
    evaluate_case,
    grounding_evaluation_cases,
    summarize_results,
)
from qa_assistant.openai_generator import OpenAIResponsesGenerator
from qa_assistant.service import QAKnowledgeBase

__all__ = [
    "OpenAIResponsesGenerator",
    "QAAssistant",
    "QAKnowledgeBase",
    "evaluate_case",
    "grounding_evaluation_cases",
    "summarize_results",
]
