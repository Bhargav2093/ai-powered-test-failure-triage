"""Parses Allure's *-result.json files (one per test case)."""

from __future__ import annotations

import json
from pathlib import Path

from triage.models import FailureRecord

_FAILED_STATUSES = {"failed", "broken"}


def _label(labels: list[dict], name: str, default: str = "") -> str:
    for label in labels:
        if label.get("name") == name:
            return label.get("value", default)
    return default


def parse_allure_results(directory: str | Path) -> list[FailureRecord]:
    """Extract one FailureRecord per failed/broken *-result.json in the given directory.

    Allure also writes *-container.json files in the same directory - those are
    skipped since they describe suite/fixture structure, not individual tests.
    """
    directory = Path(directory)
    records: list[FailureRecord] = []

    for result_file in sorted(directory.glob("*-result.json")):
        with result_file.open(encoding="utf-8") as f:
            data = json.load(f)

        status = data.get("status", "")
        if status not in _FAILED_STATUSES:
            continue

        labels = data.get("labels", [])
        test_name = _label(labels, "testMethod") or data.get("name", "unknown")
        class_name = _label(labels, "testClass") or _label(labels, "package", "unknown")

        status_details = data.get("statusDetails", {}) or {}
        message = status_details.get("message", "") or ""
        stack_trace = status_details.get("trace", "") or ""

        start = data.get("start")
        stop = data.get("stop")
        duration = (stop - start) / 1000.0 if start is not None and stop is not None else 0.0

        records.append(
            FailureRecord(
                test_name=test_name,
                class_name=class_name,
                message=message,
                stack_trace=stack_trace,
                source_format="allure",
                source_file=str(result_file),
                duration_seconds=duration,
            )
        )
    return records
