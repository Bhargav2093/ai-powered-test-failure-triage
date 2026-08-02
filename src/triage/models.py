"""Core data structures shared across the triage pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Category(str, Enum):
    FLAKY = "flaky"
    REGRESSION = "regression"
    INFRA = "infra"


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class FailureRecord:
    """One failing (or errored) test, normalized from whichever source format parsed it."""

    test_name: str
    class_name: str
    message: str
    stack_trace: str
    source_format: str  # "junit" or "allure"
    source_file: str
    duration_seconds: float = 0.0

    @property
    def full_name(self) -> str:
        return f"{self.class_name}.{self.test_name}"


@dataclass(frozen=True)
class Classification:
    category: Category
    confidence: Confidence
    matched_signals: tuple[str, ...] = ()


@dataclass(frozen=True)
class ClassifiedFailure:
    record: FailureRecord
    classification: Classification


@dataclass
class Cluster:
    """A group of failures believed to share the same root cause."""

    id: int
    members: list[ClassifiedFailure]
    signature: str

    @property
    def representative(self) -> ClassifiedFailure:
        return self.members[0]

    @property
    def category(self) -> Category:
        return self.representative.classification.category

    @property
    def size(self) -> int:
        return len(self.members)


@dataclass
class TriageResult:
    """The full output of a triage run: every cluster, plus counts by category."""

    clusters: list[Cluster] = field(default_factory=list)

    @property
    def total_failures(self) -> int:
        return sum(c.size for c in self.clusters)

    def count_by_category(self, category: Category) -> int:
        return sum(c.size for c in self.clusters if c.category == category)
