"""Rule-based classification of a failure into flaky / regression / infra.

No ML, no API calls - pure pattern matching against the exception type and
message text embedded in the stack trace. This is the deterministic core of
the pipeline: it always works, requires no network access, and never
misclassifies a real bug as flaky (REGRESSION is the safe default).
"""

from __future__ import annotations

import re

from triage.models import Category, Classification, Confidence, FailureRecord

# Ordered from most to least specific isn't required here since categories
# are mutually exclusive by signal - a signal belongs to exactly one set.
_FLAKY_SIGNALS = (
    "StaleElementReferenceException",
    "ElementClickInterceptedException",
    "ElementNotInteractableException",
    "TimeoutException",
    "NoSuchElementException",
)

_INFRA_SIGNALS = (
    "ConnectException",
    "SocketTimeoutException",
    "UnknownHostException",
    "NoHttpResponseException",
    "connection refused",
    "could not connect",
)

_HIGH_CONFIDENCE_SIGNAL_COUNT = 2


def classify(record: FailureRecord) -> Classification:
    """Classify a single failure using its exception type and message text."""
    haystack = f"{record.message}\n{record.stack_trace}"

    flaky_matches = _find_matches(haystack, _FLAKY_SIGNALS)
    if flaky_matches:
        return Classification(
            category=Category.FLAKY,
            confidence=_confidence_for(flaky_matches),
            matched_signals=flaky_matches,
        )

    infra_matches = _find_matches(haystack, _INFRA_SIGNALS)
    if infra_matches:
        return Classification(
            category=Category.INFRA,
            confidence=_confidence_for(infra_matches),
            matched_signals=infra_matches,
        )

    return Classification(
        category=Category.REGRESSION,
        confidence=Confidence.MEDIUM,
        matched_signals=(),
    )


def _find_matches(haystack: str, signals: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(
        signal
        for signal in signals
        if re.search(re.escape(signal), haystack, re.IGNORECASE)
    )


def _confidence_for(matches: tuple[str, ...]) -> Confidence:
    return Confidence.HIGH if len(matches) >= _HIGH_CONFIDENCE_SIGNAL_COUNT else Confidence.MEDIUM
