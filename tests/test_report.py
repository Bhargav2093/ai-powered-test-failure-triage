import json

from triage.models import (
    Category,
    Classification,
    ClassifiedFailure,
    Cluster,
    Confidence,
    FailureRecord,
    TriageResult,
)
from triage.report import render_html, render_json, render_markdown


def _result() -> TriageResult:
    record = FailureRecord(
        test_name="loginButtonClickable",
        class_name="com.example.LoginTests",
        message="element click intercepted",
        stack_trace="org.openqa.selenium.ElementClickInterceptedException: element click intercepted",
        source_format="junit",
        source_file="dummy.xml",
    )
    classification = Classification(
        category=Category.FLAKY, confidence=Confidence.MEDIUM,
        matched_signals=("ElementClickInterceptedException",),
    )
    member = ClassifiedFailure(record=record, classification=classification)
    cluster = Cluster(id=0, members=[member], signature="ElementClickInterceptedException")
    return TriageResult(clusters=[cluster])


class TestRenderHtml:
    def test_contains_test_name_and_category(self):
        html = render_html(_result(), narratives={0: "Likely a timing issue."})

        assert "loginButtonClickable" in html
        assert "flaky" in html
        assert "Likely a timing issue." in html

    def test_is_a_single_self_contained_document(self):
        html = render_html(_result(), narratives={0: "narrative"})

        assert html.strip().startswith("<!DOCTYPE html>")
        assert "<style>" in html  # inline CSS, no external stylesheet link
        assert "http://" not in html and "https://" not in html


class TestRenderJson:
    def test_round_trips_as_valid_json(self):
        payload = render_json(_result(), narratives={0: "narrative text"})

        data = json.loads(payload)

        assert data["total_failures"] == 1
        assert data["counts"]["flaky"] == 1
        assert data["counts"]["infra"] == 0
        assert data["clusters"][0]["narrative"] == "narrative text"
        assert data["clusters"][0]["affected"] == ["com.example.LoginTests.loginButtonClickable"]


class TestRenderMarkdown:
    def test_contains_summary_table_and_narrative(self):
        markdown = render_markdown(_result(), narratives={0: "Likely a timing issue."})

        assert "| flaky | 1 |" in markdown
        assert "Likely a timing issue." in markdown
        assert "loginButtonClickable" in markdown
