"""Human-labelled claim faithfulness and candidate-judge validation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from typing import Protocol

_TOKEN = re.compile(r"[a-z0-9]+")
_STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "at",
    "be",
    "by",
    "for",
    "in",
    "is",
    "of",
    "on",
    "the",
    "to",
}
_NORMALIZED_TERMS = {
    "checks": "check",
    "days": "day",
    "excluded": "exclude",
    "included": "include",
    "merged": "merge",
    "reports": "report",
    "retained": "retain",
    "runs": "run",
    "screenshots": "screenshot",
    "tests": "test",
}
_OPPOSITES = (
    frozenset(("before", "after")),
    frozenset(("include", "exclude")),
    frozenset(("enabled", "disabled")),
)


class FaithfulnessLabel(StrEnum):
    """Human or judge classification for one answer claim."""

    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True, slots=True)
class FaithfulnessExample:
    """One evidence-and-claim pair with a human-authored ground-truth label."""

    identifier: str
    evidence: str
    claim: str
    human_label: FaithfulnessLabel
    explanation: str

    def __post_init__(self) -> None:
        for name, value in (
            ("identifier", self.identifier),
            ("evidence", self.evidence),
            ("claim", self.claim),
            ("explanation", self.explanation),
        ):
            if not value.strip():
                raise ValueError(f"faithfulness {name} cannot be empty")
        if not isinstance(self.human_label, FaithfulnessLabel):
            raise ValueError("faithfulness human_label must be a FaithfulnessLabel")


class FaithfulnessJudge(Protocol):
    """Candidate classifier that must be validated against human labels."""

    @property
    def name(self) -> str:
        """Stable candidate-judge identity."""

    def classify(self, example: FaithfulnessExample) -> FaithfulnessLabel:
        """Classify the claim using only its evidence."""


@dataclass(frozen=True, slots=True)
class JudgeValidationPolicy:
    """Minimum evidence required before a candidate judge is called validated."""

    minimum_accuracy: float = 0.90
    minimum_unfaithful_recall: float = 0.95
    maximum_false_negatives: int = 0

    def __post_init__(self) -> None:
        for name, value in (
            ("minimum_accuracy", self.minimum_accuracy),
            ("minimum_unfaithful_recall", self.minimum_unfaithful_recall),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not isfinite(float(value))
                or not 0 <= value <= 1
            ):
                raise ValueError(f"{name} must be between 0 and 1")
        if (
            isinstance(self.maximum_false_negatives, bool)
            or not isinstance(self.maximum_false_negatives, int)
            or self.maximum_false_negatives < 0
        ):
            raise ValueError("maximum_false_negatives must be a non-negative integer")


@dataclass(frozen=True, slots=True)
class FaithfulnessDecision:
    example: FaithfulnessExample
    predicted_label: FaithfulnessLabel

    @property
    def correct(self) -> bool:
        return self.predicted_label is self.example.human_label


@dataclass(frozen=True, slots=True)
class FaithfulnessMetrics:
    example_count: int
    human_supported_count: int
    human_faithfulness_rate: float
    exact_match_count: int
    accuracy: float
    unfaithful_precision: float
    unfaithful_recall: float
    unfaithful_f1: float
    false_positive_count: int
    false_negative_count: int
    confusion_matrix: dict[str, dict[str, int]]


@dataclass(frozen=True, slots=True)
class FaithfulnessValidation:
    judge_name: str
    dataset_name: str
    decisions: tuple[FaithfulnessDecision, ...]
    metrics: FaithfulnessMetrics
    policy: JudgeValidationPolicy

    @property
    def validated(self) -> bool:
        return (
            self.metrics.accuracy >= self.policy.minimum_accuracy
            and self.metrics.unfaithful_recall >= self.policy.minimum_unfaithful_recall
            and self.metrics.false_negative_count <= self.policy.maximum_false_negatives
        )


class DeterministicFaithfulnessJudge:
    """Transparent lexical baseline whose limits are measured, not hidden."""

    name = "deterministic-claim-baseline-v1"

    @staticmethod
    def _tokens(value: str) -> tuple[str, ...]:
        return tuple(
            _NORMALIZED_TERMS.get(token, token)
            for token in _TOKEN.findall(value.casefold())
            if token not in _STOP_WORDS
        )

    def classify(self, example: FaithfulnessExample) -> FaithfulnessLabel:
        evidence = set(self._tokens(example.evidence))
        claim = set(self._tokens(example.claim))
        shared = evidence & claim
        claim_numbers = {token for token in claim if token.isdigit()}
        evidence_numbers = {token for token in evidence if token.isdigit()}
        if claim_numbers and evidence_numbers and not claim_numbers <= evidence_numbers:
            return FaithfulnessLabel.CONTRADICTED
        if any(
            pair <= evidence | claim and len(pair & evidence) == 1
            for pair in _OPPOSITES
        ):
            return FaithfulnessLabel.CONTRADICTED
        negation_mismatch = ("not" in claim) != ("not" in evidence)
        non_negated_claim = claim - {"not"}
        overlap = len(shared) / len(non_negated_claim) if non_negated_claim else 0
        if negation_mismatch and overlap >= 0.60:
            return FaithfulnessLabel.CONTRADICTED
        if claim and len(shared) / len(claim) >= 0.75:
            return FaithfulnessLabel.SUPPORTED
        return FaithfulnessLabel.UNSUPPORTED


def faithfulness_examples() -> tuple[FaithfulnessExample, ...]:
    """Return the balanced, human-labelled claim validation dataset."""
    return (
        FaithfulnessExample(
            "supported-merge-gates",
            "Ruff linting and branch-aware coverage run before a pull request "
            "is merged.",
            "Ruff and branch-aware coverage run before merge.",
            FaithfulnessLabel.SUPPORTED,
            "The evidence directly states both checks and their timing.",
        ),
        FaithfulnessExample(
            "contradicted-merge-timing",
            "Ruff and coverage run before merge.",
            "Ruff and coverage run after merge.",
            FaithfulnessLabel.CONTRADICTED,
            "The claim reverses before into after.",
        ),
        FaithfulnessExample(
            "unsupported-type-checker",
            "Ruff and coverage run before merge.",
            "Mypy validates type safety before merge.",
            FaithfulnessLabel.UNSUPPORTED,
            "The evidence never mentions Mypy or type checking.",
        ),
        FaithfulnessExample(
            "supported-retention",
            "Current policy retains compliance reports for 30 days.",
            "Compliance reports are retained for 30 days.",
            FaithfulnessLabel.SUPPORTED,
            "The duration and retained artifact match the evidence.",
        ),
        FaithfulnessExample(
            "contradicted-retention",
            "Current policy retains compliance reports for 30 days.",
            "Compliance reports are retained for 14 days.",
            FaithfulnessLabel.CONTRADICTED,
            "The claimed duration conflicts with the documented duration.",
        ),
        FaithfulnessExample(
            "unsupported-encryption",
            "Compliance reports are retained for 30 days.",
            "Compliance reports are encrypted with customer-managed keys.",
            FaithfulnessLabel.UNSUPPORTED,
            "Retention evidence says nothing about encryption.",
        ),
        FaithfulnessExample(
            "supported-browser-smoke",
            "Playwright runs Chromium checkout smoke tests before release.",
            "Playwright runs Chromium checkout smoke tests before release.",
            FaithfulnessLabel.SUPPORTED,
            "The claim is directly present in the evidence.",
        ),
        FaithfulnessExample(
            "contradicted-browser-negation",
            "Playwright runs Chromium checkout smoke tests before release.",
            "Playwright does not run Chromium checkout smoke tests before release.",
            FaithfulnessLabel.CONTRADICTED,
            "The claim adds a negation that reverses the evidence.",
        ),
        FaithfulnessExample(
            "unsupported-browser-stack",
            "Playwright runs Chromium checkout smoke tests before release.",
            "Selenium runs Firefox accessibility audits before release.",
            FaithfulnessLabel.UNSUPPORTED,
            "The tool, browser, and audit type are absent from the evidence.",
        ),
        FaithfulnessExample(
            "supported-screenshot-path",
            "Browser failure screenshots are stored under reports/screenshots.",
            "Failure screenshots are stored under reports/screenshots.",
            FaithfulnessLabel.SUPPORTED,
            "The storage path is directly supported.",
        ),
        FaithfulnessExample(
            "unsupported-log-path",
            "Failure screenshots are stored under reports/screenshots.",
            "Failure videos are uploaded to the artifacts/logs directory.",
            FaithfulnessLabel.UNSUPPORTED,
            "Neither videos nor the claimed directory appear in the evidence.",
        ),
        FaithfulnessExample(
            "unsupported-review-owner",
            "Failure screenshots are stored under reports/screenshots.",
            "The QA lead must approve every failure screenshot.",
            FaithfulnessLabel.UNSUPPORTED,
            "A storage statement does not establish review ownership.",
        ),
        FaithfulnessExample(
            "supported-external-boundary",
            "External model checks are excluded from merge-blocking deterministic CI.",
            "External model checks are excluded from deterministic merge-blocking CI.",
            FaithfulnessLabel.SUPPORTED,
            "The claim preserves the documented CI boundary.",
        ),
        FaithfulnessExample(
            "contradicted-external-boundary",
            "External model checks are excluded from merge-blocking deterministic CI.",
            "External model checks are included in merge-blocking deterministic CI.",
            FaithfulnessLabel.CONTRADICTED,
            "The claim reverses excluded into included.",
        ),
        FaithfulnessExample(
            "contradicted-current-policy",
            "The current policy is enabled and retains reports for 30 days.",
            "The current policy is disabled and retains reports for 30 days.",
            FaithfulnessLabel.CONTRADICTED,
            "The claim reverses enabled into disabled.",
        ),
    )


def _safe_ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def validate_faithfulness_judge(
    judge: FaithfulnessJudge,
    examples: tuple[FaithfulnessExample, ...] | None = None,
    *,
    policy: JudgeValidationPolicy | None = None,
    dataset_name: str = "stage4-human-claims-v1",
) -> FaithfulnessValidation:
    """Compare a candidate judge with human labels and apply safety thresholds."""
    selected = faithfulness_examples() if examples is None else examples
    if not selected:
        raise ValueError("faithfulness validation requires at least one example")
    identifiers = tuple(example.identifier for example in selected)
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("faithfulness example identifiers must be unique")
    if not judge.name.strip():
        raise ValueError("faithfulness judge name cannot be empty")
    if not dataset_name.strip():
        raise ValueError("faithfulness dataset_name cannot be empty")

    decisions = tuple(
        FaithfulnessDecision(example, judge.classify(example)) for example in selected
    )
    if any(
        not isinstance(decision.predicted_label, FaithfulnessLabel)
        for decision in decisions
    ):
        raise ValueError("faithfulness judge must return a FaithfulnessLabel")

    labels = tuple(FaithfulnessLabel)
    confusion = {
        human.value: {
            predicted.value: sum(
                decision.example.human_label is human
                and decision.predicted_label is predicted
                for decision in decisions
            )
            for predicted in labels
        }
        for human in labels
    }
    human_supported = sum(
        decision.example.human_label is FaithfulnessLabel.SUPPORTED
        for decision in decisions
    )
    exact = sum(decision.correct for decision in decisions)
    true_positive = sum(
        decision.example.human_label is not FaithfulnessLabel.SUPPORTED
        and decision.predicted_label is not FaithfulnessLabel.SUPPORTED
        for decision in decisions
    )
    false_positive = sum(
        decision.example.human_label is FaithfulnessLabel.SUPPORTED
        and decision.predicted_label is not FaithfulnessLabel.SUPPORTED
        for decision in decisions
    )
    false_negative = sum(
        decision.example.human_label is not FaithfulnessLabel.SUPPORTED
        and decision.predicted_label is FaithfulnessLabel.SUPPORTED
        for decision in decisions
    )
    precision = _safe_ratio(true_positive, true_positive + false_positive)
    recall = _safe_ratio(true_positive, true_positive + false_negative)
    f1 = _safe_ratio(2 * precision * recall, precision + recall)
    metrics = FaithfulnessMetrics(
        example_count=len(decisions),
        human_supported_count=human_supported,
        human_faithfulness_rate=human_supported / len(decisions),
        exact_match_count=exact,
        accuracy=exact / len(decisions),
        unfaithful_precision=precision,
        unfaithful_recall=recall,
        unfaithful_f1=f1,
        false_positive_count=false_positive,
        false_negative_count=false_negative,
        confusion_matrix=confusion,
    )
    return FaithfulnessValidation(
        judge_name=judge.name,
        dataset_name=dataset_name,
        decisions=decisions,
        metrics=metrics,
        policy=policy or JudgeValidationPolicy(),
    )
