"""
Match result domain model.

Represents the result of matching a candidate to a job posting with
explainable scoring and decision making.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MatchResult:
    """
    Frozen match result with scoring and explainability.

    Represents how well a candidate matches a job posting with
    dimension-level scores, overall decision, and human-readable reasons.
    """

    candidate_id: str
    job_fingerprint: str
    overall_score: float
    decision: str
    dimension_scores: dict[str, float]
    reasons: list[str]
    matched_keywords: list[str]
    missing_keywords: list[str]
    meta: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate match result constraints."""
        # Validate overall_score bounds
        if not (0 <= self.overall_score <= 100):
            raise ValueError(
                f"overall_score must be 0-100, got {self.overall_score}"
            )

        # Validate decision
        valid_decisions = {"strong_fit", "possible_fit", "weak_fit", "reject"}
        if self.decision not in valid_decisions:
            raise ValueError(
                f"decision must be one of {valid_decisions}, got {self.decision}"
            )

        # Validate dimension scores bounds
        for dim, score in self.dimension_scores.items():
            if not (0 <= score <= 100):
                raise ValueError(
                    f"dimension score '{dim}' must be 0-100, got {score}"
                )

        # Validate decision thresholds match score
        if self.decision == "strong_fit" and self.overall_score < 80:
            raise ValueError(
                f"decision 'strong_fit' requires score >= 80, got {self.overall_score}"
            )
        if self.decision == "possible_fit" and not (65 <= self.overall_score < 80):
            raise ValueError(
                f"decision 'possible_fit' requires score 65-79, got {self.overall_score}"
            )
        if self.decision == "weak_fit" and not (45 <= self.overall_score < 65):
            raise ValueError(
                f"decision 'weak_fit' requires score 45-64, got {self.overall_score}"
            )
        if self.decision == "reject" and self.overall_score >= 45:
            raise ValueError(
                f"decision 'reject' requires score < 45, got {self.overall_score}"
            )

    def to_dict(self) -> dict:
        """
        Convert to JSON-serializable dict.

        Returns:
            Dict with all match result fields
        """
        return {
            "candidate_id": self.candidate_id,
            "job_fingerprint": self.job_fingerprint,
            "overall_score": self.overall_score,
            "decision": self.decision,
            "dimension_scores": self.dimension_scores.copy(),
            "reasons": self.reasons.copy(),
            "matched_keywords": self.matched_keywords.copy(),
            "missing_keywords": self.missing_keywords.copy(),
            "meta": self.meta.copy() if self.meta else {},
        }
