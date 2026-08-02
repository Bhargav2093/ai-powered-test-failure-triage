from pathlib import Path

from triage.parsers.allure_json import parse_allure_results
from triage.parsers.junit_xml import parse_junit_xml

FIXTURES = Path(__file__).parent / "fixtures"


class TestJunitXmlParser:
    def test_parses_real_framework_failure(self):
        records = parse_junit_xml(FIXTURES / "real_framework_failure" / "junit-report.xml")

        assert len(records) == 1
        record = records[0]
        assert record.test_name == "getSinglePostReturnsValidSchema"
        assert record.class_name == "com.automation.hybrid.tests.api.PostsApiTests"
        assert "expected [999] but found [1]" in record.message
        assert "AssertionError" in record.stack_trace
        assert record.source_format == "junit"

    def test_parses_synthetic_mixed_failures(self):
        records = parse_junit_xml(FIXTURES / "synthetic" / "mixed_failures.xml")

        assert len(records) == 4
        names = {r.test_name for r in records}
        assert names == {
            "loginButtonClickable",
            "submitButtonStaleAfterReload",
            "pingInternalService",
            "cartTotalMatchesLineItems",
        }

    def test_error_elements_are_treated_like_failures(self):
        records = parse_junit_xml(FIXTURES / "synthetic" / "mixed_failures.xml")

        infra_record = next(r for r in records if r.test_name == "pingInternalService")
        assert "ConnectException" in infra_record.stack_trace

    def test_full_name_combines_class_and_test(self):
        records = parse_junit_xml(FIXTURES / "real_framework_failure" / "junit-report.xml")

        assert records[0].full_name == (
            "com.automation.hybrid.tests.api.PostsApiTests.getSinglePostReturnsValidSchema"
        )


class TestAllureJsonParser:
    def test_parses_real_framework_failure(self):
        records = parse_allure_results(FIXTURES / "real_framework_failure")

        assert len(records) == 1
        record = records[0]
        assert record.test_name == "getSinglePostReturnsValidSchema"
        assert record.class_name == "com.automation.hybrid.tests.api.PostsApiTests"
        assert "expected [999] but found [1]" in record.message
        assert record.source_format == "allure"
        assert record.duration_seconds > 0

    def test_ignores_directories_with_no_result_files(self, tmp_path):
        records = parse_allure_results(tmp_path)

        assert records == []
