"""Parses JUnit-style testsuite/testcase XML (Maven Surefire, TestNG's
JUnitReportReporter, pytest --junitxml, and most other CI test runners emit
this same schema, so this parser isn't Java-specific)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from triage.models import FailureRecord


def parse_junit_xml(path: str | Path) -> list[FailureRecord]:
    """Extract one FailureRecord per <failure>/<error> testcase in the given file.

    Passing and skipped testcases are ignored - only actionable failures are returned.
    """
    path = Path(path)
    tree = ET.parse(path)
    root = tree.getroot()

    # Root is either a single <testsuite> or a <testsuites> wrapping several.
    testcases = root.iter("testcase")

    records: list[FailureRecord] = []
    for testcase in testcases:
        outcome = testcase.find("failure")
        if outcome is None:
            outcome = testcase.find("error")
        if outcome is None:
            continue  # passed or skipped - not our concern

        name = testcase.get("name", "unknown")
        class_name = testcase.get("classname", "unknown")
        message = outcome.get("message", "") or ""
        stack_trace = (outcome.text or "").strip()
        duration = float(testcase.get("time", 0.0) or 0.0)

        records.append(
            FailureRecord(
                test_name=name,
                class_name=class_name,
                message=message,
                stack_trace=stack_trace,
                source_format="junit",
                source_file=str(path),
                duration_seconds=duration,
            )
        )
    return records
